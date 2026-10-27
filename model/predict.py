"""Score young / recent DApps with calibrated success probabilities."""
from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from common import (
    annotate_lifecycle,
    load_lifecycle,
    load_panel,
    load_static,
    savetable,
    setup_style,
)
from features import FEATURE_COLS, build_dataset
from train_eval import ARTIFACTS, feature_matrix_cols, make_hgb, calibrate_pipe, eligible_frame, time_holdout

PRIMARY_TARGET = "y_sustained_12"


def load_or_train_calibrated(k: int = 3):
    path = ARTIFACTS / f"hgb_calibrated_k{k}.joblib"
    if path.exists():
        blob = joblib.load(path)
        return blob["model"], blob["feature_cols"]

    # Train on the fly if artifact missing
    ds = build_dataset(k)
    df = eligible_frame(ds, PRIMARY_TARGET)
    train, _ = time_holdout(df)
    feature_cols = list(FEATURE_COLS)
    cal = calibrate_pipe(make_hgb(feature_cols), train, feature_cols, PRIMARY_TARGET)
    joblib.dump(
        {"model": cal, "feature_cols": feature_cols, "k": k, "target": PRIMARY_TARGET},
        path,
    )
    return cal, feature_cols


def score_dataset(ds: pd.DataFrame, model, feature_cols: list[str], k: int) -> pd.DataFrame:
    cols = feature_matrix_cols(feature_cols)
    for c in cols:
        if c not in ds.columns:
            ds[c] = np.nan
    ds = ds.copy()
    ds["has_token"] = ds["has_token"].astype(int)
    proba = model.predict_proba(ds[cols])[:, 1]
    out = ds[
        [
            c
            for c in (
                "slug",
                "category_group",
                "parent_protocol",
                "has_token",
                "launch_year",
                "launch_month",
                "last_wallets",
                "max_wallets",
                "log_last_wallets",
                "early_retention",
                "early_whale_share",
                "early_eco_share",
                "last_to_max_ratio",
                "y_sustained_12",
                "eligible_12m",
                "left_censored",
            )
            if c in ds.columns
        ]
    ].copy()
    out["k"] = k
    out["p_sustained_12"] = proba
    out["rank"] = out["p_sustained_12"].rank(ascending=False, method="min").astype(int)
    return out.sort_values("p_sustained_12", ascending=False)


def main() -> None:
    setup_style()
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument(
        "--launch-year",
        type=int,
        default=2025,
        help="Score DApps launched in this year (default 2025). Use 0 for all.",
    )
    args = parser.parse_args()

    print(f"== predict k={args.k} ==")
    model, feature_cols = load_or_train_calibrated(args.k)

    path = Path(__file__).resolve().parent / "tables" / f"dataset_k{args.k}.csv"
    if path.exists():
        ds = pd.read_csv(path)
    else:
        ds = build_dataset(args.k)
        savetable(ds, f"dataset_k{args.k}.csv")

    if args.launch_year and args.launch_year > 0:
        scored = score_dataset(
            ds[ds["launch_year"] == args.launch_year], model, feature_cols, args.k
        )
        savetable(scored, f"predictions_launch{args.launch_year}_k{args.k}.csv")
        # Actionable subset: enough early activity for features to be meaningful
        actionable = scored[scored["max_wallets"].fillna(0) >= 100].copy()
        actionable["rank"] = (
            actionable["p_sustained_12"].rank(ascending=False, method="min").astype(int)
        )
        actionable = actionable.sort_values("p_sustained_12", ascending=False)
        savetable(
            actionable,
            f"predictions_launch{args.launch_year}_k{args.k}_active100.csv",
        )
        print(f"  scored {len(scored)} DApps launched in {args.launch_year}")
        print(f"  actionable (max_wallets>=100): {len(actionable)}")
        print(actionable.head(15).to_string(index=False))
    else:
        scored = score_dataset(ds, model, feature_cols, args.k)
        savetable(scored, f"predictions_all_k{args.k}.csv")
        print(f"  scored {len(scored)} DApps")

    # Also dump holdout-year predictions for inspection
    hold = ds[ds["launch_year"].isin([2023, 2024])]
    if len(hold):
        scored_h = score_dataset(hold, model, feature_cols, args.k)
        savetable(scored_h, f"predictions_holdout_k{args.k}.csv")

    print("== predict done ==")


if __name__ == "__main__":
    main()
