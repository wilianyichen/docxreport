# Config Schema

当前本地报告 skill 区分两类配置：

- `report.yml`：用于 `build / revise / patterns / screenshot-plan / donor-style resolution`
- `enrich.yml`（以及 `wgcna.yml` / `artifacts.yml` / `figures.yml` / `finalize.yml` 这类 actions 配置）：用于 `enrich / validate / preview`

## 1. report config

```yaml
name: experiment6
backend: ooxml-template
template: /mnt/disk2/wuxiaoran/course/shuwa/模板.docx
output: /mnt/disk2/wuxiaoran/course/shuwa/6/实验6-报告-骨架版.docx
cover_title: 实验六
experiment_name: 基于铜死亡相关基因的肺腺癌 LUAD 亚型分析
expected_images: 0
assumptions:
  required_table_count: 2
  cover_table_index: 0
  report_table_index: 1
  experiment_name_row: 3
  experiment_name_col: 1
  content_row: 5
  content_col: 0
styles:
  section:
    size: 28
    bold: true
  body:
    size: 24
style_resolution:
  comment_patterns:
    - '^【说明'
    - '^【截图占位'
  cover_title_patterns:
    - '^实验(?:[一二三四五六七八九十0-9]+)$'
  section_patterns:
    - '^[一二三四五六七八九十]+、'
  subheading_patterns:
    - '^\d+(?:\.\d+)?[\.、：: ]'
  placeholder_patterns:
    - '^【'
  cover_title:
    - template
    - fallback
  experiment_name:
    - input_docx
    - template
    - fallback
  section:
    - input_docx
    - template
    - fallback
  subheading:
    - input_docx
    - template
    - fallback
  body:
    - input_docx
    - template
    - fallback
  placeholder:
    - fallback
  section_include_patterns: []
  section_exclude_patterns: []
  body_include_patterns: []
  body_exclude_patterns: []
  require_section_source: false
  require_body_source: false
blocks:
  - kind: section
    text: 一、实验目的
  - kind: body
    text: 这里放正文
  - kind: placeholder
    text: 【截图占位：PCA 校正前后图】
    source: output/PCA_before.png + output/PCA_after.png
    target: 3. 作业3：数据整合与批次校正
    mode: placeholder-only
```

要求：

- 必须有 `output`
- 必须有非空 `blocks`
- `template` 对 `build` 必填
- `expected_images` 主要用于 `revise`
- `blocks` 当前至少支持 `section / body / subheading / placeholder / image`

## 2. donor-style resolution 规则

### 2.1 donor 分类规则

- `comment_patterns`：匹配模板注释/说明文字；这些段落不会被当作 donor
- `cover_title_patterns` / `experiment_name_patterns` / `section_patterns` / `subheading_patterns` / `placeholder_patterns` / `body_patterns`：定义各类样式样本的识别规则

### 2.2 donor 来源优先级

- `cover_title` / `experiment_name` / `section` / `subheading` / `body` / `placeholder`
- 每项是一个来源优先级列表，例如：

```yaml
body:
  - input_docx
  - template
  - fallback
```

含义：优先从输入报告正文里找 donor；没有再看模板；还没有才回退到 `styles.body`。

### 2.3 donor include / exclude

每类 donor 都可显式控制：

- `<kind>_include_patterns`
- `<kind>_exclude_patterns`

例如：

```yaml
body_include_patterns:
  - '^结果解读'
body_exclude_patterns:
  - '^【'
```

这用于解决“看起来像 body，但其实不该当 donor”的场景。

### 2.4 required donor 语义

每类 donor 还可以声明必须来自真实 source：

- `require_cover_title_source`
- `require_experiment_name_source`
- `require_section_source`
- `require_subheading_source`
- `require_body_source`
- `require_placeholder_source`

若设为 `true`，但最终只落到 `fallback`，则：

- `preview` 的 `resolved_style_sources.unresolved_required` 会列出来
- `doctor` 会把对应 donor source 标成 error，而不是静默回退

## 3. enrich config

```yaml
name: experiment8-finalize
output: /mnt/disk2/wuxiaoran/course/shuwa/8/实验8-报告-完整版-含截图.docx
actions:
  - action: add_page_break
  - action: append_heading
    text: 实验运行实录（真实终端输出与代码）
    level: 1
  - action: append_paragraph
    text: 以下为实验8在 Linux 服务器上实际运行时捕获的终端输出。
  - action: append_code_from_file
    file: /mnt/disk2/wuxiaoran/course/shuwa/8/data/input/A_matrix.txt
    head_lines: 8
    tab_columns: 8
  - action: append_image
    image: /mnt/disk2/wuxiaoran/course/shuwa/8/output/wgcna/soft_threshold.png
    width_inches: 5.5
  - action: insert_image_after_anchor
    anchor: 二、实验原理
    image: /mnt/disk2/wuxiaoran/course/shuwa/8/output/figures/fig1_polobag_flowchart.png
    caption: 图 2-1：PoLoBag（Polynomial Lasso Bagging）算法流程图
    width_inches: 5.2
```

要求：

- 必须有非空 `actions`
- `output` 可选；未提供时默认覆盖输入文档
- `insert_image_after_anchor` 需要 `anchor + image`
- `append_image` 需要 `image`
- `append_heading / append_paragraph / append_code_lines / append_code_from_file / add_page_break` 用于文末富化

## 4. experiment8 的分层 enrich 配置

experiment8 当前有两种组织方式：

- 分步链路：`wgcna.yml -> artifacts.yml -> figures.yml`
- 一步流：`finalize.yml`（`enrich.yml` 可视为同方向入口）

详见：`report_configs/experiment8/README.md`

## 5. doctor / preview 会显示什么

对于 `report.yml`：

- 配置是否能读取
- `blocks` 是否存在
- 输出目录是否存在/可创建
- `template` 是否存在且满足固定表格假设
- 若提供 `input_docx`，是否可打开，以及更适合 `build` 还是 `revise`
- donor style source（cover_title / experiment_name / section / subheading / body / placeholder）
- skipped comment donor 数量
- unresolved required donor 列表（若有）

对于 `enrich/actions` 配置：

- 配置是否能读取
- `actions` 是否存在
- 输出目录是否存在/可创建
- `append_image` / `insert_image_after_anchor` / `append_code_from_file` 依赖的资源是否存在
- 若提供 `input_docx`，anchor 是否真的在报告里存在
- 最后给出推荐下一条命令

## 6. 兼容/防错行为

- report 配置误传给 enrich loader → 明确报错：`looks like a report config`
- enrich 配置误传给 report loader → 明确报错：`looks like an enrich config`
- donor 找不到时默认可 fallback；若某类 donor 配了 `require_*_source: true`，则会在诊断层明确暴露
- 第一阶段仍兼容 Python dict 形式的 report config
