"""Headline: calendar heatmap + trajectory clustering + KM survival."""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # sets matplotlib Agg backend
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
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

HORIZON = 24  # months after launch
MIN_PEAK = 1000
MIN_MONTHS = 12


def build_trajectories(panel: pd.DataFrame, life: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, list]:
    """Peak-normalized wallet trajectories aligned at launch, length HORIZON."""
    eligible = life[
        (~life["left_censored"])
        & (life["peak_wallets"] >= MIN_PEAK)
        & (life["follow_up_months"] >= MIN_MONTHS)
    ].copy()
    slugs = eligible["slug"].tolist()
    print(f"  clustering population: {len(slugs)} DApps (peak>={MIN_PEAK}, >={MIN_MONTHS}m, not left-censored)")

    series = []
    keep = []
    for slug in slugs:
        g = panel[panel["slug"] == slug].sort_values("month")
        if g.empty:
            continue
        # align on months_since_launch
        if "months_since_launch" not in g.columns:
            launch = eligible.loc[eligible["slug"] == slug, "launch_month"].iloc[0]
            g = g.copy()
            g["months_since_launch"] = (
                g["month"].dt.to_period("M") - launch.to_period("M")
            ).apply(lambda x: x.n)
        g = g[(g["months_since_launch"] >= 0) & (g["months_since_launch"] < HORIZON)]
        if len(g) < MIN_MONTHS:
            continue
        peak = g["active_wallets"].max()
        if peak <= 0:
            continue
        traj = np.zeros(HORIZON, dtype=float)
        for _, row in g.iterrows():
            m = int(row["months_since_launch"])
            if 0 <= m < HORIZON:
                traj[m] = row["active_wallets"] / peak
        # forward-fill zeros after first activity only within observed span
        last_obs = int(g["months_since_launch"].max())
        # leave months beyond last_obs as NaN then fill with last value for clustering length
        if last_obs < HORIZON - 1:
            traj[last_obs + 1:] = traj[last_obs]
        series.append(traj)
        keep.append(slug)

    X = np.vstack(series)
    meta = eligible[eligible["slug"].isin(keep)].set_index("slug").loc[keep].reset_index()
    return meta, X, keep


def shape_features(X: np.ndarray) -> pd.DataFrame:
    rows = []
    for traj in X:
        peak_idx = int(np.argmax(traj))
        peak = traj[peak_idx]
        launch = traj[0] if traj[0] > 0 else 1e-6
        # half-life after peak: first month where traj < 0.5 * peak
        after = traj[peak_idx:]
        below = np.where(after < 0.5 * peak)[0]
        half = int(below[0]) if len(below) else len(after) - 1
        # decay: mean of last 6 / peak (peak=1 after norm)
        decay = float(np.mean(traj[-6:])) if len(traj) >= 6 else float(traj[-1])
        rows.append({
            "months_to_peak_traj": peak_idx,
            "peak_to_launch": peak / launch,
            "half_life_after_peak": half,
            "decay_last6": decay,
            "mean_first3": float(np.mean(traj[:3])),
            "mean_last6": float(np.mean(traj[-6:])),
            "auc": float(np.trapezoid(traj)),
        })
    return pd.DataFrame(rows)


def choose_k(X_scaled: np.ndarray, k_range=range(2, 8)) -> tuple[int, pd.DataFrame]:
    rows = []
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=20, random_state=42)
        labels = km.fit_predict(X_scaled)
        sil = silhouette_score(X_scaled, labels) if len(set(labels)) > 1 else np.nan
        rows.append({"k": k, "inertia": km.inertia_, "silhouette": sil})
        print(f"    k={k}: silhouette={sil:.3f}, inertia={km.inertia_:.1f}")
    df = pd.DataFrame(rows)
    # Prefer best silhouette
    best = int(df.loc[df["silhouette"].idxmax(), "k"])
    return best, df


def plot_cluster_trajectories(X: np.ndarray, labels: np.ndarray, title: str, fname: str):
    n_clusters = len(set(labels))
    fig, axes = plt.subplots(1, n_clusters, figsize=(4 * n_clusters, 3.5), sharey=True)
    if n_clusters == 1:
        axes = [axes]
    t = np.arange(X.shape[1])
    for c, ax in enumerate(axes):
        mask = labels == c
        for traj in X[mask]:
            ax.plot(t, traj, color="steelblue", alpha=0.12, lw=0.8)
        if mask.sum():
            ax.plot(t, np.median(X[mask], axis=0), color="darkred", lw=2.5, label="median")
            ax.plot(t, np.percentile(X[mask], 25, axis=0), color="darkred", lw=1, ls="--", alpha=0.7)
            ax.plot(t, np.percentile(X[mask], 75, axis=0), color="darkred", lw=1, ls="--", alpha=0.7)
        ax.set_title(f"Cluster {c} (n={mask.sum()})")
        ax.set_xlabel("Months since launch")
        ax.set_ylim(0, 1.05)
        if c == 0:
            ax.set_ylabel("Wallets / own peak")
    fig.suptitle(title, y=1.02)
    fig.tight_layout()
    savefig(fig, fname)


def km_survival(panel: pd.DataFrame, life: pd.DataFrame):
    """Time from peak until activity falls below 20% of peak."""
    try:
        from lifelines import KaplanMeierFitter
    except ImportError:
        print("  lifelines not available; skipping KM")
        return

    rows = []
    for _, row in life.iterrows():
        slug = row["slug"]
        peak_month = row["peak_month"]
        peak_w = row["peak_wallets"]
        if pd.isna(peak_month) or peak_w is None or peak_w < MIN_PEAK:
            continue
        g = panel[panel["slug"] == slug].sort_values("month")
        after = g[g["month"] >= peak_month].copy()
        if after.empty:
            continue
        thr = 0.2 * peak_w
        below = after[after["active_wallets"] < thr]
        if len(below):
            event_month = below["month"].iloc[0]
            duration = (event_month.to_period("M") - peak_month.to_period("M")).n
            event = 1
        else:
            duration = (after["month"].iloc[-1].to_period("M") - peak_month.to_period("M")).n
            event = 0
        rows.append({
            "slug": slug,
            "duration": max(duration, 0),
            "event": event,
            "category_group": row.get("category_group"),
            "has_token": row.get("has_token"),
            "lifecycle_label": row.get("lifecycle_label"),
        })
    surv = pd.DataFrame(rows)
    if surv.empty:
        return
    savetable(surv, "03_survival_data.csv")

    # Overall + by token
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    kmf = KaplanMeierFitter()
    for token_val, label, ax_i in [(None, "All", 0)]:
        pass
    ax = axes[0]
    for token, label, color in [(True, "Has token", "#4c72b0"), (False, "No token", "#c44e52")]:
        sub = surv[surv["has_token"] == token]
        if len(sub) < 5:
            continue
        kmf.fit(sub["duration"], sub["event"], label=label)
        kmf.plot_survival_function(ax=ax, color=color)
    ax.set_title("Time from peak → <20% of peak (by token)")
    ax.set_xlabel("Months after peak")
    ax.set_ylabel("P(still ≥20% of peak)")

    ax = axes[1]
    top_cats = surv["category_group"].value_counts().head(5).index
    for cat in top_cats:
        sub = surv[surv["category_group"] == cat]
        if len(sub) < 5:
            continue
        kmf.fit(sub["duration"], sub["event"], label=str(cat))
        kmf.plot_survival_function(ax=ax)
    ax.set_title("Time from peak → <20% of peak (by category)")
    ax.set_xlabel("Months after peak")
    ax.set_ylabel("P(still ≥20% of peak)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    savefig(fig, "03_km_survival.png")


def main() -> None:
    setup_style()
    print("== 03 lifecycle clustering ==")
    panel = load_panel()
    static = load_static()
    life = annotate_lifecycle(load_lifecycle(), static)

    # --- Calendar heatmap ---
    print("  calendar heatmap...")
    # Sample / order by launch; use log1p wallets
    life_ord = life.sort_values("launch_month")
    # Cap rows for readability: take all if ≤300 else stratified sample
    slugs_ordered = life_ord["slug"].tolist()
    if len(slugs_ordered) > 350:
        # keep top by peak + random sample of rest
        top = life.nlargest(150, "peak_wallets")["slug"].tolist()
        rest = [s for s in slugs_ordered if s not in top]
        rng = np.random.default_rng(42)
        extra = list(rng.choice(rest, size=min(200, len(rest)), replace=False))
        slugs_ordered = [s for s in slugs_ordered if s in set(top + extra)]

    months = sorted(panel["month"].unique())
    mat = np.full((len(slugs_ordered), len(months)), np.nan)
    slug_to_i = {s: i for i, s in enumerate(slugs_ordered)}
    month_to_j = {m: j for j, m in enumerate(months)}
    sub = panel[panel["slug"].isin(slug_to_i)]
    for slug, month, aw in zip(sub["slug"], sub["month"], sub["active_wallets"]):
        i, j = slug_to_i[slug], month_to_j[month]
        mat[i, j] = np.log1p(aw)

    fig, ax = plt.subplots(figsize=(14, 10))
    sns.heatmap(
        mat,
        cmap="YlOrRd",
        ax=ax,
        cbar_kws={"label": "log1p(active wallets)"},
        xticklabels=False,
        yticklabels=False,
    )
    # year ticks
    year_starts = [j for j, m in enumerate(months) if pd.Timestamp(m).month == 1]
    ax.set_xticks(year_starts)
    ax.set_xticklabels([str(pd.Timestamp(months[j]).year) for j in year_starts], rotation=0)
    ax.set_xlabel("Calendar time")
    ax.set_ylabel("DApps (sorted by launch)")
    ax.set_title("Calendar heatmap of DApp activity (log wallets)")
    savefig(fig, "03_calendar_heatmap.png")

    # --- Build trajectories ---
    print("  building trajectories...")
    meta, X, keep = build_trajectories(panel, life)
    savetable(pd.DataFrame(X, columns=[f"m{i}" for i in range(HORIZON)]).assign(slug=keep),
              "03_trajectories_normalized.csv")

    # --- Shape-feature k-means ---
    print("  shape-feature clustering...")
    feats = shape_features(X)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(feats.values)
    best_k, kdiag = choose_k(Xs)
    savetable(kdiag, "03_k_selection_shape.csv")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(kdiag["k"], kdiag["inertia"], "o-", color="steelblue")
    axes[0].set_title("Elbow (inertia)")
    axes[0].set_xlabel("k")
    axes[1].plot(kdiag["k"], kdiag["silhouette"], "o-", color="darkorange")
    axes[1].axvline(best_k, color="red", ls="--", label=f"best k={best_k}")
    axes[1].set_title("Silhouette")
    axes[1].set_xlabel("k")
    axes[1].legend()
    savefig(fig, "03_k_selection_shape.png")

    km = KMeans(n_clusters=best_k, n_init=30, random_state=42)
    labels_shape = km.fit_predict(Xs)
    plot_cluster_trajectories(X, labels_shape, f"Shape-feature k-means (k={best_k})", "03_clusters_shape.png")

    # --- Euclidean TimeSeriesKMeans ---
    labels_eucl = labels_shape.copy()
    labels_dtw = labels_shape.copy()
    try:
        from tslearn.clustering import TimeSeriesKMeans
        from tslearn.utils import to_time_series_dataset

        X_ts = to_time_series_dataset(X)
        print("  Euclidean TimeSeriesKMeans...")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # choose k via silhouette on flattened
            eucl_scores = []
            for k in range(2, 7):
                model = TimeSeriesKMeans(n_clusters=k, metric="euclidean",
                                         max_iter=30, random_state=42, n_jobs=1)
                lab = model.fit_predict(X_ts)
                sil = silhouette_score(X, lab)
                eucl_scores.append({"k": k, "silhouette": sil})
                print(f"    eucl k={k}: sil={sil:.3f}")
            eucl_df = pd.DataFrame(eucl_scores)
            savetable(eucl_df, "03_k_selection_euclidean.csv")
            best_eucl = int(eucl_df.loc[eucl_df["silhouette"].idxmax(), "k"])
            model = TimeSeriesKMeans(n_clusters=best_eucl, metric="euclidean",
                                     max_iter=50, random_state=42, n_jobs=1)
            labels_eucl = model.fit_predict(X_ts)
            plot_cluster_trajectories(
                X, labels_eucl,
                f"TimeSeriesKMeans Euclidean (k={best_eucl})",
                "03_clusters_euclidean.png",
            )

            print("  DTW TimeSeriesKMeans (may be slow)...")
            # DTW is expensive; use smaller k search and fewer iterations
            dtw_scores = []
            for k in (2, 3, 4):
                model = TimeSeriesKMeans(
                    n_clusters=k, metric="dtw", max_iter=10,
                    random_state=42, n_jobs=1,
                    metric_params={"global_constraint": "sakoe_chiba", "sakoe_chiba_radius": 3},
                )
                lab = model.fit_predict(X_ts)
                sil = silhouette_score(X, lab)
                dtw_scores.append({"k": k, "silhouette": sil})
                print(f"    dtw k={k}: sil={sil:.3f}")
            dtw_df = pd.DataFrame(dtw_scores)
            savetable(dtw_df, "03_k_selection_dtw.csv")
            best_dtw = int(dtw_df.loc[dtw_df["silhouette"].idxmax(), "k"])
            model = TimeSeriesKMeans(
                n_clusters=best_dtw, metric="dtw", max_iter=15,
                random_state=42, n_jobs=1,
                metric_params={"global_constraint": "sakoe_chiba", "sakoe_chiba_radius": 3},
            )
            labels_dtw = model.fit_predict(X_ts)
            plot_cluster_trajectories(
                X, labels_dtw,
                f"TimeSeriesKMeans DTW (k={best_dtw})",
                "03_clusters_dtw.png",
            )
    except Exception as e:
        print(f"  tslearn clustering skipped/failed: {e}")

    # Primary labels = shape (stable, fast); also store euclidean/dtw
    assign = meta[["slug", "name", "category_group", "lifecycle_label", "has_token",
                   "launch_month", "launch_year", "peak_wallets"]].copy()
    assign["cluster_shape"] = labels_shape
    assign["cluster_euclidean"] = labels_eucl
    assign["cluster_dtw"] = labels_dtw
    assign = pd.concat([assign.reset_index(drop=True), feats.reset_index(drop=True)], axis=1)
    savetable(assign, "trajectory_clusters.csv")
    print(f"  wrote {CLUSTER_ASSIGN}")

    # --- Cluster profiles ---
    primary = "cluster_shape"
    # composition
    for dim in ("category_group", "lifecycle_label", "has_token", "launch_year"):
        ct = pd.crosstab(assign[primary], assign[dim], normalize="index")
        savetable(ct.reset_index(), f"03_cluster_by_{dim}.csv")
        fig, ax = plt.subplots(figsize=(9, 4))
        ct.plot(kind="bar", stacked=True, ax=ax, width=0.85)
        ax.set_ylabel("Share")
        ax.set_xlabel("Cluster")
        ax.set_title(f"Cluster composition by {dim}")
        ax.legend(loc="upper right", fontsize=7, ncol=2)
        ax.tick_params(axis="x", rotation=0)
        savefig(fig, f"03_cluster_by_{dim}.png")

    # Crosstab cluster vs lifecycle_label (counts)
    ct_counts = pd.crosstab(assign[primary], assign["lifecycle_label"])
    savetable(ct_counts.reset_index(), "03_cluster_vs_lifecycle.csv")
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.heatmap(ct_counts, annot=True, fmt="d", cmap="Blues", ax=ax)
    ax.set_title("Shape clusters vs rule-based lifecycle_label")
    savefig(fig, "03_cluster_vs_lifecycle.png")

    # Name clusters from median trajectory shape
    rows = []
    for c in sorted(assign[primary].unique()):
        med = np.median(X[labels_shape == c], axis=0)
        rows.append({
            "c": c,
            "peak_m": int(np.argmax(med)),
            "decay": float(np.mean(med[-6:])),
            "auc": float(np.trapezoid(med)),
        })
    sdf = pd.DataFrame(rows)
    names: dict = {}
    late = sdf[sdf["peak_m"] >= 12].sort_values("auc", ascending=False)
    for i, r in enumerate(late.itertuples()):
        names[r.c] = "slow_build" if i == 0 else "slow_build_sparse"
    for r in sdf.itertuples():
        if r.peak_m <= 5 and r.decay < 0.30:
            names[r.c] = "flash_fade"
        elif r.c not in names:
            names[r.c] = "sustained" if r.decay >= 0.50 else "gradual_decline"
        print(f"  cluster {r.c}: peak_m={r.peak_m}, decay={r.decay:.3f}, auc={r.auc:.2f} -> {names[r.c]}")
    assign["cluster_name"] = assign[primary].map(names)
    savetable(assign, "trajectory_clusters.csv")
    print("  cluster names:", names)

    # Named overview plot
    fig, ax = plt.subplots(figsize=(9, 5))
    t = np.arange(HORIZON)
    for c, name in names.items():
        mask = labels_shape == c
        ax.plot(t, np.median(X[mask], axis=0), lw=2.5, label=f"{name} (c{c}, n={mask.sum()})")
    ax.set_xlabel("Months since launch")
    ax.set_ylabel("Wallets / own peak")
    ax.set_title("Median trajectories by shape cluster")
    ax.legend(fontsize=9)
    ax.set_ylim(0, 1.05)
    savefig(fig, "03_cluster_medians_named.png")

    # --- Survival ---
    print("  Kaplan-Meier survival...")
    km_survival(panel, life)

    print("== 03 done ==")


if __name__ == "__main__":
    main()
