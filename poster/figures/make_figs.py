"""Simple poster figures for Q2, Q3 and Q5.

Run from the repo root:  python3 poster/figures/make_figs.py
Writes 300-dpi PNGs next to this script, sized for the poster's
figure slots (about 5 x 2.6 in each).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

BLUE = "#0066A9"   # poster template blue: the series that carries the message
GREY = "#9AA4AE"   # comparison series
TEXT = "#1A1A1A"
MUTED = "#555555"
GRID = "#E3E7EB"

plt.rcParams.update({
    "font.family": "Georgia",
    "font.size": 12,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": TEXT,
    "axes.labelsize": 12,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})
SIZE = (5.2, 2.7)


def pct(ax):
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))


# ---------- Q2: wallets by month since launch, lasting vs. flash ----------
def q2():
    traj = pd.read_csv(ROOT / "eda/tables/03_trajectories_normalized.csv")
    clus = pd.read_csv(ROOT / "eda/tables/trajectory_clusters.csv")[["slug", "cluster_name"]]
    d = traj.merge(clus, on="slug")
    # Two groups, as on the poster: flash_fade (115) vs. slow build (50 + 5 sparse = 55)
    d["group"] = d["cluster_name"].map(lambda c: "flash" if c == "flash_fade" else "slow")
    months = [f"m{i}" for i in range(24)]
    med = d.groupby("group")[months].median().T
    n = d["group"].value_counts()
    x = range(24)

    fig, ax = plt.subplots(figsize=SIZE)
    ax.plot(x, med["slow"], color=GREY, lw=2.4)
    ax.plot(x, med["flash"], color=BLUE, lw=2.8)
    ax.text(23.3, med["slow"].iloc[-1], f"Slow build\n({n['slow']} apps)", color=MUTED,
            va="center", fontsize=11)
    ax.text(23.3, med["flash"].iloc[-1], f"Flash and fade\n({n['flash']} apps, 68%)", color=BLUE,
            va="center", fontsize=11, fontweight="bold")
    ax.set_xlim(0, 23)
    ax.set_ylim(0, 0.7)
    ax.set_xticks([0, 3, 6, 12, 18, 23])
    ax.set_xlabel("Months since launch")
    ax.set_ylabel("Wallets, share of\nown peak (median)")
    pct(ax)
    fig.savefig(OUT / "q2_wallets_since_launch.png")
    plt.close(fig)
    return med


# ---------- Q3: top-10 share of wallets over time ----------
def q3():
    cm = pd.read_csv(ROOT / "dapp_data_v2/concentration_month.csv", parse_dates=["month"])
    e = cm[(cm.scope == "ecosystem") & (cm.metric == "active_wallets")].sort_values("month")

    fig, ax = plt.subplots(figsize=SIZE)
    ax.axhspan(0.70, 0.80, color=BLUE, alpha=0.10, lw=0)
    ax.plot(e["month"], e["top10_share"], color=BLUE, lw=2.6)
    ax.text(e["month"].iloc[-1], 0.75, " 70–80%\n band", color=BLUE, va="center",
            fontsize=11, fontweight="bold")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Top-10 apps’ share\nof active wallets")
    pct(ax)
    fig.savefig(OUT / "q3_top10_share.png")
    plt.close(fig)
    return e["top10_share"]


# ---------- Q5: retention curve ----------
def q5():
    r = pd.read_csv(ROOT / "dapp_data_v2/cohort_retention.csv")
    g = r.groupby("months_since")[["retained", "cohort_size"]].sum()
    rate = (g["retained"] / g["cohort_size"]).loc[1:24]

    fig, ax = plt.subplots(figsize=SIZE)
    ax.plot(rate.index, rate.values, color=BLUE, lw=2.8)
    for m in (1, 12):
        v = rate.loc[m]
        ax.scatter([m], [v], color=BLUE, s=36, zorder=3)
        ax.annotate(f"{v:.0%} after {m} {'month' if m == 1 else 'months'}",
                    (m, v), xytext=(10, 6), textcoords="offset points",
                    color=BLUE, fontsize=11, fontweight="bold")
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 0.2)
    ax.set_xticks([1, 3, 6, 12, 18, 24])
    ax.set_xlabel("Months since first use")
    ax.set_ylabel("Wallets that\ncome back")
    pct(ax)
    fig.savefig(OUT / "q5_retention_curve.png")
    plt.close(fig)
    return rate


if __name__ == "__main__":
    med = q2()
    top = q3()
    rate = q5()
    print("Q2 flash median: peak", med["flash"].max() , "at month", med["flash"].idxmax(),
          "| month 23:", med["flash"].iloc[-1] )
    print("Q3 top-10 share: min", top.min() , "max", top.max() ,
          "| share of months in 70-80%:", ((top >= 0.70) & (top <= 0.80)).mean() )
    print("Q5 retention: month 1", rate.loc[1] , "| month 12", rate.loc[12] )
