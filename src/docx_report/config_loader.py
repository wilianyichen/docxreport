from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from .course_profile import merge_style_resolution, profile_style_mapping, resolve_course_profile
from .errors import ConfigInvalidError, ConfigReadError, ConfigWrongTypeError
from .models import (
    EnrichmentAction,
    EnrichmentConfig,
    ParagraphStyle,
    ReportBlock,
    ReportConfig,
    ReportStyleProfile,
    StyleResolutionRules,
    TemplateLayoutAssumptions,
)

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None


def _resolve_relative(config_path: Path, value: str | Path) -> Path:
    """Resolve a path from the config file relative to the config's own directory.

    This makes a config directory relocatable: ``template: ../模板.docx`` and
    ``output: out/report.docx`` mean the same thing no matter which cwd the CLI
    runs in. Absolute paths are returned untouched.
    """
    path = Path(str(value))
    if path.is_absolute():
        return path
    return (Path(config_path).parent / path).resolve()


def load_report_config(path: Path) -> ReportConfig:
    raw = _load_report_mapping(path)
    if isinstance(raw.get("actions"), list) and not raw.get("blocks"):
        raise ConfigWrongTypeError(
            f"{path}: looks like an enrich config, not a report config",
            hint="pass this file to an enrich-targeting command, or add `blocks:` to it",
        )
    blocks_raw = raw.get("blocks")
    if not isinstance(blocks_raw, list) or not blocks_raw:
        raise ConfigInvalidError(
            f"{path}: missing blocks for report config",
            hint="a report config needs a non-empty `blocks:` list",
        )
    blocks = [
        ReportBlock(
            kind=str(block["kind"]),
            text=str(block.get("text", "")),
            meta=_extra_keys(block, {"kind", "text"}),
        )
        for block in blocks_raw
    ]
    if not raw.get("output"):
        raise ConfigInvalidError(f"{path}: missing output", hint="a report config needs an `output:` path")
    assumptions = _load_assumptions(raw.get("assumptions"))
    profile_raw, profile_path = resolve_course_profile(raw, path)
    if profile_path is not None:
        raw["_course_profile_resolved"] = str(profile_path)
    styles = _load_styles(profile_style_mapping(profile_raw))
    styles = _load_styles(raw.get("styles"), base=styles)
    style_resolution = _load_style_resolution(
        merge_style_resolution(profile_raw, raw.get("style_resolution"))
    )
    return ReportConfig(
        name=str(raw.get("name") or path.parent.name or path.stem),
        backend=str(raw.get("backend") or "ooxml-template"),
        template=_resolve_relative(path, raw["template"]) if raw.get("template") else None,
        output=_resolve_relative(path, raw["output"]),
        cover_title=str(raw.get("cover_title") or ""),
        experiment_name=str(raw.get("experiment_name") or ""),
        blocks=blocks,
        expected_images=int(raw["expected_images"]) if raw.get("expected_images") is not None else None,
        assumptions=assumptions,
        styles=styles,
        style_resolution=style_resolution,
        source=path,
        extras=_extra_keys(
            raw,
            {
                "name",
                "backend",
                "template",
                "output",
                "cover_title",
                "experiment_name",
                "blocks",
                "expected_images",
                "assumptions",
                "styles",
                "style_resolution",
            },
        ),
    )


def load_enrichment_config(path: Path) -> EnrichmentConfig:
    raw = _load_mapping(path)
    if isinstance(raw.get("blocks"), list) and not raw.get("actions"):
        raise ConfigWrongTypeError(
            f"{path}: looks like a report config, not an enrich config",
            hint="pass this file to a report-targeting command, or add `actions:` to it",
        )
    actions_raw = raw.get("actions")
    if not isinstance(actions_raw, list) or not actions_raw:
        raise ConfigInvalidError(
            f"{path}: missing actions for enrich config",
            hint="an enrich config needs a non-empty `actions:` list",
        )
    actions = [
        EnrichmentAction(
            action=str(action["action"]),
            anchor=str(action["anchor"]) if action.get("anchor") else None,
            image=Path(action["image"]) if action.get("image") else None,
            caption=str(action.get("caption") or ""),
            width_inches=float(action["width_inches"]) if action.get("width_inches") is not None else None,
            extras=_extra_keys(action, {"action", "anchor", "image", "caption", "width_inches"}),
        )
        for action in actions_raw
    ]
    return EnrichmentConfig(
        name=str(raw.get("name") or path.parent.name or path.stem),
        output=_resolve_relative(path, raw["output"]) if raw.get("output") else None,
        actions=actions,
        source=path,
        extras=_extra_keys(raw, {"name", "output", "actions"}),
    )


def _load_report_mapping(path: Path) -> dict[str, Any]:
    raw = _load_mapping(path)
    extends = raw.get("extends")
    if not extends:
        return raw
    extends_path = Path(str(extends))
    if not extends_path.is_absolute():
        extends_path = path.parent / extends_path
    base = _load_report_mapping(extends_path)
    merged = _deep_merge_mappings(base, raw)
    merged.pop("extends", None)
    return merged


def _load_mapping(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise ConfigReadError(
            f"config not found: {path}", hint="check the path, or run `doctor` from the config directory"
        )
    suffix = path.suffix.lower()
    if suffix in {".yml", ".yaml"}:
        if yaml is None:
            raise ConfigReadError("PyYAML is required to read YAML report configs", hint="pip install PyYAML")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ConfigReadError(f"{path}: expected top-level mapping")
        return data
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ConfigReadError(f"{path}: expected top-level mapping")
        return data
    if suffix == ".py":
        return _load_python_mapping(path)
    raise ConfigReadError(f"Unsupported config format: {path}", hint="use .yml, .yaml, .json or .py")


def _load_python_mapping(path: Path) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ConfigReadError(f"Could not import config module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    candidates = [
        getattr(module, "REPORT_CONFIG", None),
        getattr(module, "EXPERIMENT_6_CONFIG", None),
    ]
    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate
    for value in module.__dict__.values():
        if isinstance(value, dict) and {"output", "blocks"} <= set(value.keys()):
            return value
    raise ConfigInvalidError(
        f"{path}: no report config mapping found", hint="export REPORT_CONFIG = {...} from the module"
    )


def _load_assumptions(raw: Any) -> TemplateLayoutAssumptions:
    if raw is None:
        return TemplateLayoutAssumptions()
    if not isinstance(raw, dict):
        raise ConfigInvalidError(f"assumptions must be a mapping, got: {type(raw).__name__}")
    data = TemplateLayoutAssumptions()
    for key, value in raw.items():
        if not hasattr(data, key):
            continue
        setattr(data, key, int(value))
    return data


def _load_styles(raw: Any, base: ReportStyleProfile | None = None) -> ReportStyleProfile:
    if raw is None:
        return base if base is not None else ReportStyleProfile()
    if not isinstance(raw, dict):
        raise ConfigInvalidError(f"styles must be a mapping, got: {type(raw).__name__}")
    profile = base if base is not None else ReportStyleProfile()
    for key, value in raw.items():
        if not hasattr(profile, key):
            continue
        current = getattr(profile, key)
        if not isinstance(value, dict):
            raise ConfigInvalidError(f"styles.{key} must be a mapping")
        setattr(profile, key, _merge_paragraph_style(current, value))
    return profile


def _load_style_resolution(raw: Any) -> StyleResolutionRules:
    if raw is None:
        return StyleResolutionRules()
    if not isinstance(raw, dict):
        raise ConfigInvalidError(f"style_resolution must be a mapping, got: {type(raw).__name__}")
    rules = StyleResolutionRules()
    mapping = {
        "comment_patterns": "comment_patterns",
        "cover_title_patterns": "cover_title_patterns",
        "experiment_name_patterns": "experiment_name_patterns",
        "section_patterns": "section_patterns",
        "subheading_patterns": "subheading_patterns",
        "placeholder_patterns": "placeholder_patterns",
        "body_patterns": "body_patterns",
        "cover_title_include_patterns": "cover_title_include_patterns",
        "cover_title_exclude_patterns": "cover_title_exclude_patterns",
        "experiment_name_include_patterns": "experiment_name_include_patterns",
        "experiment_name_exclude_patterns": "experiment_name_exclude_patterns",
        "section_include_patterns": "section_include_patterns",
        "section_exclude_patterns": "section_exclude_patterns",
        "subheading_include_patterns": "subheading_include_patterns",
        "subheading_exclude_patterns": "subheading_exclude_patterns",
        "body_include_patterns": "body_include_patterns",
        "body_exclude_patterns": "body_exclude_patterns",
        "placeholder_include_patterns": "placeholder_include_patterns",
        "placeholder_exclude_patterns": "placeholder_exclude_patterns",
        "cover_title": "cover_title_prefer",
        "experiment_name": "experiment_name_prefer",
        "section": "section_prefer",
        "subheading": "subheading_prefer",
        "body": "body_prefer",
        "placeholder": "placeholder_prefer",
        "caption": "caption_prefer",
        "require_cover_title_source": "require_cover_title_source",
        "require_experiment_name_source": "require_experiment_name_source",
        "require_section_source": "require_section_source",
        "require_subheading_source": "require_subheading_source",
        "require_body_source": "require_body_source",
        "require_placeholder_source": "require_placeholder_source",
    }
    bool_keys = {
        "require_cover_title_source",
        "require_experiment_name_source",
        "require_section_source",
        "require_subheading_source",
        "require_body_source",
        "require_placeholder_source",
    }
    for raw_key, attr in mapping.items():
        if raw_key not in raw:
            continue
        value = raw[raw_key]
        if raw_key in bool_keys:
            setattr(rules, attr, bool(value))
            continue
        if not isinstance(value, list):
            raise ConfigInvalidError(f"style_resolution.{raw_key} must be a list")
        setattr(rules, attr, [str(item) for item in value])
    return rules


def _merge_paragraph_style(style: ParagraphStyle, raw: dict[str, Any]) -> ParagraphStyle:
    data = ParagraphStyle(
        ascii_font=style.ascii_font,
        hansi_font=style.hansi_font,
        east_asia_font=style.east_asia_font,
        cs_font=style.cs_font,
        size=style.size,
        bold=style.bold,
        color=style.color,
        align=style.align,
        spacing_after=style.spacing_after,
        spacing_line=style.spacing_line,
        spacing_line_rule=style.spacing_line_rule,
    )
    for key, value in raw.items():
        if key == "font":  # 简写：一次性设置西文/中文/复杂文种字体
            for attr in ("ascii_font", "hansi_font", "east_asia_font"):
                setattr(data, attr, str(value))
            continue
        if not hasattr(data, key):
            continue
        if key in {"size", "spacing_after", "spacing_line"}:
            setattr(data, key, int(value))
        elif key == "bold":
            setattr(data, key, bool(value))
        else:
            setattr(data, key, None if value is None else str(value))
    return data


def _deep_merge_mappings(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key == "extends":
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_mappings(merged[key], value)
        else:
            merged[key] = value
    return merged


def _extra_keys(raw: dict[str, Any], known: set[str]) -> dict[str, Any]:
    return {key: value for key, value in raw.items() if key not in known}
