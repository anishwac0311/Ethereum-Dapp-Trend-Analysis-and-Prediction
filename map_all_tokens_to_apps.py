#!/usr/bin/env python3
"""
Map ALL ERC-20 tokens on Ethereum to the app they belong to - in bulk, with no API calls.

Why not the API approach? Millions of tokens exist; explorer APIs allow ~100k calls/day.
Instead we rebuild the full CONTRACT-CREATION GRAPH (who created every contract) from the
public AWS S3 `traces` table once, store it in DuckDB, and resolve every token locally.

Pipeline (each step is cached in dapp_data/tokens.duckdb; the heavy step is resumable)
  1. tokens    every contract flagged is_erc20 in the S3 `contracts` table
               (+ symbol/name from the S3 `tokens` table if it exists)
  2. creates   every contract-creation trace (creator -> created), month by month
  3. anchors   known app contracts from dapp_data/token_app_contract_map.csv, plus
               'deployer anchors' = wallets that deployed exactly one app's contracts
  4. resolve   for each token walk up the creator chain (token <- creator <- its creator
               ...) up to --max-hops, stopping at the first anchor

Relations
  own_token                the DApp's own (DeFiLlama) token
  created_by_app_contract  a creator/factory in the chain is a known app contract
  same_deployer_as_app     deployed by a wallet that only deployed this app's contracts
  unmapped                 no known app. root_creator + cluster_size still group tokens
                           created by the same ultimate deployer (a proxy for "same app")

Run (after build_token_app_map.py has produced token_app_contract_map.csv)
  pip install duckdb pandas
  python map_all_tokens_to_apps.py --creates-start 2019-01 --end 2025-12

OUTPUT
  dapp_data/token_to_app_all.parquet   ALL tokens (millions of rows; read with pandas/duckdb)
  dapp_data/token_to_app_mapped.csv    only tokens mapped to a named app

COST WARNING
  Step 2 reads contract-creation rows out of the S3 `traces` table. Expect hundreds of GB
  to more than 1 TB of transfer for the full history and several GB of local disk.
  Tokens created BEFORE --creates-start get no creator and stay unmapped, so use an early
  start if you need full coverage. The step is resumable month by month: re-run to continue.
  Close anything else holding dapp_data/tokens.duckdb open.
"""
import argparse
import datetime as dt
from pathlib import Path

import duckdb
import pandas as pd

BASE = "s3://aws-public-blockchain/v1.0/eth"
OUT = Path("dapp_data")
OUT.mkdir(exist_ok=True)


# ----------------------------------------------------------------- helpers
def connect(threads):
    con = duckdb.connect(str(OUT / "tokens.duckdb"))
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET s3_region='us-east-2';")
    con.execute(f"SET threads={threads};")
    con.execute(f"SET temp_directory='{(OUT / 'tmp').as_posix()}';")
    try:
        con.execute("CREATE OR REPLACE SECRET aws_anon (TYPE s3, REGION 'us-east-2')")
    except Exception:
        pass
    return con


def table_columns(con, table, sample_date):
    path = f"{BASE}/{table}/date={sample_date}/*.parquet"
    return {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()}


def need(cols, required, table):
    miss = [c for c in required if c not in cols]
    if miss:
        raise SystemExit(f"Table '{table}' is missing expected columns {miss}. "
                         f"Columns found: {sorted(cols)}. Adjust the SQL in this script.")


def exists(con, name):
    return con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
                       [name]).fetchone()[0] > 0


# --------------------------------------------------------- step 1: tokens
def step1_tokens(con, end):
    if exists(con, "tokens"):
        return
    print("[1/4] Listing all ERC-20 contracts ...")
    cols = table_columns(con, "contracts", "2022-01-01")
    need(cols, ["address", "is_erc20"], "contracts")
    con.execute(f"""
        CREATE TABLE tokens AS
        SELECT address AS token, MIN(date)::DATE AS deployed_date
        FROM read_parquet('{BASE}/contracts/date=*/*.parquet', hive_partitioning=true)
        WHERE is_erc20 AND date <= DATE '{end}'
        GROUP BY 1""")
    n = con.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
    print(f"  {n:,} ERC-20 contracts")

    # optional metadata (symbol, name) - skipped silently if the table isn't in the bucket
    try:
        mcols = table_columns(con, "tokens", "2022-01-01")
        sym = "symbol" if "symbol" in mcols else "NULL"
        nam = "name" if "name" in mcols else "NULL"
        con.execute(f"""
            CREATE TABLE tokens_meta AS
            SELECT address AS token, ANY_VALUE({sym}) AS symbol, ANY_VALUE({nam}) AS name
            FROM read_parquet('{BASE}/tokens/date=*/*.parquet', hive_partitioning=true)
            GROUP BY 1""")
    except Exception:
        con.execute("CREATE TABLE tokens_meta(token VARCHAR, symbol VARCHAR, name VARCHAR)")
        print("  (no symbol/name metadata available in the bucket)")


# --------------------------------------------------------- step 2: creates
def step2_creates(con, start, end):
    con.execute("CREATE TABLE IF NOT EXISTS creates(creator VARCHAR, created VARCHAR)")
    con.execute("CREATE TABLE IF NOT EXISTS creates_done(month DATE)")
    cols = table_columns(con, "traces", "2022-01-01")
    need(cols, ["trace_type", "from_address", "to_address"], "traces")
    status = "AND status = 1" if "status" in cols else ""
    done = {r[0] for r in con.execute("SELECT month FROM creates_done").fetchall()}
    months = pd.date_range(start, end, freq="MS")
    todo = [m for m in months if m.date() not in done]
    print(f"[2/4] Reading contract-creation traces from S3: {len(todo)} month(s) to do "
          f"({len(months) - len(todo)} cached) - slow, resumable ...")
    failed = 0
    for month in todo:
        glob = f"{BASE}/traces/date={month:%Y-%m}-*/*.parquet"
        try:
            con.execute(f"""
                INSERT INTO creates
                SELECT from_address, to_address
                FROM read_parquet('{glob}')
                WHERE trace_type = 'create' AND to_address IS NOT NULL {status}""")
            con.execute(f"INSERT INTO creates_done VALUES (DATE '{month.date()}')")
            print(f"  {month:%Y-%m} done")
        except Exception as e:
            failed += 1
            print(f"  {month:%Y-%m} FAILED ({str(e)[:120]})")
    if failed:
        raise SystemExit(f"{failed} month(s) failed. Re-run the same command to retry them.")
    n = con.execute("SELECT COUNT(*) FROM creates").fetchone()[0]
    print(f"  creation graph: {n:,} edges")


# --------------------------------------------------------- step 3: anchors
def step3_anchors(con, min_evidence, max_deployer_contracts):
    f = OUT / "token_app_contract_map.csv"
    if not f.exists():
        raise SystemExit("dapp_data/token_app_contract_map.csv not found. "
                         "Run build_token_app_map.py first.")
    print("[3/4] Building app anchors ...")
    m = pd.read_csv(f)
    keep = m[(m["contract_role"] == "token") |
             ((m["contract_role"] == "app_contract") & (m["n_evidence"] >= min_evidence))]
    keep = keep.sort_values("n_evidence", ascending=False).drop_duplicates("contract_address")
    anchors = keep[["contract_address", "protocol_slug", "protocol_name", "contract_role"]]
    names = m.drop_duplicates("protocol_slug")[["protocol_slug", "protocol_name"]]
    con.register("anchors_df", anchors)
    con.register("names_df", names)
    con.execute("CREATE OR REPLACE TABLE anchor_contract AS SELECT * FROM anchors_df")
    con.execute("CREATE OR REPLACE TABLE app_names AS SELECT * FROM names_df")

    # wallets (never themselves created => EOAs) that deployed contracts of exactly one app
    con.execute(f"""
        CREATE OR REPLACE TABLE anchor_deployer AS
        WITH roots AS (
          SELECT c.creator AS deployer, a.protocol_slug AS slug
          FROM anchor_contract a
          JOIN creates c ON c.created = a.contract_address
          WHERE NOT EXISTS (SELECT 1 FROM creates x WHERE x.created = c.creator)),
        n AS (SELECT creator, COUNT(*) AS n FROM creates GROUP BY 1)
        SELECT r.deployer, ANY_VALUE(r.slug) AS slug
        FROM roots r JOIN n ON n.creator = r.deployer
        GROUP BY r.deployer
        HAVING COUNT(DISTINCT r.slug) = 1 AND MAX(n.n) <= {int(max_deployer_contracts)}""")
    na = con.execute("SELECT COUNT(*) FROM anchor_contract").fetchone()[0]
    nd = con.execute("SELECT COUNT(*) FROM anchor_deployer").fetchone()[0]
    print(f"  {na:,} contract anchors, {nd:,} deployer anchors")


# --------------------------------------------------------- step 4: resolve
def step4_resolve(con, max_hops):
    print("[4/4] Resolving every token against the creation graph ...")
    con.execute("""CREATE OR REPLACE TABLE hits(token VARCHAR, slug VARCHAR, relation VARCHAR,
                                                anchor VARCHAR, hops INT)""")
    con.execute("CREATE OR REPLACE TABLE all_nodes(token VARCHAR, node VARCHAR, hop INT)")

    # own tokens first
    con.execute("""
        INSERT INTO hits
        SELECT t.token, a.protocol_slug, 'own_token', t.token, 0
        FROM tokens t JOIN anchor_contract a
          ON a.contract_address = t.token AND a.contract_role = 'token'""")

    con.execute("""CREATE OR REPLACE TABLE lvl AS
                   SELECT t.token, c.creator AS node, 1 AS hop
                   FROM tokens t JOIN creates c ON c.created = t.token""")
    for hop in range(1, max_hops + 1):
        con.execute("INSERT INTO all_nodes SELECT token, node, hop FROM lvl")
        con.execute("""
            INSERT INTO hits
            SELECT l.token, a.protocol_slug, 'created_by_app_contract', l.node, l.hop
            FROM lvl l JOIN anchor_contract a ON a.contract_address = l.node
            WHERE l.node <> l.token
              AND NOT EXISTS (SELECT 1 FROM hits h WHERE h.token = l.token)""")
        con.execute("""
            INSERT INTO hits
            SELECT l.token, d.slug, 'same_deployer_as_app', l.node, l.hop
            FROM lvl l JOIN anchor_deployer d ON d.deployer = l.node
            WHERE NOT EXISTS (SELECT 1 FROM hits h WHERE h.token = l.token)""")
        con.execute("""
            CREATE OR REPLACE TABLE lvl_next AS
            SELECT l.token, c.creator AS node, l.hop + 1 AS hop
            FROM lvl l JOIN creates c ON c.created = l.node
            WHERE NOT EXISTS (SELECT 1 FROM hits h WHERE h.token = l.token)""")
        n = con.execute("SELECT COUNT(*) FROM lvl_next").fetchone()[0]
        con.execute("CREATE OR REPLACE TABLE lvl AS SELECT * FROM lvl_next")
        nh = con.execute("SELECT COUNT(DISTINCT token) FROM hits").fetchone()[0]
        print(f"  hop {hop}: {nh:,} tokens mapped so far")
        if n == 0:
            break

    con.execute("""
        CREATE OR REPLACE TABLE token_app AS
        WITH direct AS (SELECT token, ANY_VALUE(node) AS creator FROM all_nodes WHERE hop = 1 GROUP BY 1),
        root AS (SELECT token, node AS root_creator, hop AS root_hops FROM all_nodes
                 QUALIFY ROW_NUMBER() OVER (PARTITION BY token ORDER BY hop DESC) = 1),
        best AS (SELECT * FROM hits
                 QUALIFY ROW_NUMBER() OVER (PARTITION BY token ORDER BY hops,
                   CASE relation WHEN 'own_token' THEN 0
                                 WHEN 'created_by_app_contract' THEN 1 ELSE 2 END) = 1)
        SELECT t.token AS token_address, t.deployed_date, m.symbol, m.name,
               b.slug AS app_slug, n.protocol_name AS app_name,
               COALESCE(b.relation, 'unmapped') AS relation,
               b.anchor AS anchor_contract, b.hops,
               CASE WHEN b.relation = 'own_token' THEN 'high'
                    WHEN b.relation = 'created_by_app_contract' AND b.hops = 1 THEN 'high'
                    WHEN b.relation = 'created_by_app_contract' THEN 'medium'
                    WHEN b.relation = 'same_deployer_as_app' AND b.hops = 1 THEN 'medium'
                    WHEN b.relation = 'same_deployer_as_app' THEN 'low'
                    ELSE 'none' END AS confidence,
               d.creator, r.root_creator,
               COUNT(*) OVER (PARTITION BY r.root_creator) AS cluster_size
        FROM tokens t
        LEFT JOIN best b ON b.token = t.token
        LEFT JOIN app_names n ON n.protocol_slug = b.slug
        LEFT JOIN tokens_meta m ON m.token = t.token
        LEFT JOIN direct d ON d.token = t.token
        LEFT JOIN root r ON r.token = t.token""")


def export(con):
    pq = (OUT / "token_to_app_all.parquet").as_posix()
    csv = (OUT / "token_to_app_mapped.csv").as_posix()
    con.execute(f"COPY token_app TO '{pq}' (FORMAT parquet)")
    con.execute(f"COPY (SELECT * FROM token_app WHERE app_slug IS NOT NULL) TO '{csv}' (HEADER)")
    total, mapped = con.execute(
        "SELECT COUNT(*), COUNT(app_slug) FROM token_app").fetchone()
    print(f"\nFINAL: {total:,} tokens, {mapped:,} mapped to a named app ({mapped / max(total, 1):.1%})")
    print(con.execute("SELECT relation, confidence, COUNT(*) AS n FROM token_app "
                      "GROUP BY 1, 2 ORDER BY n DESC").df().to_string(index=False))
    print(f"\n  -> {pq}\n  -> {csv}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--creates-start", default="2019-01", help="YYYY-MM; earlier tokens stay unmapped")
    ap.add_argument("--end", default="2025-12", help="YYYY-MM")
    ap.add_argument("--max-hops", type=int, default=4)
    ap.add_argument("--min-evidence", type=int, default=1)
    ap.add_argument("--max-deployer-contracts", type=int, default=3000)
    ap.add_argument("--threads", type=int, default=8)
    a = ap.parse_args()
    start = pd.Timestamp(a.creates_start + "-01")
    end_m = pd.Timestamp(a.end + "-01")
    end_date = (end_m + pd.offsets.MonthEnd(0)).date()

    con = connect(a.threads)
    step1_tokens(con, end_date)
    step2_creates(con, start, end_m)
    step3_anchors(con, a.min_evidence, a.max_deployer_contracts)
    step4_resolve(con, a.max_hops)
    export(con)


if __name__ == "__main__":
    main()
