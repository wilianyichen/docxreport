"""Documentation contract: no drift, no personal paths, no dangling links."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on the 3.10 CI job
    import tomli as tomllib

from docx_report import __version__
from docx_report.cli import build_parser

ROOT = Path(__file__).resolve().parents[1]

DOC_FILES = sorted(
    [ROOT / "README.md", ROOT / "SKILL.md", *ROOT.glob("docs/*.md"), *ROOT.glob("references/*.md")]
)

COMMAND_RE = re.compile(
    r"^[ \t]*(?:\$[ \t]+)?(?:docx-report|skill_entry\.py|python -m docx_report)[ \t]+([a-z][a-z-]*)",
    re.M,
)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

# Personal identifiers / machine-specific roots that must never be committed.
FORBIDDEN_PATTERNS = [
    r"C:/Users/[A-Za-z]",
    r"C:\\\\Users\\\\",
    "/mnt/disk",
    "wuxiaoran",
    "吴笑然",
    r"20\d{8}",  # student id
]


def _commands() -> set[str]:
    parser = build_parser()
    action = next(a for a in parser._actions if getattr(a, "choices", None) and "doctor" in a.choices)
    return set(action.choices)


def _code_segments(text: str) -> list[str]:
    """Fenced blocks plus inline code spans — prose is not a command example."""
    segments = re.findall(r"```.*?```", text, re.S)
    segments += re.findall(r"`[^`\n]+`", text)
    return segments


def test_every_documented_command_exists():
    known = _commands()
    unknown: list[str] = []
    for path in DOC_FILES:
        for segment in _code_segments(path.read_text(encoding="utf-8")):
            for match in COMMAND_RE.finditer(segment):
                token = match.group(1)
                if token in known:
                    continue
                if token in {"version"}:
                    continue
                unknown.append(f"{path.name}: {token}")
    assert unknown == [], f"documented commands that do not exist: {unknown}"


def test_all_docs_mention_every_command_at_least_once_everywhere():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in DOC_FILES)
    missing = [cmd for cmd in sorted(_commands()) if f" {cmd}" not in combined]
    assert missing == []


def test_markdown_links_resolve():
    broken: list[str] = []
    for path in DOC_FILES:
        for target in LINK_RE.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            relative = target.split("#", 1)[0]
            if not relative:
                continue
            candidate = (path.parent / relative).resolve()
            if not candidate.exists():
                broken.append(f"{path.name} -> {target}")
    assert broken == [], f"broken links: {broken}"


@pytest.mark.parametrize("pattern", FORBIDDEN_PATTERNS)
def test_no_personal_or_machine_paths(pattern: str):
    hits: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in {".md", ".py", ".yml", ".yaml", ".json", ".toml"}:
            continue
        if any(part in {".git", "__pycache__", "out"} for part in path.parts):
            continue
        if path.name == Path(__file__).name:
            continue  # this file necessarily contains the patterns it forbids
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(pattern, text):
            hits.append(str(path.relative_to(ROOT)))
    assert hits == [], f"{pattern} found in {hits}"


def test_skill_frontmatter_is_valid():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    frontmatter = yaml.safe_load(text.split("---", 2)[1])
    assert frontmatter["name"] == "docx-report-skill"
    assert frontmatter["description"]
    assert frontmatter["version"] == __version__


def test_version_is_consistent_everywhere():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["version"] == __version__

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"[{__version__}]" in changelog


def test_referenced_docs_exist():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    referenced = re.findall(r"`((?:docs|references)/[^`]+\.md)`", text)
    assert referenced, "SKILL.md should index its reference documents"
    missing = [name for name in referenced if not (ROOT / name).exists()]
    assert missing == []


def test_docs_directory_has_the_promised_files():
    for name in (
        "config-schema.md",
        "cli.md",
        "quickstart.md",
        "compatibility.md",
    ):
        assert (ROOT / "docs" / name).exists(), name


WORKFLOW_FILES = sorted((ROOT / ".github" / "workflows").glob("*.yml"))


def test_workflow_files_exist():
    names = {path.name for path in WORKFLOW_FILES}
    assert {"ci.yml", "release.yml"} <= names


@pytest.mark.parametrize("workflow", WORKFLOW_FILES, ids=lambda p: p.name)
def test_workflow_yaml_is_loadable(workflow: Path):
    """A malformed workflow makes every run fail in 0s, before any test runs.

    `name: guard: no committed docx/fonts` shipped once and did exactly that:
    the unquoted ": " parses as a mapping, GitHub cannot load the file, and
    ruff/pytest/local runs all stay green because nothing reads the YAML.
    """
    data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "jobs" in data, f"{workflow.name} has no jobs"
    for job_name, job in data["jobs"].items():
        assert "runs-on" in job, f"{workflow.name}: job {job_name} has no runs-on"
        assert "steps" in job, f"{workflow.name}: job {job_name} has no steps"


@pytest.mark.parametrize("workflow", WORKFLOW_FILES, ids=lambda p: p.name)
def test_workflow_triggers_reference_an_existing_branch(workflow: Path):
    """README badges and pyproject urls point at `main`; the workflow must too."""
    data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    branches = ((data.get(True) or data.get("on") or {}).get("push") or {}).get("branches")
    if branches:
        assert "main" in branches, f"{workflow.name} pushes on {branches}, docs say main"
