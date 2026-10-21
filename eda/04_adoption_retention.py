"""Adoption speed and user retention."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    CLUSTER_ASSIGN,
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


def ecdf(ax, values, label=None, **kwargs):
    v = np.sort(np.asarray(values, dtype=float))
    v = v[~np.isnan(v)]
    if len(v) == 0:
        return
    y = np.arange(1, len(v) + 1) / len(v)
    ax.step(v, y, where="post", label=label, **kwargs)


def load_clusters() -> pd.DataFrame | None:
    if CLUSTER_ASSIGN.exists():
        return pd.read_csv(CLUSTER_ASSIGN)
    return None


def fill_cohort_from_raw() -> pd.DataFrame:
    """Load raw cohort file and fill missing retained=0 without exploding to max months_since globally."""
    raw = pd.read_csv(
        Path(__file__).resolve().parent.parent / "dapp_data_v2" / "cohort_retention.csv"
    )
    raw["cohort_month"] = pd.to_datetime(raw["cohort_month"], errors="coerce")
    # For heatmaps we aggregate; fill gaps per cohort up to observed max for that cohort
    rows = []
    for (proto, cm), g in raw.groupby(["protocol", "cohort_month"], sort=False):
        size = int(g["cohort_size"].iloc[0])
        max_ms = int(g["months_since"].max())
        lookup = g.set_index("months_since")["retained"]
        for ms in range(0, max_ms + 1):
            retained = int(lookup.get(ms, 0))
            rows.append({
                "protocol": proto,
                "cohort_month": cm,
                "months_since": ms,
                "retained": retained,
                "cohort_size": size,
                "retention_rate": retained / size if size else np.nan,
            })
    return pd.DataFrame(rows)


def main() -> None:
    setup_style()
    print("== 04 adoption & retention ==")
    panel = load_panel()
    static = load_static()
    life = annotate_lifecycle(load_lifecycle(), static)
    clusters = load_clusters()
    if clusters is not None:
        life = life.merge(
            clusters[["slug", "cluster_shape", "cluster_name"]].drop_duplicates("slug"),
            on="slug",
            how="left",
        )

    adopted = life[life["peak_wallets"] >= 1000].copy()

    # --- ECDFs of time-to-threshold ---
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    metrics = [
        ("months_to_1k", "Months to 1k cum. wallets"),
        ("months_to_10k", "Months to 10k cum. wallets"),
        ("months_to_half_peak_cum", "Months to 50% of peak cum."),
    ]
    for ax, (col, title) in zip(axes, metrics):
        for label, g in adopted.groupby("lifecycle_label"):
            ecdf(ax, g[col], label=label, lw=1.8)
        ax.set_xlabel(title)
        ax.set_ylabel("ECDF")
        ax.set_title(title)
        ax.set_xlim(left=0)
    axes[0].legend(fontsize=7, loc="lower right")
    fig.suptitle("Adoption speed by lifecycle label (peak≥1k)", y=1.02)
    fig.tight_layout()
    savefig(fig, "04_ecdf_time_to_threshold_lifecycle.png")

    if "cluster_name" in adopted.columns and adopted["cluster_name"].notna().any():
        fig, axes = plt.subplots(1, 3, figsize=(14, 4))
        for ax, (col, title) in zip(axes, metrics):
            for label, g in adopted.dropna(subset=["cluster_name"]).groupby("cluster_name"):
                ecdf(ax, g[col], label=label, lw=1.8)
            ax.set_xlabel(title)
            ax.set_ylabel("ECDF")
            ax.set_title(title)
            ax.set_xlim(left=0)
        axes[0].legend(fontsize=7, loc="lower right")
        fig.suptitle("Adoption speed by trajectory cluster", y=1.02)
        fig.tight_layout()
        savefig(fig, "04_ecdf_time_to_threshold_cluster.png")

    # Summary table
    summary = (
        adopted.groupby("lifecycle_label")[["months_to_1k", "months_to_10k", "months_to_half_peak_cum"]]
        .median()
        .reset_index()
    )
    savetable(summary, "04_median_time_to_threshold.csv")

    # --- Cumulative wallet curves top 20 ---
    top20 = life.nlargest(20, "peak_wallets")["slug"].tolist()
    fig, ax = plt.subplots(figsize=(11, 6))
    for slug in top20:
        g = panel[panel["slug"] == slug].sort_values("month")
        if g.empty:
            continue
        name = life.loc[life["slug"] == slug, "name"]
        label = name.iloc[0] if len(name) else slug
        msl = g["months_since_launch"] if "months_since_launch" in g.columns else np.arange(len(g))
        ax.plot(msl, g["cum_wallets"], label=label[:22], lw=1.5, alpha=0.85)
    ax.set_yscale("log")
    ax.set_xlabel("Months since launch")
    ax.set_ylabel("Cumulative wallets (log)")
    ax.set_title("Cumulative wallet acquisition — top 20 by peak wallets")
    ax.legend(fontsize=7, ncol=2, loc="lower right")
    savefig(fig, "04_cum_wallets_top20.png")

    # --- Cohort retention heatmaps ---
    print("  loading cohort retention (filled)...")
    cohort = fill_cohort_from_raw()
    # Attach category
    slug_cat = static[["slug", "category_group"]].drop_duplicates()
    cohort = cohort.merge(slug_cat, left_on="protocol", right_on="slug", how="left")

    # Aggregate: mean retention by category_group x months_since (weight by cohort_size, early cohorts)
    # Restrict months_since 0..12 for readability
    c12 = cohort[cohort["months_since"] <= 12].copy()
    for cat, g in c12.groupby("category_group"):
        if g["protocol"].nunique() < 5:
            continue
        # Weighted mean retention by months_since across cohorts
        # Build matrix: cohort_month x months_since, average across protocols in cat
        # Simpler: average retention_rate by months_since only, but heatmap needs 2d
        # Use launch-year cohorts aggregated
        g = g.copy()
        g["cohort_year"] = g["cohort_month"].dt.year
        piv = (
            g.groupby(["cohort_year", "months_since"])
            .apply(lambda x: np.average(x["retention_rate"], weights=x["cohort_size"]), include_groups=False)
            .unstack("months_since")
        )
        if piv.empty:
            continue
        fig, ax = plt.subplots(figsize=(9, 4))
        sns.heatmap(piv, cmap="YlGnBu", vmin=0, vmax=1, ax=ax,
                    cbar_kws={"label": "retention"})
        ax.set_title(f"Cohort retention — {cat}")
        ax.set_xlabel("Months since first interaction")
        ax.set_ylabel("Cohort year")
        savefig(fig, f"04_cohort_heatmap_{str(cat).replace(' ', '_')}.png")

    # Overall heatmap
    c12["cohort_year"] = c12["cohort_month"].dt.year
    piv = (
        c12.groupby(["cohort_year", "months_since"])
        .apply(lambda x: np.average(x["retention_rate"], weights=x["cohort_size"]), include_groups=False)
        .unstack("months_since")
    )
    fig, ax = plt.subplots(figsize=(10, 4.5))
    sns.heatmap(piv, cmap="YlGnBu", vmin=0, vmax=1, ax=ax, cbar_kws={"label": "retention"})
    ax.set_title("Ecosystem cohort retention (size-weighted)")
    ax.set_xlabel("Months since first interaction")
    ax.set_ylabel("Cohort year")
    savefig(fig, "04_cohort_heatmap_overall.png")

    # --- Retention at m1/m3/m6 by cluster ---
    # From panel: retention_prev_month averaged at months_since_launch == 1,3,6
    ret_rows = []
    for slug, g in panel.groupby("slug"):
        g = g.sort_values("months_since_launch") if "months_since_launch" in g.columns else g
        if "months_since_launch" not in g.columns:
            continue
        row = {"slug": slug}
        for m in (1, 3, 6):
            sub = g[g["months_since_launch"] == m]
            row[f"ret_m{m}"] = float(sub["retention_prev_month"].iloc[0]) if len(sub) else np.nan
        ret_rows.append(row)
    ret_df = pd.DataFrame(ret_rows)
    if clusters is not None:
        ret_df = ret_df.merge(clusters[["slug", "cluster_name"]], on="slug", how="left")
        melted = ret_df.dropna(subset=["cluster_name"]).melt(
            id_vars=["slug", "cluster_name"],
            value_vars=["ret_m1", "ret_m3", "ret_m6"],
            var_name="horizon",
            value_name="retention",
        )
        fig, ax = plt.subplots(figsize=(9, 4.5))
        sns.boxplot(data=melted, x="horizon", y="retention", hue="cluster_name", ax=ax)
        ax.set_title("Month-over-month retention at m1/m3/m6 by cluster")
        ax.set_ylim(0, 1)
        ax.legend(fontsize=8, title="")
        savefig(fig, "04_retention_by_cluster.png")
        savetable(ret_df, "04_retention_milestones.csv")

    # --- Retention consistency across cohorts ---
    # For each protocol, correlation of retention@m1 across consecutive cohorts
    print("  retention consistency...")
    cons_rows = []
    raw = pd.read_csv(
        Path(__file__).resolve().parent.parent / "dapp_data_v2" / "cohort_retention.csv"
    )
    raw["cohort_month"] = pd.to_datetime(raw["cohort_month"])
    m1 = raw[raw["months_since"] == 1].copy()
    for proto, g in m1.groupby("protocol"):
        g = g.sort_values("cohort_month")
        if len(g) < 4:
            continue
        # autocorrelation lag-1 of retention_rate
        r = g["retention_rate"].astype(float)
        if r.std() == 0:
            continue
        corr = r.autocorr(lag=1)
        cons_rows.append({
            "protocol": proto,
            "n_cohorts": len(g),
            "ret_m1_mean": r.mean(),
            "ret_m1_std": r.std(),
            "ret_m1_autocorr": corr,
        })
    cons = pd.DataFrame(cons_rows)
    if len(cons):
        savetable(cons, "04_retention_consistency.csv")
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(cons["ret_m1_autocorr"].dropna(), bins=20, color="steelblue", edgecolor="white")
        ax.axvline(cons["ret_m1_autocorr"].median(), color="red", ls="--",
                   label=f"median={cons['ret_m1_autocorr'].median():.2f}")
        ax.set_xlabel("Lag-1 autocorr of cohort m1 retention")
        ax.set_ylabel("# DApps")
        ax.set_title("Is retention consistent across cohorts?")
        ax.legend()
        savefig(fig, "04_retention_consistency.png")

    print("== 04 done ==")


if __name__ == "__main__":
    main()
