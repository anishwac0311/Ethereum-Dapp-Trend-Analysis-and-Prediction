"""Train, validate, and ablate sustained-success models.

Covers:
  - baselines (persistence / Szabo-Huberman / category prior)
  - L2 / elastic-net logistic, HistGradientBoosting, optional XGBoost
  - penalized Cox PH survival
  - rolling-origin CV by launch year + parent_protocol grouping
  - holdout 2023-24 with bootstrap CIs
  - ablations (no levels, no has_token, k-curve)
  - permutation importance / partial dependence
"""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path
from typing import Optional

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import PartialDependenceDisplay, permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from baselines import precision_at_frac, run_all_baselines, score_probs
from common import savefig, savetable, setup_style
from features import (
    CAT_COLS,
    FEATURE_COLS,
    LEVEL_FEATURES,
    build_dataset,
)

try:
    from xgboost import XGBClassifier

    HAS_XGB = True
except Exception:
    HAS_XGB = False

try:
    import shap

    HAS_SHAP = True
except Exception:
    HAS_SHAP = False

try:
    from lifelines import CoxPHFitter

    HAS_LIFELINES = True
except Exception:
    HAS_LIFELINES = False

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

PRIMARY_TARGET = "y_sustained_12"
HOLDOUT_YEARS = {2023, 2024}
TRAIN_MAX_YEAR = 2022


# ---------------------------------------------------------------------------
# Splits
# ---------------------------------------------------------------------------
def eligible_frame(ds: pd.DataFrame, target: str = PRIMARY_TARGET) -> pd.DataFrame:
    out = ds[ds["eligible_12m"] & ~ds["left_censored"]].copy()
    if target == "y_sustained_24":
        out = ds[ds["eligible_24m"] & ~ds["left_censored"]].copy()
    out = out[out[target].notna()].copy()
    out[target] = out[target].astype(int)
    out["has_token"] = out["has_token"].astype(int)
    if "parent_protocol" not in out.columns:
        out["parent_protocol"] = out["slug"]
    out["parent_protocol"] = out["parent_protocol"].fillna(out["slug"])
    return out


def time_holdout(df: pd.DataFrame):
    train = df[df["launch_year"] <= TRAIN_MAX_YEAR].copy()
    test = df[df["launch_year"].isin(HOLDOUT_YEARS)].copy()
    return train, test


def rolling_origin_folds(df: pd.DataFrame) -> list[tuple[pd.DataFrame, pd.DataFrame, str]]:
    """Expanding window by launch year; groups stay intact via parent earliest year."""
    # Assign each parent to its earliest launch year so versions don't leak across folds
    parent_year = df.groupby("parent_protocol")["launch_year"].min()
    df = df.copy()
    df["parent_year"] = df["parent_protocol"].map(parent_year)

    years = sorted(y for y in df["parent_year"].dropna().unique() if y <= TRAIN_MAX_YEAR)
    folds = []
    for i, val_year in enumerate(years):
        if i == 0:
            continue
        train_years = [y for y in years if y < val_year]
        if not train_years:
            continue
        train = df[df["parent_year"].isin(train_years)]
        val = df[df["parent_year"] == val_year]
        # Also keep only rows whose own launch_year matches the fold logic
        if len(train) < 30 or len(val) < 10:
            continue
        if val[PRIMARY_TARGET].nunique() < 2 or train[PRIMARY_TARGET].nunique() < 2:
            continue
        folds.append((train, val, f"val_{int(val_year)}"))
    return folds


# ---------------------------------------------------------------------------
# Preprocessor / models
# ---------------------------------------------------------------------------
def make_preprocessor(feature_cols: list[str], cat_cols: list[str] = CAT_COLS):
    num_cols = [c for c in feature_cols if c not in cat_cols]
    # has_token is numeric 0/1 already in feature_cols
    return ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                num_cols,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                [c for c in cat_cols if c in feature_cols or c in CAT_COLS],
            ),
        ],
        remainder="drop",
    )


def feature_matrix_cols(feature_cols: list[str]) -> list[str]:
    cols = list(feature_cols)
    for c in CAT_COLS:
        if c not in cols:
            cols.append(c)
    return cols


def make_logreg(feature_cols: list[str], elastic: bool = False) -> Pipeline:
    pre = make_preprocessor(feature_cols)
    if elastic:
        clf = LogisticRegression(
            penalty="elasticnet",
            solver="saga",
            l1_ratio=0.5,
            C=0.5,
            max_iter=4000,
            class_weight="balanced",
        )
    else:
        clf = LogisticRegression(
            penalty="l2",
            C=1.0,
            max_iter=2000,
            class_weight="balanced",
        )
    return Pipeline([("pre", pre), ("clf", clf)])


def make_hgb(feature_cols: list[str]) -> Pipeline:
    pre = make_preprocessor(feature_cols)
    clf = HistGradientBoostingClassifier(
        max_depth=3,
        learning_rate=0.05,
        max_iter=200,
        min_samples_leaf=15,
        l2_regularization=1.0,
        random_state=42,
        class_weight="balanced",
    )
    return Pipeline([("pre", pre), ("clf", clf)])


def make_xgb(feature_cols: list[str]) -> Optional[Pipeline]:
    if not HAS_XGB:
        return None
    pre = make_preprocessor(feature_cols)
    # scale_pos_weight set at fit time via wrapper — use fixed estimate
    clf = XGBClassifier(
        max_depth=3,
        learning_rate=0.05,
        n_estimators=200,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        eval_metric="logloss",
        random_state=42,
        n_jobs=2,
    )
    return Pipeline([("pre", pre), ("clf", clf)])


def fit_predict(pipe: Pipeline, train: pd.DataFrame, test: pd.DataFrame,
                feature_cols: list[str], target: str) -> np.ndarray:
    cols = feature_matrix_cols(feature_cols)
    Xtr, ytr = train[cols], train[target]
    Xte = test[cols]
    # XGB scale_pos_weight
    if HAS_XGB and isinstance(pipe.named_steps.get("clf"), XGBClassifier):
        pos = max(int(ytr.sum()), 1)
        neg = max(int(len(ytr) - pos), 1)
        pipe.named_steps["clf"].set_params(scale_pos_weight=neg / pos)
    pipe.fit(Xtr, ytr)
    if hasattr(pipe, "predict_proba"):
        return pipe.predict_proba(Xte)[:, 1]
    return pipe.decision_function(Xte)


def calibrate_pipe(pipe: Pipeline, train: pd.DataFrame, feature_cols: list[str],
                   target: str, method: str = "isotonic") -> Pipeline:
    cols = feature_matrix_cols(feature_cols)
    # Need enough data for isotonic; fall back to sigmoid
    if len(train) < 80:
        method = "sigmoid"
    cal = CalibratedClassifierCV(pipe, method=method, cv=3)
    cal.fit(train[cols], train[target])
    return cal


# ---------------------------------------------------------------------------
# Metrics + bootstrap
# ---------------------------------------------------------------------------
def bootstrap_metrics(y, p, n_boot: int = 500, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    p = np.asarray(p)
    rows = []
    n = len(y)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        yb, pb = y[idx], p[idx]
        if len(np.unique(yb)) < 2:
            continue
        rows.append({
            "auc": roc_auc_score(yb, pb),
            "ap": average_precision_score(yb, pb),
            "brier": brier_score_loss(yb, pb),
            "precision_at_10pct": precision_at_frac(yb, pb, 0.10),
            "precision_at_20pct": precision_at_frac(yb, pb, 0.20),
        })
    if not rows:
        return {}
    boot = pd.DataFrame(rows)
    out = {}
    for col in boot.columns:
        out[f"{col}_lo"] = float(boot[col].quantile(0.025))
        out[f"{col}_hi"] = float(boot[col].quantile(0.975))
        out[f"{col}_mean"] = float(boot[col].mean())
    return out


# ---------------------------------------------------------------------------
# Survival
# ---------------------------------------------------------------------------
def run_cox(train: pd.DataFrame, test: pd.DataFrame, feature_cols: list[str]) -> Optional[dict]:
    if not HAS_LIFELINES:
        print("  lifelines not available; skip Cox")
        return None
    use_cols = [c for c in feature_cols if c != "has_token"] + ["has_token"]
    # Drop categoricals for Cox — one-hot manually a few
    num = [c for c in use_cols if c not in CAT_COLS]
    tr = train[num + ["survival_duration", "survival_event", "category_group"]].copy()
    te = test[num + ["survival_duration", "survival_event", "category_group"]].copy()
    tr = tr.dropna(subset=["survival_duration", "survival_event"])
    te = te.dropna(subset=["survival_duration", "survival_event"])
    if len(tr) < 40 or tr["survival_event"].sum() < 5:
        print("  insufficient survival events; skip Cox")
        return None

    # Simple category dummies (top categories)
    for df in (tr, te):
        for cat in ("DeFi", "DEX", "Gaming", "NFT", "Infrastructure"):
            df[f"cat_{cat}"] = (df["category_group"] == cat).astype(int)
        df.drop(columns=["category_group"], inplace=True)

    # Impute medians from train; drop columns that remain all-NaN (e.g. k=1 volatility)
    drop_cols = []
    for c in list(tr.columns):
        if c in ("survival_duration", "survival_event"):
            continue
        med = tr[c].median()
        if pd.isna(med):
            drop_cols.append(c)
            continue
        tr[c] = tr[c].fillna(med)
        te[c] = te[c].fillna(med)
    if drop_cols:
        tr = tr.drop(columns=drop_cols)
        te = te.drop(columns=drop_cols)
    # Drop any residual non-finite rows
    tr = tr.replace([np.inf, -np.inf], np.nan).dropna()
    te = te.replace([np.inf, -np.inf], np.nan).dropna()
    if len(tr) < 40 or tr["survival_event"].sum() < 5:
        print("  insufficient survival rows after cleaning; skip Cox")
        return None

    cph = CoxPHFitter(penalizer=0.1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            cph.fit(tr, duration_col="survival_duration", event_col="survival_event")
        except Exception as e:
            print(f"  Cox fit failed: {e}")
            return None

    try:
        c_index = float(cph.score(te, scoring_method="concordance_index"))
    except Exception:
        c_index = np.nan

    # P(survive past 12 - k months) approx via predict_survival_function
    # For k=3, horizon from window end to m12 is ~9 months
    try:
        surv = cph.predict_survival_function(te)
        # nearest time index
        times = surv.index.values
        target_t = min(times.max(), 9)
        t_idx = times[np.argmin(np.abs(times - target_t))]
        p_surv = surv.loc[t_idx].values
    except Exception:
        p_surv = np.full(len(te), np.nan)

    return {
        "model": "coxph",
        "c_index": c_index,
        "n_train": len(tr),
        "n_test": len(te),
        "n_events_train": int(tr["survival_event"].sum()),
        "n_events_test": int(te["survival_event"].sum()),
        "p_survive_horizon": p_surv,
        "test_slugs": te.index if "slug" not in te.columns else te.get("slug"),
        "cph": cph,
    }


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------
def plot_roc_pr(y, probs: dict, tag: str):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for name, p in probs.items():
        if len(np.unique(y)) < 2:
            continue
        fpr, tpr, _ = roc_curve(y, p)
        axes[0].plot(fpr, tpr, lw=2, label=f"{name} AUC={roc_auc_score(y, p):.3f}")
        prec, rec, _ = precision_recall_curve(y, p)
        axes[1].plot(rec, prec, lw=2, label=f"{name} AP={average_precision_score(y, p):.3f}")
    axes[0].plot([0, 1], [0, 1], ls="--", color="gray")
    axes[0].set_xlabel("FPR")
    axes[0].set_ylabel("TPR")
    axes[0].set_title(f"ROC — {tag}")
    axes[0].legend(fontsize=8)
    axes[1].axhline(np.mean(y), color="gray", ls="--", label="base rate")
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].set_title(f"PR — {tag}")
    axes[1].legend(fontsize=8)
    savefig(fig, f"roc_pr_{tag}.png")


def plot_calibration(y, p, tag: str):
    if len(np.unique(y)) < 2 or len(y) < 20:
        return
    fig, ax = plt.subplots(figsize=(5, 5))
    try:
        frac_pos, mean_pred = calibration_curve(y, p, n_bins=8, strategy="quantile")
        ax.plot(mean_pred, frac_pos, "o-", label="model")
    except Exception:
        return
    ax.plot([0, 1], [0, 1], ls="--", color="gray")
    ax.set_xlabel("Predicted probability")
    ax.set_ylabel("Fraction positive")
    ax.set_title(f"Calibration — {tag}")
    ax.legend()
    savefig(fig, f"calibration_{tag}.png")


# ---------------------------------------------------------------------------
# Main experiment for one k
# ---------------------------------------------------------------------------
def run_for_k(
    ds: pd.DataFrame,
    k: int,
    target: str = PRIMARY_TARGET,
    feature_cols: Optional[list[str]] = None,
    tag_suffix: str = "",
) -> dict:
    feature_cols = feature_cols or list(FEATURE_COLS)
    tag = f"{target}_k{k}{tag_suffix}"
    df = eligible_frame(ds, target)
    train, test = time_holdout(df)
    print(f"\n== {tag}: train={len(train)} (pos={train[target].mean():.3f}) "
          f"test={len(test)} (pos={test[target].mean():.3f}) ==")

    if len(train) < 40 or len(test) < 15 or test[target].nunique() < 2:
        print("  skip: insufficient data")
        return {}

    results = []

    # Baselines
    base_df = run_all_baselines(train, test, target)
    base_df["k"] = k
    base_df["target"] = target
    base_df["tag"] = tag
    results.append(base_df)

    probs = {}
    models = {
        "logreg_l2": make_logreg(feature_cols, elastic=False),
        "logreg_elastic": make_logreg(feature_cols, elastic=True),
        "hgb": make_hgb(feature_cols),
    }
    if HAS_XGB:
        models["xgboost"] = make_xgb(feature_cols)

    fitted = {}
    for name, pipe in models.items():
        if pipe is None:
            continue
        try:
            p = fit_predict(pipe, train, test, feature_cols, target)
        except Exception as e:
            print(f"  {name} failed: {e}")
            continue
        probs[name] = p
        fitted[name] = pipe
        m = score_probs(test[target].values, p, name, k=k, target=target, tag=tag)
        boot = bootstrap_metrics(test[target].values, p)
        m.update(boot)
        results.append(pd.DataFrame([m]))
        print(f"  {name}: AUC={m['auc']:.3f} AP={m['ap']:.3f} "
              f"P@10%={m['precision_at_10pct']:.3f}")

    # Calibrated HGB (best practical default)
    if "hgb" in fitted:
        try:
            cal = calibrate_pipe(make_hgb(feature_cols), train, feature_cols, target)
            cols = feature_matrix_cols(feature_cols)
            p_cal = cal.predict_proba(test[cols])[:, 1]
            probs["hgb_calibrated"] = p_cal
            m = score_probs(test[target].values, p_cal, "hgb_calibrated",
                            k=k, target=target, tag=tag)
            m.update(bootstrap_metrics(test[target].values, p_cal))
            results.append(pd.DataFrame([m]))
            fitted["hgb_calibrated"] = cal
            plot_calibration(test[target].values, p_cal, tag)
            # Persist for predict.py
            joblib.dump(
                {"model": cal, "feature_cols": feature_cols, "k": k, "target": target},
                ARTIFACTS / f"hgb_calibrated_k{k}.joblib",
            )
        except Exception as e:
            print(f"  calibration failed: {e}")

    plot_roc_pr(test[target].values, probs, tag)

    # Rolling-origin CV (on train only) for HGB + logreg
    cv_rows = []
    folds = rolling_origin_folds(train)
    for tr, va, fold_name in folds:
        for name, factory in (
            ("logreg_l2", lambda: make_logreg(feature_cols)),
            ("hgb", lambda: make_hgb(feature_cols)),
        ):
            try:
                p = fit_predict(factory(), tr, va, feature_cols, target)
                m = score_probs(va[target].values, p, name, fold=fold_name, k=k, target=target)
                cv_rows.append(m)
            except Exception as e:
                print(f"  CV {fold_name}/{name} failed: {e}")
    cv_df = pd.DataFrame(cv_rows) if cv_rows else pd.DataFrame()
    if len(cv_df):
        savetable(cv_df, f"cv_results_{tag}.csv")
        summary = (
            cv_df.groupby("model")[["auc", "ap", "brier"]]
            .agg(["mean", "std"])
            .reset_index()
        )
        # flatten columns
        summary.columns = ["_".join(c).strip("_") for c in summary.columns.values]
        savetable(summary, f"cv_summary_{tag}.csv")
        print("  CV summary:")
        print(summary.to_string(index=False))

    # Survival
    cox = run_cox(train, test, feature_cols)
    if cox is not None:
        savetable(
            pd.DataFrame([{
                "model": "coxph",
                "k": k,
                "c_index": cox["c_index"],
                "n_train": cox["n_train"],
                "n_test": cox["n_test"],
                "n_events_train": cox["n_events_train"],
                "n_events_test": cox["n_events_test"],
            }]),
            f"survival_{tag}.csv",
        )
        print(f"  Cox C-index={cox['c_index']:.3f}")

    # Permutation importance on HGB
    if "hgb" in fitted:
        cols = feature_matrix_cols(feature_cols)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                imp = permutation_importance(
                    fitted["hgb"], test[cols], test[target],
                    n_repeats=20, random_state=42, scoring="average_precision",
                )
                imp_df = pd.DataFrame({
                    "feature": cols,
                    "importance_mean": imp.importances_mean,
                    "importance_std": imp.importances_std,
                }).sort_values("importance_mean", ascending=False)
                savetable(imp_df, f"perm_importance_{tag}.csv")
                fig, ax = plt.subplots(figsize=(8, 6))
                top = imp_df.head(15)
                sns.barplot(data=top, y="feature", x="importance_mean", ax=ax, color="steelblue")
                ax.set_title(f"Permutation importance (AP) — {tag}")
                savefig(fig, f"perm_importance_{tag}.png")
            except Exception as e:
                print(f"  perm importance failed: {e}")

        # Partial dependence for top numeric drivers
        try:
            imp_df = pd.read_csv(
                Path(__file__).resolve().parent / "tables" / f"perm_importance_{tag}.csv"
            )
            top_num = [
                f for f in imp_df["feature"].tolist()
                if f in feature_cols and f not in CAT_COLS
            ][:4]
            if top_num:
                fig, axes = plt.subplots(2, 2, figsize=(10, 8))
                for ax, feat in zip(np.ravel(axes), top_num):
                    try:
                        PartialDependenceDisplay.from_estimator(
                            fitted["hgb"], test[cols], [feat], ax=ax,
                        )
                    except Exception:
                        ax.set_visible(False)
                fig.suptitle(f"Partial dependence — {tag}")
                fig.tight_layout()
                savefig(fig, f"pdp_{tag}.png")
        except Exception as e:
            print(f"  PDP failed: {e}")

        # Optional SHAP
        if HAS_SHAP:
            try:
                # Explain on preprocessed matrix via a thin wrapper is hard with Pipeline;
                # use TreeExplainer on HGB raw after transforming.
                Xte = fitted["hgb"].named_steps["pre"].transform(test[cols])
                explainer = shap.Explainer(
                    fitted["hgb"].named_steps["clf"], Xte
                )
                sv = explainer(Xte[: min(100, len(Xte))])
                fig = plt.figure()
                shap.summary_plot(sv, show=False)
                savefig(fig, f"shap_{tag}.png")
            except Exception as e:
                print(f"  SHAP failed: {e}")

    out = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
    if len(out):
        savetable(out, f"holdout_results_{tag}.csv")
    return {
        "results": out,
        "probs": probs,
        "fitted": fitted,
        "train": train,
        "test": test,
        "feature_cols": feature_cols,
        "tag": tag,
    }


def run_ablations(ds: pd.DataFrame, k: int = 3) -> pd.DataFrame:
    """Ablations: full vs no-level vs no-has_token."""
    rows = []
    variants = {
        "full": list(FEATURE_COLS),
        "no_levels": [c for c in FEATURE_COLS if c not in LEVEL_FEATURES],
        "no_has_token": [c for c in FEATURE_COLS if c != "has_token"],
        "levels_only": LEVEL_FEATURES + ["has_token", "launch_year"],
    }
    for name, cols in variants.items():
        print(f"\n-- ablation: {name} --")
        res = run_for_k(ds, k, feature_cols=cols, tag_suffix=f"_abl_{name}")
        if res and len(res["results"]):
            tmp = res["results"].copy()
            tmp["ablation"] = name
            # keep learned models only for comparison
            tmp = tmp[tmp["model"].isin(["logreg_l2", "hgb", "hgb_calibrated"])]
            rows.append(tmp)
    if not rows:
        return pd.DataFrame()
    abl = pd.concat(rows, ignore_index=True)
    savetable(abl, f"ablations_k{k}.csv")

    # Bar chart AP by ablation
    fig, ax = plt.subplots(figsize=(8, 4))
    plot_df = abl[abl["model"] == "hgb"]
    if len(plot_df):
        sns.barplot(data=plot_df, x="ablation", y="ap", ax=ax, color="steelblue")
        ax.set_ylabel("Holdout PR-AUC (HGB)")
        ax.set_title(f"Ablations k={k}")
        savefig(fig, f"ablations_k{k}.png")
    else:
        plt.close(fig)
    return abl


def run_k_curve(datasets: dict[int, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for k, ds in datasets.items():
        res = run_for_k(ds, k)
        if res and len(res["results"]):
            tmp = res["results"].copy()
            tmp["k"] = k
            rows.append(tmp)
    if not rows:
        return pd.DataFrame()
    all_res = pd.concat(rows, ignore_index=True)
    savetable(all_res, "all_holdout_results.csv")

    # k-curve for HGB / logreg (exclude ablation runs)
    fig, ax = plt.subplots(figsize=(7, 4))
    base = all_res.copy()
    if "tag" in base.columns:
        base = base[~base["tag"].astype(str).str.contains("abl", na=False)]
    if "target" in base.columns:
        base = base[base["target"] == PRIMARY_TARGET]
    for model in ("hgb", "logreg_l2", "szabo_huberman", "persistence"):
        sub = base[base["model"] == model].sort_values("k")
        if sub.empty or "ap" not in sub.columns:
            continue
        ax.plot(sub["k"], sub["ap"], "o-", label=model, lw=2)
    ax.set_xlabel("Observation window k (months)")
    ax.set_ylabel("Holdout PR-AUC")
    ax.set_title("Signal vs observation window")
    ax.set_xticks([1, 3, 6])
    ax.legend()
    savefig(fig, "k_curve_ap.png")
    return all_res


def main() -> None:
    setup_style()
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, nargs="+", default=[1, 3, 6])
    parser.add_argument("--skip-ablations", action="store_true")
    args = parser.parse_args()

    print("== train_eval ==")
    print(f"  xgboost={HAS_XGB} shap={HAS_SHAP} lifelines={HAS_LIFELINES}")

    datasets = {}
    for k in args.k:
        path = Path(__file__).resolve().parent / "tables" / f"dataset_k{k}.csv"
        if path.exists():
            ds = pd.read_csv(path)
            # restore types
            for c in ("launch_month",):
                if c in ds.columns:
                    ds[c] = pd.to_datetime(ds[c], errors="coerce")
        else:
            print(f"  building dataset k={k}...")
            ds = build_dataset(k)
            savetable(ds, f"dataset_k{k}.csv")
        datasets[k] = ds
        use = eligible_frame(ds)
        br = (
            use.groupby("launch_year")
            .agg(n=("slug", "count"), rate=(PRIMARY_TARGET, "mean"))
            .reset_index()
        )
        savetable(br, f"base_rates_model_k{k}.csv")
        print(f"  k={k} eligible n={len(use)} rate={use[PRIMARY_TARGET].mean():.3f}")
        print(br.to_string(index=False))

    all_res = run_k_curve(datasets)

    if not args.skip_ablations and 3 in datasets:
        run_ablations(datasets[3], k=3)

    # Secondary targets at k=3
    if 3 in datasets:
        for tgt in ("y_abs_12", "y_eco_topq_12", "y_sustained_24"):
            print(f"\n-- secondary target {tgt} --")
            run_for_k(datasets[3], 3, target=tgt, tag_suffix="")

        # Conditional (flash vs grower) — smaller sample
        cond = datasets[3]
        cond_use = cond[cond["passed_1k_in_window"] == 1]
        if len(eligible_frame(cond_use, "y_cond_sustained_12")) >= 40:
            run_for_k(cond_use, 3, target="y_cond_sustained_12")

    print("== train_eval done ==")


if __name__ == "__main__":
    main()
