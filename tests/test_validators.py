"""Validators: template layout assumptions and report openability."""

from __future__ import annotations

from pathlib import Path

from docx_report.config_loader import load_enrichment_config
from docx_report.models import TemplateLayoutAssumptions
from docx_report.validators import validate_report, validate_report_file, validate_template_layout


def test_fixture_template_matches_assumptions(template_docx: Path):
    result = validate_template_layout(template_docx, TemplateLayoutAssumptions())
    assert result.ok, result.summary_lines()
    assert "2 tables" in result.messages[0]


def test_template_with_more_required_tables_fails(template_docx: Path):
    result = validate_template_layout(template_docx, TemplateLayoutAssumptions(required_table_count=3))
    assert not result.ok
    assert "expected at least 3 tables" in result.messages[0]


def test_missing_template_is_reported(tmp_path: Path):
    result = validate_template_layout(tmp_path / "nope.docx", TemplateLayoutAssumptions())
    assert not result.ok
    assert "not found" in result.messages[0]


def test_validate_report_file_rejects_non_docx(tmp_path: Path):
    junk = tmp_path / "fake.docx"
    junk.write_text("not a zip", encoding="utf-8")
    result = validate_report_file(junk)
    assert not result.ok
    assert "python-docx failed" in result.messages[0]


def test_validate_report_end_to_end(tmp_path: Path, template_docx: Path, png):
    import shutil

    from docx_report.api import build_report

    shutil.copy(template_docx, tmp_path / "template.docx")
    png("fig.png")
    config = tmp_path / "config.yml"
    config.write_text(
        """
template: template.docx
output: out/r.docx
blocks:
  - kind: section
    text: 一、实验目的
  - kind: figure
    image: fig.png
    text: 图 1 结果
""",
        encoding="utf-8",
    )
    output = build_report(config)
    result = validate_report(config, output)
    assert result.ok, result.summary_lines()
    assert any("placeholder occurrences" in message for message in result.messages)


def test_validate_enrich_config_checks_anchor(tmp_path: Path, write_text, png):
    from docx import Document

    docx = tmp_path / "existing.docx"
    doc = Document()
    doc.add_paragraph("二、实验原理")
    doc.save(str(docx))
    png("f.png")

    config = load_enrichment_config(
        write_text(
            "enrich.yml",
            """
output: out.docx
actions:
  - action: insert_image_after_anchor
    anchor: 二、实验原理
    image: f.png
""",
        )
    )
    ok = validate_report(config, docx)
    assert ok.ok, ok.summary_lines()

    missing = load_enrichment_config(
        write_text(
            "bad.yml",
            """
actions:
  - action: insert_image_after_anchor
    anchor: 不存在的标题
    image: f.png
""",
        )
    )
    assert not validate_report(missing, docx).ok
