"""Charts for the modelling slides, in the presentation's palette.

Reads the result tables written by robust_eval.py, iterations.py and final_model.py and
writes PNGs to figures/deck/. Re-run after any model change, then rebuild the deck.

  python model/deck_charts.py
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import MODEL

OUT = MODEL / "figures" / "deck"
T = MODEL / "tables"
INK, MUTED, GRID = "#17191C", "#777B86", "#ECECEC"
GREY, ORANGE, BROWN, PEACH = "#A2A5AD", "#D08A62", "#5C2817", "#FCE4D6"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": GRID,
    "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
    "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 220,
})


def _save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  saved figures/deck/{name}")


def journey(points: list[tuple[str, float, str]], name="journey.png", ylabel="PR-AUC"):
    """points: (label, value, kind) with kind in {'old', 'step', 'best'}."""
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    x = np.arange(len(points))
    vals = [p[1] for p in points]
    cols = {"old": GREY, "step": ORANGE, "best": BROWN}
    ax.plot(x, vals, color=GRID, lw=2, zorder=1)
    for i, (lab, v, kind) in enumerate(points):
        ax.scatter(i, v, s=110, color=cols[kind], zorder=2)
        ax.annotate(f"{v:.2f}", (i, v), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=10.5, color=INK)
    ax.set_xticks(x, [p[0] for p in points], fontsize=9.5)
    ax.set_ylabel(ylabel)
    lo, hi = min(vals), max(vals)
    ax.set_ylim(lo - 0.08, hi + 0.08)
    ax.grid(axis="y", color=GRID)
    _save(fig, name)


def hbar(labels, values, kinds, name, xlabel, xlim=None, ref=None, ref_label=None, fmt="{:.2f}"):
    cols = {"old": GREY, "step": ORANGE, "best": BROWN, "neg": "#C9CBD1"}
    fig, ax = plt.subplots(figsize=(7.0, 0.36 * len(labels) + 0.9))
    y = np.arange(len(labels))[::-1]
    ax.barh(y, values, color=[cols[k] for k in kinds], height=0.68)
    for yi, v in zip(y, values):
        ax.text(v + 0.004, yi, fmt.format(v), va="center", fontsize=9.5, color=INK)
    ax.set_yticks(y, labels, fontsize=9.5)
    ax.set_xlabel(xlabel)
    if xlim:
        ax.set_xlim(*xlim)
    if ref is not None:
        ax.axvline(ref, color=MUTED, lw=1, ls="--")
        if ref_label:
            ax.text(ref, len(labels) - 0.35, ref_label, fontsize=8.5, color=MUTED, ha="center")
    ax.tick_params(axis="y", length=0)
    _save(fig, name)


def ceiling(name="ceiling.png"):
    windows = ["0-2\n(k=3)", "3-5", "5-7", "7-9"]
    auc, ap, acc = [0.87, 0.94, 0.97, 0.97], [0.62, 0.77, 0.87, 0.91], [0.87, 0.91, 0.94, 0.96]
    fig, ax = plt.subplots(figsize=(6.6, 3.5))
    x = np.arange(4)
    ax.plot(x, acc, marker="o", color=BROWN, lw=2.5, label="Accuracy")
    ax.plot(x, auc, marker="o", color=ORANGE, lw=2.5, label="ROC-AUC")
    ax.plot(x, ap, marker="o", color=GREY, lw=2.5, label="PR-AUC")
    ax.axhline(0.84, color=MUTED, ls="--", lw=1)
    ax.text(3.05, 0.84, "always say\n'fail' = 84%", fontsize=8.5, color=MUTED, va="center")
    ax.axhline(0.90, color=PEACH, lw=6, zorder=0)
    ax.text(3.05, 0.90, "90% target", fontsize=8.5, color=BROWN, va="center")
    for xs, v in zip(x, acc):
        ax.annotate(f"{v:.0%}", (xs, v), textcoords="offset points", xytext=(0, -16),
                    ha="center", fontsize=9.5, color=BROWN, fontweight="bold")
    ax.set_xticks(x, windows)
    ax.set_xlabel("Months of wallet data the 1-feature model sees")
    ax.set_ylim(0.55, 1.0)
    ax.set_xlim(-0.3, 3.6)
    ax.grid(axis="y", color=GRID)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    _save(fig, name)


def threshold_grid(k=3, models=None, name="grid_k3.png"):
    g = pd.read_csv(T / f"oof_threshold_grid_k{k}.csv")
    models = models or {"hgb": ("v1 boosted trees", GREY), "panel_ar": ("panel AR forecaster", ORANGE)}
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for m, (lab, col) in models.items():
        s = g[(g["model"] == m) & np.isclose(g["rel"], 0.25)].sort_values("abs_wallets")
        if len(s):
            ax.plot(s["abs_wallets"], s["ap"], marker="o", color=col, lw=2.5, label=lab)
    ax.set_xscale("log")
    ax.minorticks_off()
    ax.set_xticks([250, 500, 1000, 2500, 5000], ["250", "500", "1k", "2.5k", "5k"])
    ax.set_xlabel("Success cutoff: wallets at months 10-12 (and >= 25% of early peak)")
    ax.set_ylabel("PR-AUC")
    ax.grid(axis="y", color=GRID)
    ax.legend(frameon=False, fontsize=9)
    _save(fig, name)


def two_stage(rows: pd.DataFrame, name="two_stage.png"):
    """rows: policy, coverage, accuracy."""
    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    y = np.arange(len(rows))[::-1]
    cols = [GREY] + [ORANGE] * (len(rows) - 2) + [BROWN]
    ax.barh(y, rows["accuracy"], color=cols, height=0.6)
    for yi, (a, c) in zip(y, zip(rows["accuracy"], rows["coverage"])):
        ax.text(a + 0.003, yi, f"{a:.1%}  on {c:.0%} of apps", va="center", fontsize=9.5, color=INK)
    ax.set_yticks(y, rows["policy"], fontsize=9.5)
    ax.set_xlim(0.80, 1.0)
    ax.axvline(0.90, color=MUTED, ls="--", lw=1)
    ax.set_xlabel("Accuracy (unseen 2024 launches)")
    ax.tick_params(axis="y", length=0)
    _save(fig, name)


def journey_two_lines(name="journey.png"):
    """Grid-mean PR-AUC at each step of the journey, month 3 and month 6."""
    c3 = pd.read_csv(T / "oof_comparison_k3.csv").set_index("model")["ap_grid_mean"]
    c6 = pd.read_csv(T / "oof_comparison_k6.csv").set_index("model")["ap_grid_mean"]
    i3 = pd.read_csv(T / "iterations_k3.csv").set_index("model")
    i6 = pd.read_csv(T / "iterations_k6.csv").set_index("model")
    new_data = ["hgb_soft_wallet_hist", "hgb_soft_compact_hist", "rf_soft_hist", "ar_resid_hgb_hist",
                "ar_resid_ridge_hist", "hgb_soft_wallet_token", "hgb_soft_wallet_tvl"]

    def best(i, c, names):
        vals = [i.loc[n, "ap_grid_mean"] for n in names if n in i.index]
        vals += [c[n] for n in names if n in c.index]
        return max(vals)

    steps = ["v1 trees", "soft\nlabels", "+ wallet\ndata", "pooled\nAR", "v2\nblend",
             "+ TVL, token,\nuser data", "v3\nensemble"]
    v3 = [i3.loc["hgb_v1", "ap_grid_mean"], c3["hgb_soft"], c3["hgb_soft_wallet"],
          i3.loc["panel_ar", "ap_grid_mean"], i3.loc["final_blend_v1", "ap_grid_mean"],
          best(i3, c3, new_data), i3.loc["ens_nested", "ap_grid_mean"]]
    v6 = [i6.loc["hgb_v1", "ap_grid_mean"], c6["hgb_soft"], c6["hgb_soft_wallet"],
          i6.loc["panel_ar", "ap_grid_mean"], i6.loc["final_blend_v1", "ap_grid_mean"],
          best(i6, c6, new_data), i6.loc["ens_nested", "ap_grid_mean"]]
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    x = np.arange(len(steps))
    for vals, col, lab, off in ((v6, BROWN, "6 months seen", 9), (v3, ORANGE, "3 months seen", -15)):
        ax.plot(x, vals, marker="o", color=col, lw=2.5, label=lab, ms=7)
        for xi, v in zip(x, vals):
            ax.annotate(f"{v:.2f}", (xi, v), textcoords="offset points", xytext=(0, off),
                        ha="center", fontsize=9, color=col)
    ax.scatter([0], [0.649], marker="D", color=GREY, s=50, zorder=3)
    ax.annotate("0.65: v1 on one lucky\nholdout split", (0, 0.649), textcoords="offset points",
                xytext=(10, 4), fontsize=8.5, color=MUTED)
    ax.set_xticks(x, steps, fontsize=9)
    ax.set_ylabel("Grid-mean PR-AUC")
    ax.set_ylim(0.50, 0.78)
    ax.grid(axis="y", color=GRID)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    _save(fig, name)
    return dict(zip(steps, zip(v3, v6)))


FAMILIES = [
    ("1-feature baseline", ["szabo_huberman"]),
    ("v1 boosted trees", ["hgb_v1"]),
    ("Spline GAM (logistic)", ["spline_gam_compact"]),
    ("Random forest / extra trees", ["rf_soft", "extratrees_soft", "rf_soft_hist"]),
    ("Soft-label boosted trees", ["hgb_soft_wallet", "hgb_soft_monotone", "hgb_soft_shallow",
                                  "hgb_soft_compact", "hgb_soft_wallet_hist", "hgb_soft_compact_hist"]),
    ("Direct regression", ["reg_ridge", "reg_hgb", "reg_ridge_compact", "reg_ridge_hist"]),
    ("AR + feature correction", ["ar_resid_ridge", "ar_resid_hgb", "ar_resid_ridge_hist",
                                 "ar_resid_hgb_hist"]),
    ("Pooled linear AR", ["panel_ar", "panel_ridge", "panel_ridge_hetero", "panel_ridge_local",
                          "panel_ridge_lags"]),
    ("Boosted panel forecaster", ["panel_hgb_mean", "panel_hgb_local", "panel_hgb_lags"]),
    ("v3 nested ensemble", ["ens_nested"]),
]


def families(name="families.png"):
    i3 = pd.read_csv(T / "iterations_k3.csv").set_index("model")["ap_grid_mean"]
    i6 = pd.read_csv(T / "iterations_k6.csv").set_index("model")["ap_grid_mean"]
    labs = [f for f, _ in FAMILIES]
    b3 = [max(i3[m] for m in ms if m in i3) for _, ms in FAMILIES]
    b6 = [max(i6[m] for m in ms if m in i6) for _, ms in FAMILIES]
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    y = np.arange(len(labs))[::-1]
    h = 0.38
    ax.barh(y + h / 2, b6, h, color=BROWN, label="6 months seen")
    ax.barh(y - h / 2, b3, h, color=ORANGE, label="3 months seen")
    for yi, a, b in zip(y, b3, b6):
        ax.text(b + 0.004, yi + h / 2, f"{b:.2f}", va="center", fontsize=8.5, color=INK)
        ax.text(a + 0.004, yi - h / 2, f"{a:.2f}", va="center", fontsize=8.5, color=INK)
    ax.set_yticks(y, labs, fontsize=9.5)
    ax.set_xlim(0.45, 0.78)
    ax.set_xlabel("Grid-mean PR-AUC (best variant in each family)")
    ax.tick_params(axis="y", length=0)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    _save(fig, name)


def two_stage_chart(name="two_stage.png"):
    ts = pd.read_csv(T / "final_two_stage.csv")
    ts = ts[ts["split"] == "test_2024_unseen"]
    lab = {"always say 'fail'": "Always say 'fail'", "month 3 only": "Month 3 only",
           "month 6 only": "Month 6 only",
           "month 3, then month 6 for the uncertain": "Month 3, then\nmonth 6 if unsure"}
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    y = np.arange(len(ts))[::-1]
    cols = [GREY, ORANGE, ORANGE, BROWN]
    ax.barh(y, ts["confident_accuracy"], color=cols, height=0.6)
    for yi, (_, r) in zip(y, ts.iterrows()):
        ax.text(r["confident_accuracy"] + 0.002, yi,
                f"{r['confident_accuracy']:.1%} on {r['coverage']:.0%} of apps; "
                f"{int(r['successes_caught'])}/{int(r['n_successes'])} successes found",
                va="center", fontsize=8.5, color=INK)
    ax.set_yticks(y, [lab[p] for p in ts["policy"]], fontsize=9.5)
    ax.set_xlim(0.85, 1.06)
    ax.set_xticks([0.85, 0.90, 0.95, 1.0], ["85%", "90%", "95%", "100%"])
    ax.set_xlabel("Accuracy of confident calls, unseen 2024 launches")
    ax.tick_params(axis="y", length=0)
    _save(fig, name)


def main():
    ceiling()
    threshold_grid(3, {"hgb": ("v1 boosted trees", GREY), "szabo_huberman": ("1-feature baseline", ORANGE),
                       "panel_ar": ("panel AR forecaster", BROWN)})
    print(journey_two_lines())
    families()
    two_stage_chart()


if __name__ == "__main__":
    main()
