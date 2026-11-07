"""Calibration of predicted survival probabilities, and cloglog-Cox recalibration.

Calibration asks: among dApps that a model gives a predicted event probability p by time t,
does a fraction ~p actually have the event by t? Observed risk in a group is estimated with
Kaplan-Meier, so censoring is handled.

Recalibration (Van Houwelingen-style): on a held-out *validation* set, fit a one-covariate Cox
model on z = log(-log S_pred(t | x)). The fitted slope corrects over/under-confident spread,
and the re-estimated baseline corrects the overall level. Applied to the test set, giving
S_cal(t | x) = S0(t) ** exp(beta * z). Fitted separately for each time point t.
"""
import numpy as np
import pandas as pd
from lifelines import CoxPHFitter, KaplanMeierFitter
from pycox.evaluation import EvalSurv


def surv_at(surv_df, t):
    """S(t | x) for every subject (step function; 1.0 before the first grid time)."""
    idx = surv_df.index.to_numpy()
    pos = np.searchsorted(idx, t, side="right") - 1
    if pos < 0:
        return np.ones(surv_df.shape[1])
    return surv_df.iloc[pos].to_numpy()


def km_risk(d, e, t):
    if len(d) == 0:
        return np.nan
    return float(1 - KaplanMeierFitter().fit(d, e).survival_function_at_times(t).iloc[0])


def calibration_table(p_pred, d, e, t, n_bins=4):
    """Quantile bins of predicted risk -> mean predicted vs Kaplan-Meier observed risk."""
    order = np.argsort(p_pred, kind="stable")
    rows = []
    for b, idx in enumerate(np.array_split(order, n_bins)):
        rows.append(
            {"bin": b, "n": len(idx), "events": int(e[idx].sum()), "pred": float(p_pred[idx].mean()), "obs": km_risk(d[idx], e[idx], t)}
        )
    return pd.DataFrame(rows)


def calibration_summary(p_pred, d, e, t, n_bins=4):
    tab = calibration_table(p_pred, d, e, t, n_bins)
    w = tab.n / tab.n.sum()
    return {
        "ici": float((w * (tab.pred - tab.obs).abs()).sum()),  # integrated calibration index (binned)
        "citl": float(p_pred.mean() - km_risk(d, e, t)),  # calibration in the large: mean predicted - observed
    }, tab


def brier_at(S, d, e, t):
    """IPCW Brier score at time t for survival probabilities S (one per subject)."""
    surv = pd.DataFrame(np.asarray(S).reshape(1, -1), index=[float(t)])
    return float(EvalSurv(surv, d, e, censor_surv="km").brier_score(np.array([float(t)])).iloc[0])


class CloglogRecalibrator:
    """Per-time-point recalibration fitted on a validation set."""

    def __init__(self, penalizer=0.05):
        self.penalizer = penalizer

    @staticmethod
    def _z(S):
        S = np.clip(np.asarray(S, dtype=float), 1e-4, 1 - 1e-4)
        return np.log(-np.log(S))

    def fit(self, S_val, d_val, e_val, t):
        self.t, self.ok, self.beta = t, False, np.nan
        z = self._z(S_val)
        if np.std(z) < 1e-8 or e_val.sum() < 3:
            return self  # degenerate: leave predictions unchanged
        df = pd.DataFrame({"z": z, "duration": d_val, "event": e_val})
        try:
            self.cph = CoxPHFitter(penalizer=self.penalizer).fit(df, "duration", "event")
            self.beta, self.ok = float(self.cph.params_["z"]), True
        except Exception:
            pass
        return self

    def transform(self, S):
        if not self.ok:
            return np.asarray(S, dtype=float)
        df = pd.DataFrame({"z": self._z(S)})
        out = self.cph.predict_survival_function(df, times=[self.t])
        return out.iloc[0].to_numpy()
