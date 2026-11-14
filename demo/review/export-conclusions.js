/* Export every Conclusion the demo site shows, as Markdown, for a word-by-word review.
   Run it in the browser console on the local site (http://localhost:8765). It drives the
   site's own render(), so the text is exactly what a visitor sees; the orange keyword
   is wrapped in **bold**. The result is returned as a string (and kept in window.__concl).
   To refresh review/conclusions.md: open the local site in Chrome, paste this file into the
   DevTools console, then run copy(window.__concl) and paste into conclusions.md.
   Not part of the site: this folder is not deployed. */
(() => {
  const ERAS = ["before", "between", "after"];
  const ERA_NAME = { before: "Before Terra", between: "Terra → Dencun", after: "After Dencun" };
  const md = [];
  const txt = el => {
    const c = el.cloneNode(true);
    c.querySelectorAll(".k").forEach(k => { k.textContent = `**${k.textContent}**`; });
    return c.textContent.replace(/\s+/g, " ").trim();
  };
  const grab = () => {
    render();
    const t = document.querySelector("main h1, main .s-qtitle");
    const c = document.querySelector("main .s-concl");
    if (!c) return { title: t ? t.textContent.trim() : "?", lines: ["(no Conclusion on this page)"], keys: 0 };
    const ps = [...c.querySelectorAll("p")];
    return { title: t ? t.textContent.replace(/\s+/g, " ").trim() : "?", lines: ps.map(txt), keys: c.querySelectorAll(".k").length };
  };
  const out = (label, g) => {
    md.push(`#### ${label}`, "", `*${g.title}*`, "");
    g.lines.forEach((l, i) => md.push(i === 0 ? `> ${l}` : `>\n> <sub>${l}</sub>`));
    md.push("");
    if (g.keys !== 1) md.push(`⚠️ ${g.keys} orange keywords (expected 1)`, "");
  };
  const keep = { ...S };

  md.push("# Conclusions on the demo site", "",
    `Exported from the local site on ${new Date().toISOString().slice(0, 10)}. Orange keywords are in **bold**; a ⚠️ line flags a Conclusion without exactly one. Lines in small type are the line under the Conclusion.`, "");

  /* 1. Question pages: six questions × three eras (question pages keep their own era, S.sera) */
  md.push("## 1. Question pages", "");
  S.scen = null; S.dapp = null; S.custom = null; S.view = "qpage";
  for (const q of ["q1", "q2", "q3", "q4", "q5", "q6"]) {
    md.push(`### ${q.toUpperCase()}`, "");
    for (const e of ERAS) { S.sq = q; S.sera = e; out(ERA_NAME[e], grab()); }
  }

  /* 2. Market walk: era (step 1), category (step 2), then each top-5 leader (steps 3–5) */
  md.push("## 2. Market walk", "");
  S.scen = "s2"; S.view = "book"; S.dapp = null; S.custom = null;
  const P2 = BOOKS.s2.pages;
  for (const e of ERAS) {
    md.push(`### ${ERA_NAME[e]}`, "");
    S.era = e; S.catPicked = false; S.leader = null; S.idx = 0;
    out("Step 1", grab());
    for (const cat of Object.keys(D.lead[e] || {})) {
      const L = D.lead[e][cat]; if (!L || !L.top || !L.top.length) continue;
      S.cat = cat; S.catPicked = true; S.leader = null; S.idx = 1;
      out(`${cat} · Step 2`, grab());
      for (const [slug, name] of L.top.slice(0, 5)) {
        S.leader = slug;
        for (let i = 2; i < P2.length; i++) { S.idx = i; out(`${cat} · following ${name} · Step ${i + 1}`, grab()); }
      }
    }
  }

  /* 3. DApp walks: ten DApps (the two booth examples, then the biggest success and the
        biggest non-success in each era, then the biggest in categories not yet covered) */
  md.push("## 3. DApp walks", "");
  const all = Object.entries(D.dapps), byPeak = (a, b) => (b[1].peak || 0) - (a[1].peak || 0);
  const pick = [];
  const add = s => { if (s && D.dapps[s] && !pick.includes(s) && pick.length < 10) pick.push(s); };
  ["uniswap-v3", "beanstalk"].forEach(add);
  for (const e of ERAS) for (const ok of [true, false]) {
    const c = all.filter(([, d]) => d.period === e && !!d.success === ok).sort(byPeak)[0]; add(c && c[0]);
  }
  for (const cat of ["Gaming", "NFT", "Social", "Infrastructure", "Other"]) {
    if (pick.some(s => D.dapps[s].cat === cat)) continue;
    const c = all.filter(([, d]) => d.cat === cat).sort(byPeak)[0]; add(c && c[0]);
  }
  S.scen = "s1"; S.view = "book"; S.custom = null;
  const P1 = BOOKS.s1.pages;
  for (const s of pick) {
    const d = D.dapps[s];
    md.push(`### ${d.name}`, "", `${d.cat} · launched ${d.launch} · ${ERA_NAME[d.period]} · ${d.success ? "success" : "not a success"}`, "");
    S.dapp = s; S.era = d.period;
    for (let i = 0; i < P1.length; i++) { S.idx = i; out(`Step ${i + 1}`, grab()); }
  }

  Object.assign(S, keep); render();
  window.__concl = md.join("\n");
  return window.__concl.length;
})();
