"""Wallet-level early features from the local DuckDB (dapp_data_v2/dapp_v2.duckdb).

Everything is cut at the observation window: launch months 0..k-1 (calendar dates
[launch_month, launch_month + k months)). The only pre-window inputs are other
DApps' activity *before* launch, which is known at prediction time.

Opens the 10 GB DB read-only; scratch tables live in an in-memory connection.
Output: model/wallet_features/data/wallet_features_by_k.csv (one row per slug, k).

  python model/wallet_features.py            # k = 1 3 6, skip if cached
  python model/wallet_features.py --refresh
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from common import DATA, annotate_lifecycle, load_lifecycle, load_panel, load_static

DB = DATA / "dapp_v2.duckdb"
OUT_DIR = Path(__file__).resolve().parent / "wallet_features" / "data"
OUT = OUT_DIR / "wallet_features_by_k.csv"

EXPERIENCED_DAYS = 90
PRIOR_LOOKBACK_MONTHS = 3
TOP_DECILE = 0.90

WALLET_FEATURES = [
    # weekly / daily acquisition shape
    "acq_last4w_share",
    "acq_week_slope",
    "acq_peak_week_frac",
    "acq_top_day_share",
    # user quality
    "user_experienced_share",
    "user_single_tx_share",
    "user_tx_gini",
    # stickiness
    "user_m0_to_last_retention",
    "user_multi_month_share",
    "user_mean_active_months",
    # cross-DApp overlap
    "user_prior_top_dapp_share",
    "user_multihoming",
]


def _launch_table(ks: list[int]) -> pd.DataFrame:
    life = annotate_lifecycle(load_lifecycle(), load_static())
    life = life[life["launch_month"].notna()].copy()
    lm = pd.to_datetime(life["launch_month"]).dt.to_period("M").dt.to_timestamp()
    base = pd.DataFrame({"slug": life["slug"].values, "launch_month": lm.values,
                         "parent_protocol": life["parent_protocol"].fillna(life["slug"]).values})
    return base.drop_duplicates("slug")


def _top_decile_by_month(panel: pd.DataFrame) -> pd.DataFrame:
    """(month, protocol) pairs in that month's top wallet decile. Uses only that month's data."""
    p = panel[["slug", "month", "active_wallets"]].copy()
    p["month"] = pd.to_datetime(p["month"]).dt.to_period("M").dt.to_timestamp()
    q = p.groupby("month")["active_wallets"].transform(lambda s: s.quantile(TOP_DECILE))
    top = p[p["active_wallets"] >= q][["month", "slug"]].rename(columns={"slug": "protocol"})
    return top.reset_index(drop=True)


def _gini(x: np.ndarray) -> float:
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    if n == 0 or x.sum() <= 0:
        return np.nan
    ranks = np.arange(1, n + 1)
    return float(2 * np.sum(ranks * x) / (n * x.sum()) - (n + 1) / n)


def _acq_shape(daily: pd.DataFrame, k: int) -> pd.DataFrame:
    """Acquisition shape from daily first-seen counts within the window."""
    rows = []
    for slug, g in daily.groupby("slug"):
        n_days = int(g["window_days"].iloc[0])
        counts = np.zeros(n_days)
        d = g["day"].values.astype(int)
        ok = (d >= 0) & (d < n_days)
        np.add.at(counts, d[ok], g["n_new"].values[ok])
        total = counts.sum()
        if total <= 0:
            continue
        n_weeks = int(np.ceil(n_days / 7))
        weekly = np.array([counts[i * 7:(i + 1) * 7].sum() for i in range(n_weeks)])
        y = np.log1p(weekly)
        slope = float(np.polyfit(np.arange(n_weeks), y, 1)[0]) if n_weeks >= 3 else np.nan
        rows.append({
            "slug": slug,
            "k": k,
            "acq_last4w_share": float(counts[-28:].sum() / total),
            "acq_week_slope": slope,
            "acq_peak_week_frac": float(np.argmax(weekly) / max(n_weeks - 1, 1)),
            "acq_top_day_share": float(counts.max() / total),
        })
    return pd.DataFrame(rows)


def build(ks: list[int]) -> pd.DataFrame:
    import duckdb

    t0 = time.time()
    kmax = max(ks)
    launches = _launch_table(ks)
    panel = load_panel()
    top = _top_decile_by_month(panel)

    con = duckdb.connect()  # scratch, in-memory
    con.execute("SET preserve_insertion_order=false")
    tmp = OUT_DIR / "_duckdb_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET temp_directory='{tmp.as_posix()}'")
    con.execute(f"ATTACH '{DB.as_posix()}' AS src (READ_ONLY)")
    con.register("launches_df", launches)
    con.register("top_df", top)
    con.execute("""
        CREATE TEMP TABLE L AS
        SELECT slug, parent_protocol, CAST(launch_month AS DATE) AS launch_month FROM launches_df
    """)
    con.execute("CREATE TEMP TABLE TOPD AS SELECT CAST(month AS DATE) AS month, protocol FROM top_df")

    # Wallet-months inside the widest window, heavy wallets removed
    print(f"  wallet-months in first {kmax} months ...")
    con.execute(f"""
        CREATE TEMP TABLE WM AS
        SELECT l.slug, w.wallet, w.month,
               date_diff('month', l.launch_month, w.month) AS age,
               w.tx_count, w.n_protocols_avg
        FROM src.wallet_month_v2 w
        JOIN L l ON w.protocol = l.slug
        WHERE w.month >= l.launch_month
          AND w.month < l.launch_month + INTERVAL {kmax} MONTH
          AND NOT EXISTS (SELECT 1 FROM src.heavy_wallets h
                          WHERE h.wallet = w.wallet AND h.month = w.month)
    """)
    print(f"    rows={con.execute('SELECT count(*) FROM WM').fetchone()[0]:,} ({time.time()-t0:.0f}s)")

    # Per-protocol first use for window wallets (needed for experience)
    print("  first-seen dates ...")
    con.execute("""
        CREATE TEMP TABLE FS AS
        SELECT f.protocol AS slug, f.wallet, f.first_date
        FROM src.wallet_first_seen f
        JOIN L l ON f.protocol = l.slug
    """)
    con.execute("""
        CREATE TEMP TABLE WW AS
        SELECT DISTINCT slug, wallet FROM WM
    """)
    # Earliest first-seen on any OTHER protocol, for window wallets only
    con.execute("""
        CREATE TEMP TABLE OTHER_FIRST AS
        SELECT ww.slug, ww.wallet, min(f.first_date) AS other_first
        FROM WW ww
        JOIN src.wallet_first_seen f ON f.wallet = ww.wallet AND f.protocol <> ww.slug
        GROUP BY 1, 2
    """)
    print(f"    ({time.time()-t0:.0f}s)")

    # Pre-launch activity on top-decile DApps (excluding same parent)
    print("  prior top-DApp usage ...")
    con.execute(f"""
        CREATE TEMP TABLE PRIOR_TOP AS
        SELECT DISTINCT ww.slug, ww.wallet
        FROM WW ww
        JOIN L l ON l.slug = ww.slug
        JOIN src.wallet_month_v2 w ON w.wallet = ww.wallet
        JOIN TOPD t ON t.protocol = w.protocol AND t.month = w.month
        LEFT JOIN L lp ON lp.slug = w.protocol
        WHERE w.month < l.launch_month
          AND w.month >= l.launch_month - INTERVAL {PRIOR_LOOKBACK_MONTHS} MONTH
          AND w.protocol <> ww.slug
          AND coalesce(lp.parent_protocol, w.protocol) <> l.parent_protocol
    """)
    print(f"    ({time.time()-t0:.0f}s)")

    out = []
    for k in ks:
        print(f"  aggregating k={k} ...")
        per_wallet = con.execute(f"""
            SELECT wm.slug, wm.wallet,
                   count(DISTINCT wm.age) AS n_months,
                   sum(wm.tx_count) AS tx,
                   avg(wm.n_protocols_avg) AS nprot,
                   max(CASE WHEN wm.age = 0 THEN 1 ELSE 0 END) AS in_m0,
                   max(CASE WHEN wm.age = {k - 1} THEN 1 ELSE 0 END) AS in_last,
                   min(fs.first_date) AS own_first,
                   min(o.other_first) AS other_first,
                   max(CASE WHEN p.wallet IS NOT NULL THEN 1 ELSE 0 END) AS prior_top
            FROM WM wm
            LEFT JOIN FS fs ON fs.slug = wm.slug AND fs.wallet = wm.wallet
            LEFT JOIN OTHER_FIRST o ON o.slug = wm.slug AND o.wallet = wm.wallet
            LEFT JOIN PRIOR_TOP p ON p.slug = wm.slug AND p.wallet = wm.wallet
            WHERE wm.age < {k}
            GROUP BY 1, 2
        """).df()
        per_wallet["experienced"] = (
            per_wallet["other_first"].notna()
            & per_wallet["own_first"].notna()
            & ((pd.to_datetime(per_wallet["own_first"])
                - pd.to_datetime(per_wallet["other_first"])).dt.days >= EXPERIENCED_DAYS)
        ).astype(float)

        def agg(g: pd.DataFrame) -> pd.Series:
            m0 = g["in_m0"] == 1
            return pd.Series({
                "user_experienced_share": g["experienced"].mean(),
                "user_single_tx_share": float((g["tx"] <= 1).mean()),
                "user_tx_gini": _gini(g["tx"].values),
                "user_m0_to_last_retention": (
                    float(g.loc[m0, "in_last"].mean()) if k >= 2 and m0.any() else np.nan
                ),
                "user_multi_month_share": float((g["n_months"] >= 2).mean()) if k >= 2 else np.nan,
                "user_mean_active_months": float(g["n_months"].mean()),
                "user_prior_top_dapp_share": float(g["prior_top"].mean()),
                "user_multihoming": float(g["nprot"].mean()),
            })

        users = per_wallet.groupby("slug").apply(agg, include_groups=False).reset_index()
        users["k"] = k

        daily = con.execute(f"""
            SELECT fs.slug,
                   date_diff('day', l.launch_month, fs.first_date) AS day,
                   date_diff('day', l.launch_month, l.launch_month + INTERVAL {k} MONTH) AS window_days,
                   count(*) AS n_new
            FROM FS fs JOIN L l ON l.slug = fs.slug
            WHERE fs.first_date >= l.launch_month
              AND fs.first_date < l.launch_month + INTERVAL {k} MONTH
            GROUP BY 1, 2, 3
        """).df()
        acq = _acq_shape(daily, k)
        out.append(users.merge(acq, on=["slug", "k"], how="outer"))
        print(f"    slugs={len(users)} ({time.time()-t0:.0f}s)")

    con.close()
    res = pd.concat(out, ignore_index=True)
    return res[["slug", "k", *WALLET_FEATURES]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, nargs="+", default=[1, 3, 6])
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    print("== wallet_features ==")
    if OUT.exists() and not args.refresh:
        print(f"  cached: {OUT} (use --refresh to rebuild)")
        return
    if not DB.exists():
        print(f"  missing {DB}; skip")
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    res = build(args.k)
    res.to_csv(OUT, index=False)
    print(f"  saved {OUT}")
    for k in args.k:
        sub = res[res["k"] == k]
        cov = sub[WALLET_FEATURES].notna().mean().round(2).to_dict()
        print(f"  k={k} n={len(sub)} coverage={cov}")
    print("== wallet_features done ==")


if __name__ == "__main__":
    main()
