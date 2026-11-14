/* The site's sentences, in one place: every Conclusion (question pages and both walks), and each walk step's
   name, notes and trail lines. Chart labels and tooltips stay with their chart code.
   {name} is a value the code fills in (a number, a name, an era); {K:name} is that value set as
   the page's one orange keyword. The code only picks which sentence to use and fills the values;
   every word lives here. After changing anything, re-export review/conclusions.md and read the diff.
   Rules for the words: DESIGN.md section 6 (W1–W6). */
const COPY = {

  /* ---------- shared words ---------- */
  "w.shrankMost": "shrank the most",
  "w.grewLeast": "grew the least",
  "w.fadedMost": "faded the most",
  "w.above": "above",
  "w.below": "below",
  "w.grew": "grew",
  "w.shrank": "shrank",

  /* ---------- question pages (the Conclusion under each question) ---------- */
  "q1.answer": "{eraLead}, {K:top} grew the most ({topChg}) and {bot} {botMove} ({botChg}). {grewWho} ended the era larger.",
  "q1.everyCategory": "Every category",
  "q1.someCategories": "{n} of {total} categories",
  "q2.answer": "For DApps launched {era}, {K:group} best separated the ones that kept growing from the ones that faded ({share} of the model's weight).{sizeNote}",
  "q2.sizeNote": " Size carried {size}.",
  "q3.answer": "{eraLead}, the top 10 DApps held {K:top10} of wallets on average, and the single largest {top1}.",
  "q4.answer": "Of DApps launched {era}, {K:success} of the successful ones had 10K wallets by month 6, against {rest} of the rest.",
  "q4.tooFew": "Too few DApps launched {era} have a year of history to judge success yet.",
  "q5.answer": "Six months on, the typical DApp launched {era} keeps {K:month6} of its first users; after one month it already keeps only {month1}.",
  "q6.answer": "Six months after crossing 10K wallets, DApps launched {era} that kept growing hold {K:growers} of users month to month; one-hit DApps hold {flash}.",
  "q6.tooFew": "Too few DApps launched {era} crossed 10K wallets to compare.",

  /* ---------- market walk ---------- */
  "w0.head": "Every era told a different story. You are looking at {K:era}.",
  "w0.read": "Pick one: the next steps only look at what happened inside it.",

  "w1.head.top": "{Era}, {K:top} was the hottest ({topChg}); {bot} {botMove} ({botChg}).",
  "w1.head.follow": "{Era}, {K:cat} {moved}, #{rank} of {n} categories; {top} was the hottest ({topChg}).",
  "w1.moved.grew": "grew {x}",
  "w1.moved.shrank": "shrank {x}",
  "w1.read.top": "The bars are {n} categories {era}, each by how much its monthly wallets changed from the era's first three months to its last three; {top} grew the most.",
  "w1.read.follow": "The bars are {n} categories {era}, each by how much its monthly wallets changed from the era's first three months to its last three; {top} grew the most, and {cat}, the one you follow, comes {ord}.",

  "w2.none": "No {cat} DApps were active {era}.",
  "w2.head.first": "{K:first} holds {firstShare} of {cat}'s wallets {era}; the top 5 hold {top5}.",
  "w2.head.follow": "{K:lead} holds {leadShare} of {cat}'s wallets {era}, {ord} of the top 5; {first} leads with {firstShare}, and the top 5 hold {top5}.",
  "w2.read.first": "The bars are {cat}'s five biggest DApps {era}, each by its share of the category's monthly wallets; {first} holds the most.",
  "w2.read.follow": "The bars are {cat}'s five biggest DApps {era}, each by its share of the category's monthly wallets; {first} holds the most, and {lead}, the one you follow, comes {ord}.",

  "w3.ask.lead": "What does {lead} share with the other leaders?",
  "w3.head.first": "{Era}, {K:group} carries {share} of the model's weight, the most of any group, ahead of {second} ({secondShare}).",
  "w3.head.rose": "{Era}, {K:group} rose {groupMove} of the model's weight as {fall} fell {fallMove}; {group} is now the largest group.",
  "w3.head.stays": "{Era}, {K:group} stays the model's largest group ({groupMove}), while {rise} rose most, {riseMove}.",
  "w3.move": "from {from} to {to}",
  "w3.read": "In its third month, {lead} {verb} {cat}'s other leaders on {group}: {mine}, against {theirs} for them. It differs most on {group2}: {mine2}, against {theirs2}.",
  "w3.read.none": "Not enough early data on {cat}'s leaders.",
  "w3.verb.matches": "matches",
  "w3.verb.above": "is above",
  "w3.verb.below": "is below",
  "w3.plain.ret": "{v} of its users had used it before",
  "w3.plain.txpw": "{v} transactions per wallet",
  "w3.plain.wal": "{v} active wallets",
  "w3.plain.whale": "a {v} whale share",

  "w4.head": "Six months on, {K:lead} kept {kept} of its first users; the typical DApp launched {launchEra} kept {typical}.",
  "w4.read": "{side} the typical DApp{otherEra}.",
  "w4.side.above": "Above",
  "w4.side.below": "Below",
  "w4.otherEra": ". It launched {launchEra}, so it is set against DApps launched then, not {era}",
  "w4.head.typical": "Six months on, DApps launched {era} keep about {K:month6} of their first users.",
  "w4.read.cannot": "We cannot follow the first users of {lead}{why}, so only the typical curve is shown.",
  "w4.why.early": ": it launched before our data starts",
  "w4.why.small": ": it had fewer than {min} wallets in its first month",

  /* ---------- DApp walk ---------- */
  "v1.shape.grower": "kept growing",
  "v1.shape.flash": "was a one-hit",
  "v1.head.grower": "{name} {K:shape}: it held on to its users after the first peak.",
  "v1.head.flash": "{name} {K:shape}: it peaked early, then faded.",
  "v1.read": "It peaked in month {peakMonth} and by month 23 held {held} of that peak. The typical grower holds {grower}; the typical one-hit DApp {flash}.",

  "v2.none": "No {cat} data {era}.",
  "v2.head": "{name} ranks {K:rank} in {cat} {era}, with {share} of its wallets.",
  "v2.head.idle": "{name} had no activity {era}.",
  "v2.rank": "#{rank} of {n}",
  "v2.read": "{first} leads with {firstShare}; the top 5 hold {top5}.{catNote}",
  "v2.catNote": " {cat} as a whole {catMove} {catChg} in this era.",

  "v3.none": "We have no third-month numbers for {name}.",
  "v3.head": "In its third month, {name} looked most like {K:three}.",
  "v3.read": "{win} of its 20 closest lookalikes were still a success a year later ({winShare}), against {base} across all DApps.",

  "v4.head": "{Era}, {K:group} carried the most weight ({share}), led by {signal}; {group2} came next ({share2}), led by {signal2}.",
  "v4.read": "On {signal}, the model's #{rank} of {n} signals, {name} had {mine} in its third month, against {theirs} for DApps that lasted.",
  "v4.read.none": "None of these five signals is in our per-DApp data, so {name} is not placed on them.",
  /* a signal's sheet, opened from its name in the table */
  "sig.sub": "{group} · #{rank} of {n} signals",
  "sig.group": "One of the {group} signals: {note}.",
  "sig.typical": "In the first three months, the typical DApp that lasted had {s}; the others had {o}. Across all eras.",
  /* the trail, the "You found" line and the card */
  "v4.brief": "Watch {signal}: {mine} vs {theirs} for DApps that lasted.",
  "v4.brief.none": "Watch {group}.",
  "v4.say": "its {signal} was {mine} vs {theirs} for DApps that lasted",
  "v4.path.label": "Watch",
  "v4.path": "{Signal} {mine} vs {theirs}",
  "v4.th.signal": "Signal",
  "v4.th.group": "Group",
  "v4.th.share": "Share",
  "v4.th.cum": "Cumulative",
  "v4.table.aria": "Top five signals {era}",
  "v4.how": "The five of the {n} on-chain signals that carry the most weight in the model fitted on DApps launched {era}; together they carry {cum}. Share is each signal's part of all the weight: how much it matters, not which way it pushes. Groups add their signals up.",

  "v5.verdict.yes": "still a success",
  "v5.verdict.no": "not a success",
  "v5.head": "A year later, {name} was {K:verdict}.",
  "v5.read": "Months 10–12 averaged {avg} wallets: {pass1} 1,000 and {pass2} a quarter of its peak ({quarter}). Over its whole history: {life}.",
  "v5.read.short": "Over its whole history: {life}.",

  /* ---------- both walks: step names, the notes under each chart (How to read, Source, Worth noticing),
     and what each step leaves on the trail ("brief"), in the "You found" line ("say") and on the card ("path") ---------- */
  "s1.time": "Your DApp, dug down",
  "s2.time": "The market, dug down",
  "w.follow": "Next steps follow",

  "w0.short": "Moment",
  "w0.ask": "Pick a moment in the market.",
  "w0.card.change": "market wallets, first vs last 3 months",
  "w0.card.hottest": "Hottest",
  "w0.card.axis": "monthly wallets",
  "w0.cap": "Market wallets: the first three months of each era against its last three.",
  "w0.brief": "{era}: {note}.",
  "w0.path.label": "Moment",

  "w1.short": "Hot or fading",
  "w1.ask": "Who's hot, and who's fading?",
  "w1.follow.top": ", the hottest this era.",
  "w1.follow.more": "Follow another category",
  "w1.how": "Change in monthly active wallets, first three months of the era against the last three.",
  "w1.src": "Category activity · n = {n} categories, monthly active wallets.",
  "w1.careful": "{n} small categories are hidden: too few wallets at the start to measure change.",
  "w1.brief": "{cat} {move} {chg} {era}.",
  "w1.say": "{cat} {moved}",
  "w1.path.label": "Hot or fading",
  "w1.path": "{cat}, wallets {chg} in the era",

  "w2.short": "Leaders",
  "w2.ask": "Who runs it?",
  "w2.follow.top": ", the leader.",
  "w2.follow.more": "Follow another leader",
  "w2.how": "Each bar is one DApp's share of the category's monthly active wallets, averaged over the era.",
  "w2.src": "Leaders · n = {n} {cat} DApps active in the era.",
  "w2.careful.few": "The top 5 hold most of {cat}: a newcomer competes with a few giants.",
  "w2.careful.spread": "{cat} is spread out: beyond the top 5 there is still {rest} to win.",
  "w2.brief": "{first} leads {cat} with {firstShare}; the top 5 hold {top5}.",
  "w2.brief.none": "No leaders.",
  "w2.say": "{lead} led it with {share} of its wallets",
  "w2.path.label": "Leader",
  "w2.path.label.none": "Leaders",
  "w2.path": "{lead}, {share} of {cat} wallets",

  "w3.short": "What they share",
  "w3.ask": "What do the leaders share?",
  "w3.how": "Each line is one group of the model's 33 early signals: its share of the model's weight in each era, all of the group's signals added up. The grey band marks the era you picked; the darker line is the group the model leans on most in it. The Conclusion compares the leader you follow with the median of the category's other four leaders, in their third month.",
  "w3.src": "Model weights · n = {n} other leaders and {m} {cat} DApps with early data.",
  "w3.careful.below": "Here the leaders were below typical on {feat}: in {cat}, being early and big mattered more than what the model weighs most across all DApps.",
  "w3.careful.early": "Leaders that launched before 2020 have no early months in our data, so they drop out of the black bars.",
  "w3.brief": "Watch {group}: {feat} {lv} for leaders vs {tv} typical.",
  "w3.say": "its leaders differed most on {feat} ({lv} vs {tv} typical)",
  "w3.say.short": "its leaders differed most on {feat}",
  "w3.path.label": "Watch",
  "w3.path": "{group}, {share} of the model's weight",

  "w4.short": "Retention",
  "w4.ask": "Do their users stay?",
  "w4.lead.none": "the leader you followed",
  "w4.how": "Black: the typical DApp launched {era}, with the middle half shaded. Blue: {lead}.",
  "w4.how.typical": "Black: the typical DApp launched in this era, with the middle half shaded.",
  "w4.src": "Retention · n = {n} DApps with 100+ wallets in their first month.",
  "w4.careful": "Most of the drop happens in the first month: only {m1} are left after one month.",
  "w4.brief": "{lead} kept {kept} after six months (typical {typical}).",
  "w4.brief.typical": "Typical retention after six months: {typical}.",
  "w4.say": "{lead} kept {kept} of its first users after six months (typical {typical})",
  "w4.say.typical": "the typical DApp kept {typical} of its first users after six months",
  "w4.path.label": "Retention",
  "w4.path": "{kept} of first users at month 6",

  "v1.short": "Shape",
  "v1.ask": "What shape is it?",
  "v1.how": "Every widely used DApp falls into one of two shapes. Black: the median DApp that kept growing. Grey dashed: the median one-hit DApp. Blue: {name}.",
  "v1.src": "Shape · n = {n} widely used DApps ({grower} kept growing, {flash} one-hit).",
  "v1.brief": "{name} {shape}.",
  "v1.say": "{name} {shape}",
  "v1.path.label": "Shape",
  "v1.path.grower": "Kept growing",
  "v1.path.flash": "One-hit",

  "v2.short": "Standing",
  "v2.ask": "Where does it stand in its category?",
  "v2.how": "Share of the category's monthly active wallets, averaged over the era it launched in. Highlighted: this DApp.",
  "v2.src": "Standing · average monthly wallets of every {cat} DApp active in the era.",
  "v2.brief": "#{rank} of {n} in {cat}, {share} of its wallets.",
  "v2.say": "ranked #{rank} of {n} in {cat}",
  "v2.path.label": "Standing",
  "v2.path": "#{rank} of {n} in {cat}",

  "v3.short": "Lookalikes",
  "v3.ask": "Who did it look like early on?",
  "v3.how": "Each dot is one DApp in its third month. The ringed dots are its closest lookalikes on these two numbers; rust means still a success a year later, grey means not. Faint dots are every other DApp.",
  "v3.src": "Lookalikes · n = {n} DApps launched 2020–2024 with a known outcome.",
  "v3.careful": "Looking alike early is not ending alike: the lookalikes went different ways.",
  "v3.brief": "Looked like {three}; {win} of 20 lookalikes lasted.",
  "v3.brief.none": "No third-month data.",
  "v3.say": "{win} of its 20 lookalikes succeeded",
  "v3.path.label": "Lookalikes",
  "v3.path": "{win} of 20 succeeded",
  "v3.path.none": "No month-3 data",

  "v4.short": "Watch",
  "v4.ask": "What should it watch?",
  "v4.src": "Model weights · the {era} model, fitted on DApps launched in that era; {n} on-chain signals.",

  "v5.short": "Outcome",
  "v5.ask": "Did it make it?",
  "v5.how": "Blue: its monthly active wallets in the first two years. Shaded: months 10–12, the months we judge. Dashed line: 1,000 wallets.",
  "v5.src": "Outcome · {name}'s own monthly on-chain activity.",
  "v5.careful": "It kept {kept} of its first users after six months; the typical DApp launched {era} kept {typical}.",
  "v5.brief.yes": "A success a year later; {life} over its whole history.",
  "v5.brief.no": "Not a success a year later; {life} over its whole history.",
  "v5.say.yes": "a year later it was a success",
  "v5.say.no": "a year later it was not a success",
  "v5.path.label": "Outcome",
  "v5.path.yes": "Success",
  "v5.path.no": "Not a success"
};

/* fill a sentence: T("q3.answer", {eraLead:"After Dencun", top10:"72%", top1:"22%"}) */
function T(key, v = {}) {
  const s = COPY[key];
  if (s == null) throw new Error("copy.js has no sentence " + key);
  return s.replace(/\{(K:)?(\w+)\}/g, (m, k, name) => {
    const x = v[name];
    if (x === undefined) throw new Error("copy.js " + key + " needs {" + name + "}");
    return k ? K(x) : x;
  });
}
