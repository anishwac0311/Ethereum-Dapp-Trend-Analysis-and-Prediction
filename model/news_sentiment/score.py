"""Rule-based article analysis: sentiment, impact, horizon, relevance, novelty, confidence.

Deterministic and offline, so the historical features can be reproduced exactly. Every
score lists the cues that produced it (`cues`), so a reader can check the reasoning.
The live report can optionally replace these scores with Claude (llm_scorer.py).

Design rules taken from the brief:
  * Sentiment and impact are scored separately. An opinion piece can be very positive
    and low impact; an ETF decision is high impact.
  * Stories about the same event are grouped into clusters (`cluster_id`). Aggregates
    count each cluster once, not each article.
  * `scope` separates Ethereum-specific news from market-wide crypto or macro news.
  * `content_type` separates fact (reporting), opinion and speculation (price talk).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from common import SOURCES, norm_tokens

# --------------------------------------------------------------------------- #
# Lexicons. Phrases are matched on whole words in lowercase text.
# Weights are on a -3..+3 scale.
# --------------------------------------------------------------------------- #
SENTIMENT_TERMS: dict[str, float] = {
    # bullish
    "surge": 2, "surges": 2, "soar": 2.5, "soars": 2.5, "rally": 2, "rallies": 2, "jumps": 1.5,
    "jump": 1.5, "gains": 1.2, "gain": 1, "climbs": 1.2, "rises": 1, "rise": 0.8, "rebound": 1.5,
    "rebounds": 1.5, "recovers": 1.2, "breakout": 1.5, "all time high": 3, "record high": 2.5,
    "new high": 2, "ath": 2.5, "bullish": 2, "outperforms": 1.5, "approves": 2.5, "approved": 2.5,
    "approval": 2, "greenlights": 2.5, "launches": 0.8, "launch": 0.6, "goes live": 1.2,
    "live on mainnet": 1.5, "mainnet": 0.8, "partnership": 1, "partners": 1, "integrates": 1,
    "adopts": 1.5, "adoption": 1.2, "inflows": 1.5, "accumulate": 1.2, "accumulating": 1.2,
    "upgrade": 0.8, "successful": 1.5, "successfully": 1.5, "milestone": 1.2, "record": 1,
    "growth": 1, "grows": 1, "expands": 1, "raises": 0.8, "funding": 0.6, "wins": 1.5,
    "victory": 1.5, "dismissed": 1.5, "dismisses": 1.5, "drops case": 2, "clarity": 1,
    "deflationary": 1.2, "burn": 0.5, "staking": 0.4, "optimistic": 1.2, "boost": 1.2,
    "boosts": 1.2, "strong": 0.8, "demand": 0.6, "buys": 1, "buying": 0.8, "bought": 0.8,
    "recovery": 1.2, "upside": 1.2, "uptrend": 1.5, "flips": 1, "overtakes": 1.2, "net inflows": 2,
    # bearish
    "crash": -3, "crashes": -3, "plunge": -2.5, "plunges": -2.5, "tumbles": -2, "tumble": -2,
    "slumps": -2, "slump": -2, "drops": -1.2, "drop": -1, "falls": -1.2, "fall": -1, "dips": -0.8,
    "dip": -0.6, "slides": -1.2, "sinks": -1.5, "sell off": -2, "selloff": -2, "liquidated": -1.8,
    "liquidations": -1.5, "bearish": -2, "losses": -1.5, "loss": -1, "hack": -2.5, "hacked": -2.5,
    "hacker": -2, "hackers": -2, "exploit": -2.5, "exploited": -2.5, "drained": -2.5, "stolen": -2.5,
    "theft": -2.2, "attack": -1.8, "attacker": -1.8, "vulnerability": -1.5, "bug": -1.2,
    "rug pull": -3, "rugpull": -3, "scam": -2.2, "fraud": -2.5, "phishing": -1.8, "sues": -2,
    "lawsuit": -2, "sued": -2, "sue": -1.5, "charged with": -2, "criminal charges": -2.2,
    "files charges": -2, "indicted": -2.2, "fined": -1.5, "frozen": -1.5, "freeze": -1.2,
    "tax": -0.8, "taxes": -0.8, "levy": -1, "capital gains": -0.5, "gains tax": -1, "gains levy": -1,
    "vulnerable": -1.2,
    "penalty": -1.5, "ban": -2.2, "bans": -2.2, "banned": -2.2, "crackdown": -2.2, "probe": -1.5,
    "investigation": -1.5, "subpoena": -1.5, "rejects": -2, "rejected": -2, "denies": -1.5,
    "delay": -1.2, "delays": -1.2, "delayed": -1.2, "postponed": -1.2, "outage": -1.8,
    "halts": -1.8, "halted": -1.8, "suspends": -1.5, "paused": -1, "bankrupt": -3,
    "bankruptcy": -3, "insolvent": -3, "collapse": -3, "collapses": -3, "contagion": -2.5,
    "outflows": -1.5, "net outflows": -2, "fear": -1.5, "panic": -2, "warning": -1.2, "warns": -1.2,
    "risk": -0.6, "risks": -0.6, "concerns": -1, "struggles": -1.2, "decline": -1.2, "declines": -1.2,
    "downtrend": -1.5, "weak": -0.8, "fud": -1.2, "dump": -1.8, "dumps": -1.8, "sells": -0.8,
    "depeg": -2.5, "depegs": -2.5, "layoffs": -1.5, "shuts down": -2, "shutdown": -1.8,
    "sanctions": -1.8, "sanctioned": -2, "centralization": -0.8, "censorship": -1.2,
}

NEGATORS = {"not", "no", "never", "fails", "fail", "failed", "without", "denies", "deny", "won't", "cant"}

# Event types: (pattern, base impact 1-10, horizon, direction prior -1/0/+1)
EVENT_TYPES: list[tuple[str, str, float, str, int]] = [
    ("etf", r"\b(etf|etfs|exchange traded fund|spot ether fund)\b", 8, "medium", 0),
    ("protocol_upgrade", r"\b(merge|the merge|shanghai|capella|dencun|cancun|pectra|prague|electra|fusaka|glamsterdam|hard fork|hardfork|eip \d+|eip\d+|proto danksharding|danksharding|beacon chain|upgrade|testnet|devnet|all core devs|acd)\b", 7, "long", 1),
    ("regulation", r"\b(sec|cftc|regulator|regulators|regulation|regulatory|lawsuit|sues|court|judge|congress|senate|bill|mica|treasury|ofac|doj|gensler|security status|securities)\b", 6.5, "medium", -1),
    ("hack_exploit", r"\b(hack|hacked|exploit|exploited|drained|stolen|attacker|rug pull|rugpull|reentrancy|flash loan attack|vulnerability|phishing)\b", 5.5, "short", -1),
    ("macro", r"\b(fed|federal reserve|fomc|inflation|cpi|interest rate|rates|recession|jobs report|treasury yields|tariff|tariffs|stocks|nasdaq|s p 500|dollar)\b", 5, "short", 0),
    ("institutional", r"\b(blackrock|fidelity|grayscale|vaneck|jpmorgan|goldman|visa|mastercard|paypal|stripe|bank|banks|institutional|institutions|treasury company|corporate treasury|nasdaq listed)\b", 5.5, "medium", 1),
    ("staking_supply", r"\b(staking|staked|stakers|validator|validators|withdrawals|unstaking|burn|burned|supply|issuance|deflationary|liquid staking|restaking)\b", 5, "medium", 0),
    ("scaling_l2", r"\b(layer 2|layer2|l2|l2s|rollup|rollups|arbitrum|optimism|base|zksync|starknet|polygon|scroll|linea|blob|blobs|blobspace)\b", 4.5, "medium", 1),
    ("exchange_flows", r"\b(whale|whales|inflows|outflows|exchange reserves|open interest|funding rates|liquidations|options expiry|futures)\b", 4, "short", 0),
    ("market_price", r"\b(price|prices|rally|surge|crash|plunge|all time high|record high|bull|bear|market|markets|trading|traders)\b", 4, "short", 0),
    ("defi", r"\b(defi|tvl|lending|dex|uniswap|aave|maker|makerdao|compound|curve|lido|stablecoin|stablecoins|yield)\b", 3.5, "medium", 0),
    ("nft_gaming", r"\b(nft|nfts|opensea|blur|metaverse|gaming|game|collectible|collectibles|punks|bored ape)\b", 3, "medium", 0),
    ("developer_ecosystem", r"\b(grant|grants|devcon|devconnect|research|researchers|client|clients|geth|nethermind|besu|erigon|prysm|lighthouse|teku|vitalik|buterin|foundation)\b", 3.5, "long", 1),
]

# Ethereum relevance tiers
ETH_CORE = r"\b(ethereum|eth|ether|ethers|vitalik|buterin|ethereum foundation|ef|beacon chain|the merge|dencun|pectra|fusaka|shanghai|eip \d+|eip\d+|geth|etherscan|erc 20|erc20|erc 721|evm|gwei|staked ether|steth)\b"
ETH_ECOSYSTEM = r"\b(arbitrum|optimism|base|zksync|starknet|polygon|scroll|linea|layer 2|rollup|rollups|lido|uniswap|aave|makerdao|maker|compound|curve|eigenlayer|restaking|ens|opensea|defi|nft|nfts|stablecoin|stablecoins|usdc|tether|usdt|dai)\b"
OTHER_CHAINS = r"\b(bitcoin|btc|solana|sol|xrp|ripple|cardano|ada|dogecoin|doge|bnb|tron|avalanche|avax|ton|litecoin|polkadot|sui|aptos|hyperliquid)\b"

SPECULATION = r"\b(price prediction|prediction|predicts|could|may|might|expect|expects|forecast|targets|target|analyst|analysts|says trader|traders say|eyes|poised|chart|technical analysis|price analysis|will .* reach)\b"
OPINION = r"\b(opinion|op ed|why|how to|explained|guide|what is|should you|we need|the case for|i think|column|editorial|podcast|interview|review)\b"
OPINION_SECTIONS = {"magazine", "opinion", "explained", "learn", "podcasts", "people", "how-to", "guides", "linked"}
SPECULATION_SECTIONS = {"price-analysis", "markets-analysis"}
FUTURE_EVENT = r"\b(scheduled|set for|slated|deadline|upcoming|next week|next month|vote|voting|decision|countdown|expected to|ahead of|to go live|activation|epoch|testnet|devnet)\b"

MONEY = re.compile(r"\$(\d+(?:\.\d+)?)\s*(k|m|b|million|billion|thousand)?\b")

CATEGORY_TERMS = {
    "DeFi": r"\b(defi|lending|borrow|yield|liquid staking|restaking|stablecoin|derivatives|perpetual|perps|vault|vaults|tvl)\b",
    "DEX": r"\b(dex|dexs|decentralized exchange|amm|swap|swaps|uniswap|curve|sushiswap|liquidity pool|aggregator)\b",
    "NFT": r"\b(nft|nfts|opensea|blur|collectible|collectibles|pfp|marketplace|punks|bored ape|art)\b",
    "Gaming": r"\b(gaming|game|games|gamefi|play to earn|metaverse|axie|sandbox|decentraland)\b",
    "Infrastructure": r"\b(bridge|bridges|oracle|oracles|layer 2|rollup|infrastructure|wallet|wallets|rpc|interoperability|cross chain)\b",
    "Social": r"\b(social|socialfi|farcaster|lens|creator|creators|community)\b",
    "Other": r"\b(dao|daos|governance|launchpad|insurance|payments|identity|ens)\b",
}


def _text(title: str, summary: str = "") -> str:
    t = f"{title} {summary}".lower()
    t = re.sub(r"[^a-z0-9$\.\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _find(pattern: str, text: str) -> list[str]:
    return [m.group(0) for m in re.finditer(pattern, text)]


def _money_usd(text: str) -> float:
    best = 0.0
    for num, unit in MONEY.findall(text):
        v = float(num)
        unit = (unit or "").lower()
        v *= {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "billion": 1e9}.get(unit, 1)
        best = max(best, v)
    return best


@dataclass
class Analysis:
    sentiment: str
    sentiment_score: float
    market_impact: float
    time_horizon: str
    confidence: float
    eth_relevance: float
    scope: str
    content_type: str
    event_type: str
    future_event: bool
    categories: list[str] = field(default_factory=list)
    cues: list[str] = field(default_factory=list)
    reasoning: str = ""
    price_implications: str = ""


def lexicon_sentiment(text: str) -> tuple[float, list[str]]:
    """Weighted lexicon score with simple negation. Returns (-100..100, matched cues)."""
    tokens = text.split()
    total, hits = 0.0, []
    # phrases first (2-3 words), then single words not already covered
    covered = set()
    for n in (3, 2, 1):
        for i in range(len(tokens) - n + 1):
            if any(j in covered for j in range(i, i + n)):
                continue
            phrase = " ".join(tokens[i:i + n])
            w = SENTIMENT_TERMS.get(phrase)
            if w is None:
                continue
            window = tokens[max(0, i - 3):i]
            if any(t in NEGATORS for t in window):
                w = -0.6 * w
                hits.append(f"not {phrase}")
            else:
                hits.append(phrase)
            total += w
            covered.update(range(i, i + n))
    # squash to -100..100; ~3 strong cues saturate
    score = 100 * math.tanh(total / 4.0)
    return score, hits


def analyze(title: str, summary: str = "", section: str = "", source: str = "",
            title_source: str = "feed") -> Analysis:
    text = _text(title, summary)
    sec = (section or "").lower()
    cues: list[str] = []

    # --- sentiment
    lex, hits = lexicon_sentiment(text)
    cues += [f"+{h}" if SENTIMENT_TERMS.get(h.replace("not ", ""), 0) > 0 and not h.startswith("not ") else f"-{h}" if not h.startswith("not ") else h for h in hits]

    # --- event type (first, i.e. highest-priority, match wins; all matches kept as cues)
    matched = [(name, imp, hz, prior, _find(pat, text)) for name, pat, imp, hz, prior in EVENT_TYPES]
    matched = [m for m in matched if m[4]]
    if matched:
        event_type, base_impact, horizon, prior, words = matched[0]
        cues.append(f"event:{event_type}({words[0]})")
    else:
        event_type, base_impact, horizon, prior = "general", 2.5, "short", 0

    # Direction overrides by event type
    if event_type == "etf":
        if re.search(r"\b(approve|approves|approved|approval|greenlight|launch|launches|debut|inflows|begins trading)\b", text):
            lex = max(lex, 45)
        elif re.search(r"\b(reject|rejects|rejected|delay|delays|delayed|postpone|outflows|denies)\b", text):
            lex = min(lex, -40)
    if event_type == "regulation" and re.search(r"\b(dismiss|dismissed|drops|ends|closes|wins|clarity|approves|commodity)\b", text):
        lex = max(lex, 30)
        prior = 1
    if event_type == "hack_exploit" and not re.search(r"\b(recovered|returns|returned|bounty|white hat|whitehat|patched|prevented)\b", text):
        lex = min(lex, -35)
    if event_type == "protocol_upgrade" and re.search(r"\b(delay|delayed|postponed|bug|incident|finality|split|halt)\b", text):
        lex = min(lex, -25)

    # Weak prior when the lexicon is silent
    score = lex if abs(lex) >= 8 else lex + 8 * prior
    score = float(np.clip(score, -100, 100))

    # --- relevance & scope
    core = _find(ETH_CORE, text)
    eco = _find(ETH_ECOSYSTEM, text)
    other = _find(OTHER_CHAINS, text)
    if source in ("ethereum_foundation", "ethereum_pm"):
        relevance = 1.0
    elif core:
        relevance = 0.95 if not other else 0.75
    elif eco:
        relevance = 0.55 if not other else 0.4
    elif other:
        relevance = 0.15
    else:
        relevance = 0.3
    if event_type == "macro" and not core:
        scope = "macro"
    elif relevance >= 0.7:
        scope = "eth_specific"
    elif relevance >= 0.4:
        scope = "eth_ecosystem"
    else:
        scope = "market_wide"
    if core:
        cues.append(f"eth:{core[0]}")
    elif eco:
        cues.append(f"eco:{eco[0]}")

    # --- impact
    impact = base_impact
    usd = _money_usd(text)
    if event_type == "hack_exploit" and usd:
        impact += min(3, max(0, math.log10(usd) - 6))  # $1m → +0, $1b → +3
        cues.append(f"size:${usd:,.0f}")
    if re.search(r"\b(sec|etf)\b", text) and core:
        impact += 1
    impact *= 0.55 + 0.45 * relevance  # off-topic news matters less for ETH
    if source in ("ethereum_foundation", "ethereum_pm") and event_type == "protocol_upgrade":
        impact += 1

    # --- content type
    spec = _find(SPECULATION, text) or sec in SPECULATION_SECTIONS
    opin = _find(OPINION, text) or sec in OPINION_SECTIONS or text.endswith("?") or "?" in title
    if spec and not (event_type in ("etf", "hack_exploit", "regulation") and not opin):
        content_type = "speculation"
    elif opin:
        content_type = "opinion"
    else:
        content_type = "fact"
    if content_type != "fact":
        impact *= 0.6
        cues.append(f"type:{content_type}")
    impact = float(np.clip(round(impact, 1), 1, 10))

    # --- confidence
    conf = 45 + 6 * min(len(hits), 4) + (10 if matched else 0)
    if title_source == "url_slug":
        conf -= 10
    if content_type != "fact":
        conf -= 8
    if summary:
        conf += 5
    conf = float(np.clip(conf, 10, 90))

    sentiment = "bullish" if score >= 15 else "bearish" if score <= -15 else "neutral"
    cats = [c for c, pat in CATEGORY_TERMS.items() if re.search(pat, text)]
    fut = bool(re.search(FUTURE_EVENT, text))

    a = Analysis(sentiment, round(score, 1), impact, horizon, conf, relevance, scope,
                 content_type, event_type, fut, cats, cues)
    a.reasoning = _reasoning(a, hits)
    a.price_implications = _implications(a)
    return a


def _reasoning(a: Analysis, hits: list[str]) -> str:
    kind = {"fact": "Factual report", "opinion": "Opinion/explainer", "speculation": "Speculative/price commentary"}[a.content_type]
    scope = {"eth_specific": "Ethereum-specific", "eth_ecosystem": "Ethereum-ecosystem",
             "market_wide": "market-wide crypto", "macro": "macro"}[a.scope]
    words = ", ".join(hits[:4]) if hits else "no strong sentiment words"
    ev = a.event_type.replace("_", " ")
    return (f"{kind}; {scope} {ev} story. Read as {a.sentiment} from: {words}. "
            f"Impact {a.market_impact}/10 reflects the event type ({ev}) scaled by ETH relevance.")


def _implications(a: Analysis) -> str:
    if a.sentiment == "neutral" or a.market_impact < 3:
        return "Unlikely to move ETH on its own; useful as context."
    side = "supportive" if a.sentiment == "bullish" else "a headwind"
    hz = {"short": "within days, and often already traded by the time it is reported",
          "medium": "over weeks, as flows and positioning adjust",
          "long": "over months, through fundamentals rather than an immediate price move"}[a.time_horizon]
    caveat = " Speculative framing, so treat with caution." if a.content_type != "fact" else ""
    reach = " Market-wide news, so ETH would likely move with the broader market." if a.scope in ("market_wide", "macro") else ""
    return f"Could be {side} for ETH {hz}.{reach}{caveat} Not a price forecast."


# --------------------------------------------------------------------------- #
# Batch scoring, de-duplication, ranking
# --------------------------------------------------------------------------- #
STOP = set("the a an of to in on for and or is are as at by with from its it this that be new how why what will after over into amid says".split())


def _sig(title: str) -> frozenset:
    return frozenset(t for t in norm_tokens(title) if t not in STOP and len(t) > 2)


def cluster_events(df: pd.DataFrame, days: int = 3, threshold: float = 0.45) -> pd.Series:
    """Group near-duplicate stories (token Jaccard ≥ threshold within ±days).

    Month-precision rows are compared within the same month. Returns a cluster id per row.
    """
    sigs = df["title"].map(_sig).tolist()
    dates = pd.to_datetime(df["published"]).values.astype("datetime64[D]")
    prec = df.get("date_precision", pd.Series("day", index=df.index)).tolist()
    order = np.argsort(dates, kind="stable")
    cluster = np.full(len(df), -1)
    # token → recent row indices (for candidate lookup)
    index: dict[str, list[int]] = {}
    next_id = 0
    win = np.timedelta64(days, "D")
    for i in order:
        s = sigs[i]
        best, best_j = 0.0, -1
        cands = set()
        for t in s:
            cands.update(index.get(t, ()))
        for j in cands:
            gap = abs(dates[i] - dates[j])
            limit = np.timedelta64(31, "D") if "month" in (prec[i], prec[j]) else win
            if gap > limit:
                continue
            u = len(s | sigs[j])
            if not u:
                continue
            jac = len(s & sigs[j]) / u
            if jac > best:
                best, best_j = jac, j
        if best >= threshold and best_j >= 0:
            cluster[i] = cluster[best_j]
        else:
            cluster[i] = next_id
            next_id += 1
        for t in s:
            lst = index.setdefault(t, [])
            lst.append(i)
            if len(lst) > 400:  # keep lookup bounded
                del lst[:200]
    cluster = _merge_by_entity(df, cluster, dates, win)
    return pd.Series(cluster, index=df.index, name="cluster_id")


# Capitalised words that are too common to identify a single event
GENERIC_ENTITIES = {
    "ethereum", "ether", "eth", "bitcoin", "btc", "crypto", "cryptocurrency", "sec", "us", "u.s.",
    "the", "a", "an", "why", "how", "what", "new", "here", "this", "after", "as", "is", "will",
    "trump", "fed", "defi", "nft", "nfts", "etf", "etfs", "dao", "layer", "web3", "ai", "says",
    "report", "analysts", "analyst", "price", "market", "markets", "coin", "token", "tokens",
    "foundation", "vitalik", "buterin", "stablecoin", "stablecoins", "usdc", "usdt", "solana", "xrp",
}
ENTITY_EVENTS = {"hack_exploit", "etf", "regulation", "protocol_upgrade", "institutional"}


def _entities(title: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]+", str(title))
    return {w.lower() for w in words[1:] if w[0].isupper() and len(w) >= 4
            and w.lower() not in GENERIC_ENTITIES} | {
        w.lower() for w in words[:1] if len(w) >= 4 and w[0].isupper() and w.lower() not in GENERIC_ENTITIES
        and not w.lower().endswith("ing")}


def _merge_by_entity(df: pd.DataFrame, cluster: np.ndarray, dates, win) -> np.ndarray:
    """Second pass: same high-impact event type + shared named entity within ±days → one event.

    Catches follow-ups worded differently ("Binance hack is 'cyber war'" / "$3.1B stolen from
    Binance not yet laundered"). Only used on real headlines; slug titles have no capitals.
    """
    if "event_type" not in df.columns:
        return cluster
    titles = df["title"].tolist()
    ts = df.get("title_source", pd.Series("feed", index=df.index)).tolist()
    ev = df["event_type"].tolist()
    parent = {c: c for c in set(cluster)}

    def find(c):
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c

    ents = [(_entities(t) if s == "feed" and e in ENTITY_EVENTS else set()) for t, s, e in zip(titles, ts, ev)]
    idx = [i for i, e in enumerate(ents) if e]
    for a_pos, i in enumerate(idx):
        for j in idx[a_pos + 1:]:
            if ev[i] != ev[j] or abs(dates[i] - dates[j]) > win:
                continue
            if ents[i] & ents[j]:
                ri, rj = find(cluster[i]), find(cluster[j])
                if ri != rj:
                    parent[rj] = ri
    return np.array([find(c) for c in cluster])


WEIGHTS = {"impact": 0.35, "sentiment": 0.25, "relevance": 0.20, "credibility": 0.10, "novelty": 0.10}


def score_frame(df: pd.DataFrame, cluster: bool = True) -> pd.DataFrame:
    """Analyse every row of a frame with title/summary/section/source/title_source/published."""
    rows = []
    for r in df.itertuples(index=False):
        a = analyze(getattr(r, "title", ""), getattr(r, "summary", "") or "",
                    getattr(r, "section", "") or "", getattr(r, "source", ""),
                    getattr(r, "title_source", "feed"))
        rows.append({
            "sentiment": a.sentiment, "sentiment_score": a.sentiment_score,
            "market_impact": a.market_impact, "time_horizon": a.time_horizon,
            "confidence": a.confidence, "eth_relevance": a.eth_relevance, "scope": a.scope,
            "content_type": a.content_type, "event_type": a.event_type,
            "future_event": a.future_event, "categories": "|".join(a.categories),
            "cues": "; ".join(a.cues), "reasoning": a.reasoning,
            "price_implications": a.price_implications,
        })
    out = pd.concat([df.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    out["credibility"] = out["source"].map(lambda s: SOURCES.get(s, {}).get("credibility", 0.6))
    out["is_primary_source"] = out["source"].map(lambda s: SOURCES.get(s, {}).get("primary", False))
    if cluster:
        out["cluster_id"] = cluster_events(out).values
        out = add_novelty(out)
    return out


def add_novelty(out: pd.DataFrame) -> pd.DataFrame:
    """Novelty: first report of an event, and how unusual the event type is."""
    out = out.copy()
    out["_d"] = pd.to_datetime(out["published"])
    # Primary sources first, then credibility, then earliest
    out = out.sort_values(["cluster_id", "is_primary_source", "credibility", "_d"],
                          ascending=[True, False, False, True])
    out["cluster_size"] = out.groupby("cluster_id")["cluster_id"].transform("size")
    out["cluster_rank"] = out.groupby("cluster_id").cumcount()
    out["is_cluster_lead"] = out["cluster_rank"] == 0
    type_freq = out.loc[out["is_cluster_lead"], "event_type"].value_counts(normalize=True)
    rarity = 1 - out["event_type"].map(type_freq).fillna(0).clip(0, 1)
    out["novelty"] = (0.6 * rarity + 0.4 * (out["cluster_rank"] == 0)).round(3)
    out = out.drop(columns=["_d"]).sort_index()
    return out


def rank_score(df: pd.DataFrame) -> pd.Series:
    """Weighted importance 0-100: 35 impact, 25 |sentiment|, 20 relevance, 10 credibility, 10 novelty."""
    raw = (
        WEIGHTS["impact"] * df["market_impact"] / 10
        + WEIGHTS["sentiment"] * df["sentiment_score"].abs() / 100
        + WEIGHTS["relevance"] * df["eth_relevance"]
        + WEIGHTS["credibility"] * df["credibility"]
        + WEIGHTS["novelty"] * df["novelty"]
    )
    return (100 * raw).round(1)
