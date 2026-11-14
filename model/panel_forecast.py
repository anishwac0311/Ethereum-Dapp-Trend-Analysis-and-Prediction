"""Global panel forecaster: one model trained on every DApp-month, not one row per DApp.

Per-DApp ARIMA/GARCH can't be fit on 1-6 early points. Instead we pool all
(slug, origin age a) pairs and learn a nonlinear AR model:

    log1p(mean wallets at ages a+h_lo .. a+h_hi)  ~  lags of log wallets at a, a-1, a-2,
                                                     age, max-to-date, shape, quality,
                                                     market state at the origin month

with direct horizons chosen so that origin a = k-1 lands exactly on the label months
10-12 (k=1: 10-12 ahead, k=3: 8-10, k=6: 5-7). Quantile regression gives a full
predictive distribution, so P(success) is available for ANY wallet cutoff and
relative rule: P(Y >= log1p(max(T, rho * window_max))).

Leakage rules: features at origin a only use months <= a; the forecaster is fitted
only on rows of training-fold DApps; scored DApps are evaluated only at origin k-1.

  python model/panel_forecast.py --k 3      # sanity report on the expanding folds
"""
from __future__ import annotations

import argparse
from typing import Iterable, Optional

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression

from common import (
    MODEL,
    annotate_lifecycle,
    load_category_month,
    load_lifecycle,
    load_panel,
    load_static,
    safe_log1p,
    savetable,
)

MAX_ORIGIN_AGE = 18
QUANTILES = np.array([0.05, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 0.95])
NEWS_DIR = MODEL / "news_sentiment" / "data"

FC_NUM = [
    "lw0", "lw1", "lw2", "age", "lmax", "last_to_max", "slope3", "lcum",
    "tx_per_wallet", "retention", "new_share", "top10_share", "cat_share", "eco_share",
    "cat_growth_3m", "eco_growth_3m", "eth_ret_1m", "eth_ret_3m", "eth_vol_1m",
    "news_sent_eth", "news_n_eth",
]
FC_CAT = ["category_group"]
AR_COLS = ["lw0", "lw1", "lw2", "age", "lmax"]


def horizon(k: int) -> tuple[int, int]:
    """Offsets from origin so that origin k-1 maps to label months 10..12."""
    return 11 - k, 13 - k


def _market_frames(cat_month: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Monthly market state, all backward-looking."""
    frames = []
    if cat_month is not None and len(cat_month):
        cm = cat_month.copy()
        cm["month"] = pd.to_datetime(cm["month"]).dt.to_period("M").dt.to_timestamp()
        eco = cm.groupby("month")["active_wallets"].sum().sort_index()
        eco_g = eco.pct_change(3, fill_method=None).rename("eco_growth_3m").reset_index()
        frames.append(("cat", cm[["month", "category_group", "growth_3m"]]
                       .rename(columns={"growth_3m": "cat_growth_3m"})))
        frames.append(("eco", eco_g))
    eth_p = NEWS_DIR / "eth_monthly.csv"
    if eth_p.exists():
        eth = pd.read_csv(eth_p)
        eth["month"] = pd.to_datetime(eth["month"]).dt.to_period("M").dt.to_timestamp()
        eth = eth.sort_values("month")
        eth["eth_ret_3m"] = eth["eth_close"].pct_change(3, fill_method=None)
        frames.append(("eth", eth[["month", "eth_ret_1m", "eth_ret_3m", "eth_vol_1m"]]))
    news_p = NEWS_DIR / "news_monthly.csv"
    if news_p.exists():
        nw = pd.read_csv(news_p)
        nw["month"] = pd.to_datetime(nw["month"]).dt.to_period("M").dt.to_timestamp()
        frames.append(("news", nw[["month", "sent_eth", "n_eth"]]
                       .rename(columns={"sent_eth": "news_sent_eth", "n_eth": "news_n_eth"})))
    return frames


def build_rows(
    k: int,
    panel: Optional[pd.DataFrame] = None,
    life: Optional[pd.DataFrame] = None,
    cat_month: Optional[pd.DataFrame] = None,
    max_age: int = MAX_ORIGIN_AGE,
) -> pd.DataFrame:
    """One row per (slug, origin age). Target is NaN when its window runs past the panel."""
    if panel is None:
        panel = load_panel()
    if life is None:
        life = annotate_lifecycle(load_lifecycle(), load_static())
    if cat_month is None:
        try:
            cat_month = load_category_month()
        except Exception:
            cat_month = None
    h_lo, h_hi = horizon(k)
    meta = life.drop_duplicates("slug").set_index("slug")

    out = []
    for slug, g in panel.groupby("slug"):
        if slug not in meta.index or bool(meta.loc[slug].get("left_censored", False)):
            continue
        g = g[g["months_since_launch"] >= 0].sort_values("months_since_launch")
        if g.empty:
            continue
        ages = g["months_since_launch"].astype(int).values
        if ages[0] != 0:
            continue
        aw = g["active_wallets"].astype(float).fillna(0).values
        lw = safe_log1p(aw)
        n = len(aw)
        cummax = np.maximum.accumulate(aw)

        def col(name):
            return g[name].astype(float).values if name in g.columns else np.full(n, np.nan)

        tx = col("tx_count")
        new = col("new_wallets")
        ret = col("retention_prev_month")
        top10 = col("top10_wallet_share")
        cat_sh = col("share_of_category_active_wallets")
        eco_sh = col("share_of_ecosystem_active_wallets")
        cum = col("cum_wallets")
        months = pd.to_datetime(g["month"]).dt.to_period("M").dt.to_timestamp().values

        for a in range(min(n, max_age + 1)):
            lo, hi = a + h_lo, a + h_hi
            target = float(np.log1p(aw[lo:hi + 1].mean())) if hi < n else np.nan
            s = lw[max(0, a - 2):a + 1]
            slope = float(np.polyfit(np.arange(len(s)), s, 1)[0]) if len(s) >= 2 else np.nan
            out.append({
                "slug": slug,
                "age": a,
                "month": months[a],
                "category_group": meta.loc[slug].get("category_group"),
                "lw0": lw[a],
                "lw1": lw[a - 1] if a >= 1 else np.nan,
                "lw2": lw[a - 2] if a >= 2 else np.nan,
                "lmax": float(np.log1p(cummax[a])),
                "max_to_date": float(cummax[a]),
                "last_to_max": aw[a] / cummax[a] if cummax[a] > 0 else np.nan,
                "slope3": slope,
                "lcum": float(np.log1p(cum[a])) if np.isfinite(cum[a]) else np.nan,
                "tx_per_wallet": tx[a] / aw[a] if aw[a] > 0 else np.nan,
                "retention": ret[a],
                "new_share": new[a] / aw[a] if aw[a] > 0 else np.nan,
                "top10_share": top10[a],
                "cat_share": cat_sh[a],
                "eco_share": eco_sh[a],
                "target": target,
            })
    rows = pd.DataFrame(out)
    rows["month"] = pd.to_datetime(rows["month"])
    for name, f in _market_frames(cat_month):
        keys = ["month", "category_group"] if name == "cat" else ["month"]
        rows = rows.merge(f, on=keys, how="left")
    for c in FC_NUM:
        if c not in rows.columns:
            rows[c] = np.nan
    rows["category_group"] = rows["category_group"].astype("category")
    return rows


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
def _weights(rows: pd.DataFrame) -> np.ndarray:
    """Each DApp contributes total weight 1, so long-lived apps don't dominate."""
    return (1.0 / rows.groupby("slug")["slug"].transform("size")).values


def _X(rows: pd.DataFrame) -> pd.DataFrame:
    return rows[FC_NUM + FC_CAT]


class QuantileForecaster:
    """Gradient-boosted quantile regression -> monotone predictive CDF."""

    def __init__(self, quantiles: Iterable[float] = QUANTILES, max_iter: int = 300):
        self.quantiles = np.asarray(list(quantiles))
        self.max_iter = max_iter
        self.models = []

    def fit(self, rows: pd.DataFrame) -> "QuantileForecaster":
        tr = rows[rows["target"].notna()]
        w = _weights(tr)
        self.models = []
        for q in self.quantiles:
            m = HistGradientBoostingRegressor(
                loss="quantile", quantile=float(q), max_depth=4, learning_rate=0.05,
                max_iter=self.max_iter, min_samples_leaf=40, l2_regularization=1.0,
                categorical_features="from_dtype", random_state=42,
            )
            m.fit(_X(tr), tr["target"].values, sample_weight=w)
            self.models.append(m)
        return self

    def predict_quantiles(self, rows: pd.DataFrame) -> np.ndarray:
        Q = np.column_stack([m.predict(_X(rows)) for m in self.models])
        return np.sort(Q, axis=1)  # fix quantile crossing


class PanelAR:
    """Pooled linear AR on log wallets + age, Gaussian residuals: the ARIMA-style baseline."""

    def fit(self, rows: pd.DataFrame) -> "PanelAR":
        tr = rows[rows["target"].notna()]
        X = self._x(tr)
        w = _weights(tr)
        self.lr = LinearRegression().fit(X, tr["target"].values, sample_weight=w)
        resid = tr["target"].values - self.lr.predict(X)
        self.sigma = float(np.sqrt(np.average(resid ** 2, weights=w)))
        return self

    @staticmethod
    def _x(rows: pd.DataFrame) -> np.ndarray:
        x = rows[AR_COLS].copy()
        x["lw1"] = x["lw1"].fillna(x["lw0"])
        x["lw2"] = x["lw2"].fillna(x["lw1"])
        x["log_age"] = np.log1p(x["age"])
        return x.values

    def predict_mean(self, rows: pd.DataFrame) -> np.ndarray:
        return self.lr.predict(self._x(rows))


def success_threshold(window_max: np.ndarray, abs_wallets: float, rel: float) -> np.ndarray:
    """log1p threshold that reproduces the (abs, rel) sustained rule on mean m10-12."""
    return np.log1p(np.maximum(abs_wallets, rel * np.asarray(window_max, dtype=float)))


def forecast_dapps(rows: pd.DataFrame, train_slugs: Iterable[str], score_slugs: Iterable[str],
                   k: int, kind: str = "gbm_q") -> pd.DataFrame:
    """Fit on train slugs' rows, return per-DApp predictive info at origin k-1.

    Output columns: slug, fc_median, fc_iqr, window_max, and either quantiles
    (q_0.05 ...) for gbm_q or fc_mu / fc_sigma for the AR baseline.
    """
    train_slugs, score_slugs = set(train_slugs), set(score_slugs)
    assert not (train_slugs & score_slugs), "forecaster train/score DApps overlap"
    tr = rows[rows["slug"].isin(train_slugs)]
    sc = rows[rows["slug"].isin(score_slugs) & (rows["age"] == k - 1)].copy()
    out = pd.DataFrame({"slug": sc["slug"].values, "window_max": sc["max_to_date"].values})
    if kind == "ar":
        m = PanelAR().fit(tr)
        mu = m.predict_mean(sc)
        out["fc_mu"], out["fc_sigma"] = mu, m.sigma
        out["fc_median"] = mu
        out["fc_iqr"] = 2 * 0.674 * m.sigma
        out.attrs["model"] = m
        return out
    m = QuantileForecaster().fit(tr)
    Q = m.predict_quantiles(sc)
    for j, q in enumerate(m.quantiles):
        out[f"q_{q:.2f}"] = Q[:, j]
    taus = list(np.round(m.quantiles, 2))
    out["fc_median"] = Q[:, taus.index(0.5)]
    out["fc_iqr"] = Q[:, taus.index(0.75)] - Q[:, taus.index(0.25)]
    out.attrs["model"] = m
    return out


def prob_from_forecast(fc: pd.DataFrame, abs_wallets: float, rel: float) -> np.ndarray:
    """P(success at (abs, rel)) for each row of forecast_dapps output (tails capped at
    half the outer quantile mass)."""
    thr = success_threshold(fc["window_max"].values, abs_wallets, rel)
    if "fc_mu" in fc.columns:
        return 1.0 - norm.cdf((thr - fc["fc_mu"].values) / fc["fc_sigma"].values)
    qcols = [c for c in fc.columns if c.startswith("q_")]
    Q = fc[qcols].values
    taus = np.array([float(c[2:]) for c in qcols])
    lo, hi = taus[0] / 2, 1 - (1 - taus[-1]) / 2
    cdf = np.array([np.interp(t, q, taus, left=lo, right=hi) for q, t in zip(Q, thr)])
    return 1.0 - cdf


def leakage_check(k: int, n_slugs: int = 25, seed: int = 0) -> None:
    """Origin-(k-1) features must not change when post-window months are deleted."""
    panel = load_panel()
    life = annotate_lifecycle(load_lifecycle(), load_static())
    full = build_rows(k, panel, life)
    rng = np.random.default_rng(seed)
    slugs = rng.choice(full["slug"].unique(), size=n_slugs, replace=False)
    sub = panel[panel["slug"].isin(slugs)]
    trunc = sub[sub["months_since_launch"] < k]
    a = full[full["slug"].isin(slugs) & (full["age"] == k - 1)].set_index("slug")[FC_NUM]
    b = build_rows(k, trunc, life)
    b = b[b["age"] == k - 1].set_index("slug")[FC_NUM]
    a, b = a.loc[b.index], b
    same = np.isclose(a.values.astype(float), b.values.astype(float), equal_nan=True).all()
    assert same, "forecaster origin features change when future months are removed"
    print(f"  leakage check k={k}: origin features identical on {len(b)} truncated DApps")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, nargs="+", default=[3])
    args = parser.parse_args()
    from robust_eval import expanding_folds, load_dataset  # local import: avoid cycle

    print("== panel_forecast ==")
    panel = load_panel()
    life = annotate_lifecycle(load_lifecycle(), load_static())
    report = []
    for k in args.k:
        leakage_check(k)
        rows = build_rows(k, panel, life)
        n_tr = int(rows["target"].notna().sum())
        print(f"  k={k}: {len(rows):,} origin rows, {n_tr:,} with targets, "
              f"{rows['slug'].nunique()} DApps (vs one row per DApp before)")
        ds = load_dataset(k)
        for fold_name, tr, va in expanding_folds(ds):
            fc = forecast_dapps(rows, tr["slug"], va["slug"], k)
            j = va.merge(fc, on="slug", how="inner")
            y = j["y_log_wallets_12"].values
            naive = np.log1p(j["last_wallets"].values)
            report.append({
                "k": k, "fold": fold_name, "n": len(j),
                "mae_forecast": float(np.mean(np.abs(j["fc_median"].values - y))),
                "mae_last_value": float(np.mean(np.abs(naive - y))),
                "coverage_50": float(np.mean((y >= j["q_0.25"]) & (y <= j["q_0.75"]))),
                "coverage_90": float(np.mean((y >= j["q_0.05"]) & (y <= j["q_0.95"]))),
            })
            print(f"    {fold_name}: n={len(j)} MAE(log) forecast={report[-1]['mae_forecast']:.3f} "
                  f"last-value={report[-1]['mae_last_value']:.3f} "
                  f"cover50={report[-1]['coverage_50']:.2f} cover90={report[-1]['coverage_90']:.2f}")
    savetable(pd.DataFrame(report), "panel_forecast_report.csv")
    print("== panel_forecast done ==")


if __name__ == "__main__":
    main()
