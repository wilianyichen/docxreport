"""Stable JSON metrics helpers shared by notebooks and report checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL = ("run", "data", "requirements")


def save_metrics_json(payload: dict[str, Any], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)
    return path


def load_metrics_json(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("metrics JSON must contain a top-level object")
    return data


def validate_metrics(payload_or_path: dict[str, Any] | Path, *, strict: bool = False) -> list[str]:
    payload = load_metrics_json(payload_or_path) if isinstance(payload_or_path, Path) else payload_or_path
    problems: list[str] = []
    if not isinstance(payload, dict):
        return ["metrics payload is not an object"]
    for key in REQUIRED_TOP_LEVEL:
        if key not in payload:
            problems.append(f"missing top-level key: {key}")
    run = payload.get("run") or {}
    for key in ("python_executable", "python_version"):
        if strict and not run.get(key):
            problems.append(f"missing run.{key}")
    requirements = payload.get("requirements")
    if requirements is not None and not isinstance(requirements, dict):
        problems.append("requirements must be an object")
    return problems
