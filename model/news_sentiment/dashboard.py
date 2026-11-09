"""Render a live report dict as a self-contained HTML dashboard (no external assets).

Colour: green = bullish, red = bearish, gray = neutral. Colour is never the only cue:
every sentiment also carries a ▲ / ▼ / ● marker and a text label. The palette was
checked for colour-blind separation; green and red are never placed side by side
(neutral gray always sits between them).
"""
from __future__ import annotations

import html
import json
from datetime import datetime

ICON = {"bullish": "▲", "bearish": "▼", "neutral": "●"}
LABEL = {"bullish": "Bullish", "bearish": "Bearish", "neutral": "Neutral"}
HORIZON = {"short": "Short (0–48h)", "medium": "Medium (2–30d)", "long": "Long (30d+)"}
SCOPE = {"eth_specific": "ETH-specific", "eth_ecosystem": "ETH ecosystem",
         "market_wide": "Market-wide", "macro": "Macro"}
CTYPE = {"fact": "Factual report", "opinion": "Opinion", "speculation": "Speculation"}


def e(x) -> str:
    return html.escape("" if x is None else str(x))


def _date(s) -> str:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).strftime("%b %d, %Y %H:%M UTC")
    except ValueError:
        return e(s)


def _pct(x) -> str:
    return "n/a" if x is None else f"{x:+.1%}"


def chip(sent: str) -> str:
    return f'<span class="chip {sent}"><span aria-hidden="true">{ICON[sent]}</span> {LABEL[sent]}</span>'


def render(r: dict) -> str:
    arts = {a["article_id"]: a for a in r["articles"]}
    leads = [a for a in r["articles"] if a.get("is_cluster_lead")]
    ov, mom, asm = r["overall"], r["momentum"], r["assessment"]
    gauge_pos = (ov["score"] + 100) / 2

    def card(a: dict, rank: int | None = None) -> str:
        n = int(a.get("cluster_size") or 1)
        dup = f'<span class="tag">covered by {n} articles (counted once)</span>' if n > 1 else ""
        title_note = ('<span class="tag">headline rebuilt from URL</span>'
                      if a.get("title_source") == "url_slug" else "")
        cues = f'<p class="cues">Cues: {e(a.get("cues"))}</p>' if a.get("scored_by") == "rules" and a.get("cues") else ""
        return f"""
<article class="card {e(a['sentiment'])}">
  <header>
    {f'<span class="rank">#{rank}</span>' if rank else ''}
    <h3><a href="{e(a['url'])}" target="_blank" rel="noopener">{e(a['title'])}</a></h3>
  </header>
  <p class="meta">{e(a['source_name'])} · {_date(a['published'])} · <a href="{e(a['url'])}" target="_blank" rel="noopener">source link</a></p>
  <div class="facts">
    {chip(a['sentiment'])}
    <span class="kv"><b>Score</b> {a['sentiment_score']:+.0f}</span>
    <span class="kv"><b>Impact</b> {a['market_impact']:.1f}/10</span>
    <span class="kv"><b>Horizon</b> {HORIZON.get(a['time_horizon'], a['time_horizon'])}</span>
    <span class="kv"><b>Confidence</b> {a['confidence']:.0f}%</span>
    <span class="kv"><b>Rank score</b> {a['rank_score']:.0f}</span>
  </div>
  <div class="tags"><span class="tag">{CTYPE.get(a['content_type'], a['content_type'])}</span>
    <span class="tag">{SCOPE.get(a['scope'], a['scope'])}</span>
    <span class="tag">{e(a['event_type']).replace('_', ' ')}</span>{dup}{title_note}
    <span class="tag">scored by {e(a.get('scored_by', 'rules'))}</span></div>
  <p><b>Reasoning.</b> {e(a['reasoning'])}</p>
  <p><b>Possible ETH implications.</b> {e(a['price_implications'])}</p>
  <p class="muted"><b>Priced in?</b> {e(a.get('priced_in_note'))}</p>
  {cues}
</article>"""

    def mini(ids: list[str], empty: str) -> str:
        if not ids:
            return f'<p class="muted">{empty}</p>'
        items = []
        for i in ids:
            a = arts[i]
            items.append(f'<li>{chip(a["sentiment"])} <a href="{e(a["url"])}" target="_blank" rel="noopener">'
                         f'{e(a["title"])}</a> <span class="muted">· {e(a["source_name"])} · impact '
                         f'{a["market_impact"]:.1f}</span></li>')
        return "<ul class='list'>" + "".join(items) + "</ul>"

    rows = []
    for i, a in enumerate(leads, 1):
        rows.append(f"""<tr>
<td class="num">{i}</td>
<td><a href="{e(a['url'])}" target="_blank" rel="noopener">{e(a['title'])}</a>
<div class="muted small">{e(a['source_name'])} · {_date(a['published'])}</div></td>
<td>{chip(a['sentiment'])}</td><td class="num">{a['sentiment_score']:+.0f}</td>
<td class="num">{a['market_impact']:.1f}</td><td>{e(a['time_horizon'])}</td>
<td class="num">{a['confidence']:.0f}%</td><td>{CTYPE.get(a['content_type'], '')}</td>
<td>{SCOPE.get(a['scope'], '')}</td><td class="num"><b>{a['rank_score']:.0f}</b></td></tr>""")

    events = []
    for ev in r["upcoming_protocol_calls"][:10]:
        when = ev["date"] or "date not stated"
        core = ' <span class="tag">core devs</span>' if ev.get("is_core") else ""
        events.append(f'<li><span class="date">{e(when)}</span> <a href="{e(ev["url"])}" target="_blank" '
                      f'rel="noopener">{e(ev["title"])}</a>{core}</li>')
    for i in r["upcoming_from_news"]:
        a = arts[i]
        events.append(f'<li><span class="date">in the news</span> <a href="{e(a["url"])}" target="_blank" '
                      f'rel="noopener">{e(a["title"])}</a> <span class="muted">· {e(a["source_name"])}</span></li>')

    scatter = [{"x": a["sentiment_score"], "y": a["market_impact"], "s": a["sentiment"],
                "t": a["title"], "src": a["source_name"]} for a in leads]
    top_cards = "".join(card(arts[i], n) for n, i in enumerate(r["top5"], 1))
    other_cards = "".join(card(a) for a in leads if a["article_id"] not in r["top5"])
    watch = "".join(f"<li>{e(w)}</li>" for w in asm.get("watchlist", []))
    env = ov["environment"]
    env_cls = {"bullish": "bullish", "bearish": "bearish"}.get(env, "neutral")
    m7 = mom.get("ret_7d")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ETH News Sentiment</title>
<style>
:root {{
  --surface:#fcfcfb; --surface-2:#f3f2ef; --border:#e2e1dc; --text:#0b0b0b; --text-2:#52514e; --muted:#6f6e69;
  --bull:#16804a; --bear:#d03b3b; --neutral:#b9b8b2; --neutral-ink:#5f5e59; --accent:#2a78d6;
  --bull-bg:#e6f4ec; --bear-bg:#fbe9e9; --neutral-bg:#efeeea;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --surface:#1a1a19; --surface-2:#242422; --border:#383835; --text:#f0efec; --text-2:#c3c2b7; --muted:#a3a29a;
  --bull:#2a9d5c; --bear:#e66767; --neutral:#5f5e59; --neutral-ink:#c3c2b7; --accent:#3987e5;
  --bull-bg:#173323; --bear-bg:#3a1d1d; --neutral-bg:#2c2c2a; }} }}
:root[data-theme="dark"] {{
  --surface:#1a1a19; --surface-2:#242422; --border:#383835; --text:#f0efec; --text-2:#c3c2b7; --muted:#a3a29a;
  --bull:#2a9d5c; --bear:#e66767; --neutral:#5f5e59; --neutral-ink:#c3c2b7; --accent:#3987e5;
  --bull-bg:#173323; --bear-bg:#3a1d1d; --neutral-bg:#2c2c2a; }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--surface); color:var(--text); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif }}
main {{ max-width:1180px; margin:0 auto; padding:24px 16px 64px }}
h1 {{ font-size:26px; margin:0 0 4px }} h2 {{ font-size:19px; margin:36px 0 12px }} h3 {{ font-size:16px; margin:0 }}
a {{ color:var(--accent) }} .muted {{ color:var(--muted) }} .small {{ font-size:13px }}
.sub {{ color:var(--text-2); margin:0 0 20px }}
.grid {{ display:grid; gap:12px; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)) }}
.tile {{ background:var(--surface-2); border:1px solid var(--border); border-radius:10px; padding:14px 16px }}
.tile .lbl {{ color:var(--text-2); font-size:13px }} .tile .val {{ font-size:28px; font-weight:650; margin-top:2px }}
.tile .note {{ color:var(--muted); font-size:12.5px }}
.hero {{ background:var(--surface-2); border:1px solid var(--border); border-radius:12px; padding:18px 20px; margin-bottom:12px }}
.gauge {{ position:relative; height:14px; border-radius:7px; margin:14px 0 6px;
  background:linear-gradient(90deg,var(--bear) 0%,var(--neutral) 42%,var(--neutral) 58%,var(--bull) 100%) }}
.gauge .mark {{ position:absolute; top:-6px; width:4px; height:26px; background:var(--text); border-radius:2px;
  outline:2px solid var(--surface); transform:translateX(-2px) }}
.gauge-scale {{ display:flex; justify-content:space-between; font-size:12px; color:var(--muted) }}
.chip {{ display:inline-flex; gap:4px; align-items:center; padding:1px 8px; border-radius:999px; font-size:12.5px; font-weight:600; white-space:nowrap }}
.chip.bullish {{ background:var(--bull-bg); color:var(--text) }} .chip.bullish span {{ color:var(--bull) }}
.chip.bearish {{ background:var(--bear-bg); color:var(--text) }} .chip.bearish span {{ color:var(--bear) }}
.chip.neutral {{ background:var(--neutral-bg); color:var(--text) }} .chip.neutral span {{ color:var(--neutral-ink) }}
.stack {{ display:flex; gap:2px; height:28px; border-radius:6px; overflow:hidden; margin:8px 0 }}
.stack div {{ min-width:2px }} .stack .bearish {{ background:var(--bear) }} .stack .neutral {{ background:var(--neutral) }} .stack .bullish {{ background:var(--bull) }}
.legend {{ display:flex; gap:16px; flex-wrap:wrap; font-size:13px; color:var(--text-2) }}
.legend i {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px }}
.two {{ display:grid; gap:12px; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)) }}
.panel {{ background:var(--surface-2); border:1px solid var(--border); border-radius:10px; padding:14px 16px }}
.panel h3 {{ margin-bottom:8px }}
.list {{ list-style:none; padding:0; margin:0 }} .list li {{ padding:7px 0; border-top:1px solid var(--border) }}
.list li:first-child {{ border-top:0 }}
.date {{ display:inline-block; min-width:96px; font-size:12.5px; color:var(--text-2); font-variant-numeric:tabular-nums }}
.tablewrap {{ overflow-x:auto; border:1px solid var(--border); border-radius:10px }}
table {{ border-collapse:collapse; width:100%; min-width:900px; font-size:13.5px }}
th,td {{ text-align:left; padding:8px 10px; border-top:1px solid var(--border); vertical-align:top }}
th {{ background:var(--surface-2); font-weight:600; color:var(--text-2); border-top:0; position:sticky; top:0 }}
td.num,th.num {{ text-align:right; font-variant-numeric:tabular-nums }}
.card {{ border:1px solid var(--border); border-left:4px solid var(--neutral); border-radius:10px; padding:14px 16px; margin:10px 0; background:var(--surface) }}
.card.bullish {{ border-left-color:var(--bull) }} .card.bearish {{ border-left-color:var(--bear) }}
.card header {{ display:flex; gap:10px; align-items:baseline }} .rank {{ font-weight:700; color:var(--text-2) }}
.card p {{ margin:8px 0 0 }} .meta {{ color:var(--text-2); font-size:13px }}
.facts {{ display:flex; flex-wrap:wrap; gap:6px 14px; margin-top:8px; align-items:center; font-size:13.5px }}
.kv b {{ color:var(--text-2); font-weight:500; margin-right:3px }}
.tags {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:8px }}
.tag {{ font-size:12px; border:1px solid var(--border); border-radius:6px; padding:0 6px; color:var(--text-2) }}
.cues {{ font-size:12px; color:var(--muted) }}
.assess dt {{ font-weight:650; margin-top:10px }} .assess dd {{ margin:2px 0 0 }}
#scatter {{ width:100%; height:300px }} #tip {{ position:fixed; pointer-events:none; background:var(--text); color:var(--surface);
  padding:6px 9px; border-radius:6px; font-size:12.5px; max-width:320px; display:none; z-index:10 }}
.note-box {{ font-size:13px; color:var(--text-2); border:1px dashed var(--border); border-radius:10px; padding:12px 14px; margin-top:12px }}
</style></head>
<body><main>
<h1>Ethereum News Sentiment &amp; Market Impact</h1>
<p class="sub">Generated {_date(r['generated_at'])} · last {r['window_days']} days · sources: {', '.join(e(s) for s in r['sources_fetched'])} ·
scoring: {'Claude' if r['scoring'] == 'claude' else 'rule-based lexicon (see cues on each card)'} · not investment advice</p>

<section class="hero" aria-label="Overall sentiment">
  <div class="lbl">Overall ETH news sentiment</div>
  <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap">
    <span style="font-size:40px;font-weight:700">{ov['score']:+.0f}</span><span class="muted">/ 100</span>
    {chip(env_cls)} <span class="muted">news environment: <b>{e(env)}</b></span>
  </div>
  <div class="gauge" role="img" aria-label="Sentiment {ov['score']:+.0f} on a scale from -100 bearish to +100 bullish">
    <div class="mark" style="left:{gauge_pos:.1f}%"></div></div>
  <div class="gauge-scale"><span>▼ −100 bearish</span><span>● 0 neutral</span><span>+100 bullish ▲</span></div>
  <p class="small muted" style="margin:8px 0 0">Impact × relevance × confidence-weighted mean over {ov['n_events']} distinct events
  (duplicate coverage of one event counted once). {ov['n_eth_specific']} ETH-specific, {ov['n_market_wide']} market-wide/macro.
  {ov['fact_share']:.0%} factual reporting, the rest opinion or speculation.</p>
</section>

<div class="grid">
  <div class="tile"><div class="lbl">▲ Bullish events</div><div class="val">{ov['pct_bullish']:.0f}%</div></div>
  <div class="tile"><div class="lbl">● Neutral events</div><div class="val">{ov['pct_neutral']:.0f}%</div></div>
  <div class="tile"><div class="lbl">▼ Bearish events</div><div class="val">{ov['pct_bearish']:.0f}%</div></div>
  <div class="tile"><div class="lbl">ETH price momentum (separate from news)</div>
    <div class="val">{'$' + format(mom['price'], ',.0f') if mom else 'n/a'}</div>
    <div class="note">24h {_pct(mom.get('ret_24h'))} · 7d {_pct(m7)} · 30d {_pct(mom.get('ret_30d'))} · {e(mom.get('state', ''))}</div></div>
</div>

<h2>Bullish vs bearish</h2>
<div class="two">
  <div class="panel"><h3>Share of distinct events</h3>
    <div class="stack" role="img" aria-label="{ov['pct_bearish']:.0f}% bearish, {ov['pct_neutral']:.0f}% neutral, {ov['pct_bullish']:.0f}% bullish">
      <div class="bearish" style="flex:{ov['pct_bearish']}" title="Bearish {ov['pct_bearish']:.0f}%"></div>
      <div class="neutral" style="flex:{ov['pct_neutral']}" title="Neutral {ov['pct_neutral']:.0f}%"></div>
      <div class="bullish" style="flex:{ov['pct_bullish']}" title="Bullish {ov['pct_bullish']:.0f}%"></div></div>
    <div class="legend"><span><i style="background:var(--bear)"></i>▼ Bearish {ov['pct_bearish']:.0f}%</span>
      <span><i style="background:var(--neutral)"></i>● Neutral {ov['pct_neutral']:.0f}%</span>
      <span><i style="background:var(--bull)"></i>▲ Bullish {ov['pct_bullish']:.0f}%</span></div>
    <p class="small muted">Sentiment ≠ impact. The chart on the right separates them: a story far to one side but low down
    is strongly worded yet unlikely to move ETH.</p></div>
  <div class="panel"><h3>Sentiment vs market impact (one dot per event)</h3>
    <svg id="scatter" role="img" aria-label="Scatter plot of sentiment score against market impact"></svg>
    <div class="legend"><span><i style="background:var(--bear)"></i>▼ Bearish</span><span><i style="background:var(--neutral)"></i>● Neutral</span>
      <span><i style="background:var(--bull)"></i>▲ Bullish</span><span class="muted">hover a dot for the headline</span></div></div>
</div>

<h2>Major catalysts</h2>
<div class="two">
  <div class="panel"><h3>▲ Strongest bullish catalysts</h3>{mini(r['bullish_catalysts'], 'None in this window.')}</div>
  <div class="panel"><h3>▼ Strongest bearish catalysts</h3>{mini(r['bearish_catalysts'], 'None in this window.')}</div>
</div>
<div class="panel" style="margin-top:12px"><h3>Upcoming events that could influence ETH</h3>
  <ul class="list">{''.join(events) or '<li class="muted">None found.</li>'}</ul>
  <p class="small muted">Protocol calls come from the open agenda issues in github.com/ethereum/pm. "In the news" items are
  headlines that mention a scheduled or pending event.</p></div>

<h2>Five most impactful stories</h2>
{top_cards}

<h2>Market impact ranking</h2>
<p class="small muted">Rank score = 35% impact + 25% sentiment strength + 20% ETH relevance + 10% source credibility + 10% novelty. One row per event.</p>
<div class="tablewrap"><table>
<thead><tr><th class="num">#</th><th>Headline</th><th>Sentiment</th><th class="num">Score</th><th class="num">Impact</th>
<th>Horizon</th><th class="num">Conf.</th><th>Type</th><th>Scope</th><th class="num">Rank</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>

<h2>Research assessment</h2>
<div class="panel assess"><dl>
  <dt>Overall ETH news outlook</dt><dd>{e(asm.get('outlook'))}</dd>
  <dt>Most important bullish development</dt><dd>{e(asm.get('top_bullish'))}</dd>
  <dt>Most important bearish development</dt><dd>{e(asm.get('top_bearish'))}</dd>
  <dt>Biggest potential upcoming catalyst</dt><dd>{e(asm.get('top_catalyst'))}</dd>
  <dt>Three stories to monitor most closely</dt><dd><ol>{watch}</ol></dd>
  <dt>News sentiment vs market momentum</dt><dd>{e(asm.get('momentum_note'))}</dd>
</dl></div>

<h2>All article summaries</h2>
{other_cards or '<p class="muted">No further articles.</p>'}

<div class="note-box"><b>How to read this.</b> Every headline links to its original article. Sentiment describes the tone
of the news for ETH, not a forecast. The ETH price tile is market momentum, shown separately so the two are not confused.
Stories about the same event are grouped and counted once. "Priced in?" compares ETH's move since publication with the
headline's direction. It is a heuristic, not proof. Rule-based scores list the words that drove them; run with
<code>--llm</code> for Claude-written reasoning.</div>
</main>
<div id="tip" role="tooltip"></div>
<script>
const pts = {json.dumps(scatter)};
(function() {{
  const svg = document.getElementById('scatter'), tip = document.getElementById('tip');
  const W = svg.clientWidth || 500, H = 300, m = {{l:36, r:12, t:10, b:30}};
  svg.setAttribute('viewBox', `0 0 ${{W}} ${{H}}`);
  const x = v => m.l + (v + 100) / 200 * (W - m.l - m.r), y = v => H - m.b - (v - 1) / 9 * (H - m.t - m.b);
  const ns = 'http://www.w3.org/2000/svg', css = getComputedStyle(document.documentElement);
  const col = s => css.getPropertyValue(s === 'bullish' ? '--bull' : s === 'bearish' ? '--bear' : '--neutral-ink');
  const add = (tag, a) => {{ const n = document.createElementNS(ns, tag); for (const k in a) n.setAttribute(k, a[k]); svg.appendChild(n); return n; }};
  const grid = css.getPropertyValue('--border'), ink = css.getPropertyValue('--muted');
  [-100, -50, 0, 50, 100].forEach(v => {{ add('line', {{x1:x(v), x2:x(v), y1:m.t, y2:H-m.b, stroke:grid, 'stroke-width': v===0?1.5:1}});
    const t = add('text', {{x:x(v), y:H-10, 'text-anchor':'middle', 'font-size':11, fill:ink}}); t.textContent = v; }});
  [1, 4, 7, 10].forEach(v => {{ add('line', {{x1:m.l, x2:W-m.r, y1:y(v), y2:y(v), stroke:grid}});
    const t = add('text', {{x:m.l-6, y:y(v)+4, 'text-anchor':'end', 'font-size':11, fill:ink}}); t.textContent = v; }});
  const lx = add('text', {{x:W-m.r, y:m.t+10, 'text-anchor':'end', 'font-size':11, fill:ink}}); lx.textContent = 'impact ↑ · sentiment →';
  pts.forEach(p => {{
    const c = add('circle', {{cx:x(p.x), cy:y(p.y), r:5, fill:col(p.s), stroke:css.getPropertyValue('--surface'), 'stroke-width':2}});
    const hit = add('circle', {{cx:x(p.x), cy:y(p.y), r:12, fill:'transparent', tabindex:0}});
    const show = ev => {{ tip.style.display='block'; tip.textContent = `${{p.t}} — ${{p.src}} · sentiment ${{p.x>0?'+':''}}${{Math.round(p.x)}} · impact ${{p.y.toFixed(1)}}`;
      const r = (ev.target.getBoundingClientRect ? ev.target.getBoundingClientRect() : {{left:0, top:0}});
      tip.style.left = Math.min(window.innerWidth - 330, (ev.clientX || r.left) + 12) + 'px'; tip.style.top = ((ev.clientY || r.top) + 12) + 'px'; c.setAttribute('r', 7); }};
    const hide = () => {{ tip.style.display='none'; c.setAttribute('r', 5); }};
    hit.addEventListener('mousemove', show); hit.addEventListener('focus', show);
    hit.addEventListener('mouseleave', hide); hit.addEventListener('blur', hide);
  }});
}})();
</script>
</body></html>"""
