"""Config loading: shapes, precedence and typed failures."""

from __future__ import annotations

import pytest

from docx_report.config_loader import load_enrichment_config, load_report_config
from docx_report.errors import (
    ConfigInvalidError,
    ConfigReadError,
    ConfigWrongTypeError,
    CourseProfileError,
)

REPORT_YAML = """
name: exp1
template: template.docx
output: out/exp1.docx
cover_title: 实验一
experiment_name: 示例实验
expected_images: 2
blocks:
  - kind: section
    text: 一、实验目的
  - kind: body
    text: 正文
  - kind: caption
    text: 图 1 示例
"""

ENRICH_YAML = """
name: exp1-enrich
output: out/exp1-final.docx
actions:
  - action: add_page_break
  - action: append_paragraph
    text: 附录
"""


def test_report_config_roundtrip(write_text):
    path = write_text("report.yml", REPORT_YAML)
    config = load_report_config(path)

    assert config.name == "exp1"
    assert config.template.name == "template.docx"
    assert config.output.name == "exp1.docx"
    assert [b.kind for b in config.blocks] == ["section", "body", "caption"]
    assert config.expected_images == 2
    assert config.source == path


def test_enrich_config_roundtrip(write_text):
    path = write_text("enrich.yml", ENRICH_YAML)
    config = load_enrichment_config(path)

    assert [a.action for a in config.actions] == ["add_page_break", "append_paragraph"]
    assert config.actions[1].extras == {"text": "附录"}


def test_missing_output_is_config_invalid(write_text):
    path = write_text("bad.yml", "blocks:\n  - kind: body\n    text: x\n")
    with pytest.raises(ConfigInvalidError) as excinfo:
        load_report_config(path)
    assert excinfo.value.code == "E_CONFIG_INVALID"
    assert "missing output" in str(excinfo.value)
    assert excinfo.value.hint


def test_wrong_type_detection_both_directions(write_text):
    report_path = write_text("report.yml", REPORT_YAML)
    enrich_path = write_text("enrich.yml", ENRICH_YAML)

    with pytest.raises(ConfigWrongTypeError) as report_as_enrich:
        load_enrichment_config(report_path)
    assert report_as_enrich.value.code == "E_CONFIG_WRONG_TYPE"

    with pytest.raises(ConfigWrongTypeError) as enrich_as_report:
        load_report_config(enrich_path)
    assert enrich_as_report.value.code == "E_CONFIG_WRONG_TYPE"


def test_unsupported_suffix_is_config_read_error(write_text):
    path = write_text("config.ini", "output = x")
    with pytest.raises(ConfigReadError) as excinfo:
        load_report_config(path)
    assert excinfo.value.code == "E_CONFIG_READ"


def test_json_config_supported(write_text):
    path = write_text(
        "report.json",
        '{"output": "o.docx", "blocks": [{"kind": "body", "text": "hi"}]}',
    )
    config = load_report_config(path)
    assert config.blocks[0].text == "hi"


def test_python_config_supported(write_text):
    path = write_text(
        "report.py",
        'REPORT_CONFIG = {"output": "o.docx", "blocks": [{"kind": "body", "text": "py"}]}\n',
    )
    config = load_report_config(path)
    assert config.blocks[0].text == "py"
    # no explicit name -> falls back to the containing directory name
    assert config.name == path.parent.name


def test_extends_deep_merges_parent(write_text):
    write_text("base.yml", REPORT_YAML)
    child = write_text(
        "child.yml",
        """
extends: base.yml
output: out/child.docx
blocks:
  - kind: body
    text: child body
""",
    )
    config = load_report_config(child)
    assert config.output.name == "child.docx"
    assert config.cover_title == "实验一"  # inherited
    assert [b.text for b in config.blocks] == ["child body"]  # list replaced, not merged


def test_course_profile_provides_defaults_and_config_overrides(write_text):
    write_text(
        "course-report-profile.yml",
        """
kind: course-report-profile
styles:
  section:
    size: 30
    bold: true
  body:
    size: 22
""",
    )
    config_path = write_text(
        "docs/report.yml",
        """
output: out/exp1.docx
styles:
  body:
    size: 21
blocks:
  - kind: body
    text: x
""",
    )
    config = load_report_config(config_path)

    assert config.styles.section.size == 30  # from profile
    assert config.styles.section.bold is True  # from profile
    assert config.styles.body.size == 21  # config wins over profile


def test_explicit_missing_course_profile_is_an_error(write_text):
    config_path = write_text(
        "docs/report.yml",
        "course_profile: nope.yml\noutput: o.docx\nblocks:\n  - kind: body\n    text: x\n",
    )
    with pytest.raises(CourseProfileError) as excinfo:
        load_report_config(config_path)
    assert excinfo.value.code == "E_COURSE_PROFILE"


def test_font_shorthand_sets_all_three_font_slots(write_text):
    config_path = write_text(
        "report.yml",
        """
output: o.docx
styles:
  body:
    font: 宋体
blocks:
  - kind: body
    text: x
""",
    )
    body = load_report_config(config_path).styles.body
    assert body.ascii_font == body.hansi_font == body.east_asia_font == "宋体"


def test_input_paths_resolve_from_config_dir_first(tmp_path):
    from docx_report.config_loader import resolve_input_path

    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "fig.png").write_bytes(b"x")
    config = tmp_path / "docs" / "report.yml"
    config.write_text("output: o.docx\nblocks: [{kind: body, text: x}]\n", encoding="utf-8")

    assert resolve_input_path(config, "fig.png") == (tmp_path / "docs" / "fig.png").resolve()


def test_input_paths_fall_back_to_course_root(tmp_path):
    """Legacy layout: config in <course>/6/docs, figure written as 6/figures/x.png."""
    from docx_report.config_loader import resolve_input_path

    (tmp_path / "6" / "docs").mkdir(parents=True)
    (tmp_path / "6" / "figures").mkdir()
    figure = tmp_path / "6" / "figures" / "a.png"
    figure.write_bytes(b"x")
    config = tmp_path / "6" / "docs" / "report.yml"
    config.write_text("output: o.docx\nblocks: [{kind: body, text: x}]\n", encoding="utf-8")

    assert resolve_input_path(config, "6/figures/a.png") == figure.resolve()


def test_paths_base_overrides_the_search(tmp_path):
    from docx_report.config_loader import resolve_input_path

    (tmp_path / "docs").mkdir()
    (tmp_path / "shared").mkdir()
    target = tmp_path / "shared" / "fig.png"
    target.write_bytes(b"x")
    config = tmp_path / "docs" / "report.yml"
    config.write_text(
        "paths_base: ../shared\noutput: o.docx\nblocks: [{kind: body, text: x}]\n",
        encoding="utf-8",
    )

    loaded = load_report_config(config)
    assert loaded.extras["paths_base"] == "../shared"
    assert resolve_input_path(config, "fig.png", paths_base="../shared") == target.resolve()


def test_output_always_resolves_from_config_dir(tmp_path):
    config = tmp_path / "docs" / "report.yml"
    config.parent.mkdir()
    config.write_text("output: out/r.docx\nblocks: [{kind: body, text: x}]\n", encoding="utf-8")

    loaded = load_report_config(config)
    assert loaded.output == (tmp_path / "docs" / "out" / "r.docx").resolve()
