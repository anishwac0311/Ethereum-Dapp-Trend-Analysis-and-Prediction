# Candidate features for the team model

The team features all use monthly active wallets. Q4 shows that successful DApps differ in how they acquire new users, and Q3 shows that markets differ in how concentrated they are. These candidate features bring both into the model.

**Code:** `script/features.py`  
**Output:** `data/dapp_acquisition_features.csv`, one row per DApp and k (1, 3, 6)  
**Join:** to `model/features.py` on `slug` and `k`

## Rules

- **No look-ahead:** only months 0..k-1, so nothing after the window leaks in.
- **Same sample as the model:** the deploy clock and the 512 DApps of `model/labels.py`.

## Features: Acquisition (new group, 5)

How a DApp acquires new users, from cumulative wallets (Q4).

| Feature | From the first k months | Finding behind it |
|---|---|---|
| `log_cum_wallets_k` | Cumulative wallets (log) | Successful DApps start bigger |
| `cum_growth_last` | New users in the last month ÷ users so far | Successful DApps keep growing |
| `growth_decay` | Last-month growth minus first-month growth (log) | Is growth slowing |
| `months_to_first_user_k` | Months from deploy to first user | Clean vs late start |
| `starts_empty` | Under 10 wallets in the first month with users | Test wallets start the clock |

## Features: Context (+3 to the existing group)

The market a DApp launches into, in its launch month (Q3).

| Feature | In the launch month | Finding behind it |
|---|---|---|
| `category_hhi_at_launch` | Category HHI | Concentrated markets |
| `category_top1_share_at_launch` | Category leader's share | Markets with one leader |
| `category_n_dapps_at_launch` | Active DApps in the category | Crowded markets |

## First look (k = 3, one feature at a time, no model)

| Feature | Successful | Not | One-feature AUC |
|---|---|---|---|
| `log_cum_wallets_k` | 8.35 | 2.71 | 0.87 |
| `cum_growth_last` | 0.69 | 0.18 | 0.75 |
| `growth_decay` | −0.63 | −0.20 | 0.37 |
| `months_to_first_user_k` | 0 | 0 | 0.46 |
| `starts_empty` | 34% | 66% | 0.34 |
| `category_hhi_at_launch` | 0.23 | 0.13 | 0.66 |
| `category_top1_share_at_launch` | 0.38 | 0.28 | 0.64 |
| `category_n_dapps_at_launch` | 28 | 68 | 0.32 |

AUC below 0.5 means lower values go with success. Full numbers: `results/tables/acquisition_features_k3.csv`.

- **Cumulative wallets separate the groups most,** but overlap with the team's size features.
- **`starts_empty` and `growth_decay` may add new signal.** Within 3 months, successful DApps slow more because they start with a bigger burst.
- **Category features partly reflect launch year,** which the model already has: categories got more crowded over time.

## Next

Not in the model yet. Test them in `model/train_eval.py`, with and without the Acquisition group, and check whether the Context features still help once launch year is in.
