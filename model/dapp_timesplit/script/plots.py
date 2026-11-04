"""Figures for the time-split checks, read from the saved tables."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import DATA, EVENTS, TABLES, TARGET, savefig, setup_style

MODELS = {"szabo_huberman": "Size only (Szabo-Huberman)", "logreg_elastic": "Logistic (elastic-net)",
          "hgb_calibrated": "Boosted trees, calibrated"}
# Models: neutral greys from the simplest (size only, light) to the most complex (boosted trees, dark)
COLOURS = {"szabo_huberman": "#CFCFCF", "logreg_elastic": "#8A96A3", "hgb_calibrated": "#34495E"}
# Time: one hue from light (earlier) to dark (later), for train -> test and for the three periods
ROLE_COLOURS = {"train": "#9ECAE1", "unused": "#F0F0F0", "test": "#08519C"}
PERIOD_COLOURS = ["#C6DBEF", "#6BAED6", "#2171B5"]
# Event lines: one colour each, away from the blues of the bars
EVENT_COLOURS = {"Terra": "#C0392B", "Dencun": "#7B3FA0"}
SPLITS = {"current": "Team split", "leakage_fixed": "Leakage fixed", "round_1": "Round 1", "round_2": "Round 2"}


def grouped_bars(ax, scores: pd.DataFrame, splits: list[str]) -> None:
    """AP per split and model, with 95% intervals and a dashed base rate (what random ranking scores)."""
    x = np.arange(len(splits))
    width = .8 / len(MODELS)
    for i, (model, label) in enumerate(MODELS.items()):
        d = scores[scores["model"] == model].set_index("split").loc[splits]
        pos = x - .4 + width * (i + .5)
        ax.bar(pos, d["ap"], width * .9, color=COLOURS[model], label=label)
        if d["ap_lo"].notna().all():
            ax.errorbar(pos, d["ap"], yerr=[d["ap"] - d["ap_lo"], d["ap_hi"] - d["ap"]], fmt="none",
                        ecolor="#6B7280", elinewidth=1, capsize=2)
        for p, v in zip(pos, d["ap"]):
            ax.text(p, .02, f"{v:.2f}", ha="center", va="bottom", fontsize=8, rotation=90,
                    color="#1F2937" if model == "szabo_huberman" else "white")
    base = scores.groupby("split")["base_rate"].first().loc[splits]
    for xi, b in zip(x, base):
        ax.hlines(b, xi - .45, xi + .45, colors="#1F2937", linestyles="--", lw=1)
    ax.plot([], [], ls="--", color="#1F2937", lw=1, label="Base rate (random)")
    ax.set_xticks(x, [SPLITS[s] for s in splits], fontsize=9)
    ax.set(ylim=(0, 1), ylabel="Holdout score (average precision)")
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, fontsize=8)


def label_bar(ax, y, x, n: int, successful: int, dark: bool, title: str = "") -> None:
    """DApps and successful DApps in one bar segment."""
    text = f"{title}\n{n} ({successful} succ.)" if title else f"{n}\n({successful} succ.)"
    ax.text(x, y, text, ha="center", va="center", fontsize=7.5, color="white" if dark else "#1F2937")


def timeline(rows: dict[str, str], name: str, events: bool, periods: bool = False) -> None:
    """Which launch months each split trains on, leaves out and tests on; optionally the event lines and the
    three launch periods used for the size effect."""
    roles = pd.read_csv(DATA / "split_assignment.csv", parse_dates=["launch_month"])
    colours = ROLE_COLOURS
    start, end = roles["launch_month"].min(), roles["launch_month"].max() + pd.DateOffset(months=1)
    month = pd.DateOffset(months=1)

    fig, ax = plt.subplots()
    labels = []
    for i, (split, label) in enumerate(rows.items()):
        for role, colour in colours.items():
            months = roles.loc[roles[split] == role, "launch_month"].drop_duplicates().sort_values()
            # Draw each run of consecutive months as one bar
            runs = months.diff().dt.days.fillna(99) > 31
            for _, run in months.groupby(runs.cumsum()):
                width = run.max() + month - run.min()
                ax.barh(i, width.days, left=run.min(), height=.5, color=colour)
                d = roles[(roles[split] == role) & roles["launch_month"].between(run.min(), run.max())]
                test_start = roles.loc[roles[split] == "test", "launch_month"].min()
                if role == "unused" and run.min() > test_start:
                    continue   # after the test: not part of this split, so left unlabelled
                if role == "unused":
                    ax.text(run.min() + width / 2, i, f"{len(d)}", ha="center", va="center", fontsize=7.5,
                            color="#1F2937")
                else:
                    label_bar(ax, i, run.min() + width / 2, len(d), int(d[TARGET].sum()), dark=(role == "test"))
        labels.append(label)

    if periods:
        terra, dencun = EVENTS["Terra"], EVENTS["Dencun"]
        spans = [(start, terra, "Before Terra"), (terra, dencun, "Terra to Dencun"), (dencun, end, "After Dencun")]
        for (a, b, period), colour in zip(spans, PERIOD_COLOURS):
            ax.barh(len(labels), (b - a).days, left=a, height=.5, color=colour)
            d = roles[(roles["launch_month"] >= a) & (roles["launch_month"] < b)]
            label_bar(ax, len(labels), a + (b - a) / 2, len(d), int(d[TARGET].sum()),
                      dark=colour == PERIOD_COLOURS[-1], title=period)
        labels.append("Each period fitted alone")
    event_lines = []
    if events:
        for event, date in EVENTS.items():
            event_lines.append(ax.axvline(date, color=EVENT_COLOURS[event], ls="--", lw=1.6,
                                          label=f"{event}  {date:%Y-%m}"))

    ax.set_yticks(range(len(labels)), labels)
    ax.set_ylim(len(labels) - .4, -.6)
    ax.set_xlim(start, end)
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    ax.set_xlabel("Launch month")
    # One legend below the plot: roles (if any), then the event lines
    handles, names = [], []
    if rows:
        handles += [plt.Rectangle((0, 0), 1, 1, color=c) for c in colours.values()]
        names += ["Train", "Not used", "Test"]
    handles += event_lines
    names += [line.get_label() for line in event_lines]
    if handles:
        ax.legend(handles, names, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=len(handles), fontsize=8)
    ax.set_title("Numbers: DApps launched (successful DApps)", fontsize=9, color="#4D4D4D")
    savefig(fig, name)


def run() -> None:
    setup_style()
    timeline({"current": "Team split", "leakage_fixed": "Leakage fixed"}, "timeline_leakage", events=False)
    timeline({"round_1": "Round 1", "round_2": "Round 2"}, "timeline_events", events=True)
    timeline({}, "timeline_periods", events=True, periods=True)
    scores = pd.read_csv(TABLES / "holdout_scores.csv")

    fig, ax = plt.subplots()
    grouped_bars(ax, scores, ["current", "leakage_fixed"])
    ax.set_title("Same 2023-24 test; training answers known before 2023 after the fix (k = 3)",
                 fontsize=9, color="#4D4D4D")
    savefig(fig, "leakage_check")

    fig, ax = plt.subplots()
    grouped_bars(ax, scores, ["round_1", "round_2"])
    ax.set_title("Stand at each event, train on answers known then, test on what launches next (k = 3)",
                 fontsize=9, color="#4D4D4D")
    savefig(fig, "event_rounds")

    # Size effect: slope of the size-only logistic regression in each launch period
    size = pd.read_csv(TABLES / "size_effect_by_period.csv")
    fig, ax = plt.subplots()
    y = np.arange(len(size))
    # Each period in its timeline colour, so the dots match the "Each period fitted alone" row
    for yi, row in size.iterrows():
        ax.errorbar(row["odds_ratio_10x"], yi,
                    xerr=[[row["odds_ratio_10x"] - np.exp(row["slope_lo"] * np.log(10))],
                          [np.exp(row["slope_hi"] * np.log(10)) - row["odds_ratio_10x"]]],
                    fmt="o", color=PERIOD_COLOURS[yi], ecolor=PERIOD_COLOURS[yi], mec="#1F2937", mew=.6,
                    elinewidth=2, capsize=4, ms=9)
    for yi, (v, n, s) in enumerate(zip(size["odds_ratio_10x"], size["n_dapps"], size["n_successful"])):
        ax.annotate(f"{v:.1f}x  ({s} of {n} successful)", (v, yi), xytext=(0, 10), textcoords="offset points",
                    ha="center", fontsize=8, color="#374151")
    ax.axvline(1, color="#9CA3AF", lw=1)
    ax.set_xscale("log")
    ax.xaxis.set_minor_locator(plt.NullLocator())
    ax.set_xticks([1, 2, 5, 10, 20], ["1x", "2x", "5x", "10x", "20x"])
    ax.set_yticks(y, size["period"].str.replace(r" \(.*\)", "", regex=True))   # dates are in the report text
    ax.set_ylim(len(size) - .5, -.6)
    ax.set(xlabel="Odds of success when last-month wallets are 10 times larger")
    ax.set_title("Size-only logistic regression, fitted per launch period; whiskers: 95% bootstrap interval",
                 fontsize=9, color="#4D4D4D")
    savefig(fig, "size_effect")

    # Weight of each feature group (share of absolute standardised coefficients), one bar per period
    groups = pd.read_csv(TABLES / "coef_groups_by_period.csv")
    order = ["Size", "Stickiness", "Context", "Movement", "Concentration"]
    period_names = list(dict.fromkeys(groups["period"]))
    h = .8 / len(period_names)
    fig, ax = plt.subplots()
    y = np.arange(len(order))
    for j, (period, colour) in enumerate(zip(period_names, PERIOD_COLOURS)):
        d = groups[groups["period"] == period].set_index("group").loc[order]
        pos = y - .4 + h * (j + .5)
        ax.barh(pos, d["weight"], h * .9, color=colour, label=period)
        ax.errorbar(d["weight"], pos, xerr=[d["weight"] - d["weight_lo"], d["weight_hi"] - d["weight"]], fmt="none",
                    ecolor="#6B7280", elinewidth=1, capsize=2)
    ax.set_yticks(y, order)
    ax.invert_yaxis()
    ax.set_axisbelow(True)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set(xlabel="Share of absolute standardised coefficients (27 features, fitted per period)")
    ax.set_title("Whiskers: 95% interval over 1,000 resamples", fontsize=9, color="#4D4D4D")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=8)
    savefig(fig, "coef_groups")

    # Same weights as a line per group across the periods, to show the shift over time
    group_colours = {"Size": "#34495E", "Stickiness": "#E67E22", "Context": "#16A085", "Movement": "#8E44AD",
                     "Concentration": "#95A5A6"}
    fig, ax = plt.subplots()
    x = np.arange(len(period_names))
    for g in order:
        d = groups[groups["group"] == g].set_index("period").loc[period_names]
        ax.plot(x, d["weight"], marker="o", ms=6, lw=2, color=group_colours[g], label=g)
        ax.annotate(f"{d['weight'].iloc[-1]:.0%}", (x[-1], d["weight"].iloc[-1]), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=8, color=group_colours[g])
    ax.set_xticks(x, period_names)
    ax.set_xlim(-.2, len(period_names) - .6)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set(ylabel="Share of absolute standardised coefficients")
    ax.set_title("Same weights as the bars, one line per group (intervals on the bars)", fontsize=9, color="#4D4D4D")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=5, fontsize=8)
    savefig(fig, "coef_groups_trend")

    # Size features: rank among all features in each period (1 at the top), fees highlighted against the rest
    size = pd.read_csv(TABLES / "size_ranks_by_period.csv").set_index("feature")
    rank_cols = [f"{p} rank" for p in period_names]
    highlight = {"log_mean_fees": ("#E67E22", "Fees"), "log_mean_tx": ("#34495E", "Transactions"),
                 "log_last_wallets": ("#2171B5", "Last-month wallets")}
    fig, ax = plt.subplots()
    x = np.arange(len(period_names))
    for f, row in size.iterrows():
        colour, label = highlight.get(f, ("#C7CCD1", None))
        ax.plot(x, row[rank_cols], color=colour, lw=2.4 if label else 1.2, marker="o", ms=7 if label else 4,
                zorder=3 if label else 2)
        if label:
            for xi, r in zip(x, row[rank_cols]):
                ax.annotate(f"{int(r)}", (xi, r), xytext=(0, 9), textcoords="offset points", ha="center",
                            fontsize=8, color=colour)
            ax.annotate(label, (x[-1], row[rank_cols[-1]]), xytext=(12, 0), textcoords="offset points",
                        va="center", fontsize=9, color=colour)
    ax.plot([], [], color="#C7CCD1", lw=1.2, marker="o", ms=4, label="Other wallet counts and gas")
    ax.invert_yaxis()
    ax.set_xticks(x, period_names)
    ax.set_xlim(-.2, len(period_names) - .4)
    ax.set_ylim(27.5, -.5)
    ax.set_yticks([1, 5, 10, 15, 20, 25])
    ax.set(ylabel="Rank among all features (1 = largest)")
    ax.legend(loc="lower left", fontsize=8)
    ax.set_title("Size features: fees climb to 1st while transactions and wallets fall", fontsize=9, color="#4D4D4D")
    savefig(fig, "size_ranks")
