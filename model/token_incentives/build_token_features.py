"""Token-incentive / airdrop features from on-chain ERC-20 transfers (AWS public data).

Why: the biggest unknown at month 3 is whether usage is being bought with token
incentives that will end. For each DApp with its own token we scan that token's
transfers from 3 months before launch to the end of the widest window, and measure
(cut at launch + k months, never later):

  token_live               token moved before the window ended
  token_pre_launch         token moved before the DApp's launch month
  log_token_recipients     distinct recipients in the window
  token_recipient_growth   recipients in the last window month / monthly mean
  airdrop_share            recipients who got the token from a fan-out sender
                           (>= FANOUT distinct recipients in one day, DEX contracts excluded)
  reward_share             share of window transfers sent by the DApp's own contracts
                           (staking rewards, emissions, claims)
  reward_ramp              own-contract recipients in last window month / max month
  user_token_share         share of the DApp's window users who received the token

Scans are resumable (one month at a time) into a local scratch DuckDB.

  python model/token_incentives/build_token_features.py            # scan + build (skips if cached)
  python model/token_incentives/build_token_features.py --refresh  # resume/extend scan + build
  python model/token_incentives/build_token_features.py --no-scan  # rebuild features only
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import DATA, annotate_lifecycle, load_lifecycle, load_static  # noqa: E402

BASE = "s3://aws-public-blockchain/v1.0/eth"
SRC_DB = DATA / "dapp_v2.duckdb"
SCAN_DB = HERE / "data" / "_token_scan.duckdb"
OUT = HERE / "data" / "dapp_token_by_k.csv"
PRE_MONTHS = 3
K_MAX = 6
FANOUT = 100
MONTH_TIMEOUT_S = 600  # watchdog: interrupt and retry a month that hangs (e.g. after sleep)

TOKEN_FEATURES = [
    "token_live",
    "token_pre_launch",
    "log_token_recipients",
    "token_recipient_growth",
    "airdrop_share",
    "reward_share",
    "reward_ramp",
    "user_token_share",
]

# Tokens that are infrastructure, not a DApp's own incentive token
SKIP_TOKENS = {
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",  # WETH
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # USDC
    "0xdac17f958d2ee523a2206206994597c13d831ec7",  # USDT
    "0x6b175474e89094c44da98b954eedeac495271d0f",  # DAI
}


def dapp_tokens() -> pd.DataFrame:
    life = annotate_lifecycle(load_lifecycle(), load_static()).drop_duplicates("slug")
    prot = pd.read_csv(DATA / "protocols.csv", usecols=["slug", "token_address"])
    d = life[["slug", "launch_month", "category_group"]].merge(prot, on="slug", how="left")
    d = d[d["launch_month"].notna()].copy()
    d["token"] = d["token_address"].astype(str).str.lower().str.strip()
    d = d[d["token"].str.match(r"^0x[0-9a-f]{40}$") & ~d["token"].isin(SKIP_TOKENS)]
    d["launch_month"] = pd.to_datetime(d["launch_month"]).dt.to_period("M").dt.to_timestamp()
    return d[["slug", "token", "launch_month", "category_group"]].reset_index(drop=True)


def months_to_tokens(d: pd.DataFrame) -> dict[pd.Timestamp, set[str]]:
    m: dict[pd.Timestamp, set[str]] = {}
    for _, r in d.iterrows():
        for off in range(-PRE_MONTHS, K_MAX):
            mo = r["launch_month"] + pd.DateOffset(months=off)
            if mo > pd.Timestamp("2025-12-01"):
                continue
            m.setdefault(mo, set()).add(r["token"])
    return dict(sorted(m.items()))


def scan(d: pd.DataFrame) -> None:
    import duckdb

    SCAN_DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(SCAN_DB))
    con.execute("INSTALL httpfs; LOAD httpfs; SET s3_region='us-east-2';")
    con.execute("SET http_retries=6; SET http_retry_wait_ms=2000")
    try:
        con.execute("CREATE OR REPLACE SECRET aws_anon (TYPE s3, REGION 'us-east-2')")
    except Exception:
        pass
    con.execute("""CREATE TABLE IF NOT EXISTS raw
                   (token VARCHAR, from_address VARCHAR, to_address VARCHAR, date DATE)""")
    con.execute("CREATE TABLE IF NOT EXISTS done (month DATE)")
    done = {pd.Timestamp(r[0]) for r in con.execute("SELECT month FROM done").fetchall()}
    plan = months_to_tokens(d)
    todo = [(m, t) for m, t in plan.items() if m not in done]
    print(f"  scanning {len(todo)} of {len(plan)} months ...")
    t0 = time.time()
    for i, (mo, toks) in enumerate(todo, 1):
        tok_list = ",".join(f"'{t}'" for t in sorted(toks))
        glob = f"{BASE}/token_transfers/date={mo:%Y-%m}-*/*.parquet"
        for attempt in range(4):
            watchdog = threading.Timer(MONTH_TIMEOUT_S, con.interrupt)
            watchdog.start()
            try:
                con.execute("BEGIN")
                con.execute(f"""
                    INSERT INTO raw
                    SELECT token_address, from_address, to_address, CAST(date AS DATE)
                    FROM read_parquet('{glob}', hive_partitioning=true)
                    WHERE token_address IN ({tok_list})
                """)
                con.execute(f"INSERT INTO done VALUES ('{mo:%Y-%m-%d}')")
                con.execute("COMMIT")
                watchdog.cancel()
                break
            except Exception as e:
                watchdog.cancel()
                try:
                    con.execute("ROLLBACK")
                except Exception:
                    pass
                print(f"    {mo:%Y-%m} attempt {attempt + 1} failed: {e}")
                time.sleep(10)
        n = con.execute("SELECT count(*) FROM raw").fetchone()[0]
        print(f"    {i}/{len(todo)} {mo:%Y-%m}: {len(toks)} tokens, raw rows {n:,} "
              f"({time.time() - t0:.0f}s)", flush=True)
    con.close()


def build(d: pd.DataFrame, ks: list[int]) -> pd.DataFrame:
    import duckdb

    con = duckdb.connect(str(SCAN_DB), read_only=True)
    con.execute(f"ATTACH '{SRC_DB.as_posix()}' AS src (READ_ONLY)")
    con.register("dt", d)
    life = annotate_lifecycle(load_lifecycle(), load_static()).drop_duplicates("slug")
    con.register("cats", life[["slug", "category_group"]])
    # AWS token_transfers stores from/to as 32-byte padded topics (66 chars);
    # the local DB uses 20-byte addresses, so keep the last 40 hex chars.
    con.execute("""
        CREATE TEMP TABLE rawn AS
        SELECT token,
               '0x' || right(lower(from_address), 40) AS from_address,
               '0x' || right(lower(to_address), 40) AS to_address,
               date
        FROM raw
    """)

    # Fan-out senders per (token, day), excluding DEX contracts (pools / routers)
    con.execute(f"""
        CREATE TEMP TABLE fanout AS
        SELECT r.token, r.from_address, r.date
        FROM rawn r
        LEFT JOIN src.cmap c ON c.contract = r.from_address
        LEFT JOIN cats ca ON ca.slug = c.protocol
        WHERE coalesce(ca.category_group, '') <> 'DEX'
        GROUP BY 1, 2, 3
        HAVING count(DISTINCT r.to_address) >= {FANOUT}
    """)
    rows = []
    for k in ks:
        print(f"  features k={k} ...")
        tx = con.execute(f"""
            SELECT dt.slug, r.to_address, r.from_address, r.date,
                   date_diff('month', dt.launch_month, date_trunc('month', r.date)) AS age,
                   (c.protocol = dt.slug) AS from_own,
                   (f.from_address IS NOT NULL) AS from_fanout
            FROM dt
            JOIN rawn r ON r.token = dt.token
            LEFT JOIN src.cmap c ON c.contract = r.from_address
            LEFT JOIN fanout f ON f.token = r.token AND f.from_address = r.from_address
                              AND f.date = r.date
            WHERE r.date < dt.launch_month + INTERVAL {k} MONTH
              AND r.date >= dt.launch_month - INTERVAL {PRE_MONTHS} MONTH
        """).df()
        users = con.execute(f"""
            SELECT DISTINCT w.protocol AS slug, w.wallet AS to_address
            FROM src.wallet_month_v2 w JOIN dt ON dt.slug = w.protocol
            WHERE w.month >= dt.launch_month
              AND w.month < dt.launch_month + INTERVAL {k} MONTH
        """).df()
        n_users = users.groupby("slug").size()
        tx_by = dict(tuple(tx.groupby("slug")))
        u_by = dict(tuple(users.groupby("slug")))
        for slug in d["slug"]:
            g = tx_by.get(slug)
            row = {"slug": slug, "k": k, "token_live": 0, "token_pre_launch": 0}
            if g is not None and len(g):
                win = g[g["age"] >= 0]
                row["token_live"] = int(len(win) > 0 or (g["age"] < 0).any())
                row["token_pre_launch"] = int((g["age"] < 0).any())
                if len(win):
                    rec = win["to_address"].nunique()
                    per_m = win.groupby("age")["to_address"].nunique().reindex(range(k), fill_value=0)
                    own = win[win["from_own"].fillna(False).astype(bool)]
                    own_m = own.groupby("age")["to_address"].nunique().reindex(range(k), fill_value=0)
                    first_src = win.sort_values("date").drop_duplicates("to_address")
                    uw = u_by.get(slug)
                    row.update({
                        "log_token_recipients": float(np.log1p(rec)),
                        "token_recipient_growth": (float(per_m.iloc[-1] / per_m.mean())
                                                   if k >= 2 and per_m.mean() > 0 else np.nan),
                        "airdrop_share": float(first_src["from_fanout"].mean()),
                        "reward_share": float(own.shape[0] / len(win)),
                        "reward_ramp": (float(own_m.iloc[-1] / own_m.max())
                                        if k >= 2 and own_m.max() > 0 else np.nan),
                        "user_token_share": (
                            float(uw["to_address"].isin(set(win["to_address"])).mean())
                            if uw is not None and n_users.get(slug, 0) > 0 else np.nan
                        ),
                    })
            rows.append(row)
    con.close()
    out = pd.DataFrame(rows)
    for c in TOKEN_FEATURES:
        if c not in out.columns:
            out[c] = np.nan
    return out[["slug", "k", *TOKEN_FEATURES]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, nargs="+", default=[1, 3, 6])
    ap.add_argument("--no-scan", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="rebuild even if the output exists")
    args = ap.parse_args()
    print("== token_incentives ==")
    if OUT.exists() and not args.refresh and not args.no_scan:
        print(f"  using cached {OUT} (--refresh to rescan, --no-scan to rebuild features)")
        print("== token_incentives done ==")
        return
    d = dapp_tokens()
    print(f"  {len(d)} DApps with an own token ({d['token'].nunique()} distinct tokens)")
    if not args.no_scan:
        scan(d)
    res = build(d, args.k)
    res.to_csv(OUT, index=False)
    print(f"  saved {OUT}")
    for k in args.k:
        sub = res[res["k"] == k]
        print(f"  k={k}: token live in window {sub['token_live'].mean():.2f}, "
              f"coverage {sub[TOKEN_FEATURES].notna().mean().round(2).to_dict()}")
    print("== token_incentives done ==")


if __name__ == "__main__":
    main()
