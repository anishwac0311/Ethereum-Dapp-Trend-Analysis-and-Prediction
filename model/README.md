# Sustained DApp success model

Predict whether an Ethereum DApp will still have meaningful usage at month 12, using only its first 1 / 3 / 6 months of on-chain activity.

See **[MODEL_REPORT.md](MODEL_REPORT.md)** for literature, label definitions, metrics, and limitations.

## Current model

`final_model.py` blends a soft-label gradient-boosted classifier with a pooled panel AR forecaster, calibrates the result, and gives every DApp a band: **likely_fail**, **uncertain** or **likely_success**.

These results are pooled out-of-fold over the 2021–2024 launch-year folds:

| Checkpoint | ROC-AUC | PR-AUC | Accuracy on confident calls (unseen 2024) |
|---|---|---|---|
| k=3 (month 3) | 0.867 | 0.647 | 89.7% on 87% of DApps; "likely fail" is 96% correct |
| k=6 (month 6) | 0.924 | 0.711 | 94.5% on 91% of DApps |

Success is evaluated across a range of cutoffs (250–5,000 wallets × 15–40% of window max), not only the 1,000-wallet line. `robust_eval.py` does this, and adds a paired bootstrap.

Off-chain inputs, merged on `slug` and `k` by `features.py`:

- [dapp_offchain/](dapp_offchain/README.md): audit, open-source, verification and governance flags
- [news_sentiment/](news_sentiment/README.md): Ethereum news sentiment, ETH price momentum and per-DApp press coverage, plus a live news dashboard (`news_sentiment/live_report.py`)
- `wallet_features.py`: wallet-level window features (acquisition shape, user quality, stickiness, cross-DApp overlap) from the local `dapp_data_v2/dapp_v2.duckdb`; cached in `wallet_features/data/`
- `dapp_tvl/fetch_tvl.py`: daily Ethereum TVL from DeFiLlama, cut at launch + k months; cached in `dapp_tvl/data/`
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
.\.venv\Scripts\python model\robust_eval.py --k 3    # model comparison across the threshold grid
.\.venv\Scripts\python model\final_model.py --k 3 6  # final blend, bands, 2025 scoring
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
| `tables/final_eval_k{3,6}.csv`, `final_bands_k{3,6}.csv` | Final model metrics and confidence bands |
| `tables/final_predictions_launch2025_k{3,6}.csv` | 2025 launches with P(success) and band |
| `artifacts/final_k{3,6}.joblib` | Final blend (HGB, AR, calibrator, band thresholds) |
| `figures/` | ROC/PR, calibration, k-curve, importance, PDP |
