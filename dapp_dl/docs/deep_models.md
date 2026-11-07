# Deep Learning Models: N-HiTS, DeepAR, DeepSurv

Documentation for the deep learning layer of **Ethereum DApp Trend Analysis and Prediction**. It covers where each model fits, what data it uses, how the code is organized, and how results are evaluated.

---

## 1. Why these three models

The project's focus is regression and prediction of dApp user counts, plus lifecycle questions (sustained vs. flash apps, acquisition speed). The three models split the work as follows.

| Model | Role | Question it answers | Primary data |
|---|---|---|---|
| **N-HiTS** | Point forecast of monthly active wallets | How many users will a dApp or category have in the next 1-12 months? | `dapp_panel.csv` |
| **DeepAR** | Probabilistic forecast (full predictive distribution) | How uncertain is that forecast, and what is the risk of collapse? | `dapp_panel.csv` |
| **DeepSurv** | Time-to-event modeling with censoring | How fast do dApps reach 1k/10k wallets, and how long do they survive? | `dapp_lifecycle.csv` |

How they complement each other:
- N-HiTS gives the best point accuracy and is the main benchmark against mixed-effects and GARCH models.
- DeepAR adds calibrated uncertainty, which is the natural counterpart to hierarchical Bayesian and GARCH-style volatility work.
- DeepSurv handles the fact that many dApps are still alive at the end of the data (right-censoring), which regression on lifetime would handle incorrectly.

### Mapping to the six project questions

| # | Question | Models used |
|---|---|---|
| 1 | Category growth/decline | N-HiTS and DeepAR on aggregated category series (`category_month.csv`) |
| 2 | Sustained vs. flash apps | DeepSurv (time to death/decline), plus forecast trajectories |
| 3 | Activity concentration | Not directly modeled; concentration features (`top10_wallet_share`, HHI) feed the forecasters as covariates |
| 4 | User acquisition speed | DeepSurv with event = reaching 1k / 10k wallets |
| 5 | User retention | Retention features as covariates; cohort curves handled separately |
| 6 | Pre-adoption dynamics | Static covariates (contracts, `first_deployed`, parent protocol) in all three models |

---

## 2. Proposed repository structure

```
Ethereum-Dapp-Trend-Analysis-and-Prediction/
├── data/
│   ├── raw/                      # the 10 CSVs as downloaded
│   └── processed/                # model-ready tables (parquet)
├── src/
│   ├── data/
│   │   ├── build_forecast_panel.py   # dapp_panel -> long format (unique_id, ds, y, covariates)
│   │   ├── build_survival_table.py   # dapp_lifecycle -> (duration, event, features)
│   │   └── splits.py                 # time-based and dApp-based splits
│   ├── models/
│   │   ├── nhits.py                  # N-HiTS training + prediction
│   │   ├── deepar.py                 # DeepAR training + sampling
│   │   ├── deepsurv.py               # DeepSurv training + risk/survival curves
│   │   └── baselines.py              # naive, seasonal naive, LightGBM, mixed-effects, GARCH, Cox PH
│   ├── evaluation/
│   │   ├── forecast_metrics.py       # MASE, sMAPE, RMSE on log scale, pinball, CRPS, coverage
│   │   └── survival_metrics.py       # C-index, integrated Brier score, time-dependent AUC
│   └── tuning/
│       └── search.py                 # Optuna search spaces per model
├── configs/
│   ├── nhits.yaml
│   ├── deepar.yaml
│   └── deepsurv.yaml
├── notebooks/                    # exploration and figures
├── results/                      # metrics tables, predictions, figures
└── docs/
    └── deep_models.md            # this file
```

Suggested libraries: `neuralforecast` (N-HiTS, DeepAR), `pycox` + `torchtuples` (DeepSurv), `optuna` (tuning), `lifelines` (Cox baseline), `lightgbm` (baseline).

---

## 3. Data flow

```
dapp_panel.csv ──► build_forecast_panel ──► N-HiTS ──┐
                                        └─► DeepAR ──┼─► forecast_metrics ─► results/
dapp_lifecycle.csv ► build_survival_table ► DeepSurv ┴─► survival_metrics ─► results/
dapp_static.csv ───► static covariates for all models
category_month.csv ► category-level forecasts (Q1)
```

---

## 4. Forecasting models (N-HiTS and DeepAR)

### 4.1 Shared data preparation

Source: `dapp_panel.csv` (about 24k dApp-month rows).

- **`unique_id`**: `slug`
- **`ds`**: `month`
- **`y`**: `log1p(active_wallets)`. The log transform stabilizes the heavy-tailed scale across dApps. Metrics are reported on both log and original scales.
- **Static covariates**: `category_group`, `has_token`, `n_contracts` (log). `tvl` is excluded by default because it is a single end-of-data snapshot per dApp (it would leak future information); `parent_protocol` is a later extension (embedding or target encoding).
- **Known-future covariates**: `months_since_launch`, calendar month.
- **Historical covariates** (observed only up to the forecast origin): `new_wallets`, `tx_per_wallet`, `retention_prev_month`, `top10_wallet_share`, `avg_n_protocols_in_tx`, `gas_used` (log).
- Robustness variant: repeat with `active_wallets_ex_heavy` as the target to check that results are not driven by heavy users.

Data issues to handle:
- dApps have different launch dates and lengths, so the panel is unbalanced. Both libraries accept this, but very short series (below input window + horizon) must be dropped or handled separately.
- Gaps in months: fill with explicit zeros only if inactivity is meant; otherwise mark as missing.
- Set `months_since_launch` carefully so future values are computable without leakage.

### 4.2 Validation scheme

- **Time split (primary)**: train on months up to T, validate on T+1 to T+h, test on the final h months. Use rolling-origin cross-validation (`cross_validation` in neuralforecast) with 3-4 windows.
- **Cold-start split (secondary)**: hold out a set of dApps entirely (by launch cohort) to test generalization to new apps, which links to Q6.
- Horizons: 1, 3, 6 and 12 months.

### 4.3 N-HiTS

**What it is**: a stack of MLP blocks that forecast at different temporal resolutions (via pooling on the input and interpolation on the output), good for long horizons and trend plus seasonality structure.

**Why it fits**: one global model is trained across all dApps, so it borrows strength across series, which matters because individual dApp histories are short. It is fast, and strong on long horizons.

**Configuration (starting point, `configs/nhits.yaml`)**
- `input_size`: 6-12 months
- `h`: 12
- `n_blocks`, `mlp_units`: tune
- `n_pool_kernel_size` / `n_freq_downsample`: tune
- Loss: MAE or Huber on the log scale
- `futr_exog_list`: `months_since_launch`
- `hist_exog_list`: historical covariates above
- `stat_exog_list`: static covariates above
- Early stopping on validation loss

**Outputs**: point forecasts per dApp-month, saved to `results/nhits_predictions.parquet`.

**Limitations**: point forecasts only. Use DeepAR (or N-HiTS with a quantile/MQLoss) for intervals.

### 4.4 DeepAR

**What it is**: an autoregressive RNN that outputs the parameters of a probability distribution at each step. Forecast paths come from sampling.

**Why it fits**: gives prediction intervals and lets you ask risk questions (probability that a dApp falls below a threshold within 6 months). It is the neural counterpart to hierarchical Bayesian and GARCH-type modeling.

**Configuration (`configs/deepar.yaml`)**
- Likelihood: Student-t on `log1p(active_wallets)` (robust to outliers). Alternatives: negative binomial on raw counts, which needs no log transform but is sensitive to scale.
- `lstm_hidden_size`, `lstm_n_layers`: tune
- `trajectory_samples`: 100-500
- Same exogenous lists as N-HiTS

**Outputs**: quantiles (10/50/90) and samples, saved to `results/deepar_predictions.parquet`.

**Limitations**: autoregressive error accumulation at long horizons, and slower training than N-HiTS.

### 4.5 Forecast evaluation

| Metric | Applies to | Notes |
|---|---|---|
| MASE | N-HiTS, DeepAR (median) | Scaled against naive forecast |
| RMSE / MAE (log scale) | all | Main point metric |
| sMAPE | all | Report with caution for near-zero counts |
| Pinball loss, CRPS | DeepAR | Quantile and distribution quality |
| 80% interval coverage | DeepAR | Should be close to 0.80 |

**Baselines to beat**: naive last value, seasonal naive, LightGBM with lag features, a mixed-effects model, and GARCH on residuals or volatility. Report per category and by `months_since_launch` bucket (young vs. mature dApps), since errors differ a lot between them.

---

## 5. Survival model (DeepSurv)

### 5.1 What it is

DeepSurv is a Cox proportional-hazards model whose linear risk function is replaced by a neural network. It outputs a relative risk score per dApp and, with a baseline hazard estimate, full survival curves. Implemented via `pycox` (`CoxPH`).

### 5.2 Why it fits

- Handles **right-censoring** correctly: dApps still active at the end of the data are not treated as having a known lifetime.
- Learns nonlinear interactions among early-life features without manual specification.
- Gives interpretable outputs: survival curves and risk rankings for sustained-vs-flash comparisons.

### 5.3 Data preparation (`build_survival_table.py`)

Source: `dapp_lifecycle.csv` (622 dApps), joined with `dapp_static.csv` if needed.

**Features (early-life only, to avoid leakage)**: `early_retention`, `early_new_wallet_share`, `early_tx_per_wallet`, `early_gas_per_tx`, `early_whale_share`, `early_prior_app_share`, `n_contracts` (log), `has_token`, `category_group` (one-hot), `launch_year`. `tvl` is excluded (end-of-data snapshot). The early window is roughly the first 3 months of life, so for `reach_*` events it can overlap the outcome and results with `early` features are optimistic; the prototype reports a `static` (launch-time only) run alongside.

**Do not use** as features: `peak_wallets`, `months_to_peak`, `decay_ratio`, `wallets_12m_after_peak`, `months_active`, `lifecycle_label`, since these are computed from the outcome period.

**Event definitions** (implemented in `build_survival_table.py`; durations are in months, shifted by +1 so all are > 0):

| Model | Clock starts | Event | Question |
|---|---|---|---|
| `decline` | peak month | first later month in which the 3-month trailing mean of active wallets is below 50% of its peak (only dApps with peak >= 100 wallets) | Q2 |
| `reach_1k` | launch | cumulative unique wallets reach 1,000 (identical to `months_to_1k`) | Q4 |
| `reach_10k` | launch | cumulative unique wallets reach 10,000 (identical to `months_to_10k`) | Q4 |

Note: `months_to_1k`, `months_to_10k` and `months_to_half_peak_cum` in `dapp_lifecycle` all measure *cumulative* reach, not decline, so the decline event is built from the monthly panel.

Censoring time for non-events is the last observed month (end of data, 2025-12).

### 5.4 Caveats

- With 622 dApps and censoring, the effective number of events may be small. Use strong regularization (dropout, weight decay, small network) and repeated cross-validation.
- The proportional hazards assumption can be tested with a Cox baseline (`lifelines` `check_assumptions`). If it fails, consider DeepHit (also in `pycox`) as a follow-up.
- Early-feature windows need a consistent definition (for example, first 3 months). dApps with fewer observed months than the window must be excluded or handled explicitly.

### 5.5 Configuration (`configs/deepsurv.yaml`)
- Network: 2 hidden layers of 16-64 units, batch norm, dropout 0.1-0.4
- Optimizer: Adam, lr tuned 1e-4 to 1e-2
- Early stopping on validation partial log-likelihood
- Stratified split by event indicator and category

### 5.6 Evaluation

| Metric | Notes |
|---|---|
| Concordance index (C-index) | Ranking quality; compare against Cox PH |
| Integrated Brier score | Calibration over time |
| Time-dependent AUC | At 6, 12, 24 months |
| Kaplan-Meier curves by predicted-risk tercile | Visual check that risk groups separate |

**Baselines**: Cox PH (`lifelines`), Random Survival Forest, and gradient-boosted survival (optional).

### 5.7 Outputs
- `results/deepsurv_risk_scores.parquet`: per-dApp risk score
- `results/deepsurv_survival_curves.parquet`: per-dApp survival probabilities by month
- Figures: KM curves by risk group, permutation feature importance

---

## 6. Hyperparameter tuning

Use Optuna with the validation scheme above. Suggested search spaces:

| Model | Parameters |
|---|---|
| N-HiTS | `input_size` {6, 9, 12}, `n_blocks`, `mlp_units`, pooling kernel sizes, `learning_rate` (log), `dropout` |
| DeepAR | `lstm_hidden_size` {32, 64, 128}, `lstm_n_layers` {1, 2}, `learning_rate`, `dropout`, likelihood {Student-t, NegBin} |
| DeepSurv | hidden units, depth, dropout, weight decay, learning rate, batch size |

Fix random seeds, average over 3-5 seeds for final numbers, and log everything under `results/`.

---

## 7. Connecting results across models

1. **Forecast + risk**: DeepAR's probability of falling below a threshold can be compared with DeepSurv's decline probability for the same dApp-horizon as a consistency check.
2. **Early signal analysis**: compare which early features matter for N-HiTS accuracy (cold-start error) and for DeepSurv risk (permutation importance).
3. **Category views**: aggregate dApp forecasts to category level and compare with direct category forecasts from `category_month.csv` (Q1).

---

## 8. Suggested implementation order

1. `build_forecast_panel.py` and baselines (naive, LightGBM) to establish reference numbers.
2. N-HiTS with covariates, rolling-origin CV.
3. DeepAR using the same panel and splits.
4. `build_survival_table.py`, Cox PH baseline, then DeepSurv.
5. Tuning, multi-seed runs, and result tables for the 2-slide summary.

---

## 9. Prototype findings

See `README.md` for the numbers. In short: N-HiTS is the best single forecaster (about 4.5% better than naive across 6 rolling origins, but level with naive in the two most recent ones); blending with LightGBM lowers RMSE but not MAE; DeepAR's 80% intervals reach nominal coverage after per-horizon split-conformal widening; DeepSurv matches but does not beat a Cox PH baseline; the `reach_*` survival predictions are already well calibrated and recalibration does not help; and time-to-decline is not predictable from launch-time or early-life features under any definition tried, so Q2 needs post-peak dynamics rather than a better event definition.
