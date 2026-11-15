# Predicting sustained DApp success from early months

**Data:** `dapp_data_v2/` (panel 2020-01 → 2025-12), `dapp_data_v2/dapp_v2.duckdb` (wallet-level), DeFiLlama Ethereum TVL history, AWS public Ethereum token transfers  
**Code:** `model/labels.py`, `features.py`, `wallet_features.py`, `user_history_features.py`, `dapp_tvl/fetch_tvl.py`, `token_incentives/`, `panel_forecast.py`, `robust_eval.py`, `iterations.py`, `final_model.py` (+ v1: `baselines.py`, `train_eval.py`, `predict.py`)  
**Reproduce:** `.\.venv\Scripts\python model\run_all.py`  
**Optional deps:** `pip install xgboost shap` (XGBoost / SHAP are used when installed)

---

## Modelling journey and the v3 model (current recommendation)

Every step below is scored the same way: pooled out-of-fold predictions on expanding launch-year folds (validate 2021, 2022, 2023, 2024; 396 DApps), grid-mean PR-AUC over 15 success definitions (250–5,000 wallets × 15–40% of the window peak), and a paired cluster bootstrap against the v2 blend. `iterations.py` runs all candidates; `final_model.py` builds v3 from them.

### Grid-mean PR-AUC at each step

| Step | Month 3 | Month 6 |
|---|---|---|
| v1 boosted trees (the 0.65 was a single lucky holdout split) | 0.547 | 0.695 |
| + soft labels | 0.572 | 0.703 |
| + wallet-level features | 0.580 | 0.664 |
| pooled panel AR forecaster | **0.629** | 0.664 |
| v2 blend (soft HGB + TVL, panel AR) | 0.608 | 0.689 |
| best model with TVL / token / user-history data | 0.580 | 0.692 |
| **v3 nested ensemble** | 0.597 | **0.717** |

### What each iteration tried (`iterations.py`)

1. **Better pooled forecasters.** Ridge on all 22 origin features, a GARCH-style heteroscedastic σ(x), boosted mean, origin ages weighted near k−1, and longer lags (months k−6…k−1 plus window mean and min). At month 3 none beat the plain linear AR. At month 6 the boosted forecaster leads: 0.738, and 0.727 with lags.
2. **Predict a number.** Direct ridge or boosted regression of log wallets at months 10–12 on DApp features, with a Gaussian residual. This is worse than pooled forecasting at both checkpoints (0.52–0.68).
3. **Classifier variety.** Random forest, extra trees, shallow and monotone-constrained soft-label HGB, a compact 13-feature HGB, and a spline GAM. At month 3 all fall between 0.53 and 0.59. At month 6, extra trees reach 0.690.
4. **New features** (`user_history_features.py`):
   - **brand:** earlier versions of the same parent, the parent's wallets before launch, whether an earlier version was proven
   - **time-aware base rates:** shrunk success rate of same-category launches whose month-12 outcome was already observable
   - **economic value:** ETH and fees per wallet
   - **users' pre-launch history:** share of fresh wallets, months active before launch, loyalty, share who had used a proven app
   - **panel AR + feature correction:** a second model learns only the residual of the AR forecast

   Signals exist: an earlier proven version raises the success rate from 16% to 40%, and ETH per wallet has ρ +0.12 after size. But no model improves at month 3, and the user-history variants only add about +0.02 at month 6.
5. **Ensembles.** Rank average, logit mean, and a stacked logistic model, each over the top 4 models with at least one forecaster and one classifier. Choosing members on all folds flatters the score (month 6: 0.756, ΔAP +0.068 with CI +0.020 to +0.127). The **nested** version re-chooses members for each validation year using only the other years, and that is the number we report.

### v3 results (`final_model.py`, honest nested ensemble)

| k | ROC-AUC | PR-AUC @1k/25% | Grid-mean PR-AUC | Brier | Accuracy @0.5 | Balanced acc. |
|---|---|---|---|---|---|---|
| 3 | 0.868 | 0.628 | 0.597 | 0.093 | 87.9% | 0.79 |
| 6 | **0.931** | **0.729** | **0.717** | 0.069 | **90.9%** | 0.83 |

Against the v2 blend:
- **Month 6:** +0.031 grid PR-AUC (95% CI −0.018 to +0.079).
- **Month 3:** −0.010 (CI −0.067 to +0.040), so the two are level.

Production members are re-chosen on all folds:
- **k=3:** panel AR, ridge forecaster with lags, Szabo–Huberman, ridge forecaster
- **k=6:** boosted forecaster, boosted forecaster with lags, v1 HGB, boosted forecaster with local weights

**Confidence bands.** Thresholds are chosen on 2021–23 and frozen, then tested on 2024: 100 apps, 9 successes.

| k | Coverage | Confident accuracy | "Likely fail" correct | "Likely success" correct | Successes caught |
|---|---|---|---|---|---|
| 3 | 71% | 91.5% | 98.4% | 44% | 4 / 9 |
| 6 | 93% | **94.6%** | 98.8% | 67% | **8 / 9** |

At month 6, v2 caught 5 of 9 successes, and its success calls were right 56% of the time.

**Two-stage policy** (`tables/final_two_stage.csv`): act on confident month-3 calls and re-score the uncertain apps at month 6. On 2024 this decides 71% of apps at month 3 and covers 95% of apps in total. It is 91.6% accurate on its confident calls, 92.0% accurate when every app is forced to a call, and catches 8 of 9 successes. On 2024, saying "fail" to every app already scores 91% because only 9 apps succeeded, so success recall and precision are the numbers to watch, not accuracy.

### Is 90% accuracy reachable?

- **At month 6:** yes. Accuracy is 90.9% at the 0.5 threshold, and 94.6% on the 93% of apps with a confident call.
- **At month 3:** only on the confident subset (91.5% on 71% of apps).

The ceiling test below shows why. Even a model that could see months 3–5 would reach only about 91% with one feature. The remaining month-3 error comes from events after month 3, not from the choice of model.

---

## v2 model (superseded by v3)

**`final_model.py`** blends two components and calibrates the result.

- **Component 1: soft-label HGB.** Features are on-chain, off-chain, news, wallet-level and window-timed Ethereum TVL.
- **Component 2: pooled panel AR forecaster.** It predicts log wallets at months 10–12.
- **Blending.** The two logits are averaged, then Platt-calibrated.
- **Confidence bands.** Every DApp gets one of three bands:
  - **likely_fail**: at least 95% of these fail
  - **likely_success**: at least 80% of these succeed
  - **uncertain**: everything in between

### How we evaluate now (`robust_eval.py`)

The v1 holdout (2023–24, n=237) has about 29 positives. Its 95% CI on PR-AUC is roughly ±0.16, so model differences of +0.05 were invisible. We now use:

- **Expanding folds.** Validate on parent-launch years 2021, 2022, 2023 and 2024, each trained on all earlier years. Versions of a protocol never straddle folds. Out-of-fold predictions are pooled across 396 DApps and 63 positives at k=3.
- **Success as a range, not one cutoff.** We compute PR-AUC at every cell of an absolute × relative grid:
  - T ∈ {250, 500, 1k, 2.5k, 5k} wallets at months 10–12
  - ρ ∈ {0.15, 0.25, 0.40} of the window max

  The headline is the mean PR-AUC over the grid. We also report Spearman correlation with log wallets, which needs no cutoff.
- **Paired cluster bootstrap.** Resampling by `parent_protocol` gives ΔAP against the v1 HGB.
- **Leakage check.** The forecaster's origin features are recomputed after deleting all months ≥ k for sampled DApps, and must come out identical (`panel_forecast.leakage_check`).

### Results (pooled out-of-fold, `y_sustained_12`)

| k | Model | ROC-AUC | PR-AUC @1k/25% | Grid-mean PR-AUC | Brier score |
|---|-------|-----|-----|-----|-----|
| 3 | v1 HGB | 0.827 | 0.576 | 0.547 | 0.101 |
| 3 | Szabo–Huberman | 0.864 | 0.654 | 0.606 | 0.137 |
| 3 | panel AR forecaster | 0.868 | 0.641 | **0.606–0.629** | 0.091 |
| 3 | soft-label HGB + wallet | 0.872 | 0.654 | 0.580 | 0.097 |
| 3 | **final blend** | 0.867 | 0.647 | 0.581 | **0.088** |
| 6 | **final blend** | **0.924** | **0.711** | **0.677** | **0.069** |

The two panel-AR grid-mean values come from two runs: 0.629 from the full model comparison and 0.606 from the final-model run.

Paired bootstrap against the v1 HGB at k=3, as grid-mean ΔAP with 95% CI:

| Model | ΔAP | 95% CI | Grid cells won (of 15) |
|---|---|---|---|
| panel AR | +0.073 | −0.012 to +0.152 | 15 |
| Szabo–Huberman | +0.053 | | 15 |
| soft-label HGB + wallet | +0.028 | | 14 |
| soft-label HGB | +0.020 | | 13 |
| hard-label HGB + wallet | −0.004 | | 8 |
| HGB stacked on forecast | −0.005 | | 4 |

**Takeaways**
1. **Under the honest protocol, the v1 0.65 becomes about 0.58.** The single holdout was a favourable draw.
2. **The useful changes were soft labels and pooled forecasting**, not more feature columns. Wallet features and TVL add nothing with hard labels, and add only a little with soft labels. No improvement has a bootstrap CI that excludes 0, because 63 positives aren't enough.
3. **Early size and trajectory carry most of the month-3 signal.** That's why a one-feature Szabo–Huberman model is competitive.

### Confidence bands (thresholds chosen on 2021–23, tested on the unseen 2024 fold)

| k | Split | Confident coverage | Confident accuracy | Precision of "likely fail" | Precision of "likely success" |
|---|---|---|---|---|---|
| 3 | 2021–23 (selection) | 86% | 93.3% | 95.0% | 81% |
| 3 | 2024 (unseen) | 87% | 89.7% | 96.1% | 40% (n≈5) |
| 6 | 2021–23 (selection) | 91% | 93.3% | 95.3% | 80% |
| 6 | 2024 (unseen) | 91% | **94.5%** | **98.8%** | 56% (n≈9) |

At month 3 the model is a reliable **failure screen**. Success calls become usable at month 6.

### How predictable is this at all? (ceiling test)

We predicted `y_sustained_12` from log mean wallets in a later 3-month window, using a 1-feature logistic model with 5-fold cross-validation:

| Wallets observed at months | ROC-AUC | PR-AUC | Accuracy |
|---|---|---|---|
| 0–2 (k=3) | 0.87 | 0.62 | 0.87 |
| 3–5 | 0.94 | 0.77 | 0.91 |
| 5–7 | 0.97 | 0.87 | 0.94 |
| 7–9 | 0.97 | 0.91 | 0.96 |

The full k=3 model is no better than this 1-feature line, so most of the remaining k=3 error is **not a modelling problem**. It comes from events after month 3 that no early data can see: incentives ending, exploits, competitors, the market regime. Our estimate of the realistic k=3 ceiling is ROC-AUC ≈ 0.90 and PR-AUC ≈ 0.70.

Plain accuracy is uninformative here: always predicting "fail" scores 84%. Use AUC, PR-AUC, balanced accuracy, or accuracy within the confidence bands.

### Why not per-DApp ARIMA / GARCH?

At prediction time each DApp has only 1, 3 or 6 monthly points, which is too few to fit any ARIMA or GARCH model. The AR idea is used in **pooled** form instead. `panel_forecast.py` learns "lagged log wallets → wallets 8–10 months ahead" from all 10k DApp-month origins, compared with 512 rows for the classifier. A linear version (`panel_ar`) and a gradient-boosted quantile version (`panel_gbm_q`) are both evaluated. The linear one generalises better. GARCH would only make sense on long market series such as ETH returns, and ETH momentum features already showed little lift.

### New Ethereum data in this version

| Source | Features | Timing |
|---|---|---|
| `dapp_v2.duckdb`: 130M wallet-month rows plus daily first-seen dates (`wallet_features.py`) | weekly acquisition momentum and slope, top-day spike share; experienced-user share; single-tx share; tx Gini; month-0→k-1 user retention; multi-month share; prior use of top-decile DApps; multi-homing | Months 0..k-1 only; heavy wallets excluded |
| DeFiLlama daily Ethereum TVL (`dapp_tvl/fetch_tvl.py`) | log mean/last TVL, TVL slope, last/max, TVL per wallet, category TVL share, TVL before launch | Dates before launch + k months. Covers 48% of DApps at k=3 and 61% at k=6; NFT, gaming and social apps have none |
| AWS public Ethereum ERC-20 transfers (`token_incentives/build_token_features.py`) | token live / pre-launch; distinct recipients and their growth; airdrop share (first receipt from a fan-out sender, DEX contracts excluded); reward share (transfers sent by the DApp's own contracts); reward ramp; share of the DApp's users who received its token | From launch − 3 months to launch + k. 307 DApps have their own token (WETH, USDC, USDT and DAI excluded). Among eligible DApps, 34% have token activity in the window at k=3 and 37% at k=6 |

### Token-incentive features: a negative result

The open question at month 3 was whether usage is being bought with token incentives that later end. We scanned 24M transfers of the DApps' own tokens.

**Signal exists.** We measured Spearman ρ with the month-10–12 outcome after removing what the current wallet count already explains, at k=3 with n≈177:

| Feature | ρ |
|---|---|
| Share of users who received the token | −0.25 |
| Share of transfers sent by own contracts (rewards) | −0.21 |
| Distinct recipients | +0.22 |

Heavily incentivised usage decays, as expected.

**The model doesn't improve.** Pooled out-of-fold grid-mean PR-AUC:

| k | soft HGB + wallet | + token | + TVL | + TVL + token |
|---|---|---|---|---|
| 3 | 0.580 | 0.564 | 0.574 | 0.564 |
| 6 | 0.664 | 0.668 | 0.675 | 0.683 |

All differences are well inside the noise, and the k=3 change is slightly negative.

There are two reasons:
- Only about a third of DApps have a token that is active in the window.
- With 63 positives, the trees can't learn a subgroup-specific effect.

The final model therefore keeps `FEATURE_COLS_PLUS_WALLET_TVL`. The token features stay in the dataset (`FEATURE_COLS_PLUS_WALLET_TOKEN`, `..._TVL_TOKEN`) for future use, for example as an explicit adjustment term in the forecaster once more labelled launches accumulate.

Data note: AWS `token_transfers` stores from/to as 32-byte padded values. They are cut to 20-byte addresses before joining to the local DB.

### Flexible success labels (`labels.py`)

- `y_log_wallets_12`, `y_rel_12`: continuous outcomes.
- `sustained_at(df, T, rho)`: any cell of the grid.
- `y_soft_12`: a soft label. It is a logistic ramp on log wallets around 1k (about 0.12 at 370 wallets, about 0.88 at 2.7k) multiplied by a linear ramp on the ratio from 15% to 40%. Training duplicates each row as a weighted positive and a weighted negative.
- `y_tier_12`: tiers dead (<250), niche, sustained (1k–5k) and breakout (≥5k).

The 45 DApps averaging 500–2,000 wallets were near-coin-flip labels under the hard cutoff.

---

# v1 report (single holdout)

The sections below are the original v1 analysis. They are kept for reference, and their numbers use the 2023–24 single holdout.

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

## Ablations (k=3, HGB holdout AP)

| Variant | HGB AP | Calibrated HGB AP |
|---------|--------|-------------------|
| full (on-chain + off-chain) | 0.577 | 0.569 |
| on_chain_only | 0.567 | **0.605** |
| on_chain_plus_gov (timed Snapshot) | 0.581 | 0.572 |
| on_chain_plus_static (audit/OSS/verified today) | 0.585 | 0.570 |
| no_levels | 0.537 | 0.510 |
| levels_only | 0.533 | 0.527 |

Off-chain columns come from `model/dapp_offchain/data/dapp_offchain_by_k.csv` (merged on `slug`+`k`). Governance counts are window-timed; audit / open-source / verified are **today’s** snapshots.

**Takeaway:** adding off-chain does **not** clearly beat a well-calibrated on-chain-only model on PR-AUC. Timed governance (`log_n_proposals_window`) shows up in permutation importance, but lift is small and calibration can prefer the leaner on-chain set. Keep off-chain as an optional block / ablation, not the default headline model, until as-of-launch audit/OSS histories exist.

Shape / retention / context features still carry signal when raw size is removed. `has_token` is nearly inert under permutation.

---

## What drives predictions (k=3 HGB, permutation on AP)

Top features: **`early_cat_share`**, **`log_last_wallets`**, **`last_to_max_ratio`**, **`log_mean_gas`**, growth slope, **`launch_cat_growth_3m`**, then **`log_n_proposals_window`** among off-chain fields.

Interpretation:
- Ending the window still large (last wallets) and not already fading (`last_to_max`) matters for persistence.
- Category share and launch-month category growth capture competition / regime.
- Early governance activity is a weak positive signal; static audit/OSS flags are weak under this split.

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
4. **Off-chain snapshot bias** — audit / open-source / verified reflect *today*, not launch-time status; only Snapshot proposal counts are cut at window k. Empirically they add little holdout PR-AUC vs on-chain-only.  
5. **Mechanical baseline** — size alone is powerful; always report the Szabo–Huberman and no-levels ablations.  
6. **Conditional flash-vs-grower** — underpowered; needs more adopted DApps or a softer threshold.  
7. **2025 scoring** — young launches are often absent from the 512-row off-chain study table, so off-chain fields impute to training medians for those apps.

---

## Recommended production recipe (current)

1. **Run order:** `iterations.py --k 3 6`, then `final_model.py --k 3 6`. This writes `artifacts/final_k{3,6}.joblib` (members, calibrator, band thresholds) and scores 2025 launches.
2. **Month 3, early read:** act on **likely_fail** calls, which were 98% correct on the unseen 2024 fold. Treat everything else as open.
3. **Month 6, confirmation:** the k=6 ensemble has AUC 0.93 and is 94.6% accurate on the 93% of DApps it calls confidently, catching 8 of 9 successes in 2024. Use this checkpoint for success calls. The two-stage policy combines the two checkpoints.
4. **Evaluate any change** with `iterations.py` (or `robust_eval.py`), using grid-mean PR-AUC and the paired bootstrap, not the single holdout.
5. Use Cox survival probability as a secondary "fade risk" score.
6. **TVL rule.** Never use today's TVL snapshot or full-history lifecycle features. TVL is allowed only as the window-timed series from `dapp_tvl/`.

---

## File map

```
model/
  labels.py          # post-window labels, survival, flexible grid / soft / tier labels
  features.py        # early features + dataset merge (off-chain, news, wallet, TVL, token)
  wallet_features.py # wallet-level window features from dapp_v2.duckdb
  dapp_tvl/          # DeFiLlama Ethereum TVL history -> window-timed TVL features
  token_incentives/  # own-token transfers (AWS public data) -> incentive / airdrop features
  panel_forecast.py  # pooled AR / quantile forecaster + leakage check
  user_history_features.py # brand, time-aware base rates, users' pre-launch history
  iterations.py      # every modelling iteration on one protocol + nested ensemble
  deck_charts.py     # charts for the presentation (figures/deck/)
  robust_eval.py     # pooled OOF, threshold grid, paired bootstrap comparison
  final_model.py     # v3 ensemble, calibration, bands, two-stage policy, 2025 scoring
  baselines.py       # persistence / Szabo-Huberman / category prior
  train_eval.py      # v1: CV, holdout, ablations, Cox, importance
  predict.py         # v1: score young DApps with calibrated HGB
  run_all.py         # end-to-end runner
  MODEL_REPORT.md    # this file
  tables/            # metrics, datasets, predictions
  figures/           # ROC/PR, calibration, k-curve, PDP, importance
  artifacts/         # joblib calibrated models
```
