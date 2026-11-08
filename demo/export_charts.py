"""Write the data behind every demo chart to demo/charts/*.csv, plus a README.md index.

Reads demo/data.js (built by build_data.py), so every number here is the number the site draws.
Run: python3 demo/export_charts.py
"""
import csv
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "charts"
D = json.loads((HERE / "data.js").read_text().split("=", 1)[1].strip().rstrip(";"))
CATS = D["meta"]["categories"]
ERAS = [("before", "Before Terra"), ("between", "Terra to Dencun"), ("after", "After Dencun")]
INDEX = []


def save(name, head, rows, chart, used_on, source, how):
    with open(OUT / name, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(head)
        w.writerows([["" if v is None else int(v) if isinstance(v, float) and v.is_integer() else v for v in r] for r in rows])
    INDEX.append((name, chart, used_on, source, how))


def by_month(months, series):
    return [[m] + [s[i] for s in series] for i, m in enumerate(months)]


if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()

# Home market strip
m = D["mkt"]
save("01_market_month.csv", ["month", "active_wallets", "tx_count", "gas_used"],
     by_month(m["months"], [m["wallets"], m["tx"], m["gas"]]),
     "Market strip: wallets, transactions and gas per month", "Home",
     "dapp_data_v2/category_month.csv", "Sum over the seven categories. Terra = 2022-05, Dencun = 2024-03.")

# Q1 growth
q = D["q1"]
for key, fname, what, how in [
        ("wallets", "02_q1_wallets_by_category.csv", "Monthly active wallets by category", "active_wallets per category."),
        ("growth_12m", "02_q1_growth_12m_by_category.csv", "12-month change in wallets by category",
         "Wallets vs the same month a year earlier (0.5 = +50%)."),
        ("dapps", "02_q1_active_dapps_by_category.csv", "Active DApps by category", "active_dapps per category.")]:
    save(fname, ["month"] + CATS, by_month(q["months"], [q[key][c] for c in CATS]), what,
         "Q1 Growth, scenario walks, Pick a timeline", "dapp_data_v2/category_month.csv", how)

# Q3 concentration
q = D["q3"]
keys = ["top1_share", "top5_share", "top10_share", "gini", "hhi"]
save("03_q3_market_concentration.csv", ["month", "n_dapps"] + keys,
     by_month(q["months"], [q["eco_n"]] + [q["eco"][k] for k in keys]),
     "Share of all wallets held by the top DApps", "Q3 Concentration",
     "dapp_data_v2/concentration_month.csv (metric = active_wallets, scope = ecosystem)", "Shares of all active wallets that month.")
save("03_q3_top10_by_category.csv", ["month"] + CATS, by_month(q["months"], [q["cat_top10"][c] for c in CATS]),
     "Top-10 share inside each category", "Q3 Concentration, scenario walks",
     "dapp_data_v2/concentration_month.csv (scope = category)", "Top-10 share of the category's wallets.")
rc = q["rank_curve"]
save("03_q3_rank_curve_by_year.csv", ["year", "n_dapps", "top_k", "cum_share"],
     [[y, v["n"], k, s] for y, v in rc.items() for k, s in zip(v["k"], v["share"])],
     "Rank curve: share held by the top k DApps", "Q3 Concentration", "dapp_data_v2/dapp_panel.csv",
     "DApps ranked by mean monthly wallets in the year; cumulative share of the top k.")
save("03_q3_size_histogram_by_year.csv", ["year", "log10_wallets_from", "log10_wallets_to", "n_dapps", "n_under_10_wallets"],
     [[y, a, b, h, v["under10"]] for y, v in rc.items() for a, b, h in zip(v["edges"][:-1], v["edges"][1:], v["hist"])],
     "DApps by size (log-normal shape)", "Q3 Concentration", "dapp_data_v2/dapp_panel.csv; power-law test in "
     "model/dapp_concentration/results/tables/power_law_by_year.csv (branch concentration-analysis)",
     "Bins are log10 of mean monthly wallets in the year.")

# Q2 survival shapes
q = D["q2"]
save("04_q2_median_shape.csv", ["month_since_launch", "flash_one_hit", "grower_kept_growing"],
     [[i, a, b] for i, (a, b) in enumerate(zip(q["median"]["flash"], q["median"]["grower"]))],
     "Median shape: wallets as a share of own peak", "Q2 Survival",
     "eda/tables/trajectory_clusters.csv, eda/tables/03_trajectories_normalized.csv",
     f"{q['n']} widely used DApps; flash_fade = one-hit, every other cluster = kept growing.")
save("04_q2_shape_by_category.csv", ["category", "flash_one_hit", "grower_kept_growing"],
     [[c, v["flash"], v["grower"]] for c, v in q["by_cat"].items()] + [["All", q["counts"]["flash"], q["counts"]["grower"]]],
     "One-hit vs kept growing, by category", "Q2 Survival", "eda/tables/trajectory_clusters.csv", "Counts of DApps.")

# Q4 speed
q = D["q4"]
save("05_q4_reach_10k.csv", ["month_since_launch", "share_10k_success", "share_10k_other", "median_cum_success", "median_cum_other"],
     [[mm, q["share_10k"]["success"][i], q["share_10k"]["other"][i], q["median_cum"]["success"][i], q["median_cum"]["other"][i]]
      for i, mm in enumerate(q["months"])],
     "Reaching 10K cumulative wallets", "Q4 Speed, Compare",
     "dapp_data_v2/dapp_panel.csv (cum_wallets), model/tables/labels_k3.csv (y_sustained_12)",
     f"Study set: {q['n']['success']} successes, {q['n']['other']} others. Month 0 = first month with a user.")

# Q5 retention and weights
q = D["q5"]
save("06_q5_retention_by_era.csv", ["era", "n_dapps", "month_since_launch", "median", "p25", "p75"],
     [[name, q["periods"][k]["n"], mm, q["periods"][k]["median"][i], q["periods"][k]["lo"][i], q["periods"][k]["hi"][i]]
      for k, name in ERAS for i, mm in enumerate(q["months"])],
     "Launch users still active, by launch era", "Q5 Retention, Compare", "dapp_data_v2/cohort_retention.csv",
     f"DApps with at least {q['min_cohort']} first-month users. Median with 25th-75th percentile band.")
save("06_q5_feature_weights_by_era.csv", ["era", "group", "weight", "low", "high"],
     [[name, g, *v] for k, name in ERAS for g, v in q["weights"][k].items()],
     "What matters in each era: feature-group weights", "Q5 Retention",
     "model/dapp_timesplit/results/tables/coef_groups_by_period.csv (branch time-split-analysis)",
     "Each group's share of the L2 logistic regression's total weight, fitted per era; low / high from 1,000 resamples.")

# Q6 take-off
save("07_q6_around_10k.csv", ["metric", "group", "months_from_10k", "median", "n_dapps"],
     [[met, t, rel, med, n] for met, g in D["q6"].items() for t, v in g.items()
      for rel, med, n in zip(v["rel"], v["median"], v["n"])],
     "Before and after crossing 10K cumulative wallets", "Q6 Take-off, Compare", "eda/tables/05_event_checkpoints.csv",
     "Month 0 = the month a DApp crosses 10K. Median across DApps of each group.")

# Method
mt = D["method"]
save("08_method_funnel.csv", ["step", "n"],
     [[k, mt[k]] for k in ["n_registry", "n_static", "n_contracts", "n_active", "n_old", "n_2025", "n_pre2020", "n_study", "n_success"]],
     "Dataset funnel", "Method, About",
     "dapp_data_v2/protocols.csv, dapp_static.csv, app_contracts.csv, dapp_lifecycle.csv; model/tables/labels_k3.csv",
     "Registry size 1,816 is from DeFiLlama, as reported in Presentation 2.")
save("08_method_lifecycle.csv", ["lifecycle", "n"], list(mt["lifecycle"].items()),
     "DApps by lifecycle label", "Method", "dapp_data_v2/dapp_lifecycle.csv", "Counts of lifecycle_label.")
save("08_method_by_category.csv", ["category", "n"], list(mt["by_cat"].items()),
     "DApps by category", "Method", "dapp_data_v2/dapp_lifecycle.csv", "Counts of category_group.")
save("08_method_by_launch_year.csv", ["launch_year", "n"], list(mt["by_year"].items()),
     "DApps by launch year", "Method", "dapp_data_v2/dapp_lifecycle.csv", "Counts of launch_year.")
pe = mt["peak_edges"]
save("08_method_peak_histogram.csv", ["log10_peak_from", "log10_peak_to", "n_dapps"],
     [[a, b, h] for a, b, h in zip(pe[:-1], pe[1:], mt["peak_hist"])],
     "Peak monthly wallets", "Method", "dapp_data_v2/dapp_lifecycle.csv", "Bins are log10 of peak_wallets.")
save("08_method_signals.csv", ["group", "signal", "feature", "kind", "success", "other"],
     [[x["group"], x["label"], x["feature"], x["kind"], x["success"], x["other"]] for x in mt["features"]],
     "33 early signals: success vs other", "Method",
     "model/tables/dataset_k3.csv; model/dapp_offchain/data/dapp_offchain_by_k.csv (k = 3)",
     "First 3 months. Median for numbers, share for yes/no flags, mean for proposal counts.")

# Era leaders
save("09_era_leaders_top5.csv", ["era", "category", "n_active_dapps", "category_avg_wallets", "rank", "slug", "dapp", "avg_wallets", "share"],
     [[name, cat, L["n"], L["tot"], i + 1, t[0], t[1], t[2], t[3]]
      for k, name in ERAS for cat in CATS if (L := D["lead"][k].get(cat)) for i, t in enumerate(L["top"])],
     "Top five DApps per category and era", "Scenario walks, Neighbours leaderboard", "dapp_data_v2/dapp_panel.csv",
     "Average monthly active wallets inside the era window; share of the category total.")

# Picker DApps and all DApps by age
save("10_dapps_170_wallets.csv", ["slug", "name", "category", "launch", "era", "shape", "peak", "success"] + [f"m{i}" for i in range(24)],
     [[s, d["name"], d["cat"], d["launch"], d["period"], d["group"], d["peak"], d["success"]] + (d["wallets"] + [None] * 24)[:24]
      for s, d in D["dapps"].items()],
     "The 170 widely used DApps: wallets by month since launch", "Pick a DApp, walk figures, Compare",
     "eda/tables/trajectory_clusters.csv, dapp_data_v2/dapp_panel.csv, model/tables/labels_k3.csv",
     "success is blank when too recent to judge. m0 = first month with a user.")
A = 36
save("11_all_dapps_wallets_by_age.csv", ["slug", "name", "category", "first_month", "lifecycle", "success"] + [f"a{i}" for i in range(A)],
     [[s, d["n"], d["c"], d["lm"], d["l"], d["s"]] + (d["w"] + [None] * A)[:A] for s, d in D["snap"].items()],
     f"All {len(D['snap'])} DApps: wallets by month of age", "Your DApp, Neighbours map, the game",
     "dapp_data_v2/dapp_panel.csv, dapp_data_v2/dapp_lifecycle.csv, model/tables/labels_k3.csv",
     "Age 0 = first month with a user.")

esc = lambda s: str(s).replace("|", "\\|")
lines = ["# Demo chart data", "",
         "One CSV per chart table, with the numbers the demo site draws. Generated from `demo/data.js` by "
         "`demo/export_charts.py`; rerun it after `build_data.py`. The DragonQuest example on the Method page uses "
         "made-up numbers and has no CSV.", "",
         "| file | chart | used on | source | how |", "|---|---|---|---|---|"]
lines += [f"| [{n}]({n}) | {esc(c)} | {esc(u)} | {esc(s)} | {esc(h)} |" for n, c, u, s, h in INDEX]
(OUT / "README.md").write_text("\n".join(lines) + "\n")
print("wrote", len(INDEX), "CSVs to", OUT)
