"""FastAPI backend for the DApp v1 vs v2 dashboard."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

try:
    from dictionary import (
        COLUMN_DESCRIPTIONS,
        INTERNAL_TABLES,
        METHODOLOGY,
        RELATIONSHIPS,
        TABLE_INFO,
        V1_TABLES,
        V2_TABLES,
        describe_column,
    )
    from loader import STORE, initial_load
    from pipeline_status import parse_run_log
    from watcher import WATCHER
except ImportError:
    from .dictionary import (
        COLUMN_DESCRIPTIONS,
        INTERNAL_TABLES,
        METHODOLOGY,
        RELATIONSHIPS,
        TABLE_INFO,
        V1_TABLES,
        V2_TABLES,
        describe_column,
    )
    from .loader import STORE, initial_load
    from .pipeline_status import parse_run_log
    from .watcher import WATCHER

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("dashboard")

ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"

IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SAFE_TABLE = re.compile(r"^v[12]_[a-z_]+$")

METRICS = [
    "active_wallets", "new_wallets", "tx_count", "gas_used", "fees_eth", "eth_value",
    "active_wallets_ex_heavy", "tx_count_ex_heavy", "gas_used_ex_heavy",
]


def _ok_ident(name: str) -> str:
    if not IDENT.match(name):
        raise HTTPException(400, f"Invalid identifier: {name}")
    return name


def _table(ds: str, name: str) -> str:
    if ds not in ("v1", "v2"):
        raise HTTPException(400, "dataset must be v1 or v2")
    tables = V1_TABLES if ds == "v1" else V2_TABLES
    if name not in tables:
        raise HTTPException(404, f"Unknown table {name} for {ds}")
    return f"{ds}_{name}"


def _df(sql: str, params: list | None = None) -> list[dict]:
    rel = STORE.execute(sql, params)
    cols = [d[0] for d in rel.description]
    rows = rel.fetchall()
    out = []
    for r in rows:
        d = {}
        for c, v in zip(cols, r):
            if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
                d[c] = None
            elif hasattr(v, "isoformat"):
                d[c] = v.isoformat()
            else:
                # Ensure JSON-safe primitives (DuckDB may return date-like objects)
                d[c] = v if isinstance(v, (str, int, float, bool)) else str(v)
        out.append(d)
    return out


def _one(sql: str, params: list | None = None) -> dict | None:
    rows = _df(sql, params)
    return rows[0] if rows else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    initial_load()
    WATCHER.start()
    # seed pipeline status
    WATCHER._last_status = parse_run_log()
    yield
    WATCHER.stop()


app = FastAPI(title="DApp Dataset Dashboard", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── meta / schema ──────────────────────────────────────────────────────────

@app.get("/api/meta")
def meta():
    snap = STORE.get()
    tables = []
    for k, info in snap.tables.items():
        tables.append({
            "key": k,
            "dataset": info.get("dataset"),
            "table": info.get("table"),
            "rows": info.get("rows", 0),
            "columns": info.get("columns", []),
            "size_bytes": info.get("size_bytes", 0),
            "exists": info.get("exists", False),
            "error": info.get("error"),
        })
    return {
        "dataVersion": snap.version,
        "loadedAt": snap.loaded_at,
        "monthRanges": snap.month_ranges,
        "categories": snap.categories,
        "metrics": METRICS,
        "tables": tables,
        "methodology": METHODOLOGY,
        "pipeline": WATCHER.status() or parse_run_log(),
    }


@app.get("/api/schema")
def schema(
    dataset: str | None = None,
    table: str | None = None,
    profile: bool = Query(False),
):
    snap = STORE.get()
    result = []
    for key, info in snap.tables.items():
        ds = info["dataset"]
        tname = info["table"]
        if dataset and ds != dataset:
            continue
        if table and tname != table:
            continue
        tinfo = TABLE_INFO.get(ds, {}).get(tname, {})
        cols_out = []
        nrows = info.get("rows", 0)
        do_profile = profile and (table is not None or nrows < 50_000)
        for col in info.get("columns", []):
            entry: dict[str, Any] = {
                "name": col,
                "dtype": info["dtypes"].get(col),
                "description": describe_column(col),
            }
            if do_profile:
                entry.update(_column_profile(key, col, info["dtypes"].get(col, ""), rows=nrows))
            cols_out.append(entry)
        result.append({
            "dataset": ds,
            "table": tname,
            "description": tinfo.get("description", ""),
            "grain": tinfo.get("grain", ""),
            "keys": tinfo.get("keys", []),
            "rows": info.get("rows", 0),
            "columns": cols_out,
        })
    return {
        "tables": result,
        "relationships": RELATIONSHIPS,
        "internalTables": INTERNAL_TABLES,
        "columnDescriptions": COLUMN_DESCRIPTIONS,
        "methodology": METHODOLOGY,
    }


def _column_profile(table: str, col: str, dtype: str, rows: int = 0) -> dict:
    try:
        # Skip expensive DISTINCT on very large tables
        heavy = rows > 100_000
        if heavy:
            row = STORE.execute(
                f"SELECT COUNT(*) AS n, COUNT({col}) AS non_null FROM {table}"
            ).fetchone()
            n, non_null = row
            nunique = None
        else:
            row = STORE.execute(
                f"""SELECT
                    COUNT(*) AS n,
                    COUNT({col}) AS non_null,
                    COUNT(DISTINCT {col}) AS nunique
                FROM {table}"""
            ).fetchone()
            n, non_null, nunique = row
        null_pct = round(100 * (1 - non_null / n), 2) if n else 0
        out: dict[str, Any] = {"null_pct": null_pct, "nunique": nunique}
        dtype_u = (dtype or "").upper()
        if any(x in dtype_u for x in ("INT", "DOUBLE", "FLOAT", "DECIMAL", "HUGEINT", "BIGINT")):
            stats = STORE.execute(
                f"SELECT MIN({col}), MAX({col}), AVG(TRY_CAST({col} AS DOUBLE)) FROM {table}"
            ).fetchone()
            out["min"] = stats[0]
            out["max"] = stats[1]
            out["mean"] = float(stats[2]) if stats[2] is not None else None
        elif "TIMESTAMP" in dtype_u or "DATE" in dtype_u:
            stats = STORE.execute(
                f"SELECT MIN({col})::VARCHAR, MAX({col})::VARCHAR FROM {table}"
            ).fetchone()
            out["min"] = stats[0]
            out["max"] = stats[1]
        else:
            samples = STORE.execute(
                f"SELECT DISTINCT CAST({col} AS VARCHAR) FROM {table} "
                f"WHERE {col} IS NOT NULL LIMIT 5"
            ).fetchall()
            out["samples"] = [s[0] for s in samples]
        return out
    except Exception as e:
        return {"error": str(e)[:120]}


# ── table browser ──────────────────────────────────────────────────────────

@app.get("/api/table/{dataset}/{name}")
def table_page(
    dataset: str,
    name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    sort: str | None = None,
    order: str = "asc",
    search: str | None = None,
    filter_col: str | None = None,
    filter_val: str | None = None,
):
    t = _table(dataset, name)
    snap = STORE.get()
    info = snap.tables.get(t)
    if not info or not info.get("exists"):
        raise HTTPException(404, f"Table {t} not loaded")
    cols = info["columns"]
    where = []
    params: list[Any] = []
    if filter_col and filter_val is not None:
        fc = _ok_ident(filter_col)
        if fc not in cols:
            raise HTTPException(400, f"Unknown column {fc}")
        where.append(f"CAST({fc} AS VARCHAR) ILIKE ?")
        params.append(f"%{filter_val}%")
    if search:
        # search across string-ish columns (limit to 8)
        ors = []
        for c in cols[:12]:
            ors.append(f"CAST({c} AS VARCHAR) ILIKE ?")
            params.append(f"%{search}%")
        if ors:
            where.append("(" + " OR ".join(ors) + ")")
    wh = ("WHERE " + " AND ".join(where)) if where else ""
    total = STORE.execute(f"SELECT COUNT(*) FROM {t} {wh}", params).fetchone()[0]
    order_sql = ""
    if sort:
        sc = _ok_ident(sort)
        if sc not in cols:
            raise HTTPException(400, f"Unknown sort column {sc}")
        direction = "DESC" if order.lower() == "desc" else "ASC"
        order_sql = f"ORDER BY {sc} {direction} NULLS LAST"
    offset = (page - 1) * page_size
    rows = _df(
        f"SELECT * FROM {t} {wh} {order_sql} LIMIT ? OFFSET ?",
        params + [page_size, offset],
    )
    return {
        "dataset": dataset,
        "table": name,
        "columns": cols,
        "dtypes": info.get("dtypes", {}),
        "descriptions": {c: describe_column(c) for c in cols},
        "page": page,
        "page_size": page_size,
        "total": total,
        "rows": rows,
    }


# ── dapps list / detail ────────────────────────────────────────────────────

@app.get("/api/dapps")
def dapps(
    q: str | None = None,
    category: str | None = None,
    dataset: str = "both",
    limit: int = Query(200, ge=1, le=2000),
):
    # Union of static tables
    sql = """
    WITH all_dapps AS (
      SELECT slug, name, category, category_group, tvl, n_contracts, 'v1' AS src
      FROM v1_dapp_static
      UNION ALL
      SELECT slug, name, category, category_group, tvl, n_contracts, 'v2' AS src
      FROM v2_dapp_static
    ),
    agg AS (
      SELECT slug,
             ANY_VALUE(name) AS name,
             ANY_VALUE(category) AS category,
             ANY_VALUE(category_group) AS category_group,
             MAX(tvl) AS tvl,
             MAX(n_contracts) AS n_contracts,
             BOOL_OR(src = 'v1') AS in_v1,
             BOOL_OR(src = 'v2') AS in_v2
      FROM all_dapps
      GROUP BY slug
    )
    SELECT * FROM agg WHERE 1=1
    """
    params: list[Any] = []
    if q:
        sql += " AND (slug ILIKE ? OR name ILIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if category:
        sql += " AND category_group = ?"
        params.append(category)
    if dataset == "v1":
        sql += " AND in_v1"
    elif dataset == "v2":
        sql += " AND in_v2"
    elif dataset == "both":
        pass
    elif dataset == "overlap":
        sql += " AND in_v1 AND in_v2"
    elif dataset == "v1_only":
        sql += " AND in_v1 AND NOT in_v2"
    elif dataset == "v2_only":
        sql += " AND in_v2 AND NOT in_v1"
    sql += " ORDER BY tvl DESC NULLS LAST LIMIT ?"
    params.append(limit)
    return {"dapps": _df(sql, params)}


@app.get("/api/dapp/{slug}")
def dapp_detail(slug: str):
    v1_static = _one("SELECT * FROM v1_dapp_static WHERE slug = ?", [slug])
    v2_static = _one("SELECT * FROM v2_dapp_static WHERE slug = ?", [slug])
    if not v1_static and not v2_static:
        raise HTTPException(404, f"DApp '{slug}' not found")

    v1_series = _df(
        "SELECT month, active_wallets, new_wallets, tx_count, gas_used, fees_eth, eth_value, "
        "cum_wallets, wallet_growth_mom FROM v1_dapp_panel WHERE slug = ? ORDER BY month",
        [slug],
    ) if v1_static else []

    v2_cols = [
        "month", "active_wallets", "new_wallets", "tx_count", "gas_used", "fees_eth", "eth_value",
        "cum_wallets", "wallet_growth_mom", "tx_per_wallet", "returning_wallets",
        "retention_prev_month", "top10_wallet_share", "avg_n_protocols_in_tx",
        "active_wallets_ex_heavy", "tx_count_ex_heavy", "gas_used_ex_heavy",
        "share_of_category_active_wallets", "share_of_ecosystem_active_wallets",
        "months_since_launch",
    ]
    # only select columns that exist
    snap = STORE.get()
    available = set(snap.tables.get("v2_dapp_panel", {}).get("columns", []))
    sel = [c for c in v2_cols if c in available]
    v2_series = _df(
        f"SELECT {', '.join(sel)} FROM v2_dapp_panel WHERE slug = ? ORDER BY month",
        [slug],
    ) if v2_static else []

    lifecycle = None
    if snap.tables.get("v2_dapp_lifecycle", {}).get("exists"):
        lifecycle = _one("SELECT * FROM v2_dapp_lifecycle WHERE slug = ?", [slug])

    cohorts = []
    if snap.tables.get("v2_cohort_retention", {}).get("exists"):
        cohorts = _df(
            "SELECT cohort_month, months_since, retained, cohort_size, retention_rate "
            "FROM v2_cohort_retention WHERE protocol = ? ORDER BY cohort_month, months_since",
            [slug],
        )

    contracts_v1 = _df(
        "SELECT source, COUNT(*) AS n FROM v1_contract_map WHERE protocol = ? GROUP BY 1",
        [slug],
    ) if v1_static else []

    contracts_v2 = []
    if v2_static and snap.tables.get("v2_app_contracts", {}).get("exists"):
        contracts_v2 = _df(
            "SELECT role, source, confidence, COUNT(*) AS n, "
            "SUM(CASE WHEN is_token THEN 1 ELSE 0 END) AS n_tokens "
            "FROM v2_app_contracts WHERE protocol = ? "
            "GROUP BY 1, 2, 3 ORDER BY n DESC",
            [slug],
        )

    return {
        "slug": slug,
        "v1": {"static": v1_static, "series": v1_series, "contracts_by_source": contracts_v1},
        "v2": {
            "static": v2_static,
            "series": v2_series,
            "lifecycle": lifecycle,
            "cohorts": cohorts,
            "contracts_breakdown": contracts_v2,
        },
    }


# ── compare ────────────────────────────────────────────────────────────────

@app.get("/api/compare/overlap")
def compare_overlap():
    row = _one("""
        WITH v1s AS (SELECT DISTINCT slug FROM v1_dapp_static),
             v2s AS (SELECT DISTINCT slug FROM v2_dapp_static)
        SELECT
          (SELECT COUNT(*) FROM v1s) AS v1_count,
          (SELECT COUNT(*) FROM v2s) AS v2_count,
          (SELECT COUNT(*) FROM v1s JOIN v2s USING (slug)) AS both,
          (SELECT COUNT(*) FROM v1s ANTI JOIN v2s USING (slug)) AS v1_only,
          (SELECT COUNT(*) FROM v2s ANTI JOIN v1s USING (slug)) AS v2_only
    """)
    return row or {}


@app.get("/api/compare/ecosystem")
def compare_ecosystem(
    metric: str = "active_wallets",
    start: str | None = None,
    end: str | None = None,
):
    metric = _ok_ident(metric)
    # v1 always has core metrics; v2 may have more
    clauses_v1 = []
    clauses_v2 = []
    params_v1: list[Any] = []
    params_v2: list[Any] = []
    if start:
        clauses_v1.append("month >= ?")
        clauses_v2.append("month >= ?")
        params_v1.append(start)
        params_v2.append(start)
    if end:
        clauses_v1.append("month <= ?")
        clauses_v2.append("month <= ?")
        params_v1.append(end)
        params_v2.append(end)
    wh1 = ("WHERE " + " AND ".join(clauses_v1)) if clauses_v1 else ""
    wh2 = ("WHERE " + " AND ".join(clauses_v2)) if clauses_v2 else ""

    # *_ex_heavy metrics exist only in v2
    snap = STORE.get()
    v1_cols = set(snap.tables.get("v1_dapp_panel", {}).get("columns", []))
    v2_cols = set(snap.tables.get("v2_dapp_panel", {}).get("columns", []))
    v1 = []
    if metric in v1_cols:
        v1 = _df(
            f"SELECT month, SUM({metric}) AS value, "
            f"COUNT(DISTINCT slug) FILTER (WHERE {metric} > 0) AS active_dapps "
            f"FROM v1_dapp_panel {wh1} GROUP BY month ORDER BY month",
            params_v1,
        )
    v2 = []
    if metric in v2_cols:
        v2 = _df(
            f"SELECT month, SUM({metric}) AS value, "
            f"COUNT(DISTINCT slug) FILTER (WHERE {metric} > 0) AS active_dapps "
            f"FROM v2_dapp_panel {wh2} GROUP BY month ORDER BY month",
            params_v2,
        )
    return {
        "metric": metric, "v1": v1, "v2": v2,
        "unavailable": [d for d, c in (("v1", v1_cols), ("v2", v2_cols)) if metric not in c],
    }


@app.get("/api/compare/scatter")
def compare_scatter(
    metric: str = "active_wallets",
    start: str | None = None,
    end: str | None = None,
):
    metric = _ok_ident(metric)
    snap = STORE.get()
    missing = [d for d in ("v1", "v2")
               if metric not in snap.tables.get(f"{d}_dapp_panel", {}).get("columns", [])]
    if missing:
        return {"metric": metric, "points": [], "unavailable": missing}

    wh_parts = []
    params: list[Any] = []
    # build filtered aggregates
    v1_f = "v1_dapp_panel"
    v2_f = "v2_dapp_panel"
    extra = ""
    if start:
        extra += " AND month >= ?"
        params.append(start)
        params.append(start)  # for both CTEs — handled below carefully
    # Simpler: filter inside CTEs with duplicated params
    params = []
    start_clause = ""
    end_clause = ""
    if start:
        start_clause = " AND month >= ?"
    if end:
        end_clause = " AND month <= ?"

    p: list[Any] = []
    if start:
        p.append(start)
    if end:
        p.append(end)
    if start:
        p.append(start)
    if end:
        p.append(end)

    rows = _df(f"""
        WITH a AS (
          SELECT slug, SUM({metric}) AS v1_val
          FROM v1_dapp_panel WHERE 1=1 {start_clause} {end_clause}
          GROUP BY slug
        ),
        b AS (
          SELECT slug, SUM({metric}) AS v2_val,
                 ANY_VALUE(name) AS name,
                 ANY_VALUE(category_group) AS category_group
          FROM v2_dapp_panel WHERE 1=1 {start_clause} {end_clause}
          GROUP BY slug
        )
        SELECT COALESCE(a.slug, b.slug) AS slug,
               COALESCE(b.name, a.slug) AS name,
               b.category_group,
               COALESCE(a.v1_val, 0) AS v1,
               COALESCE(b.v2_val, 0) AS v2,
               CASE WHEN COALESCE(a.v1_val, 0) > 0
                    THEN COALESCE(b.v2_val, 0) / a.v1_val ELSE NULL END AS ratio
        FROM a FULL OUTER JOIN b USING (slug)
        WHERE COALESCE(a.v1_val, 0) > 0 OR COALESCE(b.v2_val, 0) > 0
        ORDER BY GREATEST(COALESCE(a.v1_val,0), COALESCE(b.v2_val,0)) DESC
    """, p)
    return {"metric": metric, "points": rows}


@app.get("/api/compare/ratio-hist")
def compare_ratio_hist(metric: str = "active_wallets", bins: int = 20):
    scatter = compare_scatter(metric=metric)
    ratios = [p["ratio"] for p in scatter["points"] if p.get("ratio") is not None and p["ratio"] > 0]
    if not ratios:
        return {"bins": [], "metric": metric}
    # log10 bins
    import math as m
    logs = [m.log10(r) for r in ratios]
    lo, hi = min(logs), max(logs)
    if lo == hi:
        return {"bins": [{"x0": 10 ** lo, "x1": 10 ** hi, "count": len(ratios)}], "metric": metric}
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in logs:
        i = min(int((v - lo) / width), bins - 1)
        counts[i] += 1
    out = []
    for i, c in enumerate(counts):
        out.append({"x0": 10 ** (lo + i * width), "x1": 10 ** (lo + (i + 1) * width), "count": c})
    return {"bins": out, "metric": metric, "n": len(ratios),
            "median": sorted(ratios)[len(ratios) // 2],
            "p25": sorted(ratios)[len(ratios) // 4],
            "p75": sorted(ratios)[3 * len(ratios) // 4]}


@app.get("/api/compare/categories")
def compare_categories():
    v1 = _df("""
        SELECT category_group, COUNT(*) AS n_dapps, SUM(tvl) AS tvl
        FROM v1_dapp_static GROUP BY 1 ORDER BY n_dapps DESC
    """)
    v2 = _df("""
        SELECT category_group, COUNT(*) AS n_dapps, SUM(tvl) AS tvl
        FROM v2_dapp_static GROUP BY 1 ORDER BY n_dapps DESC
    """)
    zero = _one("""
        SELECT
          (SELECT AVG(CASE WHEN active_wallets = 0 THEN 1.0 ELSE 0.0 END) FROM v1_dapp_panel) AS v1_zero_share,
          (SELECT AVG(CASE WHEN active_wallets = 0 THEN 1.0 ELSE 0.0 END) FROM v2_dapp_panel) AS v2_zero_share
    """)
    return {"v1": v1, "v2": v2, "zero_activity": zero}


@app.get("/api/compare/disagreements")
def compare_disagreements(metric: str = "active_wallets", limit: int = 30):
    scatter = compare_scatter(metric=metric)
    pts = [p for p in scatter["points"] if p.get("v1", 0) > 0 and p.get("v2", 0) > 0 and p.get("ratio")]
    by_ratio = sorted(pts, key=lambda p: p["ratio"], reverse=True)
    return {
        "highest_v2_ratio": by_ratio[:limit],
        "lowest_v2_ratio": list(reversed(by_ratio[-limit:])),
    }


@app.get("/api/compare/coverage")
def compare_coverage():
    """Months present in each dataset with totals."""
    v1 = _df("""
        SELECT month, SUM(active_wallets) AS active_wallets, SUM(tx_count) AS tx_count,
               COUNT(DISTINCT slug) FILTER (WHERE active_wallets > 0) AS active_dapps
        FROM v1_dapp_panel GROUP BY month ORDER BY month
    """)
    v2 = _df("""
        SELECT month, SUM(active_wallets) AS active_wallets, SUM(tx_count) AS tx_count,
               COUNT(DISTINCT slug) FILTER (WHERE active_wallets > 0) AS active_dapps
        FROM v2_dapp_panel GROUP BY month ORDER BY month
    """)
    return {"v1": v1, "v2": v2}


# ── ecosystem (v2 research tables) ─────────────────────────────────────────

@app.get("/api/ecosystem/category-month")
def ecosystem_category_month(start: str | None = None, end: str | None = None):
    if not STORE.get().tables.get("v2_category_month", {}).get("exists"):
        return {"rows": []}
    wh, params = [], []
    if start:
        wh.append("month >= ?"); params.append(start)
    if end:
        wh.append("month <= ?"); params.append(end)
    w = ("WHERE " + " AND ".join(wh)) if wh else ""
    return {"rows": _df(f"SELECT * FROM v2_category_month {w} ORDER BY month, category_group", params)}


@app.get("/api/ecosystem/concentration")
def ecosystem_concentration(
    scope: str = "ecosystem",
    metric: str = "active_wallets",
    category_group: str | None = None,
):
    if not STORE.get().tables.get("v2_concentration_month", {}).get("exists"):
        return {"rows": []}
    wh = ["scope = ?", "metric = ?"]
    params: list[Any] = [scope, metric]
    if category_group:
        wh.append("category_group = ?")
        params.append(category_group)
    return {"rows": _df(
        f"SELECT * FROM v2_concentration_month WHERE {' AND '.join(wh)} ORDER BY month",
        params,
    )}


@app.get("/api/ecosystem/lifecycle")
def ecosystem_lifecycle():
    if not STORE.get().tables.get("v2_dapp_lifecycle", {}).get("exists"):
        return {"distribution": [], "scatter": []}
    dist = _df("""
        SELECT lifecycle_label, category_group, COUNT(*) AS n
        FROM v2_dapp_lifecycle GROUP BY 1, 2 ORDER BY 1, 2
    """)
    scatter = _df("""
        SELECT slug, name, category_group, lifecycle_label,
               peak_wallets, months_to_peak, decay_ratio,
               early_retention, early_whale_share, early_new_wallet_share,
               early_prior_app_share, launch_year, months_active, tvl
        FROM v2_dapp_lifecycle
        WHERE peak_wallets > 0
    """)
    return {"distribution": dist, "scatter": scatter}


@app.get("/api/ecosystem/top")
def ecosystem_top(
    dataset: str = "v2",
    metric: str = "active_wallets",
    month: str | None = None,
    limit: int = 15,
):
    metric = _ok_ident(metric)
    t = _table(dataset, "dapp_panel")
    cols = STORE.get().tables.get(t, {}).get("columns", [])
    if metric not in cols:
        return {"rows": [], "unavailable": True}
    if month:
        return {"rows": _df(
            f"SELECT slug, name, category_group, {metric} AS value, month "
            f"FROM {t} WHERE month = ? ORDER BY {metric} DESC NULLS LAST LIMIT ?",
            [month, limit],
        )}
    return {"rows": _df(
        f"SELECT slug, ANY_VALUE(name) AS name, ANY_VALUE(category_group) AS category_group, "
        f"SUM({metric}) AS value "
        f"FROM {t} GROUP BY slug ORDER BY value DESC NULLS LAST LIMIT ?",
        [limit],
    )}


# ── variations ─────────────────────────────────────────────────────────────

@app.get("/api/variations/distributions")
def variations_dist(
    dataset: str = "v2",
    metric: str = "active_wallets",
    group_by: str = "category_group",
):
    metric = _ok_ident(metric)
    group_by = _ok_ident(group_by)
    t = _table(dataset, "dapp_panel")
    cols = set(STORE.get().tables.get(t, {}).get("columns", []))
    if metric not in cols or group_by not in cols:
        return {"metric": metric, "group_by": group_by, "rows": [], "unavailable": True}
    rows = _df(f"""
        SELECT {group_by} AS grp,
               COUNT(*) AS n,
               AVG({metric}) AS mean,
               MEDIAN({metric}) AS median,
               MIN({metric}) AS min,
               MAX({metric}) AS max,
               STDDEV_SAMP({metric}) AS std,
               QUANTILE_CONT({metric}, 0.25) AS q25,
               QUANTILE_CONT({metric}, 0.75) AS q75
        FROM {t}
        WHERE {metric} > 0
        GROUP BY 1
        ORDER BY median DESC NULLS LAST
    """)
    return {"metric": metric, "group_by": group_by, "rows": rows}


@app.get("/api/variations/volatility")
def variations_volatility(dataset: str = "v2", metric: str = "active_wallets", limit: int = 40):
    metric = _ok_ident(metric)
    t = _table(dataset, "dapp_panel")
    growth_col = "wallet_growth_mom" if metric == "active_wallets" else None
    if growth_col and growth_col in STORE.get().tables.get(t, {}).get("columns", []):
        rows = _df(f"""
            SELECT slug, ANY_VALUE(name) AS name, ANY_VALUE(category_group) AS category_group,
                   STDDEV_SAMP({growth_col}) AS growth_vol,
                   AVG({metric}) AS avg_metric,
                   COUNT(*) AS n_months
            FROM {t}
            WHERE {growth_col} IS NOT NULL AND ABS({growth_col}) < 10
            GROUP BY slug
            HAVING COUNT(*) >= 6
            ORDER BY growth_vol DESC NULLS LAST
            LIMIT ?
        """, [limit])
        return {"rows": rows, "metric": metric}
    return {"rows": [], "metric": metric}


@app.get("/api/variations/heavy-impact")
def variations_heavy(limit: int = 40):
    cols = set(STORE.get().tables.get("v2_dapp_panel", {}).get("columns", []))
    if "active_wallets_ex_heavy" not in cols:
        return {"rows": []}
    rows = _df("""
        SELECT slug, ANY_VALUE(name) AS name, ANY_VALUE(category_group) AS category_group,
               SUM(active_wallets) AS total,
               SUM(active_wallets_ex_heavy) AS ex_heavy,
               1 - SUM(active_wallets_ex_heavy) / NULLIF(SUM(active_wallets), 0) AS heavy_share
        FROM v2_dapp_panel
        GROUP BY slug
        HAVING SUM(active_wallets) > 1000
        ORDER BY heavy_share DESC NULLS LAST
        LIMIT ?
    """, [limit])
    return {"rows": rows}


@app.get("/api/variations/attribution")
def variations_attribution():
    cols = set(STORE.get().tables.get("v2_dapp_panel", {}).get("columns", []))
    if "avg_n_protocols_in_tx" not in cols:
        return {"monthly": [], "by_dapp": []}
    monthly = _df("""
        SELECT month,
               AVG(avg_n_protocols_in_tx) AS avg_n,
               MEDIAN(avg_n_protocols_in_tx) AS median_n
        FROM v2_dapp_panel
        WHERE avg_n_protocols_in_tx IS NOT NULL AND active_wallets > 0
        GROUP BY month ORDER BY month
    """)
    by_dapp = _df("""
        SELECT slug, ANY_VALUE(name) AS name, ANY_VALUE(category_group) AS category_group,
               AVG(avg_n_protocols_in_tx) AS avg_n,
               AVG(top10_wallet_share) AS avg_whale
        FROM v2_dapp_panel
        WHERE active_wallets > 100
        GROUP BY slug
        ORDER BY avg_n DESC NULLS LAST
        LIMIT 40
    """)
    return {"monthly": monthly, "by_dapp": by_dapp}


# ── SSE ────────────────────────────────────────────────────────────────────

@app.get("/api/events")
async def events():
    queue: asyncio.Queue = asyncio.Queue(maxsize=32)
    loop = asyncio.get_event_loop()

    def on_event(ev: dict) -> None:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, ev)
        except Exception:
            pass

    unsub = WATCHER.subscribe(on_event)

    async def gen() -> AsyncIterator[str]:
        try:
            # initial hello
            yield f"data: {json.dumps({'type': 'hello', 'dataVersion': STORE.version, 'status': WATCHER.status()})}\n\n"
            while True:
                try:
                    ev = await asyncio.wait_for(queue.get(), timeout=20)
                    yield f"data: {json.dumps(ev, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'ping', 'dataVersion': STORE.version})}\n\n"
        finally:
            unsub()

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


@app.get("/api/pipeline")
def pipeline():
    return WATCHER.status() or parse_run_log()


# ── static frontend (production build) ─────────────────────────────────────

@app.get("/")
def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {
        "message": "DApp Dataset Dashboard API",
        "ui": "Run the Vite frontend (npm run dev) or build frontend/dist",
        "meta": "/api/meta",
        "docs": "/docs",
    }


if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{full_path:path}")
def spa(full_path: str = ""):
    if full_path.startswith("api"):
        raise HTTPException(404)
    index = STATIC_DIR / "index.html"
    candidate = STATIC_DIR / full_path
    if full_path and candidate.is_file():
        return FileResponse(candidate)
    if index.exists():
        return FileResponse(index)
    raise HTTPException(404, "Frontend not built. Use Vite on :5173 or run npm run build.")
