# Compatibility matrix

What works where, and exactly how it fails when it does not.

## Environments

| Environment | build / revise / enrich / validate / verify | `screenshot` placeholders | `pdf` | `nbcheck` / `artifact-check` |
|---|---|---|---|---|
| Windows + Word | ✅ | ✅ | ✅ | ✅ |
| Windows, no Word | ✅ | ✅ | ❌ `E_PLATFORM_UNSUPPORTED` (pywin32 missing) | ✅ |
| Windows + WPS only | ✅ | ✅ | ❌ (no COM `Word.Application`) | ✅ |
| Linux | ✅ | ✅ if a CJK font exists | ❌ `E_PLATFORM_UNSUPPORTED` | ✅ |
| macOS | ✅ | ✅ (PingFang) | ❌ `E_PLATFORM_UNSUPPORTED` | ✅ |

"✅" means covered by the test suite on that OS in CI (Linux, Windows) and by
the same code path on macOS (not in CI yet).

## Python versions

`requires-python = ">=3.10"`. CI runs 3.10 / 3.11 / 3.12 / 3.13 on Ubuntu and
Windows.

## Dependencies

| Extra | Packages | Needed for |
|---|---|---|
| *(core)* | `python-docx`, `PyYAML`, `Pillow` | everything except the items below |
| `lab` | `numpy`, `pandas`, `scikit-learn`, `matplotlib` | `src/labkit` helpers inside notebooks |
| `pdf` | `pywin32` (Windows only) | `docx-report pdf` |

No optional dependency is imported at package import time, so a missing extra
only breaks the one command that needs it.

## Fonts

Placeholder images draw Chinese text with the first font that exists among:

```
Linux   /usr/share/fonts/.../NotoSansCJK-Regular.ttc, wqy-zenhei, wqy-microhei, uming
macOS   /System/Library/Fonts/PingFang.ttc, Hiragino Sans GB.ttc
Windows C:\Windows\Fonts\msyh.ttc, simhei.ttf, simsun.ttc
```

Override explicitly when the host has a non-standard layout:

```bash
export DOCX_REPORT_PLACEHOLDER_FONT="/path/to/NotoSansCJK-Regular.ttc"
```

If no CJK font is found, Pillow's built-in bitmap font is used: English stays
readable, Chinese renders as boxes. The build still succeeds — this is a
cosmetic degradation, not an error.

## Word / WPS behaviour assumptions

| Assumption | Why it matters |
|---|---|
| Adjacent nested tables get merged | Hence the invisible 1-twip separator after every figure table |
| "Change Picture" keeps frame size/position | Hence image placeholders instead of text placeholders |
| `w:br w:type="page"` inside the title paragraph survives a text rewrite | Hence `update_cover_title` re-emits the break run (sanitized: no stale text) |
| Word reports "file may be corrupted" if `mc:Ignorable` prefixes are dropped | Hence root namespace declarations are restored after serialisation |

## Failure modes

| Symptom | Error / check | Fix |
|---|---|---|
| `expected at least 2 tables, found 1` | `E_TEMPLATE_LAYOUT` | run `inspect-template`; update `assumptions:` |
| `anchor not found: 二、实验原理` | `E_ANCHOR_MISSING` | anchor must be a body-level paragraph; `append_heading` first |
| `image not found: …` | `E_RESOURCE_MISSING` | path searched in `paths_base` → config dir → cwd → config ancestors; set `paths_base` if your layout differs |
| `… missing: … - its parent directory 'X' does not exist; directories available: …` | `E_RESOURCE_MISSING` | config drift: the folder was renamed after the config was written. Update the path; the message lists the directories that do exist |
| `expected N images, found M` | `E_IMAGE_COUNT_MISMATCH` | update `expected_images`, or the images really were lost |
| `looks like an enrich config` | `E_CONFIG_WRONG_TYPE` | wrong command for this file |
| `report still contains image placeholders` | `E_PLACEHOLDER_REMAINING` | replace placeholders, or `--allow-placeholders` for a draft |
| `pywin32 is not installed` | `E_PLATFORM_UNSUPPORTED` | `pip install "docxreport[pdf]"` |
| New paragraphs use Calibri/等线 | `doctor` shows `style-source:*: fallback` | provide a donor paragraph, or declare `[fallback]` style in the course profile |
| 28 figure tables, Word shows 13 | `verify` `figure_group_tables` < expected | separator paragraph missing — file a bug |

## Real-world regression set

Six configs from the course project this skill was extracted from are run through
`doctor` on every release. They are not shipped (they reference the author's own
figures), but they are the only non-synthetic check that config portability
still holds, because they were written before `paths_base` existed and use
paths relative to the *course root* while sitting two levels deep.

| Config | Result | Notes |
|---|---|---|
| `1/docs/report_configs_diabetes.yml` | ✅ ready | 79 blocks, 12/13 gate items complete, 1 legitimately optional |
| `1/docs/enrich_configs_diabetes.yml` | ❌ blocked | 6 of 7 `append_image` paths point at figure folders renamed after the config was written |
| `2/docs/report_configs_experiment2.yml` | ✅ ready | 107 blocks, 13 placeholders ↔ 13 captions, 17 figures |
| `3/docs/report_configs_experiment3.yml` | ❌ blocked | notebook gate: 13/20 code cells executed, 1 error output, 2 declared screenshot cells unexecuted |
| `4/docs/report_configs_experiment4.yml` | ✅ ready | 58 blocks, all 4 figures resolved |
| `6/docs/report_configs_experiment6.yml` | ✅ ready | 55 blocks, all 9 figures resolved |

Both ❌ rows are **content** problems in the source project, not tool defects —
`doctor` is doing exactly its job by refusing to call them ready. They are kept
in the set precisely because a green result there would mean the gate stopped
gating.

## Known limitations

1. **Fixed-table layout is the default model.** Free-form documents (contracts,
   papers) are out of scope; the tool assumes one content cell.
2. **Anchors are body-level only.** TOC-like structures inside a cell are not
   searched.
3. **No tracked changes / comments.** `revise` rewrites content, it does not
   produce a redline document.
4. **PDF is Word-only.** No LibreOffice headless path yet (contributions
   welcome).
5. **Caption numbering is manual.** The tool will not renumber 图 1 → 图 2 when
   you insert a figure in the middle.
6. **Chinese-first agent docs.** `SKILL.md` and `references/` are Chinese by
   design (they drive an agent's behaviour); `README`/`docs` are English.
