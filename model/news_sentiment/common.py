"""Shared paths, HTTP helpers and source metadata for the news-sentiment pipeline."""
from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from typing import Optional

import requests

PKG = Path(__file__).resolve().parent
DATA = PKG / "data"
RAW = DATA / "raw"  # HTTP cache, not in Git
REPORTS = PKG / "reports"  # live dashboards, not in Git
ROOT = PKG.parent.parent
STATIC_CSV = ROOT / "dapp_data_v2" / "dapp_static.csv"
LIFECYCLE_CSV = ROOT / "dapp_data_v2" / "dapp_lifecycle.csv"
OFFCHAIN_BY_K = PKG.parent / "dapp_offchain" / "data" / "dapp_offchain_by_k.csv"

for d in (DATA, RAW, REPORTS):
    d.mkdir(parents=True, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (compatible; dapp-research-news-pipeline/1.0)"

# Source credibility, 0-1. Primary sources (protocol developers) score highest.
# Trade press is ranked on editorial standards and how often stories are first-hand.
SOURCES = {
    "ethereum_foundation": {"name": "Ethereum Foundation Blog", "credibility": 1.00, "primary": True},
    "ethereum_pm": {"name": "Ethereum Protocol Calls (ethereum/pm)", "credibility": 1.00, "primary": True},
    "coindesk": {"name": "CoinDesk", "credibility": 0.85, "primary": False},
    "theblock": {"name": "The Block", "credibility": 0.85, "primary": False},
    "decrypt": {"name": "Decrypt", "credibility": 0.75, "primary": False},
    "cointelegraph": {"name": "Cointelegraph", "credibility": 0.70, "primary": False},
}

_session: Optional[requests.Session] = None


def session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": USER_AGENT})
    return _session


def _cache_path(url: str) -> Path:
    return RAW / (hashlib.sha1(url.encode()).hexdigest() + ".txt")


def fetch(
    url: str,
    *,
    use_cache: bool = True,
    delay: float = 1.0,
    timeout: float = 45,
    retries: int = 3,
) -> Optional[str]:
    """GET a URL politely. Cached responses are reused; failures return None."""
    path = _cache_path(url)
    if use_cache and path.exists():
        return path.read_text(encoding="utf-8")
    for attempt in range(retries):
        try:
            r = session().get(url, timeout=timeout)
            if r.status_code == 200:
                text = r.text
                if use_cache:
                    path.write_text(text, encoding="utf-8")
                time.sleep(delay)
                return text
            if r.status_code in (404, 410):
                return None
            if r.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
        except requests.RequestException:
            pass
        time.sleep(2 * (attempt + 1))
    return None


def slug_to_title(slug: str) -> str:
    """Turn a URL slug into readable words. Used only when a real headline is not available."""
    slug = re.sub(r"-\d{3,}$", "", slug)  # trailing post id
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", slug)  # leading date
    words = slug.replace("_", "-").split("-")
    return " ".join(w for w in words if w).strip().capitalize()


def norm_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9$]+", str(text).lower())
