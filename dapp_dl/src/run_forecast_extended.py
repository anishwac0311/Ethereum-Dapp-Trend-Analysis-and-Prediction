"""Extended forecast evaluation: 6 rolling origins, blends, per-horizon conformal intervals.

    python -m src.run_forecast_extended            # default configs, seeds 1 2 3
    python -m src.run_forecast_extended --smoke

Design (all time-ordered, nothing is fitted on data it is scored on)
  origins        6 cutoffs, 3 months apart (2024-03 ... 2025-06), horizon 6, default configs
                 (the tuned configs were tuned on windows ending 2024-12, so they would leak here)
  Part A         all 6 windows: Naive, LightGBM, N-HiTS, DeepAR median and two *unfitted* blends
                 (equal weights), with cluster-bootstrap (by dApp) CIs for paired MAE differences
  Part B         fit windows = first 3 origins, buffer = 4th, eval windows = last 2.
                 A fit-window target never extends past the first eval origin. Fitted here:
                 age-bucket blend weights N-HiTS vs LightGBM, and per-horizon conformal q.
"""
import argparse
import time
import warnings

import numpy as np
import pandas as pd
import yaml

from src.data.build_forecast_panel import build_forecast_panel
from src.evaluation.calibration import calibrate_by_horizon
from src.evaluation.forecast_metrics import by_group, interval_metrics, point_metrics
from src.models.baselines import lightgbm_forecast, naive_forecast
from src.models.deepar import build_deepar
from src.models.nhits import build_nhits
from src.models.rolling import rolling_forecast

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)


def abs_err(ev, col):
    return np.abs(ev.y - ev[col].clip(lower=0)).to_numpy()


def cluster_bootstrap(ev, a, b, n_boot=2000):
    """Paired MAE difference (a - b) with 95% CI, resampling dApps. Negative = a is better."""
    d = pd.DataFrame({"id": ev.unique_id.to_numpy(), "diff": abs_err(ev, a) - abs_err(ev, b)})
    g = d.groupby("id")["diff"].agg(["sum", "count"])
    s, c = g["sum"].to_numpy(), g["count"].to_numpy()
    idx = RNG.integers(0, len(g), size=(n_boot, len(g)))
    boots = s[idx].sum(1) / c[idx].sum(1)
    return s.sum() / c.sum(), np.percentile(boots, 2.5), np.percentile(boots, 97.5)


def main(smoke=False, seeds=(1, 2, 3)):
    cfg = yaml.safe_load(open("configs/data.yaml"))
    fc = cfg["forecast"]
    nh_cfg = yaml.safe_load(open("configs/nhits.yaml"))
    dp_cfg = yaml.safe_load(open("configs/deepar.yaml"))
    nw, step, h = fc["ext_windows"], fc["ext_step"], fc["horizon"]
    if smoke:
        nh_cfg["max_steps"] = dp_cfg["max_steps"] = 40
        nh_cfg["val_check_steps"] = dp_cfg["val_check_steps"] = 20
        seeds = seeds[:1]
    df, static = build_forecast_panel(cfg["raw_dir"], fc["min_peak_wallets"], fc["min_series_len"])
    print(f"{df.unique_id.nunique()} dApps; {nw} origins every {step} months; horizon {h}; seeds {list(seeds)}", flush=True)

    last = df.ds.max()
    cut_list = sorted(last - pd.DateOffset(months=h + i * step) for i in range(nw))
    keys = ["unique_id", "ds", "cutoff"]
    ev = None
    for sd in seeds:
        t = time.time()
        nh = rolling_forecast(lambda: build_nhits(static, nh_cfg, h, sd), df, static, cut_list, h)
        dp = rolling_forecast(lambda: build_deepar(static, dp_cfg, h, sd), df, static, cut_list, h)
        part = nh[keys + ["y", "NHITS"]].merge(dp.drop(columns="y"), on=keys, how="inner")
        part = part.rename(columns={c: f"{c}_s{sd}" for c in part.columns if c.startswith(("NHITS", "DeepAR"))})
        ev = part if ev is None else ev.merge(part.drop(columns="y"), on=keys, how="inner")
        print(f"  seed {sd} done in {time.time() - t:.0f}s", flush=True)
    ev = ev.reset_index(drop=True)
    for base in ["NHITS", "DeepAR-median", "DeepAR-lo-80", "DeepAR-hi-80"]:
        ev[base] = ev[[f"{base}_s{sd}" for sd in seeds]].mean(axis=1)
    ev["Naive"] = naive_forecast(df, ev)
    ev["LightGBM"] = lightgbm_forecast(df, static, ev, h, seed=seeds[0])
    ev = ev.dropna(subset=["Naive", "LightGBM", "NHITS", "DeepAR-median"]).reset_index(drop=True)
    ev["horizon_step"] = (ev.ds.dt.year - ev.cutoff.dt.year) * 12 + (ev.ds.dt.month - ev.cutoff.dt.month)
    age = df.set_index(["unique_id", "ds"]).months_since_launch
    ev["age_at_cutoff"] = age.reindex(pd.MultiIndex.from_arrays([ev.unique_id, ev.cutoff])).to_numpy()
    ev["age_bucket"] = pd.cut(ev.age_at_cutoff, [-1, 11, 35, 1e9], labels=["<12m", "12-35m", "36m+"])
    ev["Blend2"] = (ev.NHITS + ev.LightGBM) / 2
    ev["Blend3"] = (ev.NHITS + ev.LightGBM + ev["DeepAR-median"]) / 3

    cutoffs = sorted(ev.cutoff.unique())
    print("origins:", [pd.Timestamp(c).strftime("%Y-%m") for c in cutoffs])

    # ---------------- Part A: all windows, unfitted blends
    models = ["Naive", "LightGBM", "NHITS", "DeepAR-median", "Blend2", "Blend3"]
    resA = point_metrics(ev, models)
    print("\nPART A - all windows, point accuracy (MAE on log1p wallets)\n", resA.round(4).to_string())
    ageA = by_group(ev, models, "age_bucket")
    print("\nby dApp age at origin\n", ageA.round(3).to_string())
    boot = []
    for a, b in [("NHITS", "LightGBM"), ("Blend2", "NHITS"), ("Blend2", "LightGBM"), ("Blend3", "Blend2"), ("NHITS", "Naive")]:
        m, lo, hi = cluster_bootstrap(ev, a, b)
        boot.append({"a": a, "b": b, "mae_diff(a-b)": m, "ci_lo": lo, "ci_hi": hi, "significant": bool(lo > 0 or hi < 0)})
    boot = pd.DataFrame(boot)
    print("\nPaired MAE differences, cluster bootstrap by dApp (negative = first model better)\n", boot.round(4).to_string(index=False))

    # ---------------- Part B: fit -> eval
    if len(cutoffs) >= 5:
        fit_c, eval_c = cutoffs[:3], cutoffs[-2:]
        assert fit_c[-1] + pd.DateOffset(months=h) <= eval_c[0], "fit targets must not extend past the first eval origin"
        fit, test = ev[ev.cutoff.isin(fit_c)], ev[ev.cutoff.isin(eval_c)].copy()
        print(f"\nPART B - fit origins {[pd.Timestamp(c).strftime('%Y-%m') for c in fit_c]} -> eval origins {[pd.Timestamp(c).strftime('%Y-%m') for c in eval_c]}")

        weights = {}
        for bkt, f in fit.groupby("age_bucket", observed=True):
            grid = np.linspace(0, 1, 11)
            maes = [np.mean(np.abs(f.y - (w * f.NHITS + (1 - w) * f.LightGBM).clip(lower=0))) for w in grid]
            weights[bkt] = float(grid[int(np.argmin(maes))])
        test["BlendAge"] = [w * n + (1 - w) * l for w, n, l in zip(test.age_bucket.map(weights).astype(float), test.NHITS, test.LightGBM)]
        print("N-HiTS weight by age bucket (rest LightGBM):", weights)
        modelsB = ["Naive", "LightGBM", "NHITS", "DeepAR-median", "Blend2", "Blend3", "BlendAge"]
        resB = point_metrics(test, modelsB)
        print("\neval-window point accuracy\n", resB.round(4).to_string())
        print("\nby age\n", by_group(test, modelsB, "age_bucket").round(3).to_string())

        rows = []
        raw = interval_metrics(test)
        rows.append({"method": "raw", **raw})
        for name, pooled in [("conformal_pooled", True), ("conformal_per_horizon", False)]:
            cal, qs = calibrate_by_horizon(fit, test, pooled=pooled)
            m = interval_metrics(cal.assign(**{"DeepAR-lo-80": cal["DeepAR-lo-80-cal"], "DeepAR-hi-80": cal["DeepAR-hi-80-cal"]}))
            rows.append({"method": name, **m})
            if not pooled:
                cal_h = cal
                q_h = qs
        ivB = pd.DataFrame(rows).set_index("method")
        print("\nDeepAR 80% interval on eval windows\n", ivB.round(3).to_string())
        cov_h = {}
        for name, c in [("raw", test), ("pooled", calibrate_by_horizon(fit, test, pooled=True)[0]), ("per_horizon", cal_h)]:
            lo = c["DeepAR-lo-80-cal"] if "DeepAR-lo-80-cal" in c else c["DeepAR-lo-80"]
            hi = c["DeepAR-hi-80-cal"] if "DeepAR-hi-80-cal" in c else c["DeepAR-hi-80"]
            ok = (c.y >= lo.clip(lower=0)) & (c.y <= hi)
            cov_h[name] = ok.groupby(c.horizon_step).mean()
        cov_h = pd.DataFrame(cov_h)
        print("\ncoverage by horizon step\n", cov_h.round(3).to_string())
        print("per-horizon q:", {k: round(v, 3) for k, v in q_h.items()})

    if not smoke:
        out = cfg["results_dir"]
        ev.to_parquet(f"{out}/forecast_ext_predictions.parquet")
        resA.to_csv(f"{out}/forecast_ext_metrics_all_windows.csv")
        ageA.to_csv(f"{out}/forecast_ext_metrics_by_age.csv")
        boot.to_csv(f"{out}/forecast_ext_bootstrap.csv", index=False)
        if len(cutoffs) >= 5:
            resB.to_csv(f"{out}/forecast_ext_blend_eval.csv")
            pd.Series(weights, name="nhits_weight").to_csv(f"{out}/forecast_ext_blend_weights.csv")
            ivB.to_csv(f"{out}/forecast_ext_interval_metrics.csv")
            cov_h.to_csv(f"{out}/forecast_ext_coverage_by_horizon.csv")
        print(f"\nsaved to {out}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    main(a.smoke)
