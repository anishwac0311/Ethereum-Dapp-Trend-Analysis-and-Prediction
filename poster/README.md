# Poster

Group 9 poster: *Ethereum DApp Trend Analysis and Popularity Prediction*, built on the UCI template (32 × 24 in, landscape).

- `poster_layout.html`: layout mock-up on the template's box positions (1 in = 60 px).
- `figures/make_figs.py`: the one script for every poster figure. Add each new figure as a function and call it in `__main__`.

```bash
python3 poster/figures/make_figs.py
```

## Where each poster item comes from

Every path below is on this branch.

| Poster item | Fig. | Source | Status |
|---|---|---|---|
| Data funnel 1,816 → 676 → 622 → 547 → 512 | 1 | `dapp_data_v2/protocols.csv`, `dapp_data_v2/dapp_static.csv`, `dapp_data_v2/dapp_lifecycle.csv` | To do |
| Fair-testing folds (2020–24) | 2 | Drawn from the fold design in `model/dapp_timesplit/results/tables/split_sizes.csv` | To do |
| Q1 categories: DEX grows, Infrastructure −42% | 3 | `dapp_data_v2/category_month.csv` | To do |
| Q2 flash and fade: 68%, peak ~month 3, keeps ~6% | 4 | `eda/tables/03_trajectories_normalized.csv`, `eda/tables/trajectory_clusters.csv` | Done: `q2_wallets_since_launch.png` |
| Q3 top-10 share of wallets | 5 | `dapp_data_v2/concentration_month.csv` | Done: `q3_top10_share.png` |
| Q4 months to 1,000 wallets: 1 vs. 2 | 6 | `eda/tables/04_median_time_to_threshold.csv` | To do |
| Q5 retention: 17% → 3% | 7 | `dapp_data_v2/cohort_retention.csv` | Done: `q5_retention_curve.png` |
| Q6 retention near 10K wallets: 46–50% vs. 28–44% | 8 | `eda/tables/05_event_checkpoints.csv` | To do |
| Press before launch: 45% vs. 12% | 9 | `model/news_sentiment/data/dapp_news_by_k.csv`, `model/dapp_offchain/data/dapp_offchain_by_k.csv` | To do |
| Market shift: size weight 27% → 19% | 10 | `model/dapp_timesplit/results/tables/coef_groups_by_regime.csv` | To do |
| Final model scoreboard, 98% / 94.6%, 0.71–0.77 | table | `model/README.md`, `model/MODEL_REPORT.md`, `model/final_model.py`, `model/deck_charts.py` | Numbers on poster |
| Dashboard QR | — | `ethereum-dapp-trends.vercel.app` | Done |

## Numbers to recheck before printing

- Q3: the top-10 share runs 68–87%; it sits inside 70–80% only from 2022 on.
- Q6: write the answer as a range, 46–50%, not 46% → 50%.
