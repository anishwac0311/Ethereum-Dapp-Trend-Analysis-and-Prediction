"""Forecast baselines evaluated on exactly the windows produced by neuralforecast's cross_validation.

naive     repeat the last observed log1p(active_wallets) at the forecast origin
lightgbm  one global direct model: features at origin (12 lags + covariates + static) plus the
          horizon step k; trained only on (origin, k) pairs whose target is observed before the
          window's cutoff, so there is no look-ahead.
"""
import lightgbm as lgb
import numpy as np
import pandas as pd

from src.data.build_forecast_panel import FUTR, HIST, static_cols


def _mi(ds):
    return ds.dt.year * 12 + ds.dt.month


def naive_forecast(df, eval_frame):
    last = df.set_index(["unique_id", "ds"]).y
    idx = pd.MultiIndex.from_arrays([eval_frame.unique_id, eval_frame.cutoff])
    return last.reindex(idx).to_numpy()


def lightgbm_forecast(df, static, eval_frame, h, n_lags=12, seed=1):
    d = df.sort_values(["unique_id", "ds"]).reset_index(drop=True).merge(static, on="unique_id", how="left")
    d["mi"] = _mi(d.ds)
    g = d.groupby("unique_id")
    lag_cols = []
    for l in range(n_lags):
        d[f"lag{l}"] = g.y.shift(l)
        lag_cols.append(f"lag{l}")
    d["roll3"] = d[lag_cols[:3]].mean(axis=1)
    d["roll12"] = d[lag_cols].mean(axis=1)
    feat = lag_cols + ["roll3", "roll12"] + FUTR + HIST + static_cols(static)

    parts = []
    for k in range(1, h + 1):
        t = d[["unique_id", "mi"] + feat].copy()
        t["k"] = k
        t["target"] = g.y.shift(-k)
        parts.append(t)
    stacked = pd.concat(parts, ignore_index=True)
    X_cols = feat + ["k"]

    out = pd.Series(np.nan, index=eval_frame.index)
    for cutoff, ef in eval_frame.groupby("cutoff"):
        c_mi = cutoff.year * 12 + cutoff.month
        tr = stacked[(stacked.mi + stacked.k <= c_mi) & stacked.target.notna() & stacked.lag0.notna()]
        model = lgb.LGBMRegressor(
            n_estimators=300, learning_rate=0.05, num_leaves=31, min_child_samples=20,
            subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=seed, verbose=-1, n_jobs=2,
        )
        model.fit(tr[X_cols], tr.target)
        origin = stacked[stacked.mi == c_mi]
        ef_k = ((_mi(ef.ds) - c_mi)).rename("k")
        q = ef[["unique_id"]].assign(k=ef_k.values, row=ef.index)
        q = q.merge(origin.drop(columns="target"), on=["unique_id", "k"], how="left")
        out.loc[q.row.values] = model.predict(q[X_cols])
    return out.to_numpy()
