# DApp concentration

How concentrated is Ethereum DApp activity, and what shape does the size distribution follow?

**Data:** `dapp_data_v2/`, 601 protocols, 2020-01 → 2025-12, monthly active wallets  
**Code:** `model/dapp_concentration/script/`  
**Reproduce:** `cd model/dapp_concentration && python script/main.py`

See **[REPORT.md](REPORT.md)** for findings, the power-law test, and limitations.

## Quick start

```bash
cd model/dapp_concentration
pip install pandas numpy scipy matplotlib
python script/main.py
```

Inputs are read from `dapp_data_v2/` (`activity.csv`, `concentration_month.csv`, `protocols.csv`, `dapp_static.csv`).

## Main findings

1. **More DApps, mostly tiny ones.** Active DApps grow from 55 to 380 a month, but almost half now have under 10 wallets.
2. **A few apps hold most of the activity.** The top 10 keep 70–80% of wallets every year.
3. **DEX leads the top 10, and Uniswap leads DEX.** Uniswap holds about 75% of DEX wallets every year since 2021.
4. **DEX stays concentrated, DeFi stays competitive.** After 2021, HHI falls or stays flat in every category.
5. **Sizes are log-normal, not a power law.** Leaders stay on top, but being big does not make them grow faster.

## Outputs

| Path | Contents |
|------|----------|
| `data/dapp_size_by_year.csv` | Average monthly active wallets per DApp and year |
| `results/tables/concentration_by_year.csv` | Top-k share, HHI and Gini by year |
| `results/tables/market_type_by_period_scope.csv` | HHI × Gini market type per category and period |
| `results/tables/power_law_by_year.csv` | Power law vs log-normal test per year |
| `results/tables/` | Other summary tables |
| `results/figures/` | Size distribution, top-k share, HHI/Gini, DEX, market type, power-law tail |
