"""Build a throw-away .docx template that satisfies the fixed-table assumptions.

Why generate instead of committing a .docx: the project must not redistribute any
course template. The real implementation lives in `docx_report.testing` so that
downstream projects and `examples/` can reuse it.

Run standalone to inspect it:

    python tests/fixtures/build_fixture_template.py out/template.docx
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from docx_report.testing import build_minimal_template


def build(path: str | Path) -> Path:
    """Create the minimal two-table template at ``path``."""
    return build_minimal_template(path)


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "template.docx")
    print(build(target))
