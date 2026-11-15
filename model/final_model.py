"""Final Ethereum DApp success model (v3): nested ensemble + calibration + confidence bands.

v3 is the outcome of the modelling iterations in iterations.py. For each checkpoint k
the ensemble is the logit mean of the top models by grid-mean PR-AUC (at least one
forecaster and one classifier). Two versions are kept apart:

  honest evaluation   members re-chosen for each validation year using only the other
                      years (iterations.py: ens_nested); calibration leave-one-fold-out;
                      band thresholds chosen on 2021-23 and tested on unseen 2024
  production          members chosen on all folds, refit on every eligible DApp, used to
                      score 2025 launches

Confidence bands, so the model can say "I don't know" instead of guessing:
  likely_fail     P below t_lo, chosen so >= FAIL_NPV of these really fail
  likely_success  P above t_hi, chosen so >= SUCCESS_PRECISION really succeed
  uncertain       everything in between

Two-stage policy (month 3 -> month 6): act on confident month-3 calls, re-score the
uncertain ones at month 6.

  python model/iterations.py --k 3 6     # first: writes tables/iterations_oof_k{k}.csv
  python model/final_model.py --k 3 6

Outputs: tables/final_eval_k{k}.csv, final_bands_k{k}.csv, final_two_stage.csv,
         final_predictions_launch2025_k{k}.csv, artifacts/final_k{k}.joblib
"""
from __future__ import annotations

import argparse

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, balanced_accuracy_score, brier_score_loss,
                             roc_auc_score)

import iterations as it
import panel_forecast as pf
from common import MODEL, annotate_lifecycle, load_lifecycle, load_panel, load_static, savetable, setup_style
from features import TOKEN_FEATURES, TVL_FEATURES, WALLET_FEATURES
from robust_eval import grid_labels, grid_scores, load_dataset

FAIL_NPV = 0.95
SUCCESS_PRECISION = 0.80
MIN_BAND = 5
EPS = 1e-4
ARTIFACTS = MODEL / "artifacts"
COMPARE = ["final_blend_v1", "panel_ar", "szabo_huberman", "hgb_v1"]


def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


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


def lofo_platt(oof, z, y):
    p = np.full(len(oof), np.nan)
    for f in oof["fold"].unique():
        m = (oof["fold"] == f).values
        cal = LogisticRegression().fit(z[~m].reshape(-1, 1), y[~m])
        p[m] = cal.predict_proba(z[m].reshape(-1, 1))[:, 1]
    return p


def load_oof(k):
    path = MODEL / "tables" / f"iterations_oof_k{k}.csv"
    if not path.exists():
        raise SystemExit(f"missing {path}: run `python model/iterations.py --k {k}` first")
    return pd.read_csv(path)


def candidate_names(oof):
    reg = it.experiments()
    return [n for n in reg if n in oof.columns]


def evaluate(k):
    """Honest numbers from the nested ensemble + comparison rows."""
    oof = load_oof(k)
    y = oof["y_sustained_12"].values
    labels = grid_labels(oof)
    oof["p_final"] = lofo_platt(oof, _logit(oof["ens_nested"].values), y)
    evals = []
    for name in ["ens_nested"] + [c for c in COMPARE if c in oof.columns]:
        pc = oof["p_final"].values if name == "ens_nested" else lofo_platt(oof, _logit(oof[name].values), y)
        g = grid_scores(oof, name, labels)
        evals.append({
            "model": "final_v3_nested_ensemble" if name == "ens_nested" else name, "k": k,
            "n": len(y), "n_pos": int(y.sum()),
            "auc": roc_auc_score(y, oof[name]), "ap_ref": average_precision_score(y, oof[name]),
            "ap_grid_mean": float(np.nanmean(list(g.values()))),
            "brier": brier_score_loss(y, pc), "accuracy_at_0.5": float(((pc >= 0.5) == y).mean()),
            "balanced_acc": balanced_accuracy_score(y, it.lofo_threshold(oof, pc, y)),
        })
    ev = pd.DataFrame(evals)
    savetable(ev, f"final_eval_k{k}.csv")
    print(ev.round(3).to_string(index=False))

    p = oof["p_final"].values
    dev = (oof["fold"] != "val_2024").values
    t_lo, t_hi = choose_bands(p[dev], y[dev])
    bands = [band_report(p[dev], y[dev], t_lo, t_hi, "chosen_on_2021_2023"),
             band_report(p[~dev], y[~dev], t_lo, t_hi, "test_2024_unseen")]
    return oof, ev, bands, (t_lo, t_hi)


def production(k, oof, bands):
    """Members chosen on all folds; calibrator and thresholds from their OOF logit mean."""
    y = oof["y_sustained_12"].values
    names = candidate_names(oof)
    members = it.pick_members(oof, names, grid_labels(oof))
    z = np.mean([_logit(oof[n].values) for n in members], axis=0)
    cal = LogisticRegression().fit(z.reshape(-1, 1), y)
    p_all = cal.predict_proba(z.reshape(-1, 1))[:, 1]
    T_lo, T_hi = choose_bands(p_all, y)
    bands.append(band_report(p_all, y, T_lo, T_hi, "production_all_folds"))
    br = pd.DataFrame(bands)
    savetable(br, f"final_bands_k{k}.csv")
    show = ["split", "n", "t_lo", "t_hi", "coverage", "confident_accuracy", "fail_npv",
            "success_precision", "successes_caught", "uncertain_success_rate"]
    print(br[show].round(3).to_string(index=False))
    print(f"  production members: {members}")

    # refit members on all eligible DApps, score 2025 launches
    from user_history_features import merge_user_history
    ds = merge_user_history(load_dataset(k), k)
    full = pd.read_csv(MODEL / "tables" / f"dataset_k{k}.csv")
    new = full[(full["launch_year"] >= 2025) & ~full["left_censored"].astype(bool)].copy()
    new = new[~new["slug"].isin(ds["slug"])]
    artifact = {"k": k, "members": members, "calibrator": cal, "t_lo": T_lo, "t_hi": T_hi,
                "target": "sustained_1000_0.25",
                "note": "members are iterations.py experiment names; refit with iterations.experiments()"}
    if len(new):
        new["launch_month"] = pd.to_datetime(new["launch_month"], errors="coerce")
        new["has_token"] = new["has_token"].astype(int)
        for c in WALLET_FEATURES + TVL_FEATURES + TOKEN_FEATURES:
            if c not in new.columns:
                new[c] = np.nan
        new = merge_user_history(new, k)
        rows = it.add_lags(pf.build_rows(k, load_panel(), annotate_lifecycle(load_lifecycle(), load_static())), k)
        ctx = {"rows": rows, "k": k}
        reg = it.experiments()
        ps = {}
        for n in members:
            r = reg[n][2](ds, new, ctx)
            ps[n] = np.asarray(r["p"] if isinstance(r, dict) else r)
        zn = np.mean([_logit(ps[n]) for n in members], axis=0)
        pn = cal.predict_proba(zn.reshape(-1, 1))[:, 1]
        out = new[["slug", "category_group", "launch_month", "max_wallets", "last_wallets"]].copy()
        out["p_success"] = pn
        for n in members:
            out[f"p_{n}"] = ps[n]
        out["band"] = band_of(pn, T_lo, T_hi)
        out = out.sort_values("p_success", ascending=False)
        savetable(out, f"final_predictions_launch2025_k{k}.csv")
        print(f"  2025 launches scored: {len(out)}  bands: {out['band'].value_counts().to_dict()}")
    ARTIFACTS.mkdir(exist_ok=True)
    joblib.dump(artifact, ARTIFACTS / f"final_k{k}.joblib")
    print(f"  saved artifacts/final_k{k}.joblib")


def two_stage(results):
    """Month-3 confident calls first; uncertain DApps re-scored at month 6."""
    if not {3, 6} <= set(results):
        return
    a, b = results[3], results[6]
    m = a["oof"][["slug", "fold", "y_sustained_12", "p_final"]].merge(
        b["oof"][["slug", "p_final"]], on="slug", suffixes=("_3", "_6"))
    rows = []
    for split, sel in (("test_2024_unseen", m["fold"] == "val_2024"),
                       ("all_folds_pooled", np.ones(len(m), bool))):
        s = m[sel]
        y = s["y_sustained_12"].values
        b3 = band_of(s["p_final_3"].values, *a["thr"])
        b6 = band_of(s["p_final_6"].values, *b["thr"])
        call3 = b3 != "uncertain"
        final_band = np.where(call3, b3, b6)
        conf = final_band != "uncertain"
        pred = (final_band == "likely_success").astype(int)
        forced = np.where(conf, pred, (s["p_final_6"].values >= 0.5).astype(int))
        n_pos = int(y.sum())
        rows.append({"split": split, "policy": "always say 'fail'", "coverage": 1.0,
                     "confident_accuracy": 1 - y.mean(), "successes_caught": 0, "n_successes": n_pos})
        for name, bb in (("month 3 only", b3), ("month 6 only", b6)):
            c = bb != "uncertain"
            rows.append({"split": split, "policy": name, "coverage": c.mean(),
                         "confident_accuracy": ((bb[c] == "likely_success").astype(int) == y[c]).mean(),
                         "decided_at_month_3": float(c.mean()) if name == "month 3 only" else 0.0,
                         "successes_caught": int(((bb == "likely_success") & (y == 1)).sum()),
                         "n_successes": n_pos})
        rows.append({"split": split, "policy": "month 3, then month 6 for the uncertain",
                     "coverage": conf.mean(),
                     "confident_accuracy": (pred[conf] == y[conf]).mean(),
                     "decided_at_month_3": call3.mean(),
                     "forced_accuracy_all": (forced == y).mean(),
                     "successes_caught": int(((final_band == "likely_success") & (y == 1)).sum()),
                     "n_successes": n_pos})
    out = pd.DataFrame(rows)
    savetable(out, "final_two_stage.csv")
    print(out.round(3).to_string(index=False))


def main() -> None:
    setup_style()
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, nargs="+", default=[3, 6])
    args = ap.parse_args()
    print("== final_model v3 ==")
    results = {}
    for k in args.k:
        print(f"\n== final model k={k} ==")
        oof, ev, bands, thr = evaluate(k)
        production(k, oof, bands)
        results[k] = {"oof": oof, "thr": thr}
    print("\n== two-stage policy ==")
    two_stage(results)
    print("== final_model done ==")


if __name__ == "__main__":
    main()
