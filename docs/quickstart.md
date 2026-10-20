# Quickstart

From zero to a built, verified report in five steps. No existing template? Step 1
shows how to make the minimal one.

---

## 0. Install

```bash
pip install docxreport
docx-report --version
```

---

## 1. Prepare a template

The builder assumes a **two-table** layout:

| Object | Default requirement |
|---|---|
| Table 0 | cover information table |
| Table 1 | report table |
| Table 1, row 3, col 1 | experiment name |
| Table 1, row 5, col 0 | content cell (everything is rendered here) |
| Body paragraph matching `实验一` | cover title, must keep its page break |

Create one with python-docx:

```python
from docx import Document
from docx.enum.text import WD_BREAK

doc = Document()
title = doc.add_paragraph("实验一")
title.runs[0].add_break(WD_BREAK.PAGE)  # page break inside the title paragraph

cover = doc.add_table(rows=1, cols=2)
cover.cell(0, 0).text = "课程名称"

report = doc.add_table(rows=6, cols=2)
report.cell(3, 0).text = "实验名称"
report.cell(5, 0).paragraphs[0].add_run("一、实验目的")  # style donor lives here

doc.save("template.docx")
```

Then confirm:

```bash
docx-report inspect-template template.docx
```

If your template differs, override with `assumptions:` in the config (see
[config-schema](config-schema.md)). Never guess — always run `inspect-template`
first.

---

## 2. Write a report config

`docs/exp1/report.yml`:

```yaml
name: exp1
template: ../../template.docx
output: out/exp1.docx
cover_title: 实验一
experiment_name: 细胞类型注释与差异表达

blocks:
  - kind: section
    text: 一、实验目的
  - kind: body
    text: 掌握单细胞数据的质控、聚类与注释流程。
  - kind: section
    text: 二、实验结果
  - kind: figure
    image: results/umap.png
    text: 图 1 UMAP 聚类结果
  - kind: metrics
    source: results/metrics.json
    text: 关键指标：
    fields:
      - {key: qc.cells_after, label: 质控后细胞数}
      - {key: cluster.silhouette, label: 轮廓系数, fmt: ".3f"}
  - kind: screenshot
    label: 运行截图
    hint: cell 5
    text: 图 2 聚类代码运行结果
```

All relative paths resolve against `docs/exp1/`, not your shell's cwd.

---

## 3. Triage before building

```bash
docx-report doctor docs/exp1/report.yml
```

Typical output:

```
OK: doctor summary for report config 'exp1'
[OK] config: loaded report config: exp1
[OK] blocks: 6 blocks loaded
[OK] figures: 1 figure blocks, all image files exist
[OK] template-layout: template layout matches fixed-table assumptions (2 tables found)
[OK] style-source:section: section style source: template
[NOTE] no course report profile reached ...; using built-in defaults
[NEXT] python -m docx_report build docs/exp1/report.yml
```

Anything `[ERROR]` must be fixed first — `build` will fail on it anyway, just
later and with less context.

---

## 4. Build, verify

```bash
docx-report build docs/exp1/report.yml
docx-report verify docs/exp1/out/exp1.docx docs/exp1/report.yml
```

`verify` is the cheap review step. Check in its output:

* `figure_group_tables: N` equals the number of figure/screenshot blocks
* `placeholders: 0` — screenshots are placeholder **images**, not text
* `page break after cover: YES`
* `[template leftovers] none`
* `missing_images: 0`

---

## 5. Replace screenshots, then export

1. Open the docx in Word/WPS.
2. Right-click a red placeholder → *Change Picture* → pick your screenshot.
   The frame (size/position/wrap) is preserved, so nothing shifts.
3. Delete the placeholder caption text if you keep the printed caption.
4. Export:

```bash
docx-report pdf docs/exp1/out/exp1.docx
```

`pdf` refuses to run while `【图片占位` text remains — that is the guard that
stops you from shipping a draft by accident.

---

## Editing an existing report later

Do **not** rebuild. `revise` keeps the images you already pasted:

```bash
docx-report revise docs/exp1/report.yml docs/exp1/out/exp1.docx
```

Declare `expected_images: 3` in the config to make silent image loss a hard
error.

## Appending an appendix / extra figures

```yaml
# docs/exp1/finalize.yml
output: out/exp1-final.docx
actions:
  - action: add_page_break
  - action: append_heading
    text: 附录 A 运行实录
    level: 1
  - action: append_code_from_file
    file: results/run.log
    head_lines: 20
  - action: insert_image_after_anchor
    anchor: 附录 A 运行实录
    image: results/extra.png
    caption: 图 A-1 补充结果
```

```bash
docx-report enrich docs/exp1/finalize.yml docs/exp1/out/exp1.docx
```

---

## Working with notebooks

If your report must be backed by an executed notebook:

```bash
docx-report scaffold-notebook requirements.yml nb.py     # skeleton
# ... write your analysis ...
jupyter nbconvert --to notebook --execute --inplace nb.ipynb
docx-report nbcheck nb.ipynb --source-py nb.py
docx-report experiment-doctor requirements.yml
```

`build` refuses to run when a declared `experiment_requirements` gate is not
ready. That is intentional: a report must not claim results the notebook never
produced.
