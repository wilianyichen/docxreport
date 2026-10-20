from __future__ import annotations

from pathlib import Path


def default_config_root(project_root: Path) -> Path:
    return project_root / 'report_configs'


def resolve_experiment_report_config(project_root: Path, experiment_name: str) -> Path:
    config_path = default_config_root(project_root) / experiment_name / 'report.yml'
    if not config_path.exists():
        raise FileNotFoundError(config_path)
    return config_path
