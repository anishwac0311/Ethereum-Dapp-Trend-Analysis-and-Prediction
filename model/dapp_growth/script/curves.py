"""Growth speed vs size: compound growth, then one growth curve per DApp (first-user clock).

Each curve on cum_wallets has a final size L, a speed r, and a month of fastest growth t0, fitted on the log scale
on every observed month from the first user. We fit a logistic and a Gompertz curve, keep the one that fits better
(Gompertz) as the main result, and keep the other as a check.
"""
from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

from common import (DATA, EARLY_MONTHS, GROUP_COLOURS, GROUPS, compare_groups, fit_all, log_gompertz, log_logistic,
                    record, savefig)

MAIN = "Gompertz"
CHECK = "Logistic"
MARKED_MONTHS = [6, 24]
PLOT_MONTHS = 36
POOR_FIT_RMSE = 0.5   # log-scale RMSE above this (curve off by more than ~1.65x on average) is a poor fit
EARLY = 3             # months 0-2
LATE = 6              # last six observed months
FIT_COLOURS = {"Good fit": "#008A7E", "Poor fit": "#8B5CF6"}
# Months between 10% and 90% of L; the constant depends on the curve
RISE = {"Logistic": np.log(81), "Gompertz": np.log(np.log(.1) / np.log(.9))}
CURVES = {"Logistic": log_logistic, "Gompertz": log_gompertz}


def curve_values(name: str, p: pd.Series, t: np.ndarray) -> np.ndarray:
    """Cumulative wallets from a fitted curve's L, r and t0."""
    return np.exp(CURVES[name](np.log(p["L"]), np.log(p["r"]), p["t0"], t))


def log_axis(ax, title: str) -> None:
    ax.set_yscale("log")
    ax.yaxis.set_minor_locator(plt.NullLocator())
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set(xlim=(0, PLOT_MONTHS), xlabel="Months since first user", ylabel="Cumulative wallets (log scale)",
           title=title)
    ax.title.set(fontsize=9, color="#4D4D4D")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)


def observed_median(series: pd.DataFrame, slugs) -> pd.DataFrame:
    """Median cumulative wallets per month while at least half the DApps are still observed."""
    obs = (series[series["slug"].isin(slugs) & (series["t"] <= PLOT_MONTHS)]
           .assign(cum=lambda d: np.exp(d["log_cum"])).groupby("t")["cum"].agg(["median", "size"]))
    return obs[obs["size"] >= obs["size"].iloc[0] / 2]


def compound(dapps: pd.DataFrame) -> None:
    """Compound monthly growth before the outcome months, plus shorter windows and the timing of growth."""
    columns = ["compound_growth_pct", "compound_growth_k3", "compound_growth_k6", "months_to_half_peak_cum"]
    record(pd.concat([compare_groups(dapps, c) for c in columns]), "compound_growth_by_group")


def robustness(fits: pd.DataFrame, early: pd.DataFrame, dapps: pd.DataFrame, name: str) -> None:
    """Is the speed result driven by size, poor fits, or the window? r compared under each check."""
    by_group = pd.concat([compare_groups(fits, c) for c in ["L", "r", "t0", "rise_months"]])
    checks = pd.concat([compare_groups(fits[fits["L"] >= 5000], "r", "L at least 5,000"),
                        compare_groups(fits[fits["rmse"] <= POOR_FIT_RMSE], "r", "good fits only"),
                        compare_groups(early, "r", f"first {EARLY_MONTHS} months only")])
    record(pd.concat([by_group, checks]), name)

    adjusted = smf.ols("np.log(r) ~ C(group, levels=GROUPS) + np.log(L)", data=fits).fit()
    by_k = []
    for k in (1, 3, 6):
        labelled = fits[["slug", "r"]].merge(dapps[["slug", f"success_k{k}"]], on="slug")
        labelled["group"] = np.where(labelled[f"success_k{k}"] == 1, "Successful", "Not successful")
        test = compare_groups(labelled, "r")
        by_k.append({"k": k, "n_success": int(labelled[f"success_k{k}"].sum()),
                     "r_success": test["median"].iloc[1], "r_other": test["median"].iloc[0],
                     "p_value": test["p_value"].iloc[0]})
    out = pd.DataFrame(by_k)
    out["success_coef_given_L"] = adjusted.params.iloc[1]
    out["success_p_given_L"] = adjusted.pvalues.iloc[1]
    record(out, f"{name}_by_k")


def model_choice(fits: dict) -> None:
    """Which curve fits better? Both have three parameters, so AIC difference = 2 n log(RMSE_g / RMSE_l)."""
    paired = fits["Logistic"][["slug", "group", "n_months", "rmse"]].merge(
        fits["Gompertz"][["slug", "rmse"]], on="slug", suffixes=("_logistic", "_gompertz"))
    paired["aic_difference"] = 2 * paired["n_months"] * np.log(paired["rmse_gompertz"] / paired["rmse_logistic"])
    quality = paired.groupby("group").agg(
        n_dapps=("slug", "size"),
        rmse_logistic=("rmse_logistic", "median"), rmse_gompertz=("rmse_gompertz", "median"),
        poor_fits_logistic=("rmse_logistic", lambda r: int((r > POOR_FIT_RMSE).sum())),
        poor_fits_gompertz=("rmse_gompertz", lambda r: int((r > POOR_FIT_RMSE).sum())),
        favours_gompertz=("aic_difference", lambda d: int((d < -2).sum())),
        favours_logistic=("aic_difference", lambda d: int((d > 2).sum())))
    record(quality.reset_index().sort_values("group", ascending=False), "curve_fit_quality")

    # One bar per group: share of DApps each curve fits better (AIC difference beyond 2), or no clear winner
    fig, ax = plt.subplots()
    parts = [("Gompertz fits better", "#1F2937", lambda d: d < -2), ("No clear difference", "#D1D5DB", lambda d: abs(d) <= 2),
             ("Logistic fits better", "#7AA5D2", lambda d: d > 2)]
    order = list(reversed(GROUPS))
    for i, g in enumerate(order):
        diff = paired.loc[paired["group"] == g, "aic_difference"]
        left = 0
        for label, colour, rule in parts:
            share = rule(diff).mean()
            ax.barh(i, share, left=left, color=colour, height=.5, label=label if i == 0 else None)
            if share > .06:
                ax.text(left + share / 2, i, f"{share:.0%}", ha="center", va="center", fontsize=10,
                        color="white" if colour == "#1F2937" else "#1F2937")
            left += share
    ax.set_yticks(range(len(order)), [f"{g}\n({(paired['group'] == g).sum()} DApps)" for g in order])
    ax.invert_yaxis()
    ax.set(xlim=(0, 1), xlabel="Share of DApps")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.grid(False)
    ax.set_title("Which curve fits each DApp better (AIC)", fontsize=9, color="#4D4D4D")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    savefig(fig, "model_choice")


def l_by_month_figure(fits: pd.DataFrame, series: pd.DataFrame) -> None:
    """Good fits only: curve from each group's median L, r, t0, rising toward its ceiling L; points are observed."""
    good = fits[fits["rmse"] <= POOR_FIT_RMSE]
    t = np.arange(0, PLOT_MONTHS + .25, .25)
    fig, ax = plt.subplots()
    for m in MARKED_MONTHS:
        ax.axvline(m, ls="--", color="#9CA3AF", lw=0.8)
    for g in reversed(GROUPS):
        sub = good[good["group"] == g]
        p = sub[["L", "r", "t0"]].median()
        ax.axhline(p["L"], ls=":", color=GROUP_COLOURS[g], lw=1)
        ax.annotate(f"L = {p['L']:,.0f}", (PLOT_MONTHS, p["L"]), xytext=(-4, 4), textcoords="offset points",
                    ha="right", va="bottom", fontsize=9, color=GROUP_COLOURS[g])
        ax.plot(t, curve_values(MAIN, p, t), color=GROUP_COLOURS[g], lw=1.6, label=f"{g} ({len(sub)})")
        obs = observed_median(series, sub["slug"])
        ax.scatter(obs.index, obs["median"], s=14, color=GROUP_COLOURS[g], alpha=.7, lw=0)
    log_axis(ax, f"Good {MAIN} fits only. Line: curve from median L, r, t0. Dotted: ceiling L. Points: observed median.")
    savefig(fig, "L_by_month")


def fit_check_figure(fits: dict, series: pd.DataFrame) -> None:
    """Successful DApps only: the three typical main-curve fits and the three worst, with both curves."""
    successful = fits[MAIN][fits[MAIN]["group"] == "Successful"].sort_values("rmse").reset_index(drop=True)
    middle = math.ceil(len(successful) / 2)
    chosen = [("Typical fit", s) for s in successful["slug"].iloc[middle - 2:middle + 1]] + \
             [("Worst fit", s) for s in successful["slug"].iloc[-3:]]

    fig, axes = plt.subplots(2, 3)
    for ax, (label, slug) in zip(axes.flat, chosen):
        obs = series[series["slug"] == slug]
        t = obs["t"].to_numpy(float)
        ax.scatter(t, np.exp(obs["log_cum"]), s=6, color="#9CA3AF", lw=0)
        for name, colour, ls in [(MAIN, "#1F2937", "-"), (CHECK, GROUP_COLOURS["Successful"], "--")]:
            p = fits[name][fits[name]["slug"] == slug].iloc[0]
            ax.plot(t, curve_values(name, p, t), color=colour, ls=ls, lw=1.2, label=name)
        ax.set_title(f"{label}\n{slug}", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v / 1e3:,.0f}K" if v >= 1e3 else f"{v:,.0f}"))
    fig.supxlabel("Months since first user", fontsize=9)
    fig.supylabel("Cumulative wallets", fontsize=9)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncol=2)
    savefig(fig, "fit_check")


def fit_quality(fits: pd.DataFrame, series: pd.DataFrame) -> None:
    """Good vs poor main-curve fits: how they start, where the curve misses, and how fast they rise."""
    fits = fits.assign(fit=np.where(fits["rmse"] > POOR_FIT_RMSE, "Poor fit", "Good fit"))
    rows = []
    for slug, g in series.merge(fits[["slug", "L", "r", "t0"]], on="slug").groupby("slug"):
        y, t = g["log_cum"].to_numpy(), g["t"].to_numpy(float)
        gap = y - np.log(curve_values(MAIN, g.iloc[0], t))   # data minus curve, log scale
        rise = y[-1] - y[0]
        rows.append({"slug": slug, "wallets_m0": np.exp(y[0]),
                     "early_growth_share": (y[min(EARLY, len(y)) - 1] - y[0]) / rise if rise > 0 else np.nan,
                     "early_gap": gap[:EARLY].mean(), "late_gap": gap[-LATE:].mean()})
    shape = fits.merge(pd.DataFrame(rows), on="slug")

    table = (shape.groupby(["group", "fit"])
             .agg(n_dapps=("slug", "size"), wallets_m0=("wallets_m0", "median"),
                  early_growth_share=("early_growth_share", "median"), early_gap=("early_gap", "median"),
                  late_gap=("late_gap", "median"), L=("L", "median"), r=("r", "median"),
                  rise_months=("rise_months", "median"))
             .reset_index().sort_values(["group", "fit"], ascending=[False, True]))
    good = shape[(shape["group"] == "Successful") & (shape["fit"] == "Good fit")]["r"]
    table["r_p_vs_successful_good_fit"] = [
        stats.mannwhitneyu(good, shape[(shape["group"] == g) & (shape["fit"] == f)]["r"], use_continuity=True,
                           method="asymptotic").pvalue if not (g == "Successful" and f == "Good fit") else np.nan
        for g, f in zip(table["group"], table["fit"])]
    record(table, "fit_quality_by_group")

    # Shape: successful DApps only, observed median and the curve from median L, r, t0, for good and poor fits
    t = np.arange(0, PLOT_MONTHS + .25, .25)
    fig, ax = plt.subplots()
    ax.axvspan(0, EARLY - 1, color="#F3F4F6", lw=0)
    ax.text((EARLY - 1) / 2, 0.97, "months\n0-2", transform=ax.get_xaxis_transform(), ha="center", va="top",
            fontsize=8, color="#6B7280")
    successful = shape[shape["group"] == "Successful"]
    for fit in FIT_COLOURS:
        sub = successful[successful["fit"] == fit]
        ax.plot(t, curve_values(MAIN, sub[["L", "r", "t0"]].median(), t), color=FIT_COLOURS[fit], lw=1.6,
                label=f"{fit} ({len(sub)})")
        obs = observed_median(series, sub["slug"])
        ax.scatter(obs.index, obs["median"], s=14, color=FIT_COLOURS[fit], alpha=.7, lw=0)
    log_axis(ax, f"Successful DApps only. Line: {MAIN} curve from median L, r, t0. Points: observed median.")
    savefig(fig, "fit_quality_curves")


def good_fit_comparison(fits: pd.DataFrame, series: pd.DataFrame) -> None:
    """Successful vs not, among good fits only: where do the fitted parameters differ?"""
    m0 = np.exp(series[series["t"] == 0].set_index("slug")["log_cum"]).rename("wallets_m0")
    good = fits[fits["rmse"] <= POOR_FIT_RMSE].join(m0, on="slug")
    measures = {"wallets_m0": "Wallets at month 0", "L": "Ceiling L (wallets)", "t0": "Month of fastest growth t0",
                "rise_months": "Months to rise 10% to 90% of L"}
    table = pd.concat([compare_groups(good, c, "good fits") for c in measures])
    # Is the longer rise just a higher ceiling? Speed compared at the same L
    adjusted = smf.ols("np.log(r) ~ C(group, levels=GROUPS) + np.log(L)", data=good).fit()
    table = pd.concat([table, pd.DataFrame([{"sample": "good fits, same L", "measure": "log r, success effect",
                                             "p_value": adjusted.pvalues.iloc[1], "median": adjusted.params.iloc[1]}])])
    record(table, "good_fit_parameters")

    order = list(reversed(GROUPS))

    def boxes(ax, col, title, log):
        """One box per group, successful on the left, with the median written beside it."""
        values = [good.loc[good["group"] == g, col].clip(lower=.5 if log else None) for g in order]
        box = ax.boxplot(values, widths=.5, patch_artist=True, showfliers=False,
                         medianprops={"color": "#1F2937", "lw": 1.4})
        for patch, g in zip(box["boxes"], order):
            patch.set(facecolor=GROUP_COLOURS[g], alpha=.35, edgecolor=GROUP_COLOURS[g])
        for i, v in enumerate(values, start=1):
            m = v.median()
            ax.annotate(f"{m:,.0f}" if m >= 10 else f"{m:.1f}", (i, m), xytext=(26, 0), textcoords="offset points",
                        va="center", fontsize=8, color="#374151")
        if log:
            ax.set_yscale("log")
            ax.yaxis.set_minor_locator(plt.NullLocator())
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 1 else f"{v:g}"))
        ax.set_xticks([1, 2], [f"{g}\n({(good['group'] == g).sum()})" for g in order], fontsize=8)
        ax.set_title(title, fontsize=9)
        ax.tick_params(axis="y", labelsize=7)

    # Start, ceiling and peak month
    fig, axes = plt.subplots(1, 3)
    for ax, (col, title, log) in zip(axes, [("wallets_m0", "Wallets at month 0", True),
                                            ("L", "Ceiling L (wallets)", True),
                                            ("t0", "Month of fastest growth t0", False)]):
        boxes(ax, col, title, log)
    fig.suptitle(f"Good {MAIN} fits only. Box: middle half of DApps; line and number: median.", fontsize=9,
                 color="#4D4D4D")
    savefig(fig, "good_fit_parameters")

    # Speed: months to rise, and r against L (same line for both groups = same speed at the same ceiling)
    fig, (left, right) = plt.subplots(1, 2, width_ratios=[1, 1.6])
    boxes(left, "rise_months", "Months to rise 10% to 90% of L", True)
    for g in order:
        sub = good[good["group"] == g]
        right.scatter(sub["L"], sub["r"], s=10 if g == "Not successful" else 18, color=GROUP_COLOURS[g],
                      alpha=.45 if g == "Not successful" else .8, lw=0, label=f"{g} ({len(sub)})")
        line = smf.ols("np.log(r) ~ np.log(L)", data=sub).fit()
        x = np.geomspace(sub["L"].min(), sub["L"].max(), 50)
        right.plot(x, np.exp(line.params.iloc[0] + line.params.iloc[1] * np.log(x)), color=GROUP_COLOURS[g], lw=1.6)
    right.set(xscale="log", yscale="log", xlabel="Ceiling L (wallets)", ylabel="Speed r")
    right.set_title(f"r vs L; lines: trend per group (same ceiling: p = {adjusted.pvalues.iloc[1]:.2f})", fontsize=9)
    for axis in (right.xaxis, right.yaxis):
        axis.set_minor_locator(plt.NullLocator())
        axis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 1 else f"{v:g}"))
    right.tick_params(labelsize=7)
    right.legend(fontsize=8, loc="lower left")
    fig.suptitle(f"Good {MAIN} fits only.", fontsize=9, color="#4D4D4D")
    savefig(fig, "good_fit_speed")

    # Speed over time: monthly growth of cumulative wallets, successful vs not, good fits only
    fig, ax = plt.subplots()
    t = np.arange(1, PLOT_MONTHS + .25, .25)
    for g in order:
        sub = good[good["group"] == g]
        p = sub[["L", "r", "t0"]].median()
        # Gompertz: d log(cum) / dt = r exp(-r (t - t0))
        speed = np.expm1(p["r"] * np.exp(-p["r"] * (t - p["t0"]))) * 100
        ax.plot(t, speed, color=GROUP_COLOURS[g], lw=1.6, label=f"{g} ({len(sub)})")
        growth = (series[series["slug"].isin(sub["slug"])].sort_values(["slug", "t"])
                  .assign(growth=lambda d: np.expm1(d.groupby("slug")["log_cum"].diff()) * 100))
        obs = growth[(growth["t"] >= 1) & (growth["t"] <= PLOT_MONTHS)].groupby("t")["growth"].agg(["median", "size"])
        obs = obs[obs["size"] >= obs["size"].iloc[0] / 2]
        ax.scatter(obs.index, obs["median"].clip(lower=.1), s=14, color=GROUP_COLOURS[g], alpha=.7, lw=0)
    ax.set_yscale("log")
    ax.yaxis.set_minor_locator(plt.NullLocator())
    # No growth (0%) cannot sit on a log axis, so it is drawn at the 0.1% floor
    ax.set_ylim(.07, 300)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(
        lambda v, _: "≤0.1%" if v <= .1 else (f"{v:,.0f}%" if v >= 1 else f"{v:g}%")))
    ax.set(xlim=(0, PLOT_MONTHS), xlabel="Months since first user",
           ylabel="Monthly growth of cumulative wallets (log scale)",
           title=f"Good {MAIN} fits only. Line: growth speed set by the median r. Points: observed median.")
    ax.title.set(fontsize=9, color="#4D4D4D")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    savefig(fig, "r_by_month")


def run(dapps: pd.DataFrame, series: pd.DataFrame) -> None:
    compound(dapps)

    fits = {}
    for name, curve in CURVES.items():
        f = fit_all(series, curve)
        f["rise_months"] = RISE[name] / f["r"]
        f.to_csv(DATA / f"dapp_growth_curves_{name.lower()}.csv", index=False)
        early = fit_all(series[series["t"] <= EARLY_MONTHS], curve)
        early["rise_months"] = RISE[name] / early["r"]
        robustness(f, early, dapps, f"{name.lower()}_by_group")
        fits[name] = f

    model_choice(fits)
    l_by_month_figure(fits[MAIN], series)
    fit_check_figure(fits, series)
    fit_quality(fits[MAIN], series)
    good_fit_comparison(fits[MAIN], series)

    show = pd.read_csv(DATA.parent / "results" / "tables" / f"{MAIN.lower()}_by_group.csv")
    print(show[show["sample"] == "all DApps"][["measure", "group", "median", "p_value"]].to_string(index=False))
