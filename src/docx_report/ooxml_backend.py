from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile, ZipInfo

from .errors import ResourceMissingError, TemplateError
from .figure_media import MediaContext
from .models import ParagraphStyle, ReportConfig, ReportStyleProfile
from .placeholder_image import make_placeholder_image
from .style_resolver import resolve_style_profile

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
W = f"{{{W_NS}}}"


def register_namespaces(xml_bytes: bytes) -> None:
    text = xml_bytes.decode("utf-8", errors="ignore")
    for prefix, uri in re.findall(r'xmlns:([A-Za-z0-9_]+)="([^"]+)"', text):
        if prefix != "xml":
            ET.register_namespace(prefix, uri)


def w_tag(name: str) -> str:
    return f"{W}{name}"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def make_paragraph(text: str, style: ParagraphStyle) -> ET.Element:
    p = ET.Element(w_tag("p"))
    p_pr = ET.SubElement(p, w_tag("pPr"))
    spacing = ET.SubElement(p_pr, w_tag("spacing"))
    spacing.set(w_tag("after"), str(style.spacing_after))
    spacing.set(w_tag("line"), str(style.spacing_line))
    spacing.set(w_tag("lineRule"), style.spacing_line_rule)
    if style.align:
        jc = ET.SubElement(p_pr, w_tag("jc"))
        jc.set(w_tag("val"), style.align)

    r = ET.SubElement(p, w_tag("r"))
    r_pr = ET.SubElement(r, w_tag("rPr"))
    r_fonts = ET.SubElement(r_pr, w_tag("rFonts"))
    r_fonts.set(w_tag("ascii"), style.ascii_font)
    r_fonts.set(w_tag("hAnsi"), style.hansi_font)
    r_fonts.set(w_tag("eastAsia"), style.east_asia_font)
    r_fonts.set(w_tag("cs"), style.cs_font)
    if style.bold:
        ET.SubElement(r_pr, w_tag("b"))
        ET.SubElement(r_pr, w_tag("bCs"))
    if style.color:
        c = ET.SubElement(r_pr, w_tag("color"))
        c.set(w_tag("val"), style.color)
    sz = ET.SubElement(r_pr, w_tag("sz"))
    sz.set(w_tag("val"), str(style.size))
    sz_cs = ET.SubElement(r_pr, w_tag("szCs"))
    sz_cs.set(w_tag("val"), str(style.size))
    t = ET.SubElement(r, w_tag("t"))
    if text[:1].isspace() or text[-1:].isspace() or "  " in text:
        t.set(f"{{{XML_NS}}}space", "preserve")
    t.text = text
    return p


def clear_cell(cell: ET.Element) -> ET.Element:
    tc_pr = cell.find(w_tag("tcPr"))
    for child in list(cell):
        if child is not tc_pr:
            cell.remove(child)
    if tc_pr is None:
        tc_pr = ET.SubElement(cell, w_tag("tcPr"))
    return tc_pr


def replace_cell_text(cell: ET.Element, text: str, style: ParagraphStyle) -> None:
    clear_cell(cell)
    cell.append(make_paragraph(text, style))


def _resolve_dotted(data, key: str):
    cur = data
    for part in str(key).split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except Exception:
                return None
        else:
            return None
        if cur is None:
            return None
    return cur


def render_metrics_text(block, *, base: Path | None = None) -> str:
    """把 results/metrics.json 里的数字渲染成一句话，避免人工搬运数值。

    配置示例：
        - kind: metrics
          source: results/metrics.json
          text: "运行结果数据。"
          fields:
            - {key: test.accuracy, label: 测试集 Accuracy, fmt: ".4f"}
            - {key: test.death_recall, label: 死亡类 Recall, fmt: ".4f"}
    """
    source = block.meta.get("source")
    fields = block.meta.get("fields") or []
    if not source:
        raise ValueError("metrics block requires a source path")
    path = Path(str(source))
    if not path.is_absolute():
        path = (base or Path.cwd()) / path
    if not path.exists():
        raise ResourceMissingError(f"metrics source not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    parts = []
    for field in fields:
        key = field.get("key")
        label = field.get("label") or key
        fmt = field.get("fmt")
        value = _resolve_dotted(data, key)
        if value is None:
            parts.append(f"{label} = 数据缺失")
            continue
        if fmt and isinstance(value, (int, float)):
            shown = format(value, str(fmt))
        else:
            shown = str(value)
        parts.append(f"{label} = {shown}")
    prefix = block.text or ""
    return f"{prefix}{'，'.join(parts)}。"


MAX_GROUP_COLUMNS = 2
CELL_GAP_INCHES = 0.06


def _content_width_dxa(cell: ET.Element) -> int:
    """读取正文单元格宽度（twips）；读不到时回退到课程模板的 9286。"""
    tc_pr = cell.find(w_tag("tcPr"))
    if tc_pr is not None:
        tc_w = tc_pr.find(w_tag("tcW"))
        if tc_w is not None:
            try:
                value = int(tc_w.get(w_tag("w")))
                if tc_w.get(w_tag("type")) in (None, "dxa") and value > 1000:
                    return value
            except (TypeError, ValueError):
                pass
    return 9286


def _borderless_table_pr(total_width_dxa: int) -> ET.Element:
    pr = ET.Element(w_tag("tblPr"))
    tbl_w = ET.SubElement(pr, w_tag("tblW"))
    tbl_w.set(w_tag("w"), str(total_width_dxa))
    tbl_w.set(w_tag("type"), "dxa")
    layout = ET.SubElement(pr, w_tag("tblLayout"))
    layout.set(w_tag("type"), "fixed")
    borders = ET.SubElement(pr, w_tag("tblBorders"))
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = ET.SubElement(borders, w_tag(edge))
        node.set(w_tag("val"), "none")
        node.set(w_tag("sz"), "0")
        node.set(w_tag("space"), "0")
        node.set(w_tag("color"), "auto")
    margins = ET.SubElement(pr, w_tag("tblCellMar"))
    for edge in ("top", "left", "bottom", "right"):
        node = ET.SubElement(margins, w_tag(edge))
        node.set(w_tag("w"), "0")
        node.set(w_tag("type"), "dxa")
    return pr


def _table_cell(width_dxa: int, children: list[ET.Element], span: int | None = None) -> ET.Element:
    cell = ET.Element(w_tag("tc"))
    tc_pr = ET.SubElement(cell, w_tag("tcPr"))
    tc_w = ET.SubElement(tc_pr, w_tag("tcW"))
    tc_w.set(w_tag("w"), str(width_dxa))
    tc_w.set(w_tag("type"), "dxa")
    if span and span > 1:
        grid_span = ET.SubElement(tc_pr, w_tag("gridSpan"))
        grid_span.set(w_tag("val"), str(span))
    for child in children:
        cell.append(child)
    if not children or children[-1].tag != w_tag("p"):
        cell.append(ET.Element(w_tag("p")))
    return cell


def make_table_separator() -> ET.Element:
    """相邻的嵌套表会被 Word 合并成一张表，必须在表与表之间放一个极小的段落隔开。"""
    paragraph = ET.Element(w_tag("p"))
    p_pr = ET.SubElement(paragraph, w_tag("pPr"))
    spacing = ET.SubElement(p_pr, w_tag("spacing"))
    spacing.set(w_tag("before"), "0")
    spacing.set(w_tag("after"), "0")
    spacing.set(w_tag("line"), "20")
    spacing.set(w_tag("lineRule"), "exact")
    r_pr = ET.SubElement(p_pr, w_tag("rPr"))
    ET.SubElement(r_pr, w_tag("vanish"))
    run = ET.SubElement(paragraph, w_tag("r"))
    run_pr = ET.SubElement(run, w_tag("rPr"))
    ET.SubElement(run_pr, w_tag("vanish"))
    return paragraph


def make_group_table(
    top_cells: list[list[ET.Element]],
    bottom_cells: list[list[ET.Element]],
    total_width_dxa: int,
    *,
    merge_bottom: bool = False,
) -> ET.Element:
    """生成「一行放图、一行放图注」的无边框表格，列对齐保证图片与图注一一对应。"""
    columns = len(top_cells)
    if columns < 1:
        raise ValueError("group table needs at least one column")
    table = ET.Element(w_tag("tbl"))
    table.append(_borderless_table_pr(total_width_dxa))
    base = total_width_dxa // columns
    widths = [base] * columns
    widths[-1] = total_width_dxa - base * (columns - 1)
    grid = ET.SubElement(table, w_tag("tblGrid"))
    for width in widths:
        grid_col = ET.SubElement(grid, w_tag("gridCol"))
        grid_col.set(w_tag("w"), str(width))

    row_top = ET.SubElement(table, w_tag("tr"))
    for index, children in enumerate(top_cells):
        row_top.append(_table_cell(widths[index], children))

    row_bottom = ET.SubElement(table, w_tag("tr"))
    if merge_bottom:
        row_bottom.append(_table_cell(total_width_dxa, bottom_cells[0], span=columns))
    else:
        for index, children in enumerate(bottom_cells):
            row_bottom.append(_table_cell(widths[index], children))
    return table


def _figure_items(block) -> list[dict]:
    items = block.meta.get("items")
    if isinstance(items, list) and items:
        return [dict(item) for item in items]
    return [
        {"image": block.meta.get("image"), "text": block.text, "width_inches": block.meta.get("width_inches")}
    ]


def _placeholder_dir(config) -> Path:
    base = Path.cwd()
    if config.source is not None:
        source = Path(config.source)
        parent = source.parent
        base = parent.parent if parent.name.lower() == "docs" else parent
        if not base.is_absolute():
            base = Path.cwd() / base
    return base / "results" / "placeholders"


def render_blocks(
    cell: ET.Element,
    config: ReportConfig,
    image_paragraphs: list[ET.Element] | None = None,
    styles: ReportStyleProfile | None = None,
    media: MediaContext | None = None,
) -> None:
    clear_cell(cell)
    images = list(image_paragraphs or [])
    styles = styles or config.styles
    for block in config.blocks:
        if block.kind == "image":
            if not images:
                raise RuntimeError("not enough existing image paragraphs to preserve")
            cell.append(deepcopy(images.pop(0)))
            continue
        if block.kind == "metrics":
            base = Path(config.source).parent if config.source is not None else None
            cell.append(make_paragraph(render_metrics_text(block, base=base), styles.body))
            continue
        if block.kind in ("figure", "figure_group"):
            if media is None:
                raise RuntimeError("figure block requires a media context (use build_report_package)")
            items = _figure_items(block)
            if len(items) > MAX_GROUP_COLUMNS:
                raise ValueError(f"figure group allows at most {MAX_GROUP_COLUMNS} images, got {len(items)}")
            total = _content_width_dxa(cell)
            column_inches = total / len(items) / 1440 - CELL_GAP_INCHES
            top: list[list[ET.Element]] = []
            bottom: list[list[ET.Element]] = []
            for item in items:
                raw = item.get("image")
                if not raw:
                    raise ValueError(f"figure block requires an image path: {str(item.get('text'))[:30]}")
                image_path = Path(str(raw))
                if not image_path.is_absolute():
                    # Relative figure paths are anchored to the config directory,
                    # so a config folder stays relocatable.
                    base = Path(config.source).parent if config.source is not None else Path.cwd()
                    image_path = base / image_path
                if not image_path.exists():
                    raise ResourceMissingError(f"figure image not found: {image_path}")
                width = float(item.get("width_inches") or column_inches)
                top.append([media.add_image(image_path, width)])
                caption = str(item.get("text") or "")
                bottom.append([make_paragraph(caption, styles.caption)] if caption else [])
            cell.append(make_group_table(top, bottom, total))
            cell.append(make_table_separator())
            continue
        if block.kind == "screenshot":
            if media is None:
                raise RuntimeError("screenshot block requires a media context (use build_report_package)")
            count = int(block.meta.get("images") or 1)
            if count < 1 or count > MAX_GROUP_COLUMNS:
                raise ValueError(f"screenshot allows 1..{MAX_GROUP_COLUMNS} placeholder images, got {count}")
            label = str(block.meta.get("label") or "运行截图")
            hint = str(block.meta.get("hint") or "")
            ratio = block.meta.get("ratio") or [16, 10]
            directory = _placeholder_dir(config)
            total = _content_width_dxa(cell)
            column_inches = total / count / 1440 - CELL_GAP_INCHES
            top = []
            for index in range(count):
                lines = [label]
                if hint:
                    lines.append(hint)
                if count > 1:
                    lines.append(f"第 {index + 1}/{count} 张")
                lines.append("比例 16:10 ｜ 右键 → 更改图片")
                image_path = make_placeholder_image(
                    directory / f"{label}_{index + 1}.png", lines, ratio=(int(ratio[0]), int(ratio[1]))
                )
                top.append([media.add_image(image_path, column_inches)])
            cell.append(
                make_group_table(
                    top, [[make_paragraph(block.text, styles.caption)]], total, merge_bottom=True
                )
            )
            cell.append(make_table_separator())
            continue
        if block.kind == "section":
            cell.append(make_paragraph(block.text, styles.section))
        elif block.kind == "subheading":
            cell.append(make_paragraph(block.text, styles.subheading))
        elif block.kind == "placeholder":
            cell.append(make_paragraph(block.text, styles.placeholder))
        elif block.kind == "caption":
            cell.append(make_paragraph(block.text, styles.caption))
        else:
            cell.append(make_paragraph(block.text, styles.body))
    if images:
        raise RuntimeError(f"unused image paragraphs remain: {len(images)}")
    if len(cell) and cell[-1].tag == w_tag("tbl"):
        cell.append(ET.Element(w_tag("p")))


def paragraph_has_image(p: ET.Element) -> bool:
    return any(local_name(node.tag) in {"drawing", "pict"} for node in p.iter())


def sanitize_image_paragraph(p: ET.Element) -> ET.Element:
    new_p = ET.Element(p.tag, p.attrib)
    p_pr = p.find(w_tag("pPr"))
    if p_pr is not None:
        new_p.append(deepcopy(p_pr))
    for child in p:
        if child.tag != w_tag("r"):
            continue
        if any(local_name(node.tag) in {"drawing", "pict"} for node in child.iter()):
            new_p.append(deepcopy(child))
    return new_p


def extract_image_paragraphs(cell: ET.Element) -> list[ET.Element]:
    images: list[ET.Element] = []
    for p in cell.findall(w_tag("p")):
        if paragraph_has_image(p):
            images.append(sanitize_image_paragraph(p))
    return images


def read_document_xml(docx_path: Path) -> tuple[bytes, list, dict[str, bytes]]:
    with ZipFile(docx_path) as zf:
        document_xml = zf.read("word/document.xml")
        infos = list(zf.infolist())
        other_files = {
            info.filename: zf.read(info.filename) for info in infos if info.filename != "word/document.xml"
        }
    return document_xml, infos, other_files


def write_document_xml(
    target_path: Path, infos: list, other_files: dict[str, bytes], document_xml: bytes
) -> None:
    with ZipFile(target_path, "w") as dst:
        written: set[str] = set()
        for info in infos:
            data = document_xml if info.filename == "word/document.xml" else other_files[info.filename]
            dst.writestr(info, data)
            written.add(info.filename)
        # 新增的包内文件（如 figure 块写入的 word/media/*）不在模板 infos 里，需要补写
        ref_date = infos[0].date_time if infos else (1980, 1, 1, 0, 0, 0)
        ref_type = infos[0].compress_type if infos else ZipInfo("x").compress_type
        for name, data in other_files.items():
            if name in written:
                continue
            # 用固定时间戳写入，保证同一份配置重复构建得到字节一致的 docx
            info = ZipInfo(name, date_time=ref_date)
            info.compress_type = ref_type
            dst.writestr(info, data)


def resolve_template_slots(
    body: ET.Element, config: ReportConfig
) -> tuple[ET.Element, ET.Element, ET.Element]:
    tables = body.findall(w_tag("tbl"))
    assumptions = config.assumptions
    if len(tables) < assumptions.required_table_count:
        raise TemplateError(
            "template document does not contain expected tables",
            hint="run `inspect-template` and update `assumptions` in the config",
        )
    cover_table = tables[assumptions.cover_table_index]
    report_table = tables[assumptions.report_table_index]
    cover_rows = cover_table.findall(w_tag("tr"))
    report_rows = report_table.findall(w_tag("tr"))
    if len(report_rows) <= assumptions.content_row:
        raise TemplateError(
            "report table row count is unexpected", hint="check assumptions.report_table_index / content_row"
        )
    report_name_cell = report_rows[assumptions.experiment_name_row].findall(w_tag("tc"))[
        assumptions.experiment_name_col
    ]
    content_cell = report_rows[assumptions.content_row].findall(w_tag("tc"))[assumptions.content_col]
    return cover_rows[0], report_name_cell, content_cell


def find_cover_title_paragraph(body: ET.Element) -> ET.Element | None:
    paras = body.findall(w_tag("p"))
    title_like = re.compile(r"^实验(?:[0-9]+|[一二三四五六七八九十]+|\*+)$")
    for paragraph in paras:
        text = "".join((t.text or "") for t in paragraph.findall(".//" + w_tag("t"))).strip()
        if title_like.match(text):
            return paragraph
    return paras[-1] if paras else None


def build_report_xml(template_path: Path, config: ReportConfig) -> bytes:
    document_xml, _, _ = read_document_xml(template_path)
    register_namespaces(document_xml)
    root = ET.fromstring(document_xml)
    body = root.find(w_tag("body"))
    if body is None:
        raise TemplateError("template document has no body")
    _, report_name_cell, content_cell = resolve_template_slots(body, config)
    title_paragraph = find_cover_title_paragraph(body)
    resolved = resolve_style_profile(
        config,
        template_cell=content_cell,
        template_title_paragraph=title_paragraph,
        template_experiment_name_cell=report_name_cell,
    )
    replace_cell_text(report_name_cell, config.experiment_name, resolved.styles.experiment_name)
    render_blocks(content_cell, config, styles=resolved.styles)
    update_cover_title(body, config.cover_title, resolved.styles.cover_title)
    serialized = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return restore_root_namespaces(serialized, document_xml)


def _find_document_root_tag(text: str) -> str:
    """返回 XML 文本里 <...document ...> 根标签（不用正则，避免转义坑）。"""
    idx = text.find("<")
    while idx != -1:
        end = text.find(">", idx)
        if end == -1:
            return ""
        tag = text[idx : end + 1]
        head = tag[1:].split(" ", 1)[0].rstrip(">").split(">")[0]
        if head.split(":")[-1] == "document":
            return tag
        idx = text.find("<", end)
    return ""


def restore_root_namespaces(serialized: bytes, original_bytes: bytes) -> bytes:
    """把模板根元素上声明的命名空间补回序列化结果。

    ElementTree 只输出「实际被元素/属性用到」的命名空间声明，会丢掉模板为兼容性
    声明的前缀（如 wp14 / w15 / wpc / o / m / v）。若根元素保留 mc:Ignorable 却引用了
    这些前缀，就构成 OOXML 规范违规，Word 会直接报「文件可能已经损坏」。
    """
    orig = original_bytes.decode("utf-8", "ignore")
    root_tag = _find_document_root_tag(orig)
    if not root_tag:
        return serialized
    decls = dict(re.findall(r'xmlns:([A-Za-z0-9_]+)="([^"]+)"', root_tag))
    default_ns = re.search(r'\sxmlns="([^"]+)"', root_tag)
    out = serialized.decode("utf-8")
    new_tag = _find_document_root_tag(out)
    if not new_tag or not decls:
        return serialized
    have = set(re.findall(r"xmlns:([A-Za-z0-9_]+)=", new_tag))
    inject = "".join(f' xmlns:{prefix}="{uri}"' for prefix, uri in decls.items() if prefix not in have)
    if default_ns and ' xmlns="' not in new_tag:
        inject += f' xmlns="{default_ns.group(1)}"'
    if not inject:
        return serialized
    patched_tag = new_tag[:-1] + inject + ">"
    return out.replace(new_tag, patched_tag, 1).encode("utf-8")


def build_report_package(template_path: Path, config: ReportConfig) -> tuple[bytes, dict[str, bytes]]:
    """单趟构建：返回 (document.xml 字节, 需要新增/替换的包内文件)。

    相比 build_report_xml，额外支持 kind: figure —— 图片写入 word/media/，
    并同步维护关系与内容类型，图片直接落在模板的正文单元格内。
    """
    document_xml, _, other_files = read_document_xml(template_path)
    register_namespaces(document_xml)
    root = ET.fromstring(document_xml)
    body = root.find(w_tag("body"))
    if body is None:
        raise TemplateError("template document has no body")
    _, report_name_cell, content_cell = resolve_template_slots(body, config)
    title_paragraph = find_cover_title_paragraph(body)
    resolved = resolve_style_profile(
        config,
        template_cell=content_cell,
        template_title_paragraph=title_paragraph,
        template_experiment_name_cell=report_name_cell,
    )
    replace_cell_text(report_name_cell, config.experiment_name, resolved.styles.experiment_name)
    media = MediaContext(other_files)
    render_blocks(content_cell, config, styles=resolved.styles, media=media)
    update_cover_title(body, config.cover_title, resolved.styles.cover_title)
    serialized = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return restore_root_namespaces(serialized, document_xml), media.collect()


def _page_break_runs(paragraph: ET.Element) -> list[ET.Element]:
    """收集段落里只起分页作用的 <w:r><w:br w:type="page"/></w:r>，重建段落时必须保留。

    Returns *sanitized* runs: only ``w:rPr`` + the page break are copied. Copying
    the original run wholesale used to drag its ``w:t`` along, so a template whose
    break run carried text ended up with two titles glued together
    (e.g. "实验一实验七") after ``update_cover_title``.
    """
    found: list[ET.Element] = []
    for child in paragraph:
        if child.tag != w_tag("r"):
            continue
        breaks = [br for br in child.findall(w_tag("br")) if br.get(w_tag("type")) == "page"]
        if not breaks:
            continue
        run = ET.Element(w_tag("r"))
        run_pr = child.find(w_tag("rPr"))
        if run_pr is not None:
            run.append(deepcopy(run_pr))
        for br in breaks:
            run.append(deepcopy(br))
        found.append(run)
    return found


def _rebuild_paragraph_keep_breaks(paragraph: ET.Element, text: str, style: ParagraphStyle) -> None:
    """用 style 重建段落文本，但保留原有的分页符（模板封面与正文之间的分页依赖它）。"""
    breaks = _page_break_runs(paragraph)
    for child in list(paragraph):
        paragraph.remove(child)
    for run in breaks:
        paragraph.append(run)
    new_p = make_paragraph(text, style)
    for child in list(new_p):
        paragraph.append(child)


def update_cover_title(body: ET.Element, title: str, style: ParagraphStyle) -> None:
    paras = body.findall(w_tag("p"))
    if not paras:
        raise TemplateError("document body has no title paragraph")
    title_like = re.compile(r"^实验(?:[0-9]+|[一二三四五六七八九十]+|\*+)$")
    matched = False
    for p in paras:
        text = "".join((t.text or "") for t in p.findall(".//" + w_tag("t"))).strip()
        if title_like.match(text):
            matched = True
            _rebuild_paragraph_keep_breaks(p, title, style)
    if matched:
        return
    title_para = paras[-1]
    _rebuild_paragraph_keep_breaks(title_para, title, style)
