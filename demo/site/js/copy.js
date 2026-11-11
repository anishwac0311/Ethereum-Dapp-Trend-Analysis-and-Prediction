/* All Conclusion text on the site, in one place (question pages and both walks).
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

  "w3.ask": "What does {lead} share with the other leaders?",
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
  "v5.read.short": "Over its whole history: {life}."
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
