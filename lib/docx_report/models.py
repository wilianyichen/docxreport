from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ReportBlock:
    kind: str
    text: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TemplateLayoutAssumptions:
    required_table_count: int = 2
    cover_table_index: int = 0
    report_table_index: int = 1
    experiment_name_row: int = 3
    experiment_name_col: int = 1
    content_row: int = 5
    content_col: int = 0


@dataclass(slots=True)
class ParagraphStyle:
    ascii_font: str = 'Times New Roman'
    hansi_font: str = 'Times New Roman'
    east_asia_font: str = '宋体'
    cs_font: str = 'Times New Roman'
    size: int = 24
    bold: bool = False
    color: str | None = None
    align: str | None = None
    spacing_after: int = 120
    spacing_line: int = 360
    spacing_line_rule: str = 'auto'


@dataclass(slots=True)
class ReportStyleProfile:
    cover_title: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(size=32, bold=True, align='center'))
    experiment_name: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(size=24, align='center'))
    section: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(size=28, bold=True))
    subheading: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(size=24, bold=True))
    body: ParagraphStyle = field(default_factory=ParagraphStyle)
    placeholder: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(size=24, color='0000FF'))
    caption: ParagraphStyle = field(default_factory=lambda: ParagraphStyle(size=21, align='center'))


@dataclass(slots=True)
class StyleResolutionRules:
    comment_patterns: list[str] = field(default_factory=lambda: [r'^【说明', r'^【截图占位', r'^\[说明', r'^注：'])
    cover_title_patterns: list[str] = field(default_factory=lambda: [r'^实验(?:[0-9]+|[一二三四五六七八九十]+)$'])
    experiment_name_patterns: list[str] = field(default_factory=list)
    section_patterns: list[str] = field(default_factory=lambda: [r'^[一二三四五六七八九十]+、'])
    subheading_patterns: list[str] = field(default_factory=lambda: [r'^\d+(?:\.\d+)?[\.、：: ]'])
    placeholder_patterns: list[str] = field(default_factory=lambda: [r'^【'])
    body_patterns: list[str] = field(default_factory=list)
    cover_title_include_patterns: list[str] = field(default_factory=list)
    cover_title_exclude_patterns: list[str] = field(default_factory=list)
    experiment_name_include_patterns: list[str] = field(default_factory=list)
    experiment_name_exclude_patterns: list[str] = field(default_factory=list)
    section_include_patterns: list[str] = field(default_factory=list)
    section_exclude_patterns: list[str] = field(default_factory=list)
    subheading_include_patterns: list[str] = field(default_factory=list)
    subheading_exclude_patterns: list[str] = field(default_factory=list)
    body_include_patterns: list[str] = field(default_factory=list)
    body_exclude_patterns: list[str] = field(default_factory=list)
    placeholder_include_patterns: list[str] = field(default_factory=list)
    placeholder_exclude_patterns: list[str] = field(default_factory=list)
    cover_title_prefer: list[str] = field(default_factory=lambda: ['template', 'fallback'])
    experiment_name_prefer: list[str] = field(default_factory=lambda: ['input_docx', 'template', 'fallback'])
    section_prefer: list[str] = field(default_factory=lambda: ['input_docx', 'template', 'fallback'])
    subheading_prefer: list[str] = field(default_factory=lambda: ['input_docx', 'template', 'fallback'])
    body_prefer: list[str] = field(default_factory=lambda: ['input_docx', 'template', 'fallback'])
    placeholder_prefer: list[str] = field(default_factory=lambda: ['fallback'])
    caption_prefer: list[str] = field(default_factory=lambda: ['fallback'])
    require_cover_title_source: bool = False
    require_experiment_name_source: bool = False
    require_section_source: bool = False
    require_subheading_source: bool = False
    require_body_source: bool = False
    require_placeholder_source: bool = False


@dataclass(slots=True)
class ReportConfig:
    name: str
    backend: str
    template: Path | None
    output: Path
    cover_title: str
    experiment_name: str
    blocks: list[ReportBlock]
    expected_images: int | None = None
    assumptions: TemplateLayoutAssumptions = field(default_factory=TemplateLayoutAssumptions)
    styles: ReportStyleProfile = field(default_factory=ReportStyleProfile)
    style_resolution: StyleResolutionRules = field(default_factory=StyleResolutionRules)
    source: Path | None = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EnrichmentAction:
    action: str
    anchor: str | None = None
    image: Path | None = None
    caption: str = ""
    width_inches: float | None = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EnrichmentConfig:
    name: str
    output: Path | None
    actions: list[EnrichmentAction]
    source: Path | None = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CourseReportPattern:
    name: str
    mode: str
    common_steps: list[str] = field(default_factory=list)
    specific_steps: list[str] = field(default_factory=list)
    required_artifacts: list[str] = field(default_factory=list)
    validation_focus: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ValidationResult:
    ok: bool
    messages: list[str] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        prefix = "OK" if self.ok else "ERROR"
        if not self.messages:
            return [f"{prefix}: no details"]
        return [f"{prefix}: {message}" for message in self.messages]


@dataclass(slots=True)
class DoctorCheck:
    status: str
    label: str
    message: str


@dataclass(slots=True)
class DoctorResult:
    ok: bool
    config_type: str
    config_name: str
    checks: list[DoctorCheck] = field(default_factory=list)
    suggested_command: str | None = None
    notes: list[str] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        prefix = "OK" if self.ok else "ERROR"
        lines = [f"{prefix}: doctor summary for {self.config_type} config '{self.config_name}'"]
        for check in self.checks:
            lines.append(f"[{check.status.upper()}] {check.label}: {check.message}")
        for note in self.notes:
            lines.append(f"[NOTE] {note}")
        if self.suggested_command:
            lines.append(f"[NEXT] {self.suggested_command}")
        return lines
