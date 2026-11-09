"""Collect a dated historical news corpus for 2019-2025 (the DApp launch windows).

Sources with complete public archives:
  * Ethereum Foundation blog - full RSS archive: real headline, exact date, summary.
  * Cointelegraph - monthly article sitemaps: URL per article, month of publication.
  * The Block - post sitemaps: URL with the publication date in the path.

CoinDesk's sitemap sits behind a bot checkpoint and Decrypt's post sitemaps return 404,
so both are used only for live news (see live_report.py). We do not try to get around
either block.

For the two sitemap sources the headline is rebuilt from the URL slug. Publishers write
slugs from the headline, so the words match, but casing and punctuation are lost. Every
row records `title_source` so these are never presented as verbatim headlines.

Output: data/articles_history.csv
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

import pandas as pd
from lxml import etree

from common import DATA, fetch, slug_to_title

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _locs(xml: str) -> list[tuple[str, str | None]]:
    try:
        root = etree.fromstring(xml.encode("utf-8"))
    except etree.XMLSyntaxError:
        return []
    out = []
    for node in root.findall(".//sm:url", NS) + root.findall(".//sm:sitemap", NS):
        loc = node.findtext("sm:loc", namespaces=NS)
        lastmod = node.findtext("sm:lastmod", namespaces=NS)
        if loc:
            out.append((loc.strip(), lastmod))
    return out


# --------------------------------------------------------------------------- #
# Ethereum Foundation blog (primary source)
# --------------------------------------------------------------------------- #
def fetch_ef_blog() -> pd.DataFrame:
    xml = fetch("https://blog.ethereum.org/feed.xml", use_cache=False)
    if not xml:
        print("  EF blog: fetch failed")
        return pd.DataFrame()
    root = etree.fromstring(xml.encode("utf-8"))
    rows = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate")
        desc = re.sub(r"<[^>]+>", " ", item.findtext("description") or "")
        cats = [c.text for c in item.findall("category") if c.text]
        try:
            dt = parsedate_to_datetime(pub).replace(tzinfo=None)
        except Exception:
            continue
        rows.append({
            "source": "ethereum_foundation",
            "url": link,
            "title": title,
            "title_source": "feed",
            "summary": re.sub(r"\s+", " ", desc).strip()[:600],
            "published": dt.date().isoformat(),
            "date_precision": "day",
            "section": ",".join(cats).lower(),
        })
    print(f"  EF blog: {len(rows)} posts")
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Cointelegraph monthly sitemaps
# --------------------------------------------------------------------------- #
def fetch_cointelegraph(start: str, end: str) -> pd.DataFrame:
    rows = []
    for month in pd.period_range(start, end, freq="M"):
        url = f"https://cointelegraph.com/sitemap/articles/{month.strftime('%Y-%m')}.xml"
        xml = fetch(url)
        if not xml:
            print(f"  cointelegraph {month}: missing")
            continue
        n = 0
        for loc, _ in _locs(xml):
            m = re.match(r"https://cointelegraph\.com/([a-z\-]+)/([^/?#]+)/?$", loc)
            if not m:
                continue
            section, slug = m.groups()
            rows.append({
                "source": "cointelegraph",
                "url": loc,
                "title": slug_to_title(slug),
                "title_source": "url_slug",
                "summary": "",
                # Sitemap file = publication month; day is unknown.
                "published": month.to_timestamp().date().isoformat(),
                "date_precision": "month",
                "section": section,
            })
            n += 1
        print(f"  cointelegraph {month}: {n}")
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# The Block post sitemaps
# --------------------------------------------------------------------------- #
def fetch_theblock(start: str, end: str) -> pd.DataFrame:
    index = fetch("https://www.theblock.co/sitemap.xml", use_cache=False)
    if not index:
        print("  theblock: index failed")
        return pd.DataFrame()
    maps = [loc for loc, _ in _locs(index) if "post_type_post_" in loc]
    lo, hi = pd.Timestamp(start), pd.Timestamp(end) + pd.offsets.MonthEnd(0)
    rows = []
    for sm in maps:
        xml = fetch(sm)
        if not xml:
            continue
        n = 0
        for loc, _ in _locs(xml):
            m = re.match(
                r"https://www\.theblock\.co/(?:news|post|linked|data)/?([a-z\-]*)/(\d{4}-\d{2}-\d{2})-([^/?#]+)",
                loc,
            ) or re.match(r"https://www\.theblock\.co/(post|linked)/(\d+)/([^/?#]+)", loc)
            if not m:
                continue
            section, date_s, slug = m.groups()
            try:
                dt = datetime.strptime(date_s, "%Y-%m-%d")
            except ValueError:
                continue  # newer /post/<id>/ URLs carry no date
            if not (lo <= dt <= hi):
                continue
            rows.append({
                "source": "theblock",
                "url": loc,
                "title": slug_to_title(slug),
                "title_source": "url_slug",
                "summary": "",
                "published": dt.date().isoformat(),
                "date_precision": "day",
                "section": section or "news",
            })
            n += 1
        print(f"  theblock {sm.rsplit('/', 1)[-1]}: {n} in range")
    return pd.DataFrame(rows)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2019-01")
    p.add_argument("--end", default="2025-12")
    p.add_argument("--skip", nargs="*", default=[], choices=["ef", "cointelegraph", "theblock"])
    args = p.parse_args()

    frames = []
    if "ef" not in args.skip:
        frames.append(fetch_ef_blog())
    if "cointelegraph" not in args.skip:
        frames.append(fetch_cointelegraph(args.start, args.end))
    if "theblock" not in args.skip:
        frames.append(fetch_theblock(args.start, args.end))

    df = pd.concat([f for f in frames if len(f)], ignore_index=True)
    df["published"] = pd.to_datetime(df["published"])
    df = df[(df["published"] >= pd.Timestamp(args.start))
            & (df["published"] <= pd.Timestamp(args.end) + pd.offsets.MonthEnd(0))]
    df = df.drop_duplicates("url").sort_values(["published", "source"]).reset_index(drop=True)
    df["month"] = df["published"].dt.to_period("M").astype(str)
    out = DATA / "articles_history.csv"
    df.to_csv(out, index=False)
    print(f"saved {out} ({len(df):,} articles)")
    print(df.groupby("source").size().to_string())


if __name__ == "__main__":
    main()
