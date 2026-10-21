"""In-memory DuckDB snapshot loader for v1/v2 CSV outputs."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import duckdb

try:
    from dictionary import V1_TABLES, V2_TABLES
except ImportError:
    from .dictionary import V1_TABLES, V2_TABLES

log = logging.getLogger("dashboard.loader")

ROOT = Path(__file__).resolve().parents[2]
V1_DIR = ROOT / "dapp_data"
V2_DIR = ROOT / "dapp_data_v2"

# Large CSVs: load fully but avoid blowing memory on weird types
DATE_HINTS = ("month", "cohort_month", "launch_month", "peak_month", "listed_date",
              "first_deployed", "first_month", "deployed_date")


@dataclass
class Snapshot:
    con: duckdb.DuckDBPyConnection
    version: int
    loaded_at: float
    tables: dict[str, dict[str, Any]] = field(default_factory=dict)
    month_ranges: dict[str, dict[str, str | None]] = field(default_factory=dict)
    categories: list[str] = field(default_factory=list)
    file_sigs: dict[str, tuple[float, int]] = field(default_factory=dict)


class DataStore:
    """Thread-safe holder of the current DuckDB snapshot."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._snap: Snapshot | None = None
        self._version = 0

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    def get(self) -> Snapshot:
        with self._lock:
            if self._snap is None:
                raise RuntimeError("Data not loaded yet")
            return self._snap

    def swap(self, snap: Snapshot) -> None:
        with self._lock:
            old = self._snap
            self._snap = snap
            self._version = snap.version
        if old is not None:
            try:
                old.con.close()
            except Exception:
                pass

    def execute(self, sql: str, params: list | None = None):
        with self._lock:
            snap = self.get()
            if params:
                return snap.con.execute(sql, params)
            return snap.con.execute(sql)


STORE = DataStore()


def _csv_path(dataset: str, table: str) -> Path:
    base = V1_DIR if dataset == "v1" else V2_DIR
    return base / f"{table}.csv"


def watched_files() -> list[Path]:
    files: list[Path] = []
    for t in V1_TABLES:
        p = _csv_path("v1", t)
        if p.exists():
            files.append(p)
    for t in V2_TABLES:
        p = _csv_path("v2", t)
        if p.exists():
            files.append(p)
    for extra in (V2_DIR / "run.log", V1_DIR / "run.log"):
        if extra.exists():
            files.append(extra)
    return files


def file_signature(path: Path) -> tuple[float, int] | None:
    try:
        st = path.stat()
        return (st.st_mtime, st.st_size)
    except OSError:
        return None


def _load_table(con: duckdb.DuckDBPyConnection, dataset: str, table: str) -> dict[str, Any]:
    path = _csv_path(dataset, table)
    name = f"{dataset}_{table}"
    info: dict[str, Any] = {
        "dataset": dataset,
        "table": table,
        "name": name,
        "path": str(path),
        "exists": path.exists(),
        "rows": 0,
        "columns": [],
        "dtypes": {},
        "size_bytes": 0,
        "mtime": None,
    }
    if not path.exists():
        return info

    st = path.stat()
    info["size_bytes"] = st.st_size
    info["mtime"] = st.st_mtime

    # DuckDB read_csv_auto handles types well; cast month-like cols afterwards if present
    con.execute(
        f"CREATE OR REPLACE TABLE {name} AS "
        f"SELECT * FROM read_csv_auto(?, header=true, sample_size=-1, ignore_errors=true)",
        [str(path)],
    )
    cols = con.execute(
        f"SELECT column_name, data_type FROM information_schema.columns "
        f"WHERE table_name = ? ORDER BY ordinal_position",
        [name],
    ).fetchall()
    info["columns"] = [c[0] for c in cols]
    info["dtypes"] = {c[0]: c[1] for c in cols}

    # Normalize date-ish columns to TIMESTAMP where possible
    for col in info["columns"]:
        if col in DATE_HINTS or col.endswith("_date") or col.endswith("_month"):
            dtype = info["dtypes"].get(col, "")
            if "VARCHAR" in dtype.upper() or "DATE" in dtype.upper() or "TIMESTAMP" in dtype.upper():
                try:
                    con.execute(
                        f"ALTER TABLE {name} ALTER COLUMN {col} "
                        f"SET DATA TYPE TIMESTAMP USING TRY_CAST({col} AS TIMESTAMP)"
                    )
                except Exception:
                    pass

    # Refresh dtypes after casts
    cols = con.execute(
        f"SELECT column_name, data_type FROM information_schema.columns "
        f"WHERE table_name = ? ORDER BY ordinal_position",
        [name],
    ).fetchall()
    info["columns"] = [c[0] for c in cols]
    info["dtypes"] = {c[0]: c[1] for c in cols}
    info["rows"] = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    return info


def _month_range(con: duckdb.DuckDBPyConnection, table: str, col: str = "month") -> dict[str, str | None]:
    try:
        cols = {r[0] for r in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
            [table],
        ).fetchall()}
        if col not in cols:
            return {"min": None, "max": None}
        row = con.execute(
            f"SELECT MIN({col})::VARCHAR, MAX({col})::VARCHAR FROM {table} WHERE {col} IS NOT NULL"
        ).fetchone()
        return {"min": row[0], "max": row[1]}
    except Exception:
        return {"min": None, "max": None}


def load_snapshot(version: int | None = None) -> Snapshot:
    t0 = time.time()
    con = duckdb.connect(":memory:")
    con.execute("SET threads TO 4")
    tables: dict[str, dict[str, Any]] = {}
    sigs: dict[str, tuple[float, int]] = {}

    for ds, tlist in (("v1", V1_TABLES), ("v2", V2_TABLES)):
        for table in tlist:
            path = _csv_path(ds, table)
            sig = file_signature(path)
            if sig:
                sigs[str(path)] = sig
            try:
                info = _load_table(con, ds, table)
                tables[f"{ds}_{table}"] = info
                log.info("  loaded %s_%s: %s rows, %s cols", ds, table, f"{info['rows']:,}", len(info["columns"]))
            except Exception as e:
                log.exception("  FAILED loading %s/%s: %s", ds, table, e)
                tables[f"{ds}_{table}"] = {
                    "dataset": ds, "table": table, "name": f"{ds}_{table}",
                    "path": str(path), "exists": path.exists(), "rows": 0,
                    "columns": [], "dtypes": {}, "error": str(e),
                }

    month_ranges = {
        "v1": _month_range(con, "v1_dapp_panel"),
        "v2": _month_range(con, "v2_dapp_panel"),
    }

    categories: list[str] = []
    try:
        cats = con.execute("""
            SELECT DISTINCT category_group FROM (
              SELECT category_group FROM v1_dapp_static WHERE category_group IS NOT NULL
              UNION
              SELECT category_group FROM v2_dapp_static WHERE category_group IS NOT NULL
            ) ORDER BY 1
        """).fetchall()
        categories = [r[0] for r in cats]
    except Exception:
        pass

    ver = version if version is not None else STORE.version + 1
    snap = Snapshot(
        con=con,
        version=ver,
        loaded_at=time.time(),
        tables=tables,
        month_ranges=month_ranges,
        categories=categories,
        file_sigs=sigs,
    )
    log.info("snapshot v%s ready in %.1fs (%d tables)", ver, time.time() - t0, len(tables))
    return snap


def initial_load() -> Snapshot:
    log.info("Initial data load from %s and %s", V1_DIR, V2_DIR)
    snap = load_snapshot(version=1)
    STORE.swap(snap)
    return snap
