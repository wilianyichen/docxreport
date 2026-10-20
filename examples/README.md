# Examples

Four minimal pipelines. All assets (template, figures, metrics, log) are
generated at runtime — nothing binary is committed.

```bash
python examples/run_all.py     # runs all four, writes into examples/out/
```

| Directory | Shows |
|---|---|
| `01-build/` | chapter/body/figure/metrics/screenshot blocks → a report |
| `02-revise/` | updating an existing report while keeping its images |
| `03-enrich/` | appendix + code excerpt + anchored figure insertion |
| `04-course-profile/` | one style profile shared by a whole course |

Inspect a single example:

```bash
python examples/run_all.py            # generates examples/out/ and template.docx first
docx-report doctor  examples/01-build/report.yml
docx-report build   examples/01-build/report.yml
docx-report verify  examples/01-build/out/report.docx examples/01-build/report.yml
```

Paths in these configs are relative to each config file, e.g.
`template: ../template.docx` resolves to `examples/template.docx`.
