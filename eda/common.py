"""Shared loaders, flags, and plotting helpers for dapp_data_v2 EDA."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # non-interactive; avoids Tk threading crashes on Windows
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "dapp_data_v2"
EDA = Path(__file__).resolve().parent
FIG = EDA / "figures"
FIG_HTML = FIG / "html"
TABLES = EDA / "tables"
CLUSTER_ASSIGN = TABLES / "trajectory_clusters.csv"

PANEL_START = pd.Timestamp("2020-01-01")
PANEL_END = pd.Timestamp("2025-12-01")

for d in (FIG, FIG_HTML, TABLES):
    d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
def setup_style() -> None:
    sns.set_theme(style="whitegrid", context="talk", font_scale=0.85)
    plt.rcParams.update({
        "figure.dpi": 120,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


def savefig(fig: plt.Figure, name: str) -> Path:
    """Save figure as PNG under eda/figures/."""
    path = FIG / name
    if not path.suffix:
        path = path.with_suffix(".png")
    fig.savefig(path)
    plt.close(fig)
    print(f"  saved {path.relative_to(EDA)}")
    return path


def savetable(df: pd.DataFrame, name: str) -> Path:
    path = TABLES / name
    if not path.suffix:
        path = path.with_suffix(".csv")
    df.to_csv(path, index=False)
    print(f"  saved {path.relative_to(EDA)}")
    return path


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def _parse_month(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.to_period("M").dt.to_timestamp()


def load_panel() -> pd.DataFrame:
    df = pd.read_csv(DATA / "dapp_panel.csv")
    for col in ("month", "listed_date", "first_deployed"):
        if col in df.columns:
            df[col] = _parse_month(df[col]) if col == "month" else pd.to_datetime(df[col], errors="coerce")
    df["month"] = _parse_month(df["month"])
    bool_cols = [c for c in ("has_token",) if c in df.columns]
    for c in bool_cols:
        df[c] = df[c].astype(str).str.lower().isin(("true", "1", "yes"))
    return df


def load_static() -> pd.DataFrame:
    df = pd.read_csv(DATA / "dapp_static.csv")
    for col in ("listed_date", "first_deployed", "first_month"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if "has_token" in df.columns:
        df["has_token"] = df["has_token"].astype(str).str.lower().isin(("true", "1", "yes"))
    return df


def load_lifecycle() -> pd.DataFrame:
    df = pd.read_csv(DATA / "dapp_lifecycle.csv")
    for col in ("launch_month", "peak_month"):
        if col in df.columns:
            df[col] = _parse_month(df[col])
    if "has_token" in df.columns:
        df["has_token"] = df["has_token"].astype(str).str.lower().isin(("true", "1", "yes"))
    return df


def load_category_month() -> pd.DataFrame:
    df = pd.read_csv(DATA / "category_month.csv")
    df["month"] = _parse_month(df["month"])
    return df


def load_concentration() -> pd.DataFrame:
    df = pd.read_csv(DATA / "concentration_month.csv")
    df["month"] = _parse_month(df["month"])
    return df


def load_cohort_retention() -> pd.DataFrame:
    """Load cohort retention and fill missing (retained=0) cells."""
    df = pd.read_csv(DATA / "cohort_retention.csv")
    df["cohort_month"] = _parse_month(df["cohort_month"])
    # Expand to full grid per protocol x cohort x months_since
    max_ms = int(df["months_since"].max())
    rows = []
    for (proto, cm), g in df.groupby(["protocol", "cohort_month"], sort=False):
        size = int(g["cohort_size"].iloc[0])
        lookup = g.set_index("months_since")["retained"]
        for ms in range(0, max_ms + 1):
            retained = int(lookup.get(ms, 0))
            rows.append({
                "protocol": proto,
                "cohort_month": cm,
                "months_since": ms,
                "retained": retained,
                "cohort_size": size,
                "retention_rate": retained / size if size > 0 else np.nan,
            })
    return pd.DataFrame(rows)


def load_activity() -> pd.DataFrame:
    df = pd.read_csv(DATA / "activity.csv")
    df["month"] = _parse_month(df["month"])
    return df


# ---------------------------------------------------------------------------
# Censoring / eligibility flags
# ---------------------------------------------------------------------------
def annotate_lifecycle(life: pd.DataFrame, static: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Add left_censored, follow_up_months, eligible_12m flags."""
    out = life.copy()
    if static is None:
        static = load_static()
    st = static[["slug", "first_deployed"]].drop_duplicates("slug")
    out = out.merge(st, on="slug", how="left")

    out["left_censored"] = (
        out["first_deployed"].notna() & (out["first_deployed"] < PANEL_START)
    ) | (
        out["launch_month"].notna() & (out["launch_month"] <= PANEL_START)
        & out["first_deployed"].isna()
    )
    # More precise: first_deployed before panel start
    out["left_censored"] = out["first_deployed"].notna() & (
        out["first_deployed"] < PANEL_START
    )

    out["follow_up_months"] = (
        (PANEL_END.to_period("M") - out["launch_month"].dt.to_period("M")).apply(
            lambda x: x.n if pd.notna(x) else np.nan
        )
    )
    out["eligible_12m"] = out["follow_up_months"] >= 12
    out["eligible_24m"] = out["follow_up_months"] >= 24
    return out


def panel_with_launch(panel: pd.DataFrame, life: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Attach launch_month and months_since_launch (already in panel usually)."""
    df = panel.copy()
    if "months_since_launch" not in df.columns:
        if life is None:
            life = load_lifecycle()
        df = df.merge(life[["slug", "launch_month"]], on="slug", how="left", suffixes=("", "_life"))
        if "launch_month_life" in df.columns:
            df["launch_month"] = df["launch_month"].fillna(df["launch_month_life"])
            df.drop(columns=["launch_month_life"], inplace=True)
        df["months_since_launch"] = (
            df["month"].dt.to_period("M") - df["launch_month"].dt.to_period("M")
        ).apply(lambda x: x.n if pd.notna(x) else np.nan)
    return df


def heavy_wallet_share(panel: pd.DataFrame) -> pd.DataFrame:
    """Fraction of activity attributable to heavy wallets."""
    df = panel.copy()
    for metric in ("active_wallets", "tx_count", "gas_used"):
        ex = f"{metric}_ex_heavy"
        if ex in df.columns and metric in df.columns:
            total = df[metric].replace(0, np.nan)
            df[f"heavy_share_{metric}"] = 1.0 - (df[ex] / total)
            df[f"heavy_share_{metric}"] = df[f"heavy_share_{metric}"].clip(0, 1)
    return df


LEAKAGE_NOTES = [
    {
        "feature": "tvl",
        "risk": "high",
        "reason": "Snapshot TVL at data-collection time, not at launch / early window.",
    },
    {
        "feature": "lifecycle_label / decay_ratio / peak_*",
        "risk": "high",
        "reason": "Computed from full post-launch history; cannot be used as predictors.",
    },
    {
        "feature": "early_prior_app_share",
        "risk": "medium",
        "reason": "Built over all users of the DApp, not restricted to early months.",
    },
    {
        "feature": "n_contracts",
        "risk": "medium",
        "reason": "Counts contracts deployed after launch as well as before.",
    },
    {
        "feature": "share_of_ecosystem_* (late months)",
        "risk": "low",
        "reason": "Safe within early window; late-month values leak future popularity.",
    },
    {
        "feature": "has_token / symbol",
        "risk": "low",
        "reason": "Mostly static metadata; token may launch after app — treat carefully.",
    },
]


CATEGORY_ORDER = [
    "DeFi", "DEX", "Lending", "Bridge", "Infrastructure",
    "NFT", "Gaming", "Social", "Derivatives", "Yield",
]


def category_palette(cats) -> dict:
    base = sns.color_palette("tab20", n_colors=max(20, len(list(cats))))
    return {c: base[i % len(base)] for i, c in enumerate(sorted(cats))}
