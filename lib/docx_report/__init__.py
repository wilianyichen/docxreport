"""Project-local DOCX report helpers for course experiment reports."""

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

__all__ = [
    "build_report",
    "doctor_config",
    "enrich_report",
    "generate_screenshot_plan",
    "preview_config",
    "revise_report",
    "summarize_report_patterns",
    "validate_report",
]
