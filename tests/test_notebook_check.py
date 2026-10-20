"""Notebook gate: executed cells, error outputs, image density, py/ipynb drift."""

from __future__ import annotations

import base64
import json

from docx_report.notebook_check import check_notebook, check_notebook_pair, notebook_code_text


def _png_b64(colour: bytes = b"\x01") -> str:
    # A real 1x1 PNG is overkill; the checker only hashes the payload.
    return base64.b64encode(b"img-" + colour).decode()


def _nb(cells: list[dict]) -> str:
    return json.dumps(
        {
            "cells": cells,
            "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}},
            "nbformat": 4,
            "nbformat_minor": 5,
        }
    )


def _code(source: str, count: int | None = 1, outputs: list | None = None) -> dict:
    return {
        "cell_type": "code",
        "execution_count": count,
        "metadata": {},
        "source": source.splitlines(keepends=True),
        "outputs": outputs or [],
    }


def test_clean_notebook_passes(write_text):
    path = write_text(
        "nb.ipynb",
        _nb(
            [
                {"cell_type": "markdown", "metadata": {}, "source": ["# title\n"]},
                _code("print(1)", 1, [{"output_type": "stream", "name": "stdout", "text": ["1\n"]}]),
            ]
        ),
    )
    result = check_notebook(path)
    assert result.ok
    assert result.facts["executed_code_cells"] == 1
    assert result.facts["error_outputs"] == 0


def test_unexecuted_cell_blocks(write_text):
    path = write_text("nb.ipynb", _nb([_code("x = 1", None)]))
    result = check_notebook(path)
    assert not result.ok
    assert any("unexecuted code cells" in e for e in result.errors)


def test_error_output_blocks(write_text):
    path = write_text(
        "nb.ipynb",
        _nb(
            [
                _code(
                    "1/0",
                    1,
                    [{"output_type": "error", "ename": "ZeroDivisionError", "evalue": "division by zero"}],
                ),
            ]
        ),
    )
    result = check_notebook(path)
    assert not result.ok
    assert "ZeroDivisionError" in result.errors[0]


def test_too_many_images_is_a_warning_not_a_block(write_text):
    outputs = [{"output_type": "display_data", "data": {"image/png": _png_b64(bytes([i]))}} for i in range(3)]
    path = write_text("nb.ipynb", _nb([_code("plot()", 1, outputs)]))
    result = check_notebook(path, max_images_per_cell=2)
    assert result.ok
    assert result.warnings and "max images per cell" in result.warnings[0]


def test_duplicate_embedded_images_are_flagged(write_text):
    payload = _png_b64(b"same")
    outputs = [{"output_type": "display_data", "data": {"image/png": payload}} for _ in range(2)]
    path = write_text("nb.ipynb", _nb([_code("plot()", 1, outputs)]))
    result = check_notebook(path, max_images_per_cell=3)
    assert any("duplicate embedded image" in w for w in result.warnings)


def test_missing_notebook_is_an_error(tmp_path):
    result = check_notebook(tmp_path / "nope.ipynb")
    assert not result.ok
    assert "notebook not found" in result.errors[0]


def test_py_ipynb_drift_is_detected(write_text):
    py = write_text("nb.py", "# %%\nprint(1)\n# %% [markdown]\n# note\n")
    matching = write_text("ok.ipynb", _nb([_code("print(1)")]))
    drifting = write_text("drift.ipynb", _nb([_code("print(2)")]))

    assert check_notebook_pair(py, matching).ok
    bad = check_notebook_pair(py, drifting)
    assert not bad.ok
    assert "differs" in bad.errors[0]


def test_jupytext_percent_source_is_read_as_python(write_text):
    py = write_text("nb.py", "# %%\n# import os\n# print(os.name)\n# %% [markdown]\n# prose\n")
    text = notebook_code_text(py)
    assert "import os" in text
    assert "prose" not in text
