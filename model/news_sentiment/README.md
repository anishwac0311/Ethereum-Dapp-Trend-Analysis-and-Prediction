# News sentiment

Ethereum news sentiment and market-impact data, in two forms:

1. **Model features.** Leakage-safe news features per DApp and window k, ready to merge on `slug` and `k`, like `dapp_offchain`.
2. **Live analyzer.** A ranked, colour-coded dashboard of the latest Ethereum news, with a research-style summary.

## Files

| File | Rows | Use |
|---|---|---|
| `data/dapp_news_by_k.csv` | 622 DApps × k = 1-9 | Final table for the model |
| `data/news_monthly.csv` | 1 per month, 2019-01 → 2025-12 | Ethereum news environment + ETH price |
| `data/dapp_mentions.csv` | 1 per article–DApp match | Audit trail for DApp coverage features |
| `data/eth_weekly.csv`, `data/eth_monthly.csv` | weekly / monthly | ETH/USD from Kraken |
| `data/live_archive.csv` | grows each live run | Every scored live article, with exact timestamps |
| `data/articles_history.csv`, `data/articles_scored.csv` | ~87k | Raw and scored corpus (not in Git; rebuild with the scripts) |

## Sources

| Source | History | Headline | Date |
|---|---|---|---|
| Ethereum Foundation blog | Full RSS archive | Real | Day |
| Cointelegraph | Monthly article sitemaps | Rebuilt from URL slug | Month |
| The Block | Post sitemaps | Rebuilt from URL slug | Day (in URL) |
| CoinDesk, Decrypt | Live RSS only | Real | Minute |
| ethereum/pm (GitHub) | Open issues | Real | Call date |

CoinDesk's sitemap sits behind a bot checkpoint and Decrypt's post sitemaps return 404, so both are live-only. We do not try to get around either. Slug headlines keep the words of the original headline but lose casing and punctuation. Every row carries `title_source` (`feed` or `url_slug`) so a slug headline is never shown as verbatim. Nothing is generated: every row is a real URL.

## Model features

Window k ends at month k-1, counted in calendar months from the launch month, the same as the on-chain features. No feature uses an article published after month k-1.

| Column | Meaning | Group |
|---|---|---|
| `news_eth_sent` | Mean sentiment (-100…100) of Ethereum news in the window | market |
| `news_eth_sent_wtd` | Same, weighted by market impact | market |
| `news_eth_net_bull` | Bullish share − bearish share of Ethereum news | market |
| `news_eth_attention` | Share of all crypto coverage that is about Ethereum | market |
| `news_hack_rate` | Hack/exploit events per 100 events | market |
| `news_reg_bear_rate` | Negative regulatory events per 100 events | market |
| `news_cat_attention` | Share of coverage about the DApp's category (DeFi, NFT…) | market |
| `news_cat_sent` | Sentiment of that category's coverage | market |
| `news_eth_sent_pre3m` | `news_eth_sent` over the 3 months before launch | market |
| `eth_ret_window` | ETH log return over the window | price |
| `eth_ret_pre3m` | ETH log return over the 3 months before launch | price |
| `eth_vol_window` | ETH annualised volatility in the window | price |
| `dapp_log_mentions_window` | log(1 + articles naming the DApp or its parent) in the window | dapp |
| `dapp_log_mentions_pre6m` | Same, 6 months before launch (pre-launch hype) | dapp |
| `dapp_news_sent_window` | Mean sentiment of those articles; blank if none | dapp |
| `dapp_neg_event_window` | 1 if the DApp was named in a hack or negative regulatory story | dapp |

Notes:

- **Counted once per event.** Articles about the same event are grouped (title overlap within ±3 days, plus a shared named entity for high-impact stories) and only the lead article counts.
- **Market features are time effects.** Every DApp launched in the same month gets the same market and price values. With a time-based holdout (train ≤ 2022, test 2023-24) they can only help if the relationship holds across market regimes. The ablations in `train_eval.py` test this.
- **News ≠ momentum.** Price features are a separate group, so the ablations show whether news adds anything beyond what ETH's price already says.
- **DApp matching** uses the DApp name and its parent protocol, with version and suffix words removed ("Aave V3" → "aave"). Names that are ordinary words ("Loop", "Spark", "Maker") only match their longer form ("makerdao"). Mentions are therefore brand-level: an Aave V3 window also counts news about Aave.

## Effect on the model (k = 3, holdout 2023-24, n = 237, 12% positive)

HGB, primary label `y_sustained_12`, from `tables/ablations_k3.csv`:

| Features | PR-AUC [95% CI] | ROC-AUC | Brier | Precision @10% |
|---|---|---|---|---|
| On-chain + off-chain flags (`no_news`) | 0.577 [0.40, 0.75] | 0.890 | 0.086 | 0.54 |
| + market news only | 0.579 | 0.879 | 0.085 | 0.63 |
| + ETH price only | 0.552 | 0.885 | 0.084 | 0.63 |
| + DApp press coverage only | 0.638 | 0.893 | 0.072 | 0.63 |
| **All (`full`)** | **0.649 [0.47, 0.79]** | 0.885 | **0.071** | 0.63 |

- Nearly all of the gain comes from **DApp press coverage**. `dapp_log_mentions_pre6m` is the 3rd most important feature by permutation importance.
- **Market-wide sentiment and ETH price add almost nothing** on a time-based split. They are the same for every DApp launched in a given month, so they act as regime dummies.
- **The gain is not statistically conclusive.** The confidence intervals overlap and ROC-AUC is flat. The improvement shows up in ranking the top of the list and in calibration.
- **Mentions are brand-level**, so the feature partly measures "this comes from a known team". That is information available before launch, not leakage.

## Scoring

`score.py` is deterministic and offline, so the features can be rebuilt exactly. For each article it produces:

| Field | How |
|---|---|
| `sentiment`, `sentiment_score` | Crypto-finance lexicon with negation (−100…100), with overrides for ETF, regulatory, hack and upgrade events |
| `market_impact` (1-10) | Base impact of the event type (ETF 8, upgrade 7, regulation 6.5, hack 5.5 + size, …), scaled by ETH relevance, reduced for opinion and speculation |
| `time_horizon` | Short (0-48h), medium (2-30d), long (30d+), by event type |
| `confidence` | Number of agreeing cues, minus a penalty for slug headlines and for opinion/speculation |
| `eth_relevance`, `scope` | Ethereum-specific, Ethereum ecosystem, market-wide, or macro |
| `content_type` | Fact, opinion or speculation |
| `novelty` | First report of an event, and how rare the event type is |
| `cues` | The words that drove the score, so it can be checked |

Rank score = 35% impact + 25% |sentiment| + 20% ETH relevance + 10% source credibility + 10% novelty.

A lexicon misreads some headlines (for example "10% gains levy" as positive). For the live report, `--llm` has Claude score each lead article instead and write the reasoning and price implications. The historical features always use the rules, so training data does not depend on an API.

## Run

```bash
cd model/news_sentiment
python fetch_prices.py         # ETH weekly/monthly prices (Kraken)
python fetch_history.py        # 2019-2025 corpus (~20 min first time; cached in data/raw)
python build_features.py       # score, cluster, build dapp_news_by_k.csv (~5 min)
cd ..
python run_all.py              # features.py merges the news columns automatically
```

Live dashboard:

```bash
python live_report.py              # last 7 days → reports/latest.html
python live_report.py --days 3
python live_report.py --llm        # Claude scoring; pip install anthropic, set ANTHROPIC_API_KEY
```

Each live run also appends to `data/live_archive.csv`. Over time this builds a corpus of real, minute-dated headlines that can replace slug headlines when the model is retrained.
