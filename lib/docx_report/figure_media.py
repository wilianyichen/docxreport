from __future__ import annotations

"""为 ooxml 单趟构建提供「内嵌图片」能力。

背景：
    - `enrich` 走的是 python-docx，`doc.add_paragraph()` 会把内容加到**表格外**，
      而实验报告正文位于模板的表格单元格内；且它给 caption 时图注会插到图片上方。
    - 因此新增 `kind: figure` 块，由本模块在 document.xml 内直接生成 drawing，
      图片写回同一 docx 包的 word/media/ 并注册关系与内容类型。

用法：
    ctx = MediaContext(other_files)
    p = ctx.make_figure_paragraph(image_path, width_inches=5.2, name="图1")
    cell.append(p)
    extra_parts = ctx.collect()
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

EMU_PER_INCH = 914400

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
PR_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

for _prefix, _ns in (("w", W_NS), ("wp", WP_NS), ("a", A_NS), ("pic", PIC_NS), ("r", R_NS),
                     ("ct", CT_NS), ("pr", PR_NS)):
    ET.register_namespace(_prefix, _ns)

_CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
    "emf": "image/x-emf",
    "wmf": "image/x-wmf",
}


def _w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _png_size(data: bytes) -> tuple[int, int] | None:
    """无 Pillow 时直接从 PNG IHDR / JPEG SOF 读尺寸。"""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB):
                h = int.from_bytes(data[i + 5:i + 7], "big")
                w = int.from_bytes(data[i + 7:i + 9], "big")
                return w, h
            seg = int.from_bytes(data[i + 2:i + 4], "big")
            i += 2 + seg
    return None


def image_pixel_size(data: bytes) -> tuple[int, int] | None:
    try:
        from PIL import Image  # type: ignore
        import io

        with Image.open(io.BytesIO(data)) as im:
            return im.width, im.height
    except Exception:
        return _png_size(data)


class MediaContext:
    """在 build 过程中累积新的媒体文件、关系与内容类型。"""

    def __init__(self, other_files: dict[str, bytes]) -> None:
        self._other = other_files
        self._added: dict[str, bytes] = {}
        self._rels_path = "word/_rels/document.xml.rels"
        raw_rels = other_files.get(self._rels_path)
        if raw_rels is None:
            raise RuntimeError(f"template is missing {self._rels_path}")
        # 关键：保留原部件的字节级文本，只用字符串注入新增条目。
        # 若用 ElementTree 解析再序列化，默认命名空间会变成前缀（<ct:Types>/<pr:Relationships>），
        # XML 声明也会变化，Word 的 OPC 读取器会直接判定「文件已损坏」。
        self._rels_text = raw_rels.decode("utf-8")
        nums = [int(m.group(1)) for m in re.finditer(r'Id="rId(\d+)"', self._rels_text)]
        self._next_rid = max(nums, default=0) + 1
        self._new_rel_xml: list[str] = []
        existing_media = [n for n in other_files if n.startswith("word/media/")]
        nums = [int(m.group(1)) for n in existing_media
                if (m := re.fullmatch(r"word/media/dsh_image(\d+)\.\w+", n))]
        self._next_media = max(nums, default=0) + 1
        self._next_docpr = 1000
        self._ct_path = "[Content_Types].xml"
        raw_ct = other_files.get(self._ct_path)
        self._ct_text = raw_ct.decode("utf-8") if raw_ct else None
        self._new_ct_xml: list[str] = []
        self._ensure_extensions()

    def _ensure_extensions(self) -> None:
        if not self._ct_text:
            return
        have = {h.lower() for h in re.findall(r'Extension="([^"]+)"', self._ct_text)}
        for ext, ctype in _CONTENT_TYPES.items():
            if ext in have:
                continue
            self._new_ct_xml.append(f'<Default Extension="{ext}" ContentType="{ctype}"/>')

    def _add_relationship(self, target: str, rel_type: str) -> str:
        rid = f"rId{self._next_rid}"
        self._next_rid += 1
        self._new_rel_xml.append(
            f'<Relationship Id="{rid}" Type="{rel_type}" Target="{target}"/>')
        return rid

    def add_image(self, image_path: Path, width_inches: float) -> ET.Element:
        """把图片登记进包，返回 <w:p> 图片段落（居中）。"""
        data = Path(image_path).read_bytes()
        ext = Path(image_path).suffix.lower().lstrip(".") or "png"
        if ext not in _CONTENT_TYPES:
            ext = "png"
        media_name = f"word/media/dsh_image{self._next_media}.{ext}"
        self._next_media += 1
        self._added[media_name] = data
        rid = self._add_relationship(f"media/{Path(media_name).name}",
                                     f"{R_NS}/image")

        size = image_pixel_size(data) or (1600, 1200)
        w_px, h_px = size
        width_emu = int(float(width_inches) * EMU_PER_INCH)
        height_emu = int(width_emu * h_px / w_px) if w_px else int(width_emu * 0.75)

        docpr_id = self._next_docpr
        self._next_docpr += 1

        p = ET.Element(_w("p"))
        p_pr = ET.SubElement(p, _w("pPr"))
        spacing = ET.SubElement(p_pr, _w("spacing"))
        spacing.set(_w("after"), "60")
        spacing.set(_w("line"), "240")
        spacing.set(_w("lineRule"), "auto")
        jc = ET.SubElement(p_pr, _w("jc"))
        jc.set(_w("val"), "center")

        r = ET.SubElement(p, _w("r"))
        drawing = ET.SubElement(r, _w("drawing"))
        inline = ET.SubElement(drawing, f"{{{WP_NS}}}inline")
        for k in ("distT", "distB", "distL", "distR"):
            inline.set(k, "0")
        extent = ET.SubElement(inline, f"{{{WP_NS}}}extent")
        extent.set("cx", str(width_emu))
        extent.set("cy", str(height_emu))
        etree_docpr = ET.SubElement(inline, f"{{{WP_NS}}}docPr")
        etree_docpr.set("id", str(docpr_id))
        etree_docpr.set("name", f"Figure {docpr_id}")
        graphic = ET.SubElement(inline, f"{{{A_NS}}}graphic")
        gd = ET.SubElement(graphic, f"{{{A_NS}}}graphicData")
        gd.set("uri", f"{PIC_NS}")
        pic = ET.SubElement(gd, f"{{{PIC_NS}}}pic")
        nv = ET.SubElement(pic, f"{{{PIC_NS}}}nvPicPr")
        cnv = ET.SubElement(nv, f"{{{PIC_NS}}}cNvPr")
        cnv.set("id", str(docpr_id))
        cnv.set("name", Path(image_path).name)
        ET.SubElement(nv, f"{{{PIC_NS}}}cNvPicPr")
        blip_fill = ET.SubElement(pic, f"{{{PIC_NS}}}blipFill")
        blip = ET.SubElement(blip_fill, f"{{{A_NS}}}blip")
        blip.set(f"{{{R_NS}}}embed", rid)
        stretch = ET.SubElement(blip_fill, f"{{{A_NS}}}stretch")
        ET.SubElement(stretch, f"{{{A_NS}}}fillRect")
        sp_pr = ET.SubElement(pic, f"{{{PIC_NS}}}spPr")
        xfrm = ET.SubElement(sp_pr, f"{{{A_NS}}}xfrm")
        off = ET.SubElement(xfrm, f"{{{A_NS}}}off")
        off.set("x", "0")
        off.set("y", "0")
        ext_node = ET.SubElement(xfrm, f"{{{A_NS}}}ext")
        ext_node.set("cx", str(width_emu))
        ext_node.set("cy", str(height_emu))
        prst = ET.SubElement(sp_pr, f"{{{A_NS}}}prstGeom")
        prst.set("prst", "rect")
        ET.SubElement(prst, f"{{{A_NS}}}avLst")
        return p

    def collect(self) -> dict[str, bytes]:
        out: dict[str, bytes] = {}
        if not self._added:
            return out
        out.update(self._added)
        out[self._rels_path] = self._rels_text.replace(
            "</Relationships>", "".join(self._new_rel_xml) + "</Relationships>").encode("utf-8")
        if self._ct_text is not None:
            out[self._ct_path] = self._ct_text.replace(
                "</Types>", "".join(self._new_ct_xml) + "</Types>").encode("utf-8")
        return out
