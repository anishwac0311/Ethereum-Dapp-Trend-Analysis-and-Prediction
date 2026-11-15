"""Does early size predict success equally well in every market period?

Size alone is the Szabo-Huberman baseline: a logistic regression on log_last_wallets. Fitted separately on the DApps
launched in each period (before Terra, Terra to Dencun, after Dencun), its slope b says how strongly early size relates
to success there. This is descriptive: it compares periods, it does not predict one from another.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import roc_auc_score

from config import EVENTS, TARGET, record

SIZE = "log_last_wallets"   # log(1 + active wallets in the last window month)
N_BOOT = 1000
SEED = 42


def slope(x: np.ndarray, y: np.ndarray) -> float:
    return sm.Logit(y, sm.add_constant(x)).fit(disp=0).params[1]


def periods(df: pd.DataFrame) -> dict[str, pd.Series]:
    terra, dencun = EVENTS["Terra"], EVENTS["Dencun"]
    launch = df["launch_month"]
    return {"Before Terra (2020-01 to 2022-04)": launch < terra,
            "Terra to Dencun (2022-05 to 2024-02)": (launch >= terra) & (launch < dencun),
            "After Dencun (2024-03 to 2024-12)": launch >= dencun}


def run(df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    for name, mask in periods(df).items():
        d = df[mask]
        x, y = d[SIZE].to_numpy(float), d[TARGET].to_numpy(int)
        boots = []
        for _ in range(N_BOOT):
            i = rng.integers(0, len(y), len(y))
            if y[i].min() == y[i].max():
                continue
            try:
                boots.append(slope(x[i], y[i]))
            except Exception:   # perfect separation in a resample
                continue
        b = slope(x, y)
        top = x >= np.quantile(x, .8)
        rows.append({"period": name, "n_dapps": len(y), "n_successful": int(y.sum()), "base_rate": y.mean(),
                     "slope_b": b, "slope_lo": np.quantile(boots, .025), "slope_hi": np.quantile(boots, .975),
                     # Odds of success when last-month wallets are 10 times larger
                     "odds_ratio_10x": np.exp(b * np.log(10)),
                     "auc_size_only": roc_auc_score(y, x),
                     "success_rate_top20pct": y[top].mean(), "success_rate_rest": y[~top].mean()})
    return record(pd.DataFrame(rows), "size_effect_by_period")
