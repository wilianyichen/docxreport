#!/usr/bin/env python3
"""Deprecated: use ``docx-report inspect-template <template.docx>`` instead."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if (_SRC / "docx_report" / "__init__.py").exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from docx_report.cli import main  # noqa: E402

DEPRECATION = "warning: scripts/inspect_docx_template.py is deprecated; use `docx-report inspect-template`"

if __name__ == "__main__":
    print(DEPRECATION, file=sys.stderr)
    sys.exit(main(["inspect-template", *sys.argv[1:]]))
