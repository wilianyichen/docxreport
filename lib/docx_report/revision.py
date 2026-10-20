from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from .models import ReportConfig
from .ooxml_backend import (
    extract_image_paragraphs,
    find_cover_title_paragraph,
    read_document_xml,
    register_namespaces,
    render_blocks,
    replace_cell_text,
    resolve_template_slots,
    update_cover_title,
    w_tag,
    write_document_xml,
)
from .style_resolver import resolve_style_profile


def revise_existing_report(config: ReportConfig, input_docx: Path, output_path: Path | None = None) -> Path:
    document_xml, infos, other_files = read_document_xml(input_docx)
    register_namespaces(document_xml)
    root = ET.fromstring(document_xml)
    body = root.find(w_tag('body'))
    if body is None:
        raise RuntimeError(f'{input_docx.name}: document body not found')
    _, report_name_cell, content_cell = resolve_template_slots(body, config)
    image_paragraphs = extract_image_paragraphs(content_cell)
    if config.expected_images is not None and len(image_paragraphs) != config.expected_images:
        raise RuntimeError(f'{input_docx.name}: expected {config.expected_images} images, found {len(image_paragraphs)}')
    title_paragraph = find_cover_title_paragraph(body)
    resolved = resolve_style_profile(
        config,
        input_cell=content_cell,
        input_title_paragraph=title_paragraph,
        input_experiment_name_cell=report_name_cell,
    )
    replace_cell_text(report_name_cell, config.experiment_name, resolved.styles.experiment_name)
    render_blocks(content_cell, config, image_paragraphs=image_paragraphs, styles=resolved.styles)
    update_cover_title(body, config.cover_title, resolved.styles.cover_title)
    final_output = output_path or config.output
    write_document_xml(final_output, infos, other_files, ET.tostring(root, encoding='utf-8', xml_declaration=True))
    return final_output
