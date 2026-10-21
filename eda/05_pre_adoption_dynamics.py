"""Event study: metrics around the month a DApp crosses 10k cumulative wallets."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    annotate_lifecycle,
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

PRE = 6
POST = 12
THRESHOLD = 10_000

METRICS = [
    ("tx_per_wallet", "Tx per wallet"),
    ("gas_per_tx", "Gas per tx"),
    ("retention_prev_month", "MoM retention"),
    ("new_wallet_share", "New-wallet share"),
    ("top10_wallet_share", "Whale (top-10) share"),
    ("fees_eth", "Fees (ETH)"),
    ("share_of_ecosystem_active_wallets", "Ecosystem wallet share"),
    ("active_wallets", "Active wallets"),
]


def prepare_panel(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy()
    df["gas_per_tx"] = df["gas_used"] / df["tx_count"].replace(0, np.nan)
    df["new_wallet_share"] = df["new_wallets"] / df["active_wallets"].replace(0, np.nan)
    return df


def find_crossing(panel: pd.DataFrame, life: pd.DataFrame) -> pd.DataFrame:
    """First month each DApp's cum_wallets crosses THRESHOLD."""
    rows = []
    for slug, g in panel.groupby("slug"):
        g = g.sort_values("month")
        if "cum_wallets" not in g.columns:
            continue
        hit = g[g["cum_wallets"] >= THRESHOLD]
        if hit.empty:
            continue
        t0 = hit["month"].iloc[0]
        lab = life.loc[life["slug"] == slug]
        rows.append({
            "slug": slug,
            "t0": t0,
            "lifecycle_label": lab["lifecycle_label"].iloc[0] if len(lab) else np.nan,
            "category_group": lab["category_group"].iloc[0] if len(lab) else np.nan,
            "peak_wallets": lab["peak_wallets"].iloc[0] if len(lab) else np.nan,
        })
    return pd.DataFrame(rows)


def event_window(panel: pd.DataFrame, crossings: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    for _, row in crossings.iterrows():
        g = panel[panel["slug"] == row["slug"]].copy()
        g["rel_month"] = (
            g["month"].dt.to_period("M") - row["t0"].to_period("M")
        ).apply(lambda x: x.n)
        g = g[(g["rel_month"] >= -PRE) & (g["rel_month"] <= POST)]
        g["lifecycle_label"] = row["lifecycle_label"]
        g["category_group"] = row["category_group"]
        pieces.append(g)
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True)


def median_iqr(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    def q(x, p):
        return np.nanpercentile(x, p) if len(x) and np.isfinite(x).any() else np.nan

    rows = []
    for rel, g in df.groupby("rel_month"):
        v = g[metric].astype(float).values
        rows.append({
            "rel_month": rel,
            "median": np.nanmedian(v) if len(v) else np.nan,
            "q25": q(v, 25),
            "q75": q(v, 75),
            "n": np.isfinite(v).sum(),
        })
    return pd.DataFrame(rows).sort_values("rel_month")


def plot_event(df: pd.DataFrame, metric: str, ylabel: str, fname: str, by: str | None = None):
    fig, ax = plt.subplots(figsize=(8, 4))
    if by is None:
        s = median_iqr(df, metric)
        ax.fill_between(s["rel_month"], s["q25"], s["q75"], alpha=0.25, color="steelblue")
        ax.plot(s["rel_month"], s["median"], color="steelblue", lw=2.5)
    else:
        for label, g in df.groupby(by):
            if g["slug"].nunique() < 5:
                continue
            s = median_iqr(g, metric)
            ax.plot(s["rel_month"], s["median"], lw=2, label=str(label))
            ax.fill_between(s["rel_month"], s["q25"], s["q75"], alpha=0.12)
        ax.legend(fontsize=8)
    ax.axvline(0, color="black", ls="--", lw=1, label="crosses 10k cum")
    ax.set_xlabel("Months relative to 10k cumulative wallets")
    ax.set_ylabel(ylabel)
    ax.set_title(ylabel)
    savefig(fig, fname)


def main() -> None:
    setup_style()
    print("== 05 pre-adoption dynamics ==")
    panel = prepare_panel(load_panel())
    static = load_static()
    life = annotate_lifecycle(load_lifecycle(), static)

    crossings = find_crossing(panel, life)
    print(f"  DApps crossing {THRESHOLD:,} cum wallets: {len(crossings)}")
    savetable(crossings, "05_crossing_events.csv")

    if crossings.empty:
        print("  no crossings; abort")
        return

    # Classify growers vs flash among those who crossed
    # sustained / gradual_decline vs flash
    crossings["adopter_type"] = crossings["lifecycle_label"].map(
        lambda x: "flash" if x == "flash"
        else ("grower" if x in ("sustained", "gradual_decline") else "other")
    )

    ew = event_window(panel, crossings)
    # attach adopter_type
    ew = ew.merge(crossings[["slug", "adopter_type"]], on="slug", how="left")
    keep_cols = ["slug", "month", "rel_month", "lifecycle_label", "adopter_type"] + [
        m for m, _ in METRICS if m in ew.columns
    ]
    savetable(ew[keep_cols], "05_event_window.csv")

    # Overall event studies
    for metric, label in METRICS:
        if metric not in ew.columns:
            continue
        plot_event(ew, metric, label, f"05_event_{metric}.png")

    # Growers vs flash
    gf = ew[ew["adopter_type"].isin(["grower", "flash"])]
    print(f"  grower/flash event rows: {len(gf)}; dapps={gf['slug'].nunique()}")
    for metric, label in METRICS:
        if metric not in gf.columns:
            continue
        plot_event(gf, metric, f"{label} — growers vs flash",
                   f"05_event_{metric}_grower_vs_flash.png", by="adopter_type")

    # Summary table at t=-1,0,3,6,12
    checkpoints = [-1, 0, 3, 6, 12]
    rows = []
    for atype, g in gf.groupby("adopter_type"):
        for metric, _ in METRICS:
            if metric not in g.columns:
                continue
            for t in checkpoints:
                sub = g[g["rel_month"] == t][metric]
                rows.append({
                    "adopter_type": atype,
                    "metric": metric,
                    "rel_month": t,
                    "median": float(sub.median()) if len(sub) else np.nan,
                    "n": int(sub.notna().sum()),
                })
    savetable(pd.DataFrame(rows), "05_event_checkpoints.csv")

    # Interactive Plotly
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        plot_metrics = [
            ("active_wallets", "Active wallets"),
            ("tx_per_wallet", "Tx / wallet"),
            ("retention_prev_month", "Retention"),
            ("top10_wallet_share", "Whale share"),
            ("new_wallet_share", "New-wallet share"),
            ("share_of_ecosystem_active_wallets", "Ecosystem share"),
        ]
        fig = make_subplots(rows=2, cols=3, subplot_titles=[l for _, l in plot_metrics])
        colors = {"grower": "#4c72b0", "flash": "#c44e52"}
        for i, (metric, _) in enumerate(plot_metrics):
            r, c = divmod(i, 3)
            for atype in ("grower", "flash"):
                s = median_iqr(gf[gf["adopter_type"] == atype], metric)
                fig.add_trace(
                    go.Scatter(
                        x=s["rel_month"], y=s["median"],
                        name=atype, legendgroup=atype,
                        showlegend=(i == 0),
                        line=dict(color=colors[atype], width=2),
                    ),
                    row=r + 1, col=c + 1,
                )
            fig.add_vline(x=0, line_dash="dash", line_color="gray", row=r + 1, col=c + 1)
        fig.update_layout(
            title=f"Pre/post adoption event study (cross {THRESHOLD:,} cum wallets)",
            height=700, width=1100, template="plotly_white",
        )
        out = Path(__file__).resolve().parent / "figures" / "html" / "05_event_study.html"
        fig.write_html(str(out))
        print(f"  saved figures/html/05_event_study.html")
    except Exception as e:
        print(f"  plotly interactive skipped: {e}")

    print("== 05 done ==")


if __name__ == "__main__":
    main()
