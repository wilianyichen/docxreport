#!/usr/bin/env python3
"""Convenience entrypoint for the local docx-report-skill."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# 运行库查找顺序：
#   1) skill 自带的 <skill>/lib/docx_report（单一真源，任何目录可用）
#   2) 当前工作目录向上逐级查找 docx_report 包（项目内自带运行库时的回退）
_here = Path(__file__).resolve()
_lib_root = _here.parent.parent / 'lib'
if (_lib_root / 'docx_report' / '__init__.py').exists():
    PROJECT_ROOT = _lib_root
else:
    _cwd = Path.cwd()
    for _parent in [_cwd, *_cwd.parents]:
        if (_parent / 'docx_report' / '__init__.py').exists():
            PROJECT_ROOT = _parent
            break
    else:
        PROJECT_ROOT = _cwd
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from docx_report.api import (
    build_report,
    doctor_config,
    enrich_report,
    generate_screenshot_plan,
    preview_config,
    revise_report,
    summarize_report_patterns,
    validate_report,
)
from docx_report.artifact_check import check_artifacts, referenced_images_from_config
from docx_report.experiment_readiness import check_experiment_readiness
from docx_report.models import TemplateLayoutAssumptions
from docx_report.notebook_check import check_notebook, check_notebook_pair
from docx_report.notebook_scaffold import scaffold_notebook
from docx_report.pdf_export import export_pdf
from docx_report.scaffold import scaffold_report_config
from docx_report.verify import verify_document
from docx_report.validators import validate_template_layout


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="docx-report-skill local entrypoint")
    sub = parser.add_subparsers(dest="command", required=True)

    build_cmd = sub.add_parser("build", help="Build a report from config")
    build_cmd.add_argument("config", type=Path)
    build_cmd.add_argument("--output", type=Path)

    revise_cmd = sub.add_parser("revise", help="Revise an existing report while preserving screenshots")
    revise_cmd.add_argument("config", type=Path)
    revise_cmd.add_argument("input_docx", type=Path)
    revise_cmd.add_argument("--output", type=Path)

    enrich_cmd = sub.add_parser("enrich", help="Insert figures/appendices using an enrich config")
    enrich_cmd.add_argument("config", type=Path)
    enrich_cmd.add_argument("input_docx", type=Path)
    enrich_cmd.add_argument("--output", type=Path)

    validate_cmd = sub.add_parser("validate", help="Run structural validation against a config/docx")
    validate_cmd.add_argument("config", type=Path)
    validate_cmd.add_argument("input_docx", type=Path)

    preview_cmd = sub.add_parser("preview", help="Preview a report or enrich config")
    preview_cmd.add_argument("config", type=Path)
    preview_cmd.add_argument("--show-patterns", action="store_true")
    preview_cmd.add_argument("--show-screenshots", action="store_true")
    preview_cmd.add_argument("--json", action="store_true")

    inspect_cmd = sub.add_parser("inspect-template", help="Check template layout assumptions")
    inspect_cmd.add_argument("template", type=Path)

    verify_cmd = sub.add_parser("verify", help="Print a structural summary of a built report (token-cheap review)")
    verify_cmd.add_argument("docx", type=Path)
    verify_cmd.add_argument("config", type=Path, nargs="?")

    scaffold_cmd = sub.add_parser("scaffold", help="Generate a report config skeleton from a course profile")
    scaffold_cmd.add_argument("out", type=Path, help="where to write the new report config")
    scaffold_cmd.add_argument("--profile", type=Path, required=True, help="course report profile path")
    scaffold_cmd.add_argument("--experiment", type=int, required=True, help="experiment number (1..N)")
    scaffold_cmd.add_argument("--tasks", type=int, default=6, help="how many 作业 sections to prefill")
    scaffold_cmd.add_argument("--experiment-name", default="【待填写：实验题目】")

    doctor_cmd = sub.add_parser("doctor", help="Check config/input readiness and suggest the next command")
    doctor_cmd.add_argument("config", type=Path)
    doctor_cmd.add_argument("input_docx", type=Path, nargs="?")

    nbcheck_cmd = sub.add_parser("nbcheck", help="Check an executed notebook without dumping notebook JSON")
    nbcheck_cmd.add_argument("notebook", type=Path)
    nbcheck_cmd.add_argument("--max-images", type=int, default=2, help="max image outputs allowed per code cell (screenshot unit)")
    nbcheck_cmd.add_argument("--source-py", type=Path, help="Jupytext .py truth source; also checks ipynb drift")

    notebook_cmd = sub.add_parser("scaffold-notebook", help="Generate a Jupytext percent notebook skeleton")
    notebook_cmd.add_argument("requirements", type=Path)
    notebook_cmd.add_argument("out", type=Path)

    exp_cmd = sub.add_parser("experiment-doctor", help="Check experiment requirements, environment and artifacts")
    exp_cmd.add_argument("requirements", type=Path)

    artifact_cmd = sub.add_parser("artifact-check", help="Check result images for missing/duplicate/stale files")
    artifact_cmd.add_argument("root", type=Path)
    artifact_cmd.add_argument("--config", type=Path, help="report config; its figure blocks count as referenced images")
    artifact_cmd.add_argument("--metrics", type=Path)
    artifact_cmd.add_argument("--notebook", type=Path)

    pdf_cmd = sub.add_parser("pdf", help="Export DOCX to PDF through Microsoft Word")
    pdf_cmd.add_argument("docx", type=Path)
    pdf_cmd.add_argument("--output", type=Path)
    pdf_cmd.add_argument("--allow-placeholders", action="store_true")
    pdf_cmd.add_argument("--overwrite", action="store_true")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "build":
        output = build_report(args.config, output_path=args.output)
        print(output)
    elif args.command == "revise":
        output = revise_report(args.config, args.input_docx, output_path=args.output)
        print(output)
    elif args.command == "enrich":
        output = enrich_report(args.config, args.input_docx, output_path=args.output)
        print(output)
    elif args.command == "validate":
        result = validate_report(args.config, args.input_docx)
        for line in result.summary_lines():
            print(line)
    elif args.command == "preview":
        _print_preview(args.config, show_patterns=args.show_patterns, show_screenshots=args.show_screenshots, as_json=args.json)
    elif args.command == "inspect-template":
        result = validate_template_layout(args.template, TemplateLayoutAssumptions())
        for line in result.summary_lines():
            print(line)
    elif args.command == "verify":
        for line in verify_document(args.docx, args.config):
            print(line)
    elif args.command == "scaffold":
        written = scaffold_report_config(args.profile, args.experiment, args.out,
                                         tasks=args.tasks, experiment_name=args.experiment_name)
        print(written)
    elif args.command == "doctor":
        result = doctor_config(args.config, input_docx=args.input_docx)
        for line in result.summary_lines():
            print(line)
    elif args.command == "nbcheck":
        result = check_notebook(args.notebook, max_images_per_cell=args.max_images)
        for line in result.summary_lines():
            print(line)
        failed = not result.ok
        if args.source_py:
            pair = check_notebook_pair(args.source_py, args.notebook)
            for line in pair.summary_lines():
                print(line)
            failed = failed or not pair.ok
        if failed:
            raise SystemExit(2)
    elif args.command == "scaffold-notebook":
        print(scaffold_notebook(args.requirements, args.out))
    elif args.command == "experiment-doctor":
        result = check_experiment_readiness(args.requirements)
        for line in result.summary_lines():
            print(line)
        if not result.ok:
            raise SystemExit(2)
    elif args.command == "artifact-check":
        referenced = referenced_images_from_config(args.config) if args.config else []
        result = check_artifacts(args.root, referenced=referenced, metrics=args.metrics, notebook=args.notebook)
        for line in result.summary_lines():
            print(line)
        if not result.ok:
            raise SystemExit(2)
    elif args.command == "pdf":
        print(export_pdf(args.docx, args.output, allow_placeholders=args.allow_placeholders,
                         overwrite=args.overwrite))
    else:
        parser.error(f"unsupported command: {args.command}")


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


if __name__ == "__main__":
    main()
