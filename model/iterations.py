"""Modelling iterations: every candidate on the same pooled out-of-fold protocol.

Each experiment returns P(success) for the validation DApps of one expanding fold
(train on parent-years < Y, validate on Y, Y = 2021..2024). Forecast-style models
also return one probability per (T, rho) cell of the success grid, so they are
scored on the whole range of success definitions, not only 1,000 wallets / 25%.

Iterations (see MODEL_REPORT.md, "Modelling journey"):
  0  reference: Szabo-Huberman, v1 HGB, panel AR, soft HGB + wallet, final blend v1
  1  better forecasting: pooled ridge on all origin features, heteroscedastic sigma,
     boosted mean, ages weighted around the origin
  2  predict a number: direct regression of log wallets at months 10-12 on DApp features
  3  classifier variety: random forest, extra trees, shallow / monotone HGB, spline GAM
  4  new features: users' on-chain history and economic value (user_history_features.py)
  5  ensembles: rank average, LOFO-stacked logistic meta-model

Metrics per model (pooled over 396 DApps at k=3):
  ROC-AUC, PR-AUC at the reference cell, grid-mean PR-AUC over 15 cells, Spearman with
  log wallets, Brier / accuracy@0.5 / balanced accuracy / F1 after leave-one-fold-out
  Platt calibration (threshold for balanced accuracy also chosen leave-one-fold-out),
  and a paired cluster bootstrap of grid-mean dAP against the v1 final blend.

  python model/iterations.py --k 3 6
  python model/iterations.py --k 3 --only 1 2      # run selected iterations (+ refs)
"""
from __future__ import annotations

import argparse
import time
import warnings
from typing import Callable

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (ExtraTreesClassifier, HistGradientBoostingClassifier,
                              HistGradientBoostingRegressor, RandomForestClassifier)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (average_precision_score, balanced_accuracy_score,
                             brier_score_loss, f1_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler

import panel_forecast as pf
from common import MODEL, annotate_lifecycle, load_lifecycle, load_panel, load_static, savetable
from features import (CAT_COLS, FEATURE_COLS, FEATURE_COLS_PLUS_WALLET,
                      FEATURE_COLS_PLUS_WALLET_TVL)
from labels import GRID_ABS, GRID_REL
from robust_eval import (REF_ABS, REF_REL, _cols, expanding_folds, fit_hard, fit_soft,
                         fit_szabo, grid_labels, grid_scores, load_dataset, paired_bootstrap,
                         train_soft)

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

EPS = 1e-4
CELLS = [(T, r) for T in GRID_ABS for r in GRID_REL]
REFERENCE = "final_blend_v1"

try:
    from user_history_features import USER_HISTORY_FEATURES
except Exception:  # feature file not built yet
    USER_HISTORY_FEATURES = []

# Compact, interpretable core: size, trajectory, stickiness, user quality
COMPACT = [
    "log_last_wallets", "log_max_wallets", "log_mean_wallets", "last_to_max_ratio",
    "wallet_growth_slope", "early_retention", "cohort_m1_retention", "early_cat_share",
    "early_tx_per_wallet", "user_m0_to_last_retention", "user_multi_month_share",
    "acq_last4w_share", "user_single_tx_share",
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def thr_log(window_max, T, rho):
    return np.log1p(np.maximum(T, rho * np.asarray(window_max, dtype=float)))


def gaussian_cells(mu, sigma, window_max) -> dict:
    """P(log wallets >= threshold) for the reference cell and every grid cell."""
    out = {"p": 1 - norm.cdf((thr_log(window_max, REF_ABS, REF_REL) - mu) / sigma)}
    for T, r in CELLS:
        out[(T, r)] = 1 - norm.cdf((thr_log(window_max, T, r) - mu) / sigma)
    return out


def num_pre(cols, spline=False):
    num = [c for c in cols if c not in CAT_COLS]
    steps = [("impute", SimpleImputer(strategy="median", add_indicator=True)),
             ("scale", StandardScaler())]
    if spline:
        steps.append(("spline", SplineTransformer(n_knots=4, degree=3)))
    return ColumnTransformer([
        ("num", Pipeline(steps), num),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                          ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]),
         CAT_COLS),
    ])


def available(ds, cols):
    return [c for c in cols if c in ds.columns and ds[c].notna().mean() > 0.05]


# ---------------------------------------------------------------------------
# Iteration 1: better pooled forecasters (trained on ~10k DApp-month origins)
# ---------------------------------------------------------------------------
class PanelRidge:
    """Ridge on every origin feature (+ missing flags, category), optional
    heteroscedastic sigma(x) from a second model on log|residual|."""

    def __init__(self, hetero=False, boosted=False, local_k=None, alpha=3.0, extra=()):
        self.hetero, self.boosted, self.local_k, self.alpha = hetero, boosted, local_k, alpha
        self.cols = pf.FC_NUM + list(extra) + pf.FC_CAT

    def _w(self, tr):
        w = pf._weights(tr)
        if self.local_k is not None:  # emphasise origins near the scoring age
            w = w * np.exp(-np.abs(tr["age"].values - (self.local_k - 1)) / 3.0)
        return w

    def fit(self, rows):
        tr = rows[rows["target"].notna()].copy()
        X, y, w = self._X(tr), tr["target"].values, self._w(tr)
        if self.boosted:
            self.m = HistGradientBoostingRegressor(
                max_depth=4, learning_rate=0.05, max_iter=300, min_samples_leaf=40,
                l2_regularization=1.0, categorical_features="from_dtype", random_state=42)
            # out-of-bag-ish residuals: 3-fold by slug so sigma isn't optimistic
            slugs = tr["slug"].unique()
            rng = np.random.default_rng(0)
            fold = dict(zip(slugs, rng.integers(0, 3, len(slugs))))
            f = tr["slug"].map(fold).values
            resid = np.zeros(len(tr))
            for i in range(3):
                mi = HistGradientBoostingRegressor(**self.m.get_params())
                mi.fit(X[f != i], y[f != i], sample_weight=w[f != i])
                resid[f == i] = y[f == i] - mi.predict(X[f == i])
            self.m.fit(X, y, sample_weight=w)
        else:
            self.m = Pipeline([("pre", num_pre(self.cols)),
                               ("lr", Ridge(alpha=self.alpha))])
            self.m.fit(X, y, lr__sample_weight=w)
            resid = y - self.m.predict(X)
        self.sigma = float(np.sqrt(np.average(resid ** 2, weights=w)))
        if self.hetero:
            # E[log|e|] = log sigma - 0.635 for Gaussian e
            self.s = Pipeline([("pre", num_pre(self.cols)), ("lr", Ridge(alpha=10.0))])
            self.s.fit(self._Xs(X), np.log(np.abs(resid) + 1e-3), lr__sample_weight=w)
        return self

    def _X(self, rows):
        X = rows[self.cols].copy()
        if not self.boosted:
            X["category_group"] = X["category_group"].astype(str)
        return X

    @staticmethod
    def _Xs(X):
        X = X.copy()
        X["category_group"] = X["category_group"].astype(str)
        return X

    def predict(self, rows):
        X = self._X(rows)
        mu = self.m.predict(X)
        if self.hetero:
            sig = np.exp(self.s.predict(self._Xs(X)) + 0.635)
            sig = np.clip(sig, 0.25 * self.sigma, 3 * self.sigma)
        else:
            sig = np.full(len(mu), self.sigma)
        return mu, sig


LAGS = ["lw3", "lw4", "lw5", "lmean_window", "lmin_window"]


def add_lags(rows: pd.DataFrame, k: int) -> pd.DataFrame:
    """Longer AR history at each origin: lags 3-5 and the mean / min of the last k months."""
    rows = rows.sort_values(["slug", "age"]).copy()
    g = rows.groupby("slug")["lw0"]
    for L in (3, 4, 5):
        rows[f"lw{L}"] = g.shift(L)
    rows["lmean_window"] = g.transform(lambda x: x.rolling(k, min_periods=1).mean())
    rows["lmin_window"] = g.transform(lambda x: x.rolling(k, min_periods=1).min())
    return rows.reset_index(drop=True)


def panel_model(factory):
    def fn(tr, va, ctx):
        rows, k = ctx["rows"], ctx["k"]
        train_rows = rows[rows["slug"].isin(set(tr["slug"]))]
        m = factory(k).fit(train_rows)
        sc = rows[rows["slug"].isin(set(va["slug"])) & (rows["age"] == k - 1)]
        mu, sig = m.predict(sc)
        f = pd.DataFrame({"slug": sc["slug"].values, "mu": mu, "sig": sig,
                          "wmax": sc["max_to_date"].values})
        f = va[["slug", "window_max_wallets", "log_last_wallets"]].merge(f, on="slug", how="left")
        # DApps without an origin row (gaps): fall back to last value, pooled sigma
        f["mu"] = f["mu"].fillna(f["log_last_wallets"])
        f["sig"] = f["sig"].fillna(np.nanmedian(sig) if len(sig) else 1.0)
        f["wmax"] = f["wmax"].fillna(f["window_max_wallets"])
        out = gaussian_cells(f["mu"].values, f["sig"].values, f["wmax"].values)
        out["mu"] = f["mu"].values
        return out
    return fn


def panel_ar(tr, va, ctx):
    rows, k = ctx["rows"], ctx["k"]
    fc = pf.forecast_dapps(rows, tr["slug"], va["slug"], k, kind="ar")
    m = fc.attrs["model"]
    f = va[["slug", "window_max_wallets", "log_last_wallets"]].merge(fc, on="slug", how="left")
    mu = f["fc_mu"].fillna(f["log_last_wallets"]).values
    wmax = f["window_max"].fillna(f["window_max_wallets"]).values
    out = gaussian_cells(mu, np.full(len(mu), m.sigma), wmax)
    out["mu"] = mu
    return out


# ---------------------------------------------------------------------------
# Iteration 2: predict a number from DApp-level features
# ---------------------------------------------------------------------------
def direct_regression(cols_fn, boosted=False):
    def fn(tr, va, ctx):
        cols = available(tr, cols_fn())
        Xc = cols + [c for c in CAT_COLS if c not in cols]
        y = tr["y_log_wallets_12"].values

        def make():
            if boosted:
                return Pipeline([("pre", num_pre(cols)), ("m", HistGradientBoostingRegressor(
                    max_depth=3, learning_rate=0.05, max_iter=250, min_samples_leaf=15,
                    l2_regularization=1.0, random_state=42))])
            return Pipeline([("pre", num_pre(cols)), ("m", Ridge(alpha=10.0))])

        # honest residual sigma from 5 inner folds grouped by parent
        parents = tr["parent_protocol"].values
        uniq = np.unique(parents)
        rng = np.random.default_rng(1)
        g = dict(zip(uniq, rng.integers(0, 5, len(uniq))))
        f = np.array([g[p] for p in parents])
        resid = np.zeros(len(tr))
        for i in range(5):
            mi = make().fit(tr.loc[f != i, Xc], y[f != i])
            resid[f == i] = y[f == i] - mi.predict(tr.loc[f == i, Xc])
        m = make().fit(tr[Xc], y)
        mu = m.predict(va[Xc])
        out = gaussian_cells(mu, float(np.std(resid)), va["window_max_wallets"].values)
        out["mu"] = mu
        return out
    return fn


def _ar_mu(rows, train_slugs, score_df, k):
    fc = pf.forecast_dapps(rows, train_slugs, score_df["slug"], k, kind="ar")
    f = score_df[["slug", "log_last_wallets"]].merge(fc[["slug", "fc_mu"]], on="slug", how="left")
    return f["fc_mu"].fillna(f["log_last_wallets"]).values


def ar_residual(cols_fn, boosted=False, shrink=1.0):
    """Panel AR forecast + a second model that learns only the correction to it from
    DApp-level features. Inner-fold AR forecasts keep the correction honest."""
    def fn(tr, va, ctx):
        rows, k = ctx["rows"], ctx["k"]
        cols = available(tr, cols_fn())
        Xc = cols + [c for c in CAT_COLS if c not in cols]
        parents = tr["parent_protocol"].values
        uniq = np.unique(parents)
        rng = np.random.default_rng(3)
        g = dict(zip(uniq, rng.integers(0, 5, len(uniq))))
        f = np.array([g[p] for p in parents])
        mu_tr = np.zeros(len(tr))
        for i in range(5):
            mu_tr[f == i] = _ar_mu(rows, tr.loc[f != i, "slug"], tr[f == i], k)
        target = tr["y_log_wallets_12"].values - mu_tr

        def make():
            if boosted:
                return Pipeline([("pre", num_pre(cols)), ("m", HistGradientBoostingRegressor(
                    max_depth=2, learning_rate=0.03, max_iter=200, min_samples_leaf=20,
                    l2_regularization=5.0, random_state=42))])
            return Pipeline([("pre", num_pre(cols)), ("m", Ridge(alpha=30.0))])

        resid = np.zeros(len(tr))
        for i in range(5):
            mi = make().fit(tr.loc[f != i, Xc], target[f != i])
            resid[f == i] = target[f == i] - shrink * mi.predict(tr.loc[f == i, Xc])
        m = make().fit(tr[Xc], target)
        mu = _ar_mu(rows, tr["slug"], va, k) + shrink * m.predict(va[Xc])
        out = gaussian_cells(mu, float(np.std(resid)), va["window_max_wallets"].values)
        out["mu"] = mu
        return out
    return fn


# ---------------------------------------------------------------------------
# Iteration 3: classifier variety
# ---------------------------------------------------------------------------
def sk_classifier(make_clf, cols_fn, soft=False, spline=False):
    def fn(tr, va, ctx):
        cols = available(tr, cols_fn())
        Xc = cols + [c for c in CAT_COLS if c not in cols]
        pipe = Pipeline([("pre", num_pre(cols, spline=spline)), ("clf", make_clf())])
        if soft:
            s = tr["y_soft_12"].clip(0, 1).values
            X = pd.concat([tr[Xc]] * 2, ignore_index=True)
            y = np.r_[np.ones(len(tr)), np.zeros(len(tr))]
            w = np.r_[s, 1 - s]
            pos, neg = w[y == 1].sum(), w[y == 0].sum()
            w = np.where(y == 1, w * neg / max(pos, 1e-9), w)
            keep = w > 1e-6
            pipe.fit(X[keep], y[keep], clf__sample_weight=w[keep])
        else:
            yb = tr["y_sustained_12"].values
            w = np.where(yb == 1, (yb == 0).sum() / max(yb.sum(), 1), 1.0)
            pipe.fit(tr[Xc], yb, clf__sample_weight=w)
        return pipe.predict_proba(va[Xc])[:, 1]
    return fn


def monotone_hgb():
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200,
                                          min_samples_leaf=15, l2_regularization=1.0,
                                          random_state=42)


def hgb_monotone_soft(cols_fn):
    """Soft-label HGB with 'bigger and less faded is never worse' constraints."""
    inc = {"log_last_wallets", "log_mean_wallets", "log_max_wallets", "last_to_max_ratio",
           "early_retention", "user_m0_to_last_retention"}

    def fn(tr, va, ctx):
        cols = available(tr, cols_fn())
        Xc = cols + [c for c in CAT_COLS if c not in cols]
        pipe = _hgb_soft_pipe(cols)
        # constraint vector must follow the transformed column order
        pre = num_pre(cols)
        pre.fit(tr[Xc])
        names = pre.get_feature_names_out()
        cst = [1 if n.split("__", 1)[1] in inc else 0 for n in names]
        pipe.named_steps["clf"].set_params(monotonic_cst=cst)
        return _fit_soft_pipe(pipe, tr, Xc).predict_proba(va[Xc])[:, 1]
    return fn


def _hgb_soft_pipe(cols, **kw):
    params = dict(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=15,
                  l2_regularization=1.0, random_state=42)
    params.update(kw)
    return Pipeline([("pre", num_pre(cols)), ("clf", HistGradientBoostingClassifier(**params))])


def _fit_soft_pipe(pipe, tr, Xc):
    s = tr["y_soft_12"].clip(0, 1).values
    X = pd.concat([tr[Xc]] * 2, ignore_index=True)
    y = np.r_[np.ones(len(tr)), np.zeros(len(tr))]
    w = np.r_[s, 1 - s]
    pos, neg = w[y == 1].sum(), w[y == 0].sum()
    w = np.where(y == 1, w * neg / max(pos, 1e-9), w)
    keep = w > 1e-6
    pipe.fit(X[keep], y[keep], clf__sample_weight=w[keep])
    return pipe


def hgb_soft_custom(cols_fn, **kw):
    def fn(tr, va, ctx):
        cols = available(tr, cols_fn())
        Xc = cols + [c for c in CAT_COLS if c not in cols]
        return _fit_soft_pipe(_hgb_soft_pipe(cols, **kw), tr, Xc).predict_proba(va[Xc])[:, 1]
    return fn


# ---------------------------------------------------------------------------
# Reference wrappers
# ---------------------------------------------------------------------------
def ref_hgb(tr, va, ctx):
    return fit_hard(tr, va, list(FEATURE_COLS))


def ref_soft_wallet(tr, va, ctx):
    return fit_soft(tr, va, list(FEATURE_COLS_PLUS_WALLET))


def ref_final_blend(tr, va, ctx):
    ph = train_soft(tr, list(FEATURE_COLS_PLUS_WALLET_TVL)).predict_proba(
        va[_cols(FEATURE_COLS_PLUS_WALLET_TVL)])[:, 1]
    pa = panel_ar(tr, va, ctx)["p"]
    return 1 / (1 + np.exp(-(0.5 * _logit(ph) + 0.5 * _logit(pa))))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
def base_cols():
    return list(FEATURE_COLS_PLUS_WALLET)


def compact_cols():
    return list(COMPACT)


def compact_hist_cols():
    return list(COMPACT) + list(USER_HISTORY_FEATURES)


def wallet_hist_cols():
    return list(FEATURE_COLS_PLUS_WALLET) + list(USER_HISTORY_FEATURES)


def experiments() -> dict[str, tuple[int, str, Callable]]:
    E = {
        "szabo_huberman": (0, "1 feature: log wallets in month k-1", lambda tr, va, c: fit_szabo(tr, va)),
        "hgb_v1": (0, "v1 boosted trees, hard label", ref_hgb),
        "panel_ar": (0, "pooled linear AR on log wallets (v2)", panel_ar),
        "hgb_soft_wallet": (0, "soft-label HGB + wallet features (v2)", ref_soft_wallet),
        REFERENCE: (0, "v2 production: soft HGB (+TVL) + panel AR logit blend", ref_final_blend),
        # iteration 1
        "panel_ridge": (1, "pooled ridge on all 22 origin features", panel_model(lambda k: PanelRidge())),
        "panel_ridge_hetero": (1, "+ heteroscedastic sigma(x)", panel_model(lambda k: PanelRidge(hetero=True))),
        "panel_ridge_local": (1, "+ origins weighted near age k-1",
                              panel_model(lambda k: PanelRidge(hetero=True, local_k=k))),
        "panel_hgb_mean": (1, "boosted mean + heteroscedastic sigma",
                           panel_model(lambda k: PanelRidge(hetero=True, boosted=True))),
        "panel_hgb_local": (1, "boosted mean, hetero sigma, local weights",
                            panel_model(lambda k: PanelRidge(hetero=True, boosted=True, local_k=k))),
        "panel_hgb_lags": (1, "boosted mean + 6 monthly lags and window mean/min",
                           panel_model(lambda k: PanelRidge(hetero=True, boosted=True, extra=LAGS))),
        "panel_ridge_lags": (1, "ridge + 6 monthly lags and window mean/min",
                             panel_model(lambda k: PanelRidge(hetero=True, extra=LAGS))),
        # iteration 2
        "reg_ridge": (2, "ridge: features -> log wallets m10-12", direct_regression(base_cols)),
        "reg_hgb": (2, "boosted regression: features -> log wallets", direct_regression(base_cols, True)),
        "reg_ridge_compact": (2, "ridge on 13 compact features", direct_regression(compact_cols)),
        # iteration 3
        "rf_soft": (3, "random forest, soft labels", sk_classifier(
            lambda: RandomForestClassifier(n_estimators=500, min_samples_leaf=5, max_features=0.3,
                                           n_jobs=-1, random_state=42), base_cols, soft=True)),
        "extratrees_soft": (3, "extra trees, soft labels", sk_classifier(
            lambda: ExtraTreesClassifier(n_estimators=500, min_samples_leaf=5, max_features=0.3,
                                         n_jobs=-1, random_state=42), base_cols, soft=True)),
        "hgb_soft_shallow": (3, "soft HGB depth 2, stronger L2", hgb_soft_custom(
            base_cols, max_depth=2, l2_regularization=5.0, max_iter=300)),
        "hgb_soft_monotone": (3, "soft HGB with monotone size constraints", hgb_monotone_soft(base_cols)),
        "hgb_soft_compact": (3, "soft HGB on 13 compact features", hgb_soft_custom(compact_cols)),
        "spline_gam_compact": (3, "spline logistic (GAM-style) on compact features", sk_classifier(
            lambda: LogisticRegression(C=0.3, max_iter=3000), compact_cols, soft=True, spline=True)),
    }
    E.update({
        "ar_resid_ridge": (4, "panel AR + ridge correction from DApp features", ar_residual(base_cols)),
        "ar_resid_hgb": (4, "panel AR + boosted correction from DApp features",
                         ar_residual(base_cols, boosted=True)),
    })
    if USER_HISTORY_FEATURES:
        E.update({
            "ar_resid_ridge_hist": (4, "panel AR + ridge correction incl. user-history",
                                    ar_residual(wallet_hist_cols)),
            "ar_resid_hgb_hist": (4, "panel AR + boosted correction incl. user-history",
                                  ar_residual(wallet_hist_cols, boosted=True)),
            "hgb_soft_wallet_hist": (4, "soft HGB + wallet + user-history features",
                                     hgb_soft_custom(wallet_hist_cols)),
            "hgb_soft_compact_hist": (4, "soft HGB on compact + user-history",
                                      hgb_soft_custom(compact_hist_cols)),
            "reg_ridge_hist": (4, "ridge regression + user-history", direct_regression(wallet_hist_cols)),
            "rf_soft_hist": (4, "random forest + user-history", sk_classifier(
                lambda: RandomForestClassifier(n_estimators=500, min_samples_leaf=5, max_features=0.3,
                                               n_jobs=-1, random_state=42), wallet_hist_cols, soft=True)),
        })
    return E


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def lofo_calibrate(oof, col, y):
    p = np.full(len(oof), np.nan)
    z = _logit(oof[col].values).reshape(-1, 1)
    for f in oof["fold"].unique():
        m = (oof["fold"] == f).values
        cal = LogisticRegression().fit(z[~m], y[~m])
        p[m] = cal.predict_proba(z[m])[:, 1]
    return p


def lofo_threshold(oof, p, y):
    """Balanced-accuracy threshold chosen on the other folds."""
    pred = np.zeros(len(p), dtype=int)
    grid = np.linspace(0.02, 0.9, 89)
    for f in oof["fold"].unique():
        m = (oof["fold"] == f).values
        ba = [balanced_accuracy_score(y[~m], (p[~m] >= t).astype(int)) for t in grid]
        pred[m] = (p[m] >= grid[int(np.argmax(ba))]).astype(int)
    return pred


def score(oof, name, labels):
    y = oof["y_sustained_12"].values
    p_raw = oof[name].values
    g = grid_scores(oof, name, labels)
    pc = lofo_calibrate(oof, name, y)
    pred = lofo_threshold(oof, pc, y)
    return {
        "model": name,
        "auc": roc_auc_score(y, p_raw),
        "ap_ref": average_precision_score(y, p_raw),
        "ap_grid_mean": float(np.nanmean(list(g.values()))),
        "spearman": spearmanr(p_raw, oof["y_log_wallets_12"]).correlation,
        "brier_cal": brier_score_loss(y, pc),
        "acc_at_0.5": float(((pc >= 0.5).astype(int) == y).mean()),
        "balanced_acc": balanced_accuracy_score(y, pred),
        "f1": f1_score(y, pred),
    }


def pick_members(oof, names, labels, top_n=4):
    """Top models by grid-mean AP, forcing at least one forecaster and one classifier."""
    ranked = sorted([n for n in names if n != REFERENCE],
                    key=lambda n: -np.nanmean(list(grid_scores(oof, n, labels).values())))
    picks = ranked[:top_n]
    fams = {n: ("forecast" if n.startswith(("panel", "reg", "ar_")) else "classifier") for n in names}
    if len({fams[n] for n in picks}) == 1:
        other = next((n for n in ranked if fams[n] != fams[picks[0]]), None)
        if other:
            picks = picks[:-1] + [other]
    return picks


def logit_mean_cells(oof, picks, idx=None):
    idx = np.arange(len(oof)) if idx is None else idx
    out = {"p": 1 / (1 + np.exp(-np.mean([_logit(oof[n].values[idx]) for n in picks], axis=0)))}
    for T, r in CELLS:
        cols = [f"{n}@{T}_{r}" if f"{n}@{T}_{r}" in oof else n for n in picks]
        out[(T, r)] = 1 / (1 + np.exp(-np.mean([_logit(oof[c].values[idx]) for c in cols], axis=0)))
    return out


def nested_ensemble(oof, names, top_n=4):
    """Honest ensemble: members for each validation year are chosen on the OTHER years only."""
    cols = {"ens_nested": np.full(len(oof), np.nan)}
    for T, r in CELLS:
        cols[f"ens_nested@{T}_{r}"] = np.full(len(oof), np.nan)
    chosen = {}
    for f in oof["fold"].unique():
        m = (oof["fold"] == f).values
        other = oof[~m]
        picks = pick_members(other, names, grid_labels(other), top_n)
        chosen[f] = picks
        res = logit_mean_cells(oof, picks, np.where(m)[0])
        cols["ens_nested"][m] = res["p"]
        for T, r in CELLS:
            cols[f"ens_nested@{T}_{r}"][m] = res[(T, r)]
    for c, v in cols.items():
        oof[c] = v
    return chosen


def ensembles(oof, names, labels, top_n=4):
    """Iteration 5: rank average, logit mean and LOFO-stacked meta-model of the top models
    (members chosen on all folds: optimistic), plus the nested version (honest)."""
    y = oof["y_sustained_12"].values
    picks = pick_members(oof, names, labels, top_n)
    rank = np.mean([pd.Series(oof[n]).rank(pct=True).values for n in picks], axis=0)
    oof["ens_rank_avg"] = rank
    # per-cell rank average for forecasters that have cells
    for T, r in CELLS:
        cols = [f"{n}@{T}_{r}" if f"{n}@{T}_{r}" in oof else n for n in picks]
        oof[f"ens_rank_avg@{T}_{r}"] = np.mean([oof[c].rank(pct=True).values for c in cols], axis=0)
    Z = np.column_stack([_logit(oof[n].values) for n in picks])
    stack = np.full(len(oof), np.nan)
    for f in oof["fold"].unique():
        m = (oof["fold"] == f).values
        meta = LogisticRegression(C=1.0).fit(Z[~m], y[~m])
        stack[m] = meta.predict_proba(Z[m])[:, 1]
    oof["ens_stacked"] = stack
    blend = 1 / (1 + np.exp(-Z.mean(axis=1)))
    oof["ens_logit_mean"] = blend
    for T, r in CELLS:
        cols = [f"{n}@{T}_{r}" if f"{n}@{T}_{r}" in oof else n for n in picks]
        oof[f"ens_logit_mean@{T}_{r}"] = 1 / (1 + np.exp(-np.mean(
            [_logit(oof[c].values) for c in cols], axis=0)))
    return picks


def run(k: int, only: list[int] | None, n_boot: int) -> pd.DataFrame:
    t0 = time.time()
    ds = load_dataset(k)
    if USER_HISTORY_FEATURES:
        from user_history_features import merge_user_history
        ds = merge_user_history(ds, k)
    rows = pf.build_rows(k, load_panel(), annotate_lifecycle(load_lifecycle(), load_static()))
    rows = add_lags(rows, k)
    ctx = {"rows": rows, "k": k}
    E = {n: e for n, e in experiments().items() if only is None or e[0] == 0 or e[0] in only}
    print(f"\n== iterations k={k}: {len(ds)} DApps, {len(E)} experiments ==")

    parts = []
    for fold, tr, va in expanding_folds(ds):
        part = va[["slug", "parent_protocol", "mean_wallets_10_12", "window_max_wallets",
                   "y_sustained_12", "y_log_wallets_12"]].copy()
        part["fold"] = fold
        cols = {}
        for name, (_, _, fn) in E.items():
            res = fn(tr, va, ctx)
            if isinstance(res, dict):
                cols[name] = np.asarray(res["p"])
                for (T, r) in CELLS:
                    cols[f"{name}@{T}_{r}"] = np.asarray(res[(T, r)])
            else:
                cols[name] = np.asarray(res)
        part = pd.concat([part.reset_index(drop=True), pd.DataFrame(cols)], axis=1)
        parts.append(part)
        print(f"  {fold}: val={len(va)} pos={int(va['y_sustained_12'].sum())} ({time.time()-t0:.0f}s)")
    oof = pd.concat(parts, ignore_index=True).copy()
    labels = grid_labels(oof)
    names = list(E)
    picks = ensembles(oof, names, labels)
    chosen = nested_ensemble(oof, names)
    ens = ["ens_rank_avg", "ens_logit_mean", "ens_stacked", "ens_nested"]

    res = pd.DataFrame([score(oof, n, labels) for n in names + ens])
    meta = {n: (e[0], e[1]) for n, e in E.items()}
    meta.update({e: (5, f"{e.split('_', 1)[1].replace('_', ' ')} of {', '.join(picks)}") for e in ens})
    meta["ens_nested"] = (5, "logit mean; members re-chosen per fold on other folds: "
                          + "; ".join(f"{f}: {', '.join(p)}" for f, p in chosen.items()))
    res.insert(1, "iteration", res["model"].map(lambda n: meta[n][0]))
    res.insert(2, "description", res["model"].map(lambda n: meta[n][1]))
    res.insert(3, "k", k)
    boot = paired_bootstrap(oof, labels, [n for n in names + ens if n != REFERENCE], REFERENCE,
                            n_boot=n_boot)
    for col in ("d_ap_grid_mean", "d_ap_grid_lo", "d_ap_grid_hi", "p_grid_better"):
        res[col] = res["model"].map(lambda n: boot.get(n, {}).get(col, np.nan))
    res = res.sort_values(["iteration", "ap_grid_mean"], ascending=[True, False])
    tag = "" if only is None else "_iter" + "".join(map(str, only))
    savetable(res, f"iterations_k{k}{tag}.csv")
    oof.to_csv(MODEL / "tables" / f"iterations_oof_k{k}{tag}.csv", index=False)
    show = ["model", "iteration", "auc", "ap_ref", "ap_grid_mean", "spearman", "brier_cal",
            "acc_at_0.5", "balanced_acc", "f1", "d_ap_grid_mean", "d_ap_grid_lo", "d_ap_grid_hi"]
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(res[show].round(3).to_string(index=False))
    print(f"  ensemble members (all folds): {picks}")
    for f, p in chosen.items():
        print(f"  nested members for {f}: {p}")
    print(f"  ({time.time()-t0:.0f}s)")
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, nargs="+", default=[3, 6])
    ap.add_argument("--only", type=int, nargs="+", default=None)
    ap.add_argument("--n-boot", type=int, default=300)
    args = ap.parse_args()
    for k in args.k:
        run(k, args.only, args.n_boot)


if __name__ == "__main__":
    main()
