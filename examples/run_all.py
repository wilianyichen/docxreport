"""Run every example pipeline end to end into ``examples/out/``.

    python examples/run_all.py

Exits non-zero on the first failing step. No network, no Microsoft Word, no
committed binary assets: the template, figures, metrics and log are generated
here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "src"))

from docx_report.api import (  # noqa: E402 - path bootstrap
    build_report,
    enrich_report,
    revise_report,
    validate_report,
)
from docx_report.testing import build_minimal_template  # noqa: E402
from docx_report.verify import verify_document  # noqa: E402

OUT = ROOT / "out"


def prepare_assets() -> None:
    from PIL import Image

    OUT.mkdir(parents=True, exist_ok=True)
    build_minimal_template(ROOT / "template.docx")
    if not (OUT / "fig1.png").exists():
        Image.new("RGB", (320, 200), (30, 90, 160)).save(OUT / "fig1.png")
    if not (OUT / "fig2.png").exists():
        Image.new("RGB", (200, 320), (160, 90, 30)).save(OUT / "fig2.png")
    (OUT / "metrics.json").write_text(
        json.dumps({"test": {"accuracy": 0.9234, "samples": 128}}, indent=2),
        encoding="utf-8",
    )
    (OUT / "run.log").write_text(
        "$ jupyter nbconvert --execute --inplace nb.ipynb\n"
        "[NbConvertApp] Converting notebook nb.ipynb to notebook\n"
        "[NbConvertApp] Executing notebook with kernel: python3\n"
        "[NbConvertApp] Writing 48213 bytes to nb.ipynb\n",
        encoding="utf-8",
    )


def report(title: str, docx: Path, config: Path) -> None:
    validation = validate_report(config, docx)
    if not validation.ok:
        raise SystemExit(f"{title}: validate failed\n" + "\n".join(validation.summary_lines()))
    lines = verify_document(docx, config)
    figure_line = next((ln.strip() for ln in lines if "figure_group_tables" in ln), "")
    print(f"  {title}: {docx.relative_to(ROOT)}  ok")
    if figure_line:
        print(f"    {figure_line}")


def main() -> int:
    prepare_assets()

    print("[01-build] build a report from the minimal template")
    built = build_report(ROOT / "01-build" / "report.yml")
    report("build", built, ROOT / "01-build" / "report.yml")

    print("[02-revise] update the report without losing images")
    revised = revise_report(ROOT / "02-revise" / "report.yml", built)
    report("revise", revised, ROOT / "02-revise" / "report.yml")

    print("[03-enrich] append an appendix and insert an anchored figure")
    enriched = enrich_report(ROOT / "03-enrich" / "finalize.yml", built)
    report("enrich", enriched, ROOT / "03-enrich" / "finalize.yml")

    print("[04-course-profile] inherit a course profile")
    from_profile = build_report(ROOT / "04-course-profile" / "exp1" / "report.yml")
    report("course-profile", from_profile, ROOT / "04-course-profile" / "exp1" / "report.yml")

    print("\nall examples passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
