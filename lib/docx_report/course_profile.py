from __future__ import annotations

"""课程报告范式（Course Report Profile）的发现与加载。

身份标识：文件内必须有 `kind: course-report-profile`。

合并优先级（越靠右越高）：
    skill 内置默认  <  课程范式文件  <  单次实验 report config

查找规则：从 report config 所在目录逐级向上（最多 6 层）查找，
先认约定文件名，再浅扫同目录下任意 *.yml / *.yaml 的 kind 字段。
"""

import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None

COURSE_PROFILE_KIND = "course-report-profile"

COURSE_PROFILE_NAMES = (
    "课程报告范式.yml",
    "课程报告范式.yaml",
    "课程报告范式.json",
    "course-report-profile.yml",
    "course-report-profile.yaml",
    "course_report_profile.yml",
    "course_report_profile.yaml",
)


def read_structured_file(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    if yaml is None:
        raise RuntimeError(f"PyYAML is required to read {path}")
    return yaml.safe_load(text)


def is_course_profile(raw: Any) -> bool:
    return isinstance(raw, dict) and str(raw.get("kind", "")).strip() == COURSE_PROFILE_KIND


def _looks_like_course_profile(path: Path) -> bool:
    try:
        return is_course_profile(read_structured_file(path))
    except Exception:
        return False


def find_course_profile(start: Path, max_levels: int = 6) -> Path | None:
    cur = start.resolve()
    if cur.is_file():
        cur = cur.parent
    for _ in range(max_levels):
        for name in COURSE_PROFILE_NAMES:
            cand = cur / name
            if cand.is_file() and _looks_like_course_profile(cand):
                return cand
        scanned = 0
        for cand in sorted(list(cur.glob("*.yml")) + list(cur.glob("*.yaml"))):
            if cand.name in COURSE_PROFILE_NAMES:
                continue
            scanned += 1
            if scanned > 60:
                break
            if _looks_like_course_profile(cand):
                return cand
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def resolve_course_profile(raw: dict[str, Any], config_path: Path) -> tuple[dict | None, Path | None]:
    """返回 (范式内容, 范式路径)。支持 config 里 course_profile 显式指定。"""
    explicit = raw.get("course_profile")
    if explicit:
        cand = Path(str(explicit))
        if not cand.is_absolute():
            cand = (config_path.parent / cand).resolve()
        if not cand.is_file():
            raise ValueError(f"course_profile not found: {cand}")
        data = read_structured_file(cand)
        if not is_course_profile(data):
            raise ValueError(f"{cand}: kind != '{COURSE_PROFILE_KIND}'")
        return data, cand
    found = find_course_profile(config_path.parent)
    if found is None:
        return None, None
    return read_structured_file(found), found


def profile_style_mapping(profile_raw: dict | None) -> dict[str, Any] | None:
    """把课程范式的 styles + spacing 转成 _load_styles 可消费的样式映射。"""
    if not isinstance(profile_raw, dict):
        return None
    styles = profile_raw.get("styles")
    if not isinstance(styles, dict):
        return None
    spacing = profile_raw.get("spacing") if isinstance(profile_raw.get("spacing"), dict) else {}
    text_line = spacing.get("text_line")
    caption_line = spacing.get("caption_line")
    after = spacing.get("spacing_after")
    out: dict[str, Any] = {}
    for role, cfg in styles.items():
        if not isinstance(cfg, dict):
            continue
        cfg = dict(cfg)
        if "spacing_line" not in cfg:
            line = caption_line if role == "caption" and caption_line is not None else text_line
            if line is not None:
                cfg["spacing_line"] = int(line)
        if "spacing_after" not in cfg and after is not None:
            cfg["spacing_after"] = int(after)
        out[role] = cfg
    return out


def merge_style_resolution(profile_raw: dict | None, config_rules: Any) -> dict | None:
    """课程范式提供基础 donor 规则，单次 config 逐键覆盖。"""
    merged: dict[str, Any] = {}
    if isinstance(profile_raw, dict) and isinstance(profile_raw.get("style_resolution"), dict):
        merged.update(profile_raw["style_resolution"])
    if isinstance(config_rules, dict):
        merged.update(config_rules)
    return merged or None
