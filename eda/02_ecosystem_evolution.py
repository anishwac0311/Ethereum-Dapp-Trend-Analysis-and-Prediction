"""Ecosystem evolution: category growth/decline and concentration."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    load_category_month,
    load_concentration,
    load_lifecycle,
    load_panel,
    savefig,
    savetable,
    setup_style,
)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def lorenz_curve(values: np.ndarray):
    v = np.sort(np.asarray(values, dtype=float))
    v = v[v >= 0]
    if len(v) == 0 or v.sum() == 0:
        return np.array([0, 1]), np.array([0, 1])
    cum = np.cumsum(v)
    cum = np.insert(cum, 0, 0)
    x = np.linspace(0, 1, len(cum))
    y = cum / cum[-1]
    return x, y


def main() -> None:
    setup_style()
    print("== 02 ecosystem evolution ==")
    cat = load_category_month()
    conc = load_concentration()
    panel = load_panel()
    life = load_lifecycle()

    # --- Stacked area: absolute ---
    abs_p = cat.pivot(index="month", columns="category_group", values="active_wallets").fillna(0)
    fig, ax = plt.subplots(figsize=(12, 5))
    abs_p.plot.area(ax=ax, stacked=True, alpha=0.85, linewidth=0)
    ax.set_ylabel("Active wallets")
    ax.set_title("Ecosystem active wallets by category_group")
    ax.legend(loc="upper left", ncol=2, fontsize=8)
    savefig(fig, "02_wallets_by_category_absolute.png")

    # --- Stacked area: shares ---
    share = abs_p.div(abs_p.sum(axis=1).replace(0, np.nan), axis=0)
    fig, ax = plt.subplots(figsize=(12, 5))
    share.plot.area(ax=ax, stacked=True, alpha=0.85, linewidth=0)
    ax.set_ylabel("Share of ecosystem wallets")
    ax.set_ylim(0, 1)
    ax.set_title("Category share of ecosystem active wallets")
    ax.legend(loc="upper left", ncol=2, fontsize=8)
    savefig(fig, "02_wallets_by_category_share.png")

    # --- 12m growth heatmap ---
    g12 = cat.pivot(index="category_group", columns="month", values="growth_12m")
    # Keep recent years with decent coverage
    cols = [c for c in g12.columns if c >= pd.Timestamp("2021-01-01")]
    g12p = g12[cols]
    fig, ax = plt.subplots(figsize=(14, 5))
    sns.heatmap(
        g12p,
        cmap="RdYlGn",
        center=0,
        ax=ax,
        cbar_kws={"label": "12m growth"},
        xticklabels=max(1, len(cols) // 12),
    )
    ax.set_title("12-month wallet growth by category")
    ax.set_xlabel("")
    savefig(fig, "02_growth_12m_heatmap.png")

    # Growth summary table (latest available non-null per category)
    latest = (
        cat.dropna(subset=["growth_12m"])
        .sort_values("month")
        .groupby("category_group")
        .tail(1)[["category_group", "month", "active_wallets", "growth_3m", "growth_12m", "active_dapps"]]
    )
    savetable(latest.sort_values("growth_12m", ascending=False), "02_latest_category_growth.csv")

    # --- Launches per category per year ---
    life = life.copy()
    life["launch_year"] = life["launch_month"].dt.year
    launches = (
        life.groupby(["launch_year", "category_group"])
        .size()
        .reset_index(name="n_launches")
    )
    savetable(launches, "02_launches_by_year_category.csv")
    pivot_l = launches.pivot(index="launch_year", columns="category_group", values="n_launches").fillna(0)
    fig, ax = plt.subplots(figsize=(10, 5))
    pivot_l.plot(kind="bar", stacked=True, ax=ax, width=0.85)
    ax.set_ylabel("# launches")
    ax.set_title("DApp launches by year and category_group")
    ax.legend(loc="upper left", ncol=2, fontsize=8)
    ax.tick_params(axis="x", rotation=0)
    savefig(fig, "02_launches_by_year.png")

    # --- Concentration over time (ecosystem) ---
    eco = conc[(conc["scope"] == "ecosystem") & (conc["metric"] == "active_wallets")].copy()
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    for col, label in [("hhi", "HHI"), ("gini", "Gini")]:
        axes[0].plot(eco["month"], eco[col], label=label, lw=2)
    axes[0].set_ylabel("Index")
    axes[0].set_title("Ecosystem concentration (active wallets)")
    axes[0].legend()
    for col, label in [
        ("top1_share", "Top 1"),
        ("top5_share", "Top 5"),
        ("top10_share", "Top 10"),
    ]:
        axes[1].plot(eco["month"], eco[col], label=label, lw=2)
    axes[1].set_ylabel("Share")
    axes[1].set_xlabel("Month")
    axes[1].legend()
    axes[1].set_ylim(0, 1)
    savefig(fig, "02_concentration_ecosystem.png")
    savetable(eco, "02_concentration_ecosystem.csv")

    # Category-level top5 share
    cat_conc = conc[
        (conc["scope"] == "category")
        & (conc["metric"] == "active_wallets")
        & (conc["category_group"] != "ALL")
    ].copy()
    if len(cat_conc):
        top5 = cat_conc.pivot(index="month", columns="category_group", values="top5_share")
        fig, ax = plt.subplots(figsize=(12, 5))
        for col in top5.columns:
            ax.plot(top5.index, top5[col], label=col, lw=1.5, alpha=0.85)
        ax.set_ylabel("Top-5 share")
        ax.set_ylim(0, 1)
        ax.set_title("Within-category top-5 concentration")
        ax.legend(ncol=2, fontsize=8)
        savefig(fig, "02_concentration_by_category.png")

    # --- Lorenz curve (most recent year with data) ---
    last_year = int(panel["month"].dt.year.max())
    # Use last full-ish year month: Dec of last_year or latest month
    recent = panel[panel["month"].dt.year == last_year]
    if recent.empty:
        recent = panel[panel["month"] == panel["month"].max()]
    # Aggregate wallets per DApp over the year
    yearly = recent.groupby("slug")["active_wallets"].sum()
    x, y = lorenz_curve(yearly.values)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot(x, y, lw=2.5, color="steelblue", label=f"{last_year} wallet activity")
    ax.plot([0, 1], [0, 1], ls="--", color="gray", label="Equality")
    ax.fill_between(x, y, x, alpha=0.15, color="steelblue")
    ax.set_xlabel("Cumulative share of DApps")
    ax.set_ylabel("Cumulative share of wallets")
    ax.set_title(f"Lorenz curve — {last_year} active-wallet activity")
    ax.legend()
    ax.set_aspect("equal")
    savefig(fig, "02_lorenz_curve.png")

    # Gini from Lorenz
    gini = 1 - 2 * np.trapezoid(y, x)
    savetable(pd.DataFrame({"year": [last_year], "gini_wallets": [gini], "n_dapps": [len(yearly)]}),
              "02_lorenz_gini.csv")
    print(f"  {last_year} Gini (wallet activity): {gini:.3f}")
    print("== 02 done ==")


if __name__ == "__main__":
    main()
