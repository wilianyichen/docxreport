# Revision Mode

`revise` 模式用于修改已经插入截图/图片的现有实验报告，目标是在更新正文时保留已有图片。

## 约束

- 优先走 OOXML 路线，不要直接在 `python-docx` 中重建整段内容
- 先提取图片段落，再重排正文 block，最后把图片按 `image` block 回填
- 如果配置声明了 `expected_images`，数量不匹配时应立即失败
- revise 的重点是“保图修正文”，不是“顺手把 enrich 也一起做了”

## 当前适用来源

- `revise_existing_reports.py`
- `docx_report/revision.py`
- `docx_report/ooxml_backend.py`

## 适用场景

- 实验 6 这类：已有报告正文要更新，但原来插入的截图/图片不能丢
- 现有报告仍然服从固定模板表格结构

## 不适用

- 新报告从零生成（应走 `build`）
- experiment8 这类以文末附录/锚点插图为主的 enrich 流程（应走 `enrich`）
- 通用 Word 文档审阅和 tracked changes

## 建议流程

1. 先 `preview` report config，确认 `expected_images` 与 blocks 合理
2. 再 `inspect-template` / `validate`，确认模板/现有报告仍匹配固定布局
3. 执行 `revise`
4. 重新 `validate` 输出文档，确认图片数量与可打开性都正常
