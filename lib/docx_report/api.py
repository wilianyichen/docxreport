from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from .config_loader import _load_mapping, load_enrichment_config, load_report_config
from .doctor import doctor_config as run_doctor
from .enrich import enrich_existing_report
from .experiment_readiness import check_experiment_readiness
from .models import DoctorResult, EnrichmentConfig, ReportConfig, ValidationResult
from .ooxml_backend import build_report_package, find_cover_title_paragraph, read_document_xml, register_namespaces, resolve_template_slots, w_tag, write_document_xml
from .style_resolver import resolve_style_profile
from .revision import revise_existing_report
from .screenshot_plan import (
    generate_screenshot_plan as build_screenshot_plan,
    summarize_course_report_patterns,
)
from .validators import validate_report as run_validation


def build_report(config_or_path, *, output_path: Path | None = None) -> Path:
    config = _coerce_report_config(config_or_path)
    requirements_raw = (config.extras or {}).get("experiment_requirements")
    if requirements_raw:
        requirements_path = Path(str(requirements_raw))
        if not requirements_path.is_absolute() and config.source is not None:
            requirements_path = config.source.parent / requirements_path
        readiness = check_experiment_readiness(requirements_path)
        if not readiness.ok:
            details = chr(10).join(readiness.summary_lines())
            raise RuntimeError("experiment is not report-ready:" + chr(10) + details)
    if config.template is None:
        raise ValueError("build_report requires a template path in config")
    document_xml, extra_parts = build_report_package(config.template, config)
    _, infos, other_files = read_document_xml(config.template)
    other_files.update(extra_parts)
    final_output = output_path or config.output
    final_output.parent.mkdir(parents=True, exist_ok=True)
    write_document_xml(final_output, infos, other_files, document_xml)
    return final_output


def revise_report(config_or_path, input_docx: Path, *, output_path: Path | None = None) -> Path:
    config = _coerce_report_config(config_or_path)
    final_output = output_path or config.output
    final_output.parent.mkdir(parents=True, exist_ok=True)
    return revise_existing_report(config, Path(input_docx), output_path=final_output)


def enrich_report(config_or_path, input_docx: Path, *, output_path: Path | None = None) -> Path:
    config = load_enrichment_config(Path(config_or_path)) if not hasattr(config_or_path, "actions") else config_or_path
    final_output = output_path or config.output or Path(input_docx)
    final_output.parent.mkdir(parents=True, exist_ok=True)
    return enrich_existing_report(config, Path(input_docx), output_path=final_output)


def validate_report(config_or_path, input_docx: Path) -> ValidationResult:
    return run_validation(config_or_path, Path(input_docx))


def doctor_config(config_or_path, *, input_docx: Path | None = None) -> DoctorResult:
    return run_doctor(config_or_path, input_docx=Path(input_docx) if input_docx is not None else None)


def generate_screenshot_plan(config_or_path) -> list[dict[str, str]]:
    config = _coerce_report_config(config_or_path)
    return build_screenshot_plan(config)


def summarize_report_patterns(config_or_path) -> dict[str, object]:
    config = _coerce_report_config(config_or_path)
    return summarize_course_report_patterns(config)


def preview_config(config_or_path) -> dict[str, object]:
    if isinstance(config_or_path, EnrichmentConfig):
        return _preview_enrichment_config(config_or_path)
    if isinstance(config_or_path, ReportConfig):
        return _preview_report_config(config_or_path)
    path = Path(config_or_path)
    raw = _load_mapping(path)
    if isinstance(raw.get("actions"), list) and not raw.get("blocks"):
        return _preview_enrichment_config(load_enrichment_config(path))
    return _preview_report_config(load_report_config(path))


def _preview_report_config(config: ReportConfig) -> dict[str, object]:
    return {
        "type": "report",
        "name": config.name,
        "backend": config.backend,
        "template": str(config.template) if config.template else None,
        "output": str(config.output),
        "blocks": len(config.blocks),
        "block_kinds": _count_report_block_kinds(config),
        "expected_images": config.expected_images,
        "styles": _preview_report_styles(config),
        "style_resolution": _preview_style_resolution(config),
        "resolved_style_sources": _preview_resolved_style_sources(config),
    }


def _preview_enrichment_config(config: EnrichmentConfig) -> dict[str, object]:
    action_kinds: dict[str, int] = {}
    anchors: list[str] = []
    for action in config.actions:
        action_kinds[action.action] = action_kinds.get(action.action, 0) + 1
        if action.anchor:
            anchors.append(action.anchor)
    return {
        "type": "enrich",
        "name": config.name,
        "output": str(config.output) if config.output else None,
        "actions": len(config.actions),
        "action_kinds": action_kinds,
        "anchors": anchors,
    }


def _count_report_block_kinds(config: ReportConfig) -> dict[str, int]:
    counts: dict[str, int] = {}
    for block in config.blocks:
        counts[block.kind] = counts.get(block.kind, 0) + 1
    return counts


def _preview_report_styles(config: ReportConfig) -> dict[str, object]:
    return {
        "cover_title": _style_to_dict(config.styles.cover_title),
        "experiment_name": _style_to_dict(config.styles.experiment_name),
        "section": _style_to_dict(config.styles.section),
        "subheading": _style_to_dict(config.styles.subheading),
        "body": _style_to_dict(config.styles.body),
        "placeholder": _style_to_dict(config.styles.placeholder),
    }


def _style_to_dict(style) -> dict[str, object]:
    return {
        "ascii_font": style.ascii_font,
        "hansi_font": style.hansi_font,
        "east_asia_font": style.east_asia_font,
        "cs_font": style.cs_font,
        "size": style.size,
        "bold": style.bold,
        "color": style.color,
        "align": style.align,
        "spacing_after": style.spacing_after,
        "spacing_line": style.spacing_line,
        "spacing_line_rule": style.spacing_line_rule,
    }


def _preview_style_resolution(config: ReportConfig) -> dict[str, object]:
    return {
        "comment_patterns": config.style_resolution.comment_patterns,
        "cover_title_patterns": config.style_resolution.cover_title_patterns,
        "experiment_name_patterns": config.style_resolution.experiment_name_patterns,
        "section_patterns": config.style_resolution.section_patterns,
        "subheading_patterns": config.style_resolution.subheading_patterns,
        "placeholder_patterns": config.style_resolution.placeholder_patterns,
        "body_patterns": config.style_resolution.body_patterns,
        "cover_title": config.style_resolution.cover_title_prefer,
        "experiment_name": config.style_resolution.experiment_name_prefer,
        "section": config.style_resolution.section_prefer,
        "subheading": config.style_resolution.subheading_prefer,
        "body": config.style_resolution.body_prefer,
        "placeholder": config.style_resolution.placeholder_prefer,
    }


def _preview_resolved_style_sources(config: ReportConfig) -> dict[str, object]:
    if config.template is None:
        return {}
    try:
        document_xml, _, _ = read_document_xml(config.template)
        register_namespaces(document_xml)
        root = ET.fromstring(document_xml)
        body = root.find(w_tag('body'))
        if body is None:
            return {"warning": "template has no body"}
        _, report_name_cell, content_cell = resolve_template_slots(body, config)
        title_paragraph = find_cover_title_paragraph(body)
        resolved = resolve_style_profile(
            config,
            template_cell=content_cell,
            template_title_paragraph=title_paragraph,
            template_experiment_name_cell=report_name_cell,
        )
        return {
            "sources": resolved.sources,
            "unresolved_required": resolved.unresolved_required,
            "skipped_comment_count": resolved.skipped_comment_count,
        }
    except Exception as exc:
        return {"warning": f"could not resolve template donor styles: {exc}"}


def _coerce_report_config(config_or_path) -> ReportConfig:
    return load_report_config(Path(config_or_path)) if not isinstance(config_or_path, ReportConfig) else config_or_path
