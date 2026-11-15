"""Shared paths, settings, data readers and helpers for the concentration analysis."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HOME = Path(__file__).resolve().parents[1]
ROOT = HOME.parents[1]
RAW = ROOT / "dapp_data_v2"              # input CSVs, shared with the rest of the project
DATA = HOME / "data"                     # data built here
TABLES = HOME / "results" / "tables"
FIGURES = HOME / "results" / "figures"
for d in (DATA, TABLES, FIGURES):
    d.mkdir(parents=True, exist_ok=True)

# Activity measures compared throughout; *_ex_heavy drops very high-frequency wallets (mostly bots)
METRICS = ["active_wallets", "active_wallets_ex_heavy", "tx_count", "gas_used"]
TOP_K = 10

# Market periods compared in step 4
PERIODS = ["2020 pre-boom", "2021 boom", "2022-23 downturn", "2024-25 recovery"]
PERIOD_COLOURS = dict(zip(PERIODS, ["#898781", "#eb6834", "#2a78d6", "#1baf7a"]))

# Year colours: ggplot's default hue palette for six levels
YEAR_COLOURS = dict(zip(range(2020, 2026),
                        ["#F8766D", "#B79F00", "#00BA38", "#00BFC4", "#619CFF", "#F564E3"]))

# HHI x Gini market types. HHI 0.25 is the usual "highly concentrated" line; the Gini cut is our choice
HHI_HIGH = 0.25
GINI_HIGH = 0.6
MARKET_TYPES = ["few lead + long tail",         # high HHI, high Gini
                "competitive top + long tail",  # low HHI, high Gini
                "few DApps with one big lead",  # high HHI, low Gini
                "evenly spread"]                # low HHI, low Gini


def market_period(month: pd.Series) -> pd.Categorical:
    year = month.dt.year
    label = np.select([year == 2020, year == 2021, year.isin([2022, 2023])], PERIODS[:3], PERIODS[3])
    return pd.Categorical(label, categories=PERIODS, ordered=True)


def read_activity() -> pd.DataFrame:
    """Same rule as concentration_month.csv: drop a DApp's activity before its first contract deploy month."""
    first = pd.read_csv(RAW / "dapp_static.csv", usecols=["slug", "first_deployed"])
    first = pd.DataFrame({"protocol": first["slug"],
                          "first_month": pd.to_datetime(first["first_deployed"]).dt.to_period("M").dt.to_timestamp()})
    act = pd.read_csv(RAW / "activity.csv", usecols=["protocol", "month", *METRICS], parse_dates=["month"])
    act = act.merge(first, on="protocol", how="left")
    act = act[act["first_month"].isna() | (act["month"] >= act["first_month"])]
    return act.drop(columns="first_month").reset_index(drop=True)


def read_categories() -> pd.DataFrame:
    cat = pd.read_csv(RAW / "protocols.csv", usecols=["slug", "category_group", "parent_protocol"])
    return cat.rename(columns={"slug": "protocol"})


def read_concentration() -> pd.DataFrame:
    """Monthly concentration per market from the team file; scope = "ecosystem" or the category name."""
    con = pd.read_csv(RAW / "concentration_month.csv", parse_dates=["month"])
    con["scope"] = np.where(con["scope"] == "ecosystem", "ecosystem", con["category_group"])
    return con[["scope", "month", "metric", "n_dapps", "top1_share", "top5_share", "top10_share", "hhi", "gini"]]


def gini(x) -> float:
    """Gini of non-negative sizes (0 = all equal, close to 1 = one DApp holds everything)."""
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    return 2 * np.sum(np.arange(1, n + 1) * x) / (n * x.sum()) - (n + 1) / n


def concentration(x) -> dict:
    """Concentration measures for one market: x = size of each DApp."""
    x = np.asarray(x, dtype=float)
    x = x[x > 0]
    share = np.sort(x / x.sum())[::-1]
    return {"n_dapps": len(x),
            "top1_share": share[0],
            "top5_share": share[:5].sum(),
            "top10_share": share[:10].sum(),
            "hhi": np.sum(share ** 2),
            "gini": gini(x)}


def market_type(hhi: pd.Series, gini_: pd.Series) -> pd.Categorical:
    label = np.select([(hhi >= HHI_HIGH) & (gini_ >= GINI_HIGH),
                       (hhi < HHI_HIGH) & (gini_ >= GINI_HIGH),
                       hhi >= HHI_HIGH],
                      MARKET_TYPES[:3], MARKET_TYPES[3])
    return pd.Categorical(label, categories=MARKET_TYPES)


def size_by_year(activity: pd.DataFrame, metric: str, unit: str = "protocol") -> pd.DataFrame:
    """Average monthly size per DApp and year; months without activity count as 0."""
    act = activity.assign(year=activity["month"].dt.year)
    n_months = act.groupby("year")["month"].nunique().rename("n_months")
    out = act.groupby([unit, "year"], as_index=False)[metric].sum().join(n_months, on="year")
    out["size"] = out[metric] / out["n_months"]
    return out.loc[out["size"] > 0, [unit, "year", "size"]].reset_index(drop=True)


def record(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Save a summary table to results/tables/<name>.csv and return it for display."""
    df.to_csv(TABLES / f"{name}.csv", index=False)
    return df


# Every figure has the same size, so figures shown side by side line up
FIGSIZE = (8, 5)
DPI = 150


def setup_style() -> None:
    """A light, minimal look close to ggplot's theme_minimal, with one size for every figure."""
    plt.rcParams.update({
        "figure.figsize": FIGSIZE, "figure.constrained_layout.use": True,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.grid": True, "grid.color": "#EBEBEB", "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.spines.bottom": False,
        "xtick.major.size": 0, "ytick.major.size": 0,
        "xtick.color": "#4D4D4D", "ytick.color": "#4D4D4D",
        "axes.labelcolor": "#1A1A1A", "font.size": 10, "legend.frameon": False,
    })


def savefig(fig, name: str) -> None:
    fig.savefig(FIGURES / f"{name}.png", dpi=DPI)
    plt.close(fig)
