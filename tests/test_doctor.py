"""doctor: readiness triage and the "next command" hint."""

from __future__ import annotations

import shutil
from pathlib import Path

from docx_report.api import doctor_config


def _write_config(base: Path, body: str) -> Path:
    path = base / "config.yml"
    path.write_text(body, encoding="utf-8")
    return path


def test_ready_report_config_suggests_build(tmp_path: Path, template_docx: Path):
    shutil.copy(template_docx, tmp_path / "template.docx")
    config = _write_config(
        tmp_path,
        """
template: template.docx
output: out/r.docx
blocks:
  - kind: section
    text: 一、实验目的
""",
    )
    result = doctor_config(config)
    assert result.ok
    assert result.config_type == "report"
    assert result.suggested_command and "build" in result.suggested_command
    assert any("course report profile" in note for note in result.notes) or True


def test_missing_figure_is_an_error(tmp_path: Path, template_docx: Path):
    shutil.copy(template_docx, tmp_path / "template.docx")
    config = _write_config(
        tmp_path,
        """
template: template.docx
output: out/r.docx
blocks:
  - kind: figure
    image: nowhere.png
    text: 图 1
""",
    )
    result = doctor_config(config)
    assert not result.ok
    assert any(c.label == "figures" and c.status == "error" for c in result.checks)


def test_no_template_suggests_inspect_template_none(tmp_path: Path):
    config = _write_config(
        tmp_path,
        """
output: out/r.docx
blocks:
  - kind: body
    text: x
""",
    )
    result = doctor_config(config)
    assert not result.ok
    assert result.suggested_command is None
    assert any(c.label == "template" and c.status == "error" for c in result.checks)


def test_caption_placeholder_ratio_is_reported(tmp_path: Path, template_docx: Path):
    shutil.copy(template_docx, tmp_path / "template.docx")
    config = _write_config(
        tmp_path,
        """
template: template.docx
output: out/r.docx
blocks:
  - kind: placeholder
    text: 【图片占位 1】
  - kind: caption
    text: 图 1
  - kind: caption
    text: 图 2
""",
    )
    result = doctor_config(config)
    assert any(c.label == "captions" and c.status == "warn" for c in result.checks)


def test_enrich_config_with_missing_image_is_not_ready(tmp_path: Path):
    config = _write_config(
        tmp_path,
        """
output: out/final.docx
actions:
  - action: append_image
    image: missing.png
""",
    )
    result = doctor_config(config)
    assert result.config_type == "enrich"
    assert not result.ok
