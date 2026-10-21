#!/usr/bin/env python3
"""
Build an APP-CONTRACT DApp panel for Ethereum mainnet (v2).

Unlike build_dapp_dataset_s3.py (v1), this pipeline measures DApp *usage* via
application contracts (routers, pools, vaults, markets, factories) rather than
governance-token transfers. Activity is attributed from event logs + direct calls.

Sources
  - DeFiLlama API                              : DApp registry
  - app_seeds.csv (curated)                    : routers / factories / app contracts
  - DefiLlama/DefiLlama-Adapters (GitHub zip)  : address extraction from TVL adapters
  - brianleect/etherscan-labels (optional)     : name/label matching
  - AWS Public Blockchain Data (DuckDB/S3)     : s3://aws-public-blockchain/v1.0/eth/
  - dapp_data/dapp.duckdb (optional, RO)       : reuse v1 `creation` table for deployer expansion

Setup
  pip install duckdb pandas requests

Usage (six-month window, every Ethereum protocol plus all app_seeds.csv apps)
  python build_dapp_dataset_v2.py --start 2022-01-01 --end 2022-06-30 \\
      --no-deployer-expansion --skip-labels

Full run
  python build_dapp_dataset_v2.py --start 2018-01-01 --end 2025-12-31

  app_seeds.csv slugs must be exact DeFiLlama slugs; slugs DeFiLlama doesn't list on
  Ethereum (OpenSea, ENS, CryptoKitties, ...) are added to the registry using CURATED_META.
  After editing app_seeds.csv delete protocols.csv, discovered_raw.csv and
  app_contracts.csv in dapp_data_v2/ so they are rebuilt.

Outputs (./dapp_data_v2/)
  protocols.csv, app_contracts.csv, contract_conflicts.csv, activity.csv,
  dapp_static.csv, dapp_panel.csv,
  cohort_retention.csv, category_month.csv, concentration_month.csv,
  dapp_lifecycle.csv, run.log

Attribution caveats
  - A tx that touches N protocols credits each with the full gas of the tx
    (see n_protocols_in_tx). Prefer gas for ranking within an app, not across apps
    when summing ecosystem totals without dedup.
  - Logs-based attribution captures router/aggregator/smart-wallet users; it is
    several times more expensive to scan than transactions alone.
  - ERC20 tokens claimed by more than one protocol (USDC, DAI, ...) are dropped. Curated
    contracts, factory pools (Uniswap V2 pairs are ERC20) and tokens a single protocol
    claims (its own vault / receipt token) are kept.
  - Non-curated addresses claimed by 3+ protocols are treated as shared and dropped.
  - Shared infra (WETH, Permit2, Multicall, ...) is denylisted.

Research questions this dataset supports
  1. How concentrated is activity among the largest applications?
     -> concentration_month.csv
  2. Which categories of DApps are growing or declining?
     -> category_month.csv
  3. How quickly do successful DApps acquire users?
     -> dapp_lifecycle.csv (months_to_1k / 10k / half_peak, wallets_m3/m6/m12)
  4. What patterns distinguish growing vs flash apps?
     -> dapp_lifecycle.csv (lifecycle_label + early_* features) + cohort_retention.csv
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import re
import sys
import time
import zipfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import requests

BASE = "s3://aws-public-blockchain/v1.0/eth"
OUT = Path("dapp_data_v2")
OUT.mkdir(exist_ok=True)
CACHE = OUT / "cache"
CACHE.mkdir(exist_ok=True)
LOG_FILE = OUT / "run.log"
V1_DB = Path("dapp_data") / "dapp.duckdb"
SEEDS_FILE = Path("app_seeds.csv")

# Shared infrastructure that should never be attributed to a single DApp
DENYLIST = {
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",  # WETH
    "0x000000000022d473030f116ddee9f6b43ac78ba3",  # Permit2
    "0xca11bde05977b3631167028862be2a173976ca11",  # Multicall3
    "0x5ba1e12693dc8f9c48aad8770482f4739beed696",  # Multicall2
    "0xeefba1e63905ef1d7acba5a8513c70307c1ce441",  # Multicall
    "0x0000000000000000000000000000000000000000",
    "0x0000000000000000000000000000000000000001",
}

# ERC20 function selectors (4-byte) as hex substrings in bytecode
ERC20_SELECTORS = ("a9059cbb", "095ea7b3", "70a08231", "18160ddd")

SOURCE_PRIORITY = {
    "curated": 0,
    "factory": 1,
    "adapter": 2,
    "label": 3,
    "deployer": 4,
}
SOURCE_CONFIDENCE = {
    "curated": "high",
    "factory": "high",
    "adapter": "medium",
    "label": "low",
    "deployer": "low",
}

DROP_CATEGORIES = {"CEX", "Chain", "Bridge Aggregator"}  # non-app / meta

# Name / category for app_seeds.csv slugs that DeFiLlama does not list on Ethereum.
# Overrides DeFiLlama metadata when both exist.
CURATED_META = {
    "paraswap": ("ParaSwap", "DEX Aggregator"),
    "kyberswap": ("KyberSwap", "DEX Aggregator"),
    "0x": ("0x Protocol", "DEX Aggregator"),
    "cowswap": ("CoW Swap", "DEX Aggregator"),
    "dydx": ("dYdX (v1-v3 on Ethereum)", "Derivatives"),
    "pendle": ("Pendle", "Yield"),
    "instadapp": ("Instadapp", "Services"),
    "synthetix": ("Synthetix", "Synthetics"),
    "opensea-v1": ("OpenSea Wyvern v1", "NFT Marketplace"),
    "opensea-v2": ("OpenSea Wyvern v2", "NFT Marketplace"),
    "opensea-seaport": ("OpenSea Seaport", "NFT Marketplace"),
    "blur": ("Blur", "NFT Marketplace"),
    "rarible": ("Rarible", "NFT Marketplace"),
    "foundation-nft": ("Foundation", "NFT Marketplace"),
    "gem-nft": ("Gem", "NFT Marketplace"),
    "genie-nft": ("Genie", "NFT Marketplace"),
    "cryptopunks": ("CryptoPunks", "NFT Marketplace"),
    "art-blocks": ("Art Blocks", "NFT Marketplace"),
    "ens": ("ENS", "Domains"),
    "unstoppable-domains": ("Unstoppable Domains", "Domains"),
    "axie-infinity": ("Axie Infinity (Ethereum)", "Gaming"),
    "decentraland": ("Decentraland", "Gaming"),
    "gods-unchained": ("Gods Unchained", "Gaming"),
    "cryptokitties": ("CryptoKitties", "Gaming"),
    "wolf-game": ("Wolf Game", "Gaming"),
    "loot": ("Loot", "Gaming"),
    "otherside": ("Otherside", "Gaming"),
    "parallel": ("Parallel", "Gaming"),
    "sorare": ("Sorare", "Gaming"),
    "gitcoin": ("Gitcoin", "Social"),
    "poap": ("POAP", "Social"),
}

# DeFiLlama categories that group_category() would otherwise put in the wrong bucket
CATEGORY_GROUP_OVERRIDES = {
    "Domains": "Infrastructure",
    "SoFi": "Social",
    "Charity Fundraising": "Social",
}

log = logging.getLogger("dapp_v2")


# ----------------------------------------------------------------- logging
def setup_logging(verbose: bool) -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(fmt)
    file_h = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_h.setLevel(logging.DEBUG)
    file_h.setFormatter(fmt)
    log.setLevel(logging.DEBUG)
    log.handlers.clear()
    log.addHandler(console)
    log.addHandler(file_h)


def fail(msg: str) -> None:
    log.error(msg)
    raise SystemExit(1)


def fmt_secs(s: float) -> str:
    s = int(s)
    return f"{s // 3600}h{s % 3600 // 60:02d}m" if s >= 3600 else f"{s // 60}m{s % 60:02d}s"


def db_size() -> str:
    total = sum(p.stat().st_size for p in OUT.glob("dapp_v2.duckdb*") if p.is_file())
    return f"{total / 1e6:,.1f} MB"


# ----------------------------------------------------------------- helpers
def parse_eth_address(a) -> str | None:
    if not isinstance(a, str):
        return None
    a = a.strip()
    if ":" in a:
        chain, a = a.split(":", 1)
        if chain.lower() not in ("ethereum", "eth", "mainnet"):
            return None
    a = a.lower()
    if not re.fullmatch(r"0x[0-9a-f]{40}", a):
        return None
    if a in DENYLIST:
        return None
    return a


def normalize_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def group_category(cat: str) -> str:
    if cat in CATEGORY_GROUP_OVERRIDES:
        return CATEGORY_GROUP_OVERRIDES[cat]
    c = (cat or "").lower() if isinstance(cat, str) else ""
    if c == "dexs" or c.startswith("dex "):
        return "DEX"
    if "nft" in c:
        return "NFT"
    if "gam" in c or "metaverse" in c:
        return "Gaming"
    if "social" in c:
        return "Social"
    if any(k in c for k in ["bridge", "oracle", "wallet", "infra", "rpc",
                            "privacy", "developer", "data", "services"]):
        return "Infrastructure"
    if any(k in c for k in ["lend", "borrow", "yield", "staking", "derivative",
                            "cdp", "perp", "option", "stablecoin", "insurance",
                            "payment", "rwa", "launchpad", "algo", "index",
                            "leverage", "synthetic", "prediction", "farm",
                            "vault", "liquidity", "liquid staking"]):
        return "DeFi"
    return "Other"


def connect(threads: int):
    con = duckdb.connect(str(OUT / "dapp_v2.duckdb"))
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET s3_region='us-east-2';")
    con.execute(f"SET threads={threads};")
    con.execute(f"SET temp_directory='{(OUT / 'tmp').as_posix()}';")
    (OUT / "tmp").mkdir(exist_ok=True)
    try:
        con.execute("CREATE OR REPLACE SECRET aws_anon (TYPE s3, REGION 'us-east-2')")
    except Exception as e:
        log.debug(f"could not create anonymous S3 secret: {e}")
    for s in ["SET http_retries=8", "SET http_retry_wait_ms=2000",
              "SET http_retry_backoff=2", "SET http_timeout=120000"]:
        try:
            con.execute(s)
        except Exception as e:
            log.debug(f"'{s}' not supported: {e}")
    # Attach v1 DB read-only for the creation table, if present
    if V1_DB.exists():
        try:
            con.execute(f"ATTACH '{V1_DB.as_posix()}' AS v1 (READ_ONLY)")
            n = con.execute("SELECT COUNT(*) FROM v1.creation").fetchone()[0]
            log.info(f"attached v1 DB ({n:,} creation rows) from {V1_DB}")
        except Exception as e:
            log.warning(f"could not attach v1 creation table: {e}")
    else:
        log.warning(f"v1 DB not found at {V1_DB}; deployer expansion needs --scan-creation "
                    f"or a prior v1 run")
    log.info(f"DuckDB {duckdb.__version__} connected to {OUT / 'dapp_v2.duckdb'} ({db_size()})")
    return con


def execute_retry(con, sql, tries=5, wait=15):
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
def step1_registry(top_n: int | None) -> pd.DataFrame:
    f = OUT / "protocols.csv"
    if f.exists():
        df = pd.read_csv(f)
        log.info(f"[1/5] Using cached {f} ({len(df)} DApps)")
        if top_n and len(df) > top_n:
            log.warning(f"  cached file has {len(df)} DApps but --top-n is {top_n}; "
                        f"delete {f} to apply --top-n")
        return df

    log.info("[1/5] Fetching DApp registry from DeFiLlama ...")
    raw = requests.get("https://api.llama.fi/protocols", timeout=120).json()
    all_chains = pd.DataFrame(raw)
    log.debug(f"  {len(all_chains)} protocols returned")
    df = all_chains[all_chains["chains"].apply(
        lambda c: isinstance(c, list) and "Ethereum" in c)].copy()
    log.debug(f"  {len(df)} list Ethereum")

    for col in ["slug", "name", "category", "listedAt", "symbol", "address",
                "tvl", "parentProtocol", "module", "url"]:
        if col not in df.columns:
            df[col] = None

    # Drop non-app categories
    before = len(df)
    df = df[~df["category"].isin(DROP_CATEGORIES)].copy()
    log.debug(f"  dropped {before - len(df)} CEX/Chain protocols")

    df["token_address"] = df["address"].apply(parse_eth_address)
    df["category_group"] = df["category"].apply(group_category)
    df["listed_date"] = pd.to_datetime(df["listedAt"], unit="s", errors="coerce").dt.date
    sym = df["symbol"].fillna("-").astype(str).str.strip()
    df["has_token"] = (sym != "-") & (sym != "")

    # Parent protocol: DeFiLlama uses "parent#slug" style; fall back to slug
    def parent_of(row):
        pp = row.get("parentProtocol")
        if isinstance(pp, str) and pp.strip():
            # e.g. "parent#uniswap" or just "uniswap"
            return pp.split("#")[-1].strip().lower()
        return row["slug"]

    df["parent_protocol"] = df.apply(parent_of, axis=1)
    df["module"] = df["module"].fillna("").astype(str)

    df = df.sort_values("tvl", ascending=False, na_position="last")
    if top_n:
        # Keep top-N by TVL, parent siblings, and anything referenced by app_seeds.csv
        top_slugs = set(df.head(top_n)["slug"])
        top_parents = set(df.head(top_n)["parent_protocol"])
        seed_slugs = _seed_slugs()
        df = df[
            df["slug"].isin(top_slugs)
            | df["parent_protocol"].isin(top_parents)
            | df["slug"].isin(seed_slugs)
        ].copy()

    cols = ["slug", "name", "category", "category_group", "listed_date",
            "symbol", "has_token", "token_address", "tvl",
            "parent_protocol", "module", "url"]
    df = df[cols]

    df = _inject_curated_only_protocols(df, all_chains)

    df.to_csv(f, index=False)
    log.info(f"  {len(df)} DApps -> {f}")
    log.debug(f"  by category group: {df['category_group'].value_counts().to_dict()}")
    return df


def _seed_slugs() -> set[str]:
    if not SEEDS_FILE.exists():
        return set()
    return set(pd.read_csv(SEEDS_FILE)["slug"].dropna().astype(str))


def _inject_curated_only_protocols(df: pd.DataFrame, all_chains: pd.DataFrame) -> pd.DataFrame:
    """Add a registry row for every app_seeds.csv slug that is not an Ethereum DeFiLlama slug."""
    llama = all_chains.set_index("slug") if "slug" in all_chains else pd.DataFrame()
    extras = []
    for slug in sorted(_seed_slugs() - set(df["slug"])):
        name, cat = CURATED_META.get(slug, (None, None))
        if slug in llama.index:
            row = llama.loc[slug]
            name = name or row.get("name")
            cat = cat or row.get("category")
        name = name or slug.replace("-", " ").title()
        cat = cat or "Other"
        extras.append({
            "slug": slug,
            "name": name,
            "category": cat,
            "category_group": group_category(cat),
            "listed_date": None,
            "symbol": "-",
            "has_token": False,
            "token_address": None,
            "tvl": 0.0,
            "parent_protocol": slug,
            "module": "",
            "url": "",
        })
    if extras:
        df = pd.concat([df, pd.DataFrame(extras)], ignore_index=True)
        log.info(f"  injected {len(extras)} curated-only protocols "
                 f"({[e['slug'] for e in extras]})")
    for slug, (_, cat) in CURATED_META.items():
        mask = df["slug"] == slug
        if mask.any():
            df.loc[mask, "category"] = cat
            df.loc[mask, "category_group"] = group_category(cat)
    return df


# ----------------------------------------- step 2: app-contract discovery
def load_curated_seeds(reg: pd.DataFrame) -> pd.DataFrame:
    if not SEEDS_FILE.exists():
        log.warning(f"  {SEEDS_FILE} not found; curated seeds empty")
        return pd.DataFrame(columns=["contract", "protocol", "role", "source",
                                     "factory_topic0", "child_location"])
    seeds = pd.read_csv(SEEDS_FILE)
    seeds["address"] = seeds["address"].apply(parse_eth_address)
    seeds = seeds.dropna(subset=["address"])
    missing = sorted(set(seeds["slug"]) - set(reg["slug"]))
    if missing:
        log.warning(f"  {len(missing)} seed slugs not in registry (delete protocols.csv "
                    f"to rebuild it): {missing}")
    seeds["protocol"] = seeds["slug"]
    seeds["contract"] = seeds["address"]
    seeds["source"] = "curated"
    for c in ["factory_topic0", "child_location", "role"]:
        if c not in seeds.columns:
            seeds[c] = ""
        seeds[c] = seeds[c].fillna("").astype(str)
    seeds["role"] = seeds["role"].replace("", "app")
    log.info(f"  curated seeds: {len(seeds)} addresses "
             f"({seeds['protocol'].nunique()} protocols)")
    return seeds[["contract", "protocol", "role", "source",
                  "factory_topic0", "child_location"]]


def download_adapters_zip() -> Path:
    zpath = CACHE / "DefiLlama-Adapters-main.zip"
    if zpath.exists() and zpath.stat().st_size > 1_000_000:
        log.info(f"  using cached adapters zip ({zpath.stat().st_size / 1e6:.1f} MB)")
        return zpath
    url = "https://github.com/DefiLlama/DefiLlama-Adapters/archive/refs/heads/main.zip"
    log.info(f"  downloading DefiLlama-Adapters ...")
    r = requests.get(url, timeout=300, stream=True)
    r.raise_for_status()
    with open(zpath, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
    log.info(f"  saved {zpath} ({zpath.stat().st_size / 1e6:.1f} MB)")
    return zpath


ADDR_RE = re.compile(r"0x[0-9a-fA-F]{40}")
# Heuristic: prefer addresses near ethereum/eth/mainnet keys in adapter source
ETH_CTX_RE = re.compile(
    r"""(?:ethereum|eth(?:ereum)?|mainnet)\s*['":\]]""",
    re.IGNORECASE,
)


def extract_adapter_addresses(reg: pd.DataFrame) -> pd.DataFrame:
    zpath = download_adapters_zip()
    token_addrs = set(reg["token_address"].dropna().str.lower())
    rows = []
    with zipfile.ZipFile(zpath) as zf:
        # projects/<dir>/... and projects/<name>.js, keyed by lowercase dir / name
        by_dir: dict[str, list[str]] = {}
        for n in zf.namelist():
            if n.endswith("/") or not n.endswith((".js", ".ts", ".json")):
                continue
            parts = n.split("/")
            if len(parts) >= 3 and parts[1] == "projects":
                key = parts[2].lower().removesuffix(".js").removesuffix(".ts")
                by_dir.setdefault(key, []).append(n)
        for _, row in reg.iterrows():
            module = row["module"] if isinstance(row["module"], str) else ""
            # DeFiLlama module looks like "aave/index.js"; adapters live in projects/<dir>/
            module = module.strip().strip("/")
            module = module.split("/")[0] if "/" in module else module.removesuffix(".js")
            candidates = by_dir.get(module.lower()) or by_dir.get(str(row["slug"]).lower(), [])
            if not candidates:
                continue
            seen = set()
            for n in candidates[:40]:  # cap files per protocol
                try:
                    text = zf.read(n).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                # Prefer ethereum-context chunks; fall back to whole file
                chunks = []
                for m in ETH_CTX_RE.finditer(text):
                    start = max(0, m.start() - 50)
                    end = min(len(text), m.end() + 800)
                    chunks.append(text[start:end])
                search_text = "\n".join(chunks) if chunks else text
                for a in ADDR_RE.findall(search_text):
                    a = a.lower()
                    if a in DENYLIST or a in token_addrs or a in seen:
                        continue
                    seen.add(a)
                    rows.append({
                        "contract": a,
                        "protocol": row["slug"],
                        "role": "app",
                        "source": "adapter",
                        "factory_topic0": "",
                        "child_location": "",
                    })
    df = pd.DataFrame(rows)
    if df.empty:
        log.warning("  adapter extraction found 0 addresses")
        return pd.DataFrame(columns=["contract", "protocol", "role", "source",
                                     "factory_topic0", "child_location"])
    df = df.drop_duplicates(["contract", "protocol"])
    log.info(f"  adapters: {len(df):,} addresses for {df['protocol'].nunique()} protocols")
    return df


def download_etherscan_labels() -> Path | None:
    """Try a few known open label dumps; return path or None."""
    targets = [
        ("etherscan-labels.json",
         "https://raw.githubusercontent.com/brianleect/etherscan-labels/master/data/etherscan/combined/combinedLabelledAddresses.json"),
        ("etherscan-labels-alt.json",
         "https://raw.githubusercontent.com/brianleect/etherscan-labels/main/data/etherscan/combined/combinedLabelledAddresses.json"),
    ]
    for name, url in targets:
        path = CACHE / name
        if path.exists() and path.stat().st_size > 10_000:
            return path
        try:
            log.info(f"  downloading etherscan labels from {url[:60]}...")
            r = requests.get(url, timeout=120)
            if r.status_code == 200 and len(r.content) > 10_000:
                path.write_bytes(r.content)
                return path
            log.debug(f"  labels fetch status={r.status_code} size={len(r.content)}")
        except Exception as e:
            log.debug(f"  labels fetch failed: {e}")
    return None


def extract_label_addresses(reg: pd.DataFrame) -> pd.DataFrame:
    path = download_etherscan_labels()
    if path is None:
        log.warning("  etherscan labels unavailable; skipping")
        return pd.DataFrame(columns=["contract", "protocol", "role", "source",
                                     "factory_topic0", "child_location"])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning(f"  could not parse labels: {e}")
        return pd.DataFrame(columns=["contract", "protocol", "role", "source",
                                     "factory_topic0", "child_location"])

    # Build lookup: normalized name/slug -> protocol slug
    lookup = {}
    for _, row in reg.iterrows():
        for key in (row["slug"], row["name"], row["parent_protocol"]):
            n = normalize_name(str(key))
            if n and n not in lookup:
                lookup[n] = row["slug"]

    rows = []
    # Expected shapes: {address: {name, labels, ...}} or list of dicts
    items = data.items() if isinstance(data, dict) else (
        ((d.get("address") or d.get("Account"), d) for d in data if isinstance(d, dict))
    )
    token_addrs = set(reg["token_address"].dropna().str.lower())
    for addr, meta in items:
        a = parse_eth_address(str(addr))
        if not a or a in token_addrs:
            continue
        if not isinstance(meta, dict):
            continue
        labels = meta.get("labels") or meta.get("Labels") or []
        if isinstance(labels, str):
            labels = [labels]
        name = str(meta.get("name") or meta.get("Name") or "")
        text_bits = [name] + [str(x) for x in labels]
        matched = None
        for bit in text_bits:
            n = normalize_name(bit)
            if n in lookup:
                matched = lookup[n]
                break
            # substring match for longer names
            for k, slug in lookup.items():
                if len(k) >= 5 and (k in n or n in k):
                    matched = slug
                    break
            if matched:
                break
        if matched:
            rows.append({
                "contract": a,
                "protocol": matched,
                "role": "app",
                "source": "label",
                "factory_topic0": "",
                "child_location": "",
            })
    df = pd.DataFrame(rows)
    if df.empty:
        log.info("  labels: 0 matched addresses")
        return pd.DataFrame(columns=["contract", "protocol", "role", "source",
                                     "factory_topic0", "child_location"])
    df = df.drop_duplicates(["contract", "protocol"])
    log.info(f"  labels: {len(df):,} addresses for {df['protocol'].nunique()} protocols")
    return df


def step2_discover(reg: pd.DataFrame, skip_adapters: bool, skip_labels: bool) -> pd.DataFrame:
    f = OUT / "discovered_raw.csv"
    if f.exists():
        df = pd.read_csv(f)
        log.info(f"[2/5] Using cached {f} ({len(df):,} rows)")
        return df

    log.info("[2/5] Discovering app contracts (curated + adapters + labels) ...")
    parts = [load_curated_seeds(reg)]
    if not skip_adapters:
        try:
            parts.append(extract_adapter_addresses(reg))
        except Exception as e:
            log.warning(f"  adapter extraction failed: {e}")
            log.debug("traceback:", exc_info=True)
    else:
        log.info("  --skip-adapters")
    if not skip_labels:
        try:
            parts.append(extract_label_addresses(reg))
        except Exception as e:
            log.warning(f"  label extraction failed: {e}")
            log.debug("traceback:", exc_info=True)
    else:
        log.info("  --skip-labels")

    df = pd.concat(parts, ignore_index=True)
    df["contract"] = df["contract"].str.lower()
    df = df[~df["contract"].isin(DENYLIST)]
    df.to_csv(f, index=False)
    log.info(f"  discovered {len(df):,} raw mappings "
             f"({df['source'].value_counts().to_dict()}) -> {f}")
    return df


# ----------------------------------------- step 3: expand + clean
def factory_expand(con, seeds: pd.DataFrame, end: dt.date) -> pd.DataFrame:
    """Expand curated factories via PairCreated / PoolCreated-style events in logs."""
    factories = seeds[
        (seeds["source"] == "curated")
        & (seeds["role"] == "factory")
        & (seeds["factory_topic0"].astype(str).str.len() > 10)
    ].drop_duplicates("contract")
    if factories.empty:
        log.info("  no factories with topic0; skipping factory expansion")
        return pd.DataFrame(columns=["contract", "protocol", "role", "source",
                                     "factory_topic0", "child_location"])

    cols = table_columns(con, "logs")
    # AWS public-blockchain eth/logs uses topics VARCHAR[] (not topic0/topic1/...)
    need(cols, ["address", "data"], "logs")
    if "topics" in cols:
        topic0_expr = "lower(l.topics[1])"  # DuckDB arrays are 1-indexed
        log.info(f"  factory expansion: {len(factories)} factories; "
                 f"using topics[1] as topic0")
    elif "topic0" in cols:
        topic0_expr = "lower(l.topic0)"
        log.info(f"  factory expansion: {len(factories)} factories; using topic0 column")
    else:
        fail(f"logs missing topics/topic0. Columns: {sorted(cols)}")

    # Child address: child_location=data0 (default) | topic2 | topic3
    # data0 = rightmost 40 hex of first 32-byte word of data
    def child_sql(loc: str) -> str:
        loc = (loc or "data0").strip().lower()
        if loc in ("topic2", "topic_2"):
            if "topics" in cols:
                return "lower('0x' || substr(l.topics[2], -40))"
            return "lower('0x' || substr(l.topic2, -40))"
        if loc in ("topic3", "topic_3"):
            if "topics" in cols:
                return "lower('0x' || substr(l.topics[3], -40))"
            return "lower('0x' || substr(l.topic3, -40))"
        if loc in ("data1", "data_1"):
            # 2nd 32-byte word of data (Uniswap V3 PoolCreated: tickSpacing then pool)
            return "lower('0x' || substr(l.data, 91, 40))"
        # data0 / default — Uniswap V2 PairCreated puts pair in first data word
        return "lower('0x' || substr(l.data, 27, 40))"

    con.register("factories_df", factories[["contract", "protocol", "factory_topic0",
                                            "child_location"]])
    con.execute("CREATE OR REPLACE TEMP TABLE factories AS SELECT * FROM factories_df")
    legacy = con.execute("""SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'factory_children' AND column_name = 'protocol'""").fetchone()[0]
    if legacy:
        log.warning("  factory_children has the old schema (no factory column); rescanning")
        con.execute("DROP TABLE factory_children; DROP TABLE IF EXISTS factory_done_months;")
    con.execute("""CREATE TABLE IF NOT EXISTS factory_children(
        factory VARCHAR, contract VARCHAR, factory_topic0 VARCHAR, child_location VARCHAR)""")
    con.execute("CREATE TABLE IF NOT EXISTS factory_done(factory VARCHAR, month DATE)")
    done = set(con.execute("SELECT factory, month FROM factory_done").fetchall())

    # Scan each factory from the month it was deployed (Uniswap V2, the earliest, is 2020-05)
    first_month = {}
    try:
        first_month = dict(con.execute("""
            SELECT f.contract, date_trunc('month', MIN(c.deployed_date))::DATE
            FROM factories f JOIN v1.creation c ON c.contract = f.contract
            GROUP BY 1""").fetchall())
    except Exception as e:
        log.debug(f"  factory deploy dates unavailable: {e}")
    months = pd.date_range("2020-05-01", end, freq="MS")
    todo = {}
    for mo in months:
        pending = [f for f in factories["contract"]
                   if (f, mo.date()) not in done
                   and mo.date() >= first_month.get(f, dt.date(2020, 5, 1))]
        if pending:
            todo[mo] = pending
    log.info(f"  factory scan: {len(todo)} months to process for {len(factories)} factories")

    loc_of = dict(zip(factories["contract"],
                      factories["child_location"].fillna("").replace("", "data0").str.lower()))
    for i, (month, pending) in enumerate(todo.items(), 1):
        m = month.date()
        glob = f"{BASE}/logs/date={month:%Y-%m}-*/*.parquet"
        t0 = time.time()
        try:
            n_total = 0
            for loc in sorted({loc_of[f] for f in pending}):
                addrs = ",".join(f"'{f}'" for f in pending if loc_of[f] == loc)
                topic_len = "AND len(l.topics) >= 1" if "topics" in cols else ""
                min_data = 130 if loc.startswith("data1") else 66
                n = execute_retry(con, f"""
                    INSERT INTO factory_children
                    SELECT DISTINCT f.contract, {child_sql(loc)},
                           f.factory_topic0, f.child_location
                    FROM read_parquet('{glob}', hive_partitioning=true) l
                    JOIN factories f
                      ON l.address = f.contract
                     AND {topic0_expr} = lower(f.factory_topic0)
                    WHERE f.contract IN ({addrs})
                      AND length(l.data) >= {min_data}
                      {topic_len}
                """).fetchone()[0]
                n_total += n
            con.executemany("INSERT INTO factory_done VALUES (?, ?)", [(f, m) for f in pending])
            log.info(f"    [{i}/{len(todo)}] {month:%Y-%m}: {n_total:>8,} children "
                     f"({len(pending)} factories) in {fmt_secs(time.time() - t0)}")
        except Exception as e:
            if "No files found" in str(e):
                con.executemany("INSERT INTO factory_done VALUES (?, ?)",
                                [(f, m) for f in pending])
                log.info(f"    [{i}/{len(todo)}] {month:%Y-%m}: no data (skipped)")
                continue
            log.error(f"    [{i}/{len(todo)}] {month:%Y-%m}: FAILED ({str(e)[:150]})")
            log.debug("traceback:", exc_info=True)

    # Label children from the current seed file so relabeling a factory never needs a rescan
    children = con.execute("""
        SELECT DISTINCT c.contract, f.protocol, 'pool' AS role, 'factory' AS source,
               c.factory_topic0, c.child_location
        FROM factory_children c JOIN factories f ON c.factory = f.contract""").df()
    children = children[children["contract"].apply(
        lambda a: bool(re.fullmatch(r"0x[0-9a-f]{40}", str(a)))
    )]
    children = children[~children["contract"].isin(DENYLIST)]
    log.info(f"  factory children total: {len(children):,} "
             f"({children['protocol'].value_counts().to_dict()})")
    return children


def deployer_expand(con, seeds: pd.DataFrame, end: dt.date,
                    max_per_deployer: int, scan_creation: bool) -> pd.DataFrame:
    """Expand via same-deployer heuristic using v1 creation table (or scan)."""
    has_creation = False
    try:
        n = con.execute("SELECT COUNT(*) FROM v1.creation").fetchone()[0]
        has_creation = n > 0
        log.info(f"  using v1.creation ({n:,} rows) for deployer expansion")
    except Exception:
        has_creation = False

    if not has_creation:
        if not scan_creation:
            log.warning("  no creation table; skip deployer expansion "
                        "(pass --scan-creation to build one, expensive)")
            return pd.DataFrame(columns=["contract", "protocol", "role", "source",
                                         "factory_topic0", "child_location"])
        log.info("  scanning contract creations into local creation table ...")
        _scan_creation(con, end)
        creation_ref = "creation"
    else:
        creation_ref = "v1.creation"

    seed_addrs = seeds[["contract", "protocol"]].drop_duplicates("contract")
    con.register("app_seeds_df", seed_addrs)
    con.execute("CREATE OR REPLACE TEMP TABLE app_seeds AS SELECT * FROM app_seeds_df")

    t0 = time.time()
    exp = con.execute(f"""
        WITH cr AS (
          SELECT deployer, contract, deployed_date
          FROM {creation_ref}
          WHERE deployed_date <= DATE '{end}'
        ),
        dep AS (
          SELECT c.deployer, ANY_VALUE(s.protocol) AS protocol
          FROM cr c
          JOIN app_seeds s ON lower(c.contract) = s.contract
          GROUP BY 1 HAVING COUNT(DISTINCT s.protocol) = 1
        ),
        cnt AS (SELECT deployer, COUNT(*) AS n FROM cr GROUP BY 1)
        SELECT lower(c.contract) AS contract, d.protocol,
               'app' AS role, 'deployer' AS source,
               '' AS factory_topic0, '' AS child_location
        FROM cr c
        JOIN dep d USING (deployer)
        JOIN cnt n USING (deployer)
        WHERE n.n <= {int(max_per_deployer)}
    """).df()
    log.info(f"  deployer expansion: {len(exp):,} contracts for "
             f"{exp['protocol'].nunique() if len(exp) else 0} protocols "
             f"in {fmt_secs(time.time() - t0)}")
    return exp


def _scan_creation(con, end: dt.date) -> None:
    cols = table_columns(con, "transactions")
    need(cols, ["from_address", "to_address", "receipt_contract_address"], "transactions")
    status = "AND receipt_status = 1" if "receipt_status" in cols else ""
    con.execute("""CREATE TABLE IF NOT EXISTS creation(
        deployer VARCHAR, contract VARCHAR, deployed_date DATE)""")
    con.execute("CREATE TABLE IF NOT EXISTS creation_done_months(month DATE)")
    done = {r[0] for r in con.execute("SELECT month FROM creation_done_months").fetchall()}
    months = pd.date_range("2015-07-01", end, freq="MS")
    todo = [mo for mo in months if mo.date() not in done]
    for i, month in enumerate(todo, 1):
        m = month.date()
        glob = f"{BASE}/transactions/date={month:%Y-%m}-*/*.parquet"
        try:
            n = execute_retry(con, f"""
                INSERT INTO creation
                SELECT from_address, lower(receipt_contract_address), date::DATE
                FROM read_parquet('{glob}', hive_partitioning=true)
                WHERE (to_address IS NULL OR to_address IN ('', 'None'))
                  AND receipt_contract_address NOT IN ('', 'None')
                  AND date <= DATE '{end}' {status}""").fetchone()[0]
            con.execute(f"INSERT INTO creation_done_months VALUES (DATE '{m}')")
            log.info(f"    creation [{i}/{len(todo)}] {month:%Y-%m}: {n:,}")
        except Exception as e:
            if "No files found" in str(e):
                con.execute(f"INSERT INTO creation_done_months VALUES (DATE '{m}')")
                continue
            log.error(f"    creation {month:%Y-%m} FAILED: {e}")


def flag_erc20_tokens(con, contracts: pd.DataFrame) -> pd.DataFrame:
    """Flag contracts whose bytecode contains all four ERC20 selectors."""
    if contracts.empty:
        contracts["is_token"] = False
        contracts["deployed_date"] = pd.NaT
        return contracts

    addrs = contracts[["contract"]].drop_duplicates()
    con.register("addr_df", addrs)
    con.execute("CREATE OR REPLACE TEMP TABLE addrs AS SELECT * FROM addr_df")
    log.info(f"  looking up bytecode/deploy dates for {len(addrs):,} contracts ...")
    t0 = time.time()
    need(table_columns(con, "contracts"), ["address", "bytecode"], "contracts")
    # Test selectors per row so bytecode is never held in memory across the aggregation
    has_selectors = " AND ".join(f"contains(lower(bytecode), '{s}')" for s in ERC20_SELECTORS)
    con.execute("SET preserve_insertion_order=false")
    try:
        info = execute_retry(con, f"""
            SELECT lower(address) AS contract,
                   MIN(date)::DATE AS deployed_date,
                   bool_or(coalesce(length(bytecode) >= 20 AND {has_selectors}, false)) AS is_token
            FROM read_parquet('{BASE}/contracts/date=*/*.parquet', hive_partitioning=true)
            WHERE address IN (SELECT contract FROM addrs)
            GROUP BY 1
        """).df()
    except Exception as e:
        raise RuntimeError(
            f"bytecode lookup failed ({str(e)[:300]}); app_contracts.csv was not written. "
            "Re-run, or lower --threads if this was an out-of-memory error.") from e
    log.info(f"  found bytecode for {len(info):,}/{len(addrs):,} "
             f"in {fmt_secs(time.time() - t0)}")

    out = contracts.merge(info, on="contract", how="left")
    out["is_token"] = out["is_token"].fillna(False).astype(bool)
    out["deployed_date"] = pd.to_datetime(out["deployed_date"])
    n_tok = int(out["is_token"].sum())
    log.info(f"  flagged {n_tok:,} ERC20-like contracts")
    return out


def resolve_conflicts(raw: pd.DataFrame, reg: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = raw.copy()
    raw["priority"] = raw["source"].map(SOURCE_PRIORITY).fillna(99)
    raw["confidence"] = raw["source"].map(SOURCE_CONFIDENCE).fillna("low")
    parent_map = dict(zip(reg["slug"], reg["parent_protocol"]))
    raw["parent_protocol"] = raw["protocol"].map(parent_map).fillna(raw["protocol"])

    # Conflicts: same contract claimed by different parent_protocols
    winners = (raw.sort_values("priority")
               .drop_duplicates("contract", keep="first"))
    claimed = raw.merge(
        winners[["contract", "protocol", "parent_protocol", "source"]]
        .rename(columns={"protocol": "winner_protocol",
                         "parent_protocol": "winner_parent",
                         "source": "winner_source"}),
        on="contract",
    )
    conflicts = claimed[
        claimed["parent_protocol"] != claimed["winner_parent"]
    ][["contract", "protocol", "parent_protocol", "source",
       "winner_protocol", "winner_parent", "winner_source"]].drop_duplicates()
    if len(conflicts):
        conflicts.to_csv(OUT / "contract_conflicts.csv", index=False)
        log.info(f"  {len(conflicts):,} conflict rows -> {OUT / 'contract_conflicts.csv'}")
    else:
        log.info("  no cross-protocol conflicts")
    return winners, conflicts


def step3_expand_clean(con, reg, discovered, end, no_factory, no_deployer,
                       max_per_deployer, scan_creation) -> pd.DataFrame:
    f = OUT / "app_contracts.csv"
    if f.exists():
        cm = pd.read_csv(f, parse_dates=["deployed_date"])
        log.info(f"[3/5] Using cached {f} ({len(cm):,} contracts, "
                 f"{cm['protocol'].nunique()} DApps)")
        return cm

    log.info("[3/5] Expanding and cleaning app contracts ...")
    parts = [discovered]

    if not no_factory:
        parts.append(factory_expand(con, discovered, end))
    else:
        log.info("  --no-factory-expansion")

    if not no_deployer:
        parts.append(deployer_expand(con, discovered, end, max_per_deployer, scan_creation))
    else:
        log.info("  --no-deployer-expansion")

    raw = pd.concat(parts, ignore_index=True)
    raw["contract"] = raw["contract"].str.lower()
    raw = raw[raw["contract"].apply(lambda a: bool(re.fullmatch(r"0x[0-9a-f]{40}", str(a))))]
    raw = raw[~raw["contract"].isin(DENYLIST)]
    raw = raw.drop_duplicates(["contract", "protocol", "source"])

    parent_map = dict(zip(reg["slug"], reg["parent_protocol"]))
    n_claims = (raw.assign(parent=raw["protocol"].map(parent_map).fillna(raw["protocol"]))
                .groupby("contract")["parent"].nunique().rename("n_claims"))

    winners, _ = resolve_conflicts(raw, reg)
    winners = winners.merge(n_claims, on="contract", how="left")
    trusted = winners["source"].isin(["curated", "factory"])

    # Addresses many adapters mention (oracles, routers, shared vaults) aren't one app's
    shared = ~trusted & (winners["n_claims"] >= 3)
    winners = winners[~shared].copy()
    trusted = trusted[~shared]
    log.info(f"  dropped {int(shared.sum()):,} untrusted addresses claimed by 3+ protocols")

    winners = flag_erc20_tokens(con, winners)
    # A token claimed by several protocols is a shared asset (USDC, DAI, ...); a token only
    # one protocol claims is usually its own vault / LP / receipt token, which users call
    drop_token = ~trusted.values & winners["is_token"].values & (winners["n_claims"].values > 1)
    winners = winners[~drop_token].copy()
    log.info(f"  dropped {int(drop_token.sum()):,} shared ERC20 tokens; kept "
             f"{int(winners['is_token'].sum()):,} single-app / curated / pool tokens")

    parent_map = dict(zip(reg["slug"], reg["parent_protocol"]))
    winners["parent_protocol"] = winners["protocol"].map(parent_map).fillna(winners["protocol"])
    winners["confidence"] = winners["source"].map(SOURCE_CONFIDENCE).fillna("low")

    cols = ["contract", "protocol", "parent_protocol", "role", "source",
            "confidence", "is_token", "deployed_date"]
    for c in cols:
        if c not in winners.columns:
            winners[c] = None
    winners = winners[cols]
    winners.to_csv(f, index=False)
    log.info(f"  {len(winners):,} app contracts -> {f} "
             f"({winners['source'].value_counts().to_dict()})")
    return winners


# ------------------------------------------ step 4: activity (logs + direct)
def step4_activity(con, cmap: pd.DataFrame, start: dt.date, end: dt.date,
                   heavy_tx_threshold: int) -> pd.DataFrame:
    f = OUT / "activity.csv"
    if f.exists():
        act = pd.read_csv(f, parse_dates=["month"])
        log.info(f"[4/5] Using cached {f} ({len(act):,} DApp-month rows)")
        return act

    log.info("[4/5] Computing monthly activity from logs + direct calls ...")
    t_step = time.time()

    tx_cols = table_columns(con, "transactions")
    need(tx_cols, ["from_address", "to_address", "value", "hash"], "transactions")
    log_cols = table_columns(con, "logs")
    need(log_cols, ["address", "transaction_hash"], "logs")

    gas_col = "receipt_gas_used" if "receipt_gas_used" in tx_cols else "gas"
    price_col = ("receipt_effective_gas_price"
                 if "receipt_effective_gas_price" in tx_cols else "gas_price")
    status_filter = "AND t.receipt_status = 1" if "receipt_status" in tx_cols else ""

    has_old_map = con.execute("""SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = 'cmap'""").fetchone()[0]
    old_map = (con.execute("SELECT contract, protocol FROM cmap").df()
               if has_old_map else None)
    con.register("cmap_df", cmap[["contract", "protocol"]])
    con.execute("CREATE OR REPLACE TABLE cmap AS SELECT * FROM cmap_df")
    con.execute("CREATE TABLE IF NOT EXISTS meta(k VARCHAR, v VARCHAR)")
    has_first = con.execute("""SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'wallet_month_v2' AND column_name = 'first_date'""").fetchone()[0]
    if not has_first:
        con.execute("DROP TABLE IF EXISTS wallet_month_v2; DELETE FROM meta WHERE k='map_hash';")
    con.execute("""CREATE TABLE IF NOT EXISTS wallet_month_v2(
        protocol VARCHAR, month DATE, wallet VARCHAR, tx_count BIGINT,
        gas_used DOUBLE, fees_eth DOUBLE, eth_value DOUBLE,
        n_protocols_avg DOUBLE, first_date DATE)""")
    con.execute("""CREATE TABLE IF NOT EXISTS heavy_wallets(
        month DATE, wallet VARCHAR, tx_count BIGINT)""")
    con.execute("CREATE TABLE IF NOT EXISTS done_months_v2(month DATE)")

    def map_hash(df):
        return hashlib.md5("".join(sorted(df["contract"] + df["protocol"])).encode()).hexdigest()

    h = map_hash(cmap)
    old = con.execute("SELECT v FROM meta WHERE k='map_hash'").fetchone()
    if old is None or old[0] != h:
        cutoff = None
        if old is not None and old_map is not None and map_hash(old_map) == old[0]:
            old_pairs = set(zip(old_map["contract"], old_map["protocol"]))
            new_pairs = set(zip(cmap["contract"], cmap["protocol"]))
            if old_pairs <= new_pairs:
                added = cmap[[p in new_pairs - old_pairs
                              for p in zip(cmap["contract"], cmap["protocol"])]]
                dep = pd.to_datetime(added["deployed_date"], errors="coerce")
                # New factory pools come only from newly scanned (later) months, so an
                # unknown deploy date for them doesn't put earlier cached months at risk
                if "source" in added.columns:
                    dep = dep[dep.notna() | (added["source"] != "factory").values]
                # Months before the earliest added contract existed cannot contain its activity
                if not len(dep):
                    cutoff = dt.date.max
                elif dep.notna().all():
                    cutoff = dep.min().to_period("M").to_timestamp().date()
        if cutoff is not None:
            log.warning(f"  contract map grew; recomputing cached months from {cutoff:%Y-%m}")
            for t in ("wallet_month_v2", "heavy_wallets", "done_months_v2"):
                con.execute(f"DELETE FROM {t} WHERE month >= DATE '{cutoff}'")
        else:
            if old is not None:
                log.warning("  contract map changed; clearing cached activity")
            con.execute("DELETE FROM wallet_month_v2; DELETE FROM done_months_v2; "
                        "DELETE FROM heavy_wallets;")
        con.execute("DELETE FROM meta WHERE k='map_hash'")
        con.execute(f"INSERT INTO meta VALUES ('map_hash','{h}')")

    done = {r[0] for r in con.execute("SELECT month FROM done_months_v2").fetchall()}
    months = pd.date_range(pd.Timestamp(start).replace(day=1), end, freq="MS")
    todo = [mo for mo in months if mo.date() not in done]
    log.info(f"  {len(cmap):,} contracts; {len(months)} months, "
             f"{len(months) - len(todo)} cached, {len(todo)} to go")

    for i, month in enumerate(todo, 1):
        m = month.date()
        tx_glob = f"{BASE}/transactions/date={month:%Y-%m}-*/*.parquet"
        log_glob = f"{BASE}/logs/date={month:%Y-%m}-*/*.parquet"
        t0 = time.time()
        try:
            # One pass over each S3 table per month; everything after this is local
            execute_retry(con, f"""
                CREATE OR REPLACE TEMP TABLE _log_hits AS
                SELECT DISTINCT m.protocol, l.transaction_hash AS tx_hash
                FROM read_parquet('{log_glob}') l
                JOIN cmap m ON l.address = m.contract""")
            execute_retry(con, f"""
                CREATE OR REPLACE TEMP TABLE _tx AS
                SELECT t.hash, t.from_address, t.to_address, t.date::DATE AS tx_date,
                       CAST(t.{gas_col} AS DOUBLE) AS gas_used,
                       CAST(t.{price_col} AS DOUBLE) * CAST(t.{gas_col} AS DOUBLE) / 1e18
                         AS fees_eth,
                       CAST(t.value AS DOUBLE) / 1e18 AS eth_value
                FROM read_parquet('{tx_glob}') t
                WHERE (t.hash IN (SELECT tx_hash FROM _log_hits)
                       OR t.to_address IN (SELECT contract FROM cmap))
                  {status_filter}""")
            con.execute("BEGIN TRANSACTION")
            n = con.execute(f"""
                INSERT INTO wallet_month_v2
                WITH hits AS (
                  SELECT protocol, tx_hash FROM _log_hits
                  UNION
                  SELECT m.protocol, t.hash FROM _tx t JOIN cmap m ON t.to_address = m.contract
                ),
                hits_n AS (
                  SELECT protocol, tx_hash,
                         COUNT(*) OVER (PARTITION BY tx_hash) AS n_protocols_in_tx
                  FROM hits
                )
                SELECT h.protocol, DATE '{m}', t.from_address,
                       COUNT(*), SUM(t.gas_used), SUM(t.fees_eth), SUM(t.eth_value),
                       AVG(h.n_protocols_in_tx), MIN(t.tx_date)
                FROM hits_n h JOIN _tx t ON t.hash = h.tx_hash
                GROUP BY 1, 3""").fetchone()[0]
            con.execute(f"""
                INSERT INTO heavy_wallets
                SELECT DATE '{m}', wallet, SUM(tx_count)
                FROM wallet_month_v2
                WHERE month = DATE '{m}'
                GROUP BY 2
                HAVING SUM(tx_count) > {int(heavy_tx_threshold)}""")
            con.execute(f"INSERT INTO done_months_v2 VALUES (DATE '{m}')")
            con.execute("COMMIT")
            n_dapps = con.execute(f"""
                SELECT COUNT(DISTINCT protocol) FROM wallet_month_v2
                WHERE month = DATE '{m}'""").fetchone()[0]
            level = logging.WARNING if n == 0 else logging.INFO
            log.log(level, f"    [{i}/{len(todo)}] {month:%Y-%m}: {n:>9,} wallet rows, "
                           f"{n_dapps:>4} DApps in {fmt_secs(time.time() - t0)} "
                           f"| db {db_size()}")
        except Exception as e:
            try:
                con.execute("ROLLBACK")
            except Exception:
                pass
            log.error(f"    [{i}/{len(todo)}] {month:%Y-%m}: FAILED ({str(e)[:200]}) "
                      f"- re-run to retry")
            log.debug("traceback:", exc_info=True)

    con.execute("""
        CREATE OR REPLACE TABLE wallet_first_seen AS
        SELECT protocol, wallet, MIN(first_date) AS first_date
        FROM wallet_month_v2 GROUP BY 1, 2""")

    log.info("  aggregating into DApp-month activity ...")
    act = con.execute("""
        WITH wf AS (
          SELECT w.* EXCLUDE (first_date),
                 COALESCE(f.first_date, w.month) AS first_date
          FROM wallet_month_v2 w
          LEFT JOIN wallet_first_seen f
            ON w.protocol = f.protocol AND w.wallet = f.wallet
        ),
        heavy AS (SELECT DISTINCT month, wallet FROM heavy_wallets)
        SELECT
          wf.protocol, wf.month,
          COUNT(*) AS active_wallets,
          COUNT(*) FILTER (
            WHERE date_trunc('month', wf.first_date)::DATE = wf.month
          ) AS new_wallets,
          SUM(tx_count) AS tx_count,
          SUM(gas_used) AS gas_used,
          SUM(fees_eth) AS fees_eth,
          SUM(eth_value) AS eth_value,
          AVG(n_protocols_avg) AS avg_n_protocols_in_tx,
          -- ex-heavy
          COUNT(*) FILTER (WHERE h.wallet IS NULL) AS active_wallets_ex_heavy,
          SUM(tx_count) FILTER (WHERE h.wallet IS NULL) AS tx_count_ex_heavy,
          SUM(gas_used) FILTER (WHERE h.wallet IS NULL) AS gas_used_ex_heavy
        FROM wf
        LEFT JOIN heavy h ON wf.month = h.month AND wf.wallet = h.wallet
        GROUP BY wf.protocol, wf.month
        ORDER BY wf.protocol, wf.month
    """).df()
    act["month"] = pd.to_datetime(act["month"])

    n_done = con.execute("SELECT COUNT(*) FROM done_months_v2").fetchone()[0]
    if n_done < len(months):
        log.error(f"  {len(months) - n_done} month(s) failed; {f} NOT written. Re-run.")
    else:
        act.to_csv(f, index=False)
        log.info(f"  -> {f}")
    log.info(f"  {len(act):,} DApp-month rows, {act['protocol'].nunique()} DApps "
             f"[step 4 took {fmt_secs(time.time() - t_step)}]")
    return act


# ------------------------------------------------ step 5: derived datasets
def _gini(arr: np.ndarray) -> float:
    arr = np.asarray(arr, dtype=float)
    arr = arr[arr > 0]
    if len(arr) == 0:
        return np.nan
    arr = np.sort(arr)
    n = len(arr)
    idx = np.arange(1, n + 1)
    return float((2 * np.sum(idx * arr) / (n * np.sum(arr))) - (n + 1) / n)


def _hhi(shares: np.ndarray) -> float:
    s = np.asarray(shares, dtype=float)
    s = s[s > 0]
    if len(s) == 0 or s.sum() == 0:
        return np.nan
    p = s / s.sum()
    return float(np.sum(p ** 2))


def step5_derived(con, reg, cmap, act, start, end, life_args: dict) -> None:
    log.info("[5/5] Assembling derived datasets ...")

    # ---- static ----
    agg = (cmap.groupby("protocol")
           .agg(n_contracts=("contract", "nunique"),
                first_deployed=("deployed_date", "min"))
           .reset_index().rename(columns={"protocol": "slug"}))
    static = reg.merge(agg, on="slug", how="inner")
    start_month = pd.Timestamp(start).to_period("M").to_timestamp()
    static["first_month"] = (
        pd.to_datetime(static["first_deployed"]).dt.to_period("M").dt.to_timestamp()
        .fillna(start_month)
    )
    static.drop(columns=["token_address", "module", "url"], errors="ignore") \
          .to_csv(OUT / "dapp_static.csv", index=False)
    log.info(f"  {len(static)} DApps -> dapp_static.csv")

    # ---- panel grid ----
    end_month = pd.Timestamp(end).to_period("M").to_timestamp()
    months = pd.DataFrame({"month": pd.date_range(start_month, end_month, freq="MS")})
    grid = static[["slug", "first_month", "category", "category_group",
                   "parent_protocol"]].merge(months, how="cross")
    grid = grid[grid["month"] >= grid["first_month"]]

    panel = grid.merge(act.rename(columns={"protocol": "slug"}),
                       on=["slug", "month"], how="left")
    metrics = ["active_wallets", "new_wallets", "tx_count", "gas_used",
               "fees_eth", "eth_value", "avg_n_protocols_in_tx",
               "active_wallets_ex_heavy", "tx_count_ex_heavy", "gas_used_ex_heavy"]
    for m in metrics:
        if m not in panel.columns:
            panel[m] = 0
        panel[m] = panel[m].fillna(0)
    panel = panel.sort_values(["slug", "month"])

    g = panel.groupby("slug", group_keys=False)
    panel["cum_wallets"] = g["new_wallets"].cumsum()
    panel["wallet_growth_mom"] = (
        g["active_wallets"].pct_change(fill_method=None)
        .replace([np.inf, -np.inf], np.nan)
    )
    panel["tx_per_wallet"] = np.where(
        panel["active_wallets"] > 0,
        panel["tx_count"] / panel["active_wallets"], np.nan)
    panel["months_since_launch"] = (
        (panel["month"].dt.to_period("M") - panel["first_month"].dt.to_period("M"))
        .apply(lambda x: x.n if pd.notna(x) else np.nan)
    )

    # Returning wallets / retention vs previous month (approx from new vs active)
    panel["returning_wallets"] = (panel["active_wallets"] - panel["new_wallets"]).clip(lower=0)
    prev = panel[["slug", "month", "active_wallets"]].copy()
    prev["month"] = prev["month"] + pd.offsets.MonthBegin(1)
    prev = prev.rename(columns={"active_wallets": "prev_active"})
    panel = panel.merge(prev, on=["slug", "month"], how="left")
    panel["retention_prev_month"] = np.where(
        panel["prev_active"] > 0,
        panel["returning_wallets"] / panel["prev_active"], np.nan)

    # Whale share: top-10 wallets' tx share within app-month (from wallet_month_v2)
    try:
        whale = con.execute("""
            WITH ranked AS (
              SELECT protocol, month, wallet, tx_count,
                     ROW_NUMBER() OVER (PARTITION BY protocol, month
                                       ORDER BY tx_count DESC) AS rn,
                     SUM(tx_count) OVER (PARTITION BY protocol, month) AS tot
              FROM wallet_month_v2
            )
            SELECT protocol AS slug, month,
                   SUM(tx_count) FILTER (WHERE rn <= 10) * 1.0 / NULLIF(MAX(tot), 0)
                     AS top10_wallet_share
            FROM ranked GROUP BY 1, 2
        """).df()
        whale["month"] = pd.to_datetime(whale["month"])
        panel = panel.merge(whale, on=["slug", "month"], how="left")
    except Exception as e:
        log.warning(f"  top10_wallet_share skipped: {e}")
        panel["top10_wallet_share"] = np.nan

    # Share of category / ecosystem
    for metric in ["active_wallets", "tx_count", "gas_used"]:
        cat_tot = (panel.groupby(["month", "category_group"])[metric]
                   .transform("sum"))
        eco_tot = panel.groupby("month")[metric].transform("sum")
        panel[f"share_of_category_{metric}"] = np.where(
            cat_tot > 0, panel[metric] / cat_tot, np.nan)
        panel[f"share_of_ecosystem_{metric}"] = np.where(
            eco_tot > 0, panel[metric] / eco_tot, np.nan)

    panel = panel.merge(
        static[["slug", "name", "listed_date", "symbol", "has_token",
                "n_contracts", "first_deployed", "tvl"]],
        on="slug", how="left",
    )
    month_end = panel["month"] + pd.offsets.MonthEnd(0)
    panel["contract_age_days"] = (
        month_end - pd.to_datetime(panel["first_deployed"])
    ).dt.days.clip(lower=0)
    panel = panel.drop(columns=["first_month", "prev_active"], errors="ignore")
    panel.to_csv(OUT / "dapp_panel.csv", index=False)
    log.info(f"  dapp_panel.csv: {len(panel):,} rows, {panel['slug'].nunique()} DApps")

    # ---- cohort retention ----
    try:
        # wallet_month_v2 has one row per (protocol, month, wallet), so COUNT(*) counts wallets,
        # and every wallet is active in its first month, so months_since = 0 is the cohort size
        con.execute("SET preserve_insertion_order=false")
        cohorts = con.execute("""
            WITH base AS (
              SELECT w.protocol,
                     date_trunc('month', f.first_date)::DATE AS cohort_month,
                     w.month
              FROM wallet_month_v2 w
              JOIN wallet_first_seen f
                ON w.protocol = f.protocol AND w.wallet = f.wallet
            ),
            counts AS (
              SELECT protocol, cohort_month,
                     date_diff('month', cohort_month, month) AS months_since,
                     COUNT(*) AS retained
              FROM base
              WHERE month >= cohort_month
              GROUP BY 1, 2, 3
            )
            SELECT protocol, cohort_month, months_since, retained,
                   MAX(retained) FILTER (WHERE months_since = 0)
                     OVER (PARTITION BY protocol, cohort_month) AS cohort_size
            FROM counts
            ORDER BY 1, 2, 3
        """).df()
        cohorts["retention_rate"] = cohorts["retained"] / cohorts["cohort_size"].replace(0, np.nan)
        cohorts.to_csv(OUT / "cohort_retention.csv", index=False)
        log.info(f"  cohort_retention.csv: {len(cohorts):,} rows")
    except Exception as e:
        log.warning(f"  cohort_retention skipped: {e}")

    # ---- category_month (dedup wallets across apps in category) ----
    con.register("static_df", static[["slug", "category", "category_group",
                                      "parent_protocol", "first_month"]])
    try:
        cat_month = con.execute("""
            WITH wm AS (
              SELECT w.protocol, w.month, w.wallet, w.tx_count, w.gas_used,
                     s.category_group, s.category
              FROM wallet_month_v2 w
              JOIN static_df s ON w.protocol = s.slug
            )
            SELECT month, category_group,
                   COUNT(DISTINCT wallet) AS active_wallets,
                   SUM(tx_count) AS tx_count,
                   SUM(gas_used) AS gas_used,
                   COUNT(DISTINCT protocol) AS active_dapps
            FROM wm
            GROUP BY 1, 2
            ORDER BY 1, 2
        """).df()
        cat_month["month"] = pd.to_datetime(cat_month["month"])
        # newly launched DApps per category-month
        launches = (static.assign(
            launch_month=pd.to_datetime(static["first_month"]).dt.to_period("M").dt.to_timestamp()
        ).groupby(["category_group", "launch_month"])
         .size().reset_index(name="newly_launched"))
        launches = launches.rename(columns={"launch_month": "month"})
        cat_month = cat_month.merge(launches, on=["category_group", "month"], how="left")
        cat_month["newly_launched"] = cat_month["newly_launched"].fillna(0).astype(int)
        cat_month = cat_month.sort_values(["category_group", "month"])
        cg = cat_month.groupby("category_group", group_keys=False)
        cat_month["growth_3m"] = cg["active_wallets"].pct_change(3, fill_method=None)
        cat_month["growth_12m"] = cg["active_wallets"].pct_change(12, fill_method=None)
        cat_month.to_csv(OUT / "category_month.csv", index=False)
        log.info(f"  category_month.csv: {len(cat_month):,} rows")
    except Exception as e:
        log.warning(f"  category_month skipped: {e}")
        log.debug("traceback:", exc_info=True)

    # ---- concentration_month ----
    conc_rows = []
    for metric in ["active_wallets", "tx_count", "gas_used"]:
        for scope, grp_cols in [("ecosystem", ["month"]),
                                ("category", ["month", "category_group"])]:
            for keys, sub in panel.groupby(grp_cols):
                if not isinstance(keys, tuple):
                    keys = (keys,)
                vals = sub[metric].fillna(0).values
                if vals.sum() == 0:
                    continue
                order = np.sort(vals)[::-1]
                total = order.sum()
                row = {
                    "scope": scope,
                    "month": keys[0],
                    "category_group": keys[1] if scope == "category" else "ALL",
                    "metric": metric,
                    "n_dapps": int((vals > 0).sum()),
                    "hhi": _hhi(vals),
                    "gini": _gini(vals),
                    "top1_share": float(order[0] / total) if len(order) else np.nan,
                    "top5_share": float(order[:5].sum() / total) if len(order) else np.nan,
                    "top10_share": float(order[:10].sum() / total) if len(order) else np.nan,
                }
                conc_rows.append(row)
    conc = pd.DataFrame(conc_rows)
    if len(conc):
        conc["month"] = pd.to_datetime(conc["month"])
        conc.to_csv(OUT / "concentration_month.csv", index=False)
        log.info(f"  concentration_month.csv: {len(conc):,} rows")

    # ---- dapp_lifecycle ----
    life = _build_lifecycle(panel, static, con, life_args)
    life.to_csv(OUT / "dapp_lifecycle.csv", index=False)
    log.info(f"  dapp_lifecycle.csv: {len(life):,} DApps "
             f"({life['lifecycle_label'].value_counts().to_dict()})")


def _build_lifecycle(panel: pd.DataFrame, static: pd.DataFrame, con,
                     args: dict) -> pd.DataFrame:
    rows = []
    for slug, g in panel.groupby("slug"):
        g = g.sort_values("month")
        if g.empty:
            continue
        launch = g["month"].iloc[0]
        peak_idx = g["active_wallets"].idxmax()
        peak_month = g.loc[peak_idx, "month"]
        peak_wallets = g.loc[peak_idx, "active_wallets"]
        months_to_peak = int(
            (peak_month.to_period("M") - launch.to_period("M")).n
        )
        cum = g["cum_wallets"].values
        months = g["month"].values
        aw = g["active_wallets"].values

        def months_to(threshold):
            hit = np.where(cum >= threshold)[0]
            return int(hit[0]) if len(hit) else np.nan

        half_peak_cum = 0.5 * cum.max() if cum.max() > 0 else np.nan
        months_to_half = months_to(half_peak_cum) if half_peak_cum == half_peak_cum else np.nan

        def wallets_at(m_since):
            # m_since=3 means the month 3 months after launch (months_since_launch==3)
            sub = g[g["months_since_launch"] == m_since]
            return float(sub["active_wallets"].iloc[0]) if len(sub) else np.nan

        # Decay: avg last 6 months / peak
        last6 = aw[-6:] if len(aw) >= 1 else aw
        decay = float(np.mean(last6) / peak_wallets) if peak_wallets > 0 else np.nan

        # Activity 12 months after peak
        peak_plus_12 = peak_month + pd.DateOffset(months=12)
        after = g[g["month"] == peak_plus_12]
        wallets_12_after_peak = float(after["active_wallets"].iloc[0]) if len(after) else np.nan
        months_active = int((aw > 0).sum())

        # Labels
        never_thr = args["never_adopted_max"]
        flash_peak_within = args["flash_peak_within"]
        flash_remain = args["flash_remain_frac"]
        sustained_decay = args["sustained_min_decay"]
        sustained_months = args["sustained_min_months"]

        if peak_wallets < never_thr:
            label = "never_adopted"
        elif (months_to_peak <= flash_peak_within
              and wallets_12_after_peak == wallets_12_after_peak
              and peak_wallets > 0
              and wallets_12_after_peak < flash_remain * peak_wallets):
            label = "flash"
        elif decay >= sustained_decay and months_active >= sustained_months:
            label = "sustained"
        elif decay < 0.5 and months_to_peak >= 0:
            label = "gradual_decline"
        else:
            label = "other"

        # Early features (first 3 months)
        early = g[g["months_since_launch"] <= 2]
        early_ret = early["retention_prev_month"].mean() if len(early) else np.nan
        early_new_share = (
            early["new_wallets"].sum() / early["active_wallets"].sum()
            if early["active_wallets"].sum() > 0 else np.nan
        )
        early_tx_per = early["tx_per_wallet"].mean() if len(early) else np.nan
        early_gas_per_tx = (
            early["gas_used"].sum() / early["tx_count"].sum()
            if early["tx_count"].sum() > 0 else np.nan
        )
        early_whale = early["top10_wallet_share"].mean() if "top10_wallet_share" in early else np.nan

        st = static[static["slug"] == slug].iloc[0]
        rows.append({
            "slug": slug,
            "name": st.get("name"),
            "category": st.get("category"),
            "category_group": st.get("category_group"),
            "parent_protocol": st.get("parent_protocol"),
            "has_token": st.get("has_token"),
            "launch_month": launch,
            "launch_year": launch.year,
            "peak_month": peak_month,
            "peak_wallets": peak_wallets,
            "months_to_peak": months_to_peak,
            "months_to_1k": months_to(1000),
            "months_to_10k": months_to(10000),
            "months_to_half_peak_cum": months_to_half,
            "wallets_m3": wallets_at(3),
            "wallets_m6": wallets_at(6),
            "wallets_m12": wallets_at(12),
            "decay_ratio": decay,
            "wallets_12m_after_peak": wallets_12_after_peak,
            "months_active": months_active,
            "lifecycle_label": label,
            "early_retention": early_ret,
            "early_new_wallet_share": early_new_share,
            "early_tx_per_wallet": early_tx_per,
            "early_gas_per_tx": early_gas_per_tx,
            "early_whale_share": early_whale,
            "n_contracts": st.get("n_contracts"),
            "tvl": st.get("tvl"),
        })

    life = pd.DataFrame(rows)

    # Share of early users already active in another tracked app
    try:
        cross = con.execute("""
            WITH firsts AS (
              SELECT protocol, wallet, first_date FROM wallet_first_seen
            ),
            early_users AS (
              SELECT f.protocol, f.wallet, f.first_date
              FROM firsts f
            ),
            prior AS (
              SELECT e.protocol, e.wallet,
                     MAX(CASE WHEN f2.protocol <> e.protocol
                               AND f2.first_date < e.first_date THEN 1 ELSE 0 END) AS had_prior
              FROM early_users e
              LEFT JOIN firsts f2 ON e.wallet = f2.wallet
              GROUP BY 1, 2
            )
            SELECT protocol AS slug,
                   AVG(had_prior) AS early_prior_app_share
            FROM prior GROUP BY 1
        """).df()
        life = life.merge(cross, on="slug", how="left")
    except Exception as e:
        log.debug(f"  early_prior_app_share skipped: {e}")
        life["early_prior_app_share"] = np.nan

    return life


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(
        description="Build app-contract DApp panel (v2) for Ethereum")
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--end", default="2026-06-30")
    ap.add_argument("--top-n", type=int, default=None,
                    help="limit to top-N DApps by TVL (plus parent siblings)")
    ap.add_argument("--skip-adapters", action="store_true")
    ap.add_argument("--skip-labels", action="store_true")
    ap.add_argument("--no-factory-expansion", action="store_true")
    ap.add_argument("--no-deployer-expansion", action="store_true")
    ap.add_argument("--scan-creation", action="store_true",
                    help="scan S3 for contract creations if v1 DB unavailable")
    ap.add_argument("--max-contracts-per-deployer", type=int, default=3000)
    ap.add_argument("--heavy-tx-threshold", type=int, default=1000,
                    help="wallets with >N txs/month marked heavy")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--verbose", action="store_true")
    # Lifecycle thresholds
    ap.add_argument("--never-adopted-max", type=float, default=500)
    ap.add_argument("--flash-peak-within", type=int, default=6)
    ap.add_argument("--flash-remain-frac", type=float, default=0.20)
    ap.add_argument("--sustained-min-decay", type=float, default=0.50)
    ap.add_argument("--sustained-min-months", type=int, default=24)
    a = ap.parse_args()

    start, end = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)
    setup_logging(a.verbose)
    log.info("=" * 70)
    log.info(f"run started: {' '.join(sys.argv)}")
    log.info(f"  start={start} end={end} top_n={a.top_n} "
             f"skip_adapters={a.skip_adapters} skip_labels={a.skip_labels} "
             f"no_factory={a.no_factory_expansion} no_deployer={a.no_deployer_expansion}")
    log.info(f"  log file: {LOG_FILE.resolve()}")
    t_run = time.time()

    life_args = {
        "never_adopted_max": a.never_adopted_max,
        "flash_peak_within": a.flash_peak_within,
        "flash_remain_frac": a.flash_remain_frac,
        "sustained_min_decay": a.sustained_min_decay,
        "sustained_min_months": a.sustained_min_months,
    }

    try:
        con = connect(a.threads)
        reg = step1_registry(a.top_n)
        discovered = step2_discover(reg, a.skip_adapters, a.skip_labels)
        cmap = step3_expand_clean(
            con, reg, discovered, end,
            a.no_factory_expansion, a.no_deployer_expansion,
            a.max_contracts_per_deployer, a.scan_creation,
        )
        act = step4_activity(con, cmap, start, end, a.heavy_tx_threshold)
        step5_derived(con, reg, cmap, act, start, end, life_args)
    except KeyboardInterrupt:
        log.warning(f"interrupted after {fmt_secs(time.time() - t_run)}; re-run to resume")
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
