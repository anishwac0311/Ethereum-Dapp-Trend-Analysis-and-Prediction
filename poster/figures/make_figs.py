"""Poster figures: Q2, Q3, Q5, press before launch, and feature weights.

Run from the repo root:  python3 poster/figures/make_figs.py

Every figure shares one style so they sit together on the poster:
- same canvas: 6 x 3.4 in at 300 dpi (1800 x 1020 px), same plot margins
- same colours: template blue for the series that carries the message,
  grey for the comparison (its text labels use darker grey so they stay readable)
- same type: Georgia; ticks 11 pt, axis titles 12 pt, data labels 11 pt bold
- every chart has an x and a y title that names the measure and its unit
- series are named on the right edge of the plot, never in a boxed legend
"""
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

# ---- shared style -----------------------------------------------------------
BLUE = "#0066A9"   # poster template blue: the series that carries the message
GREY = "#9AA4AE"   # comparison series
TEXT = "#1A1A1A"
MUTED = "#555555"
GRID = "#E3E7EB"

FIGSIZE = (6.0, 3.4)
MARGINS = dict(left=0.20, right=0.78, bottom=0.22, top=0.90)
LABEL = dict(fontsize=11, fontweight="bold")

plt.rcParams.update({
    "font.family": "Georgia",
    "font.size": 11,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": TEXT,
    "axes.labelsize": 12,
    "axes.labelpad": 8,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "lines.linewidth": 2.6,
    "savefig.dpi": 300,
    "savefig.facecolor": "white",
})


def new_fig():
    fig, ax = plt.subplots(figsize=FIGSIZE)
    fig.subplots_adjust(**MARGINS)
    return fig, ax


def save(fig, name):
    fig.savefig(OUT / name)   # fixed canvas, no tight crop, so every PNG is the same size
    plt.close(fig)


def pct_axis(axis):
    axis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))


def end_label(ax, x, y, text, color):
    """Name a series just right of the plot area."""
    ax.annotate(text, (x, y), xytext=(8, 0), textcoords="offset points",
                va="center", ha="left", color=color, annotation_clip=False, **LABEL)


# ---- Q2: wallets by month since launch, lasting vs. flash -------------------
def q2():
    traj = pd.read_csv(ROOT / "eda/tables/03_trajectories_normalized.csv")
    clus = pd.read_csv(ROOT / "eda/tables/trajectory_clusters.csv")[["slug", "cluster_name"]]
    d = traj.merge(clus, on="slug")
    # Two groups, as on the poster: flash_fade (115) vs. slow build (50 + 5 sparse = 55)
    d["group"] = d["cluster_name"].map(lambda c: "flash" if c == "flash_fade" else "slow")
    months = [f"m{i}" for i in range(24)]
    med = d.groupby("group")[months].median().T
    med.index = range(24)
    n = d["group"].value_counts()

    fig, ax = new_fig()
    ax.plot(med.index, med["slow"], color=GREY)
    ax.plot(med.index, med["flash"], color=BLUE)
    end_label(ax, 23, med["slow"].iloc[-1], f"Slow build\n{n['slow']} apps", MUTED)
    end_label(ax, 23, med["flash"].iloc[-1], f"Flash and fade\n{n['flash']} apps (68%)", BLUE)
    ax.set_xlim(0, 23)
    ax.set_ylim(0, 0.7)
    ax.set_xticks([0, 3, 6, 12, 18, 23])
    ax.set_xlabel("Months since launch")
    ax.set_ylabel("Active wallets\n(% of the app’s own peak)")
    pct_axis(ax.yaxis)
    save(fig, "q2_wallets_since_launch.png")
    return med


# ---- Q3: top-10 share of wallets over time ----------------------------------
def q3():
    cm = pd.read_csv(ROOT / "dapp_data_v2/concentration_month.csv", parse_dates=["month"])
    e = cm[(cm.scope == "ecosystem") & (cm.metric == "active_wallets")].sort_values("month")

    fig, ax = new_fig()
    ax.axhspan(0.70, 0.80, color=BLUE, alpha=0.10, lw=0)
    ax.plot(e["month"], e["top10_share"], color=BLUE)
    end_label(ax, e["month"].iloc[-1], 0.75, "70–80%\nband", BLUE)
    ax.set_xlim(e["month"].iloc[0], e["month"].iloc[-1])
    ax.set_ylim(0, 1)
    ax.set_xlabel("Calendar month")
    ax.set_ylabel("Active wallets in\nthe top 10 apps (%)")
    pct_axis(ax.yaxis)
    save(fig, "q3_top10_share.png")
    return e["top10_share"]


# ---- Q5: retention curve ----------------------------------------------------
def q5():
    r = pd.read_csv(ROOT / "dapp_data_v2/cohort_retention.csv")
    g = r.groupby("months_since")[["retained", "cohort_size"]].sum()
    rate = (g["retained"] / g["cohort_size"]).loc[1:24]

    fig, ax = new_fig()
    ax.plot(rate.index, rate.values, color=BLUE)
    for m in (1, 12):
        v = rate.loc[m]
        ax.scatter([m], [v], color=BLUE, s=36, zorder=3)
        ax.annotate(f"{v:.0%} after {m} month{'s' if m > 1 else ''}", (m, v),
                    xytext=(10, 6), textcoords="offset points", color=BLUE, **LABEL)
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 0.2)
    ax.set_xticks([1, 3, 6, 12, 18, 24])
    ax.set_xlabel("Months since a wallet’s first use")
    ax.set_ylabel("Wallets that come\nback (%)")
    pct_axis(ax.yaxis)
    save(fig, "q5_retention_curve.png")
    return rate


# ---- Off-chain: success rate with vs. without press before launch -----------
def press():
    sys.path.insert(0, str(ROOT / "model"))
    from labels import build_labels  # team label code; v2 rule y_sustained_12

    lab = build_labels(k=3)[["slug", "y_sustained_12"]]
    news = pd.read_csv(ROOT / "model/news_sentiment/data/dapp_news_by_k.csv")
    d = news[news.k == 3].merge(lab, on="slug").dropna(subset=["y_sustained_12"])
    has = d["dapp_log_mentions_pre6m"] > 0
    rows = [  # bottom to top
        (f"No\n{(~has).sum()} apps", d.loc[~has, "y_sustained_12"].mean(), GREY),
        (f"Yes\n{has.sum()} apps", d.loc[has, "y_sustained_12"].mean(), BLUE),
    ]

    fig, ax = new_fig()
    bars = ax.barh([r[0] for r in rows], [r[1] for r in rows],
                   color=[r[2] for r in rows], height=0.55)
    for b, (_, v, c) in zip(bars, rows):
        ax.text(v + 0.01, b.get_y() + b.get_height() / 2, f"{v:.0%}",
                va="center", ha="left", color=BLUE if c == BLUE else MUTED, **LABEL)
    ax.set_xlim(0, 0.5)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Apps that last (%, v2 success rule)")
    ax.set_ylabel("Press coverage\nbefore launch")
    pct_axis(ax.xaxis)
    save(fig, "press_before_launch.png")
    return len(d), int(has.sum()), rows[1][1], rows[0][1]


# ---- Market shift: size and stickiness weight by period and by market -------
def weights():
    t = ROOT / "model/dapp_timesplit/results/tables"
    per = pd.read_csv(t / "coef_groups_by_period.csv")
    reg = pd.read_csv(t / "coef_groups_by_regime.csv")
    reg = reg[reg["sample"] == "All launches"]

    cols = [("Before\nTerra", per, "period", "Before Terra"),
            ("Terra to\nDencun", per, "period", "Terra to Dencun"),
            ("After\nDencun", per, "period", "After Dencun"),
            ("Faster\nmarket", reg, "regime", "Faster growth"),
            ("Slower\nmarket", reg, "regime", "Slower growth")]
    x = [0, 1, 2, 3.5, 4.5]   # gap between the two groupings
    w = 0.36
    size_v, stick_v = [], []
    for _, df, key, val in cols:
        g = df[df[key] == val].set_index("group")["weight"]
        size_v.append(g["Size"])
        stick_v.append(g["Stickiness"])

    fig, ax = new_fig()
    b1 = ax.bar([i - w / 2 for i in x], size_v, w, color=BLUE)
    b2 = ax.bar([i + w / 2 for i in x], stick_v, w, color=GREY)
    for bars, color in ((b1, BLUE), (b2, MUTED)):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.008,
                    f"{b.get_height():.0%}", ha="center", va="bottom", fontsize=10, color=color)
    ax.set_xticks(x)
    ax.set_xticklabels([c[0] for c in cols])
    ax.tick_params(axis="x", length=0)
    ax.axvline(2.75, color=GRID, lw=1.2)
    ax.text(1, 0.47, "By launch period", ha="center", fontsize=11, color=MUTED)
    ax.text(4.0, 0.47, "By market growth", ha="center", fontsize=11, color=MUTED)
    ax.set_xlim(-0.6, 5.1)
    ax.set_ylim(0, 0.5)
    end_label(ax, 5.1, stick_v[-1], "Stickiness", MUTED)
    end_label(ax, 5.1, size_v[-1], "Size", BLUE)
    ax.set_xlabel("Group of launches")
    ax.set_ylabel("Share of model\nweight (%)")
    pct_axis(ax.yaxis)
    save(fig, "size_stickiness_weights.png")
    return dict(zip([c[0].replace("\n", " ") for c in cols], zip(size_v, stick_v)))


if __name__ == "__main__":
    med = q2()
    top = q3()
    rate = q5()
    n_apps, n_press, with_press, without = press()
    wts = weights()
    print(f"Q2 flash median: peak {med['flash'].max():.1%} at month {med['flash'].idxmax()}, "
          f"month 23 {med['flash'].iloc[-1]:.1%}")
    print(f"Q3 top-10 share: {top.min():.1%} to {top.max():.1%}; "
          f"{((top >= 0.70) & (top <= 0.80)).mean():.0%} of months inside 70-80%")
    print(f"Q5 retention: month 1 {rate.loc[1]:.1%}, month 12 {rate.loc[12]:.1%}")
    print(f"Press: {n_press} of {n_apps} apps; {with_press:.1%} vs {without:.1%} last")
    for k, (s, st) in wts.items():
        print(f"Weights {k}: size {s:.0%}, stickiness {st:.0%}")
