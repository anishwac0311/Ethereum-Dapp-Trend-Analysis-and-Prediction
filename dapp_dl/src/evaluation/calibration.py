"""Split-conformal widening of DeepAR's prediction intervals.

The earlier evaluation window (cutoff 2024-12) is the calibration set; the later window
(cutoff 2025-06) is the evaluation set, so calibration never sees the data it is scored on.
For each calibration forecast the nonconformity score is how far the outcome falls outside
the interval, max(lo - y, y - hi) (negative when inside). The finite-sample-corrected
`level` quantile q of those scores shifts both bounds: [lo - q, hi + q]. Scores are pooled
across dApps and horizon steps (the simplest version; a per-horizon q is an easy extension).
"""
import numpy as np


def conformal_q(y, lo, hi, level=0.8):
    s = np.maximum(lo - y, y - hi)
    n = len(s)
    k = min(int(np.ceil((n + 1) * level)), n)
    return float(np.sort(s)[k - 1])


def calibrate_by_horizon(fit, test, prefix="DeepAR", level=80, pooled=False):
    """Conformal widening with one q per horizon step, learned on `fit` (earlier windows) and
    applied to `test`. With pooled=True a single q is used for all steps (the earlier method).
    Returns (test copy with -cal columns, {step: q})."""
    lo, hi = f"{prefix}-lo-{level}", f"{prefix}-hi-{level}"
    test = test.copy()
    test[lo + "-cal"], test[hi + "-cal"] = np.nan, np.nan
    qs = {}
    q_all = conformal_q(fit.y.to_numpy(), fit[lo].clip(lower=0).to_numpy(), fit[hi].to_numpy(), level / 100)
    for k in sorted(test.horizon_step.unique()):
        f = fit[fit.horizon_step == k]
        q = q_all if pooled else conformal_q(f.y.to_numpy(), f[lo].clip(lower=0).to_numpy(), f[hi].to_numpy(), level / 100)
        qs[int(k)] = q
        m = test.horizon_step == k
        test.loc[m, lo + "-cal"] = test.loc[m, lo] - q
        test.loc[m, hi + "-cal"] = test.loc[m, hi] + q
    return test, qs


def calibrate_deepar(ev, prefix="DeepAR", level=80, lo_clip=0.0):
    """Return a copy of `ev` with `{prefix}-lo-{level}-cal` / `-hi-{level}-cal` columns for the
    later window, and the q used. Rows of the calibration window are dropped."""
    cutoffs = sorted(ev.cutoff.unique())
    cal, test = ev[ev.cutoff == cutoffs[0]], ev[ev.cutoff == cutoffs[-1]].copy()
    lo, hi = f"{prefix}-lo-{level}", f"{prefix}-hi-{level}"
    q = conformal_q(cal.y.to_numpy(), cal[lo].clip(lower=lo_clip).to_numpy(), cal[hi].to_numpy(), level / 100)
    test[lo + "-cal"] = test[lo] - q
    test[hi + "-cal"] = test[hi] + q
    return test, q
