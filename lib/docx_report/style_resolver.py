from __future__ import annotations

from dataclasses import dataclass, field
import re
import xml.etree.ElementTree as ET

from .models import ParagraphStyle, ReportConfig, ReportStyleProfile

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W = f'{{{W_NS}}}'


def w_tag(name: str) -> str:
    return f'{W}{name}'


@dataclass(slots=True)
class ResolvedStyleProfile:
    styles: ReportStyleProfile
    sources: dict[str, str] = field(default_factory=dict)
    unresolved_required: list[str] = field(default_factory=list)
    skipped_comment_count: int = 0


@dataclass(slots=True)
class ParagraphSample:
    kind: str
    style: ParagraphStyle
    text: str


def resolve_style_profile(
    config: ReportConfig,
    *,
    template_cell: ET.Element | None = None,
    input_cell: ET.Element | None = None,
    template_title_paragraph: ET.Element | None = None,
    input_title_paragraph: ET.Element | None = None,
    template_experiment_name_cell: ET.Element | None = None,
    input_experiment_name_cell: ET.Element | None = None,
) -> ResolvedStyleProfile:
    fallback = config.styles
    rules = config.style_resolution
    samples_by_source = {
        'template': _extract_samples(template_cell, rules) if template_cell is not None else {},
        'input_docx': _extract_samples(input_cell, rules) if input_cell is not None else {},
    }
    title_samples = {
        'template': _extract_single_paragraph_style(template_title_paragraph) if _matches_slot_controls('cover_title', template_title_paragraph, rules) else None,
        'input_docx': _extract_single_paragraph_style(input_title_paragraph) if _matches_slot_controls('cover_title', input_title_paragraph, rules) else None,
    }
    experiment_name_samples = {
        'template': _extract_first_cell_paragraph_style(
            template_experiment_name_cell,
            rules.experiment_name_patterns,
            rules.experiment_name_include_patterns,
            rules.experiment_name_exclude_patterns,
        ),
        'input_docx': _extract_first_cell_paragraph_style(
            input_experiment_name_cell,
            rules.experiment_name_patterns,
            rules.experiment_name_include_patterns,
            rules.experiment_name_exclude_patterns,
        ),
    }
    skipped_comment_count = sum(_count_comment_paragraphs(cell, rules.comment_patterns) for cell in (template_cell, input_cell) if cell is not None)

    resolved = ReportStyleProfile(
        cover_title=_resolve_slot_style('cover_title', rules.cover_title_prefer, title_samples, fallback.cover_title),
        experiment_name=_resolve_slot_style('experiment_name', rules.experiment_name_prefer, experiment_name_samples, fallback.experiment_name),
        section=_resolve_style('section', rules.section_prefer, samples_by_source, fallback.section),
        subheading=_resolve_style('subheading', rules.subheading_prefer, samples_by_source, fallback.subheading),
        body=_resolve_style('body', rules.body_prefer, samples_by_source, fallback.body),
        placeholder=_resolve_style('placeholder', rules.placeholder_prefer, samples_by_source, fallback.placeholder),
        caption=_resolve_style('caption', rules.caption_prefer, samples_by_source, fallback.caption),
    )
    sources = {
        'cover_title': _resolve_slot_source_name(rules.cover_title_prefer, title_samples),
        'experiment_name': _resolve_slot_source_name(rules.experiment_name_prefer, experiment_name_samples),
        'section': _resolve_source_name('section', rules.section_prefer, samples_by_source),
        'subheading': _resolve_source_name('subheading', rules.subheading_prefer, samples_by_source),
        'body': _resolve_source_name('body', rules.body_prefer, samples_by_source),
        'placeholder': _resolve_source_name('placeholder', rules.placeholder_prefer, samples_by_source),
        'caption': _resolve_source_name('caption', rules.caption_prefer, samples_by_source),
    }
    unresolved_required = _collect_unresolved_required(rules, sources)
    return ResolvedStyleProfile(styles=resolved, sources=sources, unresolved_required=unresolved_required, skipped_comment_count=skipped_comment_count)


def _extract_samples(cell: ET.Element, rules) -> dict[str, ParagraphSample]:
    samples: dict[str, ParagraphSample] = {}
    for paragraph in cell.findall(w_tag('p')):
        text = ''.join((node.text or '') for node in paragraph.findall('.//' + w_tag('t'))).strip()
        if not text:
            continue
        kind = _classify_paragraph(text, rules)
        if kind == 'comment':
            continue
        if not _matches_donor_controls(kind, text, rules):
            continue
        if kind not in samples:
            samples[kind] = ParagraphSample(kind=kind, style=_extract_paragraph_style(paragraph), text=text)
    return samples


def _count_comment_paragraphs(cell: ET.Element, comment_patterns: list[str]) -> int:
    count = 0
    for paragraph in cell.findall(w_tag('p')):
        text = ''.join((node.text or '') for node in paragraph.findall('.//' + w_tag('t'))).strip()
        if text and any(re.search(pattern, text) for pattern in comment_patterns):
            count += 1
    return count


def _classify_paragraph(text: str, rules) -> str:
    if any(re.search(pattern, text) for pattern in rules.comment_patterns):
        return 'comment'
    if any(re.search(pattern, text) for pattern in rules.placeholder_patterns):
        return 'placeholder'
    if any(re.search(pattern, text) for pattern in rules.section_patterns):
        return 'section'
    if any(re.search(pattern, text) for pattern in rules.subheading_patterns):
        return 'subheading'
    if rules.body_patterns and any(re.search(pattern, text) for pattern in rules.body_patterns):
        return 'body'
    return 'body'


def _extract_single_paragraph_style(paragraph: ET.Element | None) -> ParagraphStyle | None:
    if paragraph is None:
        return None
    return _extract_paragraph_style(paragraph)


def _extract_first_cell_paragraph_style(cell: ET.Element | None, allowed_patterns: list[str], include_patterns: list[str], exclude_patterns: list[str]) -> ParagraphStyle | None:
    if cell is None:
        return None
    for paragraph in cell.findall(w_tag('p')):
        text = ''.join((node.text or '') for node in paragraph.findall('.//' + w_tag('t'))).strip()
        if not text:
            continue
        if allowed_patterns and not any(re.search(pattern, text) for pattern in allowed_patterns):
            continue
        if include_patterns and not any(re.search(pattern, text) for pattern in include_patterns):
            continue
        if exclude_patterns and any(re.search(pattern, text) for pattern in exclude_patterns):
            continue
        return _extract_paragraph_style(paragraph)
    return None


def _extract_paragraph_style(paragraph: ET.Element) -> ParagraphStyle:
    style = ParagraphStyle()
    p_pr = paragraph.find(w_tag('pPr'))
    if p_pr is not None:
        spacing = p_pr.find(w_tag('spacing'))
        if spacing is not None:
            after = spacing.get(w_tag('after'))
            line = spacing.get(w_tag('line'))
            line_rule = spacing.get(w_tag('lineRule'))
            if after is not None:
                style.spacing_after = int(after)
            if line is not None:
                style.spacing_line = int(line)
            if line_rule is not None:
                style.spacing_line_rule = line_rule
        jc = p_pr.find(w_tag('jc'))
        if jc is not None:
            style.align = jc.get(w_tag('val'))

    run = paragraph.find(w_tag('r'))
    if run is None:
        return style
    r_pr = run.find(w_tag('rPr'))
    if r_pr is None:
        return style

    fonts = r_pr.find(w_tag('rFonts'))
    if fonts is not None:
        style.ascii_font = fonts.get(w_tag('ascii')) or style.ascii_font
        style.hansi_font = fonts.get(w_tag('hAnsi')) or style.hansi_font
        style.east_asia_font = fonts.get(w_tag('eastAsia')) or style.east_asia_font
        style.cs_font = fonts.get(w_tag('cs')) or style.cs_font

    style.bold = r_pr.find(w_tag('b')) is not None or r_pr.find(w_tag('bCs')) is not None

    color = r_pr.find(w_tag('color'))
    if color is not None:
        style.color = color.get(w_tag('val'))

    size = r_pr.find(w_tag('sz'))
    if size is not None and size.get(w_tag('val')):
        style.size = int(size.get(w_tag('val')))

    return style


def _resolve_style(kind: str, prefer: list[str], samples_by_source: dict[str, dict[str, ParagraphSample]], fallback: ParagraphStyle) -> ParagraphStyle:
    for source in prefer:
        if source == 'fallback':
            return fallback
        sample = samples_by_source.get(source, {}).get(kind)
        if sample is not None:
            return sample.style
    return fallback


def _resolve_source_name(kind: str, prefer: list[str], samples_by_source: dict[str, dict[str, ParagraphSample]]) -> str:
    for source in prefer:
        if source == 'fallback':
            return 'fallback'
        if samples_by_source.get(source, {}).get(kind) is not None:
            return source
    return 'fallback'


def _resolve_slot_style(kind: str, prefer: list[str], samples_by_source: dict[str, ParagraphStyle | None], fallback: ParagraphStyle) -> ParagraphStyle:
    for source in prefer:
        if source == 'fallback':
            return fallback
        sample = samples_by_source.get(source)
        if sample is not None:
            return sample
    return fallback


def _resolve_slot_source_name(prefer: list[str], samples_by_source: dict[str, ParagraphStyle | None]) -> str:
    for source in prefer:
        if source == 'fallback':
            return 'fallback'
        if samples_by_source.get(source) is not None:
            return source
    return 'fallback'


def _matches_donor_controls(kind: str, text: str, rules) -> bool:
    include_patterns = getattr(rules, f'{kind}_include_patterns', [])
    exclude_patterns = getattr(rules, f'{kind}_exclude_patterns', [])
    if include_patterns and not any(re.search(pattern, text) for pattern in include_patterns):
        return False
    if exclude_patterns and any(re.search(pattern, text) for pattern in exclude_patterns):
        return False
    return True


def _matches_slot_controls(kind: str, paragraph: ET.Element | None, rules) -> bool:
    if paragraph is None:
        return False
    text = ''.join((node.text or '') for node in paragraph.findall('.//' + w_tag('t'))).strip()
    include_patterns = getattr(rules, f'{kind}_include_patterns', [])
    exclude_patterns = getattr(rules, f'{kind}_exclude_patterns', [])
    if include_patterns and not any(re.search(pattern, text) for pattern in include_patterns):
        return False
    if exclude_patterns and any(re.search(pattern, text) for pattern in exclude_patterns):
        return False
    return True


def _collect_unresolved_required(rules, sources: dict[str, str]) -> list[str]:
    unresolved: list[str] = []
    mapping = {
        'cover_title': rules.require_cover_title_source,
        'experiment_name': rules.require_experiment_name_source,
        'section': rules.require_section_source,
        'subheading': rules.require_subheading_source,
        'body': rules.require_body_source,
        'placeholder': rules.require_placeholder_source,
    }
    for kind, required in mapping.items():
        if required and sources.get(kind) == 'fallback':
            unresolved.append(kind)
    return unresolved
