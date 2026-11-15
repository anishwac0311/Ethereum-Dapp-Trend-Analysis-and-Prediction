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
# Market growth at launch: warm amber for faster, deep teal for slower; away from the period blues and event lines
REGIME_COLOURS = ["#F2A541", "#1F6F64"]
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


def cat_share(ax, rows: pd.DataFrame, labels: list[str], colours: list[str], hatches: list) -> None:
    """Coefficient of early_cat_share with its 95% interval, one row per set of DApps."""
    for i, (row, colour, hatch) in enumerate(zip(rows.itertuples(), colours, hatches)):
        ax.barh(i, row.coef, .6, color=colour, hatch=hatch, edgecolor="white", lw=0)
        ax.errorbar(row.coef, i, xerr=[[row.coef - row.coef_lo], [row.coef_hi - row.coef]], fmt="none",
                    ecolor="#374151", elinewidth=1.2, capsize=3)
        # Label to the right of the whisker and of the zero line, so it never crosses either
        ax.annotate(f"{row.coef:+.2f}  ({row.share_positive:.0%} of resamples > 0)", (max(row.coef_hi, 0), i),
                    xytext=(6, 0), textcoords="offset points", va="center", fontsize=8, color="#374151")
    ax.axvline(0, color="#6B7280", lw=1)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_ylim(len(labels) - .4, -.6)
    ax.set_xlim(-2.4, 3.4)   # the same on both figures, so the bars compare across slides
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    ax.set_xlabel("Standardised coefficient of early_cat_share (DApp's share of its category's wallets)")
    ax.set_title("Above 0: a large category share goes with success; below 0: with failure; whiskers: 95% interval",
                 fontsize=9, color="#4D4D4D")


def market_figures(period_names: list[str]) -> None:
    """Market growth at launch, group weights and the category-share coefficient for faster and slower growth."""
    # Market growth at each launch month, split at the median, with the market events
    months = pd.read_csv(TABLES / "market_growth_by_month.csv", parse_dates=["launch_month"])
    median = months["median_growth"].iloc[0]
    cap = 2.0
    fig, ax = plt.subplots()
    for faster, colour in zip([True, False], REGIME_COLOURS):
        d = months[months["faster"] == faster]
        ax.bar(d["launch_month"], d["growth"].clip(upper=cap), width=25, color=colour,
               label=f"{'Faster' if faster else 'Slower'} growth: {d['n_dapps'].sum()} DApps "
                     f"({d['n_successful'].sum()} succ.)")
    ax.axhline(median, color="#1F2937", ls=":", lw=1)
    ax.annotate(f"Median {median:.0%}", (months["launch_month"].max(), median), xytext=(0, 4),
                textcoords="offset points", ha="right", fontsize=8, color="#1F2937")
    ax.axhline(0, color="#6B7280", lw=1)
    for event, date in EVENTS.items():
        ax.axvline(date, color=EVENT_COLOURS[event], ls="--", lw=1.4, label=f"{event}  {date:%Y-%m}")
    ax.set_ylim(-.4, cap + .25)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set(xlabel="Launch month", ylabel="Active wallets vs 3 months earlier")
    ax.set_title(f"Launch month vs 3 months earlier, all categories; bars cut at 200% (2020 peaks reach "
                 f"{months['growth'].max():.0%})", fontsize=9, color="#4D4D4D")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=8)
    savefig(fig, "market_growth")

    # Group weights for faster and slower growth, on all launches and on 2023-24 launches alone
    regime = pd.read_csv(TABLES / "coef_groups_by_regime.csv")
    order = ["Size", "Stickiness", "Context", "Movement", "Concentration"]
    sets = [(s, r) for s in ["All launches", "2023-24 launches"] for r in ["Faster growth", "Slower growth"]]
    h = .8 / len(sets)
    fig, ax = plt.subplots()
    y = np.arange(len(order))
    for j, (sample, name) in enumerate(sets):
        d = regime[(regime["sample"] == sample) & (regime["regime"] == name)].set_index("group").loc[order]
        pos = y - .4 + h * (j + .5)
        ax.barh(pos, d["weight"], h * .9, color=REGIME_COLOURS[j % 2], label=f"{name}, {sample.lower()}",
                hatch="//" if sample != "All launches" else None, edgecolor="white", lw=0)
        ax.errorbar(d["weight"], pos, xerr=[d["weight"] - d["weight_lo"], d["weight_hi"] - d["weight"]], fmt="none",
                    ecolor="#6B7280", elinewidth=1, capsize=2)
    ax.set_yticks(y, order)
    ax.invert_yaxis()
    ax.set_axisbelow(True)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set(xlabel="Share of absolute standardised coefficients (26 features, launch_eco_growth_3m left out)")
    ax.set_title("Split at the median of launch_eco_growth_3m; whiskers: 95% interval over 1,000 resamples",
                 fontsize=9, color="#4D4D4D")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=8)
    savefig(fig, "coef_groups_regime")

    # Launch years in each half, to show how far market growth and time overlap
    sizes = pd.read_csv(TABLES / "regime_sizes.csv")
    sizes = sizes[sizes["sample"] == "All launches"].set_index("regime")
    year_cols = [c for c in sizes if c.startswith("launched_")]
    x = np.arange(len(year_cols))
    w = .38
    fig, ax = plt.subplots()
    for j, (name, colour) in enumerate(zip(sizes.index, REGIME_COLOURS)):
        bars = ax.bar(x - w / 2 + j * w, sizes.loc[name, year_cols].astype(int), w * .95, color=colour,
                      label=f"{name}: {sizes.loc[name, 'n_dapps']} DApps ({sizes.loc[name, 'n_successful']} succ.)")
        ax.bar_label(bars, fontsize=8, padding=2, color="#374151")
    ax.set_xticks(x, [c.removeprefix("launched_") for c in year_cols])
    ax.set_axisbelow(True)
    ax.grid(axis="x", visible=False)
    ax.set(xlabel="Launch year", ylabel="DApps launched")
    ax.set_title(f"Faster growth: wallets up more than {sizes['median_growth'].iloc[0]:.0%} on 3 months earlier (the median)",
                 fontsize=9, color="#4D4D4D")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=8)
    savefig(fig, "regime_by_year")

    # Category share: by launch period, then by market growth (all launches and 2023-24 alone)
    periods = pd.read_csv(TABLES / "coef_by_period.csv")
    rows = periods[periods["feature"] == "early_cat_share"].set_index("period").loc[period_names]
    fig, ax = plt.subplots()
    cat_share(ax, rows, period_names, PERIOD_COLOURS, [None] * len(rows))
    savefig(fig, "cat_share_by_period")

    coef = pd.read_csv(TABLES / "coef_by_regime.csv")
    coef = coef[coef["feature"] == "early_cat_share"].set_index(["sample", "regime"]).loc[sets]
    fig, ax = plt.subplots()
    cat_share(ax, coef, [f"{r}\n{s.lower()}" for s, r in sets], [REGIME_COLOURS[j % 2] for j in range(len(sets))],
              [None if s == "All launches" else "//" for s, _ in sets])
    savefig(fig, "cat_share_by_regime")


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

    # One panel per event, each comparing the two periods on either side of it; the middle period is in both
    group_colours = {"Size": "#34495E", "Stickiness": "#E67E22", "Context": "#16A085", "Movement": "#8E44AD",
                     "Concentration": "#95A5A6"}
    weight = groups.pivot_table(index="group", columns="period", values="weight").loc[order]
    pairs = {"Terra": (period_names[0], period_names[1]), "Dencun": (period_names[1], period_names[2])}
    # Launch months of each period, so the shared middle period shows the same dates in both panels
    launch = pd.read_csv(DATA / "split_assignment.csv", parse_dates=["launch_month"])["launch_month"]
    last = lambda d: (d - pd.DateOffset(months=1)).strftime("%Y-%m")
    months = {period_names[0]: f"{launch.min():%Y-%m} to {last(EVENTS['Terra'])}",
              period_names[1]: f"{EVENTS['Terra']:%Y-%m} to {last(EVENTS['Dencun'])}",
              period_names[2]: f"{EVENTS['Dencun']:%Y-%m} to {launch.max():%Y-%m}"}
    fig, axes = plt.subplots(1, 2, sharey=True)
    for ax, (event, (before, after)) in zip(axes, pairs.items()):
        for g in order:
            ax.plot([0, 1], weight.loc[g, [before, after]], marker="o", ms=6, lw=2.2, color=group_colours[g])
        # Values at both ends, nudged apart where two groups are close
        for side, period, ha, dx in [(0, before, "right", -8), (1, after, "left", 8)]:
            placed = []
            for g, v in weight[period].sort_values().items():
                y = max(v, placed[-1] + .012) if placed else v
                placed.append(y)
                label = f"{v:.0%}" if side == 0 else f"{v:.0%}  {g}"
                ax.annotate(label, (side, v), xytext=(dx, (y - v) * 900), textcoords="offset points", ha=ha,
                            va="center", fontsize=8, color=group_colours[g])
        ax.set_xticks([0, 1], ["Before", "After"])
        ax.set_xlim(-.45, 1.75)
        ax.set_title(f"{event}  {EVENTS[event]:%Y-%m}", fontsize=11, color=EVENT_COLOURS[event], fontweight="bold",
                     pad=16)
        # Launch months of the two periods, small under the title, so the axis stays light
        ax.annotate(f"{months[before]}  vs  {months[after]}", (.5, 1), xycoords="axes fraction", xytext=(0, 4),
                    textcoords="offset points", ha="center", va="bottom", fontsize=7.5, color="#6B7280")
        ax.grid(axis="x", visible=False)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    axes[0].set(ylabel="Share of absolute standardised coefficients")
    fig.suptitle("Weight of each feature group, launches before vs after each event", fontsize=9, color="#4D4D4D")
    savefig(fig, "coef_groups_by_event")

    market_figures(period_names)

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
