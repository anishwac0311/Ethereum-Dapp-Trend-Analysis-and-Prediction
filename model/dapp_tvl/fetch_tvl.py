"""Ethereum TVL history per DApp from DeFiLlama, cut to the observation window.

The old `tvl` column is today's snapshot (leaky). Here we take the DAILY Ethereum
TVL series per slug and keep only dates before launch_month + k months.

  python model/dapp_tvl/fetch_tvl.py            # fetch missing slugs, build features
  python model/dapp_tvl/fetch_tvl.py --refresh  # refetch everything

Outputs:
  data/raw/<slug>.json.gz       cached daily Ethereum TVL (date, tvl_usd)
  data/tvl_monthly.csv          slug, month, mean Ethereum TVL (USD)
  data/dapp_tvl_by_k.csv        window features per (slug, k)
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import annotate_lifecycle, load_lifecycle, load_panel, load_static  # noqa: E402

RAW = HERE / "data" / "raw"
MONTHLY = HERE / "data" / "tvl_monthly.csv"
OUT = HERE / "data" / "dapp_tvl_by_k.csv"
API = "https://api.llama.fi/protocol/{slug}"
SLEEP = 0.4

TVL_FEATURES = [
    "has_tvl",
    "log_mean_tvl",
    "log_last_tvl",
    "tvl_growth_slope",
    "tvl_last_to_max",
    "log_tvl_per_wallet",
    "tvl_cat_share",
    "tvl_before_launch",
]


def fetch_one(slug: str, session: requests.Session) -> list[list]:
    """Daily Ethereum TVL as [[unix_date, usd], ...]; [] if none / not listed."""
    try:
        r = session.get(API.format(slug=slug), timeout=60)
        if r.status_code != 200:
            return []
        js = r.json()
    except Exception:
        return []
    eth = (js.get("chainTvls") or {}).get("Ethereum", {}).get("tvl") or []
    return [[int(p["date"]), float(p.get("totalLiquidityUSD") or 0.0)] for p in eth]


def fetch_all(slugs: list[str], refresh: bool = False) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    s.headers["User-Agent"] = "dapp-research/0.1"
    todo = [x for x in slugs if refresh or not (RAW / f"{x}.json.gz").exists()]
    print(f"  fetching {len(todo)} of {len(slugs)} slugs ...")
    for i, slug in enumerate(todo, 1):
        pts = fetch_one(slug, s)
        with gzip.open(RAW / f"{slug}.json.gz", "wt") as f:
            json.dump(pts, f)
        if i % 50 == 0:
            print(f"    {i}/{len(todo)}")
        time.sleep(SLEEP)


def monthly_table(slugs: list[str]) -> pd.DataFrame:
    rows = []
    for slug in slugs:
        p = RAW / f"{slug}.json.gz"
        if not p.exists():
            continue
        with gzip.open(p, "rt") as f:
            pts = json.load(f)
        if not pts:
            continue
        d = pd.DataFrame(pts, columns=["date", "tvl_usd"])
        d["month"] = pd.to_datetime(d["date"], unit="s").dt.to_period("M").dt.to_timestamp()
        m = d.groupby("month")["tvl_usd"].mean().reset_index()
        m["slug"] = slug
        rows.append(m)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["month", "tvl_usd", "slug"])


def window_features(tvl: pd.DataFrame, ks: list[int]) -> pd.DataFrame:
    life = annotate_lifecycle(load_lifecycle(), load_static()).drop_duplicates("slug")
    life = life[life["launch_month"].notna()]
    panel = load_panel()[["slug", "month", "active_wallets"]]
    panel["month"] = pd.to_datetime(panel["month"]).dt.to_period("M").dt.to_timestamp()
    tvl = tvl.merge(life[["slug", "category_group"]], on="slug", how="left")
    cat_tot = tvl.groupby(["month", "category_group"])["tvl_usd"].sum().rename("cat_tvl")
    tvl = tvl.join(cat_tot, on=["month", "category_group"])
    by_slug = dict(tuple(tvl.groupby("slug")))
    wal = dict(tuple(panel.groupby("slug")))

    rows = []
    for _, r in life.iterrows():
        slug = r["slug"]
        lm = pd.Timestamp(r["launch_month"]).to_period("M").to_timestamp()
        g = by_slug.get(slug)
        for k in ks:
            end = lm + pd.DateOffset(months=k)
            row = {"slug": slug, "k": k, "has_tvl": 0}
            if g is not None:
                w = g[(g["month"] >= lm) & (g["month"] < end)].sort_values("month")
                pre = g[g["month"] < lm]
                row["tvl_before_launch"] = int((pre["tvl_usd"] > 0).any())
                v = w["tvl_usd"].values
                if len(v) and v.max() > 0:
                    lv = np.log1p(v)
                    aw = wal.get(slug)
                    mean_w = (aw[(aw["month"] >= lm) & (aw["month"] < end)]["active_wallets"].mean()
                              if aw is not None else np.nan)
                    row.update({
                        "has_tvl": 1,
                        "log_mean_tvl": float(np.log1p(v.mean())),
                        "log_last_tvl": float(lv[-1]),
                        "tvl_growth_slope": float(np.polyfit(np.arange(len(lv)), lv, 1)[0]) if len(lv) >= 2 else np.nan,
                        "tvl_last_to_max": float(v[-1] / v.max()),
                        "log_tvl_per_wallet": float(np.log1p(v.mean() / mean_w)) if mean_w and mean_w > 0 else np.nan,
                        "tvl_cat_share": float((w["tvl_usd"] / w["cat_tvl"].replace(0, np.nan)).mean()),
                    })
            rows.append(row)
    out = pd.DataFrame(rows)
    for c in TVL_FEATURES:
        if c not in out.columns:
            out[c] = np.nan
    return out[["slug", "k", *TVL_FEATURES]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, nargs="+", default=[1, 3, 6])
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()
    print("== dapp_tvl ==")
    life = annotate_lifecycle(load_lifecycle(), load_static())
    slugs = sorted(life["slug"].dropna().unique())
    if not args.no_fetch:
        fetch_all(slugs, refresh=args.refresh)
    tvl = monthly_table(slugs)
    tvl.to_csv(MONTHLY, index=False)
    feats = window_features(tvl, args.k)
    feats.to_csv(OUT, index=False)
    print(f"  saved {OUT}")
    for k in args.k:
        sub = feats[feats["k"] == k]
        print(f"  k={k}: {len(sub)} DApps, with Ethereum TVL in window: {sub['has_tvl'].mean():.2f}")
    print("== dapp_tvl done ==")


if __name__ == "__main__":
    main()
