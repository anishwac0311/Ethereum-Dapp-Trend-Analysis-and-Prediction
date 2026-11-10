# Design guide

The rules the demo site actually follows. The look borrows Mastercard's warm cream canvas and colour roles, set in our own type so the pages read like a research paper. Everything here is the default `study` theme in `site/index.html`; the other themes in that file (`?theme=cream`, `ink`, …) are early experiments and are not used.

**How this guide is laid out.** Sections 1–8 are the system: rules that hold on every page. Section 9 goes page by page and only says what is particular to that page. Where desktop and phones differ, a bullet says **Desktop** or **Phones**; anything unmarked holds on every screen. Motion, button states and touch feedback are in [MOTION.md](MOTION.md).

1. [Colours](#1-colours)
2. [Type](#2-type)
3. [Layout and spacing](#3-layout-and-spacing)
4. [Shapes, frames and cards](#4-shapes-frames-and-cards)
5. [Buttons and links](#5-buttons-and-links)
6. [Sheets, menus and pop-ups](#6-sheets-menus-and-pop-ups)
7. [Charts and maps](#7-charts-and-maps)
8. [Motion](#8-motion)
9. [Pages](#9-pages)

---

## 1. Colours

### Palette

| Role | Hex | Used for |
|------|-----|----------|
| Page | `#F5F3EE` | Page background, header, footer |
| Lifted | `#FBFAF7` | Cards and frames that sit on the page |
| Hairline | `#E6E1D9` / `#DDD8CF` | Card borders and rules |
| Ink | `#1A1A1A` | Text, buttons, the main chart series |
| Ink 2 | `#5A5650` | Subtitles and secondary text |
| Muted | `#8E8A82` | Labels, axis text |
| Grey series | `#A39E95` | The comparison series in a chart ("other", "one-hit") |
| **Rust** | `#9C4A26` | **Success only**: "still active a year later", on every chart and card |
| **Orange** | `#CF4500` | **"You / now / the key number"**: one orange cue per page |
| Light orange | `#F37338` | Decoration only: orbit arcs, first place on the leaderboard, key numbers inside dark panels. Too light for text on cream |
| Link blue | `#3860BE` | Every text link (`#1d3570` on hover) and the highlighted bar in a bar chart |
| Dark panel | `#141413` | A few "read this" panels, never on something clickable |
| Whisper cream | `#EFEAE3` | Product-row cards, the success-rule panel on Method |

**Supporting neutrals.** A few warm greys sit between the hairlines and the text colours. They are part of the palette on every screen; nothing else may be added.

| Hex | Used for |
|------|----------|
| `#E2DDD4` | Chart rules and bands, the hairline on top of figures |
| `#EBE7E0` / `#EDE9E2` | Row dividers inside lists and tables (Compare search list, Method funnel) |
| `#ECE7E0` / `#EFECE6` | Soft fills: small round buttons, hover on list rows, empty bar tracks |
| `#E8E3DB` / `#E8E2DA` / `#EFEBE5` | Empty bar tracks and the faint area under small sparklines |
| `#D9D4CA` / `#D6D1C7` | Chart polygons and histogram bars that sit behind the data |
| `#CFC9BF` | Background dots on the maps, names not picked yet on Neighbours |
| `#BDB7AC` | Outline of the small Describe / Predict tags, open places on the leaderboard |
| `#6F6B64` | Axis numbers on scatter maps |
| `#F3F0EE` | Text on ink buttons |

**Lifecycle colours** are always shown with their name beside them, or with a key that names them: Sustained `#3860BE`, Gradual decline `#141413`, Flash `#F37338`, Never adopted `#D1CDC7`, Unclear `#696969`.

**Tints.** Desktop uses no tints outside the tables above: the game start card's picture panel and the chart panel in Compare's Learn more sheet are Whisper cream. Phones keep two tints: the game start picture (`#F4E6DC`) and the per-DApp chart panel in Compare's Learn more sheet (`#ECE9E3`, `#E6ECF8`, `#EEEDEB`).

### Orange means you, now, or the key number

- **One orange word per page title**, in italic (`<em class="o-word">`):

  | Page | Word |
  |------|------|
  | Home | *today* |
  | Questions | *answers* |
  | Compare | *side by side* |
  | Method | *measured* |
  | About | *project* |
  | Today at the booth | *booth* |
  | Summary card | *dug down* (the title follows the card: "DeFi, dug down") |

  On Home it pairs with the orange latest-month dot in the market strip; both mean "now". Neighbours and Game already use orange for the visitor's own DApp and the level numbers, so their titles stay ink.
- **One key number** a page builds to may be orange as well: Method's funnel ends on 512 (the DApps the study uses).
- **One orange keyword in every Conclusion** (see Questions and Walks in section 9 for each one). In the success walkthrough on Method, the verdict in a step title is orange: "DragonQuest: not a success", "The grey DApp: a success".
- **Where you are**: the current step in the progress strip (an orange Ethereum mark), the level being played (orange outline; an orange top line on desktop), the chosen era card (2px orange border), the "Predict" tag on Q2 (orange outline and text; Describe stays grey), the game's quit ✕ cross, your rank on the game's end screen.
- **Hover and tap** on round arrows, the dashed add card and the ink start buttons (MOTION.md).

### Rust means success

Rust is reserved for success, so nothing else uses it: a card's Outcome of Success, success lines and dots on every chart. Highlighted bars, the "Level done" label and every focus ring are not rust; they use ink and Link blue.

### Blue means see more

Link blue text means "see more" (Read more ›, Your path ›, What happened ›). Going on is ink (Next →, Dig in, Let's go). The two are never mixed up. See section 5.

### Ethereum, kept quiet

A line-drawn Ethereum diamond sits before the site title and in the browser tab, and Home has one large ghost diamond at 9% opacity behind the hero. No ETH purples or gradients.

---

## 2. Type

| Role | Font | Size |
|------|------|------|
| Titles | Newsreader (serif), weight 400 | 52px on inner pages (51.2px rendered), 68px on Home and Questions |
| Subtitle under every title | Plus Jakarta Sans | 17px, Ink 2, max 720px wide, 18px below the title |
| Body | Plus Jakarta Sans | |
| Labels, eyebrows, numbers in tables | JetBrains Mono | 11.5px, tracked +0.14em |

- **Tabular numbers.** Every number that sits in a column or changes in place (tables, chart readouts, tooltips, filter values, the game's X/Y) uses `font-variant-numeric: tabular-nums`, so digits line up and a changing value does not wiggle.
- **Line length.** Body text and subtitles stop at about 60–75 characters a line (subtitles max 720px); wider text gets a narrower column, not a smaller font.
- **Leading.** Titles are tight (about 1.05–1.1); body text is about 1.5.
- **Widows.** A title or subtitle should not end with one short word alone on its last line; titles use `text-wrap: balance` and paragraphs `text-wrap: pretty`, so the browser evens out the lines; if a word is still left alone, reword it. A year range such as "2020 – 2025" never splits across lines.
- **Tracking.** Only the mono labels are tracked (+0.14em). Serif titles and sans body keep the font's own spacing; kerning is left to the fonts.
- **Small grey labels only name things nothing else names.** Swipe slides carry no "1 of 3" counter (the dots already show it), and Home's "Market › Category › DApp" caption is hidden because the layer cards say the same.
- **Chart titles** are short, in small grey caps, and are also the chart's accessible name ("The same model in each era", "Wallet change by category", "Share of the category's wallets"). Names are kept to about 33 characters; longer ones end in "…".

---

## 3. Layout and spacing

### Breakpoints

- **Phones**: 600px and narrower. **Desktop**: wider than 600px. Side-by-side page heads start at 901px. Narrow desktop windows (601–1000px) give card labels two lines and explanations three (four below 800px).
- Crossing 600px while the page is open redraws it in the right mode.
- Touch screens drop the dark hover outline that would otherwise stick on a card after a tap.

### Page order

The pages are in the order a visitor uses them: Home, Questions, Compare, Neighbours, Game, Booth (Today at the booth, `#wall`), then the reading pages Method and About. **Phones**: the page links move into a ☰ menu that slides in from the left; tapping a page, the backdrop, ✕ or Esc closes it.

### Page heads

- Every page's first line, eyebrow or title, starts 24px under the header. The first thing after the subtitle (a section heading, the filters, the cards) starts 32px under it.
- **Desktop, 901px and wider: one rule for side-by-side heads.** The title starts at the page's left edge; the explanation always sits in the same column (58.5% in, 37.5% wide); the explanation's last line sits on the same baseline as the title's last line, not just the same box bottom. This holds for Questions, Compare, Pick a DApp, Neighbours, Today at the booth and Method at 1024, 1280 and 1440px. All pages use the same width (1380px). Game and About stack their title and explanation, because their right-hand side holds the start card and the QR code.
- **Eyebrow.** The small row above a title stays on one line (walks write "2 of 5" without "Step"). The back button (a thin outline, no fill) sits left and the Describe / Predict tag at the right edge. A small solid orange Ethereum mark (7 × 11px) marks the eyebrow only when it adds something the title does not say (the question number and tag, the step in a walk). Pages whose title already says where you are have no eyebrow; the game's eyebrow is left to its level tiles, so it keeps only the quit ✕.

### Progress strip

- On walks and Question pages the eyebrow's middle is a progress strip: steps before this one are short ink bars, this one is a small solid orange Ethereum mark, the ones after it grey, then ▾. It depends only on position, so going back and forth never changes how it looks.
- It is a button: on walks it opens "Your path" (the choices made so far, so the path needs no row of its own); on Question pages it opens "All six questions".
- Only the strip is centred, between ← Home and the Describe tag; everything else in the head is left-aligned.
- **Desktop**: a larger strip (28px bars, a 15 × 24 Ethereum mark).

### Scroll direction

- Pages scroll top to bottom. A set of parallel cards scrolls left to right instead (Home's three layers, More ways in, About's data sources, the era cards, Neighbours' closest on phones, Method's rows on phones).
- **Phones**: each swipe card is about 84% wide so the next one peeks in, and swiping snaps to a card. Cards in one row share the same height, padding, label rule and title position.
- **Desktop**: rows that slide (the market strip, More ways in) show dots under them; click a dot to jump, and the dots follow when you scroll.
- Side-by-side panels stack on phones.

### Floating bars

Question pages (Q1–Q6), Method's tabs and the game's levels float at the bottom of the screen as one row of pills, the current one a dark pill (or orange outline for the game). **Phones**: anything fixed to the bottom sits `12px + env(safe-area-inset-bottom)` above the edge, so the iPhone home bar never covers it.

### No layout shift

Cards in a row keep the same number of lines for each part (names two lines, explanations two lines), so everything below starts at the same height across the row and nothing jumps while swiping. Nothing pops in mid-page once choices are made. More in MOTION.md.

---

## 4. Shapes, frames and cards

- **Radii.** Large frames (figures, side panels, the game's finish card) 28px; smaller cards (question cards, Method cards, Neighbours' closest cards) 20px.
- **Pills** (999px) only for buttons, chips, tags, inputs and the nav.
- **No hard shadows.** Clickable cards and pop-up menus get a soft halo, `0 24px 48px rgba(0,0,0,.08)`.
- **Frames only where you click.** Charts, tables and info groups sit straight on the page with a hairline on top. Frames are kept for clickable cards and panels that hold game or map state.

### Card families

| Card | Look | Used for |
|------|------|----------|
| Product-row card | Whisper cream, 28px corners, no border; small mono eyebrow, Newsreader name, a line or two of text, and a round arrow at the bottom right when it opens something | Compare's DApp cards, Home's three layers, More ways in, About's data sources, Method's cards on desktop |
| Framed card | Lifted, 1px `#E6E1D9`, 20px or 28px corners | Neighbours' closest cards, the game's finish card, swipe cards on phones |
| Tinted-top card | A tinted panel at the top (a chart or dates), then the name and facts | Compare's DApp cards and the era cards, on phones |
| Business card | See Summary card in section 9 | The summary card |

---

## 5. Buttons and links

Button states, hover, press and touch-target sizes are in MOTION.md. The rules about what goes where:

- **Two kinds of tap target.** Link blue text means "see more"; ink means "go on". On a walk step the blue links sit together and the ink Next comes last.
- **Every blue "… ›" link sits at the right end of the heading row** of the thing it belongs to, above the content, never under it. Charts: "Read more ›" on the chart's title row. Sections: on the section heading ("What happened ›" on The whole market). Where there is no heading row (Method's Signals and Data tabs), "Notes and limits ›" sits in a row of its own just above the cards, at the right. When a heading wraps on phones, the link stays at the right of its first line. The one exception is "See today at the booth ›" on the card page, under the title in its narrow left column.
- **Long notes fold.** How to read, Success and Source notes under a chart fold into "Read more ›"; it opens the note in a sheet, and links inside still work. On an era table it sits on the table's label line.
- **Slides use a round ⋯ button** in their top-right corner for details. Every other "see more" is a short blue text link, never a bare icon: an icon on its own would not say what it opens.
- **Only the arrow opens.** On More ways in cards and About's Method tile, only the round arrow at the bottom right is a link; the card is not.
- **One way forward.** On every walk step the only forward action is Next at the bottom right (Finish on the last step). Choices inside a page never say "→". Previous / Next are one row in the sans font: a plain grey back link on the left, "Next →" in plain bold ink on the right, no pill or frame. Bold ink against grey is enough to show the way on; orange stays for "you / now".
- **The Ethereum mark as a button**: the card's save mark (fills orange when saved) and Neighbours' Compare (fills ink on hover). Each carries an accessible label ("Compare Sushi BentoBox with others").
- **Focus rings are ink** on every input, dropdown and picker, and follow the pill's shape.

---

## 6. Sheets, menus and pop-ups

- **Sheets.** **Phones**: a bottom sheet rises from the bottom. **Desktop**: a 520px panel slides in from the right. ✕, a tap outside or Esc closes it, and it leaves the way it came (MOTION.md).
- **Every sheet reads the same way**, left-aligned: a heading in Newsreader, a small grey mono line (dates, a count, "1 · Categories"), then the text in the body font, with a hairline between items. Notes like "Rules." become headings, not a bold word inside a paragraph. Legends list one item per line (a dot and its meaning). "What happened in each era" lists each era as its name, the dates on their own line, then what happened.
- **Dropdowns** open under their row; on phones they are full width, so they never run off the screen.
- **Tooltips.** Hovering or tapping a dot or bar shows its tooltip (name, category and launch, the two numbers, whether it lasted). It is always kept fully on screen and sits above the floating bars.
- **Search** (Compare's add card) opens inside the card: one pill input in Whisper cream with no border and no dark ring when focused (only the caret), and a flat list inside the card, not a floating box.

---

## 7. Charts and maps

### Canvas

- **Desktop**: charts on a 980-wide canvas; maps 980 × 540.
- **Phones**: charts on a 560-wide canvas, taller (about 560 × 450, roughly 270px on screen), with 16px label text so labels stay about 10px on screen; maps on a square 560 × 560, about 80% taller. The Method walkthrough figure uses the same 560-wide canvas.

### Line names

- Each line's name sits at the end of its own line, right-aligned, instead of in a label column, so the plot takes the full width.
- If a line runs under that spot, the name moves under its line or above all the lines; failing those, it takes the nearest clear spot within about 90px of the line's end. Only when none is clear does it keep a page-coloured outline so the crossing line passes behind it. The reference line's name ("1,000 wallets") gets the same outline.
- Two names never overlap. When lines end close together, the coloured name (the DApp itself) takes the spot nearest its line before the grey reference names ("One-hit", "Kept growing").

### Room for labels

- Horizontal bar charts size their right margin from the longest value label, so "+14400%" is never cut. Vertical bars leave room above the tallest bar for its number.
- On phones, long axis captions split onto two lines at the "·", crowded month ticks show every other label, and the map's x-axis numbers sit a little lower so the corner numbers ("0%", "1.0") never touch.

### Titles and axes

- Every chart has a short grey title with "Read more ›" on the same row, on one line. A walk picker ("Following Lido ▾") sits on its own line under that row.
- Small charts on phones say what x and y are: the top and bottom of the scale sit at the left edge in small grey mono, the time along the bottom (Compare's Learn more chart reads Peak / 0 and Launch / Year 1 / Year 2; each era card's line reads its highest month ("1.7M") / 0 and its first and last month with "monthly wallets" between them, so the dates line above it is dropped on phones).
- Era breaks are named on the chart itself, in small mono at the top of their dashed lines ("Terra", "Dencun"). The Merge is mentioned only in What happened, "for context only; it is not one of our era breaks".

### Maps (Neighbours and the game)

The map has no title row of its own, so its "Read more ›" (which opens "How to read this chart") sits at the map's top right, on the "Y · …" row. The map no longer says "Drag the crosshair, or click anywhere".

---

## 8. Motion

Effects play once, on a change, and explain the data. Nothing loops except the name river on Pick a DApp, the cards drifting on the booth tank and the save-mark wiggle. All motion is skipped under `prefers-reduced-motion`. Timing, easing, feedback, button states and touch targets are in [MOTION.md](MOTION.md).

---

## 9. Pages

### Home

- **The whole market** (market strip): a carousel of three slides (Wallets, Transactions, Gas), one at a time, each straight on the page with no card or fill. "What happened ›" on the section heading opens the three eras and their dates. There is no toggle and no era bar under the chart. The dots under it are the only control. The peak alone is marked: a solid orange dot with a small orange mono "peak" (on its left when it sits next to an era name or the right edge); each slide keeps its own marker inside it.
  - **Desktop**: slides 64px apart, so one slide's chart never runs into the next slide's number; the number on the left (56px, the measure's name under it in the same serif at 26px, then the month and the change) and the chart on the right (200px tall).
  - **Phones**: the number over the chart ("1.1M active wallets", 48px and 26px), the month and the change on one line under it, then the chart (220px tall).
- **At a glance**: a section heading like The whole market (24px title, a hairline under it), then three tiles side by side (number on top, a short line under it).
- **Read the ecosystem in three layers**: three product-row cards, numbered, so the order needs no arrows.
- **Today at the booth** (after the three layers, before More ways in): two panels, side by side on desktop and swiped on phones. "Saved cards" (a 220px tank) with "See all of today ›", and "Top scores today" with "Play the game ›", each link on its label row; the labels and links sit on one line with 14px above the content. The scores panel is a podium for the day's best three: first in the middle on the tallest block (light orange, cream numeral), second on the left and third on the right on lighter blocks, each with the name and "412 pts · 1:23" above it; an empty step shows a dash and "open".
- **More ways in**: four cards in the top bar's order: The six questions (opens the question list), Compare, Neighbours, Game. **Desktop**: about three and a quarter cards in view so the fourth peeks in, snapping, with dots. **Phones**: swiped, no dots.

### Questions (Q1–Q6)

- The Questions list has no "Pick a timeline": every question page has the era switch right under its title.
- A question page reads: eyebrow (← All, the progress strip, the Describe / Predict tag), the question, the era switch, the Conclusion, then the chart. There is no extra bar under the header and no "All six questions" list (the floating Q1–Q6 bar lists them).
- The floating bar: **Phones**: the current question a dark pill with its name, the others just their number. **Desktop**: every name spelled out ("Q1 Categories … Q6 Take-off"), the current one an ink pill; the page is one wide column.
- The orange keyword in each Conclusion: the category that grew most (Q1), the strongest signal (Q2), the top-10 share (Q3), the successful share with 10K wallets by month 6 (Q4), the share kept at month 6 (Q5), the growers' retention (Q6).
- Q2's era table puts each percentage under its bar. Q5's small-sample warning sits inside its note.

### Walks (market walk and DApp walk)

- One column on every screen: the progress strip as eyebrow, the chart's title with "Read more ›", the walk picker under it, and the footer (grey back link, bold "Next →"). The bar under the header keeps only ← Home.
- The place line (era › category › DApp) is not shown under the eyebrow: it appeared only once choices were made, so it popped in mid-walk. The same choices are in Your path.
- **Walk pickers** (Hot or fading, Leaders): "Following Lido ▾" on its own line under the chart's title row; its list opens under it, inside the screen.
- **Market walk**: the leader you follow on "Who runs it?" is the subject of every step after it.
  - *Who runs it?*: the Conclusion names that leader, its share and its place in the top 5, then the first one and the top 5's share (the first one keeps the short form).
  - *What do the leaders have in common?*: the followed leader is the first, blue row, above the category's top 5 (black) and its typical DApp (grey); the line under the Conclusion gives its value on the model's strongest signal.
  - *Do their users stay?*: when we have the leader's first-users curve (38 of the 98 top-5 places), the Conclusion is about it, set against the typical DApp launched in the leader's own launch era; otherwise the Conclusion is the era's typical DApp and the line under it says why the leader can't be followed (launched before our data starts, or fewer than 100 wallets in its first month).
  - Orange keywords: the era ("You are looking at Terra → Dencun"), the category ("DeFi was the hottest"), the leader ("Lido holds 22%"), the signal ("stickiness"), the share kept ("10%").
- **DApp walk**: orange keywords are the shape ("kept growing"), the rank ("#14 of 122"), the three lookalikes, the signal ("size"), and the last step's verdict ("still a success" or "not a success", orange either way; the card and the charts keep rust for success). The Lookalikes chart has no legend above it on phones: its four marks open first in How to read.

### Summary card

- Set like a business card on every screen: "On-chain DApp research" and the Ethereum mark on top, the DApp's name in Newsreader with its category and era under it (a market walk shows the category it followed, "DeFi", with no line under it, since Moment gives the era), the five steps as label and value, and the block hash at the foot. No summary sentence.
- Each value says what it is a share of ("Lido, 22% of DeFi wallets", "Stickiness, 33% of the model's weight", "4% of first users at month 6"), in Your path too. Outcome: Success in rust, Not a success in ink. The five DApps with no third-month numbers show "No month-3 data" for Lookalikes.
- **Saving.** Only one-DApp (Layer 3) cards can be saved. The Ethereum mark at the top right is the save button: an ink outline with an orange "Tap to save" beside it; once tapped it fills orange with a small pop, the hint goes, and the note under the card reads "Saved. Your card is on today's wall."; tapping again removes it. Market walk cards keep a plain mark, and their note says "Only one-DApp cards go on the wall: dig into Lido to make one."
- Under the card, one row: "See today at the booth ›" in blue, and "Dig into Lido →" in bold ink (market walks only). Every market walk card offers a DApp to dig into: the leader you followed, else another top-5 leader, else the biggest widely used DApp in that category.
- **Desktop**: left / right, the title, the note and the links on the left, the card on the right.

### Compare

- Three DApp cards: eyebrow (category · launch), name, peak and shape, the verdict, the two-year curve, Dig in, and a round › for Learn more. Adding (the dashed "+ Add a DApp" card, whose search opens inside it) and removing (a round ✕, always visible, on cards 2 and 3; the first card has none) happen on the cards. There is no table or chart under them.
- **Learn more** opens a sheet whose top chart overlays the DApps being compared (this one a thick line in its colour, the others thin, all as a share of each one's own peak), then every number in columns, one per DApp (this one first, in bold; columns are always thirds, so with two DApps the second sits where it would with three), under a sticky header of names and colour dashes; each row's label sits above its values, and ▲ marks the leader. The ▲ and "170 widely used DApps" note sits at the bottom of the sheet.
- **Desktop**: product-row cards; the round › on each card.
- **Phones**: a swipe row of tinted-top cards, each with its own curve on a panel in its column colour; the round › (44px) on the right of the "Dig in" row; a floating bar at the bottom says "Walk Uniswap V3, step by step." with "Dig in".

### Pick a DApp

- The name river (the one endless loop on the site) with search and "Surprise me".
- **Pick a moment in the market**: three era cards, set like Compare's phone cards: the dates and the market line on a tinted panel, then the name, a one-line note, the change in market wallets ("first vs last 3 months") and the hottest category. They open on the era already chosen. The chosen card has a 2px orange border; there is no "Choose" / "Selected" text.
- It ends with the two other ways in as short rows, a grey question over a blue link ("Not listed, or not live yet? / Place your own numbers ›", "Want to line a few up? / Compare DApps ›"), stacked on phones and side by side on desktop.

### Neighbours

- **Filters**: unframed, plain small labels and light outlined buttons, so they read as the map's axis settings: "Compare by" (X, ⇄, Y) and "Only show" (category, launch date).
- **Closest cards**: Your DApp first, then "Closest 1 of 3" … Each card: the label, the name with its lifecycle shown only as an 11px colour dot at the right of the name (Your DApp's key names the colours), the date, its curve full width (64px tall), X and Y values, then the result on its own line. Names keep two lines. "Compare" is the outlined Ethereum mark at the top right, on the label row (13 × 21px in a 32px target on desktop; 14 × 22px in a 44px target on phones).
- Hovering a DApp draws orbit arcs to its three closest.
- **Desktop**: a 270px left column of framed cards that scroll up and down inside a box as tall as the filters plus the map, snapping, with the next card peeking in below; vertical dots between the column and the map (the current one grows tall; they keep their place when the page redraws). The filters are one compact row, right-aligned above the map (two rows on narrow screens), and the map fills the rest under them, so the "Y · Returning share" label has its own space.
- **Phones**: the filters as two labelled rows of equal buttons, the map straight after them, then the readout, then the four cards in one swipe row (about 84% wide; three fixed columns would leave about 100px each, too narrow for names and numbers). No dots.

### Game

- Page order: the level's question (with the quit ✕ at its right, on the same line), the task, the level pills, the map. The task is one plain line ("Pick three dark dots, reading active wallets and returning share together.").
- The levels are one row of slim pills ("L1 · 64 · 0:48", the current one outlined orange) floating at the bottom; the current pill carries the live clock. There is no separate time and score box. When a level ends, the task line turns into the result ("2 of 3 lasted · +164 points · 1:07 so far. Keep going!") with Next level right there, and nowhere else.
- The map's caption ("NFT · Before Terra · 16 DApps") is its title, in ink, with "Read more ›", which opens the two measures, each as its axis, name, one plain line and what low and high look like ("← only a few users · lots of users →"). There is no pick list: the numbered dots on the map are tappable for name and result.
- **Start**: the start card spans the map with a pill button: "Your turn … Go with your gut. / Let's go →". The game has no leaderboard of its own.
- **Finish**: the finish card sits over the map as a lifted card (Lifted, hairline, 28px corners, the soft halo, no ink border; 380px wide on desktop). "Finished" and a 32px round ↻ share the top row; then points and time, "3 of 9 picks were a success.", the name box (a Whisper cream pill, ink → button), then your place today: "You are #2 of 5 today, on the podium on Home" (the rank in orange) with "See today's top scores ›". The board keeps the best 50 of all time plus every game from today, so a new score is never dropped.
- **Timeouts**: a game stops itself, unsaved and without a message, after one minute with no tap, click or key during a level, or after ten minutes in all. The booth's `?kiosk` timer (90 seconds back to Home) still applies everywhere.
- **Desktop**: the map is centred, at most 880px wide (about 485px tall), narrower on short screens so the map and its axes fit on one screen; the start page is the start card alone (720px wide). **Phones**: the map gets the first screen (it starts about 375px down on an 812px phone); no score pop or landing dots.

### Today at the booth (`#wall`)

- Called **Today at the booth** (menu and top nav: Booth). Title "Today at the *booth*", subtitle "Cards and scores from this screen today. To add a card, walk a DApp to the end and tap its Ethereum mark."
- Two panels, side by side on desktop: "Saved cards" with "Walk a DApp ›" (opens the DApp picker) and "Top scores today" (the top 10; open places show a grey dash) with "Play the game ›". No card count under the tank; only a quiet grey "Clear today" link for staff, at the right, when today has cards (it empties the tank after a confirm).
- **The tank** (Home 220px, Booth 460px on desktop, full height on phones): a quiet blockchain motif behind it (chains of small blocks joined by dotted links, one ghost Ethereum diamond, no purple). Each saved card drifts slowly as a small card (about 144 × 80) with only the name and its block hash, all the same size (a souvenir, not a chart, so size carries no data), bouncing off the sides from an even starting grid; tapping one opens the full card. Our data has no contract addresses, so the 0x line is the walk's block hash.
- Two example cards from real walks (Uniswap V3, a success; Beanstalk, not) are always there so the tank is never empty, marked "Example walk" when opened and dropped once a visitor makes a card for the same DApp.
- Cards are kept in that browser's storage only (no server), so each booth screen shows its own visitors. A tank shows at most the newest 4 cards on Home on phones and 6 on desktop, 8 / 12 on the booth page; the browser keeps the last 40.

### Method

- One title, "How we measured it", with a lede that follows the tab: Success ("What counts as a success, shown on one DApp, and how it differs from two other labels we use"), Signals ("The 33 early signals…"), Data ("How 1,816 listed DApps became the 512…").
- The Success / Signals / Data tabs float at the bottom like the Q1–Q6 bar, the current one a dark pill with its number ("85 of 512"); the tiles at the top are hidden.
- **Success tab**: "Three labels, only one is success" (Success, then Lifecycle label and Shape), one per card with the key number and one line and a round ⋯ for the full detail. The walkthrough has a section heading, "The rule, step by step", with its ↻ on that line: five steps (the three parts of the rule, then "DragonQuest: not a success" and "The grey DApp: a success"); once it ends, only the ↻ stays in the figure's top-right corner. The "Why not ever reached 10K wallets?" note lives in the Success card's details.
- **Signals tab**: "What we look at", one card per group ("7 signals", the group name, the gist in one line, ⋯ opening its signals with their success-vs-others bars and the legend).
- **Data tab**: the funnel (1,816 → 512, five steps, 512 in orange), each step with a bar for its share of the registry; then three charts (by category, by launch year, peak wallets).
- Every card keeps two lines for its explanation under the number; a label never runs under its ⋯ button. Rules and limits fold into "Notes and limits ›" on every tab.
- The "By launch year" bars leave room above the tallest bar for its number.
- **Desktop**: grids of Whisper cream cards. **Phones**: the same cards as paged rows, left-aligned, with dots.

### About

- The three data sources (DeFiLlama, AWS Public Blockchain Data, Method) as product-row cards: icon, name (26px, room for two lines), one line of text, no small label or date-range chip. They stay on About as the credit for the data, while Method shows how it was narrowed. Only Method's round arrow at the bottom right opens Method. **Phones**: swiped, framed like the other swipe cards.
- **Take it with you** (desktop only; on a phone you are already there): at the top right beside the title, its top level with the title's. A QR code (ink on the card's cream, 132px with a quiet margin) to https://ethereum-dapp-trends.vercel.app, a serif title and one line ("Scan to open this site on your phone and keep reading."); no written address. The code is a fixed SVG in the page, so it works offline.
