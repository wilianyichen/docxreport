"""Project-local DOCX report helpers for course experiment reports."""

from __future__ import annotations

__version__ = "0.3.0"

from .api import (
    build_report,
    doctor_config,
    enrich_report,
    generate_screenshot_plan,
    preview_config,
    revise_report,
    summarize_report_patterns,
    validate_report,
)
from .errors import DocxReportError

__all__ = [
    "__version__",
    "build_report",
    "doctor_config",
    "enrich_report",
    "generate_screenshot_plan",
    "preview_config",
    "revise_report",
    "summarize_report_patterns",
    "validate_report",
    "DocxReportError",
]
