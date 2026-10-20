"""CLI contract: command surface, exit codes, JSON output, version consistency."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import tomllib

from docx_report import __version__
from docx_report.cli import build_parser, main

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_COMMANDS = {
    "doctor",
    "build",
    "revise",
    "enrich",
    "validate",
    "verify",
    "preview",
    "inspect-template",
    "scaffold",
    "nbcheck",
    "scaffold-notebook",
    "experiment-doctor",
    "artifact-check",
    "pdf",
}


def test_all_documented_commands_exist():
    parser = build_parser()
    action = next(a for a in parser._actions if getattr(a, "choices", None) and "doctor" in a.choices)
    assert set(action.choices) == EXPECTED_COMMANDS


def test_every_command_has_a_help_string(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--help"])
    out = capsys.readouterr().out
    for name in EXPECTED_COMMANDS:
        line = next((ln for ln in out.splitlines() if ln.strip().startswith(name)), None)
        assert line is not None, f"{name} missing from --help"
        # a command is documented only if its help text has real words after the name
        assert len(line.strip().split()) > 1, f"{name} has no help text"


def test_version_flag_matches_package(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_version_matches_pyproject():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == __version__


def test_missing_config_exits_with_operational_error(tmp_path, capsys):
    code = main(["doctor", str(tmp_path / "nope.yml")])
    assert code == 3
    captured = capsys.readouterr()
    assert "error [E_CONFIG_READ]" in captured.err


def test_check_failure_exits_with_two(tmp_path, write_text, png):
    """inspect-template on a non-docx exits 2 (a check ran and failed)."""
    junk = write_text("not-a-docx.docx", "hello")
    code = main(["inspect-template", str(junk)])
    assert code == 2


def test_doctor_json_output(tmp_path, template_docx):
    config = tmp_path / "config.yml"
    config.write_text(
        f"""
template: {template_docx.name}
output: out/r.docx
blocks:
  - kind: body
    text: x
""",
        encoding="utf-8",
    )
    import shutil

    shutil.copy(template_docx, tmp_path / template_docx.name)

    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(["doctor", str(config), "--json"])
    payload = json.loads(buffer.getvalue())
    assert code in (0, 2)
    assert set(payload) >= {"ok", "code", "lines"}
    assert payload["code"] in {"OK", "NOT_READY"}


def test_deprecated_scripts_still_work(tmp_path):
    import subprocess
    import sys

    script = ROOT / "scripts" / "preview_config.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"], capture_output=True, text=True, encoding="utf-8"
    )
    assert result.returncode == 0
    assert "preview" in result.stdout.lower()
