# Chart data

One CSV per chart on the demo site. They are copied from `site/data.js`, so they match the site exactly; every number was also checked against the repo CSVs listed under source. Regenerate them after `build_data.py` with `python3 demo/script/export_charts.py`.

- `model/tables/` is gitignored: run `model/run_all.py` before `build_data.py`.
- The time-split tables are read from branch `time-split-analysis` if they are not checked out.
- Not data: the DragonQuest example on Method (made up to explain the method) and the registry size of 1,816 DApps (from DeFiLlama, as reported in Presentation 2).

Files are numbered by where they appear: `01` Home, `02`–`07` the six questions, `08` Method, `09`–`11` per-DApp data used across several pages.

## Home

| file | chart | used on | source | how |
|---|---|---|---|---|
| [01_market_month.csv](tables/01_market_month.csv) | Market strip: wallets, transactions and gas per month | Home | dapp_data_v2/category_month.csv | Sum over the seven categories. Terra = 2022-05, Dencun = 2024-03. |

## Questions (Q1 – Q6)

| file | chart | used on | source | how |
|---|---|---|---|---|
| [02_q1_wallets_by_category.csv](tables/02_q1_wallets_by_category.csv) | Monthly active wallets by category | Q1 Growth, scenario walks, Pick a timeline | dapp_data_v2/category_month.csv | active_wallets per category. |
| [02_q1_growth_12m_by_category.csv](tables/02_q1_growth_12m_by_category.csv) | 12-month change in wallets by category | Q1 Growth, scenario walks, Pick a timeline | dapp_data_v2/category_month.csv | Wallets vs the same month a year earlier (0.5 = +50%). |
| [02_q1_active_dapps_by_category.csv](tables/02_q1_active_dapps_by_category.csv) | Active DApps by category | Q1 Growth, scenario walks, Pick a timeline | dapp_data_v2/category_month.csv | active_dapps per category. |
| [03_q3_market_concentration.csv](tables/03_q3_market_concentration.csv) | Share of all wallets held by the top DApps | Q3 Concentration | dapp_data_v2/concentration_month.csv (metric = active_wallets, scope = ecosystem) | Shares of all active wallets that month. |
| [03_q3_top10_by_category.csv](tables/03_q3_top10_by_category.csv) | Top-10 share inside each category | Q3 Concentration, scenario walks | dapp_data_v2/concentration_month.csv (scope = category) | Top-10 share of the category's wallets. |
| [03_q3_rank_curve_by_year.csv](tables/03_q3_rank_curve_by_year.csv) | Rank curve: share held by the top k DApps | Q3 Concentration | dapp_data_v2/dapp_panel.csv | DApps ranked by mean monthly wallets in the year; cumulative share of the top k. |
| [03_q3_size_histogram_by_year.csv](tables/03_q3_size_histogram_by_year.csv) | DApps by size (log-normal shape) | Q3 Concentration | dapp_data_v2/dapp_panel.csv; power-law test in model/dapp_concentration/results/tables/power_law_by_year.csv (branch concentration-analysis) | Bins are log10 of mean monthly wallets in the year. |
| [04_q2_median_shape.csv](tables/04_q2_median_shape.csv) | Median shape: wallets as a share of own peak | Q2 Survival | eda/tables/trajectory_clusters.csv, eda/tables/03_trajectories_normalized.csv | 170 widely used DApps; flash_fade = one-hit, every other cluster = kept growing. |
| [04_q2_shape_by_category.csv](tables/04_q2_shape_by_category.csv) | One-hit vs kept growing, by category | Q2 Survival | eda/tables/trajectory_clusters.csv | Counts of DApps. |
| [05_q4_reach_10k.csv](tables/05_q4_reach_10k.csv) | Reaching 10K cumulative wallets | Q4 Speed, Compare | dapp_data_v2/dapp_panel.csv (cum_wallets), model/tables/labels_k3.csv (y_sustained_12) | Study set: 85 successes, 427 others. Month 0 = first month with a user. |
| [06_q5_retention_by_era.csv](tables/06_q5_retention_by_era.csv) | Launch users still active, by launch era | Q5 Retention, Compare | dapp_data_v2/cohort_retention.csv | DApps with at least 100 first-month users. Median with 25th-75th percentile band. |
| [06_q5_feature_weights_by_era.csv](tables/06_q5_feature_weights_by_era.csv) | What matters in each era: feature-group weights | Q5 Retention | model/dapp_timesplit/results/tables/coef_groups_by_period.csv (branch time-split-analysis) | Each group's share of the L2 logistic regression's total weight, fitted per era; low / high from 1,000 resamples. |
| [07_q6_around_10k.csv](tables/07_q6_around_10k.csv) | Before and after crossing 10K cumulative wallets | Q6 Take-off, Compare | eda/tables/05_event_checkpoints.csv; per-DApp lines in Compare from eda/tables/05_event_window.csv | Month 0 = the month a DApp crosses 10K. Median across DApps of each group. |

## Method

| file | chart | used on | source | how |
|---|---|---|---|---|
| [08_method_funnel.csv](tables/08_method_funnel.csv) | Dataset funnel | Method, About | dapp_data_v2/protocols.csv, dapp_static.csv, app_contracts.csv, dapp_lifecycle.csv; model/tables/labels_k3.csv | Registry size 1,816 is from DeFiLlama, as reported in Presentation 2. |
| [08_method_lifecycle.csv](tables/08_method_lifecycle.csv) | DApps by lifecycle label | Method | dapp_data_v2/dapp_lifecycle.csv | Counts of lifecycle_label. |
| [08_method_by_category.csv](tables/08_method_by_category.csv) | DApps by category | Method | dapp_data_v2/dapp_lifecycle.csv | Counts of category_group. |
| [08_method_by_launch_year.csv](tables/08_method_by_launch_year.csv) | DApps by launch year | Method | dapp_data_v2/dapp_lifecycle.csv | Counts of launch_year. |
| [08_method_peak_histogram.csv](tables/08_method_peak_histogram.csv) | Peak monthly wallets | Method | dapp_data_v2/dapp_lifecycle.csv | Bins are log10 of peak_wallets. |
| [08_method_signals.csv](tables/08_method_signals.csv) | 33 early signals: success vs other | Method | model/tables/dataset_k3.csv; model/dapp_offchain/data/dapp_offchain_by_k.csv (k = 3); signal groups from model/dapp_timesplit/results/tables/coef_by_period.csv (branch time-split-analysis) | First 3 months. Median for numbers, share for yes/no flags, mean for proposal counts. |

## DApp-level data

| file | chart | used on | source | how |
|---|---|---|---|---|
| [09_era_leaders_top5.csv](tables/09_era_leaders_top5.csv) | Top five DApps per category and era | Scenario walks, Neighbours leaderboard | dapp_data_v2/dapp_panel.csv | Average monthly active wallets inside the era window; share of the category total. |
| [10_dapps_170_wallets.csv](tables/10_dapps_170_wallets.csv) | The 170 widely used DApps: wallets by month since launch | Pick a DApp, walk figures, Compare | eda/tables/trajectory_clusters.csv, dapp_data_v2/dapp_panel.csv, model/tables/labels_k3.csv | success is blank when too recent to judge. m0 = first month with a user. |
| [11_all_dapps_wallets_by_age.csv](tables/11_all_dapps_wallets_by_age.csv) | All 601 DApps: wallets by month of age | Your DApp, Neighbours map, the game | dapp_data_v2/dapp_panel.csv, dapp_data_v2/dapp_lifecycle.csv, model/tables/labels_k3.csv | Age 0 = first month with a user. |
