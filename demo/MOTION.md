# Motion guide

**Purpose.** How things move on the demo site: when something animates, how long it takes, which curve it uses and when it must not move at all. Nothing else lives here; how things look is in [DESIGN.md](DESIGN.md).

**How to read it.** Each rule is one line, then an example, then how the site applies it. Values are what `site/css/site.css` and `site/js/` use today.

---

## Rules

**M1. Motion explains a change; it never decorates.** It plays once, when something changes.
- Example: switching era morphs the bars to their new values instead of swapping the chart.
- Here: big numbers count up the first time they appear; the retention chart draws itself once per era.

**M2. Fast and quiet.** Everyday UI moves in 120–280ms; slower moves (400–600ms) only for data drawing itself or a deliberate sweep.
- Example: the chart tooltip fades in over 120ms.
- Here: hover colour 150–200ms, dropdowns 180ms, the start button's orange sweep 400ms, orbit arcs 600ms.

**M3. Ease out on the way in, ease in on the way out, and exits are about 20% shorter.**
- Example: a sheet arrives in 280ms with `cubic-bezier(.2,.7,.2,1)` and leaves in 220ms with `cubic-bezier(.4,0,1,1)`.
- Here: the filter pop-up opens in 180ms and closes in 150ms; things that travel and stop (the save-mark wiggle) use `ease-in-out`.

**M4. Enter from the trigger, leave the way you came.**
- Example: a sheet rises from the bottom on phones and slides in from the right on desktop, then goes back the same way.
- Here: the filter pop-up drops 6px into place under its filter; the phone ☰ menu slides in from the right, where its button is; a closing sheet ignores taps and its backdrop fades.

**M5. Groups arrive one after another, only the first time.** Items are staggered 30ms apart.
- Example: More ways in cards each rise 8px and fade in over 320ms when Home opens.
- Here: also the question cards, About's sources and Method's Signals and Data rows; never when a filter or era change redraws a list.

**M6. No bounce on everyday UI.** Overshoot is kept for small celebrations.
- Example: menus, sheets, filters and charts never overshoot.
- Here: `cubic-bezier(.2,1.6,.4,1)` only for a game point and the card's Ethereum mark when saved.

**M7. Feedback is short and confirms the action.**
- Example: every pill button (Start, Dig in, Next, Surprise me) shrinks to 97% while pressed.
- Here: saving a card pops the mark from 60%; until it is saved, the mark wiggles once every 4 seconds.

**M8. Never move under the user's hand; any animation can be interrupted.**
- Example: orbit arcs on Neighbours do not draw while the map is being dragged.
- Here: swipe rows snap only after the finger lets go; the name river pauses on hover.

**M9. Only three things loop.**
- Example: the name river on Pick a DApp (`linear`).
- Here: also the booth cards drifting (paused when off screen or the tab is hidden) and the save-mark wiggle; anything else that repeats is a bug.

**M10. Reduced motion means none.** Under `prefers-reduced-motion: reduce` the end state shows at once.
- Example: the start button turns orange instantly; sheets close at once.
- Here: era changes jump to new values, numbers show their final value, booth cards stay still. Every new effect needs its own reduced-motion rule.
