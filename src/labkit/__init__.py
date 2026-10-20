"""Small, transparent helpers for experiment notebooks.

Core scientific choices (cleaning, features, split, sampler, model and search
space) intentionally remain visible in each notebook.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)


def set_reproducible_seed(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)


def ensure_output_dirs(root: Path) -> tuple[Path, Path]:
    results = Path(root) / "results"
    figures = results / "figures"
    results.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    return results, figures


def evaluate_binary_classifier(y_true, y_pred, y_score=None) -> dict[str, Any]:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1], zero_division=0
    )
    result: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "class0": {
            "precision": float(precision[0]),
            "recall": float(recall[0]),
            "f1": float(f1[0]),
            "support": int(support[0]),
        },
        "class1": {
            "precision": float(precision[1]),
            "recall": float(recall[1]),
            "f1": float(f1[1]),
            "support": int(support[1]),
        },
    }
    if y_score is not None:
        result["roc_auc"] = float(roc_auc_score(y_true, y_score))
        result["pr_auc"] = float(average_precision_score(y_true, y_score))
    return result


def save_metrics_json(payload: dict[str, Any], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)
    return path


def save_figure(fig, path: Path, *, dpi: int = 160) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    return path
