#!/usr/bin/env python3
"""Print a compact summary of a report or enrich config."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

_cwd = Path.cwd()
for _parent in [_cwd, *_cwd.parents]:
    if (_parent / 'docx_report' / '__init__.py').exists():
        PROJECT_ROOT = _parent
        break
else:
    PROJECT_ROOT = _cwd
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from docx_report import generate_screenshot_plan, preview_config, summarize_report_patterns


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview a report or enrich config")
    parser.add_argument("config", type=Path)
    parser.add_argument("--show-patterns", action="store_true", help="Print common vs specific workflow summary for report configs")
    parser.add_argument("--show-screenshots", action="store_true", help="Print placeholder-derived screenshot plan for report configs")
    parser.add_argument("--json", action="store_true", help="Print the base preview as JSON")
    args = parser.parse_args()

    preview = preview_config(args.config)
    if args.json:
        print(json.dumps(preview, ensure_ascii=False, indent=2))
    else:
        for key, value in preview.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for sub_key, sub_value in sorted(value.items()):
                    print(f"  - {sub_key}: {sub_value}")
            elif isinstance(value, list):
                print(f"{key}:")
                for item in value:
                    print(f"  - {item}")
            else:
                print(f"{key}: {value}")

    if preview["type"] == "report" and args.show_patterns:
        print("patterns:")
        print(json.dumps(summarize_report_patterns(args.config), ensure_ascii=False, indent=2))

    if preview["type"] == "report" and args.show_screenshots:
        print("screenshot_plan:")
        print(json.dumps(generate_screenshot_plan(args.config), ensure_ascii=False, indent=2))

    if preview["type"] != "report" and (args.show_patterns or args.show_screenshots):
        print("note: patterns/screenshot plan are only available for report configs")


if __name__ == "__main__":
    main()
