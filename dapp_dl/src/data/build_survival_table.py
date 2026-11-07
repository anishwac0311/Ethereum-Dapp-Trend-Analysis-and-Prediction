"""dapp_lifecycle.csv + dapp_panel.csv -> (duration, event, features) tables for DeepSurv.

Three event definitions (all durations in months, shifted by +1 so every duration is > 0):

  decline   clock starts at the dApp's peak month. Event = first later month in which monthly
            active wallets fall below `decline_fraction` * peak. Censored at the last observed
            month. Only dApps with peak_wallets >= min_peak_wallets.      (Q2: sustained vs flash)
  reach_1k  clock starts at launch. Event = cumulative unique wallets reach 1,000
            (== lifecycle.months_to_1k). Censored at the last observed month.        (Q4)
  reach_10k same with 10,000.                                                          (Q4)

Feature sets
  static  known at launch: category_group, has_token, log n_contracts, launch_year
  early   static + early_* columns (the first ~3 months of life). These can overlap the
          outcome window for dApps that peak or reach a threshold inside that window, so
          treat 'early' results on reach_* events as optimistic.

tvl is a single end-of-data snapshot, so it is deliberately not used.
"""
import numpy as np
import pandas as pd

EARLY = [
    "early_retention",
    "early_new_wallet_share",
    "early_tx_per_wallet",
    "early_gas_per_tx",
    "early_whale_share",
    "early_prior_app_share",
]


def _mdiff(a, b):
    return (a.dt.year - b.dt.year) * 12 + (a.dt.month - b.dt.month)


def build_survival_tables(raw_dir, min_peak_wallets=100, decline_fraction=0.5, smooth_window=1):
    l = pd.read_csv(f"{raw_dir}/dapp_lifecycle.csv", parse_dates=["launch_month", "peak_month"]).set_index("slug")
    p = pd.read_csv(f"{raw_dir}/dapp_panel.csv", parse_dates=["month"]).sort_values(["slug", "month"])
    last_msl = p.groupby("slug").months_since_launch.max().reindex(l.index)

    # ---- features
    feats = pd.DataFrame(index=l.index)
    feats["has_token"] = l.has_token.astype(float)
    feats["log_n_contracts"] = np.log1p(l.n_contracts.astype(float))
    feats["launch_year"] = l.launch_year.astype(float)
    cat = pd.get_dummies(l.category_group, prefix="cat").astype(float)
    static = pd.concat([feats, cat], axis=1)
    early = l[EARLY].copy()
    early_miss = early.isna().any(axis=1).astype(float).rename("early_missing")
    early["early_log_gas_per_tx"] = np.log1p(early.pop("early_gas_per_tx"))
    early["early_log_tx_per_wallet"] = np.log1p(early.pop("early_tx_per_wallet"))

    tables = {}
    tables["static"] = static
    tables["early"] = pd.concat([static, early, early_miss], axis=1)

    # ---- events
    ev = {}

    # decline: from peak month
    # `smooth_window` > 1 uses a trailing rolling mean of active wallets, so one noisy month
    # cannot trigger the event; peak and threshold are then taken on the smoothed series.
    p["lvl"] = p.groupby("slug").active_wallets.transform(lambda s: s.rolling(smooth_window, min_periods=1).mean())
    lv = p.loc[p.groupby("slug").lvl.idxmax()].set_index("slug")
    pk = lv.lvl.reindex(l.index)
    peak_month = lv.month.reindex(l.index)
    p = p.merge(pd.DataFrame({"peak_month_s": peak_month, "peak_level": pk}), left_on="slug", right_index=True)
    after = p[(p.month > p.peak_month_s) & (p.lvl < decline_fraction * p.peak_level)]
    first_drop = after.groupby("slug").month.min()
    dur = pd.Series(np.nan, index=l.index)
    evt = pd.Series(0, index=l.index)
    drop_m = _mdiff(first_drop, peak_month.reindex(first_drop.index))
    dur.loc[drop_m.index] = drop_m
    evt.loc[drop_m.index] = 1
    last_month = p.groupby("slug").month.max().reindex(l.index)
    cens = _mdiff(last_month, peak_month)
    dur = dur.fillna(cens)
    d = pd.DataFrame({"duration": dur + 1, "event": evt})
    # drop dApps never adopted, and censored dApps that peaked in the final month (no follow-up)
    d = d[(pk >= min_peak_wallets) & ((d.event == 1) | (d.duration > 1))]
    ev["decline"] = d

    # reach thresholds: from launch
    for name, col in [("reach_1k", "months_to_1k"), ("reach_10k", "months_to_10k")]:
        e = l[col].notna().astype(int)
        du = l[col].fillna(last_msl)
        ev[name] = pd.DataFrame({"duration": du + 1, "event": e})

    out = {}
    for name, d in ev.items():
        out[name] = d
    return out, tables


def assemble(events, tables, name, feature_set):
    d = events[name]
    X = tables[feature_set].reindex(d.index)
    # median-impute remaining NaNs
    X = X.fillna(X.median(numeric_only=True)).fillna(0.0)
    return X.astype("float32"), d.duration.astype("float32"), d.event.astype("int64")


if __name__ == "__main__":
    import yaml

    cfg = yaml.safe_load(open("configs/data.yaml"))
    s = cfg["survival"]
    events, tables = build_survival_tables(cfg["raw_dir"], s["min_peak_wallets"], s["decline_fraction"], s.get("smooth_window", 1))
    for k, d in events.items():
        d.to_parquet(f"{cfg['processed_dir']}/survival_{k}.parquet")
        print(f"{k:10s} n={len(d):4d} events={int(d.event.sum()):4d} ({d.event.mean():.0%})  median duration={d.duration.median():.0f} months")
    for k, t in tables.items():
        t.to_parquet(f"{cfg['processed_dir']}/survival_features_{k}.parquet")
        print(f"features[{k}]: {t.shape[1]} cols")
