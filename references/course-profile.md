# 课程范式契约（Course Report Profile）

> 从 SKILL.md 拆出，按需读取。设计新课程范式或排查范式未生效时读本文件。

**分层优先级：skill 内置默认 < 课程范式文件 < 单次实验 report config**（越靠右越高）。

课程范式是「一门课一份」的统一样式与规范，该课程下的多个实验目录共用，避免每个实验 config 重复声明样式。

### 身份标识

文件内必须有：

```yaml
kind: course-report-profile
```

### 查找规则

以 report config 所在目录为起点逐级向上（最多 6 层）：

1. 先认约定文件名：`课程报告范式.yml/.yaml/.json`、`course-report-profile.yml/.yaml`、`course_report_profile.yml/.yaml`
2. 再浅扫同级目录下任意 `*.yml` / `*.yaml`（最多 60 个），只认 `kind: course-report-profile` 的文件

也可在单次 config 里显式指定，路径相对 config 所在目录：

```yaml
course_profile: ../课程报告范式.yml
```

### 范式可提供的内容

| 键 | 作用 |
|---|---|
| `styles` | 样式角色（cover_title / experiment_name / section / subheading / body / `caption` / placeholder / code）；支持 `font` 简写一次性设置 ascii/hAnsi/eastAsia |
| `spacing` | `text_line` / `caption_line` / `spacing_after`，按角色自动分配到 ParagraphStyle |
| `style_resolution` | donor 来源规则。**若课程模板的节标题与正文格式相同（层次退化），应在范式里统一指定 `section: [fallback]` 等，不要沿用模板 donor** |
| `naming` / `structure` / `figures` / `experiment_rules` | 人读约定与交付自检项，脚本暂不强制校验 |

### 图注角色 caption

图注用独立的 `caption` 块（块类型 `caption`，style 角色 `caption`），默认 10.5pt、居中、单倍行距，与正文区分：

```yaml
blocks:
  - kind: placeholder
    text: 【图片占位｜结果图：...】
  - kind: caption
    text: 图1 标题。坐标轴含义与关键数值。
```

### 已登记的课程范式

- 示例：把 `课程报告范式.yml` 放在课程根目录，该课程下各实验的 config 都会自动继承。
  文件内必须写 `kind: course-report-profile`，否则不会被识别。

### 运行库位置

skill 自带运行库在 `<skill>/lib/docx_report`，是**单一真源**；各实验目录里的 `docx_report` 以 junction 指向它，
入口脚本优先使用自带 lib，找不到才回退到「从 cwd 向上查找」。因此本 skill 在任何目录都可直接运行，无需设置 PYTHONPATH。
