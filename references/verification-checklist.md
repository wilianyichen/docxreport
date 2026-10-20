# Verification Checklist

每次写出 DOCX 之前，至少检查：

## 通用

- 模板/输入文件存在
- 输出目录存在或可创建
- 结果文件可被 `python-docx` 打开

## build / revise

- 模板布局满足固定表格假设
- report config 能被正常读取
- `blocks` 非空且章节顺序合理
- 如果报告仍保留截图占位符，确认这是预期行为
- donor style source 是否符合预期（template / input_docx / fallback）
- 模板说明/占位文字没有被错误当作 donor

## revise

- 图片数量符合 `expected_images`（若配置声明）
- 修订后截图/图片段落未被误删
- 这是一次 OOXML 保图修订，而不是 python-docx 重写整段
- 若某类 donor 要求真实来源（`require_*_source: true`），确认没有 unresolved required donor

## enrich

- enrich config 能被正常读取
- 所有 required 图像资源存在
- `insert_image_after_anchor` 的锚点存在
- `append_image` 的图像资源存在
- 对 experiment8 这种分步 enrich，确认当前阶段输入文档是对的

## doctor / preview / inspect-template

- `doctor`：确认配置类型、输入文件、模板假设、资源存在性、donor source 与下一条推荐命令
- `preview`：确认传入的是 report config 还是 enrich config，并检查 `resolved_style_sources`
- `inspect-template`：确认模板检查通过后再跑 build / revise

## 课程范式（Course Report Profile）

- `doctor` 应输出 `[OK] course-profile: ...`；若只出现 `[NOTE] no course report profile reached`，说明当前目录树里没有 `kind: course-report-profile` 的文件
- 确认课程范式文件的身份标识正确（`kind: course-report-profile`），否则会被静默忽略
- 确认单次 config **没有**重复声明 `styles` / `style_resolution`（应继承课程范式；只有本次实验特有的差异才写在 config 里）
- 若课程模板的节标题与正文格式相同（层次退化），确认范式里已把相关角色声明为 `[fallback]`
- 图注必须用 `kind: caption`（不是 `kind: body`），`doctor` 的 `captions` 检查应为与占位 1:1

## 交付前结构自检（对照课程范式）

- 节标题齐全（一~六），字号层次正确（节标题 > 作业小标题 > 正文 > 图注）
- 第五节按「作业N」逐项展开，图片未全部堆在节尾
- 每个占位行下方紧跟一行图注；占位行蓝色加粗居中
- 无模板提示语残留（如「结合实验指导书」「不能直接复制粘贴」）
- 图组一律用「一行图 + 一行图注」无边框表格；`verify` 的 `figure_group_tables` 数量应等于配置里的图组数 + 截图片段数（相邻表被合并会导致数字偏小）
- 运行截图为红色 16:10 占位图片，图注为蓝色 0000FF；交付时 `placeholders` 应为 0（已无文字占位）
- `verify` 的 `[cover page break]` 必须为 YES：封面标题段落要保留模板的 `<w:br w:type="page"/>`，否则封面与正文挤在同一页
- 报告中的数字全部来自实跑产物，未照抄指导书参考值

## 实验完整性与 Notebook 门禁

- 报告 config 若声明 `experiment_requirements`，先运行 `experiment-doctor`，只有 `READY` 才能正式 build
- 解释器绝对路径、Python 版本、Notebook kernel 与 `metrics.json.run` 一致；不得静默换环境
- mandatory 作业逐项有已执行代码、输出、指标/图片证据；代码存在但未运行不算完成
- Notebook 从空内核完整执行，0 error、0 非空未执行代码单元
- `screenshot_units` 已声明；每个截图片段对应一个已执行代码单元，图片数与声明一致
- 同一作业的代码没有被图片隔断；单元格图片数不超过 `max_images_per_cell`
- 高密度图未被强行拼成母图；母图面板有 (a)(b)(c)(d) 标注，且报告图注写清子图数
- 报告占位行引用的单元号与 `screenshot_units` 完全一致
- 外部工具截图（Data Wrangler/Excel）只在占位行标注工具名，未替代代码证据；正文数字仍来自 metrics.json
- `metrics.json` 由 Notebook 本次运行自动生成且不早于 Notebook
- 报告中的方法和数字可追溯；不得写入 Notebook 未执行的方法或指导书参考数值
- 缺依赖、外部数据或人工输入必须明确 `BLOCKED / OPTIONAL_NOT_DONE`，不得静默跳过
- 图片无缺失、无不同图号引用同一字节文件；运行 `artifact-check`
- 正式 PDF 在人工截图替换后导出；默认有占位符时 `pdf` 命令拒绝导出
