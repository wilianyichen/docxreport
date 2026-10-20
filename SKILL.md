---
name: docx-report-skill
description: "模板驱动的实验报告 DOCX 工作流：模板填充、保图修订、锚点插图、附录富化、结构核验与 PDF 导出。适用于固定表格模板的课程/实验报告。"
version: "0.3.0"
keywords: [docx, report, 实验报告, 模板, 修订, 截图, 图表, enrich, ooxml]
metadata:
  skill_type: do
  consumes: [design_spec]
  produces: [manifest]
  capabilities: [docx-generation, docx-revision, template-filling, screenshot-planning, enrich-actions]
  model_tier: standard
  task_type: operation
  status: active
  license: Apache-2.0
---

# DOCX Report Skill

## Overview

把「固定模板的实验报告」做成可复现的流水线，而不是每次手工改 Word：

- 基于固定模板生成报告；
- 在**不丢已插截图**的前提下修订正文（OOXML 保图修订）；
- 按锚点插入结果图、追加附录/运行实录；
- 从 `metrics.json` 自动搬运数字，避免手抄错；
- 用 `verify` 输出结构摘要，替代「把整份 docx 读回上下文」。

不负责 PDF 抽取 / OCR —— 上游文本请先转成可消费文本再进本 skill。

## When to Use

- 用户要生成或修订实验报告 `.docx`；
- 用户要在已有报告里补图、补附录，但不能重排已有截图；
- 用户要核对「报告是否真的做完了」（Notebook 已执行、指标可追溯）；
- 用户要检查模板/配置是否还对得上（模板被改过、配置传错入口）。

不要用于：扫描 PDF 抽取、OCR、PDF 结构化解析、通用 Word 审阅与 tracked changes。

## 运行入口

只有一个入口，`scripts/skill_entry.py` 与安装后的 `docx-report` 命令等价：

```bash
docx-report <command> ...                       # pip install docxreport 之后
python scripts/skill_entry.py <command> ...     # 仓库内直接跑
python -m docx_report <command> ...             # 包已在 sys.path 时
```

14 个子命令：

| 命令 | 用途 |
|---|---|
| `doctor` | 就绪度检查 + 给出下一条该跑的命令（**默认第一步**） |
| `build` | 模板 + `report.yml` → 新报告 |
| `revise` | 保图修订已有报告 |
| `enrich` | 按 `actions` 顺序追加/锚点插图 |
| `validate` | 结构校验（模板假设、资源、锚点、可打开性） |
| `verify` | 结构摘要（节省 token 的交付核验） |
| `preview` | 归一化预览配置，判断入口是否正确 |
| `inspect-template` | 检查模板是否满足固定表格假设 |
| `scaffold` | 由课程范式生成 report config 骨架 |
| `scaffold-notebook` | 由 requirements 生成 Jupytext percent Notebook 骨架 |
| `nbcheck` | Notebook 门禁（未执行单元、报错、图片密度、`.py`/`.ipynb` 漂移） |
| `experiment-doctor` | 实验完整性门禁（解释器、依赖、metrics、mandatory 清单） |
| `artifact-check` | 结果图缺失/重复/过期检查 |
| `pdf` | Word COM 导出 PDF（Windows） |

退出码：`0` 通过 / `2` 检查未通过 / `3` 操作错误（带 `E_*` 错误码）/ `1` 未预期异常。
断言错误请用 `error.code`，不要匹配错误文案。

## Process

Step 1: 选模式（`doctor / build / revise / enrich / validate / verify / preview / inspect-template`）
  退出标准: 已确认输入是模板、现有报告、report config 还是 enrich config
  产出: 命令选择与输入文件清单

Step 1.5: 先跑 `doctor`（推荐）
  退出标准: 已确认配置类型、模板假设、资源存在性、样式 donor 来源、下一条命令
  产出: readiness 摘要 + next command

Step 2: 执行文档操作
  退出标准: 已完成模板填充、原位修订、文末富化、锚点插图或配置预览中的一种
  产出: 新的 `.docx` 或配置摘要

Step 3: 校验
  退出标准: 模板结构、占位符、图片数量、锚点、附图资源、可打开性均通过
  产出: `validate` / `verify` 摘要

Step 4: 交付
  退出标准: 已汇报文件路径、是分步链路还是一步 finalize、以及后续可继续的动作
  产出: 最小必要说明

## 块类型（blocks）

| kind | 用途 | 关键字段 |
|---|---|---|
| `section` | 节标题（一、实验目的…） | `text` |
| `subheading` | 作业小标题 | `text` |
| `body` | 正文 | `text` |
| `caption` | 图注（图片下方，10.5pt 居中） | `text` |
| `screenshot` | **运行截图占位**：红色 16:10 占位图片，本人「右键→更改图片」替换 | `text`=图注、`label`、`hint`、`images`(1–2) |
| `figure_group` | **结果图图组**：1–2 张图，渲染成「一行图 + 一行图注」无边框表格 | `items: [{image, text}]` |
| `figure` | **自动插图**：图片嵌入正文单元格，图注在下方 | `image`、`width_inches`（默认 5.2）、`text` |
| `metrics` | **自动搬运数字**：从 JSON 读键值渲染成一句话 | `source`、`fields: {key, label, fmt}`、`text` |
| `placeholder` | 旧文字占位（保留兼容；新报告用 `screenshot`） | `text` |

约定：

- **结果图**用 `figure` / `figure_group` 自动插入；**运行截图**用 `screenshot` 插红色占位图，人工替换。
- 所有图片一律「一行图 + 一行图注」无边框表格，一行最多 2 张；禁止浮动图。
- 相邻嵌套表会被 Word 合并，渲染器在每张图组表后自动补一个不可见分隔段落 —— 不要手工删掉它。
- 高密度图（相关系数矩阵、SHAP、多混淆矩阵）保持独立尺寸，不合并，否则缩到正文宽度后不可读。

外部工具截图（VSCode Data Wrangler / Excel / pandas-profiling）可作为**辅助**运行截图：占位行写清工具名即可，但它**不能**替代可执行代码单元与结果图，正文数字仍必须来自 `metrics.json`。

## 实验完整性门禁（先完成实验，再写报告）

- 单次 report config 可声明 `experiment_requirements: <requirements.yml>`；声明后正式 `build` 前强制检查。
- **禁止环境静默回退**：指定解释器不存在、Notebook kernel 不一致或必需包不可导入 → `BLOCKED`，不得自动改用 base 环境。
- 「代码存在」不等于「实验完成」：必须有本次完整执行输出、无错误、指标/图片产物、`metrics.json` 逐项状态。
- mandatory 出现 `MISSING / PARTIAL / BLOCKED / INCONSISTENT / STALE` 时报告不是 ready，`build` 必须拒绝。
- 选做项缺外部数据写 `OPTIONAL_NOT_DONE` 并写明原因；不得用内部测试集冒充外部验证。
- 报告声称的方法（GridSearchCV、StandardScaler、SMOTE、SHAP…）必须能在 Notebook 已执行单元中追溯。
- `metrics.json` 必须由 Notebook 本次运行自动写出，并记录 `sys.executable`、Python/关键包版本。
- **一个代码单元 = 一段自洽代码 + 它自己的全部输出 = 报告里的一张运行截图**；单元代码建议 ≤ 30 行，超过就拆。
- 同一作业的代码不得被图片隔断；同构低密度子图拼 2×2 / 1×3 母图并标注 (a)(b)(c)(d)。

常用命令：`nbcheck`、`experiment-doctor`、`artifact-check`、`scaffold-notebook`、`pdf`。

## 课程范式契约（Course Report Profile）

**优先级：skill 内置默认 < 课程范式 < 单次实验 config。**

- 课程范式是「一门课一份」的统一样式，该课程各实验目录共用；单次 config 只写本次特有内容。
- 身份标识：文件内必须有 `kind: course-report-profile`，否则被静默忽略。
- 查找：从 report config 所在目录逐级向上（≤6 层），先认约定文件名再浅扫 `*.yml`；也可写 `course_profile: <相对路径>`。
- `doctor` 应输出 `[OK] course-profile: ...`；只出现 `[NOTE] no course report profile reached` 说明没找到。
- 课程模板层次退化（节标题与正文同格式）时，在范式里把对应角色声明为 `[fallback]`，不要沿用模板 donor。

细节见 `references/course-profile.md`。

## 样式契约（不允许从零造样式）

- 新增段落必须从模板 donor 段落提取 `w:rFonts`（ascii/hAnsi/eastAsia 三项）、`w:sz`、`w:spacing`，再套用；**不要依赖 python-docx 默认字体**（会回退成等线/Calibri）。
- 模板说明文字（`【说明`、`【截图占位`、`注：`）不得被当作 donor，用 `comment_patterns` 排除。
- 需要真实来源时用 `require_<role>_source: true`，让 `doctor` 报 error，而不是静默 fallback。

细节见 `references/style-contract.md`。

## 路径规则

配置里的相对路径（`template` / `output` / `image` / `source` / `file`）一律相对 **config 文件所在目录** 解析，因此配置目录可整体搬移。绝对路径原样使用。

## 文档索引

| 文件 | 何时读 |
|---|---|
| `docs/config-schema.md` | 写/改 report 或 enrich 配置（两类配置的完整字段） |
| `docs/cli.md` | 每条命令的参数与退出码 |
| `docs/quickstart.md` | 从零到第一份报告 |
| `docs/compatibility.md` | 平台/字体/Word 行为假设与失败矩阵 |
| `references/course-profile.md` | 设计课程范式、排查范式未生效 |
| `references/style-contract.md` | 从模板提取 donor 样式、排查字体/行距不匹配 |
| `references/pitfalls.md` | 修订丢图、模板定位失败、替换不生效等疑难 |
| `references/verification-checklist.md` | 交付前逐项自检 |
| `references/revision-mode.md` | 保图修订（revise）模式 |
| `references/scenario-matrix.md` | 判断当前任务该走哪个模式 |
| `references/template-assumptions.md` | 模板固定表格假设变更时 |
| `references/design-notes.md` | 理解设计取舍与边界 |

## Canonical Commands

```bash
# 0) 永远先 doctor：确认配置类型、模板假设、资源、下一条命令
docx-report doctor docs/exp6/report.yml
docx-report doctor docs/exp6/report.yml out/exp6-v1.docx
docx-report doctor docs/exp8/finalize.yml out/exp8-v1.docx

# 1) 生成 / 保图修订 / 富化
docx-report build  docs/exp6/report.yml
docx-report revise docs/exp6/report.yml out/exp6-v1.docx
docx-report enrich docs/exp8/finalize.yml out/exp8-v1.docx

# 2) 核验（比把 docx 读回上下文便宜得多）
docx-report validate docs/exp8/finalize.yml out/exp8-final.docx
docx-report verify   out/exp6.docx docs/exp6/report.yml
docx-report preview  docs/exp6/report.yml --show-patterns --show-screenshots
docx-report inspect-template 模板.docx

# 3) 实验链
docx-report scaffold docs/exp9/report.yml --profile 课程报告范式.yml --experiment 9
docx-report scaffold-notebook docs/exp9/requirements.yml docs/exp9/nb.py
docx-report nbcheck docs/exp9/nb.ipynb --source-py docs/exp9/nb.py
docx-report experiment-doctor docs/exp9/requirements.yml
docx-report artifact-check docs/exp9/results --config docs/exp9/report.yml

# 4) 导出（Windows + Word）
docx-report pdf out/exp6.docx
```

## Verification

- [ ] 目标模式已明确（doctor/build/revise/enrich/validate/verify/preview/inspect-template）
- [ ] 配置能被读取并归一化；**不确认就先跑 `doctor`**
- [ ] 课程范式是否生效；未被单次 config 意外覆盖
- [ ] 图注用 `kind: caption`（不是 `kind: body`），与占位 1:1
- [ ] 新增内容使用从模板 donor 提取的字体/字号/行距
- [ ] revise：`expected_images` 与图片数量一致
- [ ] enrich：锚点与附图资源都存在
- [ ] `verify` 中 `figure_group_tables` = 图组数 + 截图片段数（相邻表被合并会偏小）
- [ ] `verify` 中 `placeholders: 0`（已无文字占位）、`page break after cover: YES`
- [ ] 报告中的数字全部来自实跑产物，未照抄指导书参考值

## 降级行为

- 配置暂不可读 → 明确报错，不猜；YAML 不可用时可退回 Python dict config
- enrich 锚点找不到 → 报 `E_ANCHOR_MISSING`，不静默成功
- 模板结构不匹配 → 只输出结构诊断，不写入
- 报告/enrich 配置传错 → 立即报 `E_CONFIG_WRONG_TYPE`
- 找不到课程范式 → 静默使用内置默认；但显式写了 `course_profile` 而文件不存在/身份不符 → 报 `E_COURSE_PROFILE`
- PDF 平台不支持 → 报 `E_PLATFORM_UNSUPPORTED`，不抛 `ImportError` 裸栈

## 仓库结构

```
src/docx_report/       库 + CLI（单一真源）
src/labkit/            Notebook 可选辅助（种子、指标落盘、存图）
scripts/skill_entry.py 稳定入口（薄壳，不含逻辑）
references/            skill 深潜文档（中文）
docs/                  用户文档（英文）
schema/                两类配置的 JSON Schema
examples/              最小可跑链路
tests/                 pytest；所有 fixture 现场生成，无二进制资产
```

`src/labkit` 提供可选复用函数（种子、指标汇总、指标落盘、存图），**可用但非强制**：只有当某段逻辑会在多个实验重复时才 import；核心实验代码（清洗、划分、Pipeline、采样、搜索空间、评价结论）必须留在 Notebook 内可见。

## 相关工具

- 上游 PDF → 文本：本项目不内置，任何能产出结构化文本的工具都可以先跑。
- 结构理解：可选，不影响本 skill 运行。
