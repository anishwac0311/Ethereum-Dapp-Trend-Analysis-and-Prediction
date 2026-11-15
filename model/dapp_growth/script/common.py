"""Shared paths, settings, data readers and helpers for the growth analysis."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import optimize, stats

HOME = Path(__file__).resolve().parents[1]
ROOT = HOME.parents[1]
RAW = ROOT / "dapp_data_v2"              # input CSVs, shared with the rest of the project
DATA = HOME / "data"                     # data built here
TABLES = HOME / "results" / "tables"
FIGURES = HOME / "results" / "figures"
for d in (DATA, TABLES, FIGURES):
    d.mkdir(parents=True, exist_ok=True)

PANEL_START = pd.Timestamp("2020-01-01")

# Success rule, same as model/labels.py. Months count from 0, so 10-12 are the 11th-13th months after launch
ABS_WALLETS = 1000
REL_OF_WINDOW_MAX = 0.25
OUTCOME_MONTHS = [10, 11, 12]
LAST_MONTH = 12
WINDOWS = range(1, 10)

# Growth is measured before the outcome months
GROWTH_LAST_MONTH = 9

# Limits for the growth curve fits
MAX_L_MULTIPLE = 10
MIN_LOG_R = np.log(.01)
MAX_LOG_R = np.log(5)
EARLY_MONTHS = 24

GROUPS = ["Not successful", "Successful"]
GROUP_COLOURS = {"Successful": "#008A7E", "Not successful": "#C46A2B"}

# Every figure has the same size, so figures shown side by side line up
FIGSIZE = (8, 5)
DPI = 150


# ---- data ----

def read_panel() -> pd.DataFrame:
    cols = ["slug", "month", "months_since_launch", "active_wallets", "new_wallets", "cum_wallets",
            "category_group", "parent_protocol", "first_deployed"]
    panel = pd.read_csv(RAW / "dapp_panel.csv", usecols=cols, parse_dates=["month", "first_deployed"])
    return panel[cols].sort_values(["slug", "month"]).reset_index(drop=True)


def success_table(monthly: pd.DataFrame, clock: str) -> pd.DataFrame:
    """One success column per window k, plus success_abs (size rule only)."""
    m = monthly.rename(columns={clock: "t"})
    outcome = m[m["t"].isin(OUTCOME_MONTHS)].groupby("slug")["active_wallets"].mean()
    out = pd.DataFrame(index=outcome.index)
    for k in WINDOWS:
        window_max = m[m["t"] < k].groupby("slug")["active_wallets"].max().reindex(outcome.index)
        out[f"success_k{k}"] = ((outcome >= ABS_WALLETS) & (outcome >= REL_OF_WINDOW_MAX * window_max)).astype(int)
    out["success_abs"] = (outcome >= ABS_WALLETS).astype(int)
    return out.reset_index()


def months_to(cum: np.ndarray, t: np.ndarray, n: float) -> float:
    """First month cumulative wallets reach n; NaN if they never do."""
    if np.isnan(n) or not (cum >= n).any():
        return np.nan
    return float(t[np.argmax(cum >= n)])


def milestones_table(months: pd.DataFrame, clock: str) -> pd.DataFrame:
    """Milestones need every observed month, not only months 0-12."""
    rows = []
    for slug, g in months.rename(columns={clock: "t"}).groupby("slug"):
        cum, t = g["cum_wallets"].to_numpy(), g["t"].to_numpy()
        half = cum.max() / 2 if cum.max() > 0 else np.nan
        rows.append({"slug": slug, "months_to_1k": months_to(cum, t, 1000), "months_to_5k": months_to(cum, t, 5000),
                     "months_to_10k": months_to(cum, t, 10000),
                     "months_to_half_peak_cum": months_to(cum, t, half),
                     "months_to_peak": t[np.argmax(g["active_wallets"].to_numpy())],
                     "peak_wallets": g["active_wallets"].max()})
    out = pd.DataFrame(rows)
    out["reached_1k"] = out["months_to_1k"].notna().astype(int)
    out["reached_5k"] = out["months_to_5k"].notna().astype(int)
    out["reached_10k"] = out["months_to_10k"].notna().astype(int)
    return out


def wallets_table(monthly: pd.DataFrame, clock: str) -> pd.DataFrame:
    """Active and cumulative wallets at months 3, 6, 12; `m3` is the month with clock == 3, the 4th month."""
    m = monthly.rename(columns={clock: "t"})
    m = m[m["t"].isin([3, 6, 12])].pivot(index="slug", columns="t", values=["active_wallets", "cum_wallets"])
    m.columns = [f"{'wallets' if v == 'active_wallets' else 'cum_wallets'}_m{int(t)}" for v, t in m.columns]
    return m.reset_index()


def compound_growth(monthly: pd.DataFrame, clock: str, last_month: int, name: str) -> pd.DataFrame:
    """Compound monthly % growth of cumulative wallets, first non-zero month to last_month."""
    m = monthly.rename(columns={clock: "t"})
    m = m[(m["t"] <= last_month) & (m["cum_wallets"] > 0)].sort_values(["slug", "t"])
    first = m.groupby("slug").first()[["t", "cum_wallets"]]
    end = m[m["t"] == last_month].set_index("slug")["cum_wallets"]
    first = first.join(end.rename("end"), how="left")
    first = first[first["t"] < last_month]
    value = ((first["end"] / first["cum_wallets"]) ** (1 / (last_month - first["t"])) - 1) * 100
    return value.rename(name).reset_index()


def growth_table(monthly: pd.DataFrame, clock: str) -> pd.DataFrame:
    """compound_growth_pct up to GROWTH_LAST_MONTH, plus one column per window k (k = 1 holds no growth)."""
    out = compound_growth(monthly, clock, GROWTH_LAST_MONTH, "compound_growth_pct")
    for k in list(WINDOWS)[1:]:
        out = out.merge(compound_growth(monthly, clock, k - 1, f"compound_growth_k{k}"), on="slug", how="outer")
    return out


def read_growth_dapps() -> pd.DataFrame:
    """First-user summary, with success_k3 as the group."""
    dapps = pd.read_csv(DATA / "dapp_growth_first_user_summary.csv")
    dapps["group"] = np.where(dapps["success_k3"] == 1, "Successful", "Not successful")
    return dapps


def read_growth_series(dapps: pd.DataFrame) -> pd.DataFrame:
    """Every observed month from the first user, on the log scale."""
    s = read_panel().merge(dapps[["slug", "months_deploy_to_first_user", "group"]], on="slug")
    s["t"] = s["months_since_launch"] - s["months_deploy_to_first_user"]
    s = s[s["t"] >= 0]
    return pd.DataFrame({"slug": s["slug"], "group": s["group"], "t": s["t"],
                         "log_cum": np.log(s["cum_wallets"])}).sort_values(["slug", "t"]).reset_index(drop=True)


# ---- growth curves ----

def log_logistic(log_L, log_r, t0, t):
    return log_L - np.logaddexp(0, -np.exp(log_r) * (t - t0))


def log_gompertz(log_L, log_r, t0, t):
    return log_L - np.exp(np.minimum(-np.exp(log_r) * (t - t0), 50))


def fit_curve(t: np.ndarray, y: np.ndarray, log_curve) -> dict:
    """Several starting points, keeping the best; L can sit up to 10x above the last observed value."""
    log_max = y.max()
    bounds = [(log_max - .5, log_max + np.log(MAX_L_MULTIPLE)), (MIN_LOG_R, MAX_LOG_R), (-24, t.max() + 12)]

    def loss(p):
        return np.sum((y - log_curve(p[0], p[1], p[2], t)) ** 2)

    best = None
    for log_L in log_max + np.array([0, 1]):
        for log_r in np.log([.1, .5, 1.5]):
            for t0 in (0, 3, 12):
                res = optimize.minimize(loss, [log_L, log_r, t0], method="L-BFGS-B", bounds=bounds)
                if best is None or res.fun < best.fun:
                    best = res
    p = best.x
    return {"L": np.exp(p[0]), "r": np.exp(p[1]), "t0": p[2], "rmse": np.sqrt(best.fun / len(t)),
            "n_months": len(t), "last_cum": np.exp(log_max), "converged": bool(best.success),
            "at_L_cap": p[0] > log_max + np.log(MAX_L_MULTIPLE) - 1e-3,
            "at_r_edge": p[1] < MIN_LOG_R + 1e-3 or p[1] > MAX_LOG_R - 1e-3}


def fit_all(series: pd.DataFrame, log_curve) -> pd.DataFrame:
    return pd.DataFrame([{"slug": slug, "group": group, **fit_curve(g["t"].to_numpy(float), g["log_cum"].to_numpy(),
                                                                    log_curve)}
                         for (slug, group), g in series.groupby(["slug", "group"])])


def compare_groups(data: pd.DataFrame, column: str, sample: str = "all DApps") -> pd.DataFrame:
    """Median and quartiles per group, with the Wilcoxon rank-sum p-value (normal approximation)."""
    d = data[["group", column]].dropna()
    a, b = (d.loc[d["group"] == g, column] for g in GROUPS)
    p = stats.mannwhitneyu(a, b, use_continuity=True, method="asymptotic").pvalue
    return pd.DataFrame([{"sample": sample, "measure": column, "p_value": p, "group": g, "n_dapps": len(v),
                          "median": v.median(), "q25": v.quantile(.25), "q75": v.quantile(.75)}
                         for g, v in zip(GROUPS, (a, b))])


# ---- output ----

def record(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Save a summary table to results/tables/<name>.csv and return it for display."""
    df.to_csv(TABLES / f"{name}.csv", index=False)
    return df


def setup_style() -> None:
    """A light, minimal look close to ggplot's theme_minimal, with one size for every figure."""
    plt.rcParams.update({
        "figure.figsize": FIGSIZE, "figure.constrained_layout.use": True,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.grid": True, "grid.color": "#EBEBEB", "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.spines.bottom": False,
        "xtick.major.size": 0, "ytick.major.size": 0,
        "xtick.color": "#4D4D4D", "ytick.color": "#4D4D4D",
        "axes.labelcolor": "#1A1A1A", "font.size": 10, "legend.frameon": False,
    })


def savefig(fig, name: str) -> None:
    fig.savefig(FIGURES / f"{name}.png", dpi=DPI)
    plt.close(fig)
