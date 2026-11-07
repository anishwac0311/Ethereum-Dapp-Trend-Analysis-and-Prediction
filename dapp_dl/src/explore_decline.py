"""Compare candidate definitions of the `decline` event with Cox PH and DeepSurv.

    python -m src.explore_decline

Predictability is not the same as usefulness, so the table also shows the event rate and the
spread of durations; a definition that nearly everyone meets within two months carries little
signal. The definition finally chosen goes in configs/data.yaml (survival.decline_*).
"""
import warnings

import numpy as np
import pandas as pd
import yaml

from src.data.build_survival_table import assemble, build_survival_tables
from src.data.splits import stratified_event_split
from src.evaluation.survival_metrics import c_index
from src.models.deepsurv import DeepSurv
from src.models.survival_baselines import CoxBaseline

warnings.filterwarnings("ignore")

VARIANTS = [
    {"name": "raw_50", "smooth_window": 1, "decline_fraction": 0.5},     # original
    {"name": "raw_25", "smooth_window": 1, "decline_fraction": 0.25},
    {"name": "smooth3_50", "smooth_window": 3, "decline_fraction": 0.5},
    {"name": "smooth3_25", "smooth_window": 3, "decline_fraction": 0.25},
    {"name": "smooth6_25", "smooth_window": 6, "decline_fraction": 0.25},
]


def main():
    cfg = yaml.safe_load(open("configs/data.yaml"))
    ds_cfg = yaml.safe_load(open("configs/deepsurv.yaml"))
    s = cfg["survival"]
    rows = []
    for v in VARIANTS:
        events, tables = build_survival_tables(cfg["raw_dir"], s["min_peak_wallets"], v["decline_fraction"], v["smooth_window"])
        d_ev = events["decline"]
        for fset in ["static", "early"]:
            X, dur, evt = assemble(events, tables, "decline", fset)
            X, d, e = X.to_numpy(), dur.to_numpy(), evt.to_numpy()
            res = {"cox": [], "deepsurv": []}
            for seed in s["seeds"]:
                tr, va, te = stratified_event_split(e, seed, s["test_frac"], s["val_frac"])
                ds = DeepSurv(ds_cfg, seed).fit(X[tr], d[tr], e[tr], X[va], d[va], e[va])
                trva = np.r_[tr, va]
                cox = CoxBaseline().fit(X[trva], d[trva], e[trva])
                res["cox"].append(c_index(d[te], e[te], cox.risk(X[te])))
                res["deepsurv"].append(c_index(d[te], e[te], ds.risk(X[te])))
            rows.append(
                {
                    "variant": v["name"], "features": fset, "n": len(d_ev), "event_rate": d_ev.event.mean(),
                    "dur_q25": d_ev.duration.quantile(0.25), "dur_median": d_ev.duration.median(), "dur_q75": d_ev.duration.quantile(0.75),
                    "cox_c": np.mean(res["cox"]), "cox_c_sd": np.std(res["cox"]),
                    "deepsurv_c": np.mean(res["deepsurv"]), "deepsurv_c_sd": np.std(res["deepsurv"]),
                }
            )
            print(rows[-1]["variant"], fset, "done", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(f"{cfg['results_dir']}/decline_definition_comparison.csv", index=False)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
