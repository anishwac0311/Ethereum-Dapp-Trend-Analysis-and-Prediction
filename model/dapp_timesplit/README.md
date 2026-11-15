# Time-split and market checks

Does what makes a DApp succeed change with the market it launches into, and does the team model (`model/`) still predict well across time? The team's dataset, features (27 on-chain), models and metrics are used unchanged. k = 3, target `y_sustained_12`.

| Read | For |
|------|-----|
| **[PRESENTATION.md](PRESENTATION.md)** | The three slides, in order |
| **[REPORT.md](REPORT.md)** | The findings: which feature groups matter most in each launch period, by market growth, and by market growth within 2023–24 (coefficients only, no train/test) |
| **[FEATURE_WEIGHTS.md](FEATURE_WEIGHTS.md)** | Feature weights per launch period in detail (REPORT section 1) |
| **[MODEL_CHECKS.md](MODEL_CHECKS.md)** | The training part: the leakage fix, train-and-test rounds at Terra and Dencun, and the size effect per period (main score holdout average precision, AP) |

**Findings (REPORT.md)**

1. **Rules by period.** The team's L2 logistic regression on the 27 standardised features, fitted on each launch period (split at the Terra/UST collapse, 2022-05, and the Dencun upgrade, 2024-03), with 1,000 resamples.
2. **Rules by market growth.** The same fit with DApps split at the median of `launch_eco_growth_3m`, active wallets in the launch month vs 3 months earlier (left out of the fit).
3. **Within the same years.** The market-growth split repeated on 2023–24 launches alone, the only years with both halves.

**Model checks (MODEL_CHECKS.md)**

1. **Leakage fix.** The team trains on 2020–22 launches and tests on 2023–24. A DApp's answer uses months 10–12 (counted from 0), so it is known 12 months after launch, and 2022 launches train on answers from 2023. The fix trains only on DApps whose answer is known before the test starts.
2. **Event rounds.** Stand at a market event, train on what was known then, and test on what launched next.
3. **Size effect.** How strongly early size predicts success among the DApps launched in each period (size-only logistic regression, fitted per period).

```bash
cd model/dapp_timesplit
python script/main.py
```

## Splits (model checks)

Embargo rule for training DApps: launch month + 12 months < test start. Test DApps are not embargoed.

| Split | Train launches | Not used | Test launches |
|------|------|------|------|
| `current` (team) | 2020-01 to 2022-12 | — | 2023-01 to 2024-12 |
| `leakage_fixed` | 2020-01 to 2021-12 | 2022 (67 DApps) | 2023-01 to 2024-12 |
| `round_1` (at Terra) | 2020-01 to 2021-04 | 2021-05 to 2022-04 | 2022-05 to 2024-02 |
| `round_2` (at Dencun) | 2020-01 to 2023-02 | 2023-03 to 2024-02 | 2024-03 to 2024-12 |

## Outputs

| Path | Contents |
|------|----------|
| `data/split_assignment.csv` | Each DApp's launch month, success label, answer month, and role (train / test / unused) in each split |
| `results/tables/split_sizes.csv` | Launch range, DApps and successful DApps per split |
| `results/tables/holdout_scores.csv` | Every model on every split: AP, AUC, 95% bootstrap intervals, base rate |
| `results/tables/leakage_check.csv` | AP and AUC before and after the leakage fix |
| `results/tables/event_rounds.csv` | Scores for rounds 1 and 2 |
| `results/tables/vs_szabo_huberman.csv` | Each learned model's AP minus size only, per split |
| `results/tables/size_effect_by_period.csv` | Size-only slope, odds ratio for 10x wallets, and 95% bootstrap interval per launch period |
| `results/tables/coef_by_period.csv` | Standardised coefficient per feature and period, with 95% interval and share of resamples above 0 |
| `results/tables/size_ranks_by_period.csv` | Rank and coefficient of each size feature in each period |
| `results/tables/coef_ranked_after_dencun.csv` | Features ranked by absolute coefficient after Dencun, with share and cumulative share of all weight |
| `results/tables/coef_groups_by_period.csv` | Each feature group's share of absolute coefficients per period, with 95% interval |
| `results/tables/market_growth_by_month.csv` | Market growth at each launch month (active wallets vs 3 months earlier), DApps and successful DApps launched, and whether it is above the median |
| `results/tables/regime_sizes.csv` | Faster and slower market growth, on all launches and on 2023–24 alone: median, DApps, successful DApps, launch months, shrinking-market DApps and launches per year |
| `results/tables/coef_by_regime.csv` | Standardised coefficient per feature for faster and slower market growth (all launches and 2023–24), with 95% interval and share of resamples above 0 |
| `results/tables/coef_groups_by_regime.csv` | Each feature group's share of absolute coefficients for faster and slower market growth (all launches and 2023–24), with 95% interval |
| `results/figures/` | Figures in PRESENTATION.md, REPORT.md, FEATURE_WEIGHTS.md and MODEL_CHECKS.md |

## Code

- `script/main.py`: builds the team dataset once, runs every split, writes the tables
- `script/splits.py`: the splits and the embargo rule
- `script/evaluate.py`: fits the team's models on one split and scores its test set
- `script/size_effect.py`: size-only logistic regression per launch period
- `script/coef_by_period.py`: standardised coefficients per launch period, with resampling
- `script/coef_by_regime.py`: the same coefficients for faster and slower market growth at launch, on all launches and on 2023–24 alone
- `script/plots.py`: figures, drawn from the saved tables
- `script/config.py`: paths, events and settings
