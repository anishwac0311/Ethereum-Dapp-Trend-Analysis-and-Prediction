"""Rolling-origin forecasting that keeps every dApp that exists at each origin.

neuralforecast's cross_validation needs every series to cover the earliest window, which would
silently drop young dApps from the evaluation. Here, for each origin (cutoff) a fresh model is
trained on data up to that origin only (last `h` months held out as validation), using the dApps
that have at least `min_obs` observed months by then, and predicts the next `h` months.

Output has the same columns as cross_validation (unique_id, ds, cutoff, y, <model columns>).
"""
import numpy as np
import pandas as pd
from neuralforecast import NeuralForecast


def rolling_forecast(build_model, df, static, cutoffs, h, min_obs=8):
    out = []
    for cutoff in cutoffs:
        cutoff = pd.Timestamp(cutoff)
        train = df[df.ds <= cutoff]
        n_obs = train.groupby("unique_id").size()
        ids = n_obs.index[n_obs >= min_obs]
        train = train[train.unique_id.isin(ids)]

        last = train.sort_values("ds").groupby("unique_id").tail(1).set_index("unique_id")
        # dApps must be observed at the cutoff itself (series are gap-free, so this holds
        # for every dApp that has not ended before it)
        last = last[last.ds == cutoff]
        train = train[train.unique_id.isin(last.index)]

        future = pd.DataFrame(
            [
                {"unique_id": uid, "ds": cutoff + pd.DateOffset(months=k), "months_since_launch": row.months_since_launch + k}
                for uid, row in last.iterrows()
                for k in range(1, h + 1)
            ]
        )
        nf = NeuralForecast(models=[build_model()], freq="MS")
        nf.fit(df=train.reset_index(drop=True), static_df=static[static.unique_id.isin(last.index)].reset_index(drop=True), val_size=h)
        pred = nf.predict(futr_df=future)
        if "unique_id" not in pred.columns:
            pred = pred.reset_index()
        pred["cutoff"] = cutoff
        out.append(pred)
    pred = pd.concat(out, ignore_index=True)
    truth = df[["unique_id", "ds", "y"]]
    return pred.merge(truth, on=["unique_id", "ds"], how="inner")  # only months that actually exist
