# Configuration schema

Two config kinds, both YAML (JSON and Python dicts are accepted as well).
Machine-readable schemas live in [`schema/`](../schema).

* **report config** — consumed by `build`, `revise`, `preview`
* **enrich config** — consumed by `enrich`, `validate`, `preview`

Passing one where the other is expected is a hard error
(`E_CONFIG_WRONG_TYPE`), never a silent guess.

> **Path rule.** Every relative path inside a config (`template`, `output`,
> `image`, `source`, `file`) is resolved against **the config file's own
> directory**. A config folder is therefore relocatable.

---

## 1. Report config

```yaml
name: experiment6
backend: ooxml-template
template: 模板.docx                 # required for build
output: out/实验6-报告.docx          # required
cover_title: 实验六
experiment_name: 基于铜死亡相关基因的肺腺癌 LUAD 亚型分析
expected_images: 0                  # optional, used by revise

assumptions:                        # only when the template differs from defaults
  required_table_count: 2
  cover_table_index: 0
  report_table_index: 1
  experiment_name_row: 3
  experiment_name_col: 1
  content_row: 5
  content_col: 0

styles:                             # overrides; normally inherited from a course profile
  section: {size: 28, bold: true}
  body: {size: 24, font: 宋体}

style_resolution:                   # donor-source rules
  comment_patterns: ['^【说明', '^【截图占位']
  section_patterns: ['^[一二三四五六七八九十]+、']
  body: [input_docx, template, fallback]
  caption: [fallback]

blocks:
  - kind: section
    text: 一、实验目的
  - kind: body
    text: 这里放正文。
  - kind: figure
    image: results/pca.png
    width_inches: 5.2
    text: 图 1 PCA 校正前后对比
  - kind: metrics
    source: results/metrics.json
    text: 运行结果：
    fields:
      - {key: test.accuracy, label: 测试集 Accuracy, fmt: ".4f"}
      - {key: test.labels,   label: 类别数}
  - kind: screenshot
    label: 运行截图
    hint: cell 3
    images: 1
    text: 图 3 Jupyter 单元运行结果
```

### Requirements

| Field | Rule |
|---|---|
| `output` | required, non-empty |
| `blocks` | required, non-empty list |
| `template` | required for `build` |
| `expected_images` | used by `revise`; a mismatch aborts the run |

### Blocks

| kind | Rendered as | Fields |
|---|---|---|
| `section` | heading paragraph | `text` |
| `subheading` | smaller bold heading | `text` |
| `body` | normal paragraph | `text` |
| `caption` | centred, 10.5 pt (style role `caption`) | `text` |
| `figure` | image + caption in a borderless 2-row table | `image`, `width_inches` (default 5.2), `text` |
| `figure_group` | 1–2 images on one row, one merged caption row | `items: [{image, text, width_inches}]` |
| `screenshot` | red 16:10 **placeholder image(s)**, replaced by hand | `label`, `hint`, `images` (1–2), `ratio`, `text` |
| `metrics` | one sentence built from a JSON file | `source`, `fields: [{key, label, fmt}]`, `text` |
| `placeholder` | legacy text placeholder | `text` |

Rules enforced by the renderer:

* a figure group holds **at most 2** images; high-density plots (correlation
  matrices, SHAP, multi-confusion-matrix) must stay on their own
* every figure table is followed by an invisible 1-twip paragraph, otherwise
  Word merges adjacent tables
* `metrics.fields[].key` uses dotted paths (`test.accuracy`); a missing key
  renders `数据缺失` instead of failing the build
* `screenshot` and `figure`/`figure_group` are different things: screenshots
  are *for the human to replace*, figures are *generated artifacts*

### Donor-style resolution

Styles are extracted from the template rather than invented:

```yaml
style_resolution:
  cover_title: [template, fallback]
  experiment_name: [input_docx, template, fallback]
  section: [input_docx, template, fallback]
  subheading: [input_docx, template, fallback]
  body: [input_docx, template, fallback]
  placeholder: [fallback]
  caption: [fallback]
```

Each list is a source priority. `require_<role>_source: true` turns a fallback
into a visible `doctor` error instead of a silent style change. Use
`<role>_include_patterns` / `<role>_exclude_patterns` to stop a paragraph that
*looks* like a body paragraph from being used as a style donor.

### Course report profile

A course profile holds the shared style for one course, so per-experiment
configs stay small. The loader looks upward from the config directory (up to 6
levels) for a file containing `kind: course-report-profile`, or you can point at
one explicitly:

```yaml
course_profile: ../课程报告范式.yml
```

Precedence: **built-in defaults < course profile < this config**.

```yaml
kind: course-report-profile
styles:
  section: {size: 30, bold: true}
  body: {size: 24, font: 宋体}
spacing:
  text_line: 360
  caption_line: 240
```

A file without `kind: course-report-profile` is silently ignored; an explicitly
referenced but missing/invalid profile raises `E_COURSE_PROFILE`.

---

## 2. Enrich config

```yaml
name: experiment8-finalize
output: out/实验8-完整版.docx      # optional; defaults to overwriting the input
actions:
  - action: add_page_break
  - action: append_heading
    text: 实验运行实录
    level: 1
  - action: append_paragraph
    text: 以下为实际运行时捕获的终端输出。
  - action: append_code_from_file
    file: data/A_matrix.txt
    head_lines: 8
    tab_columns: 8
  - action: append_image
    image: output/soft_threshold.png
    width_inches: 5.5
  - action: insert_image_after_anchor
    anchor: 二、实验原理
    image: output/fig1_flow.png
    caption: 图 2-1 算法流程图
    width_inches: 5.2
```

### Actions

| action | Required fields | Effect |
|---|---|---|
| `add_page_break` | — | page break at the end |
| `append_heading` | `text`, `level` | heading appended at the end |
| `append_paragraph` | `text` | paragraph appended at the end |
| `append_code_lines` | `lines` | monospace block appended |
| `append_code_from_file` | `file` (+ `head_lines`, `tab_columns`) | first N lines of a file, tabs truncated |
| `append_image` | `image` (+ `width_inches`) | image appended at the end |
| `insert_image_after_anchor` | `anchor`, `image` (+ `caption`) | image inserted right after the paragraph containing `anchor` |

Notes:

* `anchor` is matched against **body-level paragraphs**. Headings inside a table
  cell are not found — append the heading first, then anchor on it.
* `required: false` in an action's extras turns a missing file into a warning in
  `validate` instead of an error.
* Auto-numbering of captions is out of scope; write the number in `caption`.

---

## 3. Validation rules

| Check | Command |
|---|---|
| config readable, correct kind, required fields present | `doctor`, `preview` |
| template has the assumed tables and rows | `doctor`, `inspect-template`, `validate` |
| referenced images/code files exist | `doctor`, `validate` |
| anchors exist in the target document | `doctor`, `validate` |
| output opens with python-docx | `validate` |
| figure tables, placeholders, page break, leftovers | `verify` |
| notebooks executed, images not duplicated | `nbcheck` |
| result images not missing/duplicated/stale | `artifact-check` |

---

## 4. Compatibility and error handling

* A report config passed to an enrich loader (or vice versa) → `E_CONFIG_WRONG_TYPE`
* Missing `output` / `blocks` / `actions` → `E_CONFIG_INVALID`
* Unreadable file, missing PyYAML, unsupported suffix → `E_CONFIG_READ`
* Template layout mismatch → `E_TEMPLATE_LAYOUT`
* Missing image/code/metrics file → `E_RESOURCE_MISSING`
* Anchor not found → `E_ANCHOR_MISSING`
* `revise` finds the wrong number of images → `E_IMAGE_COUNT_MISMATCH`
* PDF export with placeholders / on a non-Windows host → `E_PLACEHOLDER_REMAINING` / `E_PLATFORM_UNSUPPORTED`

Python dict configs (`report.py` exporting `REPORT_CONFIG = {...}`) are still
supported for backwards compatibility.
