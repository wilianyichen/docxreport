# Template Assumptions

当前模板流默认复用根目录脚本已经验证过的固定表格结构假设：

- 目标模板通常来自 `模板.docx`
- 文档主体至少包含 2 个表格
- 第 1 个表格用于封面信息
- 第 2 个表格用于报告标题和正文内容
- 实验名默认位于第 2 个表格的第 4 行第 2 列
- 正文默认位于第 2 个表格的第 6 行第 1 列

这些假设主要服务于：

- `build`：从模板生成骨架报告
- `revise`：在已有固定模板报告上保图修订

## 当前检查方式

可以直接运行：

```bash
docx-report inspect-template /path/to/template.docx
```

或：

```bash
# 旧脚本仍可用（已弃用，等价于上面的命令）
python scripts/inspect_docx_template.py /path/to/template.docx
```

## 什么时候需要更新 assumptions

- 模板表格数量变化
- 封面表格与正文表格顺序变化
- 实验名所在单元格位置变化
- 正文所在单元格位置变化

## enrich 与模板假设的关系

- `enrich` 不依赖固定表格定位
- `enrich` 更依赖段落锚点和图像/附件资源是否存在
- 所以模板结构问题优先影响 `build / revise`，锚点问题优先影响 `enrich`

## 样式格式假设

**核心原则：不从零造样式，从模板提取。** 不同模板的字体、字号、行距可能完全不同，生成/修订前必须从模板内容区域已有的段落中提取样式参数（donor-based style extraction），而非假设固定值。

提取流程详见 `SKILL.md` 中的「样式格式契约」：

1. 定位 donor 段落（模板内容区域第一个 Section 标题）
2. 从 donor run 提取 `w:rFonts`（ascii/hAnsi/eastAsia）、`w:sz`
3. 从 donor paragraph 提取 `w:spacing`（line/lineRule）
4. 从模板标题段落提取 bold、alignment
5. 将提取的参数应用到全部新增段落

python-docx 的默认字体是等线/Calibri，与任何中文模板的字体都不匹配，**每次 `add_run()` 或 `add_paragraph()` 后必须用提取到的参数显式覆盖字体、字号和行距。**
