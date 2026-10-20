# CLI reference

```
docx-report [--version] COMMAND ...
```

Every command accepts `--help`. Check commands accept `--json` and return
exit code `2` when they find problems.

| Exit code | Meaning |
|---|---|
| 0 | success / check passed |
| 2 | a check ran and found problems (findings printed) |
| 3 | operational error (`E_…` code printed to stderr) |
| 1 | unexpected error (bug) |

---

## `doctor <config> [input.docx] [--json]`

Readiness triage. Decides whether the file is a report or an enrich config, then
checks: blocks present, caption/placeholder ratio, figure images exist, course
profile applied, output directory writable, template layout, donor style sources,
anchor existence (with `input.docx`), and experiment requirements if declared.

Prints `[NEXT] <command>` — copy it.

```bash
docx-report doctor docs/exp6/report.yml
docx-report doctor docs/exp8/finalize.yml out/exp8-v1.docx
```

## `build <config> [--output PATH]`

Renders a new report from `template` + `blocks`. Refuses to run when the config
declares `experiment_requirements` and the experiment gate is not `READY`
(`E_EXPERIMENT_NOT_READY`).

```bash
docx-report build docs/exp6/report.yml
docx-report build docs/exp6/report.yml --output out/draft.docx
```

## `revise <config> <input.docx> [--output PATH]`

Updates an existing report **without losing pasted screenshots**. Works on
`word/document.xml`: image paragraphs are extracted first, blocks are rebuilt,
images are re-inserted in order. If `expected_images` is declared and the count
differs, the run aborts (`E_IMAGE_COUNT_MISMATCH`).

```bash
docx-report revise docs/exp6/report.yml out/exp6-v1.docx
```

## `enrich <config> <input.docx> [--output PATH]`

Applies an ordered `actions` list to an existing document: append
headings/paragraphs/code/images, insert images after an anchor, add page breaks.

```bash
docx-report enrich docs/exp8/finalize.yml out/exp8-v1.docx
```

## `validate <config> <docx> [--json]`

Structural validation: template assumptions (report configs), resource existence,
anchor presence (enrich configs), openability with python-docx, placeholder count.

```bash
docx-report validate docs/exp6/report.yml out/exp6.docx
```

## `verify <docx> [config] [--json]`

Token-cheap structural summary — use it instead of reading the report back:

* paragraph and Chinese-character counts
* content-cell paragraph count, image counts (inside/outside the cell)
* section headings with their detected formatting
* `figure_group_tables`, 2-row table count, images inside tables
* placeholder vs caption counts
* cover page break present?
* template leftover phrases (`结合实验指导书`, `【说明`, …)
* package media file count
* with a config: figure blocks and missing images

```bash
docx-report verify out/exp6.docx docs/exp6/report.yml
```

## `preview <config> [--show-patterns] [--show-screenshots] [--json]`

Normalises a config and prints what the loader understood. Use it first when a
build behaves differently than expected.

## `inspect-template <template.docx> [--json]`

Checks the fixed-table assumptions (≥2 tables, report table rows, content cell).
Run it after any template change.

## `scaffold <out.yml> --profile <course-profile> --experiment N [--tasks 6]`

Generates a report config skeleton, including Chinese section numbering and
placeholder blocks for N assignments.

```bash
docx-report scaffold docs/exp9/report.yml --profile 课程报告范式.yml --experiment 9 --tasks 5
```

## `scaffold-notebook <requirements.yml> <out.py>`

Generates a Jupytext percent notebook skeleton from an experiment requirements
file (sections, executed-cell structure, `n_jobs=1` note).

## `nbcheck <notebook.ipynb> [--max-images 2] [--source-py nb.py] [--json]`

Notebook gate without dumping the JSON:

* unexecuted non-empty code cells → block
* error outputs → block
* more images than `--max-images` in one cell → warning
* duplicate embedded images (same bytes) → warning
* non-monotonic execution counts → warning
* with `--source-py`: per-cell drift between the `.py` truth source and `.ipynb`

Exit code `2` when blocked.

## `experiment-doctor <requirements.yml> [--json]`

Checks the interpreter (absolute path, version), required imports, notebook
kernel consistency, `metrics.json` freshness and per-item mandatory/advanced
status. Returns `BLOCKED` instead of silently falling back to another
environment.

## `artifact-check <root> [--config report.yml] [--metrics metrics.json] [--notebook nb.ipynb] [--json]`

Scans result images for: unreferenced files, missing referenced files, identical
bytes under different names, and files older than the notebook/metrics.

## `pdf <docx> [--output PDF] [--allow-placeholders] [--overwrite]`

Exports through Microsoft Word COM (Windows + `pywin32`).

* refuses while `【图片占位` text remains (`E_PLACEHOLDER_REMAINING`)
* refuses to overwrite an existing PDF without `--overwrite`
* on non-Windows hosts raises `E_PLATFORM_UNSUPPORTED` (not an ImportError)

```bash
docx-report pdf out/exp6.docx
docx-report pdf out/exp6-draft.docx --allow-placeholders
```
