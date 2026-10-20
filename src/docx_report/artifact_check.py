"""Artifact integrity checks: missing, duplicate, stale and unreferenced figures."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ArtifactCheckResult:
    ok: bool
    checks: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        lines = [f"{'OK' if self.ok else 'BLOCK'}: artifact check"]
        lines.extend(f"[OK] {x}" for x in self.checks)
        lines.extend(f"[WARN] {x}" for x in self.warnings)
        lines.extend(f"[BLOCK] {x}" for x in self.errors)
        return lines


def check_artifacts(
    root: Path, *, referenced: Iterable[Path] = (), metrics: Path | None = None, notebook: Path | None = None
) -> ArtifactCheckResult:
    root = Path(root)
    errors: list[str] = []
    warnings: list[str] = []
    if not root.exists():
        return ArtifactCheckResult(False, errors=[f"artifact root not found: {root}"])

    images = sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )
    groups: dict[str, list[Path]] = {}
    for path in images:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        groups.setdefault(digest, []).append(path)
    dup = [paths for paths in groups.values() if len(paths) > 1]
    if dup:
        warnings.extend("duplicate bytes: " + " | ".join(str(p) for p in paths) for paths in dup)

    refs = [Path(p) for p in referenced]
    missing = [p for p in refs if not p.exists()]
    if missing:
        errors.append(f"missing referenced artifacts: {[str(p) for p in missing]}")
    ref_resolved = {p.resolve() for p in refs if p.exists()}
    orphan = [p for p in images if p.resolve() not in ref_resolved] if refs else []
    if orphan:
        warnings.append(f"unreferenced images: {len(orphan)}")

    if metrics is not None:
        metrics = Path(metrics)
        if not metrics.exists():
            errors.append(f"metrics file not found: {metrics}")
        elif (
            notebook is not None
            and Path(notebook).exists()
            and metrics.stat().st_mtime < Path(notebook).stat().st_mtime
        ):
            warnings.append("metrics file is older than notebook")

    checks = [
        f"{len(images)} image files",
        f"{len(dup)} duplicate-byte groups",
        f"{len(missing)} missing references",
    ]
    return ArtifactCheckResult(not errors, checks, errors, warnings)


def referenced_images_from_config(config_path: Path) -> list[Path]:
    from .config_loader import load_report_config

    cfg = load_report_config(Path(config_path))
    found: list[Path] = []
    for block in cfg.blocks:
        if block.kind != "figure":
            continue
        raw = str(block.meta.get("image") or "")
        if not raw:
            continue
        cand = Path(raw)
        found.append(cand if cand.is_absolute() else (Path.cwd() / cand))
    return found
