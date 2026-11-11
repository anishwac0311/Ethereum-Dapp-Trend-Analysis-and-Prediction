# Design guide

**Purpose.** How the demo site looks and is laid out: colour, type, layout, components, charts and each page. It is the source of truth for anything you can see standing still. How things move is in [MOTION.md](MOTION.md); the check before shipping is [UI-CHECKLIST.md](UI-CHECKLIST.md).

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
| Ink | `#1A1A1A` | Text, buttons, the main series |
| Ink 2 | `#5A5650` | Subtitles, secondary text |
| Muted | `#6F6B64` | Every small grey text (labels, axes, eyebrows) |
| Grey mark | `#8E8A82` | Grey dots and lines that are not text |
| Grey series | `#A39E95` | The comparison line in a chart |
| Rust | `#9C4A26` | Success only |
| Orange | `#CF4500` | You / now / the key number |
| Light orange | `#F37338` | Decoration only (orbit arcs, first place); never text on cream |
| Link blue | `#3860BE` | Text links (`#1d3570` on hover), the highlighted bar |
| Dark panel | `#141413` | A few "read this" panels, never clickable |

Supporting greys (rules, tracks, fills, map dots): `#E2DDD4` `#EBE7E0` `#EDE9E2` `#ECE7E0` `#EFECE6` `#E8E3DB` `#E8E2DA` `#EFEBE5` `#D9D4CA` `#D6D1C7` `#CFC9BF` `#BDB7AC` `#F3F0EE`. Lifecycle colours, always named beside them: Sustained `#3860BE`, Gradual decline `#141413`, Flash `#F37338`, Never adopted `#D1CDC7`, Unclear `#696969`. Phones keep two tints (game start picture `#F4E6DC`; Compare's chart panels `#ECE9E3` `#E6ECF8` `#EEEDEB`); desktop uses Whisper cream instead.

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

**C4. Blue means "see more", ink means "go on".**
- Example: "Read more ›" is blue; "Next →" is bold ink.
- Here: every "… ›" link is blue; Next, Dig in and Let's go are ink.

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

**T3. Readable lines: 60–75 characters, no widows.** Titles balance their lines; paragraphs avoid a lone last word.
- Example: a subtitle wraps at 560px instead of shrinking.
- Here: `text-wrap: balance` on titles, `pretty` on paragraphs; "2020 – 2025" never splits.

**T4. A small grey label only names what nothing else names.**
- Example: no "1 of 3" on a slide when the dots already show it.
- Here: chart titles are short grey caps (about 33 characters) that also serve as the chart's accessible name.

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
- Example: the Q1–Q6 bar sits `12px + env(safe-area-inset-bottom)` above the edge.
- Here: Q1–Q6, Method's tabs, the game's levels and Compare's Dig in bar all float at the bottom as one pill row.

**L6. The eyebrow appears only when it adds something.**
- Example: "Q2 · Survival" with the Predict tag; Compare has no eyebrow.
- Here: on walks and questions the eyebrow holds the progress strip (done steps ink, this step an orange Ethereum mark, the rest grey); it opens Your path or the question list.

**L7. Every section has the same rhythm.** Section title, a hairline 15px under it, the content 24px under the hairline (16px on phones), and the next section title 64px after the content. A "… ›" link on the title row must not make that row taller.
- Example: Home's four sections all measure 15 / 24 / 64 (15 / 16 / 64 on phones).
- Here: gaps are measured from the first and last thing you can see (text, a chart, a filled card), not from empty padding.

Page order: Home, Questions, Compare, Neighbours, Game, Booth, then Method and About. On phones the links move into a ☰ menu.

---

## 4. Components

**K1. Frames only where you click or where state lives.** Charts and info sit on the page with a hairline on top.
- Example: a Neighbours closest card is framed; a Question chart is not.
- Here: framed: Compare, More ways in and Method's ⋯ cards (Whisper cream, 28px, no border); Neighbours' cards and the game's finish card (Lifted, hairline, 20px). Unframed: Home's three layers, Method's funnel and data charts, About's sources. Kept framed on purpose: Method's success-rule panel and About's QR card.

**K2. Shapes.** 28px for large frames, 20px for small cards, pills (999px) only for buttons, chips, tags, inputs and the nav. No hard shadows: a soft halo `0 24px 48px rgba(0,0,0,.08)`.
- Example: the game's finish card is 28px with the halo, no ink border.
- Here: round icon buttons (☰ ✕ ⇄ ↻ ⋯) are a thin `#DDD8CF` outline, no fill.

**K3. What looks clickable is clickable, and only that.** When a card holds a link, only its round arrow opens it.
- Example: on a More ways in card, only the › at the bottom right is a link.
- Here: the same on About's Method tile; the card itself has no hover halo.

| Button | Rest | Hover or tap |
|--------|------|--------------|
| Round arrow | Ink chevron in a faint circle; 42px desktop, 44px phones | Orange fill, cream chevron |
| Ink start button | Ink pill, cream text | Orange sweeps in from the left |
| Plain pill ("Dig in") | Ink pill | No change |
| Dashed add card | Dashed hairline | Plus, words and edge turn orange |
| Ethereum mark (save, Compare) | Outlined mark | Fills orange (saved) or ink (hover) |

**K4. Every "… ›" link sits at the right end of its heading row**, above the content.
- Example: "Read more ›" on a chart's title row; "What happened ›" on The whole market.
- Here: the one exception is "See today at the booth ›" under the card page's title.

**K5. One way forward.** On a walk step only Next moves on; a plain grey back link sits left, bold "Next →" right.
- Example: choices inside a page never say "→".
- Here: the chosen era card shows a 2px orange border, not "Selected".

**K6. Show the answer first, details on request.**
- Example: notes under a chart fold into "Read more ›" and open in a sheet.
- Here: slides use a round ⋯ for details; everything else uses a short blue text link, never a bare icon.

**K7. Touch targets are at least 44 × 44px on phones**, even when the visible button is smaller.
- Example: the swipe dots look 7px but take a 44px-tall tap.
- Here: an invisible `::before` area fills the gap; the ✕ on Compare cards is always visible because phones have no hover.

**K8. Sheets, menus, tooltips and search behave one way.**
- Example: a sheet rises from the bottom on phones and is a 520px side panel on desktop; ✕, a tap outside or Esc closes it.
- Here: every sheet is a Newsreader heading, a grey mono line, then body text; tooltips stay fully on screen; focus rings are ink, except Compare's search (a cream pill showing only the caret).

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

---

## 6. Words

All site copy is English.

**W1. A Conclusion leads with the answer: one sentence with its number in brackets and one orange keyword, then at most one short sentence.** Anything more goes in the small line under it.
- Example: "Before Terra, **DEX** grew the most (×145) and DeFi grew the least (+63%)."
- Here: every question page and walk step; [review/conclusions.md](review/conclusions.md) holds them all for checking.

**W2. An era opens a sentence as words, and is labelled with an arrow only in controls.**
- Example: "Between Terra and Dencun, DeFi …" in a sentence; "Terra → Dencun" on the era switch.
- Here: Before Terra / Between Terra and Dencun / After Dencun.

**W3. One way to write each kind of number.**
- Example: big counts 275K, 1.1M; shares 22%; ranks #14 of 122; months Dec 2025.
- Here: a change below doubling is a signed percent with a real minus (+63%, −72%); doubling or more is a multiple (×2.6, ×145).

**W4. Ranges use an en dash with spaces; no em dashes in copy.**
- Example: "2020 – 2025", "months 10–12".
- Here: "—" appears only as the empty mark in a leaderboard slot.

**W5. Links and buttons say where they go, with one fixed sign.** "›" for see more, "→" for go on.
- Example: "Read more ›", "What happened ›"; "Next →", "Dig into Lido →".
- Here: sentence case everywhere ("Today at the booth", not "Today At The Booth").

**W6. Plain, specific words.** Say what the data shows; no marketing words.
- Example: "Six months on, Lido kept 48% of its first users", not "unlock powerful insights".
- Here: every value says what it is a share of ("22% of DeFi wallets").

---

## 7. Pages

Only what is particular to each page.

| Page | Rules |
|------|-------|
| **Home** | Market strip: three slides, dots as the only control, one orange dot on the peak. At a glance: three tiles. Three layers: unframed Market, Category, DApp; buttons say where they go ("Start with the market →", "Start with one DApp →"). Booth: the card tank and a podium. More ways in: four cards. |
| **Questions** | The list shows six cards in three columns, all one height (desktop). A question page: eyebrow, question, era switch, Conclusion, chart. Q1–Q6 float at the bottom (names spelled out on desktop). Orange keyword: Q1 top category, Q2 strongest signal, Q3 top-10 share, Q4 successful share, Q5 share kept, Q6 growers' retention. |
| **Walks** | One column; the picker ("Following Lido ▾") sits under the chart title. The category and leader you follow are the subject of the steps after you pick them; on bar charts the line under the Conclusion says what the bars are and where yours ranks. "What they share": the title names the leader; the Conclusion is how the model's weight moved ("stickiness rose from 17% to 33% … as size fell": "as", never "because", since shares add up to 100%); the line under it compares the leader with the other four leaders in plain words; the chart shows the five groups across eras with your era shaded. DApp walk: the keyword is the shape, rank, lookalikes, signal, then the verdict. |
| **Summary card** | A business card: name, category and era, five steps as label and value, block hash. Only one-DApp cards can be saved, by tapping the Ethereum mark. Under it: "See today at the booth ›" and, for market walks, "Dig into Lido →". |
| **Compare** | Three cards; add and remove on the cards; no table under them. Learn more: overlaid curves, then every number in one column per DApp, ▲ for the leader. Phones: swipe row with a floating Dig in bar. |
| **Pick a DApp** | Name river with search and Surprise me; three era cards (the chosen one has an orange border); two short "other ways in" rows at the end. |
| **Neighbours** | Unframed filters read as axis settings. Closest cards show lifecycle as a colour dot and Compare as the Ethereum mark. Desktop: a 270px card column beside the map. Phones: filters, map, readout, then a swipe row. |
| **Game** | Question, one-line task, level pills (floating), map. The level result replaces the task line. Finish card over the map, then your rank today. A game stops itself after 1 minute idle or 10 minutes in all. |
| **Today at the booth** | Saved cards tank and today's top 10, each with its link. Cards drift as small souvenirs (name and block hash), stored only in that browser; two example cards keep the tank from being empty. |
| **Method** | One title; the lede follows the tab; tabs float at the bottom. Success: three labels and the step-by-step rule. Signals: one card per group. Data: the 1,816 → 512 funnel with each step's share, then three charts, unframed. |
| **About** | Head like Home's (QR card on the right, desktop only). Three data sources as unframed columns, each matching a More ways in card (icon, title, line, arrow) without the frame; stacked on phones. Method's round arrow is the only link, at the bottom right. |
