# Sustained DApp success model

Predict whether an Ethereum DApp will still have meaningful usage at month 12, using only its first 1 / 3 / 6 months of on-chain activity.

See **[MODEL_REPORT.md](MODEL_REPORT.md)** for literature, label definitions, metrics, and limitations.

## Current model

`final_model.py` (v3) averages the log-odds of the best pooled forecasters and classifiers from `iterations.py`, calibrates the result, and gives every DApp a band: **likely_fail**, **uncertain** or **likely_success**. The ensemble members are chosen per checkpoint, and its honest score comes from choosing members for each validation year using only the other years.

These results are pooled out-of-fold over the 2021–2024 launch-year folds:

| Checkpoint | ROC-AUC | Grid-mean PR-AUC | Confident calls on unseen 2024 launches |
|---|---|---|---|
| k=3 (month 3) | 0.868 | 0.597 | 91.5% correct on 71% of DApps; "likely fail" is 98% correct |
| k=6 (month 6) | 0.931 | 0.717 | 94.6% correct on 93% of DApps; finds 8 of 9 successes |

There is also a two-stage policy: act on confident month-3 calls and re-score the rest at month 6. On 2024 it covers 95% of DApps with 91.6% accuracy. The full modelling journey (seven steps, every model family tried) is in [MODEL_REPORT.md](MODEL_REPORT.md) and in `dapp presentation 2.pptx` (slides 25–34).

Success is evaluated across a range of cutoffs (250–5,000 wallets × 15–40% of window max), not only the 1,000-wallet line. `robust_eval.py` does this, and adds a paired bootstrap.

Off-chain inputs, merged on `slug` and `k` by `features.py`:

- [dapp_offchain/](dapp_offchain/README.md): audit, open-source, verification and governance flags
- [news_sentiment/](news_sentiment/README.md): Ethereum news sentiment, ETH price momentum and per-DApp press coverage, plus a live news dashboard (`news_sentiment/live_report.py`)
- `wallet_features.py`: wallet-level window features (acquisition shape, user quality, stickiness, cross-DApp overlap) from the local `dapp_data_v2/dapp_v2.duckdb`; cached in `wallet_features/data/`
- `dapp_tvl/fetch_tvl.py`: daily Ethereum TVL from DeFiLlama, cut at launch + k months; cached in `dapp_tvl/data/`
- `user_history_features.py`: brand (earlier versions of the same protocol), time-aware category base rates, ETH and fees per wallet, and users' on-chain history before launch; cached in `wallet_features/data/user_history_by_k.csv`
- `token_incentives/build_token_features.py`: transfers of each DApp's own token from the AWS public Ethereum dataset (airdrop share, own-contract reward share, token recipients among users). The first scan takes about 4 hours and is resumable; the output is cached in `token_incentives/data/`. These features carry signal but did not improve the pooled scores, so the final model does not use them (see the report).

The `no_news*` and `on_chain_plus_news` rows in `tables/ablations_k3.csv` show what the news features add.

## Quick start

```powershell
cd "c:\Users\Anish\Downloads\dapp project"
.\.venv\Scripts\python -m pip install scikit-learn lifelines matplotlib seaborn joblib
# optional: xgboost shap
.\.venv\Scripts\python model\run_all.py
```

Or step by step:

```powershell
.\.venv\Scripts\python model\labels.py
.\.venv\Scripts\python model\features.py
.\.venv\Scripts\python model\train_eval.py
.\.venv\Scripts\python model\predict.py --k 3
```

Current model, step by step (after `labels.py`):

```powershell
.\.venv\Scripts\python model\wallet_features.py      # ~4 min, reads the 10 GB DuckDB; cached
.\.venv\Scripts\python model\dapp_tvl\fetch_tvl.py   # DeFiLlama TVL; cached
.\.venv\Scripts\python model\token_incentives\build_token_features.py  # ~4 h first scan; cached
.\.venv\Scripts\python model\features.py
.\.venv\Scripts\python model\user_history_features.py  # ~2 min; cached
.\.venv\Scripts\python model\robust_eval.py --k 3    # model comparison across the threshold grid
.\.venv\Scripts\python model\iterations.py --k 3 6   # every modelling iteration + nested ensemble (~10 min)
.\.venv\Scripts\python model\final_model.py --k 3 6  # v3 ensemble, bands, two-stage policy, 2025 scoring
.\.venv\Scripts\python model\deck_charts.py          # presentation charts -> figures/deck/
```

## Outputs

| Path | Contents |
|------|----------|
| `tables/dataset_k{1,3,6}.csv` | Features + labels |
| `tables/all_holdout_results.csv` | Holdout metrics |
| `tables/ablations_k3.csv` | Feature ablations |
| `tables/predictions_launch2025_k3_active100.csv` | Ranked 2025 apps with early activity |
| `artifacts/hgb_calibrated_k3.joblib` | Calibrated model |
| `tables/oof_comparison_k3.csv`, `oof_threshold_grid_k3.csv` | Pooled out-of-fold comparison, PR-AUC per cutoff |
| `tables/iterations_k{3,6}.csv`, `iterations_oof_k{3,6}.csv` | Every iteration's metrics (AUC, PR-AUC, grid PR-AUC, accuracy, bootstrap vs v2) and out-of-fold predictions |
| `tables/final_eval_k{3,6}.csv`, `final_bands_k{3,6}.csv` | v3 metrics and confidence bands |
| `tables/final_two_stage.csv` | Month 3 → month 6 policy: coverage, accuracy, successes found |
| `tables/final_predictions_launch2025_k{3,6}.csv` | 2025 launches with P(success) and band |
| `artifacts/final_k{3,6}.joblib` | v3 config (ensemble members, calibrator, band thresholds) |
| `figures/deck/` | Charts used in the presentation |
| `figures/` | ROC/PR, calibration, k-curve, importance, PDP |
