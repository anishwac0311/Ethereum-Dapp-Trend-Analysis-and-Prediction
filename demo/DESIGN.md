# Design guide

The rules the demo site actually follows. The look borrows Mastercard's warm cream canvas and colour roles, set in our own type so the pages read like a research paper. Everything here is the default `study` theme in `site/index.html`; the other themes in that file (`?theme=cream`, `ink`, …) are early experiments and are not used.

## Colours

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
| Whisper cream | `#EFEAE3` | The success-rule panel on Method |

**Supporting neutrals.** A few warm greys sit between the hairlines and the text colours above. They are part of the palette on every screen; nothing else may be added.

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

Two tints are left on phones only: the game start picture (`#F4E6DC`) and the per-DApp chart panel in Compare's Learn more sheet (`#ECE9E3`, `#E6ECF8`, `#EEEDEB`). Desktop shows both in Whisper cream.

**Lifecycle colours** are always shown with their name beside them: Sustained `#3860BE`, Gradual decline `#141413`, Flash `#F37338`, Never adopted `#D1CDC7`, Unclear `#696969`.

## Type

| Role | Font | Size |
|------|------|------|
| Titles | Newsreader (serif), weight 400 | 52px on inner pages, 68px on Home and Questions |
| Subtitle under every title | Plus Jakarta Sans | 17px, Ink 2, max 720px wide, 18px below the title |
| Body | Plus Jakarta Sans | |
| Labels, eyebrows, numbers in tables | JetBrains Mono | 11.5px, tracked +0.14em |

## Shapes

- **Frames**: large frames (figures, Compare table, side panels) have a 28px radius; smaller cards (question cards, Method cards) have 20px. Both are Lifted with a 1px hairline.
- **Pills** (999px) only for buttons, chips, tags, inputs and the nav.
- **Round icon buttons** (☰ menu, ✕ close, ⇄ swap, ↻ replay, ⋯ details, and the game's quit ✕ at the right of the level row, its cross in orange) are a thin #DDD8CF outline on the page colour, with no fill.
- **No hard shadows.** Clickable cards and pop-up menus get a soft halo, `0 24px 48px rgba(0,0,0,.08)`.
- **Frames only where you click.** Charts, tables and info groups sit straight on the page with a hairline on top. Frames are kept for clickable cards and panels that hold game or map state.

## Desktop (wider than 600px)

- Card rows read like a product row: big cards in Whisper cream #EFEAE3 (no colours outside the table above), 28px corners, no border, a small mono eyebrow, a Newsreader name, a line or two of text, and a round › (42px, thin ink outline on a pale fill) in the bottom-right corner when the card opens something. Used for Compare's three DApp cards, Home's three layers and More ways in.
- Compare shows its three DApp cards: eyebrow (category · launch), name, peak and shape, the verdict, the two-year curve at the bottom, Dig in, and › for Learn more. Adding (the dashed card) and removing (✕ on cards 2 and 3) happen on the cards. There is no table or chart under them: every number sits in the › side panel, in one column per DApp.
- Every sheet (Compare's Learn more, Read more) slides in from the right as a 520px panel instead of up from the bottom.
- Page heads use the width: the title on the left and its line on the right, bottom-aligned (Compare, Pick a DApp, Neighbours, Method, Today at the booth, as Questions already did). The game's start page puts the title and line on the left and the start card on the right.
- Method's Success / Signals / Data tabs float at the bottom like the Q1–Q6 bar; the three tiles at the top are hidden.
- Today at the booth puts Saved cards (a 460px tank) and Top scores today side by side. The board always draws its ten places; open ones show a grey dash (on phones too).
- The title's last line and the line beside it end on the same line on every page head.
- Compare's add card opens its search below its ✕: one pill input in Whisper cream with no border and no dark ring when it is focused (only the caret), and a flat list inside the card, not a floating box.
- Compare has no wallets chart under the cards; the › side panel carries every number and the overlaid curves.
- The game map is centred and at most 880px wide (about 485px tall), and narrower on short screens, so the whole map and its axes fit on one screen. On Neighbours the map fills the column beside the cards instead.
- Charts work as on phones: each line's name sits on its line (the label column on the right is gone, so the plot is wider), with the same rules for moving a name clear of other lines and names.
- Home's market strip works as on phones: a carousel of three wide slides (Wallets, Transactions, Gas), one at a time, each with its big latest number (88px) and line, its chart (220px tall) and the HTML era bar; the dots under it are the only control (click a dot to jump to that measure; it follows when you scroll), no arrows; the big number is 88px; no toggle; "What happened ›" at the right under the dots. The "Market › Category › DApp" caption is hidden and the heading keeps its hairline.
- Home's More ways in slides on desktop like the market strip: a fourth card, "The six questions" (opens the question list, which Home did not link to before), comes first, so the cards follow the top bar: The six questions, Compare, Neighbours, Game; about three and a quarter cards are in view so the fourth peeks in, the row snaps to a card, and dots under it (click to jump; they follow when you scroll) are the control. Phones keep their three swiped cards.
- Every blue "… ›" link sits at the right end of its row on desktop (Read more, What happened, Notes and limits, How to read this chart, See all of today, Play the game, See today's top scores), like "See all ›" beside a heading. The one exception is "See today at the booth ›" on the card page, which stays under the title in its narrow left column. Phones keep their own placement.
- Desktop uses no tints outside the table: the game start card's picture panel and the chart panel in Compare's Learn more sheet are Whisper cream #EFEAE3 (they were a warm orange tint and a per-DApp blue or grey tint).
- Neighbours on desktop: under the title, a narrow left column (270px) holds Your DApp and the three closest as framed cards (Lifted, 1px #E6E1D9, 20px corners) that scroll up and down inside a box as tall as the filters plus the map, snapping to a card, with the next card peeking in below. Vertical dots sit between the column and the map (the current one grows tall; click to jump; they follow the scroll and keep their place when the page redraws). Each closest card: "Closest 1 of 3", the name with its lifecycle shown only as a colour dot (11px) at the right of the name (Your DApp's key above already names the colours), the date, its curve full width (64px tall), X and Y values, then the result on its own line. "Compare" is the outlined Ethereum mark (the card page's save mark, 13 × 21px in a 32px round target) at the top right, on the "Closest 1 of 3" row; it fills ink on hover and carries the label "Compare Sushi BentoBox with others". Phone cards work the same way: the lifecycle dot at the right of the name and the Ethereum mark (14 × 22px in a 36px target) at the top right. To the right, the filters ("Compare by": X, ⇄, Y; "Only show": category, launch date) are one compact unframed row, right-aligned (two rows on narrow screens), and the map fills the rest under them, so the "Y · Returning share" label has its own space. "How to read this chart ›" sits under the map. Phones keep map, filters, then the readout as a sideways swipe row, with no dots.
- On phones every closest card keeps two lines for its name, so the date, lifecycle, curve and numbers sit at the same height in all three cards while swiping, and "Compare" is the outlined Ethereum mark at the top right, as on desktop; the lifecycle shows only as its colour dot beside the name.
- The game works as on phones: no pick list beside the map (the map is up to 880px wide), the level's two measures fold into the map's "Read more ›", and when a level ends the done line ("2 of 3 lasted · +164 points…") carries Next level. The current level tab shows its clock beside its score.
- Method works as on phones, laid out as grids instead of swipe rows: the three labels, the six signal groups, the five funnel steps (512 in orange) and the three data charts are Whisper cream cards with ⋯ for details; the long versions are hidden; rules and limits fold into "Notes and limits ›".
- The card page is left / right: the title, the note and the two links on the left, the card on the right.
- About's three data sources are Whisper cream cards (no small label, no date-range chip); Method's card has the round ›.
- Walk pages work as on phones: one column, a larger progress strip as eyebrow (28px bars, a 15 × 24 Ethereum mark) (▾ opens Your path), the chart's title with "Read more ›", "Following Lido ▾" under it, and the footer as a grey back link and a bold "Next →". The bar under the header keeps only ← Home (the breadcrumb and step boxes are hidden).
- Question pages (Q1–Q6) are one wide column: the six questions sit in a floating bar at the bottom like on phones, but with every name spelled out ("Q1 Categories … Q6 Take-off", the current one an ink pill); the right-hand "All six questions" column is gone. The eyebrow is the progress strip (▾ opens the list), and each chart has its small grey title with "Read more ›" on the right, which opens the note in the side panel. The era switch stays in the row under the header.

## Phones (600px and narrower)

- Charts are drawn on a 560-wide canvas instead of 980, and taller (about 560 × 450, so roughly 270px on screen), with 16px label text, and the plot takes the full width: each line's name sits just above the end of its line, right-aligned, instead of in a column to the right. If a line runs under that spot the name moves under its line or above all the lines; failing those it takes the nearest clear spot within reach of the line's end; only when none is clear does it keep a page-coloured outline so the crossing line passes behind it. Two names never overlap. The reference line's name ("1,000 wallets") gets the same outline. Labels stay about 10px on screen. Long axis captions split onto two lines at the "·", and crowded month ticks show every other label.
- Compare is a swipe row of DApp cards: each shows its own two-year curve on a tinted panel in its column colour, the key facts, "Dig in" and "Learn more". Learn more opens a bottom sheet whose top chart overlays the DApps being compared (this one a thick line in its colour, the others thin lines in theirs, all as a share of each one's own peak; the cards in the row keep one line each), then every number for that DApp in columns, one per DApp (this one first, in bold; the columns are always thirds, so with two DApps the second sits where it would with three), under a header of their names and colour dashes that stays at the top while you scroll; each row's label sits above its values, and ▲ marks the leader. A floating bar at the bottom says "Walk Uniswap V3, step by step." with "Dig in". The side-by-side table and the bottom chart are desktop only. The ▲ and "170 widely used DApps" note sits at the bottom of the Learn more sheet instead of on the page. "+ Add a DApp" opens its search inside the card. Cards 2 and 3 carry a small round ✕ in their top-right corner (always visible, since phones have no hover) that removes that DApp, freeing the slot for another; the first card has none.
- Side-by-side panels (Neighbours' readout and its three closest DApps) stack.
- Small grey labels only name things nothing else names. Swipe slides carry no "1 of 3" counter (the dots already show it), and Home's "Market › Category › DApp" line is hidden on phones because the layer cards say the same.
- Pages scroll top to bottom; a section of three parallel cards scrolls left to right instead: Home's three layers (numbered, so the order needs no arrows) and More ways in, and Neighbours' three closest. About's three data sources (DeFiLlama, AWS Public Blockchain Data, Method) swipe the same way, framed like the other swipe cards; they stay on About as the credit for the data, while Method shows how it was narrowed. They read like More ways in on Home: icon, name (26px, room for two lines) and one line of text, no small label, all at the same height in the three cards, and the date-range chip above them is dropped on phones (the hero already says it). The same goes for the three era cards in "Pick a moment in the market", which open on the era already chosen. Each card is about 84% wide so the next one peeks in, and swiping snaps to a card.
- Question pages get a floating bar at the bottom to jump between Q1–Q6: the current question is a dark pill with its name spelled out, the others show just their number.
- The pages are in the order a visitor uses them: Home, Questions, Compare, Neighbours, Game, Booth (Today at the booth, `#wall`), then the reading pages Method and About.
- The page links move into a ☰ menu that slides in from the left; tapping a page, the backdrop, ✕ or Esc closes it.
- Question pages read top to bottom: "← All · Q3 of 6", the question, the era switch, then the conclusion and chart. The back link sits in the eyebrow row (walks use "← Home"), so there is no extra bar under the header.
- Every page's first line, eyebrow or title, starts 24px under the header, and the first thing after the title's subtitle (a section heading, the filters, the cards) starts 32px under it on every page, and the eyebrow row stays on one line (walks write "2 of 5" without "Step"). In that row the back button (a thin outline, no fill) sits left and the Describe / Predict tag at the right edge. On question pages the "Q2 of 6 Survival" label is replaced by the progress strip described below.
- Home's At a glance is a section heading like The whole market (24px title, a hairline under it), then three tiles side by side (number on top, short line under it) instead of three stacked rows.
- The summary card is set like a business card on every screen: "On-chain DApp research" and the Ethereum mark on top, the DApp's name in Newsreader with its category and era under it, or for a market walk the category it followed ("DeFi") with no line under it, since Moment already gives the era, the five steps as label and value (an Outcome of Success in rust, Not a success in ink), and the block hash at the foot. It drops the summary sentence, since the steps already say it. Each value says what it is a share of ("Lido, 22% of DeFi wallets", "Stickiness, 33% of the model's weight", "4% of first users at month 6"), in Your path too. Under the card, one row like a walk's footer: "See today's wall ›" in blue on the left, "Dig into Lido →" in bold ink on the right (market walks only). The page title follows the card's name ("DeFi, dug down").
- The Wall page is called **Today at the booth** (☰ menu and top nav: Booth; address `#wall`), matching Home's section: the title "Today at the *booth*", the line "Every DApp card saved and every game played on this screen today.", then "Saved cards" (how to save, the full tank, the count and Clear today) and "Top scores today" (the top 10). Links to it read "See all of today ›" (Home) and "See today at the booth ›" (under a card).
- Only one-DApp (Layer 3) cards go on the wall, and only when the visitor saves them. The Ethereum mark in the card's top-right corner is the save button: an ink outline with an orange "Tap to save" beside it that gives a small wiggle every four seconds until it is saved (no note under the card yet); once tapped it fills orange (you / now) with a small pop, the hint goes, and the note under the card reads "Saved. Your card is on today's wall."; tapping again removes it. The card's top label is "DApp research". Every market walk card offers a DApp to dig into: the leader you followed, else another top-5 leader, else the biggest widely used DApp in that category. The five DApps with no third-month numbers show "No month-3 data" for Lookalikes instead of a dash. Market walk cards keep a plain Ethereum mark; their note says "Only one-DApp cards go on the wall: dig into Lido to make one." The Wall's subtitle reads "Walk one DApp (Layer 3) to the end, then tap the Ethereum mark on your card to pin it here",. The count reads "4 cards saved today".
- Home's "Today at the booth" (after the three layers, before More ways in) holds two panels, side by side on desktop and swiped on phones, each ending in a blue link: "Saved cards" (the tank, then "See the wall ›") and "Top scores today" (a podium for the day's best three, then "Play the game ›"). The podium puts first in the middle on the tallest block (light orange, as for first place on the game's board, with a cream numeral), second on the left and third on the right on lighter blocks, each with the name and "412 pts · 1:23" above it; an empty step shows a dash and "open". The Wall page adds today's top 10 under its tank. The game page no longer shows a leaderboard: its start page is the start card alone (720px wide on desktop), and after saving a name the end screen says "You are #2 of 5 today, on the podium on Home" (the rank in orange) with "See today's top scores ›" to the Wall; the board now keeps the best 50 of all time plus every game from today, so a new score is never dropped.
- Today's cards: Home has a 220px tank ("Today's cards", with "See the wall ›"), and the Wall page (☰ menu, `#wall`) shows the same tank full height. The tank's background is a quiet blockchain motif: chains of small blocks joined by dotted links, with one ghost Ethereum diamond in the middle (no purple). Every card finished on that screen today drifts slowly as a small card (about 144 × 80) with only the name and its block hash,  all the same size (the card is a souvenir, not a chart, so its size carries no data), bouncing off the sides; tapping one opens the full card. Two example cards from real walks (Uniswap V3, a success; Beanstalk, not) are always in the tank so it is never empty, marked "Example walk" when opened, and dropped once a visitor makes a card for the same DApp. Our data has no contract addresses, so the 0x line is the walk's block hash. Cards are kept in that browser's storage only (no server), so at the booth each screen shows its own visitors. A tank shows at most the newest 4 cards on Home on phones and 6 on desktop, and 8 / 12 on the booth page; the browser keeps the last 40 cards. The drift pauses while the tank is off screen or the tab is hidden. Under the tank one line, on one baseline: the count on the left ("4 cards saved today", "No cards saved yet today", or "36 cards made today · newest 12 here" once the cap is reached; the two examples are not counted) and an underlined grey "Clear today" on the right, which empties it after a confirm. Cards start on an even grid (as many columns as fit) and drift from there. Under reduced motion the cards stay still.
- The era cards in "Pick a moment in the market" are set like the Compare cards on phones: the dates and the market line on a tinted panel at the top, then the name, the one-line note, the change in market wallets ("first vs last 3 months", so the caption under the row is dropped), and the hottest category; the chosen card has an orange border instead of "✓ Selected".
- Method's three tabs move into a floating bar at the bottom, like the Q1–Q6 bar: Success / Signals / Data, the current one a dark pill with its number ("85 of 512"). The tiles at the top are hidden on phones, so the content starts right under the title.
- Method's "What we look at" is a paged row like "Three ways we sort apps": one group per slide ("7 signals", the group name, the gist in one line, a ⋯ button top right). The ⋯ opens that group's signals with their success-vs-others bars and the legend.
- The "Why not ever reached 10K wallets?" note moves into the Success slide's Learn more on phones.
- Method's data tab: the funnel (1,816 → 512) is a paged row, one step per slide ("Step 1") with a bar for its share of the registry, and the three charts (by category, by launch year, peak wallets) are another. The rules and limits notes on every tab fold into "Notes and limits ›".
- Method's "Three labels, only one is success" (formerly "Three ways we sort apps") is a paged row, Success first, then Lifecycle label and Shape,, one sort per slide with dots under it: the key number and one line, with a round ⋯ button in the slide's top-right corner that opens the full detail in a bottom sheet (✕, tap outside or Esc closes it). The slides are left-aligned like the market slides on Home.
- On walk steps with a choice (Hot or fading, Leaders), the "Follow another …" box moves into the chart on phones: "Following Lido ▾" on its own line under the title row. Its list opens under it, inside the screen. Its keyboard focus ring is ink, like every other focus ring.
- Walks no longer show the place line (era › category › DApp) under the eyebrow on phones: it appeared only once choices were made, so it popped in mid-walk. The same choices are listed in Your path, opened from the progress strip.
- On walks, Previous / Next shrink to one row in the same sans font: a plain grey back link on the left and "Next →" as plain bold ink text on the right, no pill or frame. Bold ink against grey is enough to show the way on; orange stays for "you / now".
- The Neighbours and game map is drawn on a square 560 × 560 canvas on phones (980 × 540 on desktop), so it is about 80% taller and its labels readable.
- Neighbours: the filters sit unframed, with plain small labels and light outlined buttons, so they read as the map's axis settings. Their dropdowns open under the row, full width, so they never run off the screen. They are two labelled rows of equal buttons ("Compare by" X ⇄ Y, "Only show" category and launch date). The map comes straight after them, then the readout, then Your DApp and the three closest together in one row of framed cards you swipe through (Your DApp first, each closest card labelled "Closest 1 of 3"; all four share the same padding, label rule and title position), each about 84% wide so the next one peeks in from the right. Three fixed columns would leave about 100px each, too narrow for names and numbers.
- The era table under Q2 puts each percentage under its bar.
- A game stops itself, unsaved and without a message, and returns to the game's start: after one minute with no tap, click or key during a level, or once it has run for ten minutes in all. The booth's ?kiosk timer (90 seconds back to Home) still applies everywhere.
- Game page order, on every screen: the level's question, then "Your task", then the three level tiles, then the map. The map's caption ("NFT · Before Terra · 16 DApps") is its title, in ink, on one row with "Read more ›", which opens the two measures; there is no "How to read this chart" row under the map. When the last level ends, the finish card (points and time, "3 of 9 picks were a success.", the name box, then your place today, with a round ↻ in its top-right corner to play again) sits over the map like the "Your turn" card at the start, instead of in a side panel. The name box's focus ring is ink and follows the pill.
- The game's finish card sits on the map like a lifted card, on every screen: Lifted with a hairline (#E6E1D9), 28px corners and the soft halo, no ink border; 380px wide on desktop. "Finished" and the replay ↻ (a 32px round button) share the top row, so nothing crowds the score; the name field is a Whisper cream pill with no dark focus ring, and its → button is ink.
- Game: the map gets the first screen (it starts about 375px down on a 812px phone). The task is one plain line with no label or rules ("Pick three dark dots, reading active wallets and returning share together."), and the three levels are one row of slim pills ("L1 · 64 · 0:48", the current one outlined orange) that floats at the bottom of the screen like the Q1–Q6 bar. The quit ✕ sits at the right of the level's title, on the same line, on every screen; the game has no eyebrow row. Earlier: the three levels shrink to small tiles (level and score), the task stays but tighter, there is no pick list under the map on phones (the numbered dots on the map, tappable for name and result, and the done line above it say the same), and "How to read this chart" holds just the two measures, each as its axis, name, one plain line and what low and high look like ("← only a few users · lots of users →"), with no frames, "why it matters" or example. When a level is done, Next level appears only in the task bar, not again under the map. There is no separate time and score box while playing, on any screen: the current level tile carries the live clock and each tile its points; when a level ends, the task box turns into the result ("2 of 3 lasted · +164 points · 1:07 so far. Keep going!") with Next level right there. No score pop or landing dots on phones. The start card spans the map with a pill button and a friendlier line: "Your turn … Go with your gut. / Let's go →" (this copy is the same on desktop).
- Touch screens drop the dark hover outline that used to stick on a card after a tap.
- The Questions page drops "Pick a timeline" on every screen: every question page has the era switch right under its title, so the picker only repeated it.
- Every chart on a phone has a short title in small grey caps, like "The same model in each era" on Q2: its accessible name ("Wallet change by category", "Share of the category's wallets"). Title and a blue "Read more ›" share the top row and stay on one line (names are kept to about 33 characters, longer ones end in "…"); a walk picker sits on its own line under that row.
- Long notes under charts (How to read, Success, Source) fold into a short blue "Read more ›" at the right of the chart's top row, so it never sits on the chart; tapping it opens the full note in a bottom sheet, links inside still work. On the era table it sits at the right of the table's label line. The Neighbours and game maps, and any chart with a small-sample warning, keep a plain blue "How to read this chart ›" row instead, so the map stays clear and the warning stays visible. On a walk, the eyebrow's middle is a small progress strip instead of "1 of 5 Moment": done steps as short ink bars, the current step as a small solid orange Ethereum mark, the rest grey, then ▾. It is a button that opens "Your path", so the path needs no row of its own. Question pages use the same strip for the six questions (the ones you have opened in ink, this one orange), and it opens "All six questions". Question pages drop the "All six questions" list: the Q1–Q6 bar already lists them.
- Home's market strip has no Wallets / Transactions / Gas toggle on phones (it read like a filter): each measure is its own slide, swiped with dots under them. Each slide has no small label (the dots show the position and the line under the number names the measure) and leads with one big number: the latest month of the measure that is on, against its peak ("1.1M active wallets in Dec 2025, −52% from the 2.3M peak"). It is grey, not orange: "today" and the latest-month dot already carry Home's orange. The line is taller (150px), the era bar sits under it, and a blue "What happened ›" at the right end of the dots row opens the era story.
- Every Conclusion has one orange keyword, on every screen. Question pages: the category that grew most (Q1), the strongest signal (Q2), the top-10 share (Q3), the successful share with 10K wallets by month 6 (Q4), the share kept at month 6 (Q5), the growers' retention (Q6).
- On a market walk, each step's Conclusion has one orange keyword: the era ("You are looking at Terra → Dencun"), the category ("Between Terra and Dencun, DeFi was the hottest"), the leader ("Lido holds 22%"), the signal ("stickiness") and the share kept ("10%").
- On a DApp walk, each step's Conclusion has one orange keyword instead of the DApp's name: the shape ("kept growing"), the rank ("#14 of 122"), the three lookalikes, the signal ("size"). The last step's verdict is its keyword too, orange either way ("still a success" or "not a success"); the card and the charts keep rust for success.
- Two kinds of tap target, never mixed up: Link blue text means "see more" (How to read this chart ›, Your path ›), the ink pill means "go on" (Next, Dig in, Let's go). On a walk step the blue links sit together and the ink Next comes last.
- The Lookalikes chart on a DApp walk has no legend above it on phones: its four marks (this DApp, lookalike success, lookalike not a success, every other DApp) open first in How to read, so the chart starts right under its top row.
- Pick a DApp ends with the two other ways in as short rows, a grey question over a blue link ("Not listed, or not live yet? / Place your own numbers ›", "Want to line a few up? / Compare DApps ›"), stacked on phones and side by side on desktop, instead of one long sentence.
- The walk's place line (era › category › DApp) stays left-aligned with the title under it; only the eyebrow's progress strip is centred, between ← Home and the Describe tag.
- Small charts on phones say what x and y are: the top and bottom of the scale sit at the left edge in small grey mono, the time along the bottom. Compare's Learn more chart reads Peak / 0 and Launch / Year 1 / Year 2; each era card's market line reads its highest month ("1.7M") / 0 and its first and last month with "monthly wallets" between them, so the dates line above it is dropped on phones.
- Tapping a dot or bar shows its tooltip (name, category and launch, the two numbers, whether it lasted); it is always kept fully on screen and sits above the floating bars.
- Legends in a sheet list one item per line (a dot and its meaning); the map no longer says "Drag the crosshair, or click anywhere".
- Slides use a ⋯ button for their details, and every other "see more" is a short blue text link, never a bare icon: an icon on its own would not say what it opens.
- Every Learn more sheet reads the same way, left-aligned: a heading in Newsreader, a small grey mono line (dates, a count, "1 · Categories"), then the text in the body font, with a hairline between items. "What happened in each era" lists each era as name, dates on their own line, then what happened; notes like "Rules." become headings rather than a bold word inside the paragraph.
- Method keeps one title, "How we measured it", but its lede follows the tab: Success ("What counts as a success, shown on one DApp, and how it differs from two other labels we use"), Signals ("The 33 early signals…"), Data ("How 1,816 listed DApps became the 512…").
- The walkthrough has a real section heading, "The rule, step by step", the same size as the other section heads, with its ↻ button on that line.
- The DragonQuest walkthrough has five steps: the three parts of the rule, then "DragonQuest: not a success" and "The grey DApp: a success". Once it ends only a round ↻ button stays in the figure's top-right corner to replay it; there is no separate verdict list.
- The DragonQuest "How to read it" figure on Method is drawn on the same 560-wide canvas with larger text.
- Crossing 600px while the page is open redraws it in the right mode.

## Rules

### One orange word per page title

Each title sets one word in italic orange (`<em class="o-word">`):

| Page | Word |
|------|------|
| Home | *today* |
| Questions | *answers* |
| Compare | *side by side* |
| Method | *measured* |
| About | *project* |
| Today at the booth | *booth* |

On Home it pairs with the orange latest-month dot in the market strip; both mean "now". Neighbours and Game already use orange for the visitor's own DApp and the level numbers, so their titles stay ink.

The game level you are playing has an orange outline (an orange top line on desktop). The "Predict" tag (only Q2) is orange, outline and text, so the one question type that looks ahead stands out from Describe, which stays grey.

Beyond the title word, a page may carry **one** key number in orange, the number the page builds to. Method's funnel ends on 512 (the DApps the study uses) in orange. The summary card's title ends on an orange *dug down*, so every page has exactly one orange cue in its title or eyebrow.

### Rust means success

Rust is reserved for success, so nothing else uses it. Highlighted bars, its "Level done" label and every focus ring (search boxes, dropdowns) are not rust; they use ink and Link blue.

### Eyebrow mark

A small solid orange Ethereum mark (7 × 11px, the same shape as the current step in the progress strip) marks the small label above a title only when the label adds something the title does not say: the question number and tag (Q2 Survival), the step in a walk (Step 3 of 5), the game level is left to its level tiles, so the game's eyebrow keeps only the quit ✕. Pages whose title already says where you are have no eyebrow.

### One way forward

On every walk step the only forward action is the Next button at the bottom right (Finish on the last step). Choices inside a page never say "→". The era cards in "Pick a moment in the market" carry no "Choose" / "Selected" text: the chosen card has a 2px orange border (you / now), the others a hairline.

### Motion

Effects play once, on a change, and explain the data. Switching era morphs bars, dots and lines to their new values. Big numbers count up the first time they appear. Hovering a DApp on Neighbours draws orbit arcs to its three closest DApps. The retention chart draws itself once per era because the drop is the story. Nothing loops except the name river on Pick a DApp and the cards drifting on the Wall. The card's save mark wiggles briefly every four seconds until it is saved. All motion is skipped under `prefers-reduced-motion`.

### Ethereum, kept quiet

A line-drawn Ethereum diamond sits before the site title and in the browser tab, and Home has one large ghost diamond at 9% opacity behind the hero. No ETH purples or gradients.
