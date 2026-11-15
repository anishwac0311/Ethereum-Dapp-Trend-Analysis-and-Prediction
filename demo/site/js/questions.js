/* =====================================================================
   The study: the baseline. Six plain questions, each answered by one part of the research,
   with one era switch that recomputes every answer. Market questions (Q1, Q3) use the era as a
   calendar window; cohort questions (Q2, Q4, Q5, Q6) use the DApps launched in that era.
   ===================================================================== */
const SERAS=[
  {k:"before", name:"Before Terra", span:"2020 – Apr 2022", note:"DeFi summer, 2021 bull market", from:"2020-01", to:"2022-04"},
  {k:"between",name:"Terra → Dencun",span:"May 2022 – Feb 2024", note:"Terra and FTX collapse", from:"2022-05", to:"2024-02"},
  {k:"after",  name:"After Dencun", span:"Mar 2024 – Dec 2025", note:"Dencun upgrade, cheaper layer-2 fees", from:"2024-03", to:"2025-12"}];
const SQ=[
  {q:"q1", tag:"Categories", kind:"Describe", ask:"Which categories are growing or declining?"},
  {q:"q2", tag:"Survival", kind:"Predict",  ask:"What separates apps that last from those that fade?"},
  {q:"q3", tag:"Concentration", kind:"Describe", ask:"How concentrated is activity among the biggest apps?"},
  {q:"q4", tag:"Speed", kind:"Describe", ask:"How quickly do successful apps gain users?"},
  {q:"q5", tag:"Retention", kind:"Describe", ask:"How many users stay after their first visit?"},
  {q:"q6", tag:"Take-off", kind:"Describe", ask:"What happens before an app takes off?"}];
const SC={ink:"#1A1A1A", rust:"#9C4A26", grey:"#A39E95", soft:"#D9D4CA", rule:"#E2DDD4"};
const sera=()=>SERAS.find(x=>x.k===(S.sera||"after"));
const med=a=>{ const v=a.filter(x=>x!=null&&isFinite(x)).sort((x,y)=>x-y); if(!v.length) return null; const h=v.length/2; return v.length%2?v[Math.floor(h)]:(v[h-1]+v[h])/2; };
const inEra=(lm,e)=>lm && lm>=e.from && lm<=e.to;

/* horizontal bars, diverging around zero when any value is negative */
function sBars(rows, fmt, opt={}){
  const ph=PHONE(), W=ph?560:980, lw=ph?150:170, rw=Math.max(ph?64:70, Math.max(...rows.map(r=>String(fmt(r.v)).length))*(ph?10.2:8)+14) /* room for the longest value label */, H=ph?440:380, cut=ph?14:20, RH=(H-30)/rows.length, neg=rows.some(r=>r.v<0);
  const vmax=Math.max(...rows.map(r=>Math.abs(r.v)),1e-9), span=W-lw-rw;
  const x0=neg? lw+span*(Math.abs(Math.min(...rows.map(r=>r.v),0))/(Math.abs(Math.min(...rows.map(r=>r.v),0))+Math.max(...rows.map(r=>r.v),0)||1)) : lw;
  const sc=v=>v/vmax*(neg? Math.max(x0-lw, lw+span-x0) : span);
  let s=`<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMinYMin meet" role="img" aria-label="${esc(opt.aria||"bars")}">`;
  [0.25,0.5,0.75,1].forEach(t=>{ if(!neg) s+=`<line x1="${lw+span*t}" x2="${lw+span*t}" y1="0" y2="${rows.length*RH}" stroke="${SC.rule}"/>`; });
  s+=`<line x1="${x0}" x2="${x0}" y1="0" y2="${rows.length*RH}" stroke="${SC.grey}"/>`;
  rows.forEach((r,i)=>{ const y=i*RH+RH/2, w=sc(r.v), col=r.hi?"#3860BE":(r.v<0?SC.grey:SC.ink);
    s+=`<g class="hovrow" data-tip="${esc(r.tip||`${r.label}\n${fmt(r.v)}`)}"><rect class="hovbg" x="0" y="${i*RH}" width="${W}" height="${RH}"/>
      <text class="sax" x="${lw-12}" y="${y+4}" text-anchor="end">${esc(r.label.length>cut?r.label.slice(0,cut-1)+"…":r.label)}</text>
      <rect x="${w<0?x0+w:x0}" y="${y-6}" width="${Math.max(2,Math.abs(w))}" height="12" fill="${col}"/>
      <text class="sax" x="${w<0?x0+8:x0+w+8}" y="${y+4}" text-anchor="start">${fmt(r.v)}</text></g>`; });
  return s+"</svg>";
}

/* each question for one era: the plain answer, its figure, and its sample */
/* an era as the opening words of a sentence: "Between Terra and Dencun, …" (not the label "Terra → Dencun") */
const eraLead=e=>({before:"Before Terra",between:"Between Terra and Dencun",after:"After Dencun"})[e.k];
function studyQ(q, e){
  const P=e.k, PIN={before:"before Terra",between:"between Terra and Dencun",after:"after Dencun"}[P];
  if(q==="q1"){
    const M=D.q1.months, a=M.indexOf(e.from), b=M.indexOf(e.to);
    const rows=CATS.map(c=>{ const W=D.q1.wallets[c], s0=W.slice(a,a+3).filter(v=>v!=null), s1=W.slice(b-2,b+1).filter(v=>v!=null);
      const m0=s0.reduce((x,y)=>x+y,0)/(s0.length||1), m1=s1.reduce((x,y)=>x+y,0)/(s1.length||1);
      return {label:c, v:m0>0?m1/m0-1:null, w0:m0, w1:m1, n:D.q1.dapps[c][b]}; }).filter(r=>r.v!=null && r.w0>=1000).sort((x,y)=>y.v-x.v);
    rows.forEach(r=>r.tip=`${r.label}, ${e.name}\n${chg(r.v)} across the era\n${fmtN(r.w0)} → ${fmtN(r.w1)} monthly wallets\n${r.n||0} active DApps at the end`);
    const top=rows[0], bot=rows[rows.length-1]; rows[0].hi=true;
    const grew=rows.filter(r=>r.v>0).length;
    return {brief:`${top.label} grew the most (${chg(top.v)}); ${bot.label} ${bot.v<0?"shrank the most":"grew the least"} (${chg(bot.v)}).`,
      answer:T("q1.answer",{eraLead:eraLead(e), top:top.label, topChg:chg(top.v), bot:bot.label, botMove:T(bot.v<0?"w.shrankMost":"w.grewLeast"), botChg:chg(bot.v), grewWho:grew===rows.length?T("q1.everyCategory"):T("q1.someCategories",{n:grew,total:rows.length})}),
      fig:sBars(rows,v=>chg(v),{aria:"Wallet change by category"}), legend:`Change in monthly active wallets, first three months of the era against the last three. Categories under 1K wallets at the start are left out.`,
      n:rows.reduce((x,r)=>x+(r.n||0),0), unit:"active DApps at the end of the era"};
  }
  if(q==="q2"){
    const W=D.q5.weights[P], order=["Size","Stickiness","Context","Movement","Concentration"], top=order.slice().sort((a,b)=>W[b][0]-W[a][0])[0];
    const rows=order.map(g=>({label:g,v:W[g][0],hi:g===top,tip:`${g}, ${e.name}\n${pct(W[g][0])} of the model's weight\nrange ${pct(W[g][1])} to ${pct(W[g][2])}`}));
    const ds=Object.values(D.snap).filter(d=>inEra(d.lm,e) && d.s!=null), ok=ds.filter(d=>d.s===1).length;
    return {brief:`${top} best tells lasting DApps from one-hit ones (${pct(W[top][0])} of the model's weight).`,
      answer:T("q2.answer",{era:PIN, group:top.toLowerCase(), share:pct(W[top][0]), sizeNote:top==='Size'?'':T("q2.sizeNote",{size:pct(W.Size[0])})}),
      fig:sBars(rows,v=>pct(v),{aria:"Weight of each feature group"}), legend:`Share of the model's weight held by each feature group. The model sees only a DApp's early months and predicts whether it is still a success a year later. Bars show the middle estimate; hover for the range.`,
      n:ds.length, unit:`DApps launched in the era with a known outcome (${ok} successes)`, thin:ok<10};
  }
  if(q==="q3"){
    const M=D.q3.months, a=M.indexOf(e.from), b=M.indexOf(e.to), xs=M.map((m,i)=>i).filter(i=>i>=M.indexOf("2020-06"));
    const avg=k=>{ const v=D.q3.eco[k].slice(a,b+1).filter(x=>x!=null); return v.reduce((x,y)=>x+y,0)/v.length; };
    const t10=avg("top10_share"), t1=avg("top1_share");
    const b1=e.k==="after"?M.length-1:b+1, a1=Math.max(a,xs[0]);
    const band=[{lo:[[a1,0],[b1,0]],hi:[[a1,1],[b1,1]],color:SC.soft,op:.45}];
    const fig=chart({tipx:i=>monthLabel(M[i]),w:980,h:380,r:150,x:[xs[0],M.length-1],y:[0,1],xticks:xs.filter(i=>M[i].endsWith("-01")),fx:i=>M[i].slice(0,4),yticks:[0,.25,.5,.75,1],fy:t=>pct(t),bands:band,
      events:[{x:M.indexOf(D.meta.terra),label:"Terra"},{x:M.indexOf(D.meta.dencun),label:"Dencun"}],
      series:[{pts:xs.map(i=>[i,D.q3.eco.top10_share[i]]),color:SC.ink,w:2.5,label:"Top 10",tip:"Top 10 DApps"},{pts:xs.map(i=>[i,D.q3.eco.top1_share[i]]),color:SC.rust,w:2,dash:"5 4",label:"Largest one",tip:"Largest DApp"}],
      xlabel:"share of monthly active wallets",aria:"Top-10 and top-1 share over time"});
    return {brief:`The top 10 DApps held ${pct(t10)} of wallets; the largest one ${pct(t1)}.`,
      answer:T("q3.answer",{eraLead:eraLead(e), top10:pct(t10), top1:pct(t1)}),
      fig, legend:"Solid: top 10 DApps. Dashed: the single largest DApp. Shaded: the chosen era.", n:D.q3.eco_n[b], unit:"active DApps at the end of the era"};
  }
  if(q==="q4"){
    const ds=Object.values(D.snap).filter(d=>inEra(d.lm,e) && d.s!=null && d.cw && d.cw[0]!=null);
    const ok=ds.filter(d=>d.s===1), no=ds.filter(d=>d.s===0), xs=[...Array(13).keys()];
    const share=(arr,i)=>arr.length? arr.filter(d=>(d.cw[i]??d.cw.filter(v=>v!=null).slice(-1)[0])>=1e4).length/arr.length : null;
    const so=xs.map(i=>[i,share(ok,i)]), sn=xs.map(i=>[i,share(no,i)]);
    const fig=chart({tipx:t=>t===0?"First month":`Month ${t}`,w:980,h:380,r:150,x:[0,12],y:[0,1],xticks:xs,fx:t=>t===0?"M0":`M${t}`,yticks:[0,.25,.5,.75,1],fy:t=>pct(t),xlabel:"months since the first user · share with 10K cumulative wallets",
      series:[{pts:so,color:SC.ink,w:2.5,label:`Successful (${ok.length})`,tip:"Successful"},{pts:sn,color:SC.rust,w:2,dash:"5 4",label:`Others (${no.length})`,tip:"Others"}],aria:"Share reaching 10K wallets"});
    const n=ds.length;
    return {brief:ok.length?`By month 6, ${pct(so[6][1])} of successful DApps had 10K wallets, against ${pct(sn[6][1])} of the rest.`:"Too few DApps with a year of history yet.",
      answer:ok.length? T("q4.answer",{era:PIN, success:pct(so[6][1]), rest:pct(sn[6][1])}) : T("q4.tooFew",{era:PIN}),
      fig, legend:"Solid: successful DApps. Dashed: the rest. Each point is the share that had reached 10K cumulative wallets by that month.", n, unit:"DApps launched in the era with a known outcome", thin:ok.length<8};
  }
  if(q==="q5"){
    const Pd=D.q5.periods[P], xs=D.q5.months;
    const others=SERAS.filter(x=>x.k!==P).map(x=>({pts:xs.map(i=>[i,D.q5.periods[x.k].median[i]]),color:SC.grey,w:1.5,tip:x.name}));
    const fig=chart({tipx:t=>t===0?"Launch month":`Month ${t}`,w:980,h:380,r:150,x:[0,6],y:[0,1],xticks:xs,fx:t=>t===0?"launch":`M${t}`,yticks:[0,.25,.5,.75,1],fy:t=>pct(t),xlabel:"months after launch · launch-month wallets still active",
      bands:[{lo:xs.map(i=>[i,Pd.lo[i]]),hi:xs.map(i=>[i,Pd.hi[i]]),color:SC.soft,op:.6}],
      series:[...others,{pts:xs.map(i=>[i,Pd.median[i]]),color:SC.ink,w:2.5,label:`${e.name} · ${pct(Pd.median[6])}`,tip:e.name}],aria:"Launch cohort retention"});
    return {brief:`${pct(Pd.median[6])} of first users are still active after six months.`,
      answer:T("q5.answer",{era:PIN, month6:pct(Pd.median[6]), month1:pct(Pd.median[1])}),
      fig, legend:"Black: the chosen era, with the middle half of DApps shaded. Grey: the other eras.", n:Pd.n, unit:"DApps with 100+ launch-month wallets", thin:Pd.n<30};
  }
  if(q==="q6"){
    const ds=Object.values(D.dapps).filter(d=>d.period===P && d.event);
    const rel=[...Array(19).keys()].map(i=>i-6);
    const curve=grp=>rel.map(r=>[r, med(ds.filter(d=>d.group===grp).map(d=>{ const k=d.event.rel.indexOf(r); return k<0?null:d.event.retention_prev_month[k]; }))]);
    const g=curve("grower"), f=curve("flash"), gN=ds.filter(d=>d.group==="grower").length, fN=ds.filter(d=>d.group==="flash").length;
    const fig=chart({tipx:t=>t===0?"The month it crosses 10K":t<0?`${-t} month${t===-1?"":"s"} before 10K`:`${t} month${t===1?"":"s"} after 10K`,w:980,h:380,r:150,x:[-6,12],y:[0,1],xticks:rel.filter(r=>r%3===0),fx:t=>t===0?"10K":t>0?`+${t}`:t,yticks:[0,.25,.5,.75,1],fy:t=>pct(t),
      events:[{x:0,label:"crosses 10K wallets"}],xlabel:"months around the 10K crossing · month-over-month retention",
      series:[{pts:g,color:SC.ink,w:2.5,label:`Kept growing (${gN})`,tip:"Kept growing"},{pts:f,color:SC.rust,w:2,dash:"5 4",label:`One-hit (${fN})`,tip:"One-hit"}],aria:"Retention around the 10K crossing"});
    const g6=g.find(x=>x[0]===6)[1], f6=f.find(x=>x[0]===6)[1];
    return {brief:(g6!=null&&f6!=null)?`Six months after 10K wallets, growers keep ${pct(g6)} of users a month; one-hit DApps ${pct(f6)}.`:"Too few DApps crossed 10K wallets.",
      answer:(g6!=null&&f6!=null)? T("q6.answer",{era:PIN, growers:pct(g6), flash:pct(f6)}) : T("q6.tooFew",{era:PIN}),
      fig, legend:"Median month-over-month retention, lined up on the month each DApp passed 10K cumulative wallets.", n:ds.length, unit:"DApps launched in the era that crossed 10K", thin:ds.length<12};
  }
}


function eraTimeline(){ const e=sera(); return `<div class="s-time">${SERAS.map(x=>`<button class="s-stop ${x.k===e.k?"on":""}" data-sera="${x.k}" aria-pressed="${x.k===e.k}"><i></i><b>${x.name}</b><span class="s-mono">${x.span}</span><span class="s-enote">${x.note}</span></button>`).join("")}</div>`; }
function studyHeader(){
  const e=sera(), v=S.view, onQ=v==="qindex"||v==="qpage", onDiag=v==="pick"&&S.pickTab==="enter";
  const nav=`<nav class="s-nav" id="s-nav"><button class="s-menu-x" data-act="menu" aria-label="Close menu">✕</button><button class="${v==="home"?"on":""}" data-go="home">Home</button><button class="${onQ?"on":""}" data-go="qindex">Questions</button><button class="${v==="compare"?"on":""}" data-go="compare">Compare</button><button class="${onDiag?"on":""}" data-go="pick" data-tab="enter" data-start-diag="1">Neighbours</button><button class="${v==="game"?"on":""}" data-go="game">Game</button><button class="${v==="wall"?"on":""}" data-go="wall">Booth</button><button class="${v==="method"?"on":""}" data-go="method">Method</button><button class="${v==="about"?"on":""}" data-go="about">About</button></nav>`;
  const subrow=(back,mid,right="")=>`<div class="s-wrap"><div class="s-sub s-sub-${v}">${back}<span class="s-mono s-subt">${mid}</span>${right||"<span></span>"}</div></div>`;
  let below="";
  if(v==="qpage") below=subrow(`<button class="s-back" data-go="qindex">← All questions</button>`,`<span class="s-eras">${SERAS.map(x=>`<button class="${x.k===e.k?"on":""}" data-sera="${x.k}" aria-pressed="${x.k===e.k}">${x.name}</button>`).join("")}</span>`);
  else if(v==="book"){ const n=new Set(S.read.map(qOf)).size;
    below=subrow(`<button class="s-back" data-go="home">← Home</button>`,(()=>{ const {lay,layers}=walkLayers(); return `<span class="w-crumbs">${layers.map(([k,v],i)=>`<span class="${i+1===lay?"on":i+1<lay?"done":""}" title="${k}">${v==="–"?k:v}</span>`).join('<i>›</i>')}</span>`; })(),
      `<span class="s-right"><nav class="s-steps" aria-label="Pages">${pages().map((p,i)=>`<button class="${i===S.idx?"cur":S.read.includes(p)?"done":""}" data-jump="${i}" title="${PNAME[p]}" aria-label="Page ${i+1} of ${pages().length}: ${PNAME[p]}"></button>`).join("")}</nav></span>`); }
  else if(v==="pick"&&S.pickTab!=="enter") below=subrow(`<button class="s-back" data-go="home">← Home</button>`,"");
  else if(v==="card") below=subrow(`<button class="s-back" data-act="reopen">← Back</button>`,"Your card",`<button class="s-back" data-go="home">Start over</button>`);
  return `<header class="s-head"><div class="s-wrap"><div class="s-top"><button class="s-brand" data-go="home"><svg class="s-mark" viewBox="0 0 20 32" aria-hidden="true"><path d="M10 1 L19 16 L10 21 L1 16 Z M10 1 V21 M1 16 L10 11 L19 16" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/><path d="M1 19 L10 31 L19 19 L10 24 Z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg><b>Ethereum DApp Trend Analysis and Popularity Prediction</b></button><button class="s-menu" data-act="menu" aria-label="Menu" aria-controls="s-nav"><svg viewBox="0 0 20 14" aria-hidden="true"><path d="M1 1h18M1 7h18M1 13h18" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg></button>${nav}<button class="s-scrim" data-act="menu" aria-label="Close menu" tabindex="-1"></button></div></div>${below}</header>`;
}
function studyFooter(){ return `<footer class="s-foot"><div class="s-wrap"><span class="s-mono">Group 9 · UC Irvine · ${new Date().getFullYear()}</span></div></footer>`; }

function eraTable(e){
  const order=["Size","Stickiness","Context","Movement","Concentration"], top=k=>order.slice().sort((a,b)=>D.q5.weights[k][b][0]-D.q5.weights[k][a][0])[0];
  return `<figure class="s-fig s-erafig"><span class="s-mono s-figlab">The same model in each era</span>
    <div class="s-grid" style="grid-template-columns:140px repeat(3,minmax(0,1fr))"><span></span>${SERAS.map(x=>`<button class="s-col ${x.k===e.k?"on":""}" data-sera="${x.k}">${x.name}</button>`).join("")}
    ${order.map(g=>`<span class="s-gname">${g}</span>${SERAS.map(x=>{ const w=D.q5.weights[x.k][g]; return `<span class="s-cell ${x.k===e.k?"on":""}" data-tip="${esc(`${g}, ${x.name}\n${pct(w[0])} of the model's weight\nrange ${pct(w[1])} to ${pct(w[2])}`)}"><i><em style="width:${w[0]/0.45*100}%"></em></i><span class="s-mono">${pct(w[0])}</span></span>`; }).join("")}`).join("")}</div>
    <div class="s-note"><p><span class="s-mono">How to read</span><span>Each column is the model trained on DApps launched in that era; each bar is a feature group's share of its weight. Click an era to switch the page to it.</span></p>
      <p><span class="s-mono">What changed</span><span>The strongest group moved from ${top("before").toLowerCase()} (${SERAS[0].name}) to ${top("after").toLowerCase()} (${SERAS[2].name}).</span></p></div></figure>`;
}
function vQIndex(){
  const e=sera(), order=["Size","Stickiness","Context","Movement","Concentration"];
  const cards=SQ.map((x,i)=>`<button class="s-card s-qcard" data-sq="${x.q}"><span class="s-qtop"><span class="s-mono">${x.q.toUpperCase()} · ${x.tag}</span>${kindTag(x.q)}</span><h3>${x.ask}</h3></button>`).join("");
  return `<main class="study s-wrap"><section class="s-hero s-hero2">
      <h1>Plain questions.<br>Research <em class="o-word">answers</em>.</h1>
      <p>Six questions people actually ask, each answered by one part of our study. Switch the era and every answer is recomputed for that market.</p></section>
    <div class="s-sec"><h2>Pick a timeline</h2></div>
    <div class="s-time-in">${eraTimeline()}</div>
    <div class="s-sec"><h2>Pick a question</h2></div>
    <div class="s-cards s-qcards3">${cards}</div>
</main>`;
}

/* the trail: on the right of every scenario and question page. Pages already read show their question and
   what you found there (with the filters you left them on); the current page is marked; the rest wait in order. */
/* what the card is about right now: the choices that every sentence below depends on */
/* the three layers of a walk (Market › Category › DApp) and which one you are in */
function walkLayers(){ const d=me(), lay=S.scen==="s2"?(S.idx<=1?1:2):3, nm=S.scen==="s2"?(S.leader&&S.idx>=2?((leadOf(era(),S.cat)||{top:[]}).top.find(t=>t[0]===S.leader)||[])[1]:null):(d?d.name:null);
  return {lay, layers:[["Market",S.scen==="s2"&&S.idx<1?"–":PERIOD[era()]],["Category",S.scen==="s2"&&S.idx<1?"–":(S.scen==="s1"&&d?d.cat:S.cat)],["DApp",nm?esc(nm):"–"]]}; }
function trail(){
  if(S.view==="book"){
    const P=pages(), d=me(), head=S.scen==="s1"?(d?esc(d.name):"Your DApp"):"The market";
    const {lay,layers}=walkLayers();
    const lbar=`<ol class="w-layers">${layers.map(([k,v],i)=>`<li class="${i+1===lay?"on":i+1<lay?"done":""}"><span class="s-mono">${i+1} · ${k}</span><b>${v}</b></li>`).join("")}</ol>`;
    return `<aside class="s-trail s-livecard">${lbar}<span class="s-mono">Your path</span><ol>${P.map((pg,i)=>{ const st=i<S.idx?"done":i===S.idx?"cur":"next", v=(S.path||{})[pg];
      return `<li class="${st}"><button ${i===S.idx?"disabled":`data-jump="${i}"`}><span class="s-mono">${i+1} · ${QNAME[pg]}</span>${st!=="next"&&v?`<b>${v[1]}</b>`:`<b class="w-q">${ASK[pg]}</b>`}${st==="cur"?`<p class="here">You are here</p>`:""}</button></li>`; }).join("")}</ol>
      </aside>`;
  }
  const e=sera();
  return `<aside class="s-trail"><span class="s-mono">All six questions</span><ol>${SQ.map((x,i)=>{ const on=x.q===S.sq;
    const rd=!on&&(S.qread||[]).includes(x.q);
    return `<li class="${on?"cur":rd?"done read":"unread"}"><button ${on?"disabled":`data-sq="${x.q}"`}><span class="s-mono">${i+1} · ${x.tag}${rd?` <em class="s-read">✓ Read</em>`:""}</span>${on?`<b class="cur-ask">${x.ask}</b>`:`<b>${x.ask}</b>`}${on?`<p class="here">You are here</p>`:rd?`<p>${studyQ(x.q,e).brief}</p>`:""}</button></li>`; }).join("")}</ol></aside>`;
}
function vQPage(){
  if(!SQ.some(x=>x.q===S.sq)) S.sq='q1';
  S.qread=S.qread||[]; if(!S.qread.includes(S.sq)) S.qread.push(S.sq);
  const e=sera(), i=SQ.findIndex(x=>x.q===S.sq), x=SQ[i], a=studyQ(x.q,e), prev=SQ[(i+5)%6], next=SQ[(i+1)%6];
  return `<main class="study s-wrap s-withtrail"><div class="s-col1"><div class="s-crumb"><button class="s-back-m" data-go="qindex" aria-label="All questions">← All</button><span class="s-mono">${x.q.toUpperCase()}<span class="s-of"> of 6</span> <em>${x.tag}</em></span>${kindTag(x.q)}</div>
    <h1 class="s-qtitle">${x.ask}</h1>
    <div class="s-crow"><blockquote class="s-concl you-k"><span class="s-mono">Conclusion</span><p>${a.answer}</p></blockquote></div>
    <div class="s-eras s-eras-m s-eras-under" role="group" aria-label="Era">${SERAS.map(s=>`<button class="${s.k===e.k?"on":""}" data-sera="${s.k}" aria-pressed="${s.k===e.k}">${s.name}</button>`).join("")}</div>
    <figure class="s-fig">${a.fig}<div class="s-note"><p><span class="s-mono">How to read</span>${a.legend}</p>${x.q==="q2"||x.q==="q4"?`<p><span class="s-mono">Success</span><span>Still averaging 1,000+ wallets in months 10–12 and keeping a quarter of the early peak. <button class="s-link" data-go="method">Method ›</button></span></p>`:""}<p><span class="s-mono">Source</span>${x.q.toUpperCase()} ${x.tag} · n = ${comma(a.n||0)} ${a.unit}.${a.thin?` <b>Small sample: read with care.</b>`:""}</p></div></figure>
    ${x.q==="q2"?eraTable(e):""}
    <nav class="s-pn">${i>0?`<button data-sq="${prev.q}"><span class="s-mono">Previous</span><span>← ${prev.q.toUpperCase()} · ${prev.tag}</span></button>`:"<span></span>"}
      ${i<SQ.length-1?`<button data-sq="${next.q}"><span class="s-mono">Next</span><span>${next.q.toUpperCase()} · ${next.tag} →</span></button>`:`<button data-go="qindex"><span class="s-mono">Done</span><span>All questions →</span></button>`}</nav>
</div>${trail()}</main>`;
}
