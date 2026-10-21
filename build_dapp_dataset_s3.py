#!/usr/bin/env python3
"""
Build a DApp-level panel dataset for Ethereum mainnet WITHOUT any Google Cloud tooling.

Sources
  - DeFiLlama API (requests)                          : DApp registry
  - AWS Public Blockchain Data, anonymous S3 (DuckDB) : s3://aws-public-blockchain/v1.0/eth/
    (Parquet files partitioned by date; no AWS account or credentials needed)

Setup
  pip install duckdb pandas requests

Usage
  # quick test (small + cheap): one year, top 100 DApps, no deployer expansion
  python build_dapp_dataset_s3.py --start 2022-01-01 --end 2022-12-31 --top-n 100 --seed-only
  # full run
  python build_dapp_dataset_s3.py --start 2018-01-01 --end 2025-12-31

Outputs (./dapp_data/)
  protocols.csv, contract_map.csv, activity.csv, dapp_static.csv,
  dapp_panel.csv  <- FINAL DApp x month panel
  run.log         <- full log of every run (appended), including tracebacks

Notes
  - Everything is cached; the script is resumable (activity is stored month by month in
    dapp_data/dapp.duckdb). Delete a file to redo that step.
  - Data is read straight from S3, so runtime is bounded by your internet speed.
    Start small. The deployer-expansion step (omitted with --seed-only) scans
    contract-creation transactions for the entire chain history up to --end.
  - Only DIRECT calls to a contract (to_address = contract) are counted.
  - 'new_wallets' in the first month of --start is overstated.
  - Column names are checked at runtime; if the dataset's schema differs from what is
    expected the script stops and prints the columns it actually found.
"""
import argparse
import datetime as dt
import hashlib
import logging
import re
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import requests

BASE = "s3://aws-public-blockchain/v1.0/eth"
OUT = Path("dapp_data")
OUT.mkdir(exist_ok=True)
LOG_FILE = OUT / "run.log"

log = logging.getLogger("dapp")


# ----------------------------------------------------------------- logging
def setup_logging(verbose):
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(fmt)
    file = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file.setLevel(logging.DEBUG)
    file.setFormatter(fmt)
    log.setLevel(logging.DEBUG)
    log.addHandler(console)
    log.addHandler(file)


def fail(msg):
    log.error(msg)
    raise SystemExit(1)


def fmt_secs(s):
    s = int(s)
    return f"{s // 3600}h{s % 3600 // 60:02d}m" if s >= 3600 else f"{s // 60}m{s % 60:02d}s"


def db_size():
    """Size of the DuckDB file plus its write-ahead log, in MB."""
    total = sum(p.stat().st_size for p in OUT.glob("dapp.duckdb*") if p.is_file())
    return f"{total / 1e6:,.1f} MB"


# ----------------------------------------------------------------- helpers
def parse_eth_address(a):
    """DeFiLlama 'address' can be '0x..', 'ethereum:0x..', 'bsc:0x..', '-' or None."""
    if not isinstance(a, str):
        return None
    a = a.strip()
    if ":" in a:
        chain, a = a.split(":", 1)
        if chain.lower() != "ethereum":
            return None
    return a.lower() if re.fullmatch(r"0x[0-9a-fA-F]{40}", a) else None


def group_category(cat):
    c = (cat or "").lower()
    if c == "dexs" or c.startswith("dex "):
        return "DEX"
    if "nft" in c:
        return "NFT"
    if "gam" in c or "metaverse" in c:
        return "Gaming"
    if "social" in c:
        return "Social"
    if any(k in c for k in ["bridge", "oracle", "wallet", "infra", "rpc",
                            "privacy", "developer", "data"]):
        return "Infrastructure"
    if any(k in c for k in ["lend", "borrow", "yield", "staking", "derivative",
                            "cdp", "perp", "option", "stablecoin", "insurance",
                            "payment", "rwa", "launchpad", "algo", "index",
                            "leverage", "synthetic", "prediction", "farm",
                            "vault", "liquidity"]):
        return "DeFi"
    return "Other"


def connect(threads):
    con = duckdb.connect(str(OUT / "dapp.duckdb"))
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET s3_region='us-east-2';")
    con.execute(f"SET threads={threads};")
    con.execute(f"SET temp_directory='{(OUT / 'tmp').as_posix()}';")
    try:  # anonymous (unsigned) access in newer DuckDB versions
        con.execute("CREATE OR REPLACE SECRET aws_anon (TYPE s3, REGION 'us-east-2')")
    except Exception as e:
        log.debug(f"could not create anonymous S3 secret: {e}")
    for s in ["SET http_retries=8", "SET http_retry_wait_ms=2000",
              "SET http_retry_backoff=2", "SET http_timeout=120000"]:
        try:
            con.execute(s)
        except Exception as e:
            log.debug(f"'{s}' not supported: {e}")
    log.info(f"DuckDB {duckdb.__version__} connected to {OUT / 'dapp.duckdb'} ({db_size()})")
    return con


def execute_retry(con, sql, tries=5, wait=15):
    """Re-run a query on transient network errors (DNS failures, resets, timeouts)."""
    for i in range(1, tries + 1):
        try:
            return con.execute(sql)
        except (duckdb.IOException, duckdb.HTTPException) as e:
            if i == tries or "No files found" in str(e):
                raise
            log.warning(f"    network error ({str(e)[:150]}); "
                        f"retry {i}/{tries - 1} in {wait * i}s")
            time.sleep(wait * i)


def table_columns(con, table, sample_date="2022-01-01"):
    path = f"{BASE}/{table}/date={sample_date}/*.parquet"
    rows = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()
    cols = {r[0] for r in rows}
    log.debug(f"columns of '{table}': {sorted(cols)}")
    return cols


def need(cols, required, table):
    miss = [c for c in required if c not in cols]
    if miss:
        fail(f"Table '{table}' is missing expected columns {miss}. "
             f"Columns found: {sorted(cols)}. Adjust the SQL in this script.")


# ------------------------------------------------- step 1: DApp registry
def step1_registry(top_n):
    f = OUT / "protocols.csv"
    if f.exists():
        df = pd.read_csv(f)
        log.info(f"[1/4] Using cached {f} ({len(df)} DApps)")
        if top_n and len(df) > top_n:
            log.warning(f"  cached file has {len(df)} DApps but --top-n is {top_n}; "
                        f"delete {f} to apply --top-n")
        return df
    log.info("[1/4] Fetching DApp registry from DeFiLlama ...")
    raw = requests.get("https://api.llama.fi/protocols", timeout=120).json()
    df = pd.DataFrame(raw)
    log.debug(f"  {len(df)} protocols returned by DeFiLlama")
    df = df[df["chains"].apply(lambda c: isinstance(c, list) and "Ethereum" in c)].copy()
    log.debug(f"  {len(df)} list Ethereum among their chains")
    for col in ["slug", "name", "category", "listedAt", "symbol", "address", "tvl"]:
        if col not in df:
            df[col] = None
    df["seed_address"] = df["address"].apply(parse_eth_address)
    df["category_group"] = df["category"].apply(group_category)
    df["listed_date"] = pd.to_datetime(df["listedAt"], unit="s", errors="coerce").dt.date
    sym = df["symbol"].fillna("-").astype(str).str.strip()
    df["has_token"] = (sym != "-") & (sym != "")
    df = df.dropna(subset=["seed_address"]).sort_values("tvl", ascending=False)
    if top_n:
        df = df.head(top_n)
    cols = ["slug", "name", "category", "category_group", "listed_date",
            "symbol", "has_token", "seed_address", "tvl"]
    df = df[cols]
    df.to_csv(f, index=False)
    log.info(f"  {len(df)} DApps with an Ethereum seed address -> {f}")
    log.debug(f"  by category group: {df['category_group'].value_counts().to_dict()}")
    return df


# ----------------------------------------- step 2: DApp -> contracts map
def step2_contract_map(con, reg, end, seed_only, max_per_deployer):
    f = OUT / "contract_map.csv"
    if f.exists():
        cm = pd.read_csv(f, parse_dates=["deployed_date"])
        log.info(f"[2/4] Using cached {f} ({len(cm):,} contracts, "
                 f"{cm['protocol'].nunique()} DApps)")
        return cm
    log.info("[2/4] Mapping DApps to contracts ...")
    t_step = time.time()
    seeds_df = (reg.sort_values("tvl", ascending=False)
                .drop_duplicates("seed_address")[["slug", "seed_address"]])
    seed_owner = dict(zip(seeds_df["seed_address"], seeds_df["slug"]))
    con.register("seeds_df", seeds_df)
    con.execute("CREATE OR REPLACE TEMP TABLE seeds AS SELECT * FROM seeds_df")

    # deployment date of each seed contract (works for factory-created contracts too)
    need(table_columns(con, "contracts"), ["address"], "contracts")
    log.info(f"  looking up deployment dates of {len(seeds_df)} seed contracts "
             f"(scans the full 'contracts' table, can take a while) ...")
    t0 = time.time()
    seed_dates = execute_retry(con, f"""
        SELECT address AS contract, MIN(date)::DATE AS deployed_date
        FROM read_parquet('{BASE}/contracts/date=*/*.parquet', hive_partitioning=true)
        WHERE date <= DATE '{end}' AND address IN (SELECT seed_address FROM seeds)
        GROUP BY 1""").df()
    log.info(f"  found deployment dates for {len(seed_dates)}/{len(seeds_df)} seeds "
             f"in {fmt_secs(time.time() - t0)}")
    if seed_dates.empty:
        log.warning("  no seed contract matched the 'contracts' table; check address format")
    seed_dates["protocol"] = seed_dates["contract"].map(seed_owner)
    seed_dates["source"] = "seed"
    parts = [seed_dates[["contract", "protocol", "deployed_date", "source"]]]

    if not seed_only:
        cols = table_columns(con, "transactions")
        need(cols, ["from_address", "to_address", "receipt_contract_address"], "transactions")
        status = "AND receipt_status = 1" if "receipt_status" in cols else ""
        con.execute("""CREATE TABLE IF NOT EXISTS creation(
            deployer VARCHAR, contract VARCHAR, deployed_date DATE)""")
        con.execute("CREATE TABLE IF NOT EXISTS creation_done_months(month DATE)")
        done = {r[0] for r in con.execute("SELECT month FROM creation_done_months").fetchall()}
        months = pd.date_range("2015-07-01", end, freq="MS")
        todo = [mo for mo in months if mo.date() not in done]
        log.info(f"  scanning contract-creation transactions: {len(months)} months, "
                 f"{len(months) - len(todo)} already cached, {len(todo)} to go")
        failed, total, t_scan = [], 0, time.time()
        for i, month in enumerate(todo, 1):
            m = month.date()
            glob = f"{BASE}/transactions/date={month:%Y-%m}-*/*.parquet"
            t0 = time.time()
            try:
                con.execute("BEGIN TRANSACTION")
                n = execute_retry(con, f"""
                    INSERT INTO creation
                    SELECT from_address, receipt_contract_address, date::DATE
                    FROM read_parquet('{glob}', hive_partitioning=true)
                    WHERE (to_address IS NULL OR to_address IN ('', 'None'))
                      AND receipt_contract_address NOT IN ('', 'None')
                      AND date <= DATE '{end}' {status}""").fetchone()[0]
                con.execute(f"INSERT INTO creation_done_months VALUES (DATE '{m}')")
                con.execute("COMMIT")
                total += n
                level = logging.WARNING if n == 0 else logging.INFO
                log.log(level, f"    [{i}/{len(todo)}] {month:%Y-%m}: {n:>9,} contracts "
                               f"in {fmt_secs(time.time() - t0)} | db {db_size()}"
                               + ("  <- 0 rows, check the filter" if n == 0 else ""))
            except Exception as e:
                con.execute("ROLLBACK")
                if "No files found" in str(e):
                    con.execute(f"INSERT INTO creation_done_months VALUES (DATE '{m}')")
                    log.info(f"    [{i}/{len(todo)}] {month:%Y-%m}: no data on S3 (skipped)")
                    continue
                failed.append(f"{month:%Y-%m}")
                log.error(f"    [{i}/{len(todo)}] {month:%Y-%m}: FAILED ({str(e)[:150]})")
                log.debug("traceback:", exc_info=True)
        log.info(f"  creation scan: {total:,} new contracts this run "
                 f"in {fmt_secs(time.time() - t_scan)}")
        if failed:
            fail(f"  {len(failed)} month(s) of the creation scan failed "
                 f"({', '.join(failed[:10])}). Re-run to resume.")
        n_created = con.execute("SELECT COUNT(*) FROM creation").fetchone()[0]
        if n_created == 0:
            fail("  Creation scan found 0 contracts; the filter does not match "
                 "this dataset. Delete dapp_data/dapp.duckdb after fixing it.")
        log.info(f"  {n_created:,} contract creations in total; "
                 f"matching deployers to DApps (no progress output, may take minutes) ...")
        t0 = time.time()
        exp = con.execute(f"""
            WITH cr AS (SELECT * FROM creation WHERE deployed_date <= DATE '{end}'),
            dep AS (
              SELECT c.deployer, ANY_VALUE(s.slug) AS protocol
              FROM cr c JOIN seeds s ON c.contract = s.seed_address
              GROUP BY 1 HAVING COUNT(DISTINCT s.slug) = 1),
            cnt AS (SELECT deployer, COUNT(*) AS n FROM cr GROUP BY 1)
            SELECT c.contract, d.protocol, c.deployed_date
            FROM cr c
            JOIN dep d USING (deployer)
            JOIN cnt  n USING (deployer)
            WHERE n.n <= {int(max_per_deployer)}""").df()
        log.info(f"  deployer expansion: {len(exp):,} contracts for "
                 f"{exp['protocol'].nunique()} DApps in {fmt_secs(time.time() - t0)}")
        exp["source"] = np.where(exp["contract"].isin(seed_owner), "seed", "deployer")
        parts.insert(0, exp)
    else:
        log.info("  --seed-only: skipping deployer expansion")

    cm = pd.concat(parts, ignore_index=True)
    cm["_p"] = (cm["source"] != "seed").astype(int)          # seeds win on duplicates
    cm = cm.sort_values("_p").drop_duplicates("contract").drop(columns="_p")
    # seeds with no known deployment date still get mapped
    known = set(cm["contract"])
    extra = pd.DataFrame([{"contract": a, "protocol": s, "deployed_date": pd.NaT, "source": "seed"}
                          for a, s in seed_owner.items() if a not in known])
    if len(extra):
        log.debug(f"  {len(extra)} seeds have no known deployment date")
    cm = pd.concat([cm, extra], ignore_index=True)
    cm["deployed_date"] = pd.to_datetime(cm["deployed_date"])
    cm.to_csv(f, index=False)
    log.info(f"  {len(cm):,} contracts mapped to {cm['protocol'].nunique()} DApps "
             f"({cm['source'].value_counts().to_dict()}) -> {f} "
             f"[step 2 took {fmt_secs(time.time() - t_step)}]")
    return cm


# ------------------------------------------ step 3: on-chain activity
def step3_activity(con, cmap, start, end):
    f = OUT / "activity.csv"
    if f.exists():
        act = pd.read_csv(f, parse_dates=["month"])
        log.info(f"[3/4] Using cached {f} ({len(act):,} DApp-month rows)")
        return act
    log.info("[3/4] Computing monthly activity from S3 (resumable) ...")
    t_step = time.time()
    cols = table_columns(con, "transactions")
    need(cols, ["from_address", "to_address", "value", "gas_price"], "transactions")
    gas_col = "receipt_gas_used" if "receipt_gas_used" in cols else "gas"
    if gas_col == "gas":
        log.warning("  receipt_gas_used not found; using gas LIMIT instead of gas used.")

    con.register("cmap_df", cmap[["contract", "protocol"]])
    con.execute("CREATE OR REPLACE TABLE cmap AS SELECT * FROM cmap_df")
    con.execute("CREATE TABLE IF NOT EXISTS meta(k VARCHAR, v VARCHAR)")
    con.execute("""CREATE TABLE IF NOT EXISTS wallet_month(
        protocol VARCHAR, month DATE, wallet VARCHAR, tx_count BIGINT,
        gas_used DOUBLE, fees_eth DOUBLE, eth_value DOUBLE)""")
    con.execute("CREATE TABLE IF NOT EXISTS done_months(month DATE)")

    # if the contract map changed, cached activity is stale -> reset
    h = hashlib.md5("".join(sorted(cmap["contract"] + cmap["protocol"])).encode()).hexdigest()
    old = con.execute("SELECT v FROM meta WHERE k='map_hash'").fetchone()
    if old is None or old[0] != h:
        if old is not None:
            log.warning("  contract map changed since last run; clearing cached activity")
        con.execute("DELETE FROM wallet_month; DELETE FROM done_months; DELETE FROM meta;")
        con.execute(f"INSERT INTO meta VALUES ('map_hash','{h}')")
    done = {r[0] for r in con.execute("SELECT month FROM done_months").fetchall()}

    months = pd.date_range(pd.Timestamp(start).replace(day=1), end, freq="MS")
    todo = [mo for mo in months if mo.date() not in done]
    log.info(f"  {len(cmap):,} contracts tracked; {len(months)} months, "
             f"{len(months) - len(todo)} already cached, {len(todo)} to go")
    t_scan = time.time()
    for i, month in enumerate(todo, 1):
        m = month.date()
        glob = f"{BASE}/transactions/date={month:%Y-%m}-*/*.parquet"
        t0 = time.time()
        try:
            n = execute_retry(con, f"""
                INSERT INTO wallet_month
                SELECT m.protocol, DATE '{m}', t.from_address,
                       COUNT(*),
                       SUM(CAST(t.{gas_col} AS DOUBLE)),
                       SUM(CAST(t.gas_price AS DOUBLE) * CAST(t.{gas_col} AS DOUBLE)) / 1e18,
                       SUM(CAST(t.value AS DOUBLE)) / 1e18
                FROM read_parquet('{glob}') t
                JOIN cmap m ON t.to_address = m.contract
                GROUP BY 1, 3""").fetchone()[0]
            con.execute(f"INSERT INTO done_months VALUES (DATE '{m}')")
            n_dapps = con.execute(f"""SELECT COUNT(DISTINCT protocol) FROM wallet_month
                                      WHERE month = DATE '{m}'""").fetchone()[0]
            level = logging.WARNING if n == 0 else logging.INFO
            log.log(level, f"    [{i}/{len(todo)}] {month:%Y-%m}: {n:>9,} wallet rows, "
                           f"{n_dapps:>4} DApps active in {fmt_secs(time.time() - t0)} "
                           f"| db {db_size()}" + ("  <- 0 rows" if n == 0 else ""))
        except Exception as e:                       # network hiccup / missing partition
            log.error(f"    [{i}/{len(todo)}] {month:%Y-%m}: FAILED ({str(e)[:150]}) "
                      f"- re-run to retry")
            log.debug("traceback:", exc_info=True)
    if todo:
        log.info(f"  activity scan finished in {fmt_secs(time.time() - t_scan)}")

    log.info("  aggregating wallet rows into DApp-month activity ...")
    act = con.execute("""
        WITH wf AS (
          SELECT *, MIN(month) OVER (PARTITION BY protocol, wallet) AS first_month
          FROM wallet_month)
        SELECT protocol, month,
               COUNT(*) AS active_wallets,
               COUNT(*) FILTER (WHERE month = first_month) AS new_wallets,
               SUM(tx_count) AS tx_count, SUM(gas_used) AS gas_used,
               SUM(fees_eth) AS fees_eth, SUM(eth_value) AS eth_value
        FROM wf GROUP BY protocol, month ORDER BY protocol, month""").df()
    act["month"] = pd.to_datetime(act["month"])
    n_done = con.execute("SELECT COUNT(*) FROM done_months").fetchone()[0]
    if n_done < len(months):
        log.error(f"  {len(months) - n_done} month(s) failed; {f} NOT written. "
                  f"Re-run to finish.")
    else:
        act.to_csv(f, index=False)
        log.info(f"  -> {f}")
    log.info(f"  {len(act):,} DApp-month rows, {act['protocol'].nunique()} DApps with activity "
             f"[step 3 took {fmt_secs(time.time() - t_step)}]")
    return act


# ------------------------------------------------ step 4: final dataset
def step4_assemble(reg, cmap, act, start, end):
    log.info("[4/4] Assembling final dataset ...")
    cmap = cmap.copy()
    cmap["deployed_date"] = pd.to_datetime(cmap["deployed_date"])
    agg = (cmap.groupby("protocol")
           .agg(n_contracts=("contract", "nunique"), first_deployed=("deployed_date", "min"))
           .reset_index().rename(columns={"protocol": "slug"}))
    static = reg.merge(agg, on="slug", how="inner")
    start_month = pd.Timestamp(start).to_period("M").to_timestamp()
    static["first_month"] = (static["first_deployed"].dt.to_period("M").dt.to_timestamp()
                             .fillna(start_month))
    static.drop(columns=["seed_address"]).to_csv(OUT / "dapp_static.csv", index=False)
    log.info(f"  {len(static)} DApps -> {OUT / 'dapp_static.csv'}")

    end_month = pd.Timestamp(end).to_period("M").to_timestamp()
    months = pd.DataFrame({"month": pd.date_range(start_month, end_month, freq="MS")})
    grid = static[["slug", "first_month"]].merge(months, how="cross")
    grid = grid[grid["month"] >= grid["first_month"]]

    panel = grid.merge(act.rename(columns={"protocol": "slug"}), on=["slug", "month"], how="left")
    metrics = ["active_wallets", "new_wallets", "tx_count", "gas_used", "fees_eth", "eth_value"]
    panel[metrics] = panel[metrics].fillna(0)
    panel = panel.sort_values(["slug", "month"])

    g = panel.groupby("slug")
    panel["cum_wallets"] = g["new_wallets"].cumsum()
    panel["wallet_growth_mom"] = (g["active_wallets"].pct_change(fill_method=None)
                                  .replace([np.inf, -np.inf], np.nan))
    panel = panel.merge(
        static[["slug", "name", "category", "category_group", "listed_date", "symbol",
                "has_token", "n_contracts", "first_deployed", "tvl"]], on="slug")
    month_end = panel["month"] + pd.offsets.MonthEnd(0)
    panel["contract_age_days"] = (month_end - panel["first_deployed"]).dt.days.clip(lower=0)
    panel = panel.drop(columns="first_month")
    panel.to_csv(OUT / "dapp_panel.csv", index=False)
    zero = (panel["active_wallets"] == 0).mean() if len(panel) else 0
    log.info(f"  FINAL: {len(panel):,} rows, {panel['slug'].nunique()} DApps, "
             f"{zero:.0%} of DApp-months have no activity -> {OUT / 'dapp_panel.csv'}")
    return panel


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--end", default="2026-06-30")
    ap.add_argument("--top-n", type=int, default=None, help="limit to top-N DApps by TVL")
    ap.add_argument("--seed-only", action="store_true",
                    help="skip same-deployer contract expansion (much faster)")
    ap.add_argument("--max-contracts-per-deployer", type=int, default=3000)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--verbose", action="store_true",
                    help="also show DEBUG messages on the console (always in run.log)")
    a = ap.parse_args()
    start, end = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)

    setup_logging(a.verbose)
    log.info("=" * 70)
    log.info(f"run started: {' '.join(sys.argv)}")
    log.info(f"  start={start} end={end} top_n={a.top_n} seed_only={a.seed_only} "
             f"max_per_deployer={a.max_contracts_per_deployer} threads={a.threads}")
    log.info(f"  log file: {LOG_FILE.resolve()}")
    t_run = time.time()
    try:
        con = connect(a.threads)
        reg = step1_registry(a.top_n)
        cmap = step2_contract_map(con, reg, end, a.seed_only, a.max_contracts_per_deployer)
        act = step3_activity(con, cmap, start, end)
        step4_assemble(reg, cmap, act, start, end)
    except KeyboardInterrupt:
        log.warning(f"interrupted by user after {fmt_secs(time.time() - t_run)}; "
                    f"finished months are saved, re-run to resume")
        raise SystemExit(130)
    except SystemExit:
        log.error(f"run stopped after {fmt_secs(time.time() - t_run)}")
        raise
    except Exception:
        log.exception(f"run crashed after {fmt_secs(time.time() - t_run)}")
        raise SystemExit(1)
    log.info(f"run finished in {fmt_secs(time.time() - t_run)}")


if __name__ == "__main__":
    main()
