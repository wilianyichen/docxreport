"""Shared fixtures. No committed binary assets: every input is generated."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:  # belt and braces next to pyproject pythonpath
    sys.path.insert(0, str(SRC))

sys.path.insert(0, str(ROOT / "tests" / "fixtures"))

from build_fixture_template import build as build_template  # noqa: E402


@pytest.fixture(scope="session")
def template_docx(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A minimal two-table template shared by the whole session."""
    target = tmp_path_factory.mktemp("templates") / "template.docx"
    return build_template(target)


@pytest.fixture()
def png(tmp_path: Path):
    """Factory writing a tiny PNG and returning its path."""

    def _make(name: str = "fig.png", size: tuple[int, int] = (80, 50)) -> Path:
        from PIL import Image

        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", size, (30, 90, 160)).save(path, format="PNG")
        return path

    return _make


@pytest.fixture()
def write_text(tmp_path: Path):
    """Factory writing a UTF-8 text file (yaml/json/etc.) and returning its path."""

    def _write(name: str, content: str) -> Path:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    return _write
