# Design guide

**Purpose.** How the demo site looks and is laid out: colour, type, layout, components, charts and each page. It is the source of truth for anything you can see standing still. How things move is in [MOTION.md](MOTION.md); the check before shipping is [CHECKLIST.md](CHECKLIST.md).

**How to read it.** Each rule is one line, an example, then how the site applies it. **Desktop** is wider than 600px, **Phones** 600px and narrower; unmarked holds on both.

---

## 1. Colour

### Palette

| Role | Hex | Use |
|------|-----|-----|
| Page | `#F5F3EE` | Background, header, footer |
| Lifted | `#FBFAF7` | Framed cards and panels |
| Whisper cream | `#EFEAE3` | Product-row cards |
| Hairline | `#E6E1D9` / `#DDD8CF` | Borders and rules |
| Ink | `#1A1A1A` | Text, buttons, the main series; the one near-black |
| Ink 2 | `#5A5650` | Subtitles, secondary text |
| Muted | `#6F6B64` | Every small grey text (labels, axes, eyebrows) |
| Grey mark | `#8E8A82` | Grey dots and lines that are not text |
| Grey series | `#A39E95` | The comparison line in a chart |
| Rust | `#9C4A26` | Success only |
| Orange | `#CF4500` | You / now / the key number |
| Light orange | `#F37338` | Decoration only (orbit arcs, first place); never text on cream |
| Link blue | `#3860BE` | Text links (`#1d3570` on hover), the highlighted bar |

Supporting greys (rules, tracks, fills, map dots): `#E2DDD4` `#EBE7E0` `#EDE9E2` `#ECE7E0` `#EFECE6` `#E8E3DB` `#E8E2DA` `#EFEBE5` `#D9D4CA` `#D6D1C7` `#CFC9BF` `#BDB7AC` `#F3F0EE`. Lifecycle colours, always named beside them: Sustained `#3860BE`, Gradual decline `#1A1A1A`, Flash `#F37338`, Never adopted `#D1CDC7`, Unclear `#696969`. Phones keep one set of tints (Compare's chart panels `#ECE9E3` `#E6ECF8` `#EEEDEB`); desktop uses Whisper cream instead.

### Rules

**C1. Only palette colours.** No new hex anywhere.
- Example: a new hover fill uses `#ECE7E0`, not a fresh grey.
- Here: hover fills, chart tracks and map dots all come from the supporting greys.

**C2. Orange means you, now, or the key number: one cue at a time.** One italic orange word per page title, one orange keyword per Conclusion.
- Example: "Before Terra, **DEX** grew the most (×145)": only *DEX* is orange.
- Here: title words *today, answers, side by side, measured, project, booth, dug down*. Pick a DApp, Neighbours, Game and question or walk titles have none: their orange is elsewhere (Surprise me, your DApp, your level, the Conclusion keyword).

**C3. Rust means success, and nothing else.**
- Example: "Still a success a year later" is rust; a highlighted bar is blue, not rust.
- Here: Outcome: Success on the card; success lines and dots on every chart.

**C4. Blue means "see more", ink means "go on".** The full table of link looks is W5.
- Example: "Read more ›" is blue; "Next →" is bold ink.

**C5. Text must be readable: 4.5:1 for small text, 3:1 for large.**
- Example: small grey labels use `#6F6B64` (4.9:1), not `#8E8A82` (3.1:1).
- Here: the podium's first-place number is ink on light orange; labels on phone tints use Ink 2.

**C6. Ethereum stays quiet.** Line-drawn marks only; no ETH purple, no gradients.
- Example: a 9% ghost diamond behind Home's hero.
- Here: the mark before the site title and in the browser tab.

---

## 2. Type

| Role | Font | Size |
|------|------|------|
| Titles | Newsreader 400 | 36–52px on every page (scales with the window) |
| Subtitle | Plus Jakarta Sans | 17px, Ink 2, max 560px, 18px under the title |
| Body | Plus Jakarta Sans | |
| Labels, numbers in tables | JetBrains Mono | 11.5px, tracked +0.14em |

**T1. Three fonts, nothing else.**
- Example: no Inter, no Space Grotesk.
- Here: only these three are loaded from Google Fonts.

**T2. Numbers that line up or change use tabular figures.**
- Example: a counter going 9 → 10 does not shift sideways.
- Here: tables, tooltips, filter values, the game's X / Y.

**T3. Readable lines: 60–75 characters, no widows.** Titles and paragraphs fill their lines and avoid a lone last word; a question title should fit one line on desktop.
- Example: a subtitle wraps at 560px instead of shrinking.
- Here: `text-wrap: pretty` everywhere (balance cut every line short and left a blank block on the right); "2020 – 2025" never splits.

**T4. A small grey label only names what nothing else names.**
- Example: no "1 of 3" on a slide when the dots already show it.
- Here: chart titles are short grey caps (about 33 characters) that also serve as the chart's accessible name.

**T5. Mono only where it earns it: labels, codes and numbers that line up.** Never for sentences.
- Example: a block hash and a table's numbers are mono; the line explaining them is not.
- Here: eyebrows, axis labels, table figures, the card's block hash.

---

## 3. Layout

**L1. Phones at 600px.** Crossing 600px redraws the page.
- Example: Compare is a swipe row on phones, a card row on desktop.
- Here: narrow desktop windows (601–1000px) give card labels two lines.

**L2. One rule for page heads: title on top, explanation under it.** Every page, Home included, uses one title size (`clamp(36px, 4vw, 52px)`), puts the explanation 18px under the title at most 560px wide, and starts the next block 32px under the explanation. The first line sits 24px under the header.
- Example: at 1280px every title starts at 199px, its explanation 18px below.
- Here: Home, About and Game keep a card on the right (At a glance, the QR code, the start card), its top level with the title. Pages with a "← Home" row start their head below it.

**L3. Pages scroll down; sets of parallel cards scroll sideways.**
- Example: More ways in, the era cards, Method's rows on phones.
- Here: unframed items and sequences stack on phones instead of swiping (About's sources, Home's three layers).
- Here: phone swipe cards are about 84% wide so the next one peeks in and snaps; desktop sliders show dots.

**L4. Nothing jumps.** Cards in a row keep equal line counts; labels have room reserved.
- Example: every Method card keeps two lines for its explanation.
- Here: bar charts size their margin from the longest label; nothing pops in mid-walk.

**L5. Fixed bars clear the phone's safe area.**
- Example: Method's tab bar sits `12px + env(safe-area-inset-bottom)` above the edge.
- Here: Method's tabs, the game's levels and Compare's Dig in bar all float at the bottom as one pill row. Floating bars switch views; reading order (questions, walks) uses the row at the end of the page (K5).

**L6. The eyebrow appears only when it adds something.**
- Example: "Q2 · Survival" with the Predict tag; Compare has no eyebrow.
- Here: on walks and questions the eyebrow holds the progress strip (done steps ink, this step an orange Ethereum mark, the rest grey); on walks it opens Your path; on question pages it only shows where you are.

**L7. Every section has the same rhythm.** Section title, a hairline 16px under it, the content 24px under the hairline (16px on phones), and the next section title 64px after the content. A "… ›" link on the title row must not make that row taller. Space does the grouping: things that belong together sit closer than things that do not; lines and frames come after (K1).
- Example: Home's four sections, About's and Method's section heads all measure 16 / 24 / 64 (16 / 16 / 64 on phones).
- Here: gaps are measured from the first and last thing you can see (text, a chart, a filled card), not from empty padding.

**L8. One main thing per screen, and it is the biggest.** Size follows importance; the one action that moves on is the one that stands out.
- Example: on a question page the Conclusion is the largest text after the title, and the chart is the largest object.
- Here: one ink pill or one bold "→" per screen (W5); Home leads with the market chart.

**L9. Align by eye, not by box.** Optical centre beats the bounding box when they disagree.
- Example: a triangle in a circle sits slightly right of the box's centre so it looks centred.
- Here: Home's peak dot sits on the line's highest point, not in the middle of its label.

Page order: Home, Questions, Compare, Neighbours, Game, Booth, then Method and About. On phones the links move into a ☰ menu.

---

## 4. Components

**K1. Frames only where you click or where state lives.** Charts and info sit on the page with a hairline on top.
- Example: a Neighbours closest card is framed; a Question chart is not.
- Here: framed: Compare and More ways in cards (Whisper cream, 28px, no border); Neighbours' cards and the game's finish card (Lifted, hairline, 20px). Unframed: Home's three layers, every Method slide (Success labels, Signals groups, funnel, data charts; a hairline on top), About's sources. Kept framed on purpose: Method's success-rule panel and About's QR card.

**K2. Shapes.** 28px for large frames, 20px for small cards, pills (999px) only for buttons, chips, tags, inputs and the nav. No hard shadows: a soft halo `0 24px 48px rgba(0,0,0,.08)`.
Nested corners: inner radius = outer radius − the padding between them (never more than the outer).
- Example: the game's finish card is 28px with the halo, no ink border; a 28px card with 20px padding holds 8px inner corners.
- Here: round icon buttons (☰ ✕ ⇄ ↻) are a thin `#DDD8CF` outline, no fill: 32px, or 42px for arrows and ☰.

**K3. What looks clickable is clickable, and only that.** When a card holds a link, only its round arrow opens it.
- Example: on a More ways in card, only the › at the bottom right is a link.
- Here: the same on About's Method tile; the card itself has no hover halo.

| Button | Rest | Hover or tap |
|--------|------|--------------|
| Ink pill, 40px (Start with …, Dig in, the tour's Next) | Ink, cream text, 14.5px, 20px sides | Orange sweeps in from the left |
| Large pill, 48px (Start the game; Surprise me) | Ink or, on Pick a DApp, orange | Orange sweeps in; Surprise me sweeps ink |
| Outline pill and round icon, 32px (tour Back; ✕ ⇄) | Hairline `#DDD8CF` | Edge turns ink |
| Round arrow, 42px (44px on phones) | Ink chevron in a faint circle | Orange fill, cream chevron |
| Blue text link ("… ›") | Link blue | Darker blue `#1d3570` |
| Dashed add card | Dashed hairline | Plus, words and edge turn orange |
| Ethereum mark (save, Compare) | Outlined mark | Fills orange (saved) or ink (hover) |

Every pill shrinks to 97% while pressed (M7).

**K4. Every "… ›" link sits at the right end of its heading row**, above the content.
- Example: "Read more ›" on a chart's title row; "What happened ›" on The whole market.
- Here: on the card page, "See it ›" sits inside the line that confirms the save, not in a heading row.

**K5. One way forward.** On a walk step or a question page only Next moves on; a plain grey back link sits left, bold "Next →" right.
- Example: choices inside a page never say "→".
- Here: the chosen era card shows a 2px orange border, not "Selected".

**K6. Show the answer first, details on request.**
- Example: notes under a chart fold into "Read more ›" and open in a sheet.
- Here: details open from a short blue text link, never a bare icon; a group of slides shares one "Read more ›" on its section head (Method's three labels), or each name opens its own (Signals, K9). A note that is only a short colour key (under 60 characters, like Neighbours' success or not) stays under the chart: a sheet must hold more than a tap costs.

**K7. Touch targets are at least 44 × 44px on phones**, even when the visible button is smaller.
- Example: the swipe dots look 7px but take a 44px-tall tap.
- Here: an invisible `::before` area fills the gap; the ✕ on Compare cards is always visible because phones have no hover.

**K8. Sheets, menus, tooltips and search behave one way.**
- Example: a sheet rises from the bottom on phones and is a 520px side panel on desktop; ✕, a tap outside or Esc closes it.
- Here: every sheet is a Newsreader heading, a grey mono line, then body text; tooltips stay fully on screen; focus rings are ink, except Compare's search (a cream pill showing only the caret).

**K9. A dotted underline means "tap for what this measure means".** Only on measure or signal names, inside a chart, table or panel, where the reader is using the name to judge something.
- Example: in the game's task, "active wallets" opens that measure's card in a sheet.
- Here: also the signal names in "What should it watch?", the two measures in Neighbours' readout and the six group names on Method's Signals tab. Never in a Conclusion, a title or a button; the definitions come from `MET` and `D.method.features`.

**K10. One icon family.** Line-drawn, one stroke weight, one size per place; no mixing of filled and outline, emoji or stock sets.
- Example: ☰ ✕ ⇄ ↻ share the same thin round button (K2).
- Here: the drawn icons (`ICO` in views.js) share one 32px grid and a 1.6 stroke; the Ethereum mark is the only brand mark.

---

## 5. Charts

**H1. Line names sit at the end of their own line**, never in a label column, and never overlap.
- Example: "Uniswap V3" at the end of the rust line; if blocked, it moves under the line, within about 90px.
- Here: the DApp's own name takes the closest spot before grey reference names.

**H2. Phones draw on a smaller, taller canvas so labels stay readable.**
- Example: 560-wide charts (980 on desktop); maps 560 × 560 on phones, 980 × 540 on desktop.
- Here: long axis captions split at "·"; crowded month ticks show every other label.

**H3. Every chart says what it shows.** A short grey title with "Read more ›" on one row; small charts name their axes.
- Example: Compare's sheet chart reads Peak / 0 and Launch / Year 1 / Year 2.
- Here: era breaks are named on the chart ("Terra", "Dencun"); the Merge appears only in What happened.

**H4. Real charts and real numbers only.** No stock illustration, mock screenshot or placeholder; every number comes from [results/CHART_DATA.md](results/CHART_DATA.md).

---

## 6. Words

All site copy is English.

**W1. A Conclusion leads with the answer: one sentence with its number in brackets and one orange keyword, then at most one short sentence.** Anything more goes in the small line under it.
- Example: "Before Terra, **DEX** grew the most (×145) and DeFi grew the least (+63%)."
- Here: every sentence lives in [site/js/copy.js](site/js/copy.js) (the code only picks one and fills in the numbers); [review/conclusions.md](review/conclusions.md) holds every filled-in result for checking.

**W2. An era opens a sentence as words, and is labelled with an arrow only in controls.**
- Example: "Between Terra and Dencun, DeFi …" in a sentence; "Terra → Dencun" on the era switch.
- Here: Before Terra / Between Terra and Dencun / After Dencun.

**W3. One way to write each kind of number.**
- Example: big counts 275K, 1.1M; shares 22%; ranks #14 of 122; months Dec 2025.
- Here: a change below doubling is a signed percent with a real minus (+63%, −72%); doubling or more is a multiple (×2.6, ×145).

**W4. Ranges use an en dash with spaces; no em dashes in copy.**
- Example: "2020 – 2025", "months 10–12".
- Here: "—" appears only as the empty mark in a leaderboard slot.

**W5. A text link's job sets its sign, colour and weight.** One look per job, everywhere:

| Job | Looks like | Sign | Examples |
|-----|-----------|------|----------|
| Go on along this path | Ink `#1A1A1A`, semibold (600) | → after | "2 · Standing →", "Q3 · Concentration →", "See your card →", "Walk another DApp →", "Dig into Lido →" |
| Go back | Ink 2 `#5A5650`, regular | ← before | "← 1 · Shape", "← Q1 · Categories", "← Home", "← All" |
| See more, or step aside to another page | Link blue `#3860BE`, regular; darker blue on hover | › after | "Read more ›", "Notes and limits ›", "See it ›", "Play the game ›", "Method ›" |
| Start a path | Ink pill (K3), not a text link | → after | "Start with the market →", "Start the game →" |

- Example: on the card page "Walk another DApp →" is ink and bold (it goes on); "See it ›" is blue (it steps aside to the booth).
- Here: blue never carries "→", ink never carries "›"; at most one bold "→" per screen. Sentence case everywhere ("Today at the booth", not "Today At The Booth").

**W6. Plain, specific words, headlines included.** Say what the data shows; no marketing words; a title names its subject, not a generic section.
- Example: "Six months on, Lido kept 48% of its first users", not "unlock powerful insights".
- Here: every value says what it is a share of ("22% of DeFi wallets").

---

## 7. Pages

Only what is particular to each page.

| Page | Rules |
|------|-------|
| **Home** | Market strip: three slides, dots as the only control, one orange dot on the peak. At a glance: three tiles. Three layers: unframed Market, Category, DApp; buttons say where they go ("Start with the market →", "Start with one DApp →"). Booth: the card tank and a podium. More ways in: four cards. |
| **Questions** | The list shows six cards in three columns, all one height (desktop). A question page: eyebrow, question, era switch, Conclusion, chart, then "← Q1 · Categories" and "Q3 · Concentration →" at the end, like a walk; Q6 ends on "All questions →". "← All" leads back to the six questions. Orange keyword: Q1 top category, Q2 strongest signal, Q3 top-10 share, Q4 successful share, Q5 share kept, Q6 growers' retention. |
| **Walks** | One column; the picker ("Following Lido ▾") sits under the chart title; on phones it is plain text, not a pill. The category and leader you follow are the subject of the steps after you pick them; on bar charts the line under the Conclusion says what the bars are and where yours ranks. "What they share": the title names the leader; the Conclusion is how the model's weight moved ("stickiness rose from 17% to 33% … as size fell": "as", never "because", since shares add up to 100%); the line under it compares the leader with the other four leaders in plain words; the chart shows the five groups across eras with your era shaded. DApp walk: the keyword is the shape, rank, lookalikes, group, then the verdict. "What should it watch?" shows the era's five strongest signals as a ranked table (signal, group, share, cumulative; no effect column, since a coefficient's sign holds only with the other 26 fixed; from data/coef_by_period.csv via script/build_signals.py), with the DApp's own value on one of them in the line under the Conclusion. |
| **Summary card** | A business card: name, category and era, five steps as label and value, block hash. Only one-DApp cards can be saved, by tapping the Ethereum mark. A line under the title says what the card is and how to save it. Next step in bold: "Walk another DApp →", or "Dig into Lido →" for market walks; once saved, "Saved to today's booth. See it ›" appears under it. |
| **Compare** | Three cards; add and remove on the cards; no table under them. Learn more: overlaid curves, then every number in one column per DApp; the names stay pinned at the top; ▲ marks the row's leader and says so on hover; seven plain rows, no section labels: category, era launched, peak wallets, shape, months to 10K, first users kept at month 6, success a year later. Phones: swipe row with a floating Dig in bar. |
| **Pick a DApp** | Name river with search and Surprise me; three era cards (the chosen one has an orange border); one line at the end, "Not listed yet? Place your own numbers ›" (reason in grey, link in blue). |
| **Neighbours** | Unframed filters read as axis settings. Closest cards show lifecycle as a colour dot and Compare as the Ethereum mark. Desktop: a 270px card column beside the map. Phones: filters, map, readout, then a swipe row. |
| **Game** | Question, one-line task, level pills (floating), map. The task's two measure words open their card (K9), so the map has no "Read more". The map's scope caption shows only on phones; on desktop the level row already names it. The level result replaces the task line. Finish card over the map, then your rank today. A game stops itself after 1 minute idle or 10 minutes in all. |
| **Today at the booth** | Saved cards tank and today's top 10, each with its link. Cards drift as small souvenirs (name and block hash), stored only in that browser; two example cards keep the tank from being empty. |
| **Method** | One title; the lede follows the tab; tabs float at the bottom; every slide is unframed with a hairline on top. Success: the rule, then "Three labels, only one is success" ("85 of 512", "25 of 622", "55 of 170") with one "Read more ›" on its section head. Signals: one slide per group, its name dotted (K9) and one plain line ("Size · How big it is"); the sheet holds the group's weight per era and its signals. Data: the 1,816 → 512 funnel with each step's share, then three charts. |
| **About** | Head like Home's (QR card on the right, desktop only). Three data sources as unframed columns, each matching a More ways in card (icon, title, line, arrow) without the frame; stacked on phones. Method's round arrow is the only link, at the bottom right. |
