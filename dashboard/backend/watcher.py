"""Poll CSV mtimes; reload snapshot when files settle after a write."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

try:
    from loader import STORE, file_signature, load_snapshot, watched_files
    from pipeline_status import parse_run_log
except ImportError:
    from .loader import STORE, file_signature, load_snapshot, watched_files
    from .pipeline_status import parse_run_log

log = logging.getLogger("dashboard.watcher")


class FileWatcher:
    def __init__(
        self,
        poll_seconds: float = 5.0,
        stable_seconds: float = 3.0,
        on_reload: Callable[[int], None] | None = None,
    ) -> None:
        self.poll_seconds = poll_seconds
        self.stable_seconds = stable_seconds
        self.on_reload = on_reload
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._pending: dict[str, tuple[tuple[float, int], float]] = {}
        self._last_status: dict[str, Any] = {}
        self._status_lock = threading.Lock()
        self._listeners: list[Callable[[dict], None]] = []
        self._listeners_lock = threading.Lock()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="csv-watcher", daemon=True)
        self._thread.start()
        log.info("file watcher started (poll=%.1fs stable=%.1fs)", self.poll_seconds, self.stable_seconds)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)

    def subscribe(self, cb: Callable[[dict], None]) -> Callable[[], None]:
        with self._listeners_lock:
            self._listeners.append(cb)

        def unsub() -> None:
            with self._listeners_lock:
                if cb in self._listeners:
                    self._listeners.remove(cb)

        return unsub

    def _emit(self, event: dict) -> None:
        with self._listeners_lock:
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(event)
            except Exception:
                log.debug("listener error", exc_info=True)

    def status(self) -> dict[str, Any]:
        with self._status_lock:
            return dict(self._last_status)

    def _loop(self) -> None:
        # Seed known signatures from current snapshot
        try:
            known = dict(STORE.get().file_sigs)
        except Exception:
            known = {}

        while not self._stop.wait(self.poll_seconds):
            try:
                self._tick(known)
            except Exception:
                log.exception("watcher tick failed")

    def _tick(self, known: dict[str, tuple[float, int]]) -> None:
        now = time.time()
        csv_changed = False

        for path in watched_files():
            key = str(path)
            sig = file_signature(path)
            if sig is None:
                continue
            old = known.get(key)
            if old == sig:
                self._pending.pop(key, None)
                continue
            # size/mtime changed
            if key.endswith("run.log"):
                known[key] = sig
                continue  # status handled separately
            pend = self._pending.get(key)
            if pend is None or pend[0] != sig:
                self._pending[key] = (sig, now)
            elif now - pend[1] >= self.stable_seconds:
                # stable long enough
                known[key] = sig
                self._pending.pop(key, None)
                csv_changed = True
                log.info("detected stable change: %s", path.name)

        # Always refresh pipeline status
        status = parse_run_log()
        with self._status_lock:
            prev = self._last_status
            self._last_status = status
        if status != prev:
            self._emit({"type": "pipelineStatus", "status": status, "dataVersion": STORE.version})

        if csv_changed and not self._pending:
            self._reload(known)

    def _reload(self, known: dict[str, tuple[float, int]]) -> None:
        log.info("reloading data snapshot ...")
        try:
            snap = load_snapshot(version=STORE.version + 1)
            STORE.swap(snap)
            known.clear()
            known.update(snap.file_sigs)
            self._emit({"type": "dataVersion", "dataVersion": snap.version, "loadedAt": snap.loaded_at})
            if self.on_reload:
                self.on_reload(snap.version)
            log.info("reload complete → version %s", snap.version)
        except Exception:
            log.exception("reload failed; keeping previous snapshot")


WATCHER = FileWatcher()
