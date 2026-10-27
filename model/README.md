# Sustained DApp success model

Predict whether an Ethereum DApp will still have meaningful usage at month 12, using only its first 1 / 3 / 6 months of on-chain activity.

See **[MODEL_REPORT.md](MODEL_REPORT.md)** for literature, label definitions, metrics, and limitations.

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

## Outputs

| Path | Contents |
|------|----------|
| `tables/dataset_k{1,3,6}.csv` | Features + labels |
| `tables/all_holdout_results.csv` | Holdout metrics |
| `tables/ablations_k3.csv` | Feature ablations |
| `tables/predictions_launch2025_k3_active100.csv` | Ranked 2025 apps with early activity |
| `artifacts/hgb_calibrated_k3.joblib` | Calibrated model |
| `figures/` | ROC/PR, calibration, k-curve, importance, PDP |
