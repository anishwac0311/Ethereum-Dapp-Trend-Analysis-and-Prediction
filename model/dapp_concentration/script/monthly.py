"""Monthly concentration from concentration_month.csv: ecosystem trend, scopes, market periods and market types.

Market periods: 2020 pre-boom, 2021 boom, 2022-23 downturn, 2024-25 recovery.
"""
from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter

from common import (GINI_HIGH, HHI_HIGH, MARKET_TYPES, PERIOD_COLOURS, PERIODS, market_period, market_type, record,
                    savefig)

V3_START = pd.Timestamp("2021-05-01")  # uniswap-v3 launches and splits uniswap's wallets with v2
BANDS = {"2020 pre-boom": ("2020-01-01", "2020-12-31"), "2021 boom": ("2021-01-01", "2021-12-31"),
         "2022-23 downturn": ("2022-01-01", "2023-12-31"), "2024-25 recovery": ("2024-01-01", "2025-12-31")}
SCOPE_COLOURS = {"ecosystem": "#222222", "DeFi": "#eb6834", "DEX": "#2a78d6",
                 "Gaming": "#eda100", "Infrastructure": "#1baf7a"}
PERIOD_MARKERS = dict(zip(PERIODS, [("o", "none"), ("o", None), ("^", None), ("s", None)]))


def v3_marker(ax) -> None:
    """Dashed line and label for the uniswap-v3 launch."""
    ax.axvline(V3_START, ls="--", color="#8C8C8C", lw=0.8)
    ax.text(V3_START, 1, "  uniswap-v3 launches", ha="left", va="center", fontsize=9, color="#666666")


def ecosystem_trend(con: pd.DataFrame) -> None:
    """Top-k shares and HHI/Gini of the whole ecosystem each month (active wallets, single protocols)."""
    eco = con.query("scope == 'ecosystem' and metric == 'active_wallets'")

    fig, ax = plt.subplots()
    v3_marker(ax)
    for col, label, colour, ls in [("top10_share", "Top 10", "#1D3B56", "-"),
                                   ("top5_share", "Top 5", "#2a78d6", (0, (6, 2))),
                                   ("top1_share", "Top 1", "#9B59B6", ":")]:
        ax.plot(eco["month"], eco[col], color=colour, ls=ls, lw=1.2, label=label)
    ax.set(ylim=(0, 1.02), ylabel="Share of active wallets")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
    savefig(fig, "share_by_month")

    fig, ax = plt.subplots()
    v3_marker(ax)
    ax.axhline(HHI_HIGH, ls=":", color="#666666", lw=0.8)
    ax.text(eco["month"].max(), HHI_HIGH + 0.02, "HHI 0.25: highly concentrated",
            ha="right", va="bottom", fontsize=9, color="#666666")
    ax.plot(eco["month"], eco["gini"], color="#1baf7a", lw=1.2, label="Gini")
    ax.plot(eco["month"], eco["hhi"], color="#eb6834", lw=1.2, label="HHI")
    ax.set(ylim=(0, 1.02), ylabel="Index")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2)
    savefig(fig, "index_by_month")


def scopes_and_periods(activity: pd.DataFrame, con: pd.DataFrame) -> None:
    """Concentration inside each category, averaged per market period, and the HHI x Gini market type."""
    monthly = activity.groupby(["period", "month"], observed=True).agg(
        active_dapps=("active_wallets", lambda s: (s > 0).sum()),
        active_wallets=("active_wallets", "sum"), tx_count=("tx_count", "sum")).reset_index()
    per_period = monthly.groupby("period", observed=True).agg(
        avg_active_dapps=("active_dapps", "mean"), avg_monthly_active_wallets=("active_wallets", "mean"),
        tx=("tx_count", "sum"), wallets=("active_wallets", "sum")).reset_index()
    per_period["tx_per_wallet"] = (per_period["tx"] / per_period["wallets"]).round(2)
    per_period["avg_active_dapps"] = per_period["avg_active_dapps"].round().astype(int)
    per_period["avg_monthly_active_wallets"] = per_period["avg_monthly_active_wallets"].round().astype(int)
    record(per_period.drop(columns=["tx", "wallets"]), "activity_by_period")

    by_month = con.query("metric in ['active_wallets', 'tx_count']")
    by_period = (by_month.groupby(["metric", "scope", "period"], observed=True)
                 [["n_dapps", "top1_share", "top10_share", "hhi", "gini"]].mean().reset_index())
    record(by_period, "concentration_by_period_scope")

    # Scopes with at least 5 DApps on average in every period
    wallets = by_period[by_period["metric"] == "active_wallets"]
    shown = sorted(s for s, g in wallets.groupby("scope") if g["n_dapps"].min() >= 5 and s != "ecosystem")
    shown = ["ecosystem"] + shown

    fig, axes = plt.subplots(2, 3, sharex=True, sharey=True)
    for ax, scope in zip(axes.flat, shown):
        for period, (start, end) in BANDS.items():
            ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color=PERIOD_COLOURS[period], alpha=.12, lw=0)
        g = by_month.query("metric == 'active_wallets' and scope == @scope")
        ax.plot(g["month"], g["hhi"], color="black", lw=0.8)
        ax.set_title(scope, fontsize=10)
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for ax in axes.flat[len(shown):]:
        ax.axis("off")
    for ax in axes[:, 0]:
        ax.set_ylabel("HHI (active wallets)")
    fig.legend(handles=[Patch(color=PERIOD_COLOURS[p], alpha=.3, label=p) for p in PERIODS],
               loc="outside lower center", ncol=4)
    savefig(fig, "hhi_by_scope_and_period")

    types = wallets[["scope", "period", "n_dapps", "hhi", "gini"]].copy()
    types["type"] = market_type(types["hhi"], types["gini"])
    types["n_dapps"] = types["n_dapps"].round().astype(int)
    types[["hhi", "gini"]] = types[["hhi", "gini"]].round(2)
    record(types, "market_type_by_period_scope")

    fig, ax = plt.subplots()
    ax.axhline(HHI_HIGH, ls="--", color="#A6A6A6", lw=0.9)
    ax.axvline(GINI_HIGH, ls="--", color="#A6A6A6", lw=0.9)
    for (x, y, ha, va), label in zip([(.99, .79, "right", "top"), (.99, .01, "right", "bottom"),
                                      (.01, .79, "left", "top"), (.01, .01, "left", "bottom")], MARKET_TYPES):
        ax.text(x, y, label, ha=ha, va=va, color="#737373", fontsize=10, style="italic")
    for scope in shown:
        g = types[types["scope"] == scope].sort_values("period")
        colour = SCOPE_COLOURS[scope]
        ax.plot(g["gini"], g["hhi"], color=colour, lw=1.4)
        for r in g.itertuples():
            marker, face = PERIOD_MARKERS[r.period]
            ax.plot(r.gini, r.hhi, marker=marker, ms=7, color=colour, mfc=face or colour, mew=1.2, ls="none")
        last = g.iloc[-1]
        ax.text(last["gini"] + .02, last["hhi"], scope, color=colour, fontsize=11, va="center")
    ax.set(xlim=(-0.05, 1.05), ylim=(-0.04, 0.84),
           xlabel="Gini  (inequality, including small DApps)", ylabel="HHI  (dominance by the largest)")
    handles = [Line2D([], [], marker=m, mfc=f or "black", color="black", ls="none", ms=7, label=p)
               for p, (m, f) in PERIOD_MARKERS.items()]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=4)
    savefig(fig, "market_type")


def dex(activity: pd.DataFrame, con: pd.DataFrame) -> None:
    """Inside DEX, the category that holds most of the top 10: top 5, largest DEX, and all uniswap versions."""
    dex_act = activity[activity["category_group"] == "DEX"]
    uniswap = (dex_act.assign(uni=dex_act["active_wallets"].where(dex_act["protocol"].str.startswith("uniswap"), 0))
               .groupby("month")[["uni", "active_wallets"]].sum())
    dex_month = con.query("scope == 'DEX' and metric == 'active_wallets'").set_index("month")
    shares = pd.DataFrame({"Top 5 DEXs": dex_month["top5_share"],
                           "Uniswap, all versions": uniswap["uni"] / uniswap["active_wallets"],
                           "Largest single DEX": dex_month["top1_share"]})
    by_year = shares.groupby(shares.index.year).mean().round(2).T
    by_year.columns = by_year.columns.astype(str)
    record(by_year.rename_axis("measure").reset_index(), "dex_concentration_by_year")

    fig, ax = plt.subplots()
    for col, colour in zip(shares.columns, ["#1D3B56", "#2a78d6", "#9B59B6"]):
        ax.plot(shares.index, shares[col], color=colour, lw=1.2, label=col)
    ax.set(ylim=(0, 1.02), ylabel="Share of DEX active wallets")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
    savefig(fig, "dex_concentration")


def run(activity: pd.DataFrame, categories: pd.DataFrame, con: pd.DataFrame) -> None:
    activity = activity.merge(categories, on="protocol", how="left")
    activity["period"] = market_period(activity["month"])
    con = con.assign(period=market_period(con["month"]))
    ecosystem_trend(con)
    scopes_and_periods(activity, con)
    dex(activity, con)
