"""生成本地占位图片（红色框 + 提示文字）。

为什么是图片而不是文字占位：
Word/WPS 的「更改图片」会保留图片对象的外框（宽/高/位置/环绕），
因此用「图片替换图片」可以保证替换后版式完全不变，而文字占位必须手调大小和位置。
"""

from __future__ import annotations

import os
from pathlib import Path

RED = (214, 22, 22)
INK = (150, 16, 16)
BACKGROUND = (255, 250, 250)

#: 环境变量：显式指定占位图字体文件，优先级高于内置候选。
FONT_ENV_VAR = "DOCX_REPORT_PLACEHOLDER_FONT"

#: 跨平台中文字体候选。找不到任何一个时回退 Pillow 内置位图字体
#: （英文仍可读，中文会显示为方块，届时用 DOCX_REPORT_PLACEHOLDER_FONT 指定）。
FONT_CANDIDATES = (
    # Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    # Windows
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
)


def resolve_font_candidates(explicit: str | Path | None = None) -> tuple[str, ...]:
    """返回字体查找顺序：显式参数 → 环境变量 → 内置候选。"""
    ordered: list[str] = []
    if explicit:
        ordered.append(str(explicit))
    env_value = os.environ.get(FONT_ENV_VAR)
    if env_value:
        ordered.append(env_value)
    ordered.extend(FONT_CANDIDATES)
    return tuple(ordered)


def _load_font(size: int, font_path: str | Path | None = None):
    from PIL import ImageFont

    for candidate in resolve_font_candidates(font_path):
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:  # noqa: BLE001 - 字体损坏时继续找下一个候选
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


def make_placeholder_image(
    path: Path,
    lines: list[str],
    *,
    width_px: int = 1000,
    ratio: tuple[int, int] = (16, 10),
    font_path: str | Path | None = None,
) -> Path:
    """写出一张红色虚线框的占位图。lines 逐行居中显示。"""
    from PIL import Image, ImageDraw

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    height_px = int(round(width_px * ratio[1] / ratio[0]))
    image = Image.new("RGB", (width_px, height_px), BACKGROUND)
    draw = ImageDraw.Draw(image)
    _dashed_rect(draw, (8, 8, width_px - 9, height_px - 9), RED)

    title_font = _load_font(max(24, width_px // 20), font_path)
    body_font = _load_font(max(18, width_px // 34), font_path)

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
    for (text, font), _h in zip(rendered, heights, strict=False):
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (width_px - (bbox[2] - bbox[0])) // 2
        colour = RED if font is title_font else INK
        draw.text((x, y), text, font=font, fill=colour)
        y += step

    image.save(path, format="PNG", optimize=True)
    return path
