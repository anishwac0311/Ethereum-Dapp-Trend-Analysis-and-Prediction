"""Predictive feasibility: early features, candidate targets, baselines."""
from __future__ import annotations

import sys
import warnings
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
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    average_precision_score,
    mean_absolute_error,
    mutual_info_score,
    r2_score,
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def early_features(panel: pd.DataFrame, life: pd.DataFrame, k: int) -> pd.DataFrame:
    """Leakage-free features from months 0..k-1 after launch."""
    rows = []
    life_idx = life.set_index("slug")
    for slug, g in panel.groupby("slug"):
        if slug not in life_idx.index:
            continue
        meta = life_idx.loc[slug]
        if isinstance(meta, pd.DataFrame):
            meta = meta.iloc[0]
        g = g.sort_values("month")
        if "months_since_launch" not in g.columns:
            continue
        early = g[(g["months_since_launch"] >= 0) & (g["months_since_launch"] < k)]
        if len(early) < max(2, k // 2):
            continue

        aw = early["active_wallets"].astype(float).values
        tx = early["tx_count"].astype(float).values
        gas = early["gas_used"].astype(float).values

        # growth slope of log1p wallets
        x = early["months_since_launch"].astype(float).values
        y = np.log1p(aw)
        slope = np.polyfit(x, y, 1)[0] if len(x) >= 2 else np.nan

        ret = early["retention_prev_month"].mean()
        new_share = early["new_wallets"].sum() / max(early["active_wallets"].sum(), 1)
        tx_pw = early["tx_count"].sum() / max(early["active_wallets"].sum(), 1)
        gas_pt = early["gas_used"].sum() / max(early["tx_count"].sum(), 1)
        whale = early["top10_wallet_share"].mean() if "top10_wallet_share" in early else np.nan
        eco = early["share_of_ecosystem_active_wallets"].mean() if "share_of_ecosystem_active_wallets" in early else np.nan

        heavy_w = np.nan
        if "active_wallets_ex_heavy" in early.columns:
            total = early["active_wallets"].sum()
            ex = early["active_wallets_ex_heavy"].sum()
            heavy_w = 1 - (ex / total) if total > 0 else np.nan

        # wallets at month 12 (for regression target) — from full panel, not early
        m12 = g[g["months_since_launch"] == 12]
        wallets_m12 = float(m12["active_wallets"].iloc[0]) if len(m12) else np.nan

        rows.append({
            "slug": slug,
            "k": k,
            "category_group": meta.get("category_group"),
            "has_token": bool(meta.get("has_token")),
            "launch_year": int(meta["launch_month"].year) if pd.notna(meta.get("launch_month")) else np.nan,
            "left_censored": bool(meta.get("left_censored", False)),
            "eligible_12m": bool(meta.get("eligible_12m", False)),
            "mean_wallets": float(np.mean(aw)),
            "max_wallets": float(np.max(aw)),
            "sum_wallets": float(np.sum(aw)),
            "mean_tx": float(np.mean(tx)),
            "mean_gas": float(np.mean(gas)),
            "wallet_growth_slope": float(slope),
            "early_retention": float(ret) if pd.notna(ret) else np.nan,
            "early_new_wallet_share": float(new_share),
            "early_tx_per_wallet": float(tx_pw),
            "early_gas_per_tx": float(gas_pt),
            "early_whale_share": float(whale) if pd.notna(whale) else np.nan,
            "early_eco_share": float(eco) if pd.notna(eco) else np.nan,
            "early_heavy_wallet_share": float(heavy_w) if pd.notna(heavy_w) else np.nan,
            # targets (full history — labels only)
            "peak_wallets": float(meta.get("peak_wallets", np.nan)),
            "lifecycle_label": meta.get("lifecycle_label"),
            "wallets_m12": wallets_m12,
            "decay_ratio": float(meta.get("decay_ratio", np.nan)) if pd.notna(meta.get("decay_ratio")) else np.nan,
        })
    return pd.DataFrame(rows)


FEATURE_COLS = [
    "mean_wallets", "max_wallets", "sum_wallets", "mean_tx", "mean_gas",
    "wallet_growth_slope", "early_retention", "early_new_wallet_share",
    "early_tx_per_wallet", "early_gas_per_tx", "early_whale_share",
    "early_eco_share", "early_heavy_wallet_share", "has_token", "launch_year",
]
CAT_COLS = ["category_group"]


def add_targets(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["y_peak_10k"] = (out["peak_wallets"] >= 10_000).astype(int)
    q75 = out.loc[out["eligible_12m"] & ~out["left_censored"], "peak_wallets"].quantile(0.75)
    out["y_peak_topq"] = (out["peak_wallets"] >= q75).astype(int)
    out["y_log_wallets_m12"] = np.log1p(out["wallets_m12"])
    out["y_lifecycle"] = out["lifecycle_label"]
    return out


def univariate_auc(df: pd.DataFrame, features: list, target: str) -> pd.DataFrame:
    rows = []
    y = df[target].values
    for f in features:
        x = df[f]
        if x.dtype == bool:
            x = x.astype(int)
        mask = x.notna() & pd.Series(y).notna().values
        if mask.sum() < 30 or len(np.unique(y[mask])) < 2:
            continue
        xv = x[mask].astype(float).values
        try:
            auc = roc_auc_score(y[mask], xv)
            # also flipped
            auc = max(auc, 1 - auc)
        except Exception:
            auc = np.nan
        # mutual info (discretize)
        try:
            bins = pd.qcut(xv, q=min(10, len(np.unique(xv))), duplicates="drop")
            mi = mutual_info_score(y[mask], bins.astype(str))
        except Exception:
            mi = np.nan
        spearman = pd.Series(xv).corr(pd.Series(y[mask]), method="spearman")
        rows.append({"feature": f, "auc": auc, "mutual_info": mi, "spearman": spearman})
    return pd.DataFrame(rows).sort_values("auc", ascending=False)


def time_split(df: pd.DataFrame):
    train = df[df["launch_year"] <= 2022]
    test = df[df["launch_year"].isin([2023, 2024])]
    return train, test


def make_preprocessor():
    num_cols = [c for c in FEATURE_COLS if c != "has_token"]
    pre = ColumnTransformer([
        ("num", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), num_cols),
        ("tok", SimpleImputer(strategy="most_frequent"), ["has_token"]),
        ("cat", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("oh", OneHotEncoder(handle_unknown="ignore")),
        ]), CAT_COLS),
    ])
    return pre


def run_binary(df: pd.DataFrame, target: str, k: int, tag: str):
    use = df[df["eligible_12m"] & ~df["left_censored"]].copy()
    use["has_token"] = use["has_token"].astype(int)
    train, test = time_split(use)
    if len(train) < 40 or len(test) < 15:
        print(f"  skip {tag}: train={len(train)} test={len(test)}")
        return None

    feats = FEATURE_COLS + CAT_COLS
    Xtr, ytr = train[feats], train[target]
    Xte, yte = test[feats], test[target]
    print(f"  {tag}: train={len(train)} (pos={ytr.mean():.2f}) test={len(test)} (pos={yte.mean():.2f})")

    results = []

    # Logistic
    pipe_lr = Pipeline([
        ("pre", make_preprocessor()),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    pipe_lr.fit(Xtr, ytr)
    proba_lr = pipe_lr.predict_proba(Xte)[:, 1]

    # GBM
    pipe_gb = Pipeline([
        ("pre", make_preprocessor()),
        ("clf", GradientBoostingClassifier(random_state=42)),
    ])
    pipe_gb.fit(Xtr, ytr)
    proba_gb = pipe_gb.predict_proba(Xte)[:, 1]

    for name, proba in [("logreg", proba_lr), ("gbm", proba_gb)]:
        auc = roc_auc_score(yte, proba) if yte.nunique() > 1 else np.nan
        ap = average_precision_score(yte, proba) if yte.nunique() > 1 else np.nan
        results.append({"model": name, "target": target, "k": k, "auc": auc, "ap": ap,
                        "n_train": len(train), "n_test": len(test), "base_rate_test": yte.mean()})
        print(f"    {name}: AUC={auc:.3f} AP={ap:.3f}")

    # ROC / PR curves for GBM
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    fpr, tpr, _ = roc_curve(yte, proba_gb)
    axes[0].plot(fpr, tpr, lw=2, label=f"GBM AUC={roc_auc_score(yte, proba_gb):.3f}")
    axes[0].plot([0, 1], [0, 1], ls="--", color="gray")
    axes[0].set_xlabel("FPR")
    axes[0].set_ylabel("TPR")
    axes[0].set_title(f"ROC — {tag}")
    axes[0].legend()

    prec, rec, _ = precision_recall_curve(yte, proba_gb)
    axes[1].plot(rec, prec, lw=2, label=f"GBM AP={average_precision_score(yte, proba_gb):.3f}")
    axes[1].axhline(yte.mean(), color="gray", ls="--", label="base rate")
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].set_title(f"PR — {tag}")
    axes[1].legend()
    savefig(fig, f"06_roc_pr_{tag}.png")

    # Permutation importance
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        imp = permutation_importance(pipe_gb, Xte, yte, n_repeats=15, random_state=42, scoring="roc_auc")
    # Map back to input feature names (approx via column order after one-hot is hard;
    # use numeric features only importance by permuting raw cols)
    imp_rows = []
    for i, col in enumerate(feats):
        imp_rows.append({"feature": col, "importance_mean": imp.importances_mean[i],
                         "importance_std": imp.importances_std[i]})
    imp_df = pd.DataFrame(imp_rows).sort_values("importance_mean", ascending=False)
    savetable(imp_df, f"06_perm_importance_{tag}.csv")

    fig, ax = plt.subplots(figsize=(8, 5))
    top = imp_df.head(12)
    sns.barplot(data=top, y="feature", x="importance_mean", ax=ax, color="steelblue")
    ax.set_title(f"Permutation importance (GBM) — {tag}")
    savefig(fig, f"06_perm_importance_{tag}.png")

    return pd.DataFrame(results), pipe_gb


def run_regression(df: pd.DataFrame, k: int):
    use = df[df["eligible_12m"] & ~df["left_censored"] & df["wallets_m12"].notna()].copy()
    use["has_token"] = use["has_token"].astype(int)
    train, test = time_split(use)
    if len(train) < 40 or len(test) < 15:
        print(f"  skip regression k={k}")
        return None
    feats = FEATURE_COLS + CAT_COLS
    rows = []
    for name, model in [
        ("ridge", Ridge(alpha=1.0)),
        ("gbm", GradientBoostingRegressor(random_state=42)),
    ]:
        pipe = Pipeline([("pre", make_preprocessor()), ("reg", model)])
        pipe.fit(train[feats], train["y_log_wallets_m12"])
        pred = pipe.predict(test[feats])
        r2 = r2_score(test["y_log_wallets_m12"], pred)
        mae = mean_absolute_error(test["y_log_wallets_m12"], pred)
        rows.append({"model": name, "k": k, "r2": r2, "mae": mae,
                     "n_train": len(train), "n_test": len(test)})
        print(f"  reg {name} k={k}: R2={r2:.3f} MAE={mae:.3f}")

        if name == "gbm":
            fig, ax = plt.subplots(figsize=(5, 5))
            ax.scatter(test["y_log_wallets_m12"], pred, alpha=0.5, s=20)
            lims = [
                min(test["y_log_wallets_m12"].min(), pred.min()),
                max(test["y_log_wallets_m12"].max(), pred.max()),
            ]
            ax.plot(lims, lims, ls="--", color="gray")
            ax.set_xlabel("Actual log1p(wallets m12)")
            ax.set_ylabel("Predicted")
            ax.set_title(f"Regression k={k} (R²={r2:.2f})")
            savefig(fig, f"06_regression_scatter_k{k}.png")
    return pd.DataFrame(rows)


def main() -> None:
    setup_style()
    print("== 06 predictive EDA ==")
    panel = load_panel()
    static = load_static()
    life = annotate_lifecycle(load_lifecycle(), static)

    # Attach cluster if available
    if CLUSTER_ASSIGN.exists():
        cl = pd.read_csv(CLUSTER_ASSIGN)[["slug", "cluster_name"]].drop_duplicates("slug")
        life = life.merge(cl, on="slug", how="left")

    all_feat = []
    for k in (3, 6):
        print(f"  building early features k={k}...")
        feat = early_features(panel, life, k)
        feat = add_targets(feat)
        if "cluster_name" in life.columns:
            feat = feat.merge(life[["slug", "cluster_name"]], on="slug", how="left")
        savetable(feat, f"06_early_features_k{k}.csv")
        all_feat.append(feat)

        # Base rates by launch year
        br = (
            feat[feat["eligible_12m"] & ~feat["left_censored"]]
            .groupby("launch_year")
            .agg(
                n=("slug", "count"),
                peak_10k_rate=("y_peak_10k", "mean"),
                topq_rate=("y_peak_topq", "mean"),
                median_wallets_m12=("wallets_m12", "median"),
            )
            .reset_index()
        )
        savetable(br, f"06_base_rates_k{k}.csv")
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(br["launch_year"] - 0.15, br["peak_10k_rate"], width=0.3, label="peak≥10k")
        ax.bar(br["launch_year"] + 0.15, br["topq_rate"], width=0.3, label="top quartile peak")
        ax.set_ylabel("Rate")
        ax.set_xlabel("Launch year")
        ax.set_title(f"Outcome base rates by cohort (k={k} feature set)")
        ax.legend()
        savefig(fig, f"06_base_rates_k{k}.png")

        # Univariate AUC
        use = feat[feat["eligible_12m"] & ~feat["left_censored"]]
        for target in ("y_peak_10k", "y_peak_topq"):
            uni = univariate_auc(use, FEATURE_COLS, target)
            savetable(uni, f"06_univariate_{target}_k{k}.csv")
            fig, ax = plt.subplots(figsize=(8, 5))
            sns.barplot(data=uni, y="feature", x="auc", ax=ax, color="steelblue")
            ax.axvline(0.5, color="red", ls="--")
            ax.set_xlim(0.45, 1.0)
            ax.set_title(f"Univariate AUC — {target} (k={k})")
            savefig(fig, f"06_univariate_auc_{target}_k{k}.png")

        # Spearman for regression target
        cont = []
        for f in FEATURE_COLS:
            mask = use[f].notna() & use["y_log_wallets_m12"].notna()
            if mask.sum() < 30:
                continue
            rho = use.loc[mask, f].astype(float).corr(use.loc[mask, "y_log_wallets_m12"], method="spearman")
            cont.append({"feature": f, "spearman": rho})
        cont_df = pd.DataFrame(cont).sort_values("spearman", key=abs, ascending=False)
        savetable(cont_df, f"06_spearman_m12_k{k}.csv")

        # Feature correlation heatmap
        num = use[FEATURE_COLS].select_dtypes(include=[np.number, bool]).astype(float)
        corr = num.corr(method="spearman")
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr, cmap="RdBu_r", center=0, ax=ax, square=True,
                    xticklabels=True, yticklabels=True)
        ax.set_title(f"Early-feature Spearman correlation (k={k})")
        savefig(fig, "06_feature_corr_k{}.png".format(k))

        # Binned relationship for top features
        top_feats = uni.head(4)["feature"].tolist() if len(uni) else FEATURE_COLS[:4]
        fig, axes = plt.subplots(2, 2, figsize=(10, 8))
        for ax, f in zip(axes.ravel(), top_feats):
            tmp = use[[f, "y_peak_10k"]].dropna()
            try:
                tmp["bin"] = pd.qcut(tmp[f].astype(float), q=5, duplicates="drop")
                rates = tmp.groupby("bin", observed=True)["y_peak_10k"].mean()
                rates.plot(kind="bar", ax=ax, color="steelblue")
                ax.set_ylabel("P(peak≥10k)")
                ax.set_title(f)
                ax.tick_params(axis="x", rotation=30)
            except Exception:
                ax.set_visible(False)
        fig.suptitle(f"Binned feature → peak≥10k (k={k})")
        fig.tight_layout()
        savefig(fig, f"06_binned_relationships_k{k}.png")

    # Baselines
    model_rows = []
    for feat in all_feat:
        k = int(feat["k"].iloc[0])
        for target in ("y_peak_10k", "y_peak_topq"):
            tag = f"{target}_k{k}"
            out = run_binary(feat, target, k, tag)
            if out is not None:
                model_rows.append(out[0])
        reg = run_regression(feat, k)
        if reg is not None:
            savetable(reg, f"06_regression_results_k{k}.csv")

    if model_rows:
        models = pd.concat(model_rows, ignore_index=True)
        savetable(models, "06_model_results.csv")

        # k=3 vs k=6 comparison
        fig, ax = plt.subplots(figsize=(8, 4))
        pivot = models[models["model"] == "gbm"].pivot_table(
            index="target", columns="k", values="auc"
        )
        pivot.plot(kind="bar", ax=ax)
        ax.set_ylabel("Test AUC")
        ax.set_title("Signal: k=3 vs k=6 observation window (GBM)")
        ax.set_ylim(0.5, 1.0)
        ax.legend(title="k months")
        ax.tick_params(axis="x", rotation=15)
        savefig(fig, "06_k3_vs_k6_auc.png")

    # Recommendation blurb table
    rec = pd.DataFrame([
        {
            "recommendation": "primary_target",
            "choice": "y_peak_10k (binary: peak active wallets ≥ 10k)",
            "rationale": "Clear, interpretable, decent base rate among eligible DApps; aligns with 'becomes popular'.",
        },
        {
            "recommendation": "secondary_target",
            "choice": "y_log_wallets_m12 (regression)",
            "rationale": "Preserves magnitude; useful for ranking. Requires eligible_12m filter.",
        },
        {
            "recommendation": "observation_window",
            "choice": "Prefer k=6 if AUC lift is material; else k=3 for earlier prediction",
            "rationale": "Compare 06_k3_vs_k6_auc.png; earlier window is more actionable for the research goal.",
        },
        {
            "recommendation": "exclusions",
            "choice": "Drop left_censored; require eligible_12m for labels; never use tvl/lifecycle/decay as features",
            "rationale": "See 01_leakage_risks.csv",
        },
        {
            "recommendation": "validation",
            "choice": "Time-based split by launch_year (≤2022 train, 2023–2024 test)",
            "rationale": "Avoids temporal leakage from shared market regimes within random CV folds.",
        },
    ])
    savetable(rec, "06_modelling_recommendations.csv")
    print("== 06 done ==")


if __name__ == "__main__":
    main()
