"""Optional: score live articles with Claude instead of the lexicon rules.

Used only by live_report.py with --llm. Needs the `anthropic` package and credentials
(ANTHROPIC_API_KEY, or an `ant auth login` profile). The historical model features always
use the deterministic rules in score.py, so the training data does not depend on an API.

Claude sees only the headline, source, date and feed summary of each article. It is told
not to add facts that are not in that text, and its output is checked against a JSON schema.
"""
from __future__ import annotations

import json

import pandas as pd

MODEL = "claude-opus-5-5"

ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "sentiment": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
        "sentiment_score": {"type": "number"},
        "market_impact": {"type": "number"},
        "time_horizon": {"type": "string", "enum": ["short", "medium", "long"]},
        "confidence": {"type": "number"},
        "eth_relevance": {"type": "number"},
        "scope": {"type": "string", "enum": ["eth_specific", "eth_ecosystem", "market_wide", "macro"]},
        "content_type": {"type": "string", "enum": ["fact", "opinion", "speculation"]},
        "likely_priced_in": {"type": "string", "enum": ["likely", "partly", "unlikely", "unclear"]},
        "reasoning": {"type": "string"},
        "price_implications": {"type": "string"},
    },
    "required": ["id", "sentiment", "sentiment_score", "market_impact", "time_horizon",
                 "confidence", "eth_relevance", "scope", "content_type", "likely_priced_in",
                 "reasoning", "price_implications"],
    "additionalProperties": False,
}
SCHEMA = {
    "type": "object",
    "properties": {"articles": {"type": "array", "items": ITEM_SCHEMA}},
    "required": ["articles"],
    "additionalProperties": False,
}

SYSTEM = """You are an Ethereum market-research analyst scoring news for an ETH news-sentiment dashboard.

For each article, use only the headline, source, date and summary provided. Do not add facts, numbers or events that are not in that text. If the text is too thin to judge, say so in the reasoning and lower confidence.

Scoring:
- sentiment_score: -100 (very bearish for ETH) to +100 (very bullish). Neutral is roughly -15..15.
- market_impact: 1-10, how much the news could matter for ETH's price or fundamentals. This is separate from sentiment: a glowing opinion piece is low impact; an ETF decision, a major protocol upgrade, a large exploit or a regulatory action is high impact.
- time_horizon: short = 0-48 hours, medium = 2-30 days, long = 30+ days.
- confidence: 1-100, how sure you are of this reading given only the provided text.
- eth_relevance: 0-1. Ethereum-specific = high; broad crypto or macro = lower.
- scope: eth_specific, eth_ecosystem (L2s, DeFi on Ethereum), market_wide (crypto overall), or macro.
- content_type: fact (reporting of something that happened), opinion, or speculation (price talk, predictions).
- likely_priced_in: whether markets have probably already reacted, given the date and the nature of the news.
- reasoning: 1-3 sentences on why this reads bullish, bearish or neutral for ETH.
- price_implications: 1-2 sentences on how the market could react. Use conditional language. Never state a price target or a guaranteed move.

Return one entry per article, using the article's id."""


def score_with_claude(df: pd.DataFrame, now_iso: str) -> pd.DataFrame:
    """Return df with the analysis columns replaced by Claude's reading. Raises on failure."""
    import anthropic

    client = anthropic.Anthropic()
    items = [
        {
            "id": str(r.article_id),
            "headline": r.title,
            "source": r.source_name,
            "published": str(r.published),
            "summary": (r.summary or "")[:700],
        }
        for r in df.itertuples(index=False)
    ]
    prompt = (
        f"Current time: {now_iso}\n\n"
        f"Articles:\n{json.dumps(items, ensure_ascii=False, indent=1)}"
    )
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=32000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined the request: {resp.stop_details}")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("Claude output was cut off (max_tokens); score fewer articles")
    text = next(b.text for b in resp.content if b.type == "text")
    out = pd.DataFrame(json.loads(text)["articles"])
    out["id"] = out["id"].astype(str)
    for c, lo, hi in [("sentiment_score", -100, 100), ("market_impact", 1, 10),
                      ("confidence", 1, 100), ("eth_relevance", 0, 1)]:
        out[c] = out[c].clip(lo, hi)
    cols = [c for c in ITEM_SCHEMA["required"] if c != "id"]
    merged = df.copy()
    merged["article_id"] = merged["article_id"].astype(str)
    merged = merged.drop(columns=[c for c in cols if c in merged.columns]).merge(
        out.rename(columns={"id": "article_id"}), on="article_id", how="left")
    # Anything Claude skipped keeps the rule-based score
    missing = merged["sentiment"].isna()
    if missing.any():
        fallback = df[df["article_id"].astype(str).isin(merged.loc[missing, "article_id"])]
        merged = pd.concat([merged[~missing], fallback], ignore_index=True)
    merged["scored_by"] = merged["sentiment"].notna().map({True: "claude", False: "rules"})
    merged.loc[merged["article_id"].isin(merged.loc[missing, "article_id"]), "scored_by"] = "rules"
    return merged


def assessment_with_claude(context: dict) -> dict:
    """Ask Claude for the final research-style assessment, grounded in the analysed articles."""
    import anthropic

    client = anthropic.Anthropic()
    schema = {
        "type": "object",
        "properties": {
            "outlook": {"type": "string"},
            "top_bullish": {"type": "string"},
            "top_bearish": {"type": "string"},
            "top_catalyst": {"type": "string"},
            "watchlist": {"type": "array", "items": {"type": "string"}},
            "momentum_note": {"type": "string"},
        },
        "required": ["outlook", "top_bullish", "top_bearish", "top_catalyst", "watchlist", "momentum_note"],
        "additionalProperties": False,
    }
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=8000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=("You write concise investment-research notes on Ethereum news. Use only the "
                "articles, metrics and events provided. Refer to stories by their headline. "
                "Keep news sentiment separate from price momentum. Never predict a price or "
                "promise a move. Each field 1-3 sentences; watchlist has exactly 3 headlines."),
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": json.dumps(context, ensure_ascii=False, default=str)}],
    )
    if resp.stop_reason != "end_turn":
        raise RuntimeError(f"assessment stopped: {resp.stop_reason}")
    return json.loads(next(b.text for b in resp.content if b.type == "text"))
