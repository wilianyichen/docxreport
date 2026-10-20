# docxreport

[![CI](https://github.com/REPLACE-ME/docxreport/actions/workflows/ci.yml/badge.svg)](https://github.com/REPLACE-ME/docxreport/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

**Template-driven experiment-report builder for Word documents.**

Fill a fixed `.docx` template from a YAML config, revise existing reports **without losing inserted screenshots**, append figures and appendices at anchors, and verify the result structurally instead of opening Word and counting paragraphs.

Built for lab/course reports where the layout is fixed, the numbers must be traceable to a `metrics.json`, and the screenshots are pasted by hand.

---

## Why this exists

Most "generate a Word report" scripts break the moment a human edits the document:

| Problem | What usually happens | What this does |
|---|---|---|
| A screenshot was pasted by hand | Regenerating the file deletes it | `revise` edits `word/document.xml` and re-inserts every image paragraph |
| Fonts drift | New paragraphs come out in Calibri/等线 | Styles are **extracted from a donor paragraph in your template**, never assumed |
| Two adjacent nested tables | Word silently merges them (28 tables become 13) | A 1-twip vanish separator is emitted between figure tables |
| Numbers copied by hand | Report says 0.91, notebook produced 0.9103 | `metrics` blocks read `metrics.json` at build time |
| "Is the report done?" | Open Word, scroll, guess | `verify` prints a structural summary (token-cheap, scriptable) |

---

## Install

```bash
pip install docxreport              # core: build / revise / enrich / validate / verify
pip install "docxreport[lab]"       # + numpy/pandas/scikit-learn/matplotlib helpers (labkit)
pip install "docxreport[pdf]"       # + pywin32, for PDF export on Windows
```

Requires Python 3.10+. Only `python-docx`, `PyYAML` and `Pillow` are mandatory.

From source:

```bash
git clone https://github.com/REPLACE-ME/docxreport
cd docxreport
pip install -e ".[dev]"
pytest
```

---

## Quickstart

```bash
mkdir my-report && cd my-report
cp /path/to/template.docx .
```

`report.yml`:

```yaml
name: exp1
template: template.docx
output: out/report.docx
cover_title: 实验一
experiment_name: 示例实验
blocks:
  - kind: section
    text: 一、实验目的
  - kind: body
    text: 掌握模板化报告流程。
  - kind: figure
    image: results/fig1.png
    text: 图 1 结果示例
  - kind: screenshot
    label: 运行截图
    hint: cell 3
    text: 图 2 Jupyter 单元运行结果
```

```bash
docx-report doctor  report.yml     # inspect config + template + resources, print next step
docx-report build   report.yml     # write out/report.docx
docx-report verify  out/report.docx report.yml
docx-report pdf     out/report.docx   # Windows + Microsoft Word only
```

`doctor` is the intended entry point: it tells you whether the config is a
report or an enrich config, whether the template still matches the assumed
table layout, which resources are missing, and which command to run next.

Screenshots are inserted as **red 16:10 placeholder images**. Replace them in
Word/WPS with *right-click → Change Picture*: the frame, size and position are
preserved, so the layout never shifts. Text placeholders are deliberately not
used.

---

## Commands

| Command | Purpose |
|---|---|
| `doctor` | Readiness triage across config, template, resources, style sources; prints the next command |
| `build` | Render a new report from a template + `report.yml` |
| `revise` | Update an existing report while preserving every inserted image |
| `enrich` | Apply an ordered `actions` list: append headings/paragraphs/code/images, insert images after anchors |
| `validate` | Structural check of a document against its config |
| `verify` | Print a structural summary (sections, figure tables, placeholders, page break, leftovers) |
| `preview` | Dump a normalised view of a config without writing anything |
| `inspect-template` | Check the template against the fixed two-table assumptions |
| `scaffold` | Generate a report config skeleton from a course profile |
| `scaffold-notebook` | Generate a Jupytext percent notebook skeleton from `requirements.yml` |
| `nbcheck` | Check an executed notebook: unexecuted cells, error outputs, image density, `.py`/`.ipynb` drift |
| `experiment-doctor` | Experiment completeness gate: interpreter, imports, notebook, metrics, mandatory items |
| `artifact-check` | Detect missing / duplicated / stale result images |
| `pdf` | Export DOCX → PDF through Microsoft Word (Windows only) |

Full reference: [`docs/cli.md`](docs/cli.md).

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success, or the check passed |
| `2` | A check ran and reported "not ready" (findings printed, nothing raised) |
| `3` | Operational error — config missing, template mismatch, missing resource, … |
| `1` | Unexpected error (bug) |

Operational errors carry a stable code (`E_CONFIG_INVALID`, `E_TEMPLATE_LAYOUT`,
`E_ANCHOR_MISSING`, `E_RESOURCE_MISSING`, `E_PLACEHOLDER_REMAINING`,
`E_PLATFORM_UNSUPPORTED`, …). Assert on `error.code`, not on message text.

---

## Configuration

Two kinds of config, deliberately separate so a wrong entry point fails loudly
instead of half-working:

* **report config** (`report.yml`) → `build`, `revise`, `preview`
* **enrich config** (`finalize.yml`, actions-based) → `enrich`, `validate`, `preview`

Relative paths inside a config: **outputs** resolve against the config file's own
directory, so a config folder can be moved without rewriting anything.
**Inputs** (`template`, `image`, `source`, `file`) additionally fall back to the
cwd and the config's ancestors (up to 5 levels) when the file is not next to the
config, which keeps legacy layouts working; pin the base explicitly with
`paths_base: ..` when needed.

### Block types

| kind | Purpose | Key fields |
|---|---|---|
| `section` | Section heading (一、二、三…) | `text` |
| `subheading` | Sub-heading | `text` |
| `body` | Body paragraph | `text` |
| `caption` | Figure caption, 10.5 pt centred | `text` |
| `figure` | Insert an image, caption below | `image`, `width_inches`, `text` |
| `figure_group` | 1–2 images in one borderless table, caption row underneath | `items: [{image, text}]` |
| `screenshot` | Red 16:10 placeholder image to replace by hand | `label`, `hint`, `images`, `text` |
| `metrics` | Render numbers from a JSON file into one sentence | `source`, `fields: [{key, label, fmt}]`, `text` |
| `placeholder` | Legacy text placeholder (kept for compatibility) | `text` |

### Enrichment actions

`add_page_break`, `append_heading`, `append_paragraph`, `append_code_lines`,
`append_code_from_file`, `append_image`, `insert_image_after_anchor`.

Schema details and examples: [`docs/config-schema.md`](docs/config-schema.md).
Machine-readable schemas: [`schema/`](schema).

---

## Design guarantees

1. **Styles come from the template, not from defaults.** A donor paragraph is
   located, and `w:rFonts` (ascii/hAnsi/eastAsia), `w:sz` and `w:spacing` are
   copied onto every new paragraph. python-docx defaults are never trusted.
2. **Images survive revision.** `revise` works on OOXML: it extracts image
   paragraphs, rebuilds the content blocks, then puts the images back in order.
   `expected_images` turns silent image loss into a hard error.
3. **`.docx` paths are never rewritten blindly.** python-docx splits text into
   runs, so string replacement happens at paragraph level.
4. **Every figure table is followed by a separator.** Otherwise Word merges
   adjacent nested tables and your 图 1–图 8 collapse into one table.
5. **`verify` counts XML, not visuals.** `python-docx` re-counts merged cells,
   which turns 10 placeholders into 40; `verify` walks `w:p` uniquely.

---

## Platform support

| Feature | Linux / macOS | Windows |
|---|---|---|
| build / revise / enrich / validate / verify / nbcheck / artifact-check | ✅ | ✅ |
| Placeholder images | ✅ (needs any CJK font for Chinese text; set `DOCX_REPORT_PLACEHOLDER_FONT`) | ✅ |
| `pdf` | ❌ raises `E_PLATFORM_UNSUPPORTED` | ✅ needs Microsoft Word + `pywin32` |

See [`docs/compatibility.md`](docs/compatibility.md) for the failure matrix.

---

## Known limitations

* The fixed-table assumption is hard-coded by default: 1 cover table + 1 report
  table, experiment name at row 4/col 2, content at row 6/col 1. Override via
  `assumptions:` or run `inspect-template` first.
* `insert_image_after_anchor` resolves anchors among **body-level paragraphs**;
  headings that live inside a table cell are not found. Append the heading with
  `append_heading` first, then anchor on it.
* PDF export drives Word through COM; there is no LibreOffice path yet.
* Placeholder replacement is a manual step by design — that is what keeps the
  layout stable.
* Documentation is Chinese-first (`SKILL.md`, `references/`); this README and
  `docs/` are English.

---

## Project layout

```
src/docx_report/        library + CLI (single source of truth)
src/labkit/             optional notebook helpers (seeds, metrics, figures)
scripts/skill_entry.py  stable entry point for agent/skill integrations
SKILL.md                agent-facing workflow and discipline (Chinese)
references/             deep-dive notes for the skill (Chinese)
docs/                   user documentation (English)
schema/                 JSON Schemas for the two config kinds
examples/               minimal runnable pipelines
tests/                  pytest suite; all fixtures generated, no binary assets
```

---

## Contributing

Issues and PRs welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md) and
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). For security reports, see
[`SECURITY.md`](SECURITY.md).

```bash
pip install -e ".[dev]"
pre-commit install
pytest -q
ruff check .
```

## License

Apache-2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

This repository ships **no** `.docx` templates, fonts or student reports; test
fixtures are generated from code so no third-party document is redistributed.
