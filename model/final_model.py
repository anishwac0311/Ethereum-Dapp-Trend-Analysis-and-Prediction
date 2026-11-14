"""Final Ethereum DApp success model: blend + calibration + confidence bands.

Components (the two that won the pooled out-of-fold comparison in robust_eval):
  1. soft-label HGB on on-chain + off-chain + news + wallet-level + window TVL features
  2. pooled panel AR forecaster (log wallets at months 10-12, Gaussian residual)
Blend = mean of the two logits, then Platt calibration.

Confidence bands, so the model can say "I don't know" instead of guessing:
  likely_fail     P below t_lo, chosen so >= FAIL_NPV of these really fail
  likely_success  P above t_hi, chosen so >= SUCCESS_PRECISION really succeed
  uncertain       everything in between
Thresholds are chosen on the 2021-2023 folds and checked on the unseen 2024 fold,
then re-chosen on all folds for production.

  python model/final_model.py --k 3 6

Outputs: tables/final_eval_k{k}.csv, tables/final_bands_k{k}.csv,
         tables/final_predictions_launch2025_k{k}.csv, artifacts/final_k{k}.joblib
"""
from __future__ import annotations

import argparse

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

import panel_forecast as pf
from common import MODEL, annotate_lifecycle, load_lifecycle, load_panel, load_static, savetable, setup_style
from features import FEATURE_COLS_PLUS_WALLET_TVL, TVL_FEATURES, WALLET_FEATURES
from robust_eval import (
    REF_ABS,
    REF_REL,
    _cols,
    expanding_folds,
    fit_hard,
    grid_labels,
    grid_scores,
    load_dataset,
    train_soft,
)

FINAL_COLS = list(FEATURE_COLS_PLUS_WALLET_TVL)
FAIL_NPV = 0.95
SUCCESS_PRECISION = 0.80
MIN_BAND = 5
EPS = 1e-4
ARTIFACTS = MODEL / "artifacts"


def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def ar_probs(rows, train_slugs, df, k, fallback):
    """Panel-AR P(success) for df; DApps without an origin row get `fallback`."""
    fc = pf.forecast_dapps(rows, train_slugs, df["slug"], k, kind="ar")
    model = fc.attrs["model"]
    fc = df[["slug"]].merge(fc, on="slug", how="left")
    p = pf.prob_from_forecast(fc.fillna({"fc_sigma": model.sigma}), REF_ABS, REF_REL)
    return np.where(np.isfinite(p), p, fallback), model


def blend_logit(p_hgb, p_ar):
    return 0.5 * _logit(p_hgb) + 0.5 * _logit(p_ar)


def choose_bands(p, y, fail_npv=FAIL_NPV, success_precision=SUCCESS_PRECISION):
    """Widest bands meeting the targets. Returns (t_lo, t_hi); NaN if a target is unreachable."""
    order = np.argsort(p)
    ps, ys = p[order], y[order]
    t_lo = np.nan
    for i in range(MIN_BAND, len(ps) + 1):
        if 1 - ys[:i].mean() >= fail_npv:
            t_lo = (ps[i - 1] + ps[i]) / 2 if i < len(ps) else ps[-1] + EPS
    t_hi = np.nan
    for i in range(len(ps) - MIN_BAND, -1, -1):
        if ys[i:].mean() >= success_precision:
            t_hi = (ps[i - 1] + ps[i]) / 2 if i > 0 else ps[0] - EPS
    if np.isfinite(t_lo) and np.isfinite(t_hi) and t_hi <= t_lo:
        t_hi = np.nan
    return t_lo, t_hi


def band_of(p, t_lo, t_hi):
    b = np.full(len(p), "uncertain", dtype=object)
    if np.isfinite(t_lo):
        b[p < t_lo] = "likely_fail"
    if np.isfinite(t_hi):
        b[p >= t_hi] = "likely_success"
    return b


def band_report(p, y, t_lo, t_hi, split):
    b = band_of(p, t_lo, t_hi)
    conf = b != "uncertain"
    pred = (b == "likely_success").astype(int)
    lf, ls = b == "likely_fail", b == "likely_success"
    return {
        "split": split, "n": len(y), "t_lo": t_lo, "t_hi": t_hi,
        "coverage": conf.mean(),
        "confident_accuracy": (pred[conf] == y[conf]).mean() if conf.any() else np.nan,
        "n_likely_fail": int(lf.sum()), "fail_npv": 1 - y[lf].mean() if lf.any() else np.nan,
        "n_likely_success": int(ls.sum()), "success_precision": y[ls].mean() if ls.any() else np.nan,
        "successes_caught": y[ls].sum() / max(y.sum(), 1),
        "n_uncertain": int((~conf).sum()),
        "uncertain_success_rate": y[~conf].mean() if (~conf).any() else np.nan,
    }


def run(k: int) -> None:
    ds = load_dataset(k)
    panel = load_panel()
    life = annotate_lifecycle(load_lifecycle(), load_static())
    rows = pf.build_rows(k, panel, life)
    tvl_cov = ds["has_tvl"].fillna(0).mean() if "has_tvl" in ds else 0
    print(f"\n== final model k={k}: {len(ds)} DApps, wallet cov "
          f"{ds[WALLET_FEATURES].notna().any(axis=1).mean():.2f}, TVL cov {tvl_cov:.2f} ==")

    # --- pooled out-of-fold components -------------------------------------
    parts = []
    for name, tr, va in expanding_folds(ds):
        part = va[["slug", "parent_protocol", "launch_year", "mean_wallets_10_12",
                   "window_max_wallets", "y_sustained_12"]].copy()
        part["fold"] = name
        part["hgb"] = fit_hard(tr, va, FINAL_COLS)
        part["p_hgb"] = train_soft(tr, FINAL_COLS).predict_proba(va[_cols(FINAL_COLS)])[:, 1]
        part["p_ar"], _ = ar_probs(rows, tr["slug"], va, k, fallback=part["p_hgb"].values)
        part["z"] = blend_logit(part["p_hgb"], part["p_ar"])
        parts.append(part)
        print(f"  {name}: val={len(va)} pos={va['y_sustained_12'].sum()}")
    oof = pd.concat(parts, ignore_index=True)
    y = oof["y_sustained_12"].values

    # leave-one-fold-out Platt calibration -> honest probabilities
    oof["p_final"] = np.nan
    for f in oof["fold"].unique():
        m = oof["fold"] == f
        cal = LogisticRegression().fit(oof.loc[~m, ["z"]], y[~m])
        oof.loc[m, "p_final"] = cal.predict_proba(oof.loc[m, ["z"]])[:, 1]
    p = oof["p_final"].values

    labels = grid_labels(oof)
    evals = []
    for name, col in (("final_blend", "p_final"), ("hgb_soft_wallet_tvl", "p_hgb"),
                      ("panel_ar", "p_ar"), ("hgb_hard_same_features", "hgb")):
        g = grid_scores(oof.rename(columns={col: name}), name, labels)
        evals.append({
            "model": name, "k": k, "n": len(y), "n_pos": int(y.sum()),
            "auc": roc_auc_score(y, oof[col]), "ap_ref": average_precision_score(y, oof[col]),
            "ap_grid_mean": float(np.nanmean(list(g.values()))),
            "brier": brier_score_loss(y, oof["p_final"]) if col == "p_final" else np.nan,
        })
    ev = pd.DataFrame(evals)
    savetable(ev, f"final_eval_k{k}.csv")
    print(ev.round(3).to_string(index=False))

    # --- confidence bands: choose on 2021-23, test on 2024 ------------------
    dev = oof["fold"] != "val_2024"
    t_lo, t_hi = choose_bands(p[dev], y[dev])
    bands = [band_report(p[dev], y[dev], t_lo, t_hi, "chosen_on_2021_2023"),
             band_report(p[~dev], y[~dev], t_lo, t_hi, "test_2024_unseen")]
    T_lo, T_hi = choose_bands(p, y)
    bands.append(band_report(p, y, T_lo, T_hi, "production_all_folds"))
    br = pd.DataFrame(bands)
    savetable(br, f"final_bands_k{k}.csv")
    show = ["split", "n", "t_lo", "t_hi", "coverage", "confident_accuracy", "fail_npv",
            "success_precision", "successes_caught", "uncertain_success_rate"]
    print(br[show].round(3).to_string(index=False))

    # --- production fit + scoring of 2025 launches ---------------------------
    cal = LogisticRegression().fit(oof[["z"]], y)
    hgb = train_soft(ds, FINAL_COLS)
    full = pd.read_csv(MODEL / "tables" / f"dataset_k{k}.csv")
    for c in WALLET_FEATURES + TVL_FEATURES:
        if c not in full.columns:
            full[c] = np.nan
    new = full[(full["launch_year"] >= 2025) & ~full["left_censored"].astype(bool)].copy()
    new = new[~new["slug"].isin(ds["slug"])]
    artifact = {"hgb": hgb, "calibrator": cal, "feature_cols": FINAL_COLS, "k": k,
                "t_lo": T_lo, "t_hi": T_hi, "target": f"sustained_{REF_ABS}_{REF_REL}"}
    if len(new):
        new["has_token"] = new["has_token"].astype(int)
        ph = hgb.predict_proba(new[_cols(FINAL_COLS)])[:, 1]
        pa, ar = ar_probs(rows, ds["slug"], new, k, fallback=ph)
        artifact["panel_ar"] = ar
        pf_ = cal.predict_proba(pd.DataFrame({"z": blend_logit(ph, pa)}))[:, 1]
        out = new[["slug", "category_group", "launch_month", "max_wallets", "last_wallets"]].copy()
        out["p_success"], out["p_hgb_soft"], out["p_panel_ar"] = pf_, ph, pa
        out["band"] = band_of(pf_, T_lo, T_hi)
        out = out.sort_values("p_success", ascending=False)
        savetable(out, f"final_predictions_launch2025_k{k}.csv")
        print(f"  2025 launches scored: {len(out)}  bands: {out['band'].value_counts().to_dict()}")
    ARTIFACTS.mkdir(exist_ok=True)
    joblib.dump(artifact, ARTIFACTS / f"final_k{k}.joblib")
    print(f"  saved artifacts/final_k{k}.joblib")


def main() -> None:
    setup_style()
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, nargs="+", default=[3, 6])
    args = ap.parse_args()
    print("== final_model ==")
    for k in args.k:
        run(k)
    print("== final_model done ==")


if __name__ == "__main__":
    main()
