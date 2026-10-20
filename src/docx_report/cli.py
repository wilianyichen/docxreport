"""Command-line interface for docx_report.

Single source of truth for every documented command. ``scripts/skill_entry.py``
is a thin shim around :func:`main`, so the skill and the ``docx-report`` console
script can never drift apart again.

Exit codes (stable contract, see also ``docx_report.errors``):

* ``0`` success, or a check that passed
* ``2`` a check ran and reported "not ready" (findings are printed, not raised)
* ``3`` operational error (missing config/resource, bad template, ...)
* ``1`` unexpected error (bug)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .api import (
    build_report,
    doctor_config,
    enrich_report,
    generate_screenshot_plan,
    preview_config,
    revise_report,
    summarize_report_patterns,
    validate_report,
)
from .artifact_check import check_artifacts, referenced_images_from_config
from .errors import EXIT_CHECK_FAILED, EXIT_OK, DocxReportError
from .experiment_readiness import check_experiment_readiness
from .models import TemplateLayoutAssumptions
from .notebook_check import check_notebook, check_notebook_pair
from .notebook_scaffold import scaffold_notebook
from .pdf_export import export_pdf
from .scaffold import scaffold_report_config
from .validators import validate_template_layout
from .verify import verify_document

PROG = "docx-report"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _emit(lines: list[str], *, as_json: bool, ok: bool, code: str, extra: dict | None = None) -> None:
    if as_json:
        payload = {"ok": ok, "code": code, "lines": lines}
        if extra:
            payload.update(extra)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for line in lines:
            print(line)


def _print_preview(config_path: Path, *, show_patterns: bool, show_screenshots: bool, as_json: bool) -> None:
    preview = preview_config(config_path)
    if as_json:
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

    if preview["type"] == "report" and show_patterns:
        print("patterns:")
        print(json.dumps(summarize_report_patterns(config_path), ensure_ascii=False, indent=2))

    if preview["type"] == "report" and show_screenshots:
        print("screenshot_plan:")
        print(json.dumps(generate_screenshot_plan(config_path), ensure_ascii=False, indent=2))

    if preview["type"] != "report" and (show_patterns or show_screenshots):
        print("note: patterns/screenshot plan are only available for report configs")


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Template-driven experiment-report builder: build, revise (screenshot-safe), "
        "enrich, validate and export DOCX reports.",
        epilog="Start with `doctor <config>`: it inspects the config, the template and the referenced "
        "resources, then prints the exact next command.",
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    p = sub.add_parser("doctor", help="Inspect a config and suggest the next command")
    p.add_argument("config", type=Path, help="report.yml or enrich/finalize.yml")
    p.add_argument("input_docx", type=Path, nargs="?", help="optional existing docx to inspect")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("build", help="Build a new report skeleton from a template")
    p.add_argument("config", type=Path, help="report config")
    p.add_argument("--output", type=Path, help="override config output path")

    p = sub.add_parser("revise", help="Update an existing report while preserving inserted images")
    p.add_argument("config", type=Path, help="report config")
    p.add_argument("input_docx", type=Path, help="existing report to revise")
    p.add_argument("--output", type=Path, help="override config output path")

    p = sub.add_parser("enrich", help="Insert figures/appendices into an existing report")
    p.add_argument("config", type=Path, help="enrich (actions) config")
    p.add_argument("input_docx", type=Path, help="existing report to enrich")
    p.add_argument("--output", type=Path, help="output path (defaults to config/overwrite)")

    p = sub.add_parser("validate", help="Check document structure against a config")
    p.add_argument("config", type=Path, help="report or enrich config")
    p.add_argument("input_docx", type=Path, help="docx to validate")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("verify", help="Print a structural summary of a built report")
    p.add_argument("docx", type=Path, help="built report")
    p.add_argument("config", type=Path, nargs="?", help="optional config for cross-checks")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("preview", help="Preview a report/enrich config without writing anything")
    p.add_argument("config", type=Path, help="report or enrich config")
    p.add_argument("--show-patterns", action="store_true", help="dump donor-style resolution patterns")
    p.add_argument("--show-screenshots", action="store_true", help="dump the screenshot plan")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("inspect-template", help="Check the template against fixed table assumptions")
    p.add_argument("template", type=Path, help="template .docx")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("scaffold", help="Generate a report config skeleton from a course profile")
    p.add_argument("out", type=Path, help="where to write the new report config")
    p.add_argument("--profile", type=Path, required=True, help="course report profile path")
    p.add_argument("--experiment", type=int, required=True, help="experiment number (1..N)")
    p.add_argument("--tasks", type=int, default=6, help="how many assignment sections to prefill")
    p.add_argument("--experiment-name", default="TODO: experiment title")

    p = sub.add_parser("nbcheck", help="Check an executed notebook without dumping its JSON")
    p.add_argument("notebook", type=Path, help="executed .ipynb (or Jupytext .py)")
    p.add_argument("--max-images", type=int, default=2, help="max image outputs per code cell")
    p.add_argument("--source-py", type=Path, help="Jupytext .py truth source; also checks ipynb drift")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("scaffold-notebook", help="Generate a Jupytext percent notebook skeleton")
    p.add_argument("requirements", type=Path, help="experiment requirements.yml")
    p.add_argument("out", type=Path, help="output .py notebook skeleton")

    p = sub.add_parser("experiment-doctor", help="Check experiment requirements, env and artifacts")
    p.add_argument("requirements", type=Path, help="experiment requirements.yml")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("artifact-check", help="Check result images for missing/duplicate/stale files")
    p.add_argument("root", type=Path, help="results directory to scan")
    p.add_argument("--config", type=Path, help="report config; its figure blocks count as referenced")
    p.add_argument("--metrics", type=Path, help="metrics.json produced by the notebook")
    p.add_argument("--notebook", type=Path, help="executed notebook, for staleness comparison")
    p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("pdf", help="Export DOCX to PDF through Microsoft Word (Windows only)")
    p.add_argument("docx", type=Path, help="docx to export")
    p.add_argument("--output", type=Path, help="output pdf path")
    p.add_argument(
        "--allow-placeholders", action="store_true", help="export a draft even if image placeholders remain"
    )
    p.add_argument("--overwrite", action="store_true", help="replace an existing pdf")

    return parser


# --------------------------------------------------------------------------- #
# dispatch
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _dispatch(args)
    except DocxReportError as exc:
        print(f"error [{exc.code}]: {exc.message}", file=sys.stderr)
        if exc.hint:
            print(f"hint: {exc.hint}", file=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:  # pragma: no cover
        print("aborted", file=sys.stderr)
        return 130


def _dispatch(args: argparse.Namespace) -> int:
    cmd = args.command

    if cmd == "build":
        print(build_report(args.config, output_path=args.output))
        return EXIT_OK

    if cmd == "revise":
        print(revise_report(args.config, args.input_docx, output_path=args.output))
        return EXIT_OK

    if cmd == "enrich":
        print(enrich_report(args.config, args.input_docx, output_path=args.output))
        return EXIT_OK

    if cmd == "pdf":
        print(
            export_pdf(
                args.docx, args.output, allow_placeholders=args.allow_placeholders, overwrite=args.overwrite
            )
        )
        return EXIT_OK

    if cmd == "preview":
        _print_preview(
            args.config,
            show_patterns=args.show_patterns,
            show_screenshots=args.show_screenshots,
            as_json=args.json,
        )
        return EXIT_OK

    if cmd == "scaffold":
        print(
            scaffold_report_config(
                args.profile,
                args.experiment,
                args.out,
                tasks=args.tasks,
                experiment_name=args.experiment_name,
            )
        )
        return EXIT_OK

    if cmd == "scaffold-notebook":
        print(scaffold_notebook(args.requirements, args.out))
        return EXIT_OK

    if cmd == "doctor":
        result = doctor_config(args.config, input_docx=args.input_docx)
        _emit(
            result.summary_lines(),
            as_json=args.json,
            ok=result.ok,
            code="OK" if result.ok else "NOT_READY",
            extra={"suggested_command": result.suggested_command},
        )
        return EXIT_OK if result.ok else EXIT_CHECK_FAILED

    if cmd == "validate":
        result = validate_report(args.config, args.input_docx)
        _emit(result.summary_lines(), as_json=args.json, ok=result.ok, code="OK" if result.ok else "INVALID")
        return EXIT_OK if result.ok else EXIT_CHECK_FAILED

    if cmd == "verify":
        lines = verify_document(args.docx, args.config)
        ok = not any(line.startswith("ERROR") for line in lines)
        _emit(lines, as_json=args.json, ok=ok, code="OK" if ok else "INVALID")
        return EXIT_OK if ok else EXIT_CHECK_FAILED

    if cmd == "inspect-template":
        result = validate_template_layout(args.template, TemplateLayoutAssumptions())
        _emit(
            result.summary_lines(),
            as_json=args.json,
            ok=result.ok,
            code="OK" if result.ok else "TEMPLATE_MISMATCH",
        )
        return EXIT_OK if result.ok else EXIT_CHECK_FAILED

    if cmd == "nbcheck":
        result = check_notebook(args.notebook, max_images_per_cell=args.max_images)
        lines = list(result.summary_lines())
        ok = result.ok
        if args.source_py:
            pair = check_notebook_pair(args.source_py, args.notebook)
            lines.extend(pair.summary_lines())
            ok = ok and pair.ok
        _emit(lines, as_json=args.json, ok=ok, code="OK" if ok else "NOTEBOOK_NOT_READY")
        return EXIT_OK if ok else EXIT_CHECK_FAILED

    if cmd == "experiment-doctor":
        result = check_experiment_readiness(args.requirements)
        _emit(
            result.summary_lines(), as_json=args.json, ok=result.ok, code="OK" if result.ok else "NOT_READY"
        )
        return EXIT_OK if result.ok else EXIT_CHECK_FAILED

    if cmd == "artifact-check":
        referenced = referenced_images_from_config(args.config) if args.config else []
        result = check_artifacts(
            args.root, referenced=referenced, metrics=args.metrics, notebook=args.notebook
        )
        _emit(
            result.summary_lines(),
            as_json=args.json,
            ok=result.ok,
            code="OK" if result.ok else "ARTIFACT_PROBLEM",
        )
        return EXIT_OK if result.ok else EXIT_CHECK_FAILED

    raise DocxReportError(f"unsupported command: {cmd}", hint="run --help")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
