# 样式格式契约（Style Formatting Contract）

> 从 SKILL.md 拆出，按需读取，避免每次加载 skill 都注入全文。

**核心原则：不从零造样式，从模板中提取。** 每个模板的字体、字号、行距、对齐都不同，必须在生成前从模板已有的段落中提取样式参数，再应用到全部新增内容。

### 第一步：定位 donor 段落

在模板中找到至少一个格式完好的"代表段落"作为样式 donor。通常选实验报告内容区域内的第一个 Section 标题段落（如"一、实验实习目的及要求"）。

### 第二步：提取样式参数

从 donor 段落的第一个 run 和段落属性中提取：

```
donor_run   = donor_para.runs[0]._r
donor_rPr   = donor_run.find(qn('w:rPr'))
donor_pPr   = donor_para._element.find(qn('w:pPr'))

font_ascii    = donor_rPr.find('w:rFonts').get(qn('w:ascii'))      # 如"宋体"
font_eastAsia = donor_rPr.find('w:rFonts').get(qn('w:eastAsia'))   # 如"宋体"
font_hAnsi    = donor_rPr.find('w:rFonts').get(qn('w:hAnsi'))      # 如"宋体"
font_size     = donor_rPr.find('w:sz').get(qn('w:val'))            # 如 152400
line_spacing  = donor_pPr.find('w:spacing').get(qn('w:line'))      # 如 360
line_rule     = donor_pPr.find('w:spacing').get(qn('w:lineRule'))  # 如 auto

# 此外记录标题的 bold 状态和对齐方式（见第三步）
```

### 第三步：确定样式角色

从模板已有 experimental title 和 section heading 中提取角色样式：

| 角色 | 提取来源 | 提取属性 |
|------|---------|---------|
| 实验标题 | 模板中已有的"实验一：实验名称"段落 | bold, alignment |
| Section 标题 | 模板中已有的"一、实验实习目的及要求"等段落 | bold, alignment |
| 正文内容 | Section 标题的去 bold 版本 + 相同字体 | 字体、字号、行距与标题一致 |

### 第四步：应用样式

- **已有段落占位（模板原有 slot）**：复用段落中已有 run 的 `w:rPr`，仅替换 `w:t` 文本。空占位段无 run 时，从相邻 section 标题段落深拷贝 run 元素。
- **新增段落（append）**：调用 `add_paragraph()` 后，用第二步提取的参数设置 `w:rFonts`（ascii/hAnsi/eastAsia 三项齐全）、`w:sz`、`w:spacing`。标题额外设对齐 + bold。
- **禁止依赖 python-docx 默认字体**：不设 `w:rFonts` 时 Word 回退到等线/Calibri，几乎不可能与任何中文模板的字体一致。

### 示例（jiwang 模板提取结果）

从一个真实课程模板的"一、实验实习目的及要求"段落提取到的参数：

| 参数 | 提取值 |
|------|--------|
| font_ascii | 宋体 |
| font_eastAsia | 宋体 |
| font_hAnsi | 宋体 |
| font_size | 152400 (12pt) |
| line_spacing | 360 (1.5x) |
| line_rule | auto |
| title_bold | True |
| title_alignment | center |
| heading_bold | False |
