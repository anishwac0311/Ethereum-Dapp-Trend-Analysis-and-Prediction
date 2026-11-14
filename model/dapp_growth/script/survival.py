"""Survival analysis: how long successful and other DApps take to reach 5k and 10k cumulative wallets (first-user clock)."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter
from scipy import stats

from common import GROUP_COLOURS, GROUPS, compare_groups, record, savefig

MILESTONES = ["5k", "10k"]
KM_MONTHS = [3, 6, 12, 24]
MARKED_MONTHS = [6, 24]
PLOT_MONTHS = 36


def kaplan_meier(time: np.ndarray, event: np.ndarray) -> pd.DataFrame:
    """Share of DApps that have reached the milestone by each event month (1 - survival)."""
    rows, surv = [], 1.0
    for t in np.unique(time[event == 1]):
        at_risk = (time >= t).sum()
        surv *= 1 - ((time == t) & (event == 1)).sum() / at_risk
        rows.append({"month": t, "reached": 1 - surv})
    return pd.DataFrame(rows)


def reached_by(curve: pd.DataFrame, month: float) -> float:
    before = curve[curve["month"] <= month]
    return before["reached"].iloc[-1] if len(before) else 0.0


def log_rank(time: np.ndarray, event: np.ndarray, group: np.ndarray) -> tuple[float, float]:
    """Two-group log-rank test (chi-square, 1 degree of freedom)."""
    observed = expected = variance = 0.0
    for t in np.unique(time[event == 1]):
        at_risk = time >= t
        n, n1 = at_risk.sum(), (at_risk & (group == 1)).sum()
        d = ((time == t) & (event == 1)).sum()
        d1 = ((time == t) & (event == 1) & (group == 1)).sum()
        observed += d1
        expected += d * n1 / n
        if n > 1:
            variance += d * (n1 / n) * (1 - n1 / n) * (n - d) / (n - 1)
    chisq = (observed - expected) ** 2 / variance
    return chisq, stats.chi2.sf(chisq, 1)


def time_to(dapps: pd.DataFrame, label: str) -> None:
    """Kaplan-Meier, log-rank and a figure for one milestone, e.g. label = "10k"."""
    # Reached: months to the milestone; not reached: censored at the last observed month
    reached = dapps[f"reached_{label}"].to_numpy()
    time = np.where(reached == 1, dapps[f"months_to_{label}"], dapps["observed_months"] - 1).astype(float)

    curves = {g: kaplan_meier(time[dapps["group"] == g], reached[dapps["group"] == g]) for g in GROUPS}
    rows = []
    for g in GROUPS:
        in_group = (dapps["group"] == g).to_numpy()
        rows.append({"group": g, "n_dapps": int(in_group.sum()), f"reached_{label}": int(reached[in_group].sum()),
                     "censored": int((reached[in_group] == 0).sum()),
                     **{f"reached_by_m{m}": round(reached_by(curves[g], m), 3) for m in KM_MONTHS}})
    record(pd.DataFrame(rows), f"time_to_{label}_by_group")

    # Log-rank test for the success label at several windows k
    by_k = []
    for k in (1, 3, 6):
        success = dapps[f"success_k{k}"].to_numpy()
        chisq, p = log_rank(time, reached, success)
        by_k.append({"k": k, "n_success": int(success.sum()), "chisq": chisq, "p_value": p})
    record(pd.DataFrame(by_k), f"time_to_{label}_logrank_by_k")

    # Among DApps that reached the milestone: how fast is each group?
    record(compare_groups(dapps[reached == 1], f"months_to_{label}", f"reached {label}"),
           f"months_to_{label}_reached")

    fig, ax = plt.subplots()
    for m in MARKED_MONTHS:
        ax.axvline(m, ls="--", color="#9CA3AF", lw=0.8)
    for g in reversed(GROUPS):
        c = curves[g]
        ax.step(np.r_[0, c["month"], PLOT_MONTHS], np.r_[0, c["reached"], c["reached"].iloc[-1]], where="post",
                color=GROUP_COLOURS[g], lw=1.6, label=g)
    ax.set(xlim=(0, PLOT_MONTHS), ylim=(0, 1.02), xlabel="Months since first user",
           ylabel=f"Share of DApps at {label.upper()} cumulative wallets")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    savefig(fig, f"time_to_{label}")

    print(f"-- {label.upper()}")
    print(pd.DataFrame(rows).to_string(index=False))
    print(pd.DataFrame(by_k).to_string(index=False))


def run(dapps: pd.DataFrame) -> None:
    for label in MILESTONES:
        time_to(dapps, label)
