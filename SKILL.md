---
name: docx-report-skill
description: "本地实验报告 DOCX 生成/修订/富化技能。用于模板报告填充、保留截图修订、插入生成图表、追加实验实录/WGCNA 附录与配置预览。"
version: "0.2.0"
skill_type: do
consumes: [design_spec]
produces: [manifest]
keywords: [docx, report, 实验报告, 模板, 修订, 截图, 图表, enrich]
capabilities: [docx-generation, docx-revision, template-filling, screenshot-planning, enrich-actions]
model_tier: standard
task_type: operation
status: active
---

# DOCX Report Skill

## Overview

这个 skill 负责当前项目里的实验报告 DOCX 工作流：

- 基于固定模板生成报告
- 在不丢截图的前提下修订已有报告
- 按锚点插入生成图表
- 追加实验运行实录、WGCNA 附录等 enrich 内容
- 预览 report/enrich 配置并检查模板假设

它不负责 PDF 抽取；上游 PDF 内容请继续交给 `pdf-extract-pipeline`。

## When to Use

- 用户要生成实验报告 `.docx`
- 用户要修改已有实验报告，但不想丢失已插入截图
- 用户要把结果图、终端实录、附录追加进报告
- 用户要检查 report/enrich 配置是否走对入口
- 用户要检查 `模板.docx` 是否仍满足固定表格假设
- 用户要把当前散落脚本统一成可复用的本地工作流
- 不要在此场景使用：扫描 PDF 抽取、OCR、PDF 结构化解析

## Process

Step 1: 选择模式（`doctor / experiment-doctor / nbcheck / build / revise / enrich / validate / preview / inspect-template / pdf`）
  退出标准: 已明确当前任务属于哪个阶段，并确认输入是模板、现有报告、report config 还是 enrich config
  产出: 命令选择与输入文件清单

Step 1.5: 先做 doctor（推荐）
  退出标准: 已确认配置类型、输入文件、模板假设、enrich 资源与下一条推荐命令
  产出: readiness 摘要 + next command

Step 2: 读取配置
  退出标准: 已加载实验报告配置，并识别这是 `report.yml` 还是 `actions` 型 enrich 配置
  产出: 标准化后的配置对象

Step 3: 执行文档操作
  退出标准: 已完成模板填充、原位修订、文末富化、锚点插图或配置预览中的一种
  产出: 新的 `.docx` 文件或配置摘要

Step 4: 运行校验
  退出标准: 模板结构、占位符、图片数量、锚点、附图资源和可打开性检查通过
  产出: 校验摘要

Step 5: 输出给用户
  退出标准: 已汇报生成文件路径、适用限制、是分步链路还是一步 finalize、以及后续可继续的动作
  产出: 最小必要说明


## 课程范式契约（Course Report Profile）

**分层优先级：skill 内置默认 < 课程范式文件 < 单次实验 config**（越靠右越高）。

- 课程范式是「一门课一份」的统一样式与规范，该课程各实验目录共用；单次 config 只写本次特有内容。
- 身份标识：文件内必须写 `kind: course-report-profile`，否则被静默忽略。
- 查找：从 report config 所在目录逐级向上（≤6 层），先认约定文件名再浅扫 `*.yml`；也可在 config 里写 `course_profile: <路径>`。
- `doctor` 应输出 `[OK] course-profile: ...`。
- 已登记：`C:/Users/wilia/Desktop/學習資料/生物大数据/课程报告范式.yml`（课程 A2061250，适用目录 1~8）。

细节（查找规则、可提供字段、合并语义、如何新建一门课的范式）见 `references/course-profile.md`。

## 实验完整性门禁（先完成实验，再写报告）

- 单次报告 config 可声明 `experiment_requirements: <requirements.yml>`；声明后，正式 `build` 前强制运行完整性检查。
- 要求文件必须固定实际解释器绝对路径、Python 版本、必需导入、Notebook、metrics 和 mandatory/advanced 清单。
- **禁止环境静默回退**：指定解释器不存在、Notebook 实际 kernel 不一致或必需包不可导入时返回 `BLOCKED`，不得自动改用 base 环境。
- “代码存在”不等于“实验完成”：必须同时有本次完整执行输出、无错误、指标/图片产物和 `metrics.json` 中的逐项状态。
- mandatory 出现 `MISSING / PARTIAL / BLOCKED / INCONSISTENT / STALE` 时，报告不是 ready，`build` 必须拒绝。
- 选做项缺少外部数据时写 `OPTIONAL_NOT_DONE` 并明确原因；不得用内部测试集冒充外部验证。
- 报告声称使用的方法（如 GridSearchCV、StandardScaler、SMOTE、SHAP）必须能在 Notebook 的已执行单元和产物中追溯。
- `metrics.json` 必须由 Notebook 本次运行自动写出，并记录 `sys.executable`、Python/关键包版本和 requirements 状态。
- **一个代码单元 = 一段自洽代码 + 它自己的全部输出 = 报告里的一张运行截图**（`screenshot_units` 声明并用 `nbcheck` 校验）。
- 同一作业的代码不得被图片隔断；同构低密度子图拼成 2×2 / 1×3 母图并标注 (a)(b)(c)(d)。
- 高密度图（相关系数矩阵、SHAP、多混淆矩阵）保持独立尺寸，不合并，否则缩到正文宽度后不可读。
- 单元代码建议 ≤ 30 行；超过就拆成多个截图片段，不要指望把 60 行代码缩进一页还看得清。

常用命令：`nbcheck`、`experiment-doctor`、`artifact-check`、`scaffold-notebook`、`pdf`。

## 块类型（blocks）

| kind | 用途 | 关键字段 |
|---|---|---|
| `section` | 节标题（一、实验目的…） | `text` |
| `subheading` | 作业小标题 | `text` |
| `body` | 正文 | `text` |
| `caption` | 图注（位于图片下方，10.5pt 居中） | `text` |
| `screenshot` | **运行截图占位**：插入红色 16:10 占位图片，本人「右键→更改图片」替换 | `text`=图注、`label`、`hint`、`images`(1或2) |
| `figure_group` | **结果图图组**：`items` 里 1~2 张图，渲染成「一行图 + 一行图注」无边框表格 | `items: [{image, text}]` |
| `placeholder` | 旧的文字占位（保留兼容；新报告请用 `screenshot`） | `text` |
| **`figure`** | **自动插图**：图片直接嵌入正文单元格，图注自动置于图片下方 | `image`（相对 cwd 的路径）、`width_inches`（默认 5.2）、`text`=图注 |
| **`metrics`** | **自动搬运数字**：从 JSON 读键值渲染成一句话，避免人工转抄指标 | `source`（JSON 路径）、`fields`：`{key: 点号路径, label, fmt}`、`text`=句首 |

约定：**结果图用 `figure` / `figure_group`（表格化）自动插入**；运行截图用 `screenshot` 块插入**红色占位图片**，本人用「更改图片」替换。
所有图片一律走「一行图 + 一行图注」的无边框表格，一行最多 2 张；禁止浮动图。

外部工具截图（VSCode Data Wrangler / Excel / pandas-profiling 等）允许作为**辅助**运行截图：
占位行写清工具名即可，不需要单元号；但它**不能**替代作业的可执行代码单元与结果图，
报告正文的数字仍必须来自 `results/metrics.json`。

## references 索引（按需读取，勿全量注入）

| 文件 | 何时读 |
|---|---|
| `references/course-profile.md` | 设计新的课程范式、或排查范式未生效 |
| `references/style-contract.md` | 需要从模板提取 donor 样式、排查字体/行距不匹配 |
| `references/pitfalls.md` | 修订丢图、模板定位失败、替换不生效等疑难 |
| `references/config-schema.md` | 写/改 report 或 enrich 配置 |
| `references/verification-checklist.md` | 交付前逐项自检 |
| `references/revision-mode.md` | 保图修订（revise）模式 |
| `references/scenario-matrix.md` | 判断当前任务该走哪个模式 |
| `references/template-assumptions.md` | 模板固定表格假设变更时 |
| `references/design-notes.md` | 理解 skill 的设计取舍 |

- `lib/labkit/__init__.py` 提供可选复用函数（种子、指标汇总、指标落盘、存图）。它是“可用但非强制”的；只有当某段逻辑会在多个实验重复时才 import，核心实验代码（清洗、划分、Pipeline、采样、搜索空间、评价结论）必须留在 Notebook 内可见。

## Canonical Commands

```bash
# doctor：先检查 readiness，再决定下一步
python C:/Users/wilia/.workbuddy/skills/docx-report-skill/scripts/skill_entry.py doctor report_configs/experiment6/report.yml
python C:/Users/wilia/.workbuddy/skills/docx-report-skill/scripts/skill_entry.py doctor report_configs/experiment6/report.yml 2023212557-吴笑然-实验6.docx
python C:/Users/wilia/.workbuddy/skills/docx-report-skill/scripts/skill_entry.py doctor report_configs/experiment8/finalize.yml 8/实验8-报告-v1-无附加作业.docx

# 生成骨架报告
python C:/Users/wilia/.workbuddy/skills/docx-report-skill/scripts/skill_entry.py build report_configs/experiment6/report.yml

# 保图修订
python C:/Users/wilia/.workbuddy/skills/docx-report-skill/scripts/skill_entry.py revise report_configs/experiment6/report.yml /path/to/existing.docx

# enrich 一步流
python C:/Users/wilia/.workbuddy/skills/docx-report-skill/scripts/skill_entry.py enrich report_configs/experiment8/finalize.yml 8/实验8-报告-v1-无附加作业.docx

# 预览 report/enrich 配置
python C:/Users/wilia/.workbuddy/skills/docx-report-skill/scripts/skill_entry.py preview report_configs/experiment6/report.yml --show-patterns --show-screenshots
python C:/Users/wilia/.workbuddy/skills/docx-report-skill/scripts/skill_entry.py preview report_configs/experiment8/finalize.yml

# 模板假设检查
python C:/Users/wilia/.workbuddy/skills/docx-report-skill/scripts/skill_entry.py inspect-template 模板.docx

# 结构校验
python C:/Users/wilia/.workbuddy/skills/docx-report-skill/scripts/skill_entry.py validate report_configs/experiment8/finalize.yml /tmp/exp8-finalize.docx
```




## Verification

- [ ] 目标模式（`doctor / build / revise / enrich / validate / preview / inspect-template`）已明确
- [ ] 配置能被脚本读取并归一化
- [ ] 若不确定是否可执行，先跑过 `doctor`
- [ ] 已确认课程范式是否生效；未被单次 config 意外覆盖
- [ ] 图注使用 `kind: caption`，字号与正文不同（默认 10.5pt 居中）
- [ ] 已从模板 donor 段落提取样式参数（字体、字号、行距），并应用到全部新增内容；
      但若课程范式把该角色声明为 `[fallback]`，以范式为准（课程模板层次退化时属正常）
- [ ] 若为 revise 模式，图片数量检查已执行
- [ ] 若为 enrich 模式，锚点/附图资源检查已执行
- [ ] 若为 preview 模式，已确认配置类型无误

## 降级行为

- YAML 配置暂不可读 → 退回 Python dict report 配置
- enrich 锚点找不到 → 输出明确错误或警告，不静默成功
- 模板结构不匹配 → 仅输出结构诊断，不做 build / revise 写入
- report/enrich 配置传错 → 立即报错，不隐式猜测执行
- 找不到课程范式（无 `kind: course-report-profile` 的文件）→ 静默使用 skill 内置默认样式；但 config 里显式写了 `course_profile` 而文件不存在或身份不符时立即报错



## 关联 Skill

- `pdf-extract-pipeline` — 上游，负责把 PDF 指导书转换成可消费文本
- `graphify` — 可选，用于理解当前项目脚本与流程结构

