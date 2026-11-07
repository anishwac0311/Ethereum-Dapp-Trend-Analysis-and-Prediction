"""Survival metrics: C-index, integrated Brier score, time-dependent Brier and AUC (IPCW-free, simple).

All functions take durations/events as numpy arrays and `surv` as a DataFrame of survival
probabilities (index = time grid in months, columns = subjects) as returned by pycox.
"""
import numpy as np
import scipy.integrate
from lifelines.utils import concordance_index
from pycox.evaluation import EvalSurv

# pycox 0.3 calls scipy.integrate.simps, which recent scipy releases removed.
if not hasattr(scipy.integrate, "simps"):
    scipy.integrate.simps = scipy.integrate.simpson


def c_index(durations, events, risk):
    """Higher risk should mean shorter survival."""
    return concordance_index(durations, -np.asarray(risk), events)


def eval_surv(surv, durations, events):
    return EvalSurv(surv, durations, events, censor_surv="km")


def survival_metrics(surv, durations, events, times):
    ev = eval_surv(surv, durations, events)
    grid = np.linspace(durations.min(), np.percentile(durations, 90), 50)
    out = {
        "c_index_td": float(ev.concordance_td("antolini")),
        "ibs": float(ev.integrated_brier_score(grid)),
    }
    for t in times:
        out[f"brier@{t}m"] = float(ev.brier_score(np.array([t])).iloc[0])
    return out
