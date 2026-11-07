"""dapp_panel.csv -> long-format panel for N-HiTS / DeepAR (unique_id, ds, y, covariates).

Target y = log1p(active_wallets). Only dApps that reached `min_peak_wallets` and have at
least `min_series_len` months are kept (the rest are effectively never-adopted).

Leakage notes
- `tvl` and `n_contracts` in dapp_panel are one constant snapshot per dApp (taken at the end
  of the data), so TVL is excluded by default; n_contracts is kept as a weak static feature.
- Historical covariates are only available up to the forecast origin (hist_exog); only
  `months_since_launch` is a known-future covariate.
"""
import numpy as np
import pandas as pd

FUTR = ["months_since_launch"]
HIST = [
    "log_new_wallets",
    "log_gas_used",
    "log_tx_per_wallet",
    "retention_prev_month",
    "top10_wallet_share",
    "avg_n_protocols_in_tx",
]


def build_forecast_panel(raw_dir, min_peak_wallets=100, min_series_len=24):
    p = pd.read_csv(f"{raw_dir}/dapp_panel.csv", parse_dates=["month"])
    p = p.sort_values(["slug", "month"]).reset_index(drop=True)

    peak = p.groupby("slug").active_wallets.max()
    length = p.groupby("slug").size()
    keep = peak.index[(peak >= min_peak_wallets) & (length.reindex(peak.index) >= min_series_len)]
    p = p[p.slug.isin(keep)].copy()

    df = pd.DataFrame(
        {
            "unique_id": p.slug.astype(str),
            "ds": p.month,
            "y": np.log1p(p.active_wallets.clip(lower=0)),
            "months_since_launch": p.months_since_launch.astype(float),
            "log_new_wallets": np.log1p(p.new_wallets.clip(lower=0)),
            "log_gas_used": np.log1p(p.gas_used.clip(lower=0)),
            "log_tx_per_wallet": np.log1p(p.tx_per_wallet.fillna(0).clip(lower=0)),
            "retention_prev_month": p.retention_prev_month.fillna(0),
            "top10_wallet_share": p.top10_wallet_share.fillna(0),
            "avg_n_protocols_in_tx": p.avg_n_protocols_in_tx.fillna(0),
        }
    )
    df = df.replace([np.inf, -np.inf], 0).reset_index(drop=True)

    st = p.groupby("slug").first()[["category_group", "has_token", "n_contracts"]]
    static = pd.get_dummies(st.category_group, prefix="cat").astype(float)
    static["has_token"] = st.has_token.astype(float)
    static["log_n_contracts"] = np.log1p(st.n_contracts.astype(float))
    static.index = static.index.astype(str)
    static = static.rename_axis("unique_id").reset_index()
    return df, static


def static_cols(static):
    return [c for c in static.columns if c != "unique_id"]


if __name__ == "__main__":
    import sys
    import yaml

    cfg = yaml.safe_load(open("configs/data.yaml"))
    df, static = build_forecast_panel(cfg["raw_dir"], **{k: cfg["forecast"][k] for k in ("min_peak_wallets", "min_series_len")})
    df.to_parquet(f"{cfg['processed_dir']}/forecast_panel.parquet")
    static.to_parquet(f"{cfg['processed_dir']}/forecast_static.parquet")
    print(f"panel: {len(df):,} rows, {df.unique_id.nunique()} dApps, {df.ds.min():%Y-%m} to {df.ds.max():%Y-%m}")
    print("static cols:", static_cols(static))
