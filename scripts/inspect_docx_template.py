#!/usr/bin/env python3
"""Inspect the fixed-table assumptions of a DOCX template."""

from __future__ import annotations

import argparse
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

from docx_report.models import TemplateLayoutAssumptions
from docx_report.validators import validate_template_layout


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect DOCX template layout assumptions")
    parser.add_argument("template", type=Path)
    args = parser.parse_args()

    result = validate_template_layout(args.template, TemplateLayoutAssumptions())
    for line in result.summary_lines():
        print(line)


if __name__ == "__main__":
    main()
