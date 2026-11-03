"""Candidate model features from the Q4 findings: how a DApp acquires users in its first k months.

One row per DApp and window k, on the deploy clock and the same 512 DApps as model/labels.py, so the table can be
joined to model/features.py on (slug, k). Only months 0..k-1 are used, so nothing after the window leaks in.

Acquisition (new group): cumulative wallets, whether new users are still arriving, and how clean the start is.
Context (three additions, from Q3): how concentrated the DApp's category was in its launch month, how much the
category leader held, and how many DApps were competing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import DATA, GROUPS, RAW, compare_groups, record

KS = (1, 3, 6)
EMPTY_START = 10   # fewer wallets than this in the first month with a user counts as an empty (test-wallet) start
ACQUISITION = ["log_cum_wallets_k", "cum_growth_last", "growth_decay", "months_to_first_user_k", "starts_empty"]
CONTEXT = ["category_hhi_at_launch", "category_top1_share_at_launch", "category_n_dapps_at_launch"]


def window_features(g: pd.DataFrame, k: int) -> dict:
    """Features from one DApp's months 0..k-1 (g sorted by month)."""
    cum = g["cum_wallets"].to_numpy(float)[:k]
    growth = np.full(len(cum), np.nan)   # monthly growth of cumulative wallets; undefined while still at 0
    growth[1:] = np.where(cum[:-1] > 0, cum[1:] / np.where(cum[:-1] > 0, cum[:-1], 1) - 1, np.nan)
    has_user = np.flatnonzero(cum >= 1)
    first_user = int(has_user[0]) if len(has_user) else k
    return {
        "log_cum_wallets_k": np.log1p(cum[-1]),
        # New users in the last window month, relative to everyone so far
        "cum_growth_last": growth[-1] if k >= 2 else np.nan,
        # Log growth in the last month minus the first; below 0 means new users are slowing down
        "growth_decay": np.log1p(growth[-1]) - np.log1p(growth[1]) if k >= 3 else np.nan,
        "months_to_first_user_k": first_user,
        "starts_empty": int(first_user == k or cum[first_user] < EMPTY_START),
    }


def build(panel: pd.DataFrame) -> pd.DataFrame:
    dapps = pd.read_csv(DATA / "dapp_growth_summary.csv", parse_dates=["launch_month"])
    rows = panel[panel["slug"].isin(dapps["slug"])].sort_values(["slug", "month"])
    windows = {slug: g for slug, g in rows.groupby("slug")}

    hhi = pd.read_csv(RAW / "concentration_month.csv", parse_dates=["month"])
    hhi = (hhi[(hhi["scope"] == "category") & (hhi["metric"] == "active_wallets")]
           .rename(columns={"month": "launch_month", "hhi": "category_hhi_at_launch",
                            "top1_share": "category_top1_share_at_launch", "n_dapps": "category_n_dapps_at_launch"})
           [["category_group", "launch_month", *CONTEXT]])
    context = dapps[["slug", "category_group", "launch_month"]].merge(hhi, on=["category_group", "launch_month"],
                                                                      how="left")

    out = pd.DataFrame([{"slug": slug, "k": k, **window_features(windows[slug], k)}
                        for slug in dapps["slug"] for k in KS])
    out = out.merge(context[["slug", *CONTEXT]], on="slug", how="left")
    return out[["slug", "k", *ACQUISITION, *CONTEXT]]


def describe(features: pd.DataFrame, k: int = 3) -> pd.DataFrame:
    """Median by outcome and a one-feature AUC at window k. Descriptive only: no model, no holdout."""
    labels = pd.read_csv(DATA / "dapp_growth_summary.csv")[["slug", f"success_k{k}"]]
    d = features[features["k"] == k].merge(labels, on="slug")
    d["group"] = np.where(d[f"success_k{k}"] == 1, "Successful", "Not successful")
    rows = []
    for col in ACQUISITION + CONTEXT:
        test = compare_groups(d, col, f"k = {k}")
        valid = d[[col, "group"]].dropna()
        ranks = valid[col].rank()
        n1 = (valid["group"] == "Successful").sum()
        n0 = len(valid) - n1
        auc = (ranks[valid["group"] == "Successful"].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
        rows.append({"feature": col, "group": "Acquisition" if col in ACQUISITION else "Context",
                     "median_successful": test["median"].iloc[1], "median_not": test["median"].iloc[0],
                     "auc": auc, "p_value": test["p_value"].iloc[0], "n_missing": int(d[col].isna().sum())})
    return pd.DataFrame(rows)


def run(panel: pd.DataFrame) -> None:
    features = build(panel)
    features.to_csv(DATA / "dapp_acquisition_features.csv", index=False)
    summary = record(describe(features), "acquisition_features_k3")
    print(f"{features['slug'].nunique()} DApps x {len(KS)} windows")
    print(summary.round(3).to_string(index=False))
