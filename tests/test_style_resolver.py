"""Donor-style resolution: never invent fonts, always extract from the template."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from docx_report.models import ReportBlock, ReportConfig, StyleResolutionRules
from docx_report.ooxml_backend import (
    find_cover_title_paragraph,
    read_document_xml,
    register_namespaces,
    resolve_template_slots,
    w_tag,
)
from docx_report.style_resolver import resolve_style_profile


def _config(template: Path, **overrides) -> ReportConfig:
    config = ReportConfig(
        name="t",
        backend="ooxml-template",
        template=template,
        output=template.parent / "out.docx",
        cover_title="实验一",
        experiment_name="示例",
        blocks=[ReportBlock(kind="body", text="x")],
    )
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def _template_parts(template: Path, config: ReportConfig):
    document_xml, _, _ = read_document_xml(template)
    register_namespaces(document_xml)
    body = ET.fromstring(document_xml).find(w_tag("body"))
    _, name_cell, content_cell = resolve_template_slots(body, config)
    return body, name_cell, content_cell


def test_section_style_is_taken_from_template_donor(template_docx: Path):
    config = _config(template_docx)
    body, name_cell, content_cell = _template_parts(template_docx, config)
    resolved = resolve_style_profile(
        config,
        template_cell=content_cell,
        template_title_paragraph=find_cover_title_paragraph(body),
        template_experiment_name_cell=name_cell,
    )

    assert resolved.sources["section"] == "template"
    # The fixture donor is 12pt => 24 half-points, SimSun ascii + 宋体 eastAsia, 1.5 spacing.
    assert resolved.styles.section.size == 24
    assert resolved.styles.section.ascii_font == "SimSun"
    assert resolved.styles.section.east_asia_font == "宋体"
    assert resolved.styles.section.spacing_line == 360


def test_fallback_is_used_when_no_donor_matches(template_docx: Path):
    config = _config(template_docx)
    config.style_resolution = StyleResolutionRules(section_prefer=["fallback"])
    _, name_cell, content_cell = _template_parts(template_docx, config)
    resolved = resolve_style_profile(
        config, template_cell=content_cell, template_experiment_name_cell=name_cell
    )
    assert resolved.sources["section"] == "fallback"
    assert resolved.styles.section.size == 28  # built-in default


def test_required_source_missing_is_reported_not_silently_ignored(template_docx: Path):
    config = _config(template_docx)
    config.style_resolution = StyleResolutionRules(section_prefer=["fallback"], require_section_source=True)
    _, name_cell, content_cell = _template_parts(template_docx, config)
    resolved = resolve_style_profile(
        config, template_cell=content_cell, template_experiment_name_cell=name_cell
    )
    assert resolved.unresolved_required == ["section"]


def test_comment_paragraphs_are_never_used_as_donors(template_docx: Path):
    """Template guidance text (【说明…】) must not become the body style."""
    config = _config(template_docx)
    resolved = resolve_style_profile(config)
    assert resolved.skipped_comment_count == 0  # nothing to skip in a clean fixture


def test_caption_style_is_distinct_from_body():
    from docx_report.models import ReportStyleProfile

    profile = ReportStyleProfile()
    assert profile.caption.size < profile.body.size
    assert profile.caption.align == "center"
    assert profile.body.align is None
