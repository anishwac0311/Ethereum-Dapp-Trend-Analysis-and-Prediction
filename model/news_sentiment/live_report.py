"""Live Ethereum News Sentiment & Market Impact report.

Fetches the latest articles (CoinDesk, The Block, Decrypt, Cointelegraph, Ethereum
Foundation blog) and upcoming protocol calls (ethereum/pm), scores and ranks them,
compares news sentiment with ETH price momentum, and writes:

  reports/<timestamp>/report.json     everything below, machine-readable
  reports/<timestamp>/articles.csv    one row per article with its analysis
  reports/<timestamp>/dashboard.html  self-contained dashboard (no external assets)
  reports/latest.html                 copy of the newest dashboard
  data/live_archive.csv               every scored live article, appended run after run

The archive adds to the historical corpus over time, so future model retrains can use
fully-dated real headlines instead of slug-derived ones.

Usage:
  python live_report.py                 # last 7 days, rule-based scoring
  python live_report.py --days 3
  python live_report.py --llm           # Claude scores the articles (needs credentials)
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import numpy as np
import pandas as pd
from lxml import etree

from common import DATA, REPORTS, SOURCES, fetch
from score import WEIGHTS, rank_score, score_frame

FEEDS = [
    ("coindesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("theblock", "https://www.theblock.co/rss.xml"),
    ("decrypt", "https://decrypt.co/feed"),
    ("cointelegraph", "https://cointelegraph.com/rss/tag/ethereum"),
    ("cointelegraph", "https://cointelegraph.com/rss"),
    ("ethereum_foundation", "https://blog.ethereum.org/feed.xml"),
]
PM_ISSUES = "https://api.github.com/repos/ethereum/pm/issues?state=open&per_page=60"
COINGECKO = "https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=30"


# --------------------------------------------------------------------------- #
# Collection
# --------------------------------------------------------------------------- #
def _strip(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def fetch_feed(source: str, url: str) -> list[dict]:
    xml = fetch(url, use_cache=False, delay=0.5)
    if not xml:
        print(f"  {source}: feed unavailable ({url})")
        return []
    try:
        root = etree.fromstring(xml.encode("utf-8"), parser=etree.XMLParser(recover=True))
    except Exception:
        return []
    out = []
    for item in root.iter("item"):
        title = _strip(item.findtext("title") or "")
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate")
        if not (title and link and pub):
            continue
        try:
            dt = parsedate_to_datetime(pub).astimezone(timezone.utc)
        except Exception:
            continue
        cats = [c.text for c in item.findall("category") if c.text]
        out.append({
            "source": source,
            "source_name": SOURCES[source]["name"],
            "url": link.split("?")[0],
            "title": title,
            "title_source": "feed",
            "summary": _strip(item.findtext("description") or "")[:800],
            "published": dt,
            "date_precision": "day",
            "section": ",".join(cats).lower(),
        })
    print(f"  {source}: {len(out)} items")
    return out


_MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"


def fetch_protocol_calls() -> list[dict]:
    """Open issues in ethereum/pm: the agenda for All Core Devs calls and breakouts."""
    txt = fetch(PM_ISSUES, use_cache=False, delay=0.5)
    if not txt:
        return []
    events = []
    for issue in json.loads(txt):
        if "pull_request" in issue:
            continue
        title = issue.get("title", "")
        m = re.search(rf"\b({_MONTHS})[a-z]*\.?\s+(\d{{1,2}}),?\s+(\d{{4}})", title, re.I)
        when = None
        if m:
            try:
                when = datetime.strptime(f"{m.group(1)[:3]} {m.group(2)} {m.group(3)}", "%b %d %Y").date()
            except ValueError:
                when = None
        events.append({
            "title": title,
            "url": issue.get("html_url"),
            "date": when.isoformat() if when else None,
            "source": "ethereum_pm",
            "kind": "protocol_call",
            "is_core": bool(re.search(r"\b(all core devs|acd[ect]?|consensus|execution)\b", title, re.I)),
        })
    return events


def fetch_prices() -> pd.Series | None:
    txt = fetch(COINGECKO, use_cache=False, delay=0.2)
    if not txt:
        return None
    try:
        p = json.loads(txt)["prices"]
    except (KeyError, ValueError):
        return None
    s = pd.Series([x[1] for x in p], index=pd.to_datetime([x[0] for x in p], unit="ms", utc=True))
    return s.sort_index()


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #
def price_context(df: pd.DataFrame, px: pd.Series | None, now: datetime) -> pd.DataFrame:
    """ETH move since each article was published, and a priced-in note."""
    df = df.copy()
    df["eth_move_since_pub"] = np.nan
    df["priced_in_note"] = ""
    if px is None or px.empty:
        df["priced_in_note"] = "No price data available."
        return df
    last = px.iloc[-1]
    for i, r in df.iterrows():
        t = pd.Timestamp(r["published"])
        before = px[px.index <= t]
        if before.empty:
            continue
        move = last / before.iloc[-1] - 1
        df.at[i, "eth_move_since_pub"] = move
        age_h = (now - t.to_pydatetime()).total_seconds() / 3600
        direction = 1 if r["sentiment"] == "bullish" else -1 if r["sentiment"] == "bearish" else 0
        notes = []
        if direction and abs(move) >= 0.03:
            if np.sign(move) == direction:
                notes.append(f"ETH has already moved {move:+.1%} in the headline's direction since publication; "
                             "part of this may be priced in.")
            else:
                notes.append(f"ETH has moved {move:+.1%} against the headline since publication; "
                             "the market has not followed this story (other forces may dominate).")
        if r["time_horizon"] == "short" and age_h > 48:
            notes.append("Short-term story older than 48h; its immediate effect has likely been absorbed.")
        if not notes:
            notes.append(f"ETH {move:+.1%} since publication; no clear sign it is priced in yet." if direction
                         else f"ETH {move:+.1%} since publication.")
        df.at[i, "priced_in_note"] = " ".join(notes)
    return df


def momentum(px: pd.Series | None) -> dict:
    if px is None or px.empty:
        return {}
    last_t, last = px.index[-1], px.iloc[-1]

    def ret(h: float):
        prev = px[px.index <= last_t - timedelta(hours=h)]
        return float(last / prev.iloc[-1] - 1) if len(prev) else None

    r = {"price": float(last), "as_of": last_t.isoformat(), "ret_24h": ret(24),
         "ret_7d": ret(24 * 7), "ret_30d": ret(24 * 29.5)}
    daily = px.resample("1D").last().pct_change().dropna()
    r["vol_30d_ann"] = float(daily.std() * np.sqrt(365)) if len(daily) > 5 else None
    r7 = r["ret_7d"] or 0
    r["state"] = "uptrend" if r7 > 0.05 else "downtrend" if r7 < -0.05 else "range-bound"
    return r


def overall(leads: pd.DataFrame) -> dict:
    rel = leads[leads["eth_relevance"] >= 0.4]
    if rel.empty:
        rel = leads
    w = rel["market_impact"] * rel["eth_relevance"] * rel["confidence"] / 100
    score = float(np.average(rel["sentiment_score"], weights=w)) if w.sum() else 0.0
    shares = rel["sentiment"].value_counts(normalize=True).reindex(["bullish", "neutral", "bearish"]).fillna(0)
    bull, bear = float(shares["bullish"]), float(shares["bearish"])
    if score >= 15 and bull > bear + 0.1:
        env = "bullish"
    elif score <= -15 and bear > bull + 0.1:
        env = "bearish"
    else:
        env = "mixed"
    return {
        "score": round(score, 1), "environment": env,
        "pct_bullish": round(100 * bull, 1), "pct_neutral": round(100 * float(shares["neutral"]), 1),
        "pct_bearish": round(100 * bear, 1), "n_events": int(len(rel)),
        "n_eth_specific": int((rel["scope"] == "eth_specific").sum()),
        "n_market_wide": int(rel["scope"].isin(["market_wide", "macro"]).sum()),
        "fact_share": round(float((rel["content_type"] == "fact").mean()), 2),
    }


def template_assessment(ov: dict, ranked: pd.DataFrame, mom: dict, events: list[dict]) -> dict:
    leads = ranked[ranked["is_cluster_lead"]]
    bull = leads[leads["sentiment"] == "bullish"].head(1)
    bear = leads[leads["sentiment"] == "bearish"].head(1)
    future = leads[leads["future_event"]].head(1)
    core = [e for e in events if e.get("is_core") and e.get("date")]
    if len(future):
        cat = f"{future.iloc[0]['title']} ({future.iloc[0]['source_name']})"
    elif core:
        cat = f"{core[0]['title']} (ethereum/pm)"
    else:
        cat = "No dated catalyst found in this news window."
    m7 = mom.get("ret_7d")
    mtxt = (f"ETH is {m7:+.1%} over 7 days ({mom.get('state')})." if m7 is not None else "No price data.")
    agree = ((ov["score"] > 15 and (m7 or 0) > 0) or (ov["score"] < -15 and (m7 or 0) < 0))
    return {
        "outlook": (f"News flow reads {ov['environment']} (score {ov['score']:+.0f}/100 across "
                    f"{ov['n_events']} distinct events; {ov['pct_bullish']:.0f}% bullish, "
                    f"{ov['pct_bearish']:.0f}% bearish). This describes the tone of coverage, not "
                    f"where ETH will trade."),
        "top_bullish": bull.iloc[0]["title"] if len(bull) else "No material bullish story in this window.",
        "top_bearish": bear.iloc[0]["title"] if len(bear) else "No material bearish story in this window.",
        "top_catalyst": cat,
        "watchlist": leads.head(3)["title"].tolist(),
        "momentum_note": mtxt + (" Price action agrees with news tone." if agree else
                                 " Price action and news tone are not aligned, so treat the news signal with caution."),
    }


def run(days: int, use_llm: bool, max_llm: int) -> dict:
    now = datetime.now(timezone.utc)
    print("== fetching live news ==")
    rows = []
    for src, url in FEEDS:
        rows += fetch_feed(src, url)
    if not rows:
        raise SystemExit("No feeds could be fetched.")
    df = pd.DataFrame(rows).drop_duplicates("url")
    df = df[df["published"] >= now - timedelta(days=days)].reset_index(drop=True)
    df["article_id"] = df["url"].map(lambda u: hashlib.sha1(u.encode()).hexdigest()[:10])
    print(f"  {len(df)} articles in the last {days} days")

    scored = score_frame(df)
    scored["scored_by"] = "rules"
    scored["rank_score"] = rank_score(scored)

    # Keep Ethereum-relevant stories, plus market-wide ones big enough to matter for ETH
    keep = (scored["eth_relevance"] >= 0.4) | (scored["market_impact"] >= 4)
    scored = scored[keep].reset_index(drop=True)

    if use_llm:
        leads = scored[scored["is_cluster_lead"]].nlargest(max_llm, "rank_score")
        try:
            from llm_scorer import score_with_claude
            print(f"  scoring {len(leads)} lead articles with Claude...")
            llm = score_with_claude(leads, now.isoformat())
            llm_cols = ["sentiment", "sentiment_score", "market_impact", "time_horizon", "confidence",
                        "eth_relevance", "scope", "content_type", "reasoning", "price_implications",
                        "scored_by", "likely_priced_in"]
            scored = scored.set_index("article_id")
            llm = llm.set_index("article_id")
            for c in llm_cols:
                if c in llm.columns:
                    scored.loc[llm.index, c] = llm[c]
            scored = scored.reset_index()
            scored["rank_score"] = rank_score(scored)
        except Exception as e:  # keep the report usable without the API
            print(f"  Claude scoring unavailable ({type(e).__name__}: {e}); using rule-based scores")
            use_llm = False

    px = fetch_prices()
    scored = price_context(scored, px, now)
    ranked = scored.sort_values("rank_score", ascending=False).reset_index(drop=True)
    leads = ranked[ranked["is_cluster_lead"]]

    ov = overall(leads)
    mom = momentum(px)
    events = fetch_protocol_calls()
    today = now.date().isoformat()
    events = [e for e in events if (e["date"] is None or e["date"] >= today)]
    events.sort(key=lambda e: (e["date"] is None, e["date"] or "", not e["is_core"]))
    news_events = leads[leads["future_event"] & (leads["market_impact"] >= 3.5)].head(8)

    assessment = template_assessment(ov, ranked, mom, events)
    if use_llm:
        try:
            from llm_scorer import assessment_with_claude
            ctx = {
                "overall": ov, "momentum": mom,
                "top_articles": leads.head(15)[["title", "source_name", "published", "sentiment",
                                                "sentiment_score", "market_impact", "time_horizon",
                                                "scope", "content_type", "reasoning"]].to_dict("records"),
                "upcoming_protocol_calls": events[:10],
            }
            assessment = assessment_with_claude(ctx)
        except Exception as e:
            print(f"  Claude assessment unavailable ({type(e).__name__}); using template")

    report = {
        "generated_at": now.isoformat(), "window_days": days,
        "scoring": "claude" if use_llm else "rules", "weights": WEIGHTS,
        "overall": ov, "momentum": mom, "assessment": assessment,
        "top5": leads.head(5)["article_id"].tolist(),
        "bullish_catalysts": leads[leads["sentiment"] == "bullish"].head(5)["article_id"].tolist(),
        "bearish_catalysts": leads[leads["sentiment"] == "bearish"].head(5)["article_id"].tolist(),
        "upcoming_protocol_calls": events[:12],
        "upcoming_from_news": news_events["article_id"].tolist(),
        "sources_fetched": sorted(set(df["source"])),
        "articles": json.loads(ranked.to_json(orient="records", date_format="iso")),
    }

    stamp = now.strftime("%Y%m%d-%H%M")
    out = REPORTS / stamp
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    ranked.to_csv(out / "articles.csv", index=False)
    from dashboard import render
    (out / "dashboard.html").write_text(render(report), encoding="utf-8")
    shutil.copy(out / "dashboard.html", REPORTS / "latest.html")

    arch = DATA / "live_archive.csv"
    keep_cols = ["article_id", "source", "url", "title", "title_source", "summary", "published",
                 "date_precision", "section", "sentiment", "sentiment_score", "market_impact",
                 "time_horizon", "confidence", "eth_relevance", "scope", "content_type",
                 "event_type", "scored_by"]
    new = ranked[keep_cols].copy()
    new["published"] = pd.to_datetime(new["published"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    if arch.exists():
        new = pd.concat([pd.read_csv(arch), new]).drop_duplicates("url", keep="last")
    new.to_csv(arch, index=False)

    print(f"\nOverall ETH news sentiment: {ov['score']:+.1f} ({ov['environment']}) | "
          f"{ov['pct_bullish']}% bull / {ov['pct_neutral']}% neutral / {ov['pct_bearish']}% bear")
    if mom:
        print(f"ETH ${mom['price']:,.0f} | 7d {mom['ret_7d']:+.1%} ({mom['state']})")
    print(f"saved {out / 'dashboard.html'}")
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--llm", action="store_true", help="score with Claude (needs anthropic + credentials)")
    p.add_argument("--max-llm", type=int, default=40, help="max lead articles sent to Claude")
    a = p.parse_args()
    run(a.days, a.llm, a.max_llm)


if __name__ == "__main__":
    main()
