#!/usr/bin/env python3
"""Skill entry point — a thin shim over :mod:`docx_report.cli`.

Kept at a stable path because agent instructions and existing project scripts
reference it. All behaviour lives in the package, so this file and the
``docx-report`` console script can never diverge.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if (_SRC / "docx_report" / "__init__.py").exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from docx_report.cli import main  # noqa: E402 - path bootstrap must run first

if __name__ == "__main__":
    sys.exit(main())
