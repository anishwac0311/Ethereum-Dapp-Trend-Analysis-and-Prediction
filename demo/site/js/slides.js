/* ---------- header: one title, one call to action ---------- */
function header(){
  const bar=(l,c,r)=>`<header class="top"><div class="bar">${l}${c}${r}</div>${S.view==="book"?`<nav class="steps" aria-label="Pages">${pages().map((p,i)=>`<button class="${i===S.idx?"cur":S.read.includes(p)?"done":""}" data-jump="${i}" title="${PNAME[p]}" aria-label="Page ${i+1} of ${pages().length}: ${PNAME[p]}"></button>`).join("")}</nav>`:""}</header>`;
  if(S.view==="home") return bar(`<span class="brand">On-chain DApp research</span>`,`<span></span>`,`<span class="navgroup"><button class="navlink" data-go="qindex">The six questions</button><button class="navlink" data-go="about">About us</button></span>`);
  if(S.view==="about"||S.view==="method") return bar(`<button class="navlink" data-act="aboutback">← Back</button>`,`<span></span>`,`<span></span>`);
  if(S.view==="pick") return bar(`<button class="navlink" data-go="home">← Home</button>`,`<span class="lbl">Choose your DApp</span>`,`<span></span>`);
  if(S.view==="card") return bar(`<button class="navlink" data-act="reopen">← Back</button>`,`<span class="lbl">Your card</span>`,`<button class="navlink" data-go="home">Start over</button>`);
  const n=new Set(S.read.map(qOf)).size;
  return bar(`<button class="navlink" data-go="home">← Home</button>`,`<span class="lbl">${BOOKS[S.scen].time}</span>`,`<button class="pill" data-go="card">Get my card · ${n}</button>`);
}

/* ---------- a slide: the answer on the left, the evidence on the right ---------- */
const KIND = {q1:"Describe",q2:"Predict",q3:"Describe",q4:"Describe",q5:"Describe",q6:"Describe"};
const kindTag = q => `<span class="s-kind ${KIND[q].toLowerCase()}" data-tip="${KIND[q]==="Predict"?"What our model says separates DApps that last from those that fade":"What happened in the data"}">${KIND[q]}</span>`;
const ASK = {q1:"Which categories are growing or declining?", q2:"What separates apps that last from those that fade?", q3:"How concentrated is activity among the biggest apps?", q4:"How quickly do successful apps gain users?", q5:"How many users stay after their first visit?", q6:"What happens before an app takes off?"};
/* top-right filter bar: compact selects and sliders, so the charts sit right under the title */
/* filters live beside the title as small chips; each opens a panel on hover, focus or tap */
const fwrap=(label,body)=>`<div class="fl"><button type="button" class="fchip" aria-haspopup="true">${label}</button><div class="fpop">${body}</div></div>`;
function selectFilter(name,label,opts,cur){ return fwrap(label,`<span class="flbl">${label}</span><select data-sel="${name}" aria-label="${label}">${opts.map(o=>`<option value="${o[0]}"${o[0]===cur?" selected":""}>${o[1]}</option>`).join("")}</select>`); }
/* the thread between pages: what this page found, and the next question it raises */
/* the DApp a finished market walk hands over to Layer 3 */
/* the DApp a market walk digs into: the leader you followed, else another top-5 leader, else the biggest of the widely used DApps in that category, so every market card has a way to a saveable card */
function deepOf(){ if(S.scen!=="s2") return null; const L=leadOf(era(),S.cat);
  const k=L?[S.leader,...L.top.map(t=>t[0])].find(k=>k&&D.dapps[k]):null; if(k) return k;
  const inCat=Object.keys(D.dapps).filter(k=>D.dapps[k].cat===S.cat).sort((a,b)=>(D.dapps[b].peak||0)-(D.dapps[a].peak||0)); return inCat[0]||null; }
function bridge(p,q,next){
  if(STEP[q]) return "";
  const d=me(), who=S.scen==="s1"&&d?esc(d.name):null, cat=S.scen==="s1"&&d?d.cat:S.cat;
  const ASKN = who ? {q4:`Did ${who} find its users fast enough?`, q5:`Do ${who}'s users come back?`, q6:`What happened around ${who}'s 10K mark?`, q3:`How big are ${who}'s rivals?`, q1:`Is ${cat} still growing?`, q2:`Is ${who} built to last?`}
    : {q3:`Is ${cat} run by a few giants?`, q2:`With giants on top, do new ${cat} apps last?`, q5:`Do the users of ${cat} apps come back?`, q4:`How fast do the ${cat} winners find users?`, q1:`Is ${cat} growing?`, q6:"What happens around the 10K mark?"};
  if(!next) return `<div class="s-bridge"><span class="s-mono">You found</span><p>${p.brief||""}</p><span class="s-mono">Next</span><p><button class="s-link" data-go="card">See every answer on your card →</button></p></div>`;
  const nq=qOf(next), lead=S.q1lead;
  const follow = S.scen==="s2" && q==="q1" && lead && lead.c!==S.cat ? `<p class="s-follow"><button class="s-cardbtn" data-follow="${lead.c}">Follow ${lead.c}, the fastest grower (${sgn(lead.g)}) →</button><span>or keep going with ${S.cat}</span></p>` : "";
  return `<div class="s-bridge"><span class="s-mono">You found</span><p>${p.brief||""}</p><span class="s-mono">So next</span><p><button class="s-link s-nextq" data-turn="1">${nq.toUpperCase()} · ${ASKN[nq]||ASK[nq]} →</button></p>${follow}</div>`;
}
/* the same note block under every scenario figure: how to read it, the success rule when it is used,
   what is worth noticing, and where the numbers come from */
function figNotes(p,q){
  if(p.how||p.src){ const row=(k,v)=>v?`<p><span class="s-mono">${k}</span><span>${v}</span></p>`:""; return `<div class="s-note">${row("How to read",p.how)}${p.define?row("Success",`Still averaging 1,000+ wallets in months 10–12 and keeping a quarter of the early peak. <button class="s-link" data-go="method">Method ›</button>`):""}${row("Worth noticing",p.careful)}${row("Source",p.src)}</div>`; }
  const you=S.scen==="s1"&&me()?` The rust line is ${esc(me().name)}.`:"", e=era();
  const HOW={q1:"Top: monthly active wallets across all categories; the dotted line is the month you picked. Bottom: each category against a year earlier.",
    q3:"Top: share of wallets held by the 10 largest DApps each month. Bottom: share held by the largest DApps of that year, ranked by size (log scale).",
    q2:"Top: the median shape of each group, as a share of each DApp's own peak."+you+" Bottom: each feature group's share of the model's weight.",
    q5:"Black: DApps launched in the chosen era, with the middle half shaded. Grey: the other two eras."+you,
    q4:"Top: share of each group that had reached 10K cumulative wallets by each month. Bottom: the typical cumulative path (log scale)."+you,
    q6:"Every DApp is lined up on the month it crossed 10K cumulative wallets (marked 10K). Lines are the median of each group."+you};
  const SRC={q1:`Monthly activity of ${D.meta.n_dapps} DApps, ${monthLabel(D.meta.panel_start)} – ${monthLabel(D.meta.panel_end)}.`,
    q3:`Monthly activity of ${D.meta.n_dapps} DApps, ${monthLabel(D.meta.panel_start)} – ${monthLabel(D.meta.panel_end)}.`,
    q2:`${D.q2.n} widely used DApps (1,000+ monthly wallets and a year of history); model trained on ${D.q4.n.success+D.q4.n.other} DApps with a known outcome.`,
    q5:`${D.q5.periods[e].n} DApps launched ${PERIOD_IN[e]} with 100+ wallets in their first month.`,
    q4:`${D.q4.n.success} successful and ${D.q4.n.other} other DApps with a known outcome.`,
    q6:`Widely used DApps that crossed 10K cumulative wallets.`};
  const row=(k,v)=>`<p><span class="s-mono">${k}</span><span>${v}</span></p>`;
  return `<div class="s-note">${row("How to read",HOW[q]||"")}${p.define?row("Success",`Still averaging 1,000+ wallets in months 10–12 and keeping a quarter of the early peak. <button class="s-link" data-go="method">Method ›</button>`):""}${p.careful?row("Worth noticing",p.careful):""}${row("Source",`${q.toUpperCase()} ${QNAME[q]} · ${SRC[q]||""}`)}</div>`;
}
function slide(p){
  const q=qOf(pages()[S.idx]), f=(p.filters||[]).filter(Boolean);
  if(S.theme==="study"){
    const P=pages(), prev=S.idx>0?P[S.idx-1]:null, next=S.idx<P.length-1?P[S.idx+1]:null;
    return `<main class="study sslide s-wrap s-withtrail"><div class="s-col1"><div class="s-crumb"><button class="s-back-m" data-go="home" aria-label="Back to Home">← Home</button><span class="s-mono">${STEP[q]?`<span class="s-stepw">Step </span>${S.idx+1} of ${P.length}`:q.toUpperCase()} <em>${QNAME[q]}</em></span>${kindTag(q)}</div>${(()=>{ const L=walkLayers().layers.filter(l=>l[1]!=="–"); return L.length?`<p class="w-ctx s-mono">${L.map(l=>l[1]).join(" <i>›</i> ")}</p>`:""; })()}
      <h1 class="s-qtitle">${p.ask||ASK[q]}</h1>
      <div class="s-crow"><blockquote class="s-concl${S.scen==="s1"||S.scen==="s2"?" you-k":""}"><span class="s-mono">Conclusion</span><p>${p.head}</p>${(p.read||p.caption)?`<p class="s-sub2">${p.read||p.caption}</p>`:""}</blockquote>${f.length?`<div class="filters">${f.join("")}</div>`:""}</div>${p.pick||""}
      ${p.bare?p.fig:`<figure class="s-fig">${p.fig}${p.under||""}${figNotes(p,q)}</figure>`}
      ${bridge(p,q,next)}
      <nav class="s-pn">${prev?`<button data-turn="-1"><span class="s-mono">Previous</span><span>← ${STEP[prev]?`${P.indexOf(prev)+1} ·`:prev.slice(0,2).toUpperCase()} ${PNAME[prev]}</span></button>`:"<span></span>"}
        ${next?`<button data-turn="1"><span class="s-mono">Next</span><span>${STEP[next]?`${P.indexOf(next)+1} ·`:next.slice(0,2).toUpperCase()} ${PNAME[next]} →</span></button>`
          :`<button data-turn="1"><span class="s-mono">Finish</span><span>See your card →</span></button>`}</nav></div>${trail()}</main>`;
  }
  return `<div class="slide"><header class="slide-head"><div class="ask">${ASK[q]}</div><h2>${p.head}</h2>
      <div class="caprow"><p class="caption">${p.read||p.caption||""}</p>${f.length?`<div class="filters">${f.join("")}</div>`:""}</div></header>
    <section class="picture"><div class="fig">${p.fig}</div>${p.under||""}</section>
    <div class="notes one">${p.careful?`<div class="careful"><span class="lbl">Worth noticing</span><p>${p.careful}</p></div>`:""}</div></div>`;
}

