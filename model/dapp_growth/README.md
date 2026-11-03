# DApp growth

How quickly do successful DApps acquire users? Success is the team's `y_sustained_12` rule at k = 3 (see `model/labels.py`).

**Data:** `dapp_data_v2/dapp_panel.csv`, 2020-01 → 2025-12. See **[REPORT.md](REPORT.md)** for findings and **[FEATURES.md](FEATURES.md)** for candidate model features.

## Quick start

```bash
cd model/dapp_growth
pip install pandas numpy scipy statsmodels matplotlib
python script/main.py
```

About 1 minute.

## Sample

| Step | Deploy clock | First-user clock |
|------|-------------:|-----------------:|
| All DApps in the panel | 622 | 622 |
| Launched from 2020, or deploy date unknown | 587 | 587 |
| Has at least one user (`cum_wallets > 0`) | — | 566 |
| Observed 13 months (months 0–12) | **512** | **486** |

- **Launched before 2020 is dropped:** the panel starts in 2020-01, so we cannot see their start; 32 of 35 already had users that month.
- **Deploy clock (512):** month 0 = deploy month. Same DApps as `model/labels.py`; success labels are defined here.
- **First-user clock (486):** month 0 = first month with any wallet, since a DApp can sit unused after deploying. All Q4 analyses use it.

## Main findings

1. **The gap opens early.** By month 6, 82% of successful DApps reach 5K cumulative wallets (vs 9%) and 66% reach 10K (vs 5%).
2. **And never closes.** By month 24 it is 100% vs 16% for 5K and 96% vs 9% for 10K.
3. **Gompertz fits better than logistic**, for 75% of successful DApps, so it is the main growth curve.
4. **Different start, higher ceiling.** Among good fits, successful DApps start with about 560 wallets vs 4 and reach a ceiling of 82K vs 153.
5. **Not faster, but longer.** At the same ceiling the speed r is the same; successful DApps keep growing while the others stop by about month 10.

## Outputs

| Path | Contents |
|------|----------|
| `data/dapp_growth_summary.csv` | One row per DApp, deploy clock: success by k, milestones, wallets, growth |
| `data/dapp_growth_first_user_summary.csv` | Same, first-user clock |
| `data/dapp_growth_curves_{logistic,gompertz}.csv` | Fitted L, r, t0 per DApp |
| `data/dapp_acquisition_features.csv` | Candidate model features (see FEATURES.md) |
| `results/tables/sample_steps.csv` | Sample counts above |
| `results/tables/time_to_{5k,10k}_by_group.csv` | Share at 5K / 10K by months 3, 6, 12, 24 |
| `results/tables/curve_fit_quality.csv` | Logistic vs Gompertz: error, poor fits, AIC preference |
| `results/tables/gompertz_by_group.csv` | L, r, t0 by group, with robustness checks (`logistic_by_group.csv` for the check) |
| `results/tables/fit_quality_by_group.csv` | Good vs poor curve fits: start, early/late gap, speed |
| `results/tables/good_fit_parameters.csv` | Successful vs not, good fits only: month-0 wallets, L, t0, rise months, r at the same L |
| `results/tables/` | Other summary tables |
| `results/figures/` | Figures in REPORT.md, plus fit checks |
