"""Placeholder image generation must work without a specific system font."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image

from docx_report import placeholder_image
from docx_report.placeholder_image import make_placeholder_image, resolve_font_candidates


def test_size_follows_16_10_ratio(tmp_path: Path):
    path = make_placeholder_image(tmp_path / "p.png", ["运行截图"], width_px=800)
    with Image.open(path) as image:
        assert image.size == (800, 500)
        assert image.format == "PNG"


def test_environment_variable_takes_precedence(monkeypatch, tmp_path: Path):
    monkeypatch.setenv(placeholder_image.FONT_ENV_VAR, str(tmp_path / "fake.ttf"))
    candidates = resolve_font_candidates()
    assert candidates[0] == str(tmp_path / "fake.ttf")


def test_explicit_font_argument_wins(monkeypatch, tmp_path: Path):
    monkeypatch.setenv(placeholder_image.FONT_ENV_VAR, "env.ttf")
    candidates = resolve_font_candidates("/custom/font.ttc")
    assert candidates[0] == "/custom/font.ttc"
    assert candidates[1] == "env.ttf"


def test_missing_font_falls_back_instead_of_crashing(monkeypatch, tmp_path: Path):
    # Simulate a host with none of the known CJK fonts installed.
    monkeypatch.setattr(placeholder_image, "FONT_CANDIDATES", ())
    monkeypatch.delenv(placeholder_image.FONT_ENV_VAR, raising=False)
    path = make_placeholder_image(tmp_path / "p.png", ["SCREENSHOT", "line 2"], width_px=400)
    with Image.open(path) as image:
        assert image.size == (400, 250)


def test_broken_font_file_is_skipped(monkeypatch, tmp_path: Path):
    bogus = tmp_path / "broken.ttf"
    bogus.write_bytes(b"not a font")
    monkeypatch.setattr(placeholder_image, "FONT_CANDIDATES", (str(bogus),))
    monkeypatch.delenv(placeholder_image.FONT_ENV_VAR, raising=False)
    # Must not raise; falls back to Pillow's default bitmap font.
    assert make_placeholder_image(tmp_path / "p.png", ["x"], width_px=200).exists()


def test_no_font_env_leak_between_calls(monkeypatch):
    monkeypatch.delenv(placeholder_image.FONT_ENV_VAR, raising=False)
    assert placeholder_image.FONT_ENV_VAR not in os.environ
