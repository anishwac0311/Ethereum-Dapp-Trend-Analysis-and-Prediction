"""Fit the team's models on one split and score its test set (holdout average precision and AUC)."""
from __future__ import annotations

import pandas as pd

from config import K, TARGET  # first: puts the team model on the import path
from baselines import run_all_baselines, score_probs
from features import FEATURE_COLS
from train_eval import bootstrap_metrics, calibrate_pipe, feature_matrix_cols, fit_predict, make_hgb, make_logreg

MODELS = {"logreg_l2": lambda cols: make_logreg(cols),
          "logreg_elastic": lambda cols: make_logreg(cols, elastic=True),
          "hgb": make_hgb}


def evaluate(train: pd.DataFrame, test: pd.DataFrame, split: str, feature_cols=None) -> pd.DataFrame:
    """Baselines, logistic, boosted trees and calibrated boosted trees, each with bootstrap intervals."""
    cols = list(feature_cols or FEATURE_COLS)
    y = test[TARGET].values
    rows = run_all_baselines(train, test, TARGET).to_dict("records")
    for name, make in MODELS.items():
        p = fit_predict(make(cols), train, test, cols, TARGET)
        rows.append({**score_probs(y, p, name), **bootstrap_metrics(y, p)})
    calibrated = calibrate_pipe(make_hgb(cols), train, cols, TARGET)
    p = calibrated.predict_proba(test[feature_matrix_cols(cols)])[:, 1]
    rows.append({**score_probs(y, p, "hgb_calibrated"), **bootstrap_metrics(y, p)})

    out = pd.DataFrame(rows)
    out.insert(0, "split", split)
    out["k"] = K
    out["n_train"], out["pos_train"] = len(train), int(train[TARGET].sum())
    out["n_test"], out["pos_test"] = len(test), int(test[TARGET].sum())
    keep = ["split", "model", "auc", "ap", "ap_lo", "ap_hi", "auc_lo", "auc_hi", "brier", "precision_at_10pct",
            "base_rate", "n_train", "pos_train", "n_test", "pos_test", "k"]
    return out[[c for c in keep if c in out.columns]]
