"""Paths and settings for the time-split checks. The team model in model/ is used as it is."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HOME = Path(__file__).resolve().parents[1]
ROOT = HOME.parents[1]
MODEL = ROOT / "model"                   # the team model: dataset builder, models, metrics
DATA = HOME / "data"                     # data built here
TABLES = HOME / "results" / "tables"
FIGURES = HOME / "results" / "figures"
for d in (DATA, TABLES, FIGURES):
    d.mkdir(parents=True, exist_ok=True)

# The team's modules import each other by plain name (common, features, ...), so model/ goes on the path
sys.path.insert(0, str(MODEL))

K = 3                                    # months observed, as in the team's headline results
TARGET = "y_sustained_12"
# The outcome is the mean of months 10-12, counted from 0, so a DApp's answer is known 12 months after launch
OUTCOME_LAG_MONTHS = 12

# Market events that start each test period: the Terra/UST collapse and the Dencun upgrade
EVENTS = {"Terra": pd.Timestamp("2022-05-01"), "Dencun": pd.Timestamp("2024-03-01")}
HOLDOUT_START = pd.Timestamp("2023-01-01")   # the team's holdout: launches in 2023-24


def record(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Save a table to results/tables/<name>.csv and return it for display."""
    df.to_csv(TABLES / f"{name}.csv", index=False)
    return df


# Every figure has the same size, so figures shown side by side line up (same style as the Q3 and Q4 folders)
FIGSIZE = (8, 5)
DPI = 150


def setup_style() -> None:
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
