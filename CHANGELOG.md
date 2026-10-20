# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-10-20

First open-source-ready release. The previous state was a personal skill with no
packaging, tests, licence or CI.

### Added

- `pyproject.toml` (distribution `docxreport`, import name `docx_report`), extras
  `lab`, `pdf`, `dev`; console script `docx-report`.
- Typed error hierarchy in `docx_report.errors` with stable codes
  (`E_CONFIG_INVALID`, `E_TEMPLATE_LAYOUT`, `E_ANCHOR_MISSING`,
  `E_RESOURCE_MISSING`, `E_IMAGE_COUNT_MISMATCH`, `E_PLACEHOLDER_REMAINING`,
  `E_PLATFORM_UNSUPPORTED`, …) plus an exit-code contract (0/2/3/1).
- `--json` output for `doctor`, `validate`, `verify`, `inspect-template`,
  `nbcheck`, `experiment-doctor`, `artifact-check`.
- `--version` on the CLI, sourced from `docx_report.__version__`.
- `docx_report.testing.build_minimal_template()` so downstream projects can
  generate the fixture template instead of copying a course document.
- JSON Schemas for both config kinds (`schema/report.schema.json`,
  `schema/enrich.schema.json`) and a round-trip test that keeps schema and loader
  in agreement.
- `examples/` with four runnable pipelines and `examples/run_all.py`.
- pytest suite (107 tests, 63% line coverage baseline) with generated fixtures —
  no committed `.docx`, fonts or screenshots.
- CI matrix (Ubuntu + Windows × Python 3.10–3.13), packaging job, and a guard job
  that fails if a document or font binary is committed.
- Apache-2.0 licence, `NOTICE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, issue templates, pre-commit config, release workflow.
- `docs/` (English): quickstart, CLI reference, config schema, compatibility.

### Changed

- **Relative paths no longer depend on the process cwd.** Outputs resolve against
  the config file's directory. Inputs (`template`, `image`, `source`, `file`) are
  searched in `paths_base` → config dir → cwd → config ancestors (≤5 levels), so
  existing `6/figures/x.png`-style configs keep working; `paths_base` pins the
  base explicitly when needed.
- Library moved from `lib/` to `src/` (src layout); `scripts/skill_entry.py` is now
  a thin shim over `docx_report.cli` instead of a 220-line duplicate.
- `scripts/preview_config.py` and `scripts/inspect_docx_template.py` are
  deprecated shims that print a warning and delegate to the CLI.
- `doctor`'s "next command" hint is derived at runtime (console script → repo
  shim → `python -m docx_report`) instead of hardcoding one machine's path.
- `verify` locates the content cell from the config's `assumptions` when a config
  is supplied, falling back to the 实验目的/实验原理 keyword heuristic.

### Fixed

- `update_cover_title` duplicated the old cover title when the template's page
  break run also carried text (`实验一` + `实验七` in one paragraph). Page-break
  runs are now rebuilt as `w:rPr` + `w:br` only.
- `_load_mapping` leaked `FileNotFoundError` instead of raising `E_CONFIG_READ`.
- Placeholder images no longer depend on Windows fonts: candidates cover
  Linux/macOS, `DOCX_REPORT_PLACEHOLDER_FONT` overrides them, and a missing CJK
  font degrades to Pillow's default instead of crashing.
- PDF export raises `E_PLATFORM_UNSUPPORTED` on non-Windows hosts or when
  `pywin32` is absent, instead of a bare `ModuleNotFoundError`.
- Module docstrings sat after `from __future__ import annotations`, which made
  them plain string expressions (and broke import ordering).
- `doctor` reported only the **first** missing resource in an enrich config and
  silently skipped every later action: `ok = ok and _check_resource_exists(...)`
  short-circuits once `ok` is `False`, and the function that appends the check is
  never called. Each action now runs its check and combines the result after
  (`tests/test_doctor.py::test_every_missing_action_is_reported_not_just_the_first`).
- A missing image whose parent directory does not exist now says so and lists the
  directories that *are* there, instead of a bare `file missing` that reads like
  the asset was never produced. Renamed figure folders are the most common cause
  of config drift in practice; the listing is printed once per directory rather
  than once per broken action.

### Removed

- Hardcoded personal paths, student identifiers and the private course-template
  path from `SKILL.md` and all `references/`.
- The `lib/` directory (superseded by `src/`).

## [0.2.0] - 2026-09-18

Internal skill release: figure-group tables, image placeholders, OOXML
screenshot-safe revision, course report profiles, experiment-completeness gate.

## [0.1.0] - 2026-08

Initial local scripts: template filling and screenshot-preserving revision.
