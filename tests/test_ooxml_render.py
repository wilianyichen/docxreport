"""Low-level OOXML rendering: figure tables, separators, metrics sentences."""

from __future__ import annotations

import json

import pytest

from docx_report.errors import ResourceMissingError
from docx_report.models import ParagraphStyle, ReportBlock
from docx_report.ooxml_backend import (
    MAX_GROUP_COLUMNS,
    _content_width_dxa,
    make_group_table,
    make_paragraph,
    make_table_separator,
    render_metrics_text,
    w_tag,
)

NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _cell(text: str):
    return [make_paragraph(text, ParagraphStyle())]


def test_group_table_is_borderless_and_has_two_rows():
    table = make_group_table([_cell("img1")], [_cell("cap1")], 9000)
    assert table.tag == w_tag("tbl")

    borders = table.find(f"{w_tag('tblPr')}/{w_tag('tblBorders')}")
    edges = list(borders)
    assert len(edges) == 6
    assert {edge.get(w_tag("val")) for edge in edges} == {"none"}

    rows = table.findall(w_tag("tr"))
    assert len(rows) == 2
    assert len(rows[0].findall(w_tag("tc"))) == 1


def test_group_table_columns_sum_to_total_width():
    total = 9286
    table = make_group_table([_cell("a"), _cell("b")], [_cell("ca"), _cell("cb")], total)
    grid = table.find(w_tag("tblGrid"))
    widths = [int(col.get(w_tag("w"))) for col in grid.findall(w_tag("gridCol"))]
    assert sum(widths) == total
    assert len(table.findall(w_tag("tr"))[1].findall(w_tag("tc"))) == 2


def test_group_table_merged_caption_row_spans_all_columns():
    table = make_group_table([_cell("a"), _cell("b")], [_cell("merged")], 9000, merge_bottom=True)
    bottom_cells = table.findall(w_tag("tr"))[1].findall(w_tag("tc"))
    assert len(bottom_cells) == 1
    span = bottom_cells[0].find(f"{w_tag('tcPr')}/{w_tag('gridSpan')}")
    assert span.get(w_tag("val")) == "2"


def test_group_table_rejects_empty_column_list():
    with pytest.raises(ValueError):
        make_group_table([], [], 9000)


def test_separator_is_a_tiny_vanish_paragraph():
    """Without it Word merges adjacent nested tables (the 28-vs-13 incident)."""
    paragraph = make_table_separator()
    assert paragraph.tag == w_tag("p")
    spacing = paragraph.find(f"{w_tag('pPr')}/{w_tag('spacing')}")
    assert spacing.get(w_tag("line")) == "20"
    assert spacing.get(w_tag("lineRule")) == "exact"
    assert paragraph.find(f"{w_tag('r')}/{w_tag('rPr')}/{w_tag('vanish')}") is not None


def test_content_width_falls_back_when_missing():
    import xml.etree.ElementTree as ET

    bare = ET.Element(w_tag("tc"))
    assert _content_width_dxa(bare) == 9286


def test_max_group_columns_is_two():
    assert MAX_GROUP_COLUMNS == 2


def test_metrics_sentence_uses_formatted_values(tmp_path):
    source = tmp_path / "metrics.json"
    source.write_text(json.dumps({"test": {"accuracy": 0.91234, "n": 7}}), encoding="utf-8")
    block = ReportBlock(
        kind="metrics",
        text="模型表现：",
        meta={
            "source": str(source),
            "fields": [
                {"key": "test.accuracy", "label": "Accuracy", "fmt": ".4f"},
                {"key": "test.n", "label": "样本数"},
                {"key": "test.missing", "label": "缺失项"},
            ],
        },
    )
    text = render_metrics_text(block)
    assert text == "模型表现：Accuracy = 0.9123，样本数 = 7，缺失项 = 数据缺失。"


def test_metrics_block_requires_existing_source(tmp_path):
    block = ReportBlock(kind="metrics", text="", meta={"source": str(tmp_path / "nope.json")})
    with pytest.raises(ResourceMissingError):
        render_metrics_text(block)


def test_metrics_block_requires_source_key():
    block = ReportBlock(kind="metrics", text="", meta={})
    with pytest.raises(ValueError):
        render_metrics_text(block)


def test_page_break_run_is_preserved_without_old_text():
    """Regression: a break run that carried text left the old title glued on."""
    import xml.etree.ElementTree as ET

    from docx_report.ooxml_backend import _rebuild_paragraph_keep_breaks

    paragraph = ET.Element(w_tag("p"))
    run = ET.SubElement(paragraph, w_tag("r"))
    ET.SubElement(run, w_tag("t")).text = "实验一"
    br = ET.SubElement(run, w_tag("br"))
    br.set(w_tag("type"), "page")

    _rebuild_paragraph_keep_breaks(paragraph, "实验七", ParagraphStyle())

    texts = "".join(node.text or "" for node in paragraph.iter(w_tag("t")))
    assert texts == "实验七"
    assert paragraph.find(f".//{w_tag('br')}").get(w_tag("type")) == "page"
