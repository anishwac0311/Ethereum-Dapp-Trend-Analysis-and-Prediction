# Demo site

An interactive site for the capstone showcase: six research questions answered on real data from 622 Ethereum DApps (2020 – 2025). Live at <https://ethereum-dapp-trends.vercel.app>.

- Where every number comes from: [results/CHART_DATA.md](results/CHART_DATA.md)
- How it looks and reads (colour, type, layout, components, words): [DESIGN.md](DESIGN.md)
- How it moves: [MOTION.md](MOTION.md)
- What to check before calling a change done: [CHECKLIST.md](CHECKLIST.md)

## Run it

```bash
python3 -m http.server 8765 --directory demo/site
```

Open <http://localhost:8765>. No build step: the page loads plain scripts in order.

At the booth, open <http://localhost:8765/?kiosk>: after 90 seconds with no input it goes back to a fresh Home (`?kiosk=120` sets the seconds). Cards saved with the Ethereum mark, and game scores, stay in that browser for Today at the booth (`#wall`); "Clear today" there empties it.

After editing, reload with Cmd+Shift+R so the browser drops cached scripts.

## Pages

| Page | What it is for |
|------|----------------|
| Home | The whole market at a glance, then three ways in: market, category, one DApp |
| Questions | The six questions, one page each, with an era switch |
| Walks | Follow the market, or one DApp, step by step to a summary card |
| Compare | Up to three DApps side by side |
| Neighbours | Place your own numbers and see the DApps that looked like yours |
| Game | Pick the DApps that lasted, reading two early signals at a time |
| Today at the booth | Today's saved cards and top scores |
| Method | How success is measured, the 33 signals, and how 1,816 DApps became 512 |
| About | Team, course and data sources |

## Files

| Path | Contents |
|------|----------|
| `site/index.html` | The page shell: the stylesheet, then the scripts in load order |
| `site/css/site.css` | All styles |
| `site/data.js` | Every number the site shows (generated) |
| `site/js/signals.js` | Each era's model signals, ranked by weight (generated) |
| `site/js/core.js` | Shared state and helpers |
| `site/js/copy.js` | Every sentence: Conclusions, and each walk step's name, notes and trail lines. Edit wording here |
| `site/js/charts.js` | Chart drawing |
| `site/js/slides.js` | The walk page frame: head, Conclusion, figure, notes |
| `site/js/views.js` | Home, Pick a DApp, Method, About, the card and the booth |
| `site/js/questions.js` | The question list and question pages |
| `site/js/compare.js` | Compare |
| `site/js/neighbours.js` | Neighbours and the measure cards |
| `site/js/game.js` | The game |
| `site/js/walks.js` | Both walks, step by step |
| `site/js/app.js` | Rendering, clicks and keys, sheets; loads last |
| `script/build_data.py` | Builds `data.js` from the repo's CSVs |
| `script/build_signals.py` | Builds `signals.js` from `data/coef_by_period.csv` |
| `script/export_charts.py` | Writes each chart's data to `results/tables/` |
| `data/coef_by_period.csv` | The model's coefficients per era (27 signals × 3 eras) |
| `results/tables/*.csv` | One CSV per chart, for the poster and slides |
| `review/export-conclusions.js` | Exports every Conclusion the site shows |
| `review/conclusions.md` | That export, for word-by-word review |

## Changing things

**Words.** Edit the sentence in `site/js/copy.js`, then refresh `review/conclusions.md`: open the local site, paste `review/export-conclusions.js` into the browser console, run `copy(window.__concl)` and paste the result into the file. Read the diff before committing.

**Data.** From the repo root:

```bash
python3 demo/script/build_data.py
python3 demo/script/build_signals.py
python3 demo/script/export_charts.py
```

**Deploy.** Only after the changes have been reviewed locally:

```bash
cd demo/site && vercel deploy --prod
```
