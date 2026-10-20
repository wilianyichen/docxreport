"""CLI contract: command surface, exit codes, JSON output, version consistency."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on the 3.10 CI job
    import tomli as tomllib

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
    """Every subcommand must carry a description in the top-level --help table.

    Do not assert "the name and its description share a line". argparse moves the
    description onto its own line whenever the command name does not fit the
    *name column*, whose width is capped by max_help_position=24 and is
    independent of the terminal width. Which commands wrap changed between
    Python releases (3.10 wrapped `inspect-template`, 3.11/3.12/3.13 wrapped
    `experiment-doctor`), so a per-line assertion failed on part of the matrix
    while the product was fine. Scanning the block between one command name and
    the next is layout-independent.
    """
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--help"])
    lines = capsys.readouterr().out.splitlines()

    first_line: dict[str, int] = {}
    order: list[str] = []
    for index, line in enumerate(lines):
        tokens = line.strip().split(maxsplit=1)
        name = tokens[0] if tokens else ""
        if name in EXPECTED_COMMANDS and name not in first_line:
            first_line[name] = index
            order.append(name)

    missing = sorted(EXPECTED_COMMANDS - set(order))
    assert not missing, f"missing from --help: {missing}"

    for position, name in enumerate(order):
        start = first_line[name]
        end = first_line[order[position + 1]] if position + 1 < len(order) else len(lines)
        block = " ".join(lines[start:end]).strip()
        description = block[len(name) :].strip()
        words = description.split()
        assert len(words) >= 3, f"{name} has no help text; block was {block!r}"


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
