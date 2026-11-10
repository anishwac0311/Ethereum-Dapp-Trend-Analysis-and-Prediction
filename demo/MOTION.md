# Motion and buttons

How things move and how buttons answer on the demo site. Colours, type and layout live in [DESIGN.md](DESIGN.md); this file covers interaction and motion only. Every value below is what `site/index.html` uses today unless it is marked **Not yet**.

A good screen works on three layers: visual design (type, spacing, colour: DESIGN.md), interaction design (buttons, menus, feedback, what is shown when) and motion design (entrances, exits, easing, transitions). The last two are here.

## Principles

1. **Motion explains a change.** Effects play once, when something changes, and show where it came from or where it went. Nothing moves just to decorate.
2. **Fast and quiet.** Everyday UI moves in 120–280ms with no bounce. Slower moves (400–600ms) are kept for data drawing itself or a deliberate sweep.
3. **Never block the user.** Any animation can be interrupted by the next click, scroll or drag, and nothing animates while the user is holding or dragging.
4. **Reduced motion means none.** Under `prefers-reduced-motion: reduce` every effect is skipped and the end state shows at once.

## Timing

| Use | Duration |
|-----|----------|
| Tooltip on a chart (`#tip`) | 120ms, fades in and rises 4px |
| Colour or border change on hover | 150–200ms |
| Filter pop-up (`.fpop`, dropdown) | 180ms in, 150ms out |
| Swipe dots growing (current dot widens or grows tall) | 250ms |
| Bottom sheet (phones) and side sheet (desktop) | 280ms in, 220ms out |
| Game points and the saved-card pop | 350–450ms |
| Ink start buttons' orange sweep | 400ms |
| Orbit arcs on Neighbours drawing themselves | 600ms |

Dropdowns and pop-ups stay between 150 and 250ms. Exits are about 20% shorter than entrances: the filter pop-up opens in 180ms and closes in 150ms; sheets open in 280ms and close in 220ms.

## Easing

| Curve | Where |
|-------|-------|
| `cubic-bezier(.2,.7,.2,1)` (ease-out) | The default. Entrances: sheets, the start-button sweep, orbit arcs, small slides |
| `cubic-bezier(.4,0,1,1)` (ease-in) | Exits: sheets leaving speed up as they go |
| `ease-in-out` | Things that move from one place to another and stop, such as the tour bubble and the save-mark wiggle |
| `cubic-bezier(.2,1.6,.4,1)` (overshoot) | Celebration only: a game point (`+1`), a landed dot in the game's progress, the card's Ethereum mark when it is saved |
| `linear` | Endless loops only (the name river on Pick a DApp) |

No bounce or overshoot on everyday UI: menus, sheets, filters, hovers and charts all use ease-out.

## Entrances and exits

- **Ease out on the way in.** New things arrive fast and settle slowly.
- **Enter from the trigger.** A bottom sheet rises from the bottom edge on phones, and on desktop the side sheet slides in from the right, where the reading continues. A pop-up starts 6px above its resting place and drops into it, next to the filter that opened it.
- **Exit the way you came.** Closing a sheet (✕, a tap outside or Esc) slides it back out: down on phones, right on desktop, in 220ms with an ease-in (`cubic-bezier(.4,0,1,1)`), while the dark backdrop fades. The sheet ignores taps while it leaves. Under reduced motion it closes at once.
- **Start pop-ups slightly small** (**Not yet**): pop-ups grow from 95% to full size, never from 0. Ours rise instead of growing, which does the same job.
- **Overlap old and new.** When the era changes, bars, dots and lines morph to their new values instead of the chart being swapped out.
- **Data draws once.** Big numbers count up the first time they appear, and the retention chart draws itself once per era because the drop is the story. Hovering a DApp on Neighbours draws orbit arcs to its three closest DApps.

## Stagger

When a group appears, its items arrive one after another, about 30ms apart, not all at once (**Not yet**: lists and card rows appear together today). Use it only on a group's first entrance, never when a filter redraws a list the user is reading.

## Feedback

| Feedback | Rule |
|----------|------|
| Hover | Colour only: links go to `#1d3570`, round arrows and "+ Add a DApp" turn orange `#CF4500`, list rows fill `#ECE7E0` |
| Press | A pressed button shrinks a little (`.pk-rand` "Surprise me" goes to 98%; 97% is the upper limit), or turns orange on tap where there is no hover |
| Success | A short pop confirms it: the save mark grows from 60% with a slight overshoot, and a game point pops in |
| Waiting | The save mark wiggles once every 4 seconds until the card is saved; this is the only nagging loop |

**Optimistic update.** Saving a card, clearing today and every filter change apply on the spot: there is no server, and the screen never waits for one.

## Interruptible and hands-off

- The orbit arcs on Neighbours do not draw while the map is being dragged (`.dragging .orb{animation:none}`).
- The name river on Pick a DApp pauses on hover.
- The Wall's drifting cards pause while the tank is off screen or the tab is hidden.
- Swipe rows snap only after the finger lets go; the dots follow the scroll and never pull the row on their own.

## Loops

Only three things loop: the name river on Pick a DApp, the cards drifting on the Wall, and the save-mark wiggle until saving. Anything else that repeats is a bug.

## Reduced motion

Ten `prefers-reduced-motion` blocks turn effects off. Under reduced motion the start buttons switch to orange at once, era changes jump straight to the new values, numbers show their final value, the Wall's cards stay still, and the game's pops show without animating. New effects need their own reduced-motion rule.

## Buttons

### Affordance: what looks clickable is clickable

- **Frames only where you click** (DESIGN.md, Shapes): a framed card can be clicked or holds state; a chart on the page cannot.
- **Only the arrow opens.** On More ways in cards and About's Method tile, only the round arrow is a link. The card around it has no hover halo, so nothing suggests the whole card opens.
- **One way forward** on walk steps: only Next at the bottom right moves forward (DESIGN.md, Rules).
- Blue `… ›` text links always sit at the right end of their heading row (DESIGN.md).

### Button families

| Button | Rest | Hover or tap |
|--------|------|--------------|
| Round arrow (More ways in, Method tile, Compare's ›) | Ink chevron in a faint circle (1px, 12% ink, no fill); 42px desktop, 44px phones | Orange `#CF4500` fill, chevron in cream |
| Ink start button ("Start the game →", "I'm new · start here →", "Developers · start here →") | Ink pill, cream text | Orange sweeps in from the left over 0.4s; text stays cream |
| Plain pill ("Dig in") | Ink pill | No hover effect |
| Dashed add card ("+ Add a DApp", desktop) | Dashed hairline | Plus, words and dashed edge turn orange |
| Round icon button (☰, ✕, ⇄, ↻, ⋯) | Thin `#DDD8CF` outline, no fill | Soft fill |
| Ethereum mark (save or Compare) | Outlined mark in a 32px (desktop) or 36px (phone) round target | Fills ink |

### Touch targets

- On phones every control is at least 44 × 44px, even when its icon is smaller: the round arrows are 44px, and both Ethereum marks (the card's save mark, 16 × 26px, and Neighbours' Compare, 14 × 22px) sit in a 44px target, so the icon stays the same size and in the same place.
- Phones have no hover, so anything that needs to be seen (the ✕ on Compare cards 2 and 3) is always visible.
- A tap must not leave a hover outline stuck on a card (DESIGN.md, Phones).

## Showing less until asked (progressive disclosure)

The page shows the answer first and the method on request: "Read more" folds on desktop, "Learn more" sheets on Compare, "How to read this chart ›" under the map, ⋯ details on Method cards, and Notes and limits at the end of a question. A new detail goes behind one of these, not onto the page.

## No layout shift

Nothing on screen jumps when something loads or changes:
- Method cards keep two lines for each explanation so the rows line up whatever the text length.
- Chart labels have room reserved above the tallest bar and to the right of the longest value.
- Numbers that change in place use tabular figures (see DESIGN.md, Type), so a counter does not wiggle as digits change.
- The progress strip and the swipe dots keep a fixed size when they change state.

## Continuous transitions (**Not yet**)

A shared element transition keeps one element on screen while the page changes around it, for example a Compare card growing into its Learn more sheet. The site uses single-file vanilla JS, so this would be the View Transitions API (`view-transition-name` on the card and the sheet). React's Framer Motion `layoutId` does the same job and does not apply here. This is a candidate, not a rule.

## Terms

The 40 terms behind these rules, with where each one applies here.

### Design terms

| Term | Meaning | Here |
|------|---------|------|
| Kerning | Space between two particular letters | Left to the fonts |
| Optical centre | Where a thing looks centred, which is not always its geometric centre | Check by eye on round buttons and the play triangle |
| Tabular numbers | Digits all the same width, so numbers line up | DESIGN.md, Type |
| Layout shift | Things on screen jumping when content loads or changes | No layout shift, above |
| Tracking | Letter spacing across a whole run of text | Mono labels +0.14em (DESIGN.md) |
| Optimistic update | Updating the screen at once without waiting for a server | Feedback, above |
| X-height | Height of lowercase letters; sets how big text feels | Compare fonts at the same size by x-height, not by px |
| Touch target | The tappable area around a control | Touch targets, above |
| Leading | Space between lines (line height) | DESIGN.md, Type |
| Origin-aware animation | Motion that starts from where its trigger is | Enter from the trigger, above |
| OKLCH | Colour model with separate lightness, chroma and hue | Not used; colours are fixed hex tokens |
| Widow | A lone word left on a paragraph's last line | DESIGN.md, Type |
| Safe area | Screen space clear of the notch, status bar and home bar | DESIGN.md, Phones |
| Stagger | Items in a group animating one after another | Stagger, above |
| Line length | How many characters fit on a line | DESIGN.md, Type |
| Affordance | A thing showing how it can be used | Affordance, above |
| Combobox | A text box with a list of matches to pick from | The DApp search on Pick a DApp and "+ Add a DApp" |
| Interruptible animation | Motion that gives way at once to the next input | Interruptible and hands-off, above |
| Progressive disclosure | Showing more only when it is asked for | Showing less until asked, above |
| Shared element transition | One element carried across a change of screen | Continuous transitions, above |

### Animation techniques

| Technique | Here |
|-----------|------|
| Ease-out for entrances | Default curve |
| Dropdowns at 150–250ms | Filter pop-up, 180ms |
| Stagger list rows by 30ms | Not yet |
| Scale to 0.97 on press | "Surprise me" at 98% |
| Stretch moving knobs 12% | Not used; the site has no sliders |
| Stagger as details settle | Not yet |
| Arcs for object movement | Orbit arcs on Neighbours |
| Pulse to confirm success | Save mark pop, game points |
| Ease-in-out for moves | Tour bubble, save-mark wiggle |
| Start popovers at 0.95 | Not yet; pop-ups rise 6px instead |
| Enter from the trigger | Sheets and pop-ups |
| Exit to the trigger | Sheets slide back out the way they came |
| No bounce on everyday UI | Overshoot is kept for celebrations |
| Don't tween while held | Orbit arcs off while dragging |
| Make exits 20% shorter | Sheets 220ms (vs 280ms in), filter pop-up 150ms (vs 180ms) |
| Overlap old and new states | Era change morphs charts |
| Masks for reveals and colour | The start buttons' orange sweep (a growing background) |
| Crossfade icons with blur | Not used |
| Rubber band past bounds | Native scroll on phones only |
| Reuse the same `layoutId` | Not used (React only); see Continuous transitions |
