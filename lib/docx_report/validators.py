from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from docx import Document

from .config_loader import _load_mapping, load_enrichment_config, load_report_config
from .models import EnrichmentConfig, ReportConfig, TemplateLayoutAssumptions, ValidationResult
from .ooxml_backend import read_document_xml, register_namespaces, w_tag
from .pydocx_backend import find_paragraph_after


def validate_template_layout(template_path: Path, assumptions: TemplateLayoutAssumptions) -> ValidationResult:
    if not template_path.exists():
        return ValidationResult(False, [f'template not found: {template_path}'])
    try:
        document_xml, _, _ = read_document_xml(template_path)
        register_namespaces(document_xml)
        root = ET.fromstring(document_xml)
        body = root.find(w_tag('body'))
        if body is None:
            return ValidationResult(False, ['template has no body'])
        tables = body.findall(w_tag('tbl'))
        if len(tables) < assumptions.required_table_count:
            return ValidationResult(False, [f'expected at least {assumptions.required_table_count} tables, found {len(tables)}'])
        report_rows = tables[assumptions.report_table_index].findall(w_tag('tr'))
        if len(report_rows) <= assumptions.content_row:
            return ValidationResult(False, [f'report table has too few rows: {len(report_rows)}'])
        return ValidationResult(True, [f'template layout matches fixed-table assumptions ({len(tables)} tables found)'])
    except Exception as exc:  # pragma: no cover - defensive
        return ValidationResult(False, [str(exc)])


def validate_report_file(report_path: Path) -> ValidationResult:
    if not report_path.exists():
        return ValidationResult(False, [f'report not found: {report_path}'])
    try:
        Document(str(report_path))
        return ValidationResult(True, [f'report opens via python-docx: {report_path.name}'])
    except Exception as exc:  # pragma: no cover - defensive
        return ValidationResult(False, [f'python-docx failed to open report: {exc}'])


def validate_report(config_or_path, input_docx: Path) -> ValidationResult:
    if _looks_like_enrichment_config(config_or_path):
        config = config_or_path if isinstance(config_or_path, EnrichmentConfig) else load_enrichment_config(Path(config_or_path))
        return _validate_enriched_report(config, Path(input_docx))

    config = config_or_path if isinstance(config_or_path, ReportConfig) else load_report_config(Path(config_or_path))
    messages: list[str] = []
    ok = True
    if config.template is not None:
        layout_result = validate_template_layout(config.template, config.assumptions)
        messages.extend(layout_result.messages)
        ok = ok and layout_result.ok
    report_result = validate_report_file(input_docx)
    messages.extend(report_result.messages)
    ok = ok and report_result.ok
    if ok:
        try:
            with ZipFile(input_docx) as zf:
                document_xml = zf.read('word/document.xml').decode('utf-8', errors='ignore')
            placeholder_count = document_xml.count('截图占位')
            messages.append(f'placeholder occurrences in XML: {placeholder_count}')
        except Exception as exc:
            ok = False
            messages.append(f'failed to inspect report XML: {exc}')
    return ValidationResult(ok, messages)


def _validate_enriched_report(config: EnrichmentConfig, input_docx: Path) -> ValidationResult:
    report_result = validate_report_file(input_docx)
    messages = list(report_result.messages)
    ok = report_result.ok
    if not ok:
        return ValidationResult(False, messages)

    doc = Document(str(input_docx))
    for action in config.actions:
        if action.action == 'insert_image_after_anchor':
            if not action.anchor:
                ok = False
                messages.append('insert_image_after_anchor missing anchor')
                continue
            idx = find_paragraph_after(doc, action.anchor, skip=int(action.extras.get('skip', 0) or 0))
            if idx is None:
                ok = False
                messages.append(f'anchor missing in report: {action.anchor}')
            else:
                messages.append(f'anchor found in report: {action.anchor}')
            if action.image is not None:
                image_path = _resolve_enrichment_path(config, action.image)
                required = bool(action.extras.get('required', True))
                if image_path.exists():
                    messages.append(f'image file found: {image_path.name}')
                elif required:
                    ok = False
                    messages.append(f'image file missing: {image_path}')
                else:
                    messages.append(f'optional image file missing: {image_path}')
            continue

        if action.action == 'append_image' and action.image is not None:
            image_path = _resolve_enrichment_path(config, action.image)
            required = bool(action.extras.get('required', True))
            if image_path.exists():
                messages.append(f'append image file found: {image_path.name}')
            elif required:
                ok = False
                messages.append(f'append image file missing: {image_path}')
            else:
                messages.append(f'optional append image file missing: {image_path}')
    return ValidationResult(ok, messages)


def _looks_like_enrichment_config(config_or_path) -> bool:
    if isinstance(config_or_path, EnrichmentConfig):
        return True
    path = Path(config_or_path)
    suffix = path.suffix.lower()
    if suffix not in {'.yml', '.yaml', '.json'}:
        return False
    try:
        raw = _load_mapping(path)
    except Exception:
        return False
    return isinstance(raw, dict) and isinstance(raw.get('actions'), list)


def _resolve_enrichment_path(config: EnrichmentConfig, path: Path) -> Path:
    if path.is_absolute() or config.source is None:
        return path
    return config.source.parent / path
