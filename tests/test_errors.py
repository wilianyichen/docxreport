"""Error contract: stable codes, hints, and backwards-compatible base classes."""

from __future__ import annotations

import pytest

from docx_report.errors import (
    EXIT_ERROR,
    AnchorNotFoundError,
    ConfigInvalidError,
    DocxReportError,
    ImageCountMismatchError,
    OverwriteRefusedError,
    PlaceholderRemainingError,
    PlatformNotSupportedError,
    ResourceMissingError,
    TemplateError,
)


def test_code_and_exit_code_are_stable():
    exc = ConfigInvalidError("boom", hint="fix it", context={"path": "x.yml"})
    assert exc.code == "E_CONFIG_INVALID"
    assert exc.exit_code == EXIT_ERROR
    assert str(exc) == "boom"
    assert exc.as_dict() == {
        "code": "E_CONFIG_INVALID",
        "message": "boom",
        "hint": "fix it",
        "context": {"path": "x.yml"},
    }


def test_subclasses_keep_builtin_base_behaviour():
    # Existing user scripts catch ValueError / FileNotFoundError / RuntimeError.
    assert isinstance(ConfigInvalidError("x"), ValueError)
    assert isinstance(ResourceMissingError("x"), FileNotFoundError)
    assert isinstance(TemplateError("x"), RuntimeError)
    assert isinstance(OverwriteRefusedError("x"), FileExistsError)


def test_specific_codes():
    assert AnchorNotFoundError("x").code == "E_ANCHOR_MISSING"
    assert ImageCountMismatchError("x").code == "E_IMAGE_COUNT_MISMATCH"
    assert PlaceholderRemainingError("x").code == "E_PLACEHOLDER_REMAINING"
    assert PlatformNotSupportedError("x").code == "E_PLATFORM_UNSUPPORTED"


def test_every_error_is_a_docxreport_error():
    for cls in (
        ConfigInvalidError,
        ResourceMissingError,
        TemplateError,
        AnchorNotFoundError,
        PlaceholderRemainingError,
    ):
        assert issubclass(cls, DocxReportError)


def test_keyword_only_extras_do_not_leak_into_message():
    exc = DocxReportError("msg", hint="h")
    assert "h" not in str(exc)
    with pytest.raises(TypeError):
        DocxReportError("msg", unexpected=True)
