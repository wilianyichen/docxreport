"""Schema <-> loader agreement: every shipped example must satisfy its schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from docx_report.config_loader import load_enrichment_config, load_report_config

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "report": json.loads((ROOT / "schema" / "report.schema.json").read_text(encoding="utf-8")),
    "enrich": json.loads((ROOT / "schema" / "enrich.schema.json").read_text(encoding="utf-8")),
}


def _examples() -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    for path in sorted((ROOT / "examples").rglob("*.yml")):
        if "课程报告范式" in path.name:
            continue  # course profile has its own shape
        kind = "enrich" if path.name.startswith(("finalize", "enrich")) else "report"
        found.append((kind, path))
    return found


@pytest.mark.parametrize(("kind", "path"), _examples(), ids=lambda value: getattr(value, "name", str(value)))
def test_example_matches_schema(kind: str, path: Path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(SCHEMAS[kind])
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


@pytest.mark.parametrize(("kind", "path"), _examples(), ids=lambda value: getattr(value, "name", str(value)))
def test_schema_valid_example_also_loads(kind: str, path: Path):
    """The schema must not accept configs the loader rejects."""
    if kind == "enrich":
        config = load_enrichment_config(path)
        assert config.actions
    else:
        config = load_report_config(path)
        assert config.blocks


def _validate(kind: str, payload: dict) -> list[str]:
    validator = Draft202012Validator(SCHEMAS[kind])
    return [e.message for e in validator.iter_errors(payload)]


def test_report_requires_output_and_blocks():
    assert _validate("report", {"blocks": [{"kind": "body"}]})
    assert _validate("report", {"output": "o.docx"})
    assert not _validate("report", {"output": "o.docx", "blocks": [{"kind": "body", "text": "x"}]})


def test_unknown_block_kind_is_rejected():
    errors = _validate("report", {"output": "o.docx", "blocks": [{"kind": "sparkline"}]})
    assert errors


def test_figure_requires_image_and_group_requires_items():
    assert _validate("report", {"output": "o.docx", "blocks": [{"kind": "figure", "text": "x"}]})
    assert _validate("report", {"output": "o.docx", "blocks": [{"kind": "figure_group", "text": "x"}]})
    ok = {
        "output": "o.docx",
        "blocks": [
            {"kind": "figure", "image": "a.png", "text": "图 1"},
            {"kind": "figure_group", "items": [{"image": "a.png", "text": "图 2"}]},
        ],
    }
    assert not _validate("report", ok)


def test_figure_group_allows_at_most_two_images():
    payload = {
        "output": "o.docx",
        "blocks": [{"kind": "figure_group", "items": [{"image": "a.png"}] * 3}],
    }
    assert _validate("report", payload)


def test_metrics_requires_source():
    assert _validate("report", {"output": "o.docx", "blocks": [{"kind": "metrics", "fields": []}]})


def test_enrich_action_requirements():
    assert _validate("enrich", {"actions": [{"action": "insert_image_after_anchor"}]})
    assert _validate("enrich", {"actions": [{"action": "append_heading"}]})
    assert _validate("enrich", {"actions": [{"action": "nope"}]})
    assert not _validate("enrich", {"actions": [{"action": "append_heading", "text": "附录"}]})


def test_styles_reject_unknown_keys():
    payload = {
        "output": "o.docx",
        "styles": {"body": {"font_size": 12}},
        "blocks": [{"kind": "body", "text": "x"}],
    }
    assert _validate("report", payload)
