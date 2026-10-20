from __future__ import annotations

"""生成本地占位图片（红色框 + 提示文字）。

为什么是图片而不是文字占位：
Word/WPS 的「更改图片」会保留图片对象的外框（宽/高/位置/环绕），
因此用「图片替换图片」可以保证替换后版式完全不变，而文字占位必须手调大小和位置。
"""

from pathlib import Path

RED = (214, 22, 22)
INK = (150, 16, 16)
BACKGROUND = (255, 250, 250)
FONT_CANDIDATES = (
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
)


def _load_font(size: int):
    from PIL import ImageFont

    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def _dashed_rect(draw, box, color, *, dash=28, gap=18, width=6):
    x0, y0, x1, y1 = box
    for x in range(x0, x1, dash + gap):
        draw.line([(x, y0), (min(x + dash, x1), y0)], fill=color, width=width)
        draw.line([(x, y1), (min(x + dash, x1), y1)], fill=color, width=width)
    for y in range(y0, y1, dash + gap):
        draw.line([(x0, y), (x0, min(y + dash, y1))], fill=color, width=width)
        draw.line([(x1, y), (x1, min(y + dash, y1))], fill=color, width=width)


def make_placeholder_image(path: Path, lines: list[str], *,
                           width_px: int = 1000, ratio: tuple[int, int] = (16, 10)) -> Path:
    """写出一张红色虚线框的占位图。lines 逐行居中显示。"""
    from PIL import Image, ImageDraw

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    height_px = int(round(width_px * ratio[1] / ratio[0]))
    image = Image.new("RGB", (width_px, height_px), BACKGROUND)
    draw = ImageDraw.Draw(image)
    _dashed_rect(draw, (8, 8, width_px - 9, height_px - 9), RED)

    title_font = _load_font(max(24, width_px // 20))
    body_font = _load_font(max(18, width_px // 34))

    rendered = []
    for index, line in enumerate(lines):
        rendered.append((line, title_font if index == 0 else body_font))

    heights = []
    for text, font in rendered:
        bbox = draw.textbbox((0, 0), text, font=font)
        heights.append(bbox[3] - bbox[1])
    step = max(heights) + int(width_px * 0.022)
    total = step * len(rendered)
    y = (height_px - total) // 2
    for (text, font), h in zip(rendered, heights):
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (width_px - (bbox[2] - bbox[0])) // 2
        colour = RED if font is title_font else INK
        draw.text((x, y), text, font=font, fill=colour)
        y += step

    image.save(path, format="PNG", optimize=True)
    return path
