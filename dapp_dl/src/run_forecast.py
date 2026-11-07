"""Run N-HiTS and DeepAR (plus baselines) with rolling-origin evaluation, several seeds.

    python -m src.run_forecast                         # default configs, seeds 1 2 3
    python -m src.run_forecast --tuned                 # configs/*_tuned.yaml (from src.tuning.search)
    python -m src.run_forecast --smoke                 # 40 training steps, for checking the pipeline

Outputs (results/, suffixed _default or _tuned):
  forecast_predictions, forecast_metrics (per seed and seed-ensemble), horizon / age tables,
  deepar_interval_metrics (raw vs conformal-calibrated, on the later window only).
"""
import argparse
import time
import warnings

import numpy as np
import pandas as pd
import yaml

from src.data.build_forecast_panel import build_forecast_panel
from src.evaluation.calibration import calibrate_deepar
from src.evaluation.forecast_metrics import by_group, interval_metrics, point_metrics
from src.models.baselines import lightgbm_forecast, naive_forecast
from src.models.deepar import run_deepar
from src.models.nhits import run_nhits

warnings.filterwarnings("ignore")


def main(smoke=False, tuned=False, seeds=(1, 2, 3)):
    cfg = yaml.safe_load(open("configs/data.yaml"))
    fc = cfg["forecast"]
    suffix = "tuned" if tuned else "default"
    nh_cfg = yaml.safe_load(open(f"configs/nhits{'_tuned' if tuned else ''}.yaml"))
    dp_cfg = yaml.safe_load(open(f"configs/deepar{'_tuned' if tuned else ''}.yaml"))
    if smoke:
        nh_cfg["max_steps"] = dp_cfg["max_steps"] = 40
        nh_cfg["val_check_steps"] = dp_cfg["val_check_steps"] = 20
        seeds = seeds[:1]

    h, nw = fc["horizon"], fc["n_windows"]
    df, static = build_forecast_panel(cfg["raw_dir"], fc["min_peak_wallets"], fc["min_series_len"])
    print(f"[{suffix}] {df.unique_id.nunique()} dApps, {len(df):,} rows; horizon={h}, windows={nw}, seeds={list(seeds)}")

    keys = ["unique_id", "ds", "cutoff"]
    ev = None
    for sd in seeds:
        t = time.time()
        nh = run_nhits(df, static, nh_cfg, h, nw, sd)
        dp = run_deepar(df, static, dp_cfg, h, nw, sd)
        part = nh[keys + ["y", "NHITS"]].merge(dp.drop(columns="y"), on=keys, how="inner")
        part = part.rename(columns={c: f"{c}_s{sd}" for c in part.columns if c.startswith(("NHITS", "DeepAR"))})
        ev = part if ev is None else ev.merge(part.drop(columns="y"), on=keys, how="inner")
        print(f"  seed {sd} done in {time.time() - t:.0f}s", flush=True)
    ev = ev.reset_index(drop=True)

    # seed ensemble (mean of seeds); per-seed columns are kept for the spread
    for base in ["NHITS", "DeepAR-median", "DeepAR-lo-80", "DeepAR-hi-80"]:
        ev[base] = ev[[f"{base}_s{sd}" for sd in seeds]].mean(axis=1)
    ev["Naive"] = naive_forecast(df, ev)
    ev["LightGBM"] = lightgbm_forecast(df, static, ev, h, seed=seeds[0])
    ev = ev.dropna(subset=["Naive", "LightGBM", "NHITS", "DeepAR-median"]).reset_index(drop=True)

    ev["horizon_step"] = (ev.ds.dt.year - ev.cutoff.dt.year) * 12 + (ev.ds.dt.month - ev.cutoff.dt.month)
    age = df.set_index(["unique_id", "ds"]).months_since_launch
    ev["age_at_cutoff"] = age.reindex(pd.MultiIndex.from_arrays([ev.unique_id, ev.cutoff])).to_numpy()
    ev["age_bucket"] = pd.cut(ev.age_at_cutoff, [-1, 11, 35, 1e9], labels=["<12m", "12-35m", "36m+"])

    # ---- point accuracy: ensemble, plus per-seed mean/std for the neural models
    models = ["Naive", "LightGBM", "NHITS", "DeepAR-median"]
    res = point_metrics(ev, models)
    seed_mae = {m: [point_metrics(ev.assign(**{m: ev[f"{m}_s{sd}"]}), [m]).loc[m, "MAE_log"] for sd in seeds] for m in ["NHITS", "DeepAR-median"]}
    res["MAE_seed_mean"] = [np.mean(seed_mae[m]) if m in seed_mae else np.nan for m in res.index]
    res["MAE_seed_std"] = [np.std(seed_mae[m]) if m in seed_mae else np.nan for m in res.index]
    print("\nPoint accuracy (log1p wallets; lower is better). NHITS / DeepAR-median rows are seed ensembles.")
    print(res.round(4).to_string())
    h_tab, a_tab = by_group(ev, models, "horizon_step"), by_group(ev, models, "age_bucket")
    print("\nMAE_log by horizon step\n", h_tab.round(3).to_string())
    print("\nMAE_log by dApp age at forecast origin\n", a_tab.round(3).to_string())

    # ---- DeepAR intervals: raw vs conformal, scored on the later window only
    later, q = calibrate_deepar(ev, "DeepAR", 80)
    single = np.mean([interval_metrics(later.assign(**{"DeepAR-lo-80": later[f"DeepAR-lo-80_s{sd}"], "DeepAR-hi-80": later[f"DeepAR-hi-80_s{sd}"], "DeepAR-median": later[f"DeepAR-median_s{sd}"]}))["coverage"] for sd in seeds])
    raw = interval_metrics(later)
    cal = interval_metrics(later.assign(**{"DeepAR-lo-80": later["DeepAR-lo-80-cal"], "DeepAR-hi-80": later["DeepAR-hi-80-cal"]}))
    iv = pd.DataFrame({"single_seed_mean_coverage": {"coverage": single}, "ensemble_raw": raw, "ensemble_conformal": cal}).T
    iv["conformal_q"] = [np.nan, np.nan, q]
    print(f"\nDeepAR 80% interval on the later window (cutoff {later.cutoff.iloc[0]:%Y-%m}), conformal q={q:.3f}")
    print(iv.round(3).to_string())

    if not smoke:
        out = cfg["results_dir"]
        ev.to_parquet(f"{out}/forecast_predictions_{suffix}.parquet")
        res.to_csv(f"{out}/forecast_metrics_{suffix}.csv")
        h_tab.to_csv(f"{out}/forecast_metrics_by_horizon_{suffix}.csv")
        a_tab.to_csv(f"{out}/forecast_metrics_by_age_{suffix}.csv")
        iv.to_csv(f"{out}/deepar_interval_metrics_{suffix}.csv")
        print(f"\nsaved to {out}/ (suffix _{suffix})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--tuned", action="store_true")
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    a = ap.parse_args()
    main(a.smoke, a.tuned, tuple(a.seeds))
