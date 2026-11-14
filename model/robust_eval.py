"""Threshold-robust, pooled out-of-fold model comparison.

Why: the 2023-24 holdout has ~29 positives, so a single AP at the hard 1k / 25%
cutoff can't separate a real +0.05 from noise. Here:

  * expanding folds: validate on parent-launch years 2021, 2022, 2023, 2024, each
    trained on all earlier years (versions of a protocol never straddle folds)
  * pooled OOF predictions over ~400 DApps instead of 237
  * success is a RANGE: AP at every (abs wallets T, relative rho) grid cell; the
    headline is grid-mean AP. Also Spearman vs log wallets at m10-12 (no cutoff)
  * paired cluster bootstrap (by parent_protocol) for deltas vs the current HGB

Outputs (model/tables, model/figures):
  oof_comparison_k{k}.csv, oof_threshold_grid_k{k}.csv, oof_predictions_k{k}.csv,
  ap_vs_threshold_k{k}.png
"""
from __future__ import annotations

import argparse
from typing import Callable, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    cohen_kappa_score,
    roc_auc_score,
)

from baselines import precision_at_frac
from common import MODEL, annotate_lifecycle, load_lifecycle, load_panel, load_static, savefig, savetable, setup_style
from features import (FEATURE_COLS, FEATURE_COLS_PLUS_WALLET, FEATURE_COLS_PLUS_WALLET_TVL,
                      TVL_FEATURES, WALLET_FEATURES, build_dataset)
from labels import GRID_ABS, GRID_REL, TIERS, soft_label, success_tier, sustained_at
import panel_forecast as pf

REF_ABS, REF_REL = 1_000, 0.25
VAL_YEARS = (2021, 2022, 2023, 2024)
REFERENCE_MODEL = "hgb"
N_BOOT = 500
INNER_FOLDS = 5
FC_FEATURES = ["fc_median", "fc_iqr", "fc_p_ref"]


# ---------------------------------------------------------------------------
# Data + folds
# ---------------------------------------------------------------------------
def load_dataset(k: int) -> pd.DataFrame:
    path = MODEL / "tables" / f"dataset_k{k}.csv"
    ds = pd.read_csv(path) if path.exists() else build_dataset(k)
    if "launch_month" in ds.columns:
        ds["launch_month"] = pd.to_datetime(ds["launch_month"], errors="coerce")
    ds = ds[ds["eligible_12m"].astype(bool) & ~ds["left_censored"].astype(bool)].copy()
    ds = ds[ds["mean_wallets_10_12"].notna() & ds["window_max_wallets"].notna()].copy()
    # Flexible labels (recomputed so older cached datasets work too)
    ds["y_log_wallets_12"] = np.log1p(ds["mean_wallets_10_12"].astype(float))
    ds["y_soft_12"] = soft_label(ds)
    ds["y_tier_12"] = success_tier(ds)
    ds["y_sustained_12"] = sustained_at(ds, REF_ABS, REF_REL).astype(int)
    ds["has_token"] = ds["has_token"].astype(int)
    ds["parent_protocol"] = ds["parent_protocol"].fillna(ds["slug"])
    parent_year = ds.groupby("parent_protocol")["launch_year"].min()
    ds["parent_year"] = ds["parent_protocol"].map(parent_year)
    for c in WALLET_FEATURES + TVL_FEATURES:
        if c not in ds.columns:
            ds[c] = np.nan
    return ds.reset_index(drop=True)


def expanding_folds(ds: pd.DataFrame):
    """(name, train, val) for each validation parent-year, trained on all earlier years."""
    out = []
    for vy in VAL_YEARS:
        tr = ds[ds["parent_year"] < vy]
        va = ds[ds["parent_year"] == vy]
        if len(tr) < 40 or len(va) < 10 or tr["y_sustained_12"].nunique() < 2:
            continue
        out.append((f"val_{vy}", tr, va))
    return out


def inner_groups(df: pd.DataFrame, n: int = INNER_FOLDS, seed: int = 42) -> np.ndarray:
    parents = df["parent_protocol"].unique()
    rng = np.random.default_rng(seed)
    gid = dict(zip(parents, rng.integers(0, n, len(parents))))
    return df["parent_protocol"].map(gid).values


# ---------------------------------------------------------------------------
# Model wrappers: each returns P(success) on val (or a ranking score)
# ---------------------------------------------------------------------------
def _hgb(feature_cols):
    from train_eval import make_hgb
    return make_hgb(feature_cols)


def _cols(feature_cols):
    from train_eval import feature_matrix_cols
    return feature_matrix_cols(feature_cols)


def fit_hard(tr, va, feature_cols, factory=_hgb):
    pipe = factory(feature_cols)
    pipe.fit(tr[_cols(feature_cols)], tr["y_sustained_12"])
    return pipe.predict_proba(va[_cols(feature_cols)])[:, 1]


def fit_soft(tr, va, feature_cols):
    """Soft labels via duplication: each row is a positive with weight s and a negative
    with weight 1-s; positives reweighted to balance (matches class_weight='balanced')."""
    return train_soft(tr, feature_cols).predict_proba(va[_cols(feature_cols)])[:, 1]


def train_soft(tr, feature_cols):
    """Fitted soft-label HGB pipeline (see fit_soft)."""
    pipe = _hgb(feature_cols)
    pipe.named_steps["clf"].set_params(class_weight=None)
    s = tr["y_soft_12"].clip(0, 1).values
    X = pd.concat([tr[_cols(feature_cols)]] * 2, ignore_index=True)
    y = np.r_[np.ones(len(tr)), np.zeros(len(tr))]
    w = np.r_[s, 1 - s]
    pos, neg = w[y == 1].sum(), w[y == 0].sum()
    w = np.where(y == 1, w * (neg / max(pos, 1e-9)), w)
    keep = w > 1e-6
    pipe.fit(X[keep], y[keep], clf__sample_weight=w[keep])
    return pipe


def fit_elastic(tr, va, feature_cols):
    from train_eval import make_logreg
    return fit_hard(tr, va, feature_cols, factory=lambda c: make_logreg(c, elastic=True))


def fit_szabo(tr, va, feature_cols=None):
    lr = LogisticRegression(class_weight="balanced", max_iter=1000)
    lr.fit(tr[["log_last_wallets"]].fillna(0), tr["y_sustained_12"])
    return lr.predict_proba(va[["log_last_wallets"]].fillna(0))[:, 1]


def add_forecast_features(tr, va, rows, k):
    """Out-of-fold forecast features: inner splits for train, full train fit for val."""
    tr, va = tr.copy(), va.copy()
    g = inner_groups(tr)
    parts = []
    for i in np.unique(g):
        fc = pf.forecast_dapps(rows, tr.loc[g != i, "slug"], tr.loc[g == i, "slug"], k)
        fc["fc_p_ref"] = pf.prob_from_forecast(fc, REF_ABS, REF_REL)
        parts.append(fc[["slug", *FC_FEATURES]])
    tr = tr.merge(pd.concat(parts), on="slug", how="left")
    fc = pf.forecast_dapps(rows, tr["slug"], va["slug"], k)
    fc["fc_p_ref"] = pf.prob_from_forecast(fc, REF_ABS, REF_REL)
    va = va.merge(fc[["slug", *FC_FEATURES]], on="slug", how="left")
    return tr, va, fc


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def _ap(y, p):
    return average_precision_score(y, p) if len(np.unique(y)) == 2 else np.nan


def grid_labels(df: pd.DataFrame) -> dict[tuple, np.ndarray]:
    return {(T, r): sustained_at(df, T, r).values.astype(int) for T in GRID_ABS for r in GRID_REL}


def grid_scores(oof: pd.DataFrame, model: str, labels: dict) -> dict[tuple, float]:
    """AP per grid cell. Forecasters re-threshold their own CDF per cell; classifiers
    use their single probability as a ranking score."""
    out = {}
    for cell, y in labels.items():
        col = f"{model}@{cell[0]}_{cell[1]}"
        p = oof[col].values if col in oof.columns else oof[model].values
        out[cell] = _ap(y, p)
    return out


def paired_bootstrap(oof, labels, models, ref, n_boot=N_BOOT, seed=7):
    """Cluster bootstrap over parent_protocol: delta (model - ref) of ref-cell AP and grid-mean AP."""
    rng = np.random.default_rng(seed)
    parents = oof["parent_protocol"].values
    uniq = np.unique(parents)
    idx_by = {p: np.where(parents == p)[0] for p in uniq}
    deltas = {m: {"ref": [], "grid": []} for m in models}
    for _ in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([idx_by[p] for p in pick])
        b = oof.iloc[idx]
        lb = {c: y[idx] for c, y in labels.items()}
        g_ref = grid_scores(b, ref, lb)
        for m in models:
            g = grid_scores(b, m, lb)
            deltas[m]["ref"].append(g[(REF_ABS, REF_REL)] - g_ref[(REF_ABS, REF_REL)])
            deltas[m]["grid"].append(np.nanmean(list(g.values())) - np.nanmean(list(g_ref.values())))
    out = {}
    for m, d in deltas.items():
        r, gm = np.array(d["ref"]), np.array(d["grid"])
        out[m] = {
            "d_ap_ref_mean": np.nanmean(r), "d_ap_ref_lo": np.nanquantile(r, .025),
            "d_ap_ref_hi": np.nanquantile(r, .975),
            "d_ap_grid_mean": np.nanmean(gm), "d_ap_grid_lo": np.nanquantile(gm, .025),
            "d_ap_grid_hi": np.nanquantile(gm, .975),
            "p_grid_better": float(np.mean(gm > 0)),
        }
    return out


def tier_kappa(fc: pd.DataFrame, y_tier: np.ndarray) -> float:
    """Quadratic-weighted kappa of the forecaster's most likely tier."""
    cuts = [c for c, _ in TIERS][1:]
    p_ge = np.column_stack([pf.prob_from_forecast(fc, c, REF_REL) for c in cuts])
    probs = np.column_stack([1 - p_ge[:, 0], p_ge[:, 0] - p_ge[:, 1], p_ge[:, 1] - p_ge[:, 2], p_ge[:, 2]])
    return float(cohen_kappa_score(y_tier.astype(int), probs.argmax(1), weights="quadratic"))


# ---------------------------------------------------------------------------
# Main comparison
# ---------------------------------------------------------------------------
def run(k: int = 3, n_boot: int = N_BOOT) -> pd.DataFrame:
    ds = load_dataset(k)
    has_wallet = ds[WALLET_FEATURES].notna().any(axis=1).mean() > 0.5
    panel = load_panel()
    life = annotate_lifecycle(load_lifecycle(), load_static())
    rows = pf.build_rows(k, panel, life)
    print(f"\n== robust_eval k={k}: {len(ds)} eligible DApps, {len(rows):,} forecaster rows, "
          f"wallet features {'on' if has_wallet else 'MISSING'} ==")

    stack_cols = list(FEATURE_COLS) + FC_FEATURES
    stack_wallet_cols = list(FEATURE_COLS_PLUS_WALLET) + FC_FEATURES
    classifiers: dict[str, tuple[Callable, list, bool]] = {
        # name: (fit_fn, feature_cols, needs_forecast_features)
        "szabo_huberman": (fit_szabo, [], False),
        "logreg_elastic": (fit_elastic, list(FEATURE_COLS), False),
        "hgb": (fit_hard, list(FEATURE_COLS), False),          # current headline model
        "hgb_soft": (fit_soft, list(FEATURE_COLS), False),
    }
    if has_wallet:
        classifiers["hgb_wallet"] = (fit_hard, list(FEATURE_COLS_PLUS_WALLET), False)
        classifiers["hgb_soft_wallet"] = (fit_soft, list(FEATURE_COLS_PLUS_WALLET), False)
        if ds["has_tvl"].fillna(0).mean() > 0.2:
            classifiers["hgb_soft_wallet_tvl"] = (fit_soft, list(FEATURE_COLS_PLUS_WALLET_TVL), False)
    classifiers["hgb_stacked"] = (fit_hard, stack_cols, True)
    classifiers["hgb_soft_stacked"] = (fit_soft, stack_cols, True)
    if has_wallet:
        classifiers["hgb_soft_stacked_wallet"] = (fit_soft, stack_wallet_cols, True)

    folds = expanding_folds(ds)
    oof_parts, kappas = [], {"panel_ar": [], "panel_gbm_q": []}
    for name, tr, va in folds:
        print(f"  {name}: train={len(tr)} val={len(va)} pos={va['y_sustained_12'].mean():.3f}")
        part = va[["slug", "parent_protocol", "launch_year", "mean_wallets_10_12", "last_wallets",
                   "window_max_wallets", "y_sustained_12", "y_log_wallets_12", "y_tier_12"]].copy()
        part["fold"] = name
        need_fc = any(v[2] for v in classifiers.values())
        tr_fc, va_fc, fc_val = (add_forecast_features(tr, va, rows, k) if need_fc
                                else (tr, va, None))
        for m, (fn, cols, use_fc) in classifiers.items():
            a, b = (tr_fc, va_fc) if use_fc else (tr, va)
            part[m] = fn(a, b, cols)
        for kind, m in (("ar", "panel_ar"), ("gbm_q", "panel_gbm_q")):
            fc = (fc_val if kind == "gbm_q" and fc_val is not None
                  else pf.forecast_dapps(rows, tr["slug"], va["slug"], k, kind=kind))
            fc = part[["slug"]].merge(fc, on="slug", how="left")
            miss = fc["fc_median"].isna()
            if miss.any():  # DApps with no origin row: fall back to last-value forecast
                lw = np.log1p(part["last_wallets"].values) if "last_wallets" in part else 0.0
                fc.loc[miss, "window_max"] = part.loc[miss.values, "window_max_wallets"].values
                for c in [c for c in fc.columns if c.startswith("q_") or c in ("fc_median", "fc_mu")]:
                    fc.loc[miss, c] = np.asarray(lw)[miss.values]
                if "fc_sigma" in fc.columns:
                    fc["fc_sigma"] = fc["fc_sigma"].fillna(fc["fc_sigma"].max())
                print(f"    {m}: {int(miss.sum())} DApps without origin row -> last-value fallback")
            part[m] = pf.prob_from_forecast(fc, REF_ABS, REF_REL)
            part[f"{m}_median"] = fc["fc_median"].values
            for T in GRID_ABS:
                for r in GRID_REL:
                    part[f"{m}@{T}_{r}"] = pf.prob_from_forecast(fc, T, r)
            kappas[m].append((tier_kappa(fc, part["y_tier_12"].values), len(part)))
        oof_parts.append(part)

    oof = pd.concat(oof_parts, ignore_index=True)
    savetable(oof, f"oof_predictions_k{k}.csv")
    models = list(classifiers) + ["panel_ar", "panel_gbm_q"]
    labels = grid_labels(oof)
    y_ref = oof["y_sustained_12"].values

    grid_rows, comp = [], []
    ref_grid = grid_scores(oof, REFERENCE_MODEL, labels)
    print(f"  bootstrap ({n_boot} paired resamples) ...")
    boot = paired_bootstrap(oof, labels, [m for m in models if m != REFERENCE_MODEL],
                            REFERENCE_MODEL, n_boot=n_boot)
    hold = oof["launch_year"].isin([2023, 2024]).values
    for m in models:
        g = grid_scores(oof, m, labels)
        for (T, r), ap in g.items():
            grid_rows.append({"model": m, "abs_wallets": T, "rel": r, "ap": ap,
                              "base_rate": labels[(T, r)].mean(), "k": k})
        p = oof[m].values
        score_for_rank = oof[f"{m}_median"].values if f"{m}_median" in oof.columns else p
        row = {
            "model": m, "k": k, "n": len(oof), "n_pos_ref": int(y_ref.sum()),
            "ap_ref": g[(REF_ABS, REF_REL)],
            "ap_grid_mean": float(np.nanmean(list(g.values()))),
            "cells_beating_hgb": int(sum(g[c] > ref_grid[c] for c in g)) if m != REFERENCE_MODEL else np.nan,
            "auc_ref": roc_auc_score(y_ref, p),
            "brier_ref": brier_score_loss(y_ref, np.clip(p, 0, 1)),
            "p_at_10pct": precision_at_frac(y_ref, p, 0.10),
            "spearman_log_wallets": float(spearmanr(score_for_rank, oof["y_log_wallets_12"]).statistic),
            "ap_ref_holdout_2023_24": _ap(y_ref[hold], p[hold]),
        }
        if m in kappas:
            ks = kappas[m]
            row["tier_kappa"] = float(np.average([x for x, _ in ks], weights=[n for _, n in ks]))
        row.update(boot.get(m, {}))
        comp.append(row)

    comp = pd.DataFrame(comp).sort_values("ap_grid_mean", ascending=False)
    grid = pd.DataFrame(grid_rows)
    savetable(comp, f"oof_comparison_k{k}.csv")
    savetable(grid, f"oof_threshold_grid_k{k}.csv")
    _plot(grid, k)

    show = ["model", "ap_ref", "ap_grid_mean", "d_ap_grid_mean", "d_ap_grid_lo", "d_ap_grid_hi",
            "cells_beating_hgb", "spearman_log_wallets", "brier_ref", "ap_ref_holdout_2023_24"]
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(comp[[c for c in show if c in comp.columns]].round(3).to_string(index=False))
    return comp


def _plot(grid: pd.DataFrame, k: int) -> None:
    sub = grid[grid["rel"] == REF_REL]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    top = (grid.groupby("model")["ap"].mean().sort_values(ascending=False).index[:6].tolist())
    for m in dict.fromkeys(top + [REFERENCE_MODEL]):
        s = sub[sub["model"] == m].sort_values("abs_wallets")
        ax.plot(s["abs_wallets"], s["ap"], "o-", lw=2.5 if m != REFERENCE_MODEL else 1.5,
                ls="-" if m != REFERENCE_MODEL else "--", label=m)
    base = sub.drop_duplicates("abs_wallets").sort_values("abs_wallets")
    ax.plot(base["abs_wallets"], base["base_rate"], ":", color="grey", label="base rate")
    ax.set_xscale("log")
    ax.set_xticks(list(GRID_ABS))
    ax.set_xticklabels([f"{t:,}" for t in GRID_ABS])
    ax.set_xlabel(f"Wallet cutoff at months 10-12 (relative rule {REF_REL:.0%} of window max)")
    ax.set_ylabel("Pooled out-of-fold PR-AUC")
    ax.set_title(f"Success across a range of cutoffs, k={k}")
    ax.legend(fontsize=8, ncol=2)
    savefig(fig, f"ap_vs_threshold_k{k}.png")


def main() -> None:
    setup_style()
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, nargs="+", default=[3])
    parser.add_argument("--n-boot", type=int, default=N_BOOT)
    args = parser.parse_args()
    print("== robust_eval ==")
    for k in args.k:
        run(k, n_boot=args.n_boot)
    print("== robust_eval done ==")


if __name__ == "__main__":
    main()
