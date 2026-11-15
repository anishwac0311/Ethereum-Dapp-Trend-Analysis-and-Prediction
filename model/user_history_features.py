"""Iteration-4 features: brand, time-aware base rates, users' on-chain history, value.

All inputs are known at prediction time (launch + k months):

Brand / context (from the monthly panel)
  parent_n_prior_versions   earlier launches of the same parent protocol
  parent_log_wallets_pre    log wallets of the parent's other versions in the month before launch
  parent_proven             an earlier version already had 1,000+ wallets at months 10-12,
                            and that outcome was observable before launch + k
  cat_recent_success        shrunk success rate of same-category launches whose month-12
                            outcome was observable before launch + k (last 24 months)
  eco_recent_success        same for all categories (captures the market regime)
  log_value_per_wallet      ETH moved per active wallet in the window
  log_fees_per_wallet       fees (ETH) paid per active wallet in the window

Users' on-chain history (from dapp_v2.duckdb, the 6 months before launch)
  user_fresh_share          window users with no Ethereum activity before launch
  user_prior_active_months  mean months active anywhere in the 6 months before launch
  user_prior_loyalty        mean active months per protocol used before launch (stickiness type)
  user_proven_share         users who used an app already proven to last (outcome known by launch)

Output: model/wallet_features/data/user_history_by_k.csv

  python model/user_history_features.py            # skip if cached
  python model/user_history_features.py --refresh
"""
from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

from common import DATA, annotate_lifecycle, load_lifecycle, load_panel, load_static
from wallet_features import OUT_DIR

DB = DATA / "dapp_v2.duckdb"
OUT = OUT_DIR / "user_history_by_k.csv"
LOOKBACK = 6
PROVEN_WALLETS = 1_000
RATE_WINDOW_MONTHS = 24
SHRINK = 5.0

BRAND_FEATURES = ["parent_n_prior_versions", "parent_log_wallets_pre", "parent_proven",
                  "cat_recent_success", "eco_recent_success", "log_value_per_wallet",
                  "log_fees_per_wallet"]
USER_FEATURES = ["user_fresh_share", "user_prior_active_months", "user_prior_loyalty",
                 "user_proven_share"]
USER_HISTORY_FEATURES = BRAND_FEATURES + USER_FEATURES


def _launches() -> pd.DataFrame:
    life = annotate_lifecycle(load_lifecycle(), load_static()).drop_duplicates("slug")
    life = life[life["launch_month"].notna()].copy()
    life["launch_month"] = pd.to_datetime(life["launch_month"]).dt.to_period("M").dt.to_timestamp()
    life["parent_protocol"] = life["parent_protocol"].fillna(life["slug"])
    return life[["slug", "parent_protocol", "category_group", "launch_month", "left_censored"]]


def _outcomes(panel: pd.DataFrame, L: pd.DataFrame) -> pd.DataFrame:
    """Per DApp: proven flag (mean wallets at months 10-12 >= 1,000) and the date it is known."""
    p = panel[(panel["months_since_launch"] >= 9) & (panel["months_since_launch"] <= 11)]
    m = p.groupby("slug").agg(m1012=("active_wallets", "mean"), n=("active_wallets", "size"))
    m = m[m["n"] == 3]
    o = L.merge(m, left_on="slug", right_index=True, how="inner")
    o["proven"] = (o["m1012"] >= PROVEN_WALLETS).astype(int)
    o["known_at"] = o["launch_month"] + pd.DateOffset(months=12)  # first month after label window
    return o[["slug", "parent_protocol", "category_group", "launch_month", "proven", "known_at"]]


def brand_features(ks: list[int], panel: pd.DataFrame, L: pd.DataFrame) -> pd.DataFrame:
    panel = panel.copy()
    panel["month"] = pd.to_datetime(panel["month"]).dt.to_period("M").dt.to_timestamp()
    panel["parent_protocol"] = panel["slug"].map(L.set_index("slug")["parent_protocol"]).fillna(panel["slug"])
    out_ = _outcomes(panel, L)
    pw = panel.groupby(["parent_protocol", "slug", "month"])["active_wallets"].sum().reset_index()
    base_rate = out_["proven"].mean()
    rows = []
    for k in ks:
        for r in L.itertuples(index=False):
            cutoff = r.launch_month + pd.DateOffset(months=k)  # first month NOT observed
            sib = L[(L["parent_protocol"] == r.parent_protocol) & (L["slug"] != r.slug)
                    & (L["launch_month"] < r.launch_month)]
            pre = pw[(pw["parent_protocol"] == r.parent_protocol) & (pw["slug"] != r.slug)
                     & (pw["month"] == r.launch_month - pd.DateOffset(months=1))]
            known = out_[(out_["known_at"] <= cutoff) & (out_["slug"] != r.slug)]
            sib_known = known[known["parent_protocol"] == r.parent_protocol]
            recent = known[known["launch_month"] >= cutoff - pd.DateOffset(months=RATE_WINDOW_MONTHS + 12)]
            cat = recent[recent["category_group"] == r.category_group]
            win = panel[(panel["slug"] == r.slug) & (panel["months_since_launch"] >= 0)
                        & (panel["months_since_launch"] < k)]
            aw = win["active_wallets"].sum()
            rows.append({
                "slug": r.slug, "k": k,
                "parent_n_prior_versions": len(sib),
                "parent_log_wallets_pre": float(np.log1p(pre["active_wallets"].sum())),
                "parent_proven": int(sib_known["proven"].max()) if len(sib_known) else 0,
                "cat_recent_success": (cat["proven"].sum() + SHRINK * base_rate) / (len(cat) + SHRINK),
                "eco_recent_success": (recent["proven"].sum() + SHRINK * base_rate) / (len(recent) + SHRINK),
                "log_value_per_wallet": float(np.log1p(win["eth_value"].sum() / aw)) if aw > 0 else np.nan,
                "log_fees_per_wallet": float(np.log1p(1e3 * win["fees_eth"].sum() / aw)) if aw > 0 else np.nan,
            })
    return pd.DataFrame(rows)


def user_features(ks: list[int], panel: pd.DataFrame, L: pd.DataFrame) -> pd.DataFrame:
    import duckdb

    t0 = time.time()
    kmax = max(ks)
    out_ = _outcomes(panel, L)
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    tmp = OUT_DIR / "_duckdb_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET temp_directory='{tmp.as_posix()}'")
    con.execute(f"ATTACH '{DB.as_posix()}' AS src (READ_ONLY)")
    con.register("l_df", L[["slug", "launch_month"]])
    con.register("o_df", out_[["slug", "proven", "known_at"]])
    con.execute("CREATE TEMP TABLE L AS SELECT slug, CAST(launch_month AS DATE) lm FROM l_df")
    con.execute("CREATE TEMP TABLE PROVEN AS SELECT slug, CAST(known_at AS DATE) known_at "
                "FROM o_df WHERE proven = 1")
    print("  window users ...")
    con.execute(f"""
        CREATE TEMP TABLE WU AS
        SELECT l.slug, w.wallet, l.lm, min(date_diff('month', l.lm, w.month)) AS first_age
        FROM src.wallet_month_v2 w JOIN L l ON w.protocol = l.slug
        WHERE w.month >= l.lm AND w.month < l.lm + INTERVAL {kmax} MONTH
          AND NOT EXISTS (SELECT 1 FROM src.heavy_wallets h
                          WHERE h.wallet = w.wallet AND h.month = w.month)
        GROUP BY 1, 2, 3
    """)
    print(f"    {con.execute('SELECT count(*) FROM WU').fetchone()[0]:,} ({time.time()-t0:.0f}s)")
    print("  pre-launch history ...")
    con.execute(f"""
        CREATE TEMP TABLE HIST AS
        SELECT u.slug, u.wallet,
               count(DISTINCT w.month) AS act_months,
               count(DISTINCT w.protocol) AS n_prot,
               count(*) AS prot_months,
               max(CASE WHEN p.slug IS NOT NULL THEN 1 ELSE 0 END) AS used_proven
        FROM WU u
        JOIN src.wallet_month_v2 w ON w.wallet = u.wallet
        LEFT JOIN PROVEN p ON p.slug = w.protocol AND p.known_at <= u.lm
        WHERE w.month < u.lm AND w.month >= u.lm - INTERVAL {LOOKBACK} MONTH
          AND w.protocol <> u.slug
        GROUP BY 1, 2
    """)
    print(f"    ({time.time()-t0:.0f}s)")
    rows = []
    for k in ks:
        df = con.execute(f"""
            SELECT u.slug,
                   avg(CASE WHEN h.wallet IS NULL THEN 1.0 ELSE 0.0 END) AS user_fresh_share,
                   avg(coalesce(h.act_months, 0)) AS user_prior_active_months,
                   avg(h.prot_months * 1.0 / h.n_prot) AS user_prior_loyalty,
                   avg(coalesce(h.used_proven, 0)) AS user_proven_share
            FROM WU u LEFT JOIN HIST h ON h.slug = u.slug AND h.wallet = u.wallet
            WHERE u.first_age < {k}
            GROUP BY 1
        """).df()
        df["k"] = k
        rows.append(df)
    con.close()
    return pd.concat(rows, ignore_index=True)


def build(ks: list[int]) -> pd.DataFrame:
    panel = load_panel()
    L = _launches()
    print("  brand / base-rate features ...")
    b = brand_features(ks, panel, L)
    u = user_features(ks, panel, L)
    res = b.merge(u, on=["slug", "k"], how="left")
    return res[["slug", "k", *USER_HISTORY_FEATURES]]


def merge_user_history(ds: pd.DataFrame, k: int) -> pd.DataFrame:
    ds = ds.drop(columns=[c for c in USER_HISTORY_FEATURES if c in ds.columns])
    if not OUT.exists():
        for c in USER_HISTORY_FEATURES:
            ds[c] = np.nan
        return ds
    t = pd.read_csv(OUT)
    t = t[t["k"] == k][["slug", *USER_HISTORY_FEATURES]]
    return ds.merge(t, on="slug", how="left")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, nargs="+", default=[1, 3, 6])
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    print("== user_history_features ==")
    if OUT.exists() and not args.refresh:
        print(f"  cached: {OUT} (use --refresh to rebuild)")
        return
    res = build(args.k)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT, index=False)
    print(f"  saved {OUT}")
    for k in args.k:
        sub = res[res["k"] == k]
        print(f"  k={k} n={len(sub)} coverage={sub[USER_HISTORY_FEATURES].notna().mean().round(2).to_dict()}")
    print("== user_history_features done ==")


if __name__ == "__main__":
    main()
