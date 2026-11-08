# Demo site

An interactive site for the showcase booth. Visitors pick an Ethereum DApp, or describe their own, and walk through the six research questions with real data from 622 DApps (2020 – 2025). It also has a short game.

See **[DESIGN.md](DESIGN.md)** for colours, type, layout rules, and how each page is built.

## Quick start

Run these from the repo root:

```bash
python3 demo/build_data.py
python3 demo/export_charts.py
python3 -m http.server 8765 --directory demo
```

Then open <http://localhost:8765>. The site is a single HTML page with no build step and no dependencies. Run `build_data.py` again whenever the data changes.

## Which file is which

| File | What it is | Made by |
|------|-----------|---------|
| `index.html` | The whole site: styles, pages, charts and the game, in plain JavaScript | hand-written |
| `data.js` | Every number the site shows (`window.DEMO`) | `build_data.py` |
| `build_data.py` | Reads the repo's CSVs and writes `data.js` | hand-written |
| `export_charts.py` | Writes the data behind each chart to `charts/` as CSV | hand-written |
| `charts/*.csv` | One CSV per chart table, for redrawing charts elsewhere (posters, slides) | `export_charts.py` |
| `charts/README.md` | Index of the CSVs: chart, page, source, how each is computed | `export_charts.py` |
| `DESIGN.md` | Design system and page rules | hand-written |

## Inputs

`build_data.py` reads only files that the rest of the repo already produces:

| Path | Used for |
|------|----------|
| `dapp_data_v2/category_month.csv` | Market strip, Q1 growth |
| `dapp_data_v2/concentration_month.csv` | Q3 concentration |
| `dapp_data_v2/dapp_panel.csv` | Per-DApp monthly wallets, Q4 speed, era leaders, Q3 rank curve |
| `dapp_data_v2/dapp_lifecycle.csv`, `dapp_static.csv`, `app_contracts.csv` | Method funnel and dataset counts |
| `dapp_data_v2/cohort_retention.csv` | Q5 retention |
| `eda/tables/trajectory_clusters.csv`, `03_trajectories_normalized.csv` | Q2 survival shapes, the 170 DApps in the picker |
| `eda/tables/05_event_checkpoints.csv`, `05_event_window.csv` | Q6 take-off |
| `model/tables/labels_k3.csv`, `dataset_k3.csv` | Success label and early signals (run `model/run_all.py` first; this folder is gitignored) |
| `model/dapp_offchain/data/dapp_offchain_by_k.csv` | Off-chain signals |
| `model/dapp_timesplit/results/tables/coef_groups_by_period.csv`, `coef_by_period.csv` | Q5 feature weights by era (read from branch `time-split-analysis` if not checked out) |

## Pages

| Page | What the visitor does |
|------|-----------------------|
| Home | Choose one of three ways in: Compare, Your DApp, or the game |
| Questions | The six questions (Q1 Growth – Q6 Take-off), each with its chart and answer |
| Your DApp | Enter a DApp's first months and see where it sits among DApps of the same age |
| Pick a DApp | Choose one of 170 widely used DApps and walk it through the questions |
| Compare | Put up to three DApps side by side |
| Game | Guess which DApps lasted; scores go on a local top-10 board |
| Method | The dataset, the success rule, and the 33 early signals |
| About | University, course, advisor, team and data sources |
