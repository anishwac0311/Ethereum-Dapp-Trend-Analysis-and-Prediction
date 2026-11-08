"""Build demo/data.js from the repo's own outputs.

Every number the demo shows comes from this file. Run from the repo root:
    python3 demo/build_data.py
"""
import io
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "dapp_data_v2"
EDA = ROOT / "eda" / "tables"
MODEL = ROOT / "model" / "tables"
TS = ROOT / "model" / "dapp_timesplit" / "results" / "tables"
OUT = Path(__file__).resolve().parent / "data.js"
OFF = ROOT / "model" / "dapp_offchain" / "data"
TS_BRANCH = "time-split-analysis"  # the time-split tables live on this branch until PR #4 merges


def read_ts(name):
    """Read a time-split table from disk, or from its branch when this checkout does not have it."""
    path = TS / name
    if path.exists():
        return pd.read_csv(path)
    rel = path.relative_to(ROOT).as_posix()
    txt = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{TS_BRANCH}:{rel}"], text=True)
    return pd.read_csv(io.StringIO(txt))

TERRA = "2022-05"
DENCUN = "2024-03"
CATS = ["DEX", "DeFi", "Infrastructure", "NFT", "Gaming", "Social", "Other"]
FEATURED = [
    "uniswap-v3", "lido", "blur", "curve-dex", "pancakeswap-amm", "aave-v3",
    "opensea-v2", "opensea-seaport", "hop-protocol", "starknet-bridge",
    "base-bridge", "linea-bridge",
]


def period_of(month: str) -> str:
    m = month[:7]
    if m < TERRA:
        return "before"
    if m < DENCUN:
        return "between"
    return "after"


def r(x, d=4):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return None
    return round(float(x), d)


def rl(xs, d=4):
    return [r(x, d) for x in xs]


panel = pd.read_csv(V2 / "dapp_panel.csv", usecols=[
    "slug", "name", "category_group", "month", "active_wallets", "cum_wallets",
])
panel["month"] = panel["month"].str[:7]
panel = panel.sort_values(["slug", "month"])
first = panel[panel.active_wallets > 0].groupby("slug").month.min()
panel = panel.join(first.rename("first_month"), on="slug")
panel = panel[panel.month >= panel.first_month]
mi = lambda s: int(s[:4]) * 12 + int(s[5:7])
panel["m"] = panel.month.map(mi) - panel.first_month.map(mi)

data = {"meta": {
    "panel_start": panel.month.min(), "panel_end": panel.month.max(),
    "n_dapps": int(len(pd.read_csv(V2 / "dapp_lifecycle.csv"))), "terra": TERRA, "dencun": DENCUN,
    "categories": CATS,
}}

# Q1: category growth (12-month change in active wallets, per month)
cm = pd.read_csv(V2 / "category_month.csv")
cm["month"] = cm["month"].str[:7]
months = sorted(cm.month.unique())
q1 = {"months": months, "growth_12m": {}, "wallets": {}, "dapps": {}}
for c in CATS:
    s = cm[cm.category_group == c].set_index("month").reindex(months)
    q1["growth_12m"][c] = rl(s.growth_12m, 3)
    q1["wallets"][c] = [None if pd.isna(v) else int(v) for v in s.active_wallets]
    q1["dapps"][c] = [None if pd.isna(v) else int(v) for v in s.active_dapps]
data["q1"] = q1
# Home market strip: the whole market each month, summed over categories (wallets, transactions, gas)
mk = cm[cm.category_group.isin(CATS)].groupby("month")[["active_wallets", "tx_count", "gas_used"]].sum().reindex(months)
data["mkt"] = {"months": months,
               "wallets": [None if pd.isna(v) else int(v) for v in mk.active_wallets],
               "tx": [None if pd.isna(v) else int(v) for v in mk.tx_count],
               "gas": [None if pd.isna(v) else float(v) for v in mk.gas_used]}

# Q3: concentration
conc = pd.read_csv(V2 / "concentration_month.csv")
conc = conc[conc.metric == "active_wallets"].copy()
conc["month"] = conc["month"].str[:7]
eco = conc[conc.scope == "ecosystem"].set_index("month").reindex(months)
q3 = {"months": months, "eco": {k: rl(eco[k], 3) for k in
      ["top1_share", "top5_share", "top10_share", "gini", "hhi"]},
      "eco_n": [None if pd.isna(v) else int(v) for v in eco.n_dapps],
      "cat_top10": {}, "rank_curve": {}}
for c in CATS:
    s = conc[(conc.scope == "category") & (conc.category_group == c)].set_index("month").reindex(months)
    q3["cat_top10"][c] = rl(s.top10_share, 3)
# rank curve per year: DApps ranked by mean monthly wallets that year
panel["year"] = panel.month.str[:4]
for y, g in panel.groupby("year"):
    sizes = g.groupby("slug").active_wallets.mean().sort_values(ascending=False)
    sizes = sizes[sizes > 0]
    cum = (sizes.cumsum() / sizes.sum()).values
    ks = sorted(set([1, 2, 3, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300, 400, len(cum)]))
    ks = [k for k in ks if k <= len(cum)]
    logs = np.log10(sizes.values)
    hist, edges = np.histogram(logs, bins=np.arange(0, 7, 0.5))
    q3["rank_curve"][y] = {"n": int(len(cum)), "k": ks, "share": rl([cum[k - 1] for k in ks], 3),
                           "hist": hist.tolist(), "edges": rl(edges, 1),
                           "under10": int((sizes < 10).sum())}
data["q3"] = q3

# Q2: trajectory shape clusters (170 adopted DApps)
tc = pd.read_csv(EDA / "trajectory_clusters.csv")
tn = pd.read_csv(EDA / "03_trajectories_normalized.csv").set_index("slug")
mcols = [f"m{i}" for i in range(24)]
tc["group"] = tc.cluster_name.map(lambda x: "flash" if x == "flash_fade" else "grower")
q2 = {"n": int(len(tc)), "counts": tc.group.value_counts().to_dict(),
      "median": {}, "by_cat": {}}
for g, d in tc.groupby("group"):
    q2["median"][g] = rl(tn.loc[d.slug, mcols].median().values, 3)
for c in CATS:
    d = tc[tc.category_group == c]
    q2["by_cat"][c] = {"flash": int((d.group == "flash").sum()), "grower": int((d.group == "grower").sum())}
data["q2"] = q2

# Q4: time to 10K cumulative wallets, team success label (k=3)
lab = pd.read_csv(MODEL / "labels_k3.csv")
lab = lab[(~lab.left_censored) & lab.eligible_12m & lab.y_sustained_12.notna()]
cw = panel.pivot_table(index="slug", columns="m", values="cum_wallets", aggfunc="max")
cw = cw.reindex(columns=range(0, 13)).ffill(axis=1)
q4 = {"months": list(range(13)), "share_10k": {}, "n": {}, "median_cum": {}}
for name, d in [("success", lab[lab.y_sustained_12 == 1]), ("other", lab[lab.y_sustained_12 == 0])]:
    sub = cw.reindex(d.slug)
    q4["n"][name] = int(len(d))
    q4["share_10k"][name] = rl((sub >= 10_000).mean().values, 3)
    q4["median_cum"][name] = rl(sub.median().values, 0)
data["q4"] = q4

# Q5: launch-cohort retention by launch period + feature-group weights
cr = pd.read_csv(V2 / "cohort_retention.csv")
cr["cohort_month"] = cr["cohort_month"].str[:7]
cr = cr.join(first.rename("first_month"), on="protocol")
launch = cr[cr.cohort_month == cr.first_month]
size = launch.groupby("protocol").cohort_size.max()
ret = launch.pivot_table(index="protocol", columns="months_since", values="retention_rate", aggfunc="max")
ret = ret.reindex(columns=range(0, 7)).fillna(0.0)
ret[0] = 1.0
ok = size[size >= 100].index
ret = ret.loc[ret.index.intersection(ok)]
per = pd.Series({s: period_of(first[s]) for s in ret.index})
q5 = {"months": list(range(7)), "min_cohort": 100, "periods": {}}
for p in ["before", "between", "after"]:
    sub = ret.loc[per[per == p].index]
    q5["periods"][p] = {"n": int(len(sub)), "median": rl(sub.median().values, 3),
                        "lo": rl(sub.quantile(0.25).values, 3), "hi": rl(sub.quantile(0.75).values, 3)}
cg = read_ts("coef_groups_by_period.csv")
pmap = {"Before Terra": "before", "Terra to Dencun": "between", "After Dencun": "after"}
q5["weights"] = {pmap[p]: {row.group: [r(row.weight, 3), r(row.weight_lo, 3), r(row.weight_hi, 3)]
                           for row in d.itertuples()} for p, d in cg.groupby("period")}
data["q5"] = q5

# Q6: event study around the 10K cumulative crossing
ck = pd.read_csv(EDA / "05_event_checkpoints.csv")
q6 = {}
for metric in ["retention_prev_month", "new_wallet_share", "top10_wallet_share", "share_of_ecosystem_active_wallets"]:
    d = ck[ck.metric == metric]
    if d.empty:
        continue
    q6[metric] = {t: {"rel": d[d.adopter_type == t].rel_month.tolist(),
                      "median": rl(d[d.adopter_type == t]["median"], 4),
                      "n": d[d.adopter_type == t]["n"].tolist()}
                  for t in sorted(d.adopter_type.unique())}
ew = pd.read_csv(EDA / "05_event_window.csv")
data["q6"] = q6


# "What we measure": the dataset itself, and every feature for successful vs other DApps
static = pd.read_csv(V2 / "dapp_static.csv")
life = pd.read_csv(V2 / "dapp_lifecycle.csv")          # every app with any on-chain activity
n_contracts = sum(1 for _ in open(V2 / "app_contracts.csv")) - 1
edges = np.arange(0, 7.5, 0.5)
hist, _ = np.histogram(np.log10(life.peak_wallets.clip(lower=1)), bins=edges)
study = lab  # eligible, not left-censored, label known (k=3)
n_old = int((life.launch_year < 2025).sum())
method = {
    "n_registry": 1816,  # DeFiLlama registry size, as reported in Presentation 2
    "n_static": int(len(static)), "n_contracts": int(n_contracts), "n_active": int(len(life)),
    "n_old": n_old, "n_2025": int((life.launch_year == 2025).sum()),
    "n_study": int(len(study)), "n_pre2020": int(n_old - len(study)),
    "n_success": int((study.y_sustained_12 == 1).sum()),
    "lifecycle": {k: int(v) for k, v in life.lifecycle_label.value_counts().items()},
    "by_cat": {c: int((life.category_group == c).sum()) for c in CATS},
    "by_year": {str(y): int(n) for y, n in life.launch_year.value_counts().sort_index().items()},
    "peak_hist": hist.tolist(), "peak_edges": [float(e) for e in edges],
}
ds = pd.read_csv(MODEL / "dataset_k3.csv")
ds = ds[ds.slug.isin(study.slug)].copy()
groups = read_ts("coef_by_period.csv")[["feature", "group"]].drop_duplicates()
LABEL = {
    "log_mean_wallets": ("Average monthly wallets", "log"), "log_max_wallets": ("Peak monthly wallets", "log"),
    "log_last_wallets": ("Last-month wallets", "log"), "log_mean_wallets_ex_heavy": ("Average wallets, no heavy users", "log"),
    "log_mean_tx": ("Monthly transactions", "log"), "log_mean_gas": ("Monthly gas used", "log"),
    "log_mean_fees": ("Monthly fees (ETH)", "logf"),
    "wallet_growth_slope": ("Growth slope (log wallets / month)", "num"), "last_to_max_ratio": ("Last month vs peak", "pct"),
    "wallet_mom_volatility": ("Month-to-month swings", "num"), "months_since_inwindow_peak": ("Months since the peak", "num"),
    "early_retention": ("Month-to-month retention", "pct"), "cohort_m1_retention": ("First users back next month", "pct"),
    "early_new_wallet_share": ("Wallets that are new", "pct"), "early_returning_share": ("Wallets that return", "pct"),
    "early_tx_per_wallet": ("Transactions per wallet", "num"), "early_gas_per_tx": ("Gas per transaction", "big"),
    "avg_n_protocols_in_tx": ("Apps used in one transaction", "num"),
    "early_whale_share": ("Activity from the top 10 wallets", "pct"), "early_heavy_wallet_share": ("Heavy wallets", "pct"),
    "early_cat_share": ("Share of its category", "pct"), "early_eco_share": ("Share of all DApp wallets", "pct"),
    "launch_cat_growth_3m": ("Category growth at launch", "spct"), "launch_eco_growth_3m": ("Market growth at launch", "spct"),
    "is_new_version_of_existing_protocol": ("New version of an existing app", "yes"), "has_token": ("Has a token", "yes"),
    "launch_year": ("Launch year", "year"),
}
feats = []
for row in groups.itertuples():
    f = row.feature
    label, kind = LABEL[f]
    col = ds[f].astype(float)
    if kind in ("log", "logf"):
        col = np.expm1(col)
    agg = (lambda x: x.mean()) if kind == "yes" else (lambda x: x.median())
    feats.append({"feature": f, "group": row.group, "label": label, "kind": kind,
                  "success": r(agg(col[ds.y_sustained_12 == 1]), 6), "other": r(agg(col[ds.y_sustained_12 == 0]), 6)})
off = pd.read_csv(OFF / "dapp_offchain_by_k.csv")
off = off[(off.k == 3) & off.slug.isin(study.slug)].merge(study[["slug", "y_sustained_12"]], on="slug")
for f, label, kind in [("is_audited", "Audited", "yes"), ("is_open_source", "Open source", "yes"),
                       ("is_verified", "Contract verified", "yes"), ("has_governance", "Has governance", "yes"),
                       ("n_proposals", "Governance proposals, all time", "num"),
                       ("n_proposals_window", "Governance proposals by month k", "num")]:
    col = off[f].astype(float)
    agg = (lambda x: x.mean()) if kind == "yes" else (lambda x: x.mean())
    feats.append({"feature": f, "group": "Off-chain", "label": label, "kind": "yes" if kind == "yes" else "avg",
                  "success": r(agg(col[off.y_sustained_12 == 1]), 4), "other": r(agg(col[off.y_sustained_12 == 0]), 4)})
method["features"] = feats
data["method"] = method


# Diagnose: every DApp's state at each month of age (0 = first month with a user), so a visitor's numbers
# can be compared with DApps of the same age, and we can show what happened to them next.
pp = pd.read_csv(V2 / "dapp_panel.csv", usecols=["slug", "month", "active_wallets", "new_wallets", "tx_count", "top10_wallet_share", "gas_used", "fees_eth", "avg_n_protocols_in_tx"])
pp["month"] = pp["month"].str[:7]
pp = pp.join(first.rename("first_month"), on="slug").dropna(subset=["first_month"])
pp = pp[pp.month >= pp.first_month]
pp["m"] = pp.month.map(mi) - pp.first_month.map(mi)
labmap12 = lab.set_index("slug").y_sustained_12.to_dict()
_cw = panel.pivot_table(index="slug", columns="m", values="cum_wallets", aggfunc="max").reindex(columns=range(13)).ffill(axis=1)
cwall = {k: v for k, v in _cw.iterrows()}
shape = dict(zip(tc.slug, tc.cluster_name.map(lambda x: "flash" if x == "flash_fade" else "grower")))
AGE_W, AGE_F = 36, 24
snap = {}
for row in life.itertuples():
    g = pp[pp.slug == row.slug].set_index("m")
    if g.empty:
        continue
    w = g.active_wallets.reindex(range(AGE_W))
    nw = g.new_wallets.reindex(range(AGE_F))
    snap[row.slug] = {
        "n": row.name, "c": row.category_group, "y": int(row.launch_year), "l": row.lifecycle_label,
        "lm": first.get(row.slug), "cw": [None if pd.isna(v) else int(v) for v in cwall.get(row.slug, pd.Series(dtype=float)).reindex(range(13))],
        "s": None if row.slug not in labmap12 or pd.isna(labmap12[row.slug]) else int(labmap12[row.slug]),
        "g": shape.get(row.slug),
        "w": [None if pd.isna(v) else int(v) for v in w],
        "t": [None if pd.isna(v) else int(v) for v in g.tx_count.reindex(range(AGE_F))],
        "ns": [None if pd.isna(a) or pd.isna(b) or b <= 0 else round(float(a) / float(b), 2) for a, b in zip(nw, w[:AGE_F])],
        "wh": [None if pd.isna(v) else round(float(v), 2) for v in g.top10_wallet_share.reindex(range(AGE_F))],
        # third month (age 2) only, for the success map's extra axes
        "m3": {k: (None if pd.isna(v) else (round(float(v), 4) if k != "gas" else int(v))) for k, v in
               {"gas": g.gas_used.get(2), "fee": g.fees_eth.get(2), "apps": g.avg_n_protocols_in_tx.get(2)}.items()},
    }
data["snap"] = snap

# Leaders: for each era and category, every DApp's average monthly active wallets inside the era window,
# its share of the category, and its rank (the scenario walks use the top five and the visitor's DApp)
ERAS = {"before": ("2020-01", "2022-04"), "between": ("2022-05", "2024-02"), "after": ("2024-03", "2025-12")}
lp = pd.read_csv(V2 / "dapp_panel.csv", usecols=["slug", "month", "active_wallets", "category_group"])
lp["month"] = lp["month"].str[:7]
lname = life.set_index("slug").name.to_dict()
lead = {}
for e, (a0, b0) in ERAS.items():
    w = lp[(lp.month >= a0) & (lp.month <= b0)]
    nmon = w.month.nunique()
    g = w.groupby(["category_group", "slug"]).active_wallets.sum() / max(nmon, 1)
    lead[e] = {}
    for cat, sr in g.groupby(level=0):
        sr = sr.droplevel(0)
        sr = sr[sr > 0].sort_values(ascending=False)
        tot = float(sr.sum()) or 1.0
        lead[e][cat] = {"n": int(len(sr)), "tot": int(round(tot)),
                        "all": {slug: [int(round(v)), round(float(v) / tot, 4), i + 1] for i, (slug, v) in enumerate(sr.items())},
                        "top": [[slug, lname.get(slug, slug), int(round(v)), round(float(v) / tot, 4)] for slug, v in sr.head(5).items()]}
data["lead"] = lead
data["meta"]["snap_ages"] = AGE_F

# Per-DApp series for the picker (the 170 adopted DApps)
aw = panel.pivot_table(index="slug", columns="m", values="active_wallets", aggfunc="max").reindex(columns=range(24))
labmap = lab.set_index("slug").y_sustained_12.to_dict()
dapps = {}
for row in tc.itertuples():
    s = row.slug
    e = ew[ew.slug == s].set_index("rel_month")
    dapps[s] = {
        "name": row.name, "cat": row.category_group, "launch": first.get(s, row.launch_month[:7]),
        "period": period_of(first.get(s, row.launch_month[:7])),
        "group": row.group, "peak": int(row.peak_wallets),
        "success": None if s not in labmap else int(labmap[s]),
        "wallets": [None if pd.isna(v) else int(v) for v in aw.loc[s].values] if s in aw.index else [],
        "norm": rl(tn.loc[s, mcols].values, 3) if s in tn.index else [],
        "cum": [None if pd.isna(v) else int(v) for v in cw.loc[s].values] if s in cw.index else [],
        "ret": rl(ret.loc[s].values, 3) if s in ret.index else None,
        "event": {"rel": e.index.tolist(), "retention_prev_month": rl(e.retention_prev_month, 3),
                  "new_wallet_share": rl(e.new_wallet_share, 3)} if len(e) else None,
    }
data["dapps"] = dapps
data["featured"] = [s for s in FEATURED if s in dapps]

OUT.write_text("window.DEMO = " + json.dumps(data, separators=(",", ":")) + ";\n")
print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB)")
print("Q4 n:", q4["n"], "10K by m6:", q4["share_10k"]["success"][6], q4["share_10k"]["other"][6])
print("Q2:", q2["counts"])
print("Q5 n:", {p: v["n"] for p, v in q5["periods"].items()}, "m6:", {p: v["median"][6] for p, v in q5["periods"].items()})
print("Q3 2025:", q3["rank_curve"]["2025"]["n"], "top10:", q3["rank_curve"]["2025"]["share"][4])
print("Q6 keys:", list(q6))
