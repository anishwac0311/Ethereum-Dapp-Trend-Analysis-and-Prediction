"""Score the historical corpus and build leakage-safe news features for the DApp model.

Inputs : data/articles_history.csv (fetch_history.py), data/eth_monthly.csv (fetch_prices.py)
Outputs:
  data/articles_scored.csv   every article with its analysis (not in Git: large, rebuildable)
  data/news_monthly.csv      one row per month: Ethereum news environment + ETH price
  data/dapp_mentions.csv     article ↔ DApp matches (for audit)
  data/dapp_news_by_k.csv    one row per (slug, k): the table the model joins on

Timing. Window k covers calendar months 0..k-1 after the launch month, the same months as
the on-chain features. Every feature uses only articles published in or before month k-1,
or in the months before launch. Nothing from after the window is used.

Counting. Aggregates use one article per event cluster (the lead, preferring primary
sources), so ten outlets covering one hack count once.
"""
from __future__ import annotations

import argparse
import re

import numpy as np
import pandas as pd

from common import DATA, LIFECYCLE_CSV, OFFCHAIN_BY_K
from score import CATEGORY_TERMS, score_frame

ETH_REL = 0.7  # relevance cut-off for "Ethereum news"

# --------------------------------------------------------------------------- #
# DApp aliases
# --------------------------------------------------------------------------- #
SUFFIXES = {"finance", "protocol", "dao", "network", "exchange", "ecosystem", "labs", "defi",
            "capital", "money", "markets", "market", "xyz", "io", "fi", "app", "swap"}
# Names that are ordinary words; only their longer, specific form is matched.
GENERIC = {
    "loop", "cap", "native", "flex", "bits", "everything", "harbor", "grace", "noon", "seer",
    "gamma", "sir", "safe", "spark", "fluid", "cleave", "concrete", "legion", "lagoon",
    "notional", "parallel", "electra", "ample", "alto", "anvil", "goose", "river", "ring",
    "union", "radiant", "maker", "compound", "across", "base", "element", "origin", "index",
    "prime", "reserve", "hop", "keep", "loot", "manifest", "marginal", "mint", "more", "nest",
    "nested", "seamless", "solid", "spot", "sync", "tangible", "term", "wing", "yield", "zero",
    "kernel", "cork", "cook", "sweep", "hourglass", "pareto", "wagmi", "ether", "sandbox",
    "geyser", "bumper", "level", "summer", "native", "royal", "superform", "accountable", "astra",
    "bond", "bridge", "clever", "dough", "envelop", "exactly", "fira", "flashstake", "gem",
    "genie", "goober", "hats", "inception", "king", "lynx", "mitosis", "napier", "neutral",
    "nucleus", "overtime", "parallax", "pine", "poolside", "premia", "prisma", "redacted",
    "resolv", "rubicon", "sector", "shift", "silo", "solace", "spectra", "spice", "stablehodl",
    "sturdy", "supernova", "swarm", "tetu", "treehouse", "unitas", "vector", "voltz", "warp",
    "wasabi", "whales", "zircuit", "re", "de1", "bits", "fuji", "aera", "affine", "ajna", "aloe",
    "ante", "aspida", "cega", "harvest", "pickle", "convex", "rocket", "stake", "the",
    "foundation", "team", "percent", "beta", "carbon", "mind", "secured", "inverse", "jones",
    "davos", "outcome", "venus", "optimism", "otherside", "gnosis",
}
EXTRA_ALIASES = {
    "maker": ["makerdao", "maker dao", "maker protocol", "sky protocol"],
    "compound-finance": ["compound finance", "compound protocol", "compound dao", "compound labs"],
    "safe": ["gnosis safe", "safe wallet", "safe global"],
    "ether-fi": ["ether fi", "etherfi"],
    "the-sandbox": ["the sandbox"],
    "rocket-pool": ["rocket pool", "rocketpool"],
    "convex-finance": ["convex finance", "convex"],
    "harvest-finance": ["harvest finance"],
    "pickle": ["pickle finance"],
    "curve-finance": ["curve finance", "curve dao", "curve"],
    "uniswap": ["uniswap", "uniswap labs"],
    "opensea-seaport": ["opensea", "seaport"],
    "opensea-v1": ["opensea"],
    "opensea-v2": ["opensea"],
    "blast-l2": ["blast l2", "blast network", "blast mainnet"],
    "arbitrum-foundation": ["arbitrum"],
    "optimism-foundation": ["optimism network", "optimism foundation", "optimism mainnet", "op mainnet",
                            "op stack", "optimism superchain", "optimism layer"],
    "foundation-nft": ["foundation nft", "foundation app"],
    "otherside": ["otherside metaverse", "yuga otherside"],
    "gnosis-protocol-v1": ["gnosis protocol", "gnosis chain", "gnosis safe"],
    "venus-finance": ["venus protocol"],
    "polygon-bridge": ["polygon bridge", "polygon pos bridge"],
    "zksync-era-txbridge": ["zksync"],
    "starknet-bridge": ["starknet"],
    "ens": ["ens", "ethereum name service"],
    "tornado-cash": ["tornado cash"],
    "lido": ["lido", "lido finance", "lido dao"],
    "eigencloud": ["eigenlayer", "eigen layer", "eigencloud"],
    "olympus-dao": ["olympus dao", "olympusdao"],
    "frax-finance": ["frax", "frax finance"],
    "axie-infinity": ["axie infinity", "axie"],
}
# Multi-word names that are generic phrases
BLOCKED_ALIASES = {"defi yield", "yield protocol", "team finance", "secured finance"}
NEGATIVE_CONTEXT = {"curve": r"\byield curve\b|\blearning curve\b|\bahead of the curve\b"}


def _clean_name(s: str) -> str:
    s = re.sub(r"\(.*?\)", " ", str(s).lower())
    s = re.sub(r"[^a-z0-9\.]+", " ", s).replace(".", " ")
    toks = [t for t in s.split() if not re.fullmatch(r"v\d+", t)]
    return " ".join(toks).strip()


def dapp_aliases(slug: str, name: str, parent: str) -> set[str]:
    out: set[str] = set(EXTRA_ALIASES.get(parent, [])) | set(EXTRA_ALIASES.get(slug, []))
    for raw in {name, str(parent).replace("-", " ")}:
        full = _clean_name(raw)
        if not full:
            continue
        toks = full.split()
        core = list(toks)
        while len(core) > 1 and core[-1] in SUFFIXES:
            core = core[:-1]
        for cand in {full, " ".join(core)}:
            words = cand.split()
            if not words:
                continue
            if len(words) == 1 and (cand in GENERIC or cand in SUFFIXES or len(cand) < 4):
                continue
            out.add(cand)
    return {a for a in out if a and a not in BLOCKED_ALIASES}


def _text_ngrams(text: str, n_max: int = 4) -> set[str]:
    toks = re.sub(r"[^a-z0-9]+", " ", str(text).lower()).split()
    grams = set()
    for n in range(1, n_max + 1):
        for i in range(len(toks) - n + 1):
            grams.add(" ".join(toks[i:i + n]))
    return grams


def match_dapps(articles: pd.DataFrame, life: pd.DataFrame) -> pd.DataFrame:
    alias_map: dict[str, set[str]] = {}
    for r in life.itertuples(index=False):
        for a in dapp_aliases(r.slug, r.name, r.parent_protocol):
            alias_map.setdefault(a, set()).add(r.slug)
    rows = []
    texts = (articles["title"].fillna("") + " " + articles["summary"].fillna("")).tolist()
    for idx, text in zip(articles.index, texts):
        grams = _text_ngrams(text)
        hits = grams.intersection(alias_map)
        if not hits:
            continue
        low = text.lower()
        for a in hits:
            neg = NEGATIVE_CONTEXT.get(a)
            if neg and re.search(neg, low):
                continue
            for slug in alias_map[a]:
                rows.append({"article_idx": idx, "slug": slug, "alias": a})
    m = pd.DataFrame(rows).drop_duplicates(["article_idx", "slug"]) if rows else pd.DataFrame(
        columns=["article_idx", "slug", "alias"])
    return m


# --------------------------------------------------------------------------- #
# Monthly environment
# --------------------------------------------------------------------------- #
def monthly_table(scored: pd.DataFrame, prices: pd.DataFrame | None) -> pd.DataFrame:
    lead = scored[scored["is_cluster_lead"]].copy()
    lead["is_eth"] = lead["eth_relevance"] >= ETH_REL
    lead["bull"] = lead["sentiment"] == "bullish"
    lead["bear"] = lead["sentiment"] == "bearish"
    lead["hack"] = lead["event_type"] == "hack_exploit"
    lead["reg_bear"] = (lead["event_type"] == "regulation") & lead["bear"]
    lead["upgrade"] = lead["event_type"] == "protocol_upgrade"
    lead["ef"] = lead["source"] == "ethereum_foundation"
    lead["w"] = lead["market_impact"]

    def agg(g: pd.DataFrame) -> pd.Series:
        e = g[g["is_eth"]]
        out = {
            "n_articles": len(g),
            "n_eth": len(e),
            "eth_share": len(e) / len(g) if len(g) else np.nan,
            "sent_all": g["sentiment_score"].mean(),
            "sent_eth": e["sentiment_score"].mean() if len(e) else np.nan,
            "sent_eth_wtd": np.average(e["sentiment_score"], weights=e["w"]) if len(e) else np.nan,
            "bull_share_eth": e["bull"].mean() if len(e) else np.nan,
            "bear_share_eth": e["bear"].mean() if len(e) else np.nan,
            "impact_eth_mean": e["market_impact"].mean() if len(e) else np.nan,
            "n_hack": int(g["hack"].sum()),
            "n_reg_bear": int(g["reg_bear"].sum()),
            "n_upgrade": int(g["upgrade"].sum()),
            "n_ef_posts": int(g["ef"].sum()),
            "fact_share": (g["content_type"] == "fact").mean(),
        }
        cats = g["categories"].fillna("")
        for c in CATEGORY_TERMS:
            mask = cats.str.contains(rf"(?:^|\|){c}(?:\||$)", regex=True)
            out[f"n_cat_{c}"] = int(mask.sum())
            out[f"sent_cat_{c}"] = g.loc[mask, "sentiment_score"].mean() if mask.any() else np.nan
        return pd.Series(out)

    mon = lead.groupby("month").apply(agg, include_groups=False).reset_index()
    if prices is not None:
        mon = mon.merge(prices[["month", "eth_close", "eth_ret_1m", "eth_vol_1m"]], on="month", how="left")
    return mon


# --------------------------------------------------------------------------- #
# Window features per (slug, k)
# --------------------------------------------------------------------------- #
NEWS_MARKET_FEATURES = [
    "news_eth_sent", "news_eth_sent_wtd", "news_eth_net_bull", "news_eth_attention",
    "news_hack_rate", "news_reg_bear_rate", "news_cat_attention", "news_cat_sent",
    "news_eth_sent_pre3m",
]
PRICE_FEATURES = ["eth_ret_window", "eth_ret_pre3m", "eth_vol_window"]
NEWS_DAPP_FEATURES = [
    "dapp_log_mentions_window", "dapp_log_mentions_pre6m", "dapp_news_sent_window",
    "dapp_neg_event_window",
]
ALL_FEATURES = NEWS_MARKET_FEATURES + PRICE_FEATURES + NEWS_DAPP_FEATURES


def _months(launch: pd.Period, lo: int, hi: int) -> list[str]:
    return [str(launch + i) for i in range(lo, hi + 1)]


def by_k_table(mon: pd.DataFrame, scored: pd.DataFrame, mentions: pd.DataFrame,
               life: pd.DataFrame, ks: range) -> pd.DataFrame:
    M = mon.set_index("month")
    lead_idx = set(scored.index[scored["is_cluster_lead"]])
    men = mentions[mentions["article_idx"].isin(lead_idx)].merge(
        scored[["month", "sentiment_score", "event_type", "sentiment"]],
        left_on="article_idx", right_index=True)
    men_by_slug = {s: g for s, g in men.groupby("slug")}

    def wmean(col: str, wcol: str, months: list[str]) -> float:
        sub = M.reindex(months)[[col, wcol]].dropna()
        if sub.empty or sub[wcol].sum() == 0:
            return np.nan
        return float(np.average(sub[col], weights=sub[wcol]))

    rows = []
    for r in life.itertuples(index=False):
        if pd.isna(r.launch_month):
            continue
        launch = pd.Period(r.launch_month, "M")
        cat = r.category_group if r.category_group in CATEGORY_TERMS else "Other"
        g = men_by_slug.get(r.slug)
        for k in ks:
            win = _months(launch, 0, k - 1)
            pre3 = _months(launch, -3, -1)
            pre6 = _months(launch, -6, -1)
            W = M.reindex(win)
            n_all = W["n_articles"].sum()
            n_eth = W["n_eth"].sum()
            bull = (W["bull_share_eth"] * W["n_eth"]).sum()
            bear = (W["bear_share_eth"] * W["n_eth"]).sum()
            row = {
                "slug": r.slug, "k": k,
                "news_eth_sent": wmean("sent_eth", "n_eth", win),
                "news_eth_sent_wtd": wmean("sent_eth_wtd", "n_eth", win),
                "news_eth_net_bull": (bull - bear) / n_eth if n_eth else np.nan,
                "news_eth_attention": n_eth / n_all if n_all else np.nan,
                "news_hack_rate": 100 * W["n_hack"].sum() / n_all if n_all else np.nan,
                "news_reg_bear_rate": 100 * W["n_reg_bear"].sum() / n_all if n_all else np.nan,
                "news_cat_attention": W[f"n_cat_{cat}"].sum() / n_all if n_all else np.nan,
                "news_cat_sent": wmean(f"sent_cat_{cat}", f"n_cat_{cat}", win),
                "news_eth_sent_pre3m": wmean("sent_eth", "n_eth", pre3),
                "eth_ret_window": W["eth_ret_1m"].sum(min_count=1),
                "eth_ret_pre3m": M.reindex(pre3)["eth_ret_1m"].sum(min_count=1),
                "eth_vol_window": W["eth_vol_1m"].mean(),
            }
            if g is not None:
                gw = g[g["month"].isin(win)]
                gp = g[g["month"].isin(pre6)]
                row["dapp_log_mentions_window"] = float(np.log1p(len(gw)))
                row["dapp_log_mentions_pre6m"] = float(np.log1p(len(gp)))
                row["dapp_news_sent_window"] = gw["sentiment_score"].mean() if len(gw) else np.nan
                neg = (gw["event_type"] == "hack_exploit") | (
                    (gw["event_type"] == "regulation") & (gw["sentiment"] == "bearish"))
                row["dapp_neg_event_window"] = int(neg.any())
            else:
                row.update({"dapp_log_mentions_window": 0.0, "dapp_log_mentions_pre6m": 0.0,
                            "dapp_news_sent_window": np.nan, "dapp_neg_event_window": 0})
            rows.append(row)
    out = pd.DataFrame(rows)
    # Months the corpus doesn't cover → NaN, not 0
    covered = set(mon["month"])
    first, last = min(covered), max(covered)
    lm = life.set_index("slug")["launch_month"]
    start = out["slug"].map(lambda s: str(pd.Period(lm[s], "M") - 6))
    end = out.apply(lambda x: str(pd.Period(lm[x["slug"]], "M") + int(x["k"]) - 1), axis=1)
    outside = (start < first) | (end > last)
    out.loc[outside, NEWS_DAPP_FEATURES] = np.nan
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--kmax", type=int, default=9)
    p.add_argument("--rescore", action="store_true", help="re-score even if articles_scored.csv exists")
    args = p.parse_args()

    scored_path = DATA / "articles_scored.csv"
    if scored_path.exists() and not args.rescore:
        scored = pd.read_csv(scored_path)
        print(f"loaded {scored_path.name} ({len(scored):,})")
    else:
        arts = pd.read_csv(DATA / "articles_history.csv")
        arts["summary"] = arts["summary"].fillna("")
        print(f"scoring {len(arts):,} articles...")
        scored = score_frame(arts)
        scored.to_csv(scored_path, index=False)
        print(f"saved {scored_path.name}")
    scored["month"] = scored["month"].astype(str)
    scored["summary"] = scored["summary"].fillna("")

    prices = pd.read_csv(DATA / "eth_monthly.csv") if (DATA / "eth_monthly.csv").exists() else None
    mon = monthly_table(scored, prices)
    mon.to_csv(DATA / "news_monthly.csv", index=False)
    print(f"saved news_monthly.csv ({len(mon)} months)")

    life = pd.read_csv(LIFECYCLE_CSV)
    mentions = match_dapps(scored, life)
    mentions.merge(scored[["month", "source", "title", "url"]], left_on="article_idx",
                   right_index=True).to_csv(DATA / "dapp_mentions.csv", index=False)
    print(f"saved dapp_mentions.csv ({len(mentions):,} matches, {mentions['slug'].nunique()} DApps)")

    byk = by_k_table(mon, scored, mentions, life, range(1, args.kmax + 1))
    if OFFCHAIN_BY_K.exists():
        split = pd.read_csv(OFFCHAIN_BY_K)[["slug", "split"]].drop_duplicates("slug")
        byk = byk.merge(split, on="slug", how="left")
        cols = ["slug", "split", "k"] + ALL_FEATURES
        byk = byk[cols]
    byk.to_csv(DATA / "dapp_news_by_k.csv", index=False)
    print(f"saved dapp_news_by_k.csv ({len(byk):,} rows)")
    k3 = byk[byk["k"] == 3]
    print("\nk=3 coverage (non-null share):")
    print(k3[ALL_FEATURES].notna().mean().round(3).to_string())
    print(f"\nDApps with ≥1 mention in window (k=3): {(k3['dapp_log_mentions_window'] > 0).sum()}")


if __name__ == "__main__":
    main()
