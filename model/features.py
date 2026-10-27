"""Leakage-safe early features from months 0..k-1 after launch."""
from __future__ import annotations

import argparse
from typing import Optional

import numpy as np
import pandas as pd

from common import (
    annotate_lifecycle,
    load_category_month,
    load_lifecycle,
    load_panel,
    load_static,
    safe_log1p,
    savetable,
    setup_style,
)
from labels import build_labels

# Numeric feature columns (excluding categoricals / meta)
LEVEL_FEATURES = [
    "log_mean_wallets",
    "log_max_wallets",
    "log_last_wallets",
    "log_mean_tx",
    "log_mean_gas",
    "log_mean_fees",
    "log_mean_wallets_ex_heavy",
]
SHAPE_FEATURES = [
    "wallet_growth_slope",
    "last_to_max_ratio",
    "wallet_mom_volatility",
    "months_since_inwindow_peak",
]
QUALITY_FEATURES = [
    "early_retention",
    "cohort_m1_retention",
    "early_new_wallet_share",
    "early_returning_share",
    "early_tx_per_wallet",
    "early_gas_per_tx",
    "avg_n_protocols_in_tx",
]
CONCENTRATION_FEATURES = [
    "early_whale_share",
    "early_heavy_wallet_share",
]
CONTEXT_FEATURES = [
    "early_eco_share",
    "early_cat_share",
    "launch_eco_growth_3m",
    "launch_cat_growth_3m",
    "is_new_version_of_existing_protocol",
    "has_token",
    "launch_year",
]
FEATURE_COLS = (
    LEVEL_FEATURES
    + SHAPE_FEATURES
    + QUALITY_FEATURES
    + CONCENTRATION_FEATURES
    + CONTEXT_FEATURES
)
CAT_COLS = ["category_group"]


def _cohort_m1_in_window(
    cohort: Optional[pd.DataFrame],
    slug: str,
    launch_month,
    k: int,
) -> float:
    """Mean month-1 retention for cohorts whose m1 observation falls inside [0, k-1]."""
    if cohort is None or cohort.empty:
        return np.nan
    # cohort file uses protocol = slug
    g = cohort[cohort["protocol"] == slug]
    if g.empty:
        return np.nan
    # months_since == 1 rows where cohort_month is within first (k-1) months of launch
    m1 = g[g["months_since"] == 1].copy()
    if m1.empty or launch_month is None or pd.isna(launch_month):
        return np.nan
    launch = pd.Timestamp(launch_month).to_period("M")
    # cohort observed at m1 means the cohort started at launch + (msl of cohort start)
    # Restrict to cohorts that start in months 0..k-2 so m1 is still inside window
    rates = []
    for _, row in m1.iterrows():
        cm = pd.Timestamp(row["cohort_month"]).to_period("M")
        offset = (cm - launch).n
        if 0 <= offset <= max(0, k - 2):
            if row["cohort_size"] and row["cohort_size"] > 0:
                rates.append(float(row["retention_rate"]))
    if not rates:
        return np.nan
    return float(np.mean(rates))


def _market_growth(
    cat_month: Optional[pd.DataFrame],
    launch_month,
    category_group: str,
) -> tuple[float, float]:
    """Category and ecosystem growth_3m at launch month."""
    if cat_month is None or cat_month.empty or launch_month is None or pd.isna(launch_month):
        return np.nan, np.nan
    lm = pd.Timestamp(launch_month).to_period("M").to_timestamp()
    cat_row = cat_month[
        (cat_month["month"] == lm) & (cat_month["category_group"] == category_group)
    ]
    cat_g = float(cat_row["growth_3m"].iloc[0]) if len(cat_row) and "growth_3m" in cat_row else np.nan

    # Ecosystem = sum across categories that month, then MoM-ish proxy via weighted avg of growth_3m
    month_all = cat_month[cat_month["month"] == lm]
    if month_all.empty or "growth_3m" not in month_all.columns:
        eco_g = np.nan
    else:
        w = month_all["active_wallets"].astype(float).clip(lower=0)
        g = month_all["growth_3m"].astype(float)
        mask = g.notna() & w.notna() & (w > 0)
        eco_g = float(np.average(g[mask], weights=w[mask])) if mask.any() else np.nan
    return cat_g, eco_g


def _parent_has_prior(
    life: pd.DataFrame,
    slug: str,
    parent: str,
    launch_month,
) -> int:
    if not parent or pd.isna(parent) or launch_month is None or pd.isna(launch_month):
        return 0
    others = life[
        (life["parent_protocol"] == parent)
        & (life["slug"] != slug)
        & life["launch_month"].notna()
        & (life["launch_month"] < launch_month)
    ]
    return int(len(others) > 0)


def early_features(
    panel: pd.DataFrame,
    life: pd.DataFrame,
    k: int,
    cohort: Optional[pd.DataFrame] = None,
    cat_month: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Build leakage-free features from months 0..k-1."""
    life_idx = life.set_index("slug")
    rows = []
    for slug, g in panel.groupby("slug"):
        if slug not in life_idx.index:
            continue
        meta = life_idx.loc[slug]
        if isinstance(meta, pd.DataFrame):
            meta = meta.iloc[0]
        g = g.sort_values("month")
        if "months_since_launch" not in g.columns:
            continue
        early = g[
            (g["months_since_launch"] >= 0) & (g["months_since_launch"] < k)
        ].sort_values("months_since_launch")
        if len(early) < max(1, k // 2):
            continue

        aw = early["active_wallets"].astype(float).values
        tx = early["tx_count"].astype(float).values
        gas = early["gas_used"].astype(float).values
        fees = (
            early["fees_eth"].astype(float).values
            if "fees_eth" in early.columns
            else np.zeros_like(aw)
        )
        aw_ex = (
            early["active_wallets_ex_heavy"].astype(float).values
            if "active_wallets_ex_heavy" in early.columns
            else aw
        )

        x = early["months_since_launch"].astype(float).values
        y = safe_log1p(aw)
        slope = float(np.polyfit(x, y, 1)[0]) if len(x) >= 2 else np.nan

        max_aw = float(np.max(aw)) if len(aw) else np.nan
        last_aw = float(aw[-1]) if len(aw) else np.nan
        last_to_max = (last_aw / max_aw) if max_aw and max_aw > 0 else np.nan
        peak_idx = int(np.argmax(aw)) if len(aw) else 0
        months_since_peak = float(x[-1] - x[peak_idx]) if len(x) else np.nan

        # MoM volatility of log wallets
        if len(aw) >= 3:
            mom = np.diff(safe_log1p(aw))
            vol = float(np.std(mom))
        else:
            vol = np.nan

        ret = early["retention_prev_month"].mean() if "retention_prev_month" in early else np.nan
        new_share = float(early["new_wallets"].sum() / max(early["active_wallets"].sum(), 1))
        ret_share = (
            float(early["returning_wallets"].sum() / max(early["active_wallets"].sum(), 1))
            if "returning_wallets" in early
            else np.nan
        )
        tx_pw = float(early["tx_count"].sum() / max(early["active_wallets"].sum(), 1))
        gas_pt = float(early["gas_used"].sum() / max(early["tx_count"].sum(), 1))
        avg_n = (
            float(early["avg_n_protocols_in_tx"].mean())
            if "avg_n_protocols_in_tx" in early
            else np.nan
        )
        whale = (
            float(early["top10_wallet_share"].mean())
            if "top10_wallet_share" in early
            else np.nan
        )
        eco = (
            float(early["share_of_ecosystem_active_wallets"].mean())
            if "share_of_ecosystem_active_wallets" in early
            else np.nan
        )
        cat_sh = (
            float(early["share_of_category_active_wallets"].mean())
            if "share_of_category_active_wallets" in early
            else np.nan
        )
        heavy = np.nan
        if "active_wallets_ex_heavy" in early.columns:
            total = float(early["active_wallets"].sum())
            ex = float(early["active_wallets_ex_heavy"].sum())
            heavy = 1.0 - (ex / total) if total > 0 else np.nan

        launch_month = meta.get("launch_month")
        cat_g, eco_g = _market_growth(cat_month, launch_month, meta.get("category_group"))
        cohort_m1 = _cohort_m1_in_window(cohort, slug, launch_month, k)
        life_df = life if "slug" in life.columns else life.reset_index()
        is_version = _parent_has_prior(
            life_df, slug, meta.get("parent_protocol"), launch_month
        )

        rows.append({
            "slug": slug,
            "k": k,
            "category_group": meta.get("category_group"),
            "parent_protocol": meta.get("parent_protocol"),
            "has_token": int(bool(meta.get("has_token"))),
            "launch_year": int(launch_month.year) if pd.notna(launch_month) else np.nan,
            "launch_month": launch_month,
            "left_censored": bool(meta.get("left_censored", False)),
            "eligible_12m": bool(meta.get("eligible_12m", False)),
            "eligible_24m": bool(meta.get("eligible_24m", False)),
            # levels (log)
            "log_mean_wallets": float(safe_log1p(np.mean(aw))),
            "log_max_wallets": float(safe_log1p(max_aw)),
            "log_last_wallets": float(safe_log1p(last_aw)),
            "log_mean_tx": float(safe_log1p(np.mean(tx))),
            "log_mean_gas": float(safe_log1p(np.mean(gas))),
            "log_mean_fees": float(safe_log1p(np.mean(fees))),
            "log_mean_wallets_ex_heavy": float(safe_log1p(np.mean(aw_ex))),
            # raw helpers for baselines
            "mean_wallets": float(np.mean(aw)),
            "max_wallets": max_aw,
            "last_wallets": last_aw,
            # shape
            "wallet_growth_slope": slope,
            "last_to_max_ratio": last_to_max,
            "wallet_mom_volatility": vol,
            "months_since_inwindow_peak": months_since_peak,
            # quality
            "early_retention": float(ret) if pd.notna(ret) else np.nan,
            "cohort_m1_retention": cohort_m1,
            "early_new_wallet_share": new_share,
            "early_returning_share": ret_share,
            "early_tx_per_wallet": tx_pw,
            "early_gas_per_tx": gas_pt,
            "avg_n_protocols_in_tx": avg_n,
            # concentration
            "early_whale_share": whale,
            "early_heavy_wallet_share": heavy,
            # context
            "early_eco_share": eco,
            "early_cat_share": cat_sh,
            "launch_eco_growth_3m": eco_g,
            "launch_cat_growth_3m": cat_g,
            "is_new_version_of_existing_protocol": is_version,
        })
    return pd.DataFrame(rows)


def build_dataset(
    k: int,
    panel: Optional[pd.DataFrame] = None,
    life: Optional[pd.DataFrame] = None,
    cohort: Optional[pd.DataFrame] = None,
    cat_month: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Merge early features with post-window labels for window k."""
    if panel is None:
        panel = load_panel()
    if life is None:
        life = annotate_lifecycle(load_lifecycle(), load_static())
    if cat_month is None:
        try:
            cat_month = load_category_month()
        except Exception:
            cat_month = None
    if cohort is None:
        try:
            # Prefer raw cohort file (faster than expanded grid)
            cohort = pd.read_csv(
                __import__("pathlib").Path(__file__).resolve().parent.parent
                / "dapp_data_v2"
                / "cohort_retention.csv"
            )
            cohort["cohort_month"] = pd.to_datetime(cohort["cohort_month"], errors="coerce")
        except Exception:
            cohort = None

    feats = early_features(panel, life, k, cohort=cohort, cat_month=cat_month)
    labs = build_labels(panel, life, k=k)
    label_cols = [
        "slug",
        "y_sustained_12",
        "y_abs_12",
        "y_sustained_24",
        "y_eco_topq_12",
        "y_cond_sustained_12",
        "mean_wallets_10_12",
        "mean_wallets_22_24",
        "mean_eco_share_10_12",
        "wallets_m12",
        "wallets_m24",
        "window_max_wallets",
        "passed_1k_in_window",
        "survival_duration",
        "survival_event",
        "eco_share_q75",
    ]
    labs = labs[[c for c in label_cols if c in labs.columns]]
    # Drop overlapping meta from labels that features already has
    ds = feats.merge(labs, on="slug", how="inner")
    return ds


def main() -> None:
    setup_style()
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, nargs="+", default=[1, 3, 6])
    args = parser.parse_args()

    print("== features ==")
    panel = load_panel()
    life = annotate_lifecycle(load_lifecycle(), load_static())
    try:
        cat_month = load_category_month()
    except Exception:
        cat_month = None
    try:
        from pathlib import Path
        cohort = pd.read_csv(Path(__file__).resolve().parent.parent / "dapp_data_v2" / "cohort_retention.csv")
        cohort["cohort_month"] = pd.to_datetime(cohort["cohort_month"], errors="coerce")
    except Exception:
        cohort = None

    for k in args.k:
        print(f"  building dataset k={k}...")
        ds = build_dataset(k, panel=panel, life=life, cohort=cohort, cat_month=cat_month)
        savetable(ds, f"dataset_k{k}.csv")
        use = ds[ds["eligible_12m"] & ~ds["left_censored"]]
        print(
            f"    n={len(ds)} eligible={len(use)} "
            f"sustained_12_rate={use['y_sustained_12'].dropna().mean():.3f}"
        )
    print("== features done ==")


if __name__ == "__main__":
    main()
