# Demo site

An interactive site for the capstone showcase: the six research questions on real data from 622 Ethereum DApps (2020 – 2025), live at <https://ethereum-dapp-trends.vercel.app>.

See **[CHART_DATA.md](results/CHART_DATA.md)** for where every number comes from, and **[DESIGN.md](DESIGN.md)** for colours and page rules.

## Quick start

```bash
python3 -m http.server 8765 --directory demo/site
```

Then open <http://localhost:8765>. At the booth, open <http://localhost:8765/?kiosk> instead: it returns to Home after 90 seconds idle. DApp cards saved with the bookmark are kept in that browser for Today at the booth (`#wall`); use "Clear today" there to empty it.

If the data changes:

```bash
python3 demo/script/build_data.py
python3 demo/script/export_charts.py
cd demo/site && vercel deploy --prod
```

## Pages

| Page | Purpose |
|------|---------|
| Questions | Understand the research one question at a time |
| Scenario walks | Follow one DApp through the questions as a story |
| Compare | See the differences between DApps side by side |
| Neighbours | Find the DApps that looked like yours early on |
| Game | Learn to read early signals by spotting the DApps that lasted |
| Today at the booth | Show today's saved DApp cards and top 10 game scores from this screen (summary on Home) |
| Method | Show how we measured success and which signals we used |

## Files

| Path | Contents |
|------|----------|
| `site/index.html` | The site: pages, charts and game |
| `site/data.js` | Every number the site shows |
| `script/build_data.py` | Builds `data.js` from the repo's CSVs |
| `script/export_charts.py` | Writes each chart's data to `results/tables/` |
| `results/tables/*.csv` | One CSV per chart, for the poster and slides |
