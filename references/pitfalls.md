# 常见借口 · 红旗 · 失败模式 · Gotchas

> 从 SKILL.md 拆出，按需读取。

## Common Rationalizations

| 借口 | 真相 | 回应 |
|------|------|------|
| “直接在旧脚本里再改一次就行” | 会继续复制 run 分裂、保图和 enrich 动作逻辑 | “先进入统一入口，再补实验特例。” |
| “截图已经插好，改正文应该很简单” | 现有报告修订最容易误伤图片段落 | “先走 revise 模式，再谈文字变更。” |
| “先随便 enrich 一下，后面再看配置对不对” | report/enrich 配置传错入口时会浪费很多时间 | “先 preview 配置，再执行写入。” |

## Red Flags

| # | 红旗 | 症状 | 纠正措施 |
|---|------|------|---------|
| 1 | 模板结构变化 | 表格数量或固定 cell 不存在 | 先运行 `inspect-template`，再更新布局假设 |
| 2 | run 分裂替换失效 | 目标文本在报告里没改掉 | 回到 paragraph 级别替换 helper |
| 3 | 截图丢失 | 修订后图片数量减少 | 回到 revise 模式并开启图片数量校验 |
| 4 | enrich 入口选错 | 把 report config 当 enrich config 或反之 | 先运行 `preview`，确认 `type: report/enrich` |

## Failure Modes

| # | 失败模式 | 症状 | 修复 |
|---|---------|------|------|
| 1 | 固定模板定位失败 | `expected at least two tables` 一类错误 | 更新布局假设并重跑模板检查 |
| 2 | 锚点缺失 | enrich 阶段找不到目标标题 | 调整 anchor 文本或先生成章节标题 |
| 3 | 配置不完整 | 缺少 `output` / `blocks` / `actions` | 补齐配置后再执行 |
| 4 | enrich 资源缺失 | 图表或附图路径不存在 | 先修复资源，再执行 enrich/validate |
| 5 | 字体/字号/行距不匹配 | 部分段落使用等线/Calibri 而非宋体，或行距不是 1.5 | 对照「样式格式契约」逐段修复 w:rFonts、w:sz、w:spacing |

## Gotchas

- *AI 默认会直接按 run 替换字符串* —— 不。必须优先使用 paragraph 级别 helper。
- *AI 默认会把 PDF 抽取也塞进这个 skill* —— 不。PDF 继续走 `pdf-extract-pipeline`。
- *AI 默认会假设所有实验都和模板完全一致* —— 不。先检查模板假设，再写入。
- *AI 默认会把 experiment8 当成单一 enrich 配置* —— 不。它既支持分步链路，也支持 `finalize.yml` 一步流。
- *AI 默认会用 python-docx 的默认字体生成新 run* —— 不。必须先从模板 donor 段落提取 `w:rFonts`（ascii/hAnsi/eastAsia）、`w:sz`、`w:spacing`，再应用到新增内容。参照「样式格式契约」。

## 实验/Notebook 链路的已知事故（均已用代码拦住）

| 事故 | 现象 | 现在的拦截方式 |
|---|---|---|
| 环境认错 | 凭记忆假定 `D:\anaconda\envs\py39`，实际在 `C:\Users\wilia\.conda\envs\py39` | requirements 声明绝对路径；`experiment-doctor` 先探针验证解释器+版本+必需 import |
| 静默换环境 | 指定解释器不存在时改用 base，而 base 的 sklearn/imblearn 是混装的 | `forbid_environment_fallback`；Notebook 内 `assert sys.executable` |
| 报告虚写方法 | 报告写了 `GridSearchCV`/`StandardScaler`，Notebook 里根本没有 | requirements 的 `requires_methods` 扫描**已执行**代码单元，缺一即 INCONSISTENT |
| py/ipynb 脱同步 | 手工在 Jupyter 改 ipynb，`.py` 真源过期 | `nbcheck --source-py` 逐代码单元比对 |
| cwd 依赖路径 | 从 `_tmp` 跑 nbconvert 时找不到 `data/` | 显式候选列表 + 唯一匹配，不唯一就报错 |
| joblib 清理报错 | `n_jobs=-1` 训练收尾阶段 KeyError | 约定 `n_jobs=1`；脚手架模板已内置该注释 |
| 手搓 docx 统计 | `python-docx` 遍历合并单元格会重复计数，10 个占位被数成 40 个 | 一律用 `verify`（按 OOXML `w:p` 唯一遍历），不要自己数 |
| 无关依赖误判 | `pip check` 因 xgboost 非零退出被当阻断 | 门禁只检查本实验 `required_imports`，不做全局 `pip check` |

## 作业纪律（针对 agent 自身）

- 大段带转义的内容**不要用 shell heredoc**：写到 `_tmp/*.py` 再执行，避免被截断或把转义序列破坏。
- 打补丁用“锚点出现次数断言”，`count != 1` 立即中止；不要盲替换。
- 切片文件前先确认总行数；`view_range` 越界会直接失败。
- 每次写 YAML/JSON 后立刻解析校验，再进入下一步。
- 往文件里插入内容前，先确认插入点不在三引号字符串内部。
## 图组表格 / 占位图（2026-09-18 新增布局）

| 事故 | 现象 | 拦截方式 |
|---|---|---|
| 嵌套表被合并 | 正文里 28 个图组表，Word 只报 13 个 —— 相邻的嵌套表被 Word 合并成一张 | 每个图组表后必须紧跟一个 `make_table_separator()`（vanish + line=20 exact 的极小段落） |
| 孤立媒体误判 | 把 `word/media/image1.png` 当成删除残留，其实它是 `word/header1.xml` 引用的页眉校徽 | 检测孤立媒体必须扫描**全部 `.rels`（含 header/footer）**，不能只看 `document.xml` |
| 占位用文字 | 文字占位替换图片后尺寸/位置每张都要手调 | 改用红色 16:10 占位**图片**，本人「右键→更改图片」，外框自动保持 |
| 图注颜色语义 | 蓝色同时用于占位与图注，失去区分 | 图注=蓝色 0000FF（最终样式）；占位=红色 FF0000 |
