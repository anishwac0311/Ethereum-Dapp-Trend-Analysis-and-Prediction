# Ethereum dApp deep-learning prototype: N-HiTS, DeepAR, DeepSurv

Working prototype for the deep learning layer of *Ethereum dApp Trend Analysis and Prediction*.
Design rationale and how each model maps to the six project questions: `docs/deep_models.md`.

## Run

```bash
pip install -r requirements.txt
# put the 10 CSVs in data/raw/ (names without the drive-download prefix)
python -m src.data.build_forecast_panel        # -> data/processed/forecast_*.parquet
python -m src.data.build_survival_table        # -> data/processed/survival_*.parquet
python -m src.run_forecast                     # default configs, 3 seeds (~2.5 min on 2 CPU cores)
python -m src.tuning.search nhits 12           # Optuna -> configs/nhits_tuned.yaml
python -m src.tuning.search deepar 10          # Optuna -> configs/deepar_tuned.yaml
python -m src.run_forecast --tuned             # evaluate the tuned configs
python -m src.run_survival [--tune]            # DeepSurv + Cox PH (--tune: per-split Optuna search)
python -m src.explore_decline                  # compare decline-event definitions
python -m src.run_forecast_extended            # 6 origins, blends, bootstrap CIs, per-horizon conformal (~15 min)
python -m src.run_survival_calibration         # survival calibration + recalibration (~6 min)
python -m src.run_forecast --smoke             # 40-step pipeline check
```

Settings live in `configs/` (`data.yaml`, `nhits.yaml`, `deepar.yaml`, `deepsurv.yaml`, `*_tuned.yaml`).

## Setup

| Part | Setup |
|---|---|
| Forecasting data | 253 dApps with peak >= 100 monthly wallets and >= 24 months; target `log1p(active_wallets)` |
| Evaluation | rolling origin, 2 non-overlapping windows (cutoffs 2024-12 and 2025-06), 6-month horizon, refit per window, 3,036 forecasts, 3 seeds |
| N-HiTS / DeepAR | static + known-future (`months_since_launch`) + historical covariates; DeepAR uses a Student-t likelihood |
| Baselines | naive last value; global LightGBM (direct multi-horizon) |
| Tuning | N-HiTS / DeepAR on windows that end 2024-12, i.e. before the test period; DeepSurv per outer split using only its train/validation parts |
| Calibration | split-conformal widening of DeepAR's 80% interval, calibrated on the 2024-12 window and scored on the 2025-06 window |
| Extended evaluation | 6 origins 3 months apart (2024-03 ... 2025-06) with a rolling loop (`src/models/rolling.py`) that keeps every dApp existing at each origin; default configs only, because the tuned ones were tuned on windows ending 2024-12 |
| DeepSurv | events `decline`, `reach_1k`, `reach_10k`; 5 repeated stratified 60/15/25 splits; Cox PH baseline |

## Results

Forecast error on log1p(active wallets), lower is better (N-HiTS and DeepAR rows are 3-seed ensembles):

| Model | MAE, default config | MAE, tuned config | vs naive (default / tuned) |
|---|---|---|---|
| Naive | 0.511 | 0.511 | – |
| LightGBM | 0.492 | 0.492 | +3.8% |
| N-HiTS | **0.473** | 0.477 | +7.5% / +6.8% |
| DeepAR (median) | 0.505 | 0.493 | +1.2% / +3.6% |

- Tuning helped on the tuning windows (N-HiTS 0.466 -> 0.459, DeepAR pinball 0.553 -> 0.524) but **did not transfer to N-HiTS on the test windows**: the difference is within seed noise (seed std 0.001-0.008). It did help DeepAR, which now matches LightGBM.
- Seed ensembling gives N-HiTS a small gain over single seeds (0.473 vs 0.477 mean).
- On these two windows LightGBM looked better for dApps under 12 months old (0.845 vs 0.93-0.95), but the 6-origin evaluation below shows they are tied there (0.753 vs 0.750), so treat that as window noise.
- **Caveat on the "vs naive" column:** the +7% N-HiTS gain over naive comes mostly from the 2024-12 origin. Across 6 origins it is +4.5%, and in 2025-03 and 2025-06 N-HiTS is level with or slightly worse than naive (see the per-origin table below).

DeepAR 80% interval, later window only (n = 1,518):

| | Coverage | Mean width (log units) |
|---|---|---|
| Raw (3-seed ensemble, tuned) | 0.61 | 0.94 |
| After conformal widening (q = 0.30) | **0.83** | 1.48 |

Coverage after widening varies with horizon (0.92 at 1 month, 0.74 at 6 months): a per-horizon q is the obvious next refinement.

Survival, C-index on held-out splits (mean over 5 splits):

| Event | Features | DeepSurv | DeepSurv tuned | Cox PH |
|---|---|---|---|---|
| `reach_1k` | static | 0.671 | 0.667 | 0.676 |
| `reach_1k` | early (optimistic: window overlaps outcome) | 0.874 | 0.879 | 0.873 |
| `reach_10k` | static | 0.707 | 0.738 | 0.745 |
| `decline` | static | 0.540 | 0.530 | 0.539 |
| `decline` | early | 0.523 | 0.539 | 0.566 |

- DeepSurv matches Cox PH after tuning but does not beat it at n = 622.
- **`decline` is not predictable from launch-time or early-life features.** Five definitions (raw or 3/6-month smoothed; 25% or 50% thresholds; `results/decline_definition_comparison.csv`) all give C-index 0.51-0.57. The default is the 3-month smoothed 50% version because one noisy month cannot trigger it, not because it predicts better. Answering Q2 needs post-peak dynamics (time-varying covariates or landmark models).

## Extended forecast evaluation (6 origins, default configs, 3-seed ensembles, n = 8,928 forecasts)

| Model | MAE | RMSE |
|---|---|---|
| Naive | 0.499 | 0.759 |
| LightGBM | 0.510 | 0.736 |
| **N-HiTS** | **0.477** | 0.728 |
| DeepAR (median) | 0.522 | 0.810 |
| N-HiTS + LightGBM (equal weights) | 0.478 | **0.709** |
| N-HiTS + LightGBM + DeepAR | 0.474 | 0.717 |

Paired MAE differences with a 95% bootstrap CI that resamples whole dApps (negative = first model better):

| Comparison | Difference | 95% CI |
|---|---|---|
| N-HiTS vs LightGBM | -0.033 | [-0.049, -0.017] |
| N-HiTS vs Naive | -0.022 | [-0.033, -0.011] |
| N-HiTS+LightGBM vs N-HiTS | +0.002 | [-0.006, +0.010] |
| 3-model blend vs 2-model blend | -0.005 | [-0.012, +0.002] |

MAE by forecast origin (the gain over naive is not stable over time):

| Origin | Naive | N-HiTS | LightGBM |
|---|---|---|---|
| 2024-03 | 0.554 | 0.522 | 0.559 |
| 2024-06 | 0.494 | 0.467 | 0.511 |
| 2024-09 | 0.509 | 0.497 | 0.562 |
| 2024-12 | 0.553 | 0.474 | 0.489 |
| 2025-03 | 0.419 | 0.432 | 0.446 |
| 2025-06 | 0.470 | 0.471 | 0.495 |

- N-HiTS is the best single model and clearly beats LightGBM, which also loses its edge on young dApps (<12m: 0.750 vs 0.753).
- **Blending with LightGBM does not lower MAE** (no significant change); it lowers RMSE (0.728 to 0.709), i.e. it trims the largest misses. An age-bucket weighted blend fitted on the first three origins did no better than equal weights on the last two (0.4482 vs 0.4487).
- The last two origins contain no dApps under 12 months old, so the "<12m" blend weight is never used there.

DeepAR 80% interval on the last two origins, calibrated on the first three (nothing is fitted on data it is scored on):

| Method | Coverage | Mean width (log units) |
|---|---|---|
| Raw (default config) | 0.64 | 0.98 |
| Conformal, one q for all horizons | 0.86 | 1.63 |
| **Conformal, one q per horizon** | 0.86 | 1.66 |

Per-horizon calibration fixes the uneven coverage: 0.85-0.88 at every horizon, versus 0.94 at 1 month falling to 0.76 at 6 months with a single q. Overall coverage sits above the 0.80 target because the calibration origins (2024) were harder than the scored ones (2025): naive MAE 0.52 against 0.44.

## Survival calibration

Models are fit on the training part, recalibrated on the validation part (cloglog Cox, slope and level fitted per time point) and scored on the test part, mean over 5 splits. Averaged over the three time points:

| Event / features | Model | Brier raw -> recalibrated | ICI raw -> recalibrated |
|---|---|---|---|
| `reach_1k` static | DeepSurv | 0.154 -> 0.154 | 0.056 -> 0.062 |
| `reach_1k` early | DeepSurv | 0.083 -> 0.087 | 0.042 -> 0.059 |
| `reach_10k` static | DeepSurv | 0.107 -> 0.107 | 0.039 -> 0.045 |
| `decline` static | DeepSurv | 0.207 -> 0.208 | 0.101 -> 0.108 |
| `decline` early | DeepSurv | 0.213 -> **0.205** | 0.116 -> **0.097** |

(ICI = mean absolute gap between predicted and Kaplan-Meier observed risk across four risk bins; Cox PH shows the same pattern, full table in `results/survival_calibration.csv`.)

- **The `reach_*` models are already calibrated** (fitted slopes 0.8-1.0, gaps of a few points), so recalibration only adds noise from fitting on about 90 validation dApps. Leave them as they are.
- **Recalibration helps only `decline`/early DeepSurv**, where predicted risk was 8-10 points too low at 4 and 6 months and the correction recovers about half of that.
- `decline` slopes are far from 1 (0.27 to 0.88 for DeepSurv, negative for Cox on early features): the predictions have little real spread to calibrate, which agrees with the low C-index.

## Caveats

- The first tables use only 2 evaluation windows; prefer the 6-origin evaluation, whose neighbouring windows overlap in time (cluster bootstrap by dApp does not account for that).
- Tuned forecast configs were tuned on windows ending 2024-12, so the extended evaluation uses default configs only.
- The dApp universe (peak >= 100 wallets, >= 24 months of history) is chosen using the full sample, which is a mild look-ahead shared by every model.
- The survival calibration sets here are small (about 80-160 test dApps per split), so single-split differences are noisy.
- `tvl` is a single end-of-data snapshot, so it is excluded from all models.
- Median imputation of early features is computed over all dApps (minor leakage from imputation only).
- Decline definitions were compared on the same splits used for reporting; since none helped, this does not change any conclusion.
- Predictions beyond 2025-12 need a `futr_df` with future `months_since_launch`; the prototype only evaluates on held-out history.
- `pycox` needs a one-line `scipy.integrate.simps` shim on current scipy (in `src/evaluation/survival_metrics.py`).

## Layout

```
configs/         data / model settings, *_tuned.yaml written by the searches
src/data/        build_forecast_panel.py, build_survival_table.py, splits.py
src/models/      nhits.py, deepar.py, deepsurv.py, baselines.py, survival_baselines.py, rolling.py
src/evaluation/  forecast_metrics.py, survival_metrics.py, calibration.py, survival_calibration.py
src/tuning/      search.py
src/             run_forecast.py, run_forecast_extended.py, run_survival.py, run_survival_calibration.py, explore_decline.py
results/         metrics CSVs (_default / _tuned), predictions, tuning trials, DeepSurv risk scores and permutation importance
docs/            deep_models.md
```
