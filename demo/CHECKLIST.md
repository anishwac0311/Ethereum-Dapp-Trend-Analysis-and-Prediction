# Checklist

**Purpose.** The check to run before calling any UI change done. It holds no rules of its own: each line points to the rule in [DESIGN.md](DESIGN.md) (D) or [MOTION.md](MOTION.md) (M). The second part lists what makes a site look generated from a template, and the three things we do close to it on purpose.

---

## Before you ship

**Look**
- [ ] Only palette colours; one orange cue; rust only for success (D: C1–C3)
- [ ] Small text at least 4.5:1, large 3:1 (D: C5)
- [ ] Only the three fonts; tabular numbers; no widows; mono only for labels and numbers (D: T1–T3, T5)
- [ ] Page head follows the one rule; spacing reuses 24 / 32px (D: L2)
- [ ] Sections keep the 16 / 24 / 64 rhythm (16 / 16 / 64 on phones); space groups before lines (D: L7)
- [ ] Nothing jumps when content loads or changes (D: L4)
- [ ] One main thing per screen, and it is the biggest (D: L8)
- [ ] Nested corners: inner = outer − padding (D: K2)
- [ ] Real charts and real numbers, no placeholders (D: H4)

**Use**
- [ ] Frames only where you click; only the arrow opens (D: K1, K3)
- [ ] "… ›" links at the right of their heading row (D: K4)
- [ ] Answer first, details behind Read more or a sheet (D: K6)
- [ ] Phone tap targets at least 44px (D: K7)
- [ ] Dotted underline only on measure names in charts, tables and panels (D: K9)
- [ ] One icon family, one stroke (D: K10)

**Move**
- [ ] Plays once and explains a change (M: M1)
- [ ] Ease-out in, shorter ease-in out (M: M3)
- [ ] Interruptible; nothing moves while dragging (M: M8)
- [ ] Has a reduced-motion version (M: M10)

**Words**
- [ ] Conclusion leads with the answer, one keyword, at most one extra sentence (D: W1)
- [ ] Eras as words in sentences; numbers in the one format (D: W2, W3)
- [ ] En dash for ranges, no em dashes (D: W4)
- [ ] Links: go on = ink bold →, back = grey ←, see more = blue › (D: W5)
- [ ] Plain, specific words; titles name their subject (D: W6)
- [ ] Changed a sentence? Edit it in [site/js/copy.js](site/js/copy.js), re-export and read the diff of [review/conclusions.md](review/conclusions.md)

Known exceptions:
- C5: orange text is 4.2–4.5:1 (it is the one accent); placeholder dashes and Pick a DApp's drifting names are decoration.
- K1: framed without a click: Method's success-rule panel, About's QR card, Home's podium (a chart); More ways in cards are framed though only their arrow opens.
- K2: the podium's bars (10px, a chart) and the booth's small drifting cards (12px) keep their own radius.
- K7: the market strip's phone dots are 15px wide so they sit close; swiping is the main control.

---

## Template look to avoid

Avoid: purple–blue or text gradients, emoji in headings, default fonts (Inter, Space Grotesk), coloured card borders, glass cards, icon-box trios, a badge over every heading, stock icon sets or UI kits, fade-in on scroll, cursor glows, hover that only fades, em dashes and buzzwords, grain textures.

Watch (close to a sign on purpose):
- Blur only on the floating bars, never on cards.
- Reuse the named spacing values; there is no token scale yet.
- One italic orange word per page title, nowhere else.
