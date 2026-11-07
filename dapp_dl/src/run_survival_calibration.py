"""Calibration of DeepSurv and Cox PH survival predictions, before and after recalibration.

    python -m src.run_survival_calibration

For every split: models are fit on the training part only (DeepSurv early-stops on the validation
part), the recalibrator is fitted on the validation part, and everything is scored on the held-out
test part. Reported per (event, feature set, model, time point), averaged over splits:
  brier_raw / brier_cal   IPCW Brier score (lower is better)
  ici_raw / ici_cal       binned integrated calibration index = mean |predicted - observed| risk
  citl_raw / citl_cal     calibration in the large = mean predicted risk - Kaplan-Meier observed risk
  slope                   fitted recalibration slope on the cloglog scale (1 = already calibrated)
"""
import warnings

import numpy as np
import pandas as pd
import yaml

from src.data.build_survival_table import assemble, build_survival_tables
from src.data.splits import stratified_event_split
from src.evaluation.survival_calibration import (
    CloglogRecalibrator, brier_at, calibration_summary, calibration_table, surv_at,
)
from src.models.deepsurv import DeepSurv
from src.models.survival_baselines import CoxBaseline
from src.run_survival import RUNS

warnings.filterwarnings("ignore")


def main():
    cfg = yaml.safe_load(open("configs/data.yaml"))
    ds_cfg = yaml.safe_load(open("configs/deepsurv.yaml"))
    s = cfg["survival"]
    events, tables = build_survival_tables(cfg["raw_dir"], s["min_peak_wallets"], s["decline_fraction"], s["smooth_window"])

    rows, bins = [], []
    for event, fset in RUNS:
        Xdf, dur, evt = assemble(events, tables, event, fset)
        X, d, e = Xdf.to_numpy(), dur.to_numpy(), evt.to_numpy()
        times = [float(t) for t in np.unique(np.round(np.quantile(d[e == 1], ds_cfg["time_quantiles"])))]
        for seed in s["seeds"]:
            tr, va, te = stratified_event_split(e, seed, s["test_frac"], s["val_frac"])
            models = {
                "DeepSurv": DeepSurv(ds_cfg, seed).fit(X[tr], d[tr], e[tr], X[va], d[va], e[va]),
                "CoxPH": CoxBaseline().fit(X[tr], d[tr], e[tr]),
            }
            for name, m in models.items():
                S_va_df, S_te_df = m.survival(X[va]), m.survival(X[te])
                for t in times:
                    S_va, S_te = surv_at(S_va_df, t), surv_at(S_te_df, t)
                    rec = CloglogRecalibrator().fit(S_va, d[va], e[va], t)
                    S_cal = rec.transform(S_te)
                    out = {"event": event, "features": fset, "model": name, "seed": seed, "t": t, "slope": rec.beta, "recal_fitted": rec.ok}
                    for tag, S in [("raw", S_te), ("cal", S_cal)]:
                        summ, tab = calibration_summary(1 - S, d[te], e[te], t)
                        out[f"brier_{tag}"] = brier_at(S, d[te], e[te], t)
                        out[f"ici_{tag}"] = summ["ici"]
                        out[f"citl_{tag}"] = summ["citl"]
                        bins.append(tab.assign(event=event, features=fset, model=name, seed=seed, t=t, version=tag))
                    rows.append(out)
        print(f"done {event}/{fset} (times {times})", flush=True)

    res = pd.DataFrame(rows)
    res.to_csv(f"{cfg['results_dir']}/survival_calibration_by_seed.csv", index=False)
    pd.concat(bins).to_csv(f"{cfg['results_dir']}/survival_calibration_bins.csv", index=False)
    keys = ["event", "features", "model", "t"]
    metrics = ["brier_raw", "brier_cal", "ici_raw", "ici_cal", "citl_raw", "citl_cal", "slope"]
    summ = res.groupby(keys)[metrics].mean()
    summ["brier_improved_in_seeds"] = res.assign(b=res.brier_cal < res.brier_raw).groupby(keys).b.mean()
    summ["ici_improved_in_seeds"] = res.assign(b=res.ici_cal < res.ici_raw).groupby(keys).b.mean()
    summ.to_csv(f"{cfg['results_dir']}/survival_calibration.csv")
    pd.set_option("display.width", 220)
    print("\nCalibration, mean over splits (t in months)")
    print(summ.round(3).to_string())
    over = res.groupby(["event", "features", "model"])[["brier_raw", "brier_cal", "ici_raw", "ici_cal"]].mean()
    print("\nAveraged over time points")
    print(over.round(4).to_string())


if __name__ == "__main__":
    main()
