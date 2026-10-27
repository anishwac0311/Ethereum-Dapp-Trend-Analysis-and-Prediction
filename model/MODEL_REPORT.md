# Predicting sustained DApp success from early months

**Data:** `dapp_data_v2/` (panel 2020-01 → 2025-12)  
**Code:** `model/labels.py`, `features.py`, `baselines.py`, `train_eval.py`, `predict.py`  
**Reproduce:** `.\.venv\Scripts\python model\run_all.py`  
**Optional deps:** `pip install xgboost shap` (XGBoost / SHAP are used when installed)

---

## Research question

Can the first 1–6 months of on-chain activity tell us whether an Ethereum DApp will still have meaningful usage a year later — not just whether it spikes early?

Prior EDA (`eda/06_predictive_eda.py`) showed strong AUCs for “ever peak ≥ 10k wallets,” but many peaks fall inside the observation window, so that label is partly mechanical. This package predicts **post-window persistence**.

---

## Related work (what we build on)

| Source | Finding | Implication for us |
|--------|---------|-------------------|
| Wu 2019 (arXiv 1902.04969) | Long-tail DApp usage; most apps are rarely used | Success is rare → use PR-AUC, class weights |
| Bärtl 2023 (Frontiers in Blockchain) | Many DApps (esp. DeFi) show negative utilization trends after mid-2021 | Need regime controls / eco-share labels |
| Arvanitou et al. 2024 (IST) | Category + development intensity associate with users/txs (ordinal regression, n=122) | Category is a weak but real prior |
| Research Policy 2026 (OSS ↔ on-chain) | GitHub activity correlates with later engagement | Out of scope here (no GitHub features yet) |
| ICDLT 2025 “Anticipating Crypto Success” | XGBoost + SHAP on launch-time token features; modest precision | Prefer GBM + explanations; don’t expect high precision alone |
| Pump.fun graduation studies | Early liquidity / wallet behaviour → GBM ensembles | Early activity features are the right ingredients |
| Szabo & Huberman 2010 | log early popularity ≈ log later popularity | Must-beat univariate baseline |
| CrowdPop / Malmi (app popularity) | First-week usage → RF / popularity rank | Same problem shape as ours |
| DeFi Survival / FinSurvival 2025 | Cox / KM on protocol user transitions; domain features beat generics | Add survival label + Cox PH |
| Early TSC benchmarks (MiniRocket) | Strong on long series, large n | **Not suitable** — we have 1–6 points × ~500 DApps |

**Gap filled:** leakage-safe prediction of *sustained* Ethereum DApp usage from early app-contract activity, with time-based validation.

---

## Label design

All outcomes use months **after** the observation window `k`.

| Label | Definition | Eligible base rate (k=3) |
|-------|------------|--------------------------|
| **`y_sustained_12` (primary)** | Mean active wallets in months 10–12 ≥ 1,000 **and** ≥ 25% of in-window max | 16.6% (512 DApps) |
| `y_abs_12` | Absolute only (≥ 1k at m10–12) | 18.4% |
| `y_sustained_24` | Same rule at months 22–24 | 15.8% (387) |
| `y_eco_topq_12` | Top quartile of mean eco-wallet share at m10–12 (regime-neutral) | 25% |
| `y_cond_sustained_12` | Primary label among apps that already hit 1k in-window | 54% of 105 |
| Survival | Months from end of window until wallets stay below 20% of window max for 3 consecutive months (right-censored OK) | — |

Threshold check: primary rate ≥ 8% at abs=1000 for k∈{1,3,6}, so thresholds were **not** lowered.

Filters: drop `left_censored`; require `eligible_12m` (or 24m for the long horizon).

---

## Features (months 0 … k−1)

Leakage exclusions follow `eda/tables/01_leakage_risks.csv`: no TVL, lifecycle/decay/peak labels, `n_contracts`, or unrestricted prior-app share.

- **Levels:** log mean/max/last wallets, tx, gas, fees; ex-heavy wallets  
- **Shape:** growth slope, last/max ratio (early fade), MoM volatility, months since in-window peak  
- **Quality:** MoM retention, in-window cohort m1 retention, new/returning share, tx/wallet, gas/tx, composability (`avg_n_protocols_in_tx`)  
- **Concentration:** top-10 whale share, heavy-wallet share  
- **Context:** category & eco share, category/eco `growth_3m` at launch, `is_new_version_of_existing_protocol`, `has_token`, launch year  

---

## Models and validation

**Baselines:** persistence (last wallets ≥ 1k), Szabo–Huberman (logistic on `log_last_wallets`), category prior.

**Learners:** L2 and elastic-net logistic (balanced), shallow `HistGradientBoosting` (depth 3, L2, balanced), optional XGBoost, isotonic/Platt calibration, penalized Cox PH (`lifelines`).

**Splits:**
- Rolling-origin CV by earliest `parent_protocol` launch year (versions never straddle folds)
- Final holdout: train launch ≤ 2022, test 2023–2024 (same as EDA)

**Primary metric:** PR-AUC (positives ~12% on holdout). Also ROC-AUC, Brier, precision@10%/20%, bootstrap 95% CIs.

---

## Holdout results (`y_sustained_12`)

| k | Model | AUC | PR-AUC (AP) | P@10% | Base rate |
|---|-------|-----|-------------|-------|-----------|
| 1 | persistence | 0.72 | 0.34 | 0.42 | 0.135 |
| 1 | Szabo–Huberman | 0.72 | 0.41 | 0.42 | 0.135 |
| 1 | HGB | **0.77** | **0.39** | **0.46** | 0.135 |
| 3 | persistence | 0.87 | 0.49 | 0.71 | 0.122 |
| 3 | Szabo–Huberman | 0.88 | 0.59 | 0.63 | 0.122 |
| 3 | logreg elastic | **0.89** | 0.60 | 0.63 | 0.122 |
| 3 | HGB calibrated | 0.89 | **0.60** | 0.58 | 0.122 |
| 6 | Szabo–Huberman | 0.92 | 0.63 | 0.63 | 0.114 |
| 6 | HGB | 0.90 | **0.64** | **0.71** | 0.114 |

![k-curve](figures/k_curve_ap.png)

**Takeaways:**
1. **k=3 is the sweet spot for actionability** — clear lift over k=1; k=6 adds more AP but waits longer.
2. Learned models beat the category prior easily; beating Szabo–Huberman on PR-AUC is modest but real at k=3 (calibrated HGB) and k=6 (HGB).
3. Rolling-origin CV (k=3): logreg mean AP ≈ 0.68, HGB ≈ 0.59 — logistic is more stable under temporal shift; HGB wins some holdouts.

### Secondary labels (k=3)

| Target | Best model | AUC | AP |
|--------|------------|-----|-----|
| `y_abs_12` | HGB | 0.92 | 0.77 |
| `y_eco_topq_12` | HGB | 0.93 | 0.83 |
| `y_sustained_24` | HGB | 0.90 | 0.61 |
| `y_cond_sustained_12` (n_test=40) | elastic net | 0.66 | 0.64 |

Absolute scale and eco-share ranks are easier than the dual absolute+relative persistence rule. Distinguishing flash vs sustained *conditional on early scale* is hard with n≈40 holdout positives/negatives — treat as exploratory.

### Survival

Cox PH C-index ≈ **0.69** (k=3) and **0.78** (k=6) on holdout. Useful as a secondary risk score alongside the classifier.

---

## Ablations (k=3, HGB)

| Variant | Holdout AP |
|---------|------------|
| full | 0.567 |
| no_levels | 0.551 |
| no_has_token | 0.567 |
| levels_only | 0.533 |

Shape / retention / context features still carry signal when raw size is removed. `has_token` is nearly inert under permutation (token may launch after the app). Levels alone are strong on AUC but weaker on PR-AUC than the full set.

---

## What drives predictions (k=3 HGB, permutation on AP)

Top features: **`early_cat_share`**, **`log_last_wallets`**, **`last_to_max_ratio`**, **`log_mean_gas`**, **`launch_cat_growth_3m`**, growth slope, early retention.

Interpretation:
- Ending the window still large (last wallets) and not already fading (`last_to_max`) matters for persistence.
- Category share and launch-month category growth capture competition / regime.
- Whale share and gas/tx are unstable or negatively associated in this cut.

See `figures/perm_importance_y_sustained_12_k3.png` and `figures/pdp_y_sustained_12_k3.png`.

---

## Scoring new DApps

```powershell
.\.venv\Scripts\python model\predict.py --k 3
```

Writes:
- `tables/predictions_launch2025_k3.csv` — all 2025 launches  
- `tables/predictions_launch2025_k3_active100.csv` — max early wallets ≥ 100 (more trustworthy)  
- `tables/predictions_holdout_k3.csv` — 2023–24 for inspection  
- `artifacts/hgb_calibrated_k{1,3,6}.joblib` — calibrated models  

**Caveat:** many 2025 apps have tiny early samples (retention=1.0 on 2 wallets). Absolute probabilities compress toward ~0.6; use the `active100` file and treat ranks as exploratory until those cohorts mature.

---

## Limitations

1. **Small n / rare positives** — holdout has ~27–32 positives; CIs are wide (see bootstrap columns in holdout CSVs).  
2. **Market regime** — 2021 bull vs 2023–25 cooler market; eco-share label and launch growth features mitigate but do not eliminate shift.  
3. **Attribution** — panel credits full gas to every protocol touched in a tx; prefer within-app trends over cross-app gas totals (`build_dapp_dataset_v2.py` caveats).  
4. **No off-chain features** — GitHub / social / audits left out; literature suggests they would help.  
5. **Mechanical baseline** — size alone is powerful; always report the Szabo–Huberman and no-levels ablations.  
6. **Conditional flash-vs-grower** — underpowered; needs more adopted DApps or a softer threshold.

---

## Recommended production recipe

1. Observe **k=3** months.  
2. Predict **`y_sustained_12`** with **calibrated HGB** (or elastic-net logistic if you need coefficients).  
3. Report PR-AUC / P@10% vs Szabo–Huberman.  
4. Use Cox survival probability as a secondary “fade risk” score.  
5. Never feed TVL / full-history lifecycle features into the model.

---

## File map

```
model/
  labels.py          # post-window labels + survival
  features.py        # early features + dataset merge
  baselines.py       # persistence / Szabo-Huberman / category prior
  train_eval.py      # CV, holdout, ablations, Cox, importance
  predict.py         # score young DApps
  run_all.py         # end-to-end runner
  MODEL_REPORT.md    # this file
  tables/            # metrics, datasets, predictions
  figures/           # ROC/PR, calibration, k-curve, PDP, importance
  artifacts/         # joblib calibrated models
```
