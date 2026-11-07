"""Run DeepSurv (and a Cox PH baseline) on the three survival events, over repeated stratified splits.

    python -m src.run_survival            # fixed DeepSurv config
    python -m src.run_survival --tune     # tune DeepSurv per outer split (validation part only)
"""
import argparse
import warnings

import numpy as np
import pandas as pd
import yaml

from src.data.build_survival_table import assemble, build_survival_tables
from src.data.splits import stratified_event_split
from src.evaluation.survival_metrics import c_index, survival_metrics
from src.models.deepsurv import DeepSurv
from src.models.survival_baselines import CoxBaseline
from src.tuning.search import tune_deepsurv

warnings.filterwarnings("ignore")

# (event, feature set) combinations. 'early' on reach_* is flagged as potentially optimistic
# because the early window overlaps the outcome window (see build_survival_table.py).
RUNS = [
    ("decline", "static"),
    ("decline", "early"),
    ("reach_1k", "static"),
    ("reach_1k", "early"),
    ("reach_10k", "static"),
]


def permutation_importance(model, X, d, e, cols, rng, n_rep=5):
    base = c_index(d, e, model.risk(X))
    out = {}
    for j, c in enumerate(cols):
        drops = []
        for _ in range(n_rep):
            Xp = X.copy()
            Xp[:, j] = rng.permutation(Xp[:, j])
            drops.append(base - c_index(d, e, model.risk(Xp)))
        out[c] = np.mean(drops)
    return pd.Series(out)


def main(tune=False, n_trials=12):
    suffix = "tuned" if tune else "default"
    cfg = yaml.safe_load(open("configs/data.yaml"))
    ds_cfg = yaml.safe_load(open("configs/deepsurv.yaml"))
    s = cfg["survival"]
    events, tables = build_survival_tables(cfg["raw_dir"], s["min_peak_wallets"], s["decline_fraction"], s["smooth_window"])

    rows, importances, oof_risk = [], {}, {}
    for event, fset in RUNS:
        Xdf, dur, evt = assemble(events, tables, event, fset)
        X, d, e = Xdf.to_numpy(), dur.to_numpy(), evt.to_numpy()
        cols = list(Xdf.columns)
        times = np.unique(np.round(np.quantile(d[e == 1], ds_cfg["time_quantiles"])))
        imps, risks = [], []
        for seed in s["seeds"]:
            tr, va, te = stratified_event_split(e, seed, s["test_frac"], s["val_frac"])
            cfg_ds = ds_cfg
            if tune:  # uses only this split's train/validation parts; the test part is never touched
                cfg_ds, _ = tune_deepsurv(X[tr], d[tr], e[tr], X[va], d[va], e[va], ds_cfg, n_trials, seed)
            ds = DeepSurv(cfg_ds, seed).fit(X[tr], d[tr], e[tr], X[va], d[va], e[va])
            cox = CoxBaseline().fit(X[np.r_[tr, va]], d[np.r_[tr, va]], e[np.r_[tr, va]])
            for name, m in [("DeepSurv", ds), ("CoxPH", cox)]:
                r = {"event": event, "features": fset, "model": name, "seed": seed}
                r["c_index"] = c_index(d[te], e[te], m.risk(X[te]))
                r.update(survival_metrics(m.survival(X[te]), d[te], e[te], times))
                rows.append(r)
            imps.append(permutation_importance(ds, X[te], d[te], e[te], cols, np.random.default_rng(seed)))
            risks.append(pd.Series(ds.risk(X[te]), index=Xdf.index[te]))
        importances[(event, fset)] = pd.concat(imps, axis=1).mean(axis=1)
        oof_risk[(event, fset)] = pd.concat(risks, axis=1).mean(axis=1).rename("deepsurv_log_risk")
        print(f"done {event}/{fset}: n={len(d)}, events={e.sum()}, times={times.tolist()}")

    res = pd.DataFrame(rows)
    metric_cols = [c for c in res.columns if c not in ("event", "features", "model", "seed")]
    summ = res.groupby(["event", "features", "model"])[metric_cols].agg(["mean", "std"])
    summ.columns = [f"{a}_{b}" for a, b in summ.columns]
    res.to_csv(f"{cfg['results_dir']}/survival_metrics_by_seed_{suffix}.csv", index=False)
    summ.to_csv(f"{cfg['results_dir']}/survival_metrics_{suffix}.csv")

    show = summ[["c_index_mean", "c_index_std", "c_index_td_mean", "ibs_mean"]].round(3)
    print("\nSurvival metrics (mean/std over seeds, held-out test splits)")
    print(show.to_string())

    for (event, fset), imp in importances.items():
        imp.sort_values(ascending=False).to_csv(f"{cfg['results_dir']}/deepsurv_permutation_importance_{event}_{fset}_{suffix}.csv", header=["c_index_drop"])
        oof_risk[(event, fset)].to_frame().to_parquet(f"{cfg['results_dir']}/deepsurv_risk_scores_{event}_{fset}_{suffix}.parquet")
    print("\nTop permutation importances (decline/early):")
    print(importances[("decline", "early")].sort_values(ascending=False).head(6).round(4).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tune", action="store_true")
    ap.add_argument("--trials", type=int, default=12)
    a = ap.parse_args()
    main(a.tune, a.trials)
