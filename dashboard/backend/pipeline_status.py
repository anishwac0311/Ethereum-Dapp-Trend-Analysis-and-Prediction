"""Parse dapp_data_v2/run.log for live pipeline progress."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from loader import V2_DIR, V1_DIR
except ImportError:
    from .loader import V2_DIR, V1_DIR

RUN_STARTED = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\w+\s+run started:\s+(?P<cmd>.+)$"
)
RUN_FINISHED = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\w+\s+run finished in (?P<dur>.+)$"
)
STEP = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\w+\s+\[(?P<step>\d+)/(?P<total>\d+)\]\s+(?P<msg>.+)$"
)
MONTH_PROGRESS = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\w+\s+"
    r"\[(?P<i>\d+)/(?P<n>\d+)\]\s+(?P<month>\d{4}-\d{2}):\s+"
    r"(?P<rows>[\d,]+)\s+wallet rows,\s+(?P<dapps>\d+)\s+DApps in (?P<dur>\S+)"
)
MONTHS_CACHED = re.compile(
    r"(?P<total>\d+) months,\s+(?P<cached>\d+) cached,\s+(?P<todo>\d+) to go"
)
ARGS = re.compile(r"start=(?P<start>\S+)\s+end=(?P<end>\S+)")
FAILED = re.compile(r"FAILED|run crashed|run stopped")


def _parse_ts(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _tail_lines(path: Path, max_bytes: int = 512_000) -> list[str]:
    if not path.exists():
        return []
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
                f.readline()  # discard partial line
            data = f.read().decode("utf-8", errors="replace")
        return data.splitlines()
    except OSError:
        return []


def parse_run_log(path: Path | None = None) -> dict[str, Any]:
    path = path or (V2_DIR / "run.log")
    lines = _tail_lines(path)
    if not lines and (V1_DIR / "run.log").exists():
        # fallback empty v2 — still return idle
        pass

    status: dict[str, Any] = {
        "running": False,
        "finished": False,
        "failed": False,
        "log_path": str(path),
        "log_exists": path.exists(),
        "started_at": None,
        "finished_at": None,
        "command": None,
        "start": None,
        "end": None,
        "step": None,
        "step_total": None,
        "step_message": None,
        "month": None,
        "month_i": None,
        "month_n": None,
        "month_rows": None,
        "month_dapps": None,
        "month_duration": None,
        "months_total": None,
        "months_cached": None,
        "months_todo": None,
        "duration": None,
        "eta_seconds": None,
        "last_line": lines[-1] if lines else None,
        "recent_months": [],
    }

    # Find last "run started" and parse from there
    start_idx = None
    for i, line in enumerate(lines):
        if RUN_STARTED.search(line):
            start_idx = i

    if start_idx is None:
        status["running"] = False
        return status

    segment = lines[start_idx:]
    m = RUN_STARTED.search(segment[0])
    if m:
        status["started_at"] = m.group("ts")
        status["command"] = m.group("cmd").strip()

    recent_months: list[dict[str, Any]] = []
    month_durs: list[float] = []

    for line in segment:
        if ARGS.search(line) and status["start"] is None:
            am = ARGS.search(line)
            if am:
                status["start"] = am.group("start")
                status["end"] = am.group("end")

        sm = STEP.search(line)
        if sm and "wallet rows" not in line:
            status["step"] = int(sm.group("step"))
            status["step_total"] = int(sm.group("total"))
            status["step_message"] = sm.group("msg")[:200]

        cm = MONTHS_CACHED.search(line)
        if cm:
            status["months_total"] = int(cm.group("total"))
            status["months_cached"] = int(cm.group("cached"))
            status["months_todo"] = int(cm.group("todo"))

        mm = MONTH_PROGRESS.search(line)
        if mm:
            status["month"] = mm.group("month")
            status["month_i"] = int(mm.group("i"))
            status["month_n"] = int(mm.group("n"))
            status["month_rows"] = int(mm.group("rows").replace(",", ""))
            status["month_dapps"] = int(mm.group("dapps"))
            status["month_duration"] = mm.group("dur")
            recent_months.append({
                "month": mm.group("month"),
                "i": int(mm.group("i")),
                "n": int(mm.group("n")),
                "rows": int(mm.group("rows").replace(",", "")),
                "dapps": int(mm.group("dapps")),
                "duration": mm.group("dur"),
                "ts": mm.group("ts"),
            })
            # rough duration parse for ETA
            dur = mm.group("dur")
            secs = _dur_to_secs(dur)
            if secs is not None:
                month_durs.append(secs)

        if RUN_FINISHED.search(line):
            fm = RUN_FINISHED.search(line)
            status["finished"] = True
            status["finished_at"] = fm.group("ts") if fm else None
            status["duration"] = fm.group("dur") if fm else None
            status["running"] = False

        if FAILED.search(line) and "re-run" not in line.lower():
            # only mark failed if finished wasn't set after
            if not status["finished"]:
                status["failed"] = True

    status["recent_months"] = recent_months[-12:]

    if not status["finished"] and not status["failed"]:
        status["running"] = True

    # ETA from average month duration × remaining
    if status["running"] and month_durs and status["month_i"] and status["month_n"]:
        remaining = status["month_n"] - status["month_i"]
        avg = sum(month_durs[-5:]) / len(month_durs[-5:])
        status["eta_seconds"] = int(avg * remaining)

    return status


def _dur_to_secs(dur: str) -> float | None:
    # formats: 7m47s, 1h51m, 18m27s, 10m00s
    try:
        h = m = s = 0
        if "h" in dur:
            parts = dur.split("h", 1)
            h = int(parts[0])
            dur = parts[1]
        if "m" in dur:
            parts = dur.split("m", 1)
            m = int(parts[0])
            dur = parts[1]
        if dur.endswith("s"):
            s = int(dur[:-1] or 0)
        elif dur.isdigit():
            s = int(dur)
        return h * 3600 + m * 60 + s
    except Exception:
        return None
