"""Data quality, coverage, censoring, heavy-wallet share, leakage table."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    LEAKAGE_NOTES,
    annotate_lifecycle,
    heavy_wallet_share,
    load_lifecycle,
    load_panel,
    load_static,
    savefig,
    savetable,
    setup_style,
)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def main() -> None:
    setup_style()
    print("== 01 data quality ==")
    panel = load_panel()
    static = load_static()
    life = annotate_lifecycle(load_lifecycle(), static)

    # --- Missingness ---
    miss = (
        panel.isna().mean()
        .sort_values(ascending=False)
        .rename("frac_missing")
        .reset_index()
        .rename(columns={"index": "column"})
    )
    savetable(miss, "01_panel_missingness.csv")

    fig, ax = plt.subplots(figsize=(10, 5))
    top = miss.head(20)
    sns.barplot(data=top, y="column", x="frac_missing", ax=ax, color="steelblue")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Fraction missing")
    ax.set_title("Panel missingness (top 20 columns)")
    savefig(fig, "01_panel_missingness.png")

    # --- Coverage: DApps per month ---
    cov = (
        panel.groupby("month")
        .agg(n_dapps=("slug", "nunique"),
             active_wallets=("active_wallets", "sum"),
             tx_count=("tx_count", "sum"))
        .reset_index()
    )
    savetable(cov, "01_coverage_by_month.csv")

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    axes[0].plot(cov["month"], cov["n_dapps"], color="steelblue", lw=2)
    axes[0].set_ylabel("# active DApps")
    axes[0].set_title("Coverage: DApps with activity per month")
    axes[1].semilogy(cov["month"], cov["active_wallets"], color="darkorange", lw=2)
    axes[1].set_ylabel("Sum active wallets (log)")
    axes[1].set_xlabel("Month")
    savefig(fig, "01_coverage_timeline.png")

    # Coverage by category
    cat_cov = (
        panel.groupby(["month", "category_group"])["slug"]
        .nunique()
        .reset_index(name="n_dapps")
    )
    pivot = cat_cov.pivot(index="month", columns="category_group", values="n_dapps").fillna(0)
    fig, ax = plt.subplots(figsize=(12, 5))
    pivot.plot.area(ax=ax, stacked=True, alpha=0.85, linewidth=0)
    ax.set_ylabel("# DApps")
    ax.set_title("Active DApps by category_group over time")
    ax.legend(loc="upper left", ncol=2, fontsize=8)
    savefig(fig, "01_coverage_by_category.png")

    # --- Static vs panel gap ---
    panel_slugs = set(panel["slug"].unique())
    static_slugs = set(static["slug"].unique())
    missing_panel = sorted(static_slugs - panel_slugs)
    gap_df = static[static["slug"].isin(missing_panel)][
        ["slug", "name", "category_group", "first_deployed", "n_contracts"]
    ]
    savetable(gap_df, "01_static_without_panel.csv")
    print(f"  static DApps with no panel rows: {len(missing_panel)}")

    # --- Censoring ---
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    axes[0].bar(
        ["left_censored", "not"],
        [life["left_censored"].sum(), (~life["left_censored"]).sum()],
        color=["#c44e52", "#4c72b0"],
    )
    axes[0].set_title("Left-censoring\n(first_deployed < 2020-01)")
    axes[0].set_ylabel("# DApps")

    axes[1].hist(life["follow_up_months"].dropna(), bins=20, color="steelblue", edgecolor="white")
    axes[1].axvline(12, color="red", ls="--", label="12m")
    axes[1].set_title("Follow-up months available")
    axes[1].set_xlabel("Months from launch to panel end")
    axes[1].legend()

    elig = life["eligible_12m"].value_counts()
    axes[2].bar(
        ["eligible_12m", "not"],
        [elig.get(True, 0), elig.get(False, 0)],
        color=["#55a868", "#c44e52"],
    )
    axes[2].set_title("Eligible for 12m outcome")
    savefig(fig, "01_censoring.png")

    censor_summary = pd.DataFrame({
        "metric": [
            "n_lifecycle",
            "left_censored",
            "eligible_12m",
            "eligible_24m",
            "median_follow_up",
        ],
        "value": [
            len(life),
            int(life["left_censored"].sum()),
            int(life["eligible_12m"].sum()),
            int(life["eligible_24m"].sum()),
            float(life["follow_up_months"].median()),
        ],
    })
    savetable(censor_summary, "01_censoring_summary.csv")

    # --- Panel gaps (zero-activity months inside span) ---
    gap_rows = []
    for slug, g in panel.groupby("slug"):
        g = g.sort_values("month")
        if len(g) < 2:
            continue
        months = pd.period_range(g["month"].iloc[0], g["month"].iloc[-1], freq="M")
        present = set(g["month"].dt.to_period("M"))
        missing = [m for m in months if m not in present]
        if missing:
            gap_rows.append({
                "slug": slug,
                "span_months": len(months),
                "observed_months": len(g),
                "gap_months": len(missing),
                "gap_frac": len(missing) / len(months),
            })
    gaps = pd.DataFrame(gap_rows)
    if len(gaps):
        savetable(gaps.sort_values("gap_frac", ascending=False), "01_panel_gaps.csv")
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(gaps["gap_frac"], bins=20, color="steelblue", edgecolor="white")
        ax.set_xlabel("Fraction of months missing inside active span")
        ax.set_ylabel("# DApps")
        ax.set_title(f"Internal panel gaps ({len(gaps)} DApps with ≥1 gap)")
        savefig(fig, "01_panel_gaps.png")
    else:
        print("  no internal panel gaps found")

    # --- Heavy wallet share ---
    hw = heavy_wallet_share(panel)
    hw_month = (
        hw.groupby("month")
        .agg(
            heavy_share_wallets=("heavy_share_active_wallets", "median"),
            heavy_share_tx=("heavy_share_tx_count", "median"),
            heavy_share_gas=("heavy_share_gas_used", "median"),
        )
        .reset_index()
    )
    savetable(hw_month, "01_heavy_wallet_share_month.csv")

    fig, ax = plt.subplots(figsize=(11, 4))
    for col, label in [
        ("heavy_share_wallets", "wallets"),
        ("heavy_share_tx", "tx"),
        ("heavy_share_gas", "gas"),
    ]:
        ax.plot(hw_month["month"], hw_month[col], label=label, lw=2)
    ax.set_ylabel("Median heavy-wallet share")
    ax.set_title("Activity attributable to heavy wallets (median across DApps)")
    ax.legend()
    ax.set_ylim(0, 1)
    savefig(fig, "01_heavy_wallet_share.png")

    # --- Leakage table ---
    leak = pd.DataFrame(LEAKAGE_NOTES)
    savetable(leak, "01_leakage_risks.csv")
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.axis("off")
    colors = {"high": "#f4cccc", "medium": "#ffe599", "low": "#d9ead3"}
    table = ax.table(
        cellText=leak.values,
        colLabels=leak.columns,
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.2, 1.6)
    for i, risk in enumerate(leak["risk"]):
        table[(i + 1, 1)].set_facecolor(colors.get(risk, "white"))
    ax.set_title("Feature leakage risks for predictive modelling", pad=20)
    savefig(fig, "01_leakage_table.png")

    # Lifecycle label counts
    lc = life["lifecycle_label"].value_counts().rename_axis("label").reset_index(name="n")
    savetable(lc, "01_lifecycle_counts.csv")
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.barplot(data=lc, x="n", y="label", ax=ax, palette="muted")
    ax.set_title("Lifecycle labels (rule-based)")
    ax.set_xlabel("# DApps")
    savefig(fig, "01_lifecycle_counts.png")

    print("== 01 done ==")


if __name__ == "__main__":
    main()
