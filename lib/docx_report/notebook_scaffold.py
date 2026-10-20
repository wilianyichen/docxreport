from __future__ import annotations

"""Generate a compact Jupytext percent-format experiment notebook skeleton."""

from pathlib import Path
from typing import Any

from .course_profile import read_structured_file


HEADER = """# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#   kernelspec:
#     display_name: {kernel}
#     language: python
#     name: {kernel_name}
# ---
# %% [markdown]
# # 实验{experiment}：{title}
# 本文件是 Notebook 单一文本真源。请修改本文件后重新生成并完整执行 `.ipynb`。

# %%
from pathlib import Path
import json, platform, sys
import numpy as np
import pandas as pd

SEED = 42
np.random.seed(SEED)
# cwd 在 Jupyter / CLI / nbconvert 下可能不同：用显式候选并唯一匹配，不唯一就报错，禁止猜测。
cwd = Path.cwd().resolve()
candidates = [cwd, cwd / "1", cwd.parent, cwd.parent / "1"]
matches = [p for p in candidates if (p / "data").is_dir()]
if len(matches) != 1:
    raise RuntimeError("无法唯一定位项目根目录: cwd=" + str(cwd) + " matches=" + str(matches))
PROJECT_ROOT = matches[0]
RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
# 中文字体注册：matplotlib 默认 DejaVu Sans 不含 CJK 字形，图标题/坐标轴中文会显示成方框（tofu）。
# 提前注册系统中文矢量字体，保证后续 plt 出图中文正常。路径不存在则静默跳过。
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager as _fm
for _fp in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc"]:
    try:
        _fm.fontManager.addfont(_fp)
    except Exception:
        pass
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
print(sys.executable)
print(sys.version)

"""

CELL = """# %% [markdown]
# ## {label}：{title}
# 要求证据：{evidence}

# %%
# TODO: 在此实现 {label}。约定：
#   1) 每个代码单元默认只输出一幅主图，多面板比较要合成一张 Figure；
#   2) 模型训练/搜索一律 n_jobs=1（Windows 下 n_jobs=-1 会在 joblib 清理阶段偶发 KeyError，也不利于复现）。
raise NotImplementedError("{label} 尚未完成")

"""

FOOTER = """# %% [markdown]
# ## 运行产物与要求状态

# %%
# TODO: 将真实运行指标写入 results/metrics.json，并逐项记录 requirements 状态。
metrics = {{
    "run": {{
        "experiment": {experiment},
        "seed": SEED,
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
    }},
    "data": {{}},
    "requirements": {{}},
}}
(RESULTS_DIR / "metrics.json").write_text(
    json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
)
"""


def scaffold_notebook(requirements_path: Path, out_path: Path) -> Path:
    req = read_structured_file(Path(requirements_path))
    if req.get("kind") != "experiment-requirements":
        raise ValueError("requirements kind must be experiment-requirements")
    experiment = int(req.get("experiment") or 0)
    title = str(req.get("title") or "【待填写】")
    env = req.get("environment") or {}
    kernel = str(env.get("kernel_display_name") or "Python (required environment)")
    kernel_name = str(env.get("kernel_name") or "python3")
    text = HEADER.format(experiment=experiment, title=title, kernel=kernel, kernel_name=kernel_name)
    for item in list(req.get("mandatory") or []) + list(req.get("advanced") or []):
        label = str(item.get("id") or "requirement")
        item_title = str(item.get("title") or label)
        evidence = ", ".join(str(x) for x in item.get("evidence", [])) or "【待定义】"
        text += CELL.format(label=label, title=item_title, evidence=evidence)
    text += FOOTER.format(experiment=experiment)
    out_path = Path(out_path)
    if out_path.exists():
        raise FileExistsError(f"refusing to overwrite: {out_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return out_path
