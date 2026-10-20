# Scenario Matrix

## 目标层级

### 单个课程报告（单实验）

关注点：

- 当前实验的报告内容是否与结果一致
- 当前实验是 `build`、`revise` 还是 `enrich`
- 当前实验是否已有截图、是否需要保图修订
- 当前实验的图表、附加作业、日志段落是否要插入

### 全部课程报告（跨实验）

关注点：

- 是否共享同一 `模板.docx` 结构
- 是否共享统一的 `blocks` 数据模型
- 是否共享 `build / revise / enrich / validate / preview` 流程
- 是否共享占位符、图片槽位、锚点插图这几类抽象

## 场景差异

| 场景 | 主要输入 | 通用层 | 特异层 |
|------|---------|--------|--------|
| build（骨架生成） | 模板 + report.yml | 模板定位、封面写入、block 渲染 | 当前实验的章节文字、占位符、输出路径 |
| revise（保图修订） | 已填写报告 + report.yml | 读取 OOXML、提取图片段落、回填 blocks、可打开性校验 | `expected_images`、image slot 分布、当前实验的修订内容 |
| enrich（后处理） | 现有报告 + enrich/actions config | 锚点查找、文末追加、插图、可打开性校验 | 当前实验的图表路径、caption、章节锚点、实录/WGCNA 内容 |
| validate（结构检查） | 模板或报告 + config | 模板表格检查、资源存在性检查、文档可打开性检查 | 当前实验可能额外要求的数值/截图/输出物核对 |
| preview（配置预览） | report/enrich config | 统计 block 或 action 类型、帮助判断入口是否正确 | 当前实验的 placeholders、anchors、finalize 链路 |

## 共性

- 固定模板表格定位（主要用于 build / revise）
- 统一 `section / body / subheading / placeholder / image` blocks
- run 分裂处理需要 paragraph 级别替换
- 输出都需要经过 validate
- 截图问题可抽象为“占位符 -> 来源 -> 目标段落”
- 富化问题可抽象为“action 序列追加到现有文档”

## 特异性

- 实验正文内容与章节数量
- 每个实验的关键指标和结果解释
- 是否已经插入图片
- enrich 阶段的锚点、图表、附录、终端实录结构
- 是否存在手动截图清单、自动生成图表或一步 finalize 流程

## experiment8 的代表性差异

experiment8 比 experiment6 更典型地体现了 enrich 的层次：

- `wgcna.yml`：附加作业段落 + 文末图
- `artifacts.yml`：实验运行实录 + 代码/输出片段
- `figures.yml`：正文锚点插图
- `finalize.yml`：一步完成上述所有 enrich 动作
