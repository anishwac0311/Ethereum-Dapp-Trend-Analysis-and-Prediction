"""Simple baselines that any learned model must beat."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


def _safe_auc(y, p) -> float:
    y = np.asarray(y)
    p = np.asarray(p)
    if len(np.unique(y)) < 2:
        return np.nan
    return float(roc_auc_score(y, p))


def _safe_ap(y, p) -> float:
    y = np.asarray(y)
    p = np.asarray(p)
    if len(np.unique(y)) < 2:
        return np.nan
    return float(average_precision_score(y, p))


def _safe_brier(y, p) -> float:
    y = np.asarray(y, dtype=float)
    p = np.clip(np.asarray(p, dtype=float), 0, 1)
    return float(brier_score_loss(y, p))


def precision_at_frac(y, p, frac: float = 0.1) -> float:
    y = np.asarray(y)
    p = np.asarray(p)
    n = max(1, int(round(len(p) * frac)))
    idx = np.argsort(-p)[:n]
    return float(y[idx].mean()) if n else np.nan


def score_probs(y, p, name: str, **extra) -> dict:
    return {
        "model": name,
        "auc": _safe_auc(y, p),
        "ap": _safe_ap(y, p),
        "brier": _safe_brier(y, p),
        "precision_at_10pct": precision_at_frac(y, p, 0.10),
        "precision_at_20pct": precision_at_frac(y, p, 0.20),
        "base_rate": float(np.mean(y)),
        "n": int(len(y)),
        **extra,
    }


def persistence_rule(train: pd.DataFrame, test: pd.DataFrame, target: str) -> tuple[np.ndarray, dict]:
    """Score = 1 if last in-window wallets >= 1k else last_wallets/1000 (clipped)."""
    last = test["last_wallets"].astype(float).fillna(0).values
    proba = np.clip(last / 1000.0, 0, 1)
    # Also hard rule for reporting
    hard = (last >= 1000).astype(float)
    metrics = score_probs(test[target].values, proba, "persistence")
    metrics["hard_precision"] = float(
        test.loc[hard == 1, target].mean()
    ) if hard.sum() else np.nan
    metrics["hard_recall"] = float(
        ((hard == 1) & (test[target].values == 1)).sum() / max(test[target].sum(), 1)
    )
    return proba, metrics


def szabo_huberman(train: pd.DataFrame, test: pd.DataFrame, target: str) -> tuple[np.ndarray, dict]:
    """Log early popularity → later success via univariate logistic on log_last_wallets."""
    xtr = train[["log_last_wallets"]].fillna(0)
    ytr = train[target].astype(int)
    xte = test[["log_last_wallets"]].fillna(0)
    clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    clf.fit(xtr, ytr)
    proba = clf.predict_proba(xte)[:, 1]
    return proba, score_probs(test[target].values, proba, "szabo_huberman")


def category_prior(train: pd.DataFrame, test: pd.DataFrame, target: str) -> tuple[np.ndarray, dict]:
    """Predict using category_group empirical success rate (smoothed)."""
    rates = train.groupby("category_group")[target].mean()
    global_rate = float(train[target].mean())
    # Laplace-ish: blend with global
    counts = train.groupby("category_group")[target].count()
    blended = (rates * counts + global_rate * 5) / (counts + 5)
    proba = test["category_group"].map(blended).fillna(global_rate).astype(float).values
    return proba, score_probs(test[target].values, proba, "category_prior")


def run_all_baselines(train: pd.DataFrame, test: pd.DataFrame, target: str) -> pd.DataFrame:
    rows = []
    for fn in (persistence_rule, szabo_huberman, category_prior):
        _, m = fn(train, test, target)
        rows.append(m)
    return pd.DataFrame(rows)
