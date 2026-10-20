"""Typed errors for docx_report.

Every user-facing failure carries a stable machine-readable ``code`` so callers
(and CI) can assert on the failure class instead of matching on message text.
Messages keep the original wording as much as possible to avoid breaking
existing scripts.

Exit-code contract used by the CLI:

* ``0``  success
* ``2``  a check ran and reported "not ready" (not an exception)
* ``3``  an operational error (anything derived from :class:`DocxReportError`)
* ``1``  unexpected error (bug); traceback is printed
"""

from __future__ import annotations

from typing import Any

EXIT_OK = 0
EXIT_CHECK_FAILED = 2
EXIT_ERROR = 3


class DocxReportError(Exception):
    """Base class for operational errors with a stable code."""

    code: str = "E_UNKNOWN"
    exit_code: int = EXIT_ERROR

    def __init__(
        self, message: str, *, hint: str | None = None, context: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.context = context or {}

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.hint:
            payload["hint"] = self.hint
        if self.context:
            payload["context"] = self.context
        return payload


class ConfigError(DocxReportError, ValueError):
    """Config file cannot be read, is the wrong type, or is incomplete."""

    code = "E_CONFIG"


class ConfigWrongTypeError(ConfigError):
    """A report config was passed where an enrich config was expected (or vice versa)."""

    code = "E_CONFIG_WRONG_TYPE"


class ConfigInvalidError(ConfigError):
    """Config is well-formed but violates the schema (missing/!type-mismatched keys)."""

    code = "E_CONFIG_INVALID"


class ConfigReadError(ConfigError):
    """Config file does not exist / is not parseable."""

    code = "E_CONFIG_READ"


class CourseProfileError(ConfigError):
    """Course report profile is missing or has the wrong ``kind``."""

    code = "E_COURSE_PROFILE"


class TemplateError(DocxReportError, RuntimeError):
    """The .docx template does not match the fixed layout assumptions."""

    code = "E_TEMPLATE_LAYOUT"


class AnchorNotFoundError(DocxReportError, RuntimeError):
    """An ``insert_image_after_anchor`` anchor is not present in the document."""

    code = "E_ANCHOR_MISSING"


class ResourceMissingError(DocxReportError, FileNotFoundError):
    """A referenced image / code file / artifact does not exist."""

    code = "E_RESOURCE_MISSING"


class EnrichmentActionError(DocxReportError, ValueError):
    """An enrichment action is unknown or missing required fields."""

    code = "E_ACTION_INVALID"


class DocumentError(DocxReportError, RuntimeError):
    """The target document cannot be opened or fails an invariant."""

    code = "E_DOCUMENT"


class ImageCountMismatchError(DocumentError):
    """``revise`` found a different number of images than ``expected_images``."""

    code = "E_IMAGE_COUNT_MISMATCH"


class PlaceholderRemainingError(DocxReportError):
    """PDF export refused because image placeholders were not replaced."""

    code = "E_PLACEHOLDER_REMAINING"


class PdfExportError(DocxReportError):
    """PDF export failed."""

    code = "E_PDF_EXPORT"


class OverwriteRefusedError(PdfExportError, FileExistsError):
    """An output file already exists and ``overwrite`` was not requested."""

    code = "E_OUTPUT_EXISTS"


class PlatformNotSupportedError(PdfExportError):
    """PDF export needs Microsoft Word, which this platform does not provide."""

    code = "E_PLATFORM_UNSUPPORTED"


class ExperimentNotReadyError(DocxReportError, RuntimeError):
    """Experiment completeness gate blocked the build."""

    code = "E_EXPERIMENT_NOT_READY"


__all__ = [
    "EXIT_OK",
    "EXIT_CHECK_FAILED",
    "EXIT_ERROR",
    "DocxReportError",
    "ConfigError",
    "ConfigWrongTypeError",
    "ConfigInvalidError",
    "ConfigReadError",
    "CourseProfileError",
    "TemplateError",
    "AnchorNotFoundError",
    "ResourceMissingError",
    "EnrichmentActionError",
    "DocumentError",
    "ImageCountMismatchError",
    "PlaceholderRemainingError",
    "PdfExportError",
    "OverwriteRefusedError",
    "PlatformNotSupportedError",
    "ExperimentNotReadyError",
]
