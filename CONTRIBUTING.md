# Contributing

Thanks for taking the time to contribute. This project builds Word documents
from templates, so the bar is: **don't break layout guarantees, and don't
silently lose data**.

## Development setup

```bash
git clone https://github.com/wilianyichen/docxreport
cd docxreport
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
pytest -q
```

Optional: `pip install -e ".[lab,pdf]"` if you touch `src/labkit` or PDF export.

## Before you open a PR

```bash
ruff check .
ruff format --check .
pytest -q
python examples/run_all.py
```

CI runs the same commands on Ubuntu and Windows for Python 3.10–3.13.

## Project conventions

| Area | Rule |
|---|---|
| Docs | `README.md` and `docs/` in English; `SKILL.md` and `references/` stay Chinese (they drive an agent's behaviour, and translating them loses domain terms) |
| Paths | Any path in a config resolves against the config directory. Don't reintroduce cwd-relative resolution |
| Errors | Raise a subclass of `DocxReportError` with a stable `code`; never `raise RuntimeError("…")` for a user-facing failure |
| Binary assets | Never commit `.docx`, `.pdf`, `.ttf`/`.ttc`, screenshots. Generate fixtures in tests (CI enforces this) |
| Images | Figure/screenshot images must go through `figure` / `figure_group` / `screenshot` blocks, rendered as borderless 2-row tables with a separator paragraph afterwards |
| Styles | Never rely on python-docx defaults; extract `w:rFonts`/`w:sz`/`w:spacing` from a donor paragraph |
| Commits | Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`) |

## Adding a new block kind

1. Add the kind to `docs/config-schema.md` and `schema/report.schema.json`.
2. Implement rendering in `src/docx_report/ooxml_backend.py::render_blocks`.
3. If it can contain an image, go through `MediaContext.add_image` so
   relationships and content types stay consistent, and append
   `make_table_separator()` after any nested table you emit.
4. Add a test in `tests/test_ooxml_render.py` (unit) and, if the block produces
   visible output, extend `tests/test_e2e_smoke.py`.
5. Update `verify` if the block should appear in its structural summary.

## Adding a new CLI command

1. Implement the logic in a module under `src/docx_report/`.
2. Register it in `src/docx_report/cli.py` (`build_parser` + `_dispatch`).
3. `tests/test_cli.py::EXPECTED_COMMANDS` will fail until you add the name —
   that is intentional: the command surface is a contract.
4. Document it in `docs/cli.md` and the table in `SKILL.md`/`README.md`.

## Changing the loader

`tests/test_schema_roundtrip.py` asserts that everything the JSON Schema accepts
also loads, so keep `schema/*.json` and `config_loader.py` in sync.

## Reporting bugs

Include:

* the command you ran (and its exit code),
* the relevant part of the config (**redact paths**),
* the output of `docx-report doctor <config>`,
* your OS and Python version.

If the problem is a broken `.docx`, a minimal reproduction (config + generated
fixture template from `docx_report.testing`) is worth more than the full report.

## Security

See [SECURITY.md](SECURITY.md). Do not open a public issue for vulnerabilities.

## Licence

By contributing you agree that your contribution is licensed under
Apache-2.0 (see [LICENSE](LICENSE)).
