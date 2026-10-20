from __future__ import annotations

"""Token-cheap checks for executed Jupyter notebooks."""

import base64
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class NotebookCheckResult:
    ok: bool
    checks: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)

    def summary_lines(self) -> list[str]:
        lines = [f"{'OK' if self.ok else 'BLOCK'}: notebook check"]
        lines.extend(f"[OK] {x}" for x in self.checks)
        lines.extend(f"[WARN] {x}" for x in self.warnings)
        lines.extend(f"[BLOCK] {x}" for x in self.errors)
        return lines


def check_notebook(path: Path, *, max_images_per_cell: int = 2) -> NotebookCheckResult:
    path = Path(path)
    if not path.exists():
        return NotebookCheckResult(False, errors=[f"notebook not found: {path}"])
    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return NotebookCheckResult(False, errors=[f"cannot parse notebook: {exc}"])

    cells = nb.get("cells") or []
    code = [(i, c) for i, c in enumerate(cells, 1) if c.get("cell_type") == "code"]
    unexecuted = [i for i, c in code if c.get("execution_count") is None and "".join(c.get("source", [])).strip()]
    error_cells: list[str] = []
    figure_counts: dict[int, int] = {}
    image_hashes: dict[str, list[str]] = {}
    execution_counts: list[int] = []

    for i, cell in code:
        count = cell.get("execution_count")
        if isinstance(count, int):
            execution_counts.append(count)
        figures = 0
        for j, output in enumerate(cell.get("outputs") or [], 1):
            if output.get("output_type") == "error":
                error_cells.append(f"cell {i}: {output.get('ename')}: {output.get('evalue')}")
            data = output.get("data") or {}
            for mime, payload in data.items():
                if not mime.startswith("image/"):
                    continue
                figures += 1
                raw = "".join(payload) if isinstance(payload, list) else str(payload)
                try:
                    digest = hashlib.sha256(base64.b64decode(raw)).hexdigest()
                except Exception:  # noqa: BLE001
                    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
                image_hashes.setdefault(digest, []).append(f"cell {i} output {j}")
        if figures:
            figure_counts[i] = figures

    errors: list[str] = []
    warnings: list[str] = []
    if unexecuted:
        errors.append(f"unexecuted code cells: {unexecuted}")
    if error_cells:
        errors.extend(error_cells)
    multi = {i: n for i, n in figure_counts.items() if n > max_images_per_cell}
    if multi:
        warnings.append("cell exceeds max images per cell (" + str(max_images_per_cell) + "): " + str(multi))
    duplicates = [refs for refs in image_hashes.values() if len(refs) > 1]
    if duplicates:
        warnings.append(f"duplicate embedded image groups: {duplicates}")
    if execution_counts and execution_counts != sorted(execution_counts):
        warnings.append("execution counts are not monotonically increasing")

    facts = {
        "path": str(path),
        "cells": len(cells),
        "code_cells": len(code),
        "executed_code_cells": len(code) - len(unexecuted),
        "error_outputs": len(error_cells),
        "image_outputs": sum(figure_counts.values()),
        "image_cells": figure_counts,
        "kernel": (nb.get("metadata") or {}).get("kernelspec"),
        "language_info": (nb.get("metadata") or {}).get("language_info"),
    }
    checks = [
        f"{len(cells)} cells; {len(code)} code cells",
        f"{len(code) - len(unexecuted)}/{len(code)} non-empty code cells executed",
        f"{sum(figure_counts.values())} embedded image outputs",
        f"0 error outputs" if not error_cells else f"{len(error_cells)} error outputs",
    ]
    return NotebookCheckResult(not errors, checks, errors, warnings, facts)


def notebook_code_text(path: Path, *, executed_only: bool = True) -> str:
    """Concatenated source of code cells, executed ones by default.

    Accepts both executed .ipynb JSON and Jupytext percent .py sources. For a .py
    source there are no execution counts, so `executed_only` is ignored there.
    """
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    try:
        nb = json.loads(raw)
    except Exception:  # noqa: BLE001
        # 非 JSON：当作 Jupytext percent .py 处理
        return _jupytext_code_text(raw)
    chunks: list[str] = []
    for cell in nb.get("cells") or []:
        if cell.get("cell_type") != "code":
            continue
        if executed_only and cell.get("execution_count") is None:
            continue
        source = "".join(cell.get("source", []))
        if source.strip():
            chunks.append(source)
    return chr(10).join(chunks)


def _percent_code_blocks(text: str) -> list[tuple[bool, list[str]]]:
    """Split Jupytext percent source into (is_markdown, lines) blocks."""
    blocks: list[tuple[bool, list[str]]] = []
    current: tuple[bool, list[str]] | None = None
    for line in text.splitlines():
        if line.startswith("# %%") or line.startswith("#%%"):
            current = ("[markdown]" in line, [])
            blocks.append(current)
            continue
        if current is not None:
            current[1].append(line)
    return blocks


def _normalize(lines) -> list[str]:
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        out.append(stripped)
    return out


def _jupytext_code_text(text: str) -> str:
    """Extract executed-code text from a Jupytext percent .py source.

    In percent format every code line is prefixed with '# '; strip that prefix so the
    returned text reads as real Python (used when a notebook isn't an .ipynb JSON file).
    Markdown cells are skipped.
    """
    chunks: list[str] = []
    for is_markdown, lines in _percent_code_blocks(text):
        if is_markdown:
            continue
        code: list[str] = []
        for line in lines:
            if line.startswith("# "):
                code.append(line[2:])
            elif line == "#":
                code.append("")
            else:
                code.append(line)
        joined = "\n".join(code).strip()
        if joined:
            chunks.append(joined)
    return "\n\n".join(chunks)


def _load_notebook_cells(path: Path, raw: str | None = None) -> list | None:
    """Return notebook cells if `path` is an executed .ipynb JSON, else None.

    Jupytext percent .py sources are not JSON and carry no execution outputs, so
    image-level screenshot validation does not apply to them.
    """
    if raw is None:
        raw = Path(path).read_text(encoding="utf-8")
    try:
        nb = json.loads(raw)
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(nb, dict) or "cells" not in nb:
        return None
    return nb.get("cells") or []


def check_notebook_pair(source_py: Path, ipynb_path: Path) -> NotebookCheckResult:
    """Detect drift between the Jupytext .py truth source and the executed .ipynb."""
    source_py = Path(source_py)
    ipynb_path = Path(ipynb_path)
    for candidate in (source_py, ipynb_path):
        if not candidate.exists():
            return NotebookCheckResult(False, errors=["not found: " + str(candidate)])
    text = source_py.read_text(encoding="utf-8")
    py_blocks = []
    for is_markdown, lines in _percent_code_blocks(text):
        if is_markdown:
            continue
        normalized = _normalize(lines)
        if normalized:
            py_blocks.append(normalized)

    nb = json.loads(ipynb_path.read_text(encoding="utf-8"))
    nb_blocks = []
    for cell in nb.get("cells") or []:
        if cell.get("cell_type") != "code":
            continue
        normalized = _normalize("".join(cell.get("source", [])).splitlines())
        if normalized:
            nb_blocks.append(normalized)

    errors: list[str] = []
    warnings: list[str] = []
    if len(py_blocks) != len(nb_blocks):
        errors.append("code cell count differs: py=" + str(len(py_blocks)) + " ipynb=" + str(len(nb_blocks)))
    else:
        for index, (a, b) in enumerate(zip(py_blocks, nb_blocks), 1):
            if a != b:
                errors.append("code cell " + str(index) + " differs between .py and .ipynb")
    checks = [
        "py code cells: " + str(len(py_blocks)),
        "ipynb code cells: " + str(len(nb_blocks)),
        "drift: " + ("none" if not errors else str(len(errors)) + " cell(s)"),
    ]
    return NotebookCheckResult(not errors, checks, errors, warnings,
                               {"source_py": str(source_py), "ipynb": str(ipynb_path)})


def check_screenshot_units(path: Path, units: list[dict]) -> NotebookCheckResult:
    """Validate that each declared screenshot unit maps to one executed code cell and its image count.

    规则：一个代码单元 = 一段自洽代码 + 它自己的全部输出 = 报告里的一张运行截图。
    注意：仅对「已执行的 .ipynb（JSON 格式）」做图片级校验；若传入的是 Jupytext percent
    .py 单一真源（非 JSON），则无图片可校验，降级为提示而不报错。
    """
    path = Path(path)
    if not path.exists():
        return NotebookCheckResult(False, errors=["notebook not found: " + str(path)])
    cells = _load_notebook_cells(path)
    if cells is None:
        return NotebookCheckResult(
            True,
            checks=[f"notebook is not executed .ipynb JSON (likely Jupytext .py source); screenshot image validation skipped: {path.name}"],
            errors=[],
            warnings=["screenshot units declared but notebook is not an executed .ipynb; verify images were produced and captured manually"],
            facts={"units": units, "skipped": True},
        )
    checks: list[str] = []
    errors: list[str] = []
    used: list[int] = []
    for unit in units:
        uid = str(unit.get("id"))
        index = int(unit.get("cell") or 0)
        expected = int(unit.get("images", 1))
        if not 1 <= index <= len(cells):
            errors.append(uid + ": cell " + str(index) + " out of range 1.." + str(len(cells)))
            continue
        cell = cells[index - 1]
        if cell.get("cell_type") != "code":
            errors.append(uid + ": cell " + str(index) + " is not a code cell")
            continue
        if cell.get("execution_count") is None:
            errors.append(uid + ": cell " + str(index) + " is not executed")
        actual = sum(1 for o in (cell.get("outputs") or []) if any(k.startswith("image/") for k in (o.get("data") or {})))
        if actual != expected:
            errors.append(uid + ": cell " + str(index) + " has " + str(actual) + " image output(s), declared " + str(expected))
        used.append(index)
    duplicate = sorted({i for i in used if used.count(i) > 1})
    if duplicate:
        errors.append("cells reused by multiple screenshot units: " + str(duplicate))
    checks.append(str(len(units)) + " screenshot units declared")
    checks.append("cells: " + ", ".join(str(i) for i in sorted(used)))
    return NotebookCheckResult(not errors, checks, errors, [], {"units": units})
