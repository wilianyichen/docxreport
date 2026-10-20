from __future__ import annotations

"""Experiment completeness gate used before a report is declared build-ready."""

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .course_profile import read_structured_file
from .metrics_schema import load_metrics_json, validate_metrics
from .notebook_check import check_notebook, check_screenshot_units, notebook_code_text, NotebookCheckResult

BLOCKING = {"missing", "partial", "blocked", "inconsistent", "stale"}


@dataclass
class ReadinessItem:
    item_id: str
    status: str
    message: str


@dataclass
class ExperimentReadinessResult:
    ok: bool
    items: list[ReadinessItem] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)

    def summary_lines(self) -> list[str]:
        lines = [f"{'READY' if self.ok else 'BLOCK'}: experiment readiness"]
        for item in self.items:
            tag = "OK" if item.status == "complete" else item.status.upper()
            lines.append(f"[{tag}] {item.item_id}: {item.message}")
        return lines


def _resolve(base: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_absolute() else (base / p).resolve()


def _runtime_probe(executable: Path, imports: list[str], *, isolate_user_site: bool = False) -> tuple[bool, dict[str, Any], str]:
    code = (
        "import importlib,json,platform,sys; out={'python_executable':sys.executable,"
        "'python_version':platform.python_version(),'packages':{}}; "
        f"mods={imports!r}; "
        "[(lambda m: out['packages'].__setitem__(m,getattr(importlib.import_module(m),'__version__','unknown')))(m) for m in mods]; "
        "print(json.dumps(out))"
    )
    cmd = [str(executable)] + (["-s"] if isolate_user_site else []) + ["-c", code]
    run = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if run.returncode:
        return False, {}, (run.stderr or run.stdout).strip()
    return True, json.loads(run.stdout.strip().splitlines()[-1]), ""


def check_experiment_readiness(requirements_path: Path) -> ExperimentReadinessResult:
    requirements_path = Path(requirements_path).resolve()
    req = read_structured_file(requirements_path)
    if req.get("kind") != "experiment-requirements":
        raise ValueError("requirements kind must be experiment-requirements")
    base = requirements_path.parent
    inputs = req.get("inputs") or {}
    notebook = _resolve(base, inputs.get("notebook"))
    source_py = _resolve(base, inputs.get("source_py"))
    metrics_path = _resolve(base, inputs.get("metrics"))
    items: list[ReadinessItem] = []
    facts: dict[str, Any] = {}
    nb_text = ""

    env = req.get("environment") or {}
    exe = _resolve(base, env.get("python_executable"))
    if exe is None or not exe.exists():
        items.append(ReadinessItem("environment", "blocked", f"required interpreter not found: {exe}"))
    else:
        imports = [str(x) for x in env.get("required_imports", [])]
        ok, runtime, error = _runtime_probe(exe, imports, isolate_user_site=bool(env.get("isolate_user_site", False)))
        if not ok:
            items.append(ReadinessItem("environment", "blocked", error))
        else:
            expected = str(env.get("python_version") or "")
            version_ok = not expected or runtime["python_version"].startswith(expected.rstrip("*"))
            exe_ok = Path(runtime["python_executable"]).resolve() == exe.resolve()
            status = "complete" if version_ok and exe_ok else "inconsistent"
            items.append(ReadinessItem("environment", status, json.dumps(runtime, ensure_ascii=False)))
            facts["runtime"] = runtime

    if notebook is None:
        items.append(ReadinessItem("notebook", "missing", "notebook path not declared"))
    else:
        nb = check_notebook(notebook, max_images_per_cell=int(req.get("max_images_per_cell", 2)))
        for line in nb.summary_lines():
            pass
        items.append(ReadinessItem("notebook", "complete" if nb.ok else "inconsistent", "; ".join(nb.summary_lines())))
        facts["notebook"] = nb.facts
        try:
            nb_text = notebook_code_text(notebook)
        except Exception:  # noqa: BLE001
            nb_text = ""
        units = req.get("screenshot_units") or []
        if units:
            try:
                su = check_screenshot_units(notebook, units)
            except Exception as exc:  # noqa: BLE001
                su = NotebookCheckResult(
                    True,
                    checks=[],
                    errors=[],
                    warnings=[f"screenshot-units check skipped: {exc}"],
                    facts={"units": units},
                )
            items.append(ReadinessItem("screenshot-units", "complete" if su.ok else "inconsistent",
                                       "; ".join(su.checks + su.errors)))

    metrics: dict[str, Any] = {}
    if metrics_path is None or not metrics_path.exists():
        items.append(ReadinessItem("metrics", "missing", f"metrics not found: {metrics_path}"))
    else:
        metrics = load_metrics_json(metrics_path)
        problems = validate_metrics(metrics, strict=True)
        items.append(ReadinessItem("metrics", "complete" if not problems else "inconsistent", "; ".join(problems) or str(metrics_path)))
        freshness_source = source_py if source_py is not None and source_py.exists() else notebook
        if freshness_source is not None and freshness_source.exists() and metrics_path.stat().st_mtime < freshness_source.stat().st_mtime:
            items.append(ReadinessItem("freshness", "stale", f"metrics file is older than source: {freshness_source}"))

    declared = metrics.get("requirements") or {}
    for group, optional in (("mandatory", False), ("advanced", True)):
        for spec in req.get(group) or []:
            item_id = str(spec.get("id"))
            status = str(declared.get(item_id, {}).get("status") if isinstance(declared.get(item_id), dict) else declared.get(item_id, "missing")).lower()
            message = str(declared.get(item_id, {}).get("message", "") if isinstance(declared.get(item_id), dict) else "")
            if optional and status in {"optional_not_done", "blocked"} and bool(spec.get("external_input_required")):
                items.append(ReadinessItem(item_id, "optional_not_done", message or "external input not provided"))
            else:
                items.append(ReadinessItem(item_id, status, message or f"metrics requirements status={status}"))
            missing_methods = [token for token in (spec.get("requires_methods") or []) if token not in nb_text]
            if missing_methods:
                items.append(ReadinessItem(item_id, "inconsistent",
                                           "notebook has no executed evidence for: " + ", ".join(missing_methods)))

    ok = not any(i.status in BLOCKING for i in items)
    return ExperimentReadinessResult(ok, items, facts)
