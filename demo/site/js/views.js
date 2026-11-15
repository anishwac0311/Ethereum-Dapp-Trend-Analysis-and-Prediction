/* ---------- other views ---------- */
function vHome(){
  const door=(s,title,desc)=>{ const qs=[...new Set(BOOKS[s].pages.map(qOf))];
    return `<button class="s-card" data-start="${s}" aria-label="Open: ${title}"><span class="s-mono">Scenario ${s==="s1"?"1 · Developers and DApp teams":"2 · Newcomers and the curious"}</span><span class="s-arrow">↗</span>
      <h3>${title}</h3><p>${desc}</p></button>`; };
  const facts=[[comma(D.meta.n_dapps),`Ethereum DApps, ${D.meta.panel_start.slice(0,4)} – ${D.meta.panel_end.slice(0,4)}`],["3 months","of on-chain activity is all we look at"],[`1 in ${Math.round(1/successRate())}`,"DApps still count as a success a year later"]];
  return `<main class="study s-wrap"><section class="s-hero s-hero-eth"><svg class="eth-ghost" viewBox="0 0 200 320" aria-hidden="true"><g fill="none" stroke="#1A1A1A" stroke-width="1" stroke-linejoin="round"><path d="M100 4 L192 160 L100 214 L8 160 Z"/><path d="M100 4 V214 M8 160 L100 112 L192 160"/><path d="M8 186 L100 316 L192 186 L100 240 Z"/><path d="M100 240 V316"/></g></svg><div>
      <h1>What do you want<br>to know <em class="o-word">today</em>?</h1>
      <p>We answer one question at a time, using what ${D.meta.n_dapps} Ethereum DApps did in their first months on chain.</p></div>
      <div class="s-wcard"><div class="s-wcard-h"><span>At a glance</span></div>
        ${facts.map(f=>`<div class="s-fact"><b>${f[0]}</b><span>${f[1]}</span></div>`).join("")}
</div></section>
    <div class="s-sec"><h2>The whole market, <span class="nowrap">${D.meta.panel_start.slice(0,4)} – ${D.meta.panel_end.slice(0,4)}</span></h2><span class="h-tog" role="tablist" aria-label="Measure">${Object.entries(HM).map(([k,[l]])=>`<button class="${(HM[S.hm]?S.hm:"wallets")===k?"on":""}" data-hm="${k}" aria-pressed="${(HM[S.hm]?S.hm:"wallets")===k}">${l}</button>`).join("")}</span>${marketStory()}</div>
    ${marketSwipe()}
    <div class="s-sec"><h2>Read the ecosystem in three layers</h2><span class="s-mono">Market › Category › DApp</span></div>
    <div class="w-dig">
      ${[["Market","Which era? Which category is hot, which is fading?","s2","Start with the market"],["Category","Who leads it? What do the leaders have in common?",null,null],["DApp","What shape is it? Who did it look like? Did it make it?","s1","Start with one DApp"]].map(([k,t,sc,lab],i)=>`<div class="w-lv"><b>${k}</b><p>${t}</p>${sc?`<button class="w-go" data-start="${sc}">${lab} →</button>`:""}</div>`).join("")}
    </div>
    <div class="s-sec"><h2>Today at the booth</h2></div>
    <div class="tb">
      <div class="tb-p"><div class="tb-hrow"><span class="s-mono tb-h">Saved cards</span><button class="fold-more tb-play" data-go="wall"><span>See all of today</span><i>›</i></button></div>${wallTank("tank")}</div>
      <div class="tb-p"><div class="tb-hrow"><span class="s-mono tb-h">Top scores today</span><button class="fold-more tb-play" data-go="game"><span>Play the game</span><i>›</i></button></div>${podium()}</div>
    </div>
    <div class="s-sec"><h2>More ways in</h2></div>
    <div class="h-more">
      <div class="h-way h-way-q"><svg class="h-ico" viewBox="0 0 32 32" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M10 8h16M10 13h16M10 18h16M10 23h12"/></g><g fill="currentColor"><circle cx="5.5" cy="8" r="1.4"/><circle cx="5.5" cy="13" r="1.4"/><circle cx="5.5" cy="18" r="1.4"/><circle cx="5.5" cy="23" r="1.4"/></g></svg><b>The six questions</b><p>One question at a time, each answered for the era you pick.</p><button class="h-arrow" data-go="qindex" aria-label="Open The six questions">→</button></div>
      <div class="h-way"><svg class="h-ico" viewBox="0 0 32 32" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><rect x="3" y="6" width="11" height="20" rx="2"/><rect x="18" y="6" width="11" height="20" rx="2"/><path d="M6 11.5h5M6 16h3M6 20.5h4.5M21 11.5h3M21 16h5M21 20.5h2.5"/></g></svg><b>Compare</b><p>Line up to three DApps side by side, question by question.</p><button class="h-arrow" data-go="compare" aria-label="Open Compare">→</button></div>
      <div class="h-way"><svg class="h-ico" viewBox="0 0 32 32" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M16 4v6M16 22v6M4 16h6M22 16h6"/><circle cx="16" cy="16" r="3.2"/></g><g fill="currentColor"><circle cx="8" cy="8" r="1.6"/><circle cx="25" cy="9" r="1.6"/><circle cx="9" cy="25" r="1.6"/><circle cx="24" cy="24" r="1.6"/></g></svg><b>Neighbours</b><p>Place your own numbers on the map and see which DApps looked like yours.</p><button class="h-arrow" data-go="pick" data-tab="enter" data-start-diag="1" aria-label="Open Neighbours">→</button></div>
      <div class="h-way"><svg class="h-ico" viewBox="0 0 32 32" aria-hidden="true"><g fill="currentColor"><circle cx="7" cy="22" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="17" cy="24" r="1.6"/><circle cx="26" cy="20" r="1.6"/><circle cx="8" cy="7" r="1.6"/></g><circle cx="22" cy="10" r="2.2" fill="#CF4500"/><circle cx="22" cy="10" r="5.5" fill="none" stroke="#CF4500" stroke-width="1.6"/></svg><b>Game</b><p>Two numbers per dot, three levels: can you spot the DApps that lasted?</p><button class="h-arrow" data-go="game" aria-label="Open Game">→</button></div>
    </div>
    <div class="srt-dots h-moredots" aria-label="More ways in">${[0,1,2,3].map(i=>`<button class="${i?"":"on"}" data-act="hmdot" data-i="${i}" aria-label="Card ${i+1}"></button>`).join("")}</div>
</main>`;
}
/* Home: total monthly active wallets across every DApp, with the Terra and Dencun breaks marked */
const HM={wallets:["Wallets","active wallets"],tx:["Transactions","transactions"],gas:["Gas","gas used"]};
/* phones: one slide per measure (its own big number, line and era bar), swiped with dots under them, instead of a toggle */
function marketSwipe(){ const ks=Object.keys(HM);
  /* the era breaks are named on the chart itself ("Terra", "Dencun"); the eras and their dates are in "What happened ›" */
  const slides=ks.map(k=>marketStrip(k,true));
  return `<div class="srt h-swipe" aria-label="The whole market">${slides.map((h,i)=>`<div class="srt-s h-slide" aria-label="${HM[ks[i]][0]}">${h}</div>`).join("")}</div>
    <div class="srt-dots h-dots" role="tablist" aria-label="Measures">${ks.map((k,i)=>`<button class="${i?"":"on"}" data-act="hdot" data-i="${i}" role="tab" aria-label="${HM[k][0]}"></button>`).join("")}</div>`; }
function marketStory(){
  /* each era as name, then its dates on their own line, then what happened */
  const era=s=>{ const m=String(s).match(/^(.*?) \((.*?)\): (.*)$/); return m?`<div class="i-item"><b class="i-name">${m[1]}</b><span class="s-mono">${m[2]}</span><p>${m[3].charAt(0).toUpperCase()+m[3].slice(1)}</p></div>`:`<p>${s}</p>`; };
  return `<button class="fold-ic h-more2" data-act="fold" data-title="What happened in each era" aria-label="What happened in each era"><span>What happened</span><i>›</i></button><div class="h-erainfo" hidden>${era(ERA_NOTE.before)}${era(ERA_NOTE.between)}${era(ERA_NOTE.after)}<div class="i-item i-aside"><b class="i-name">The Merge</b><span class="s-mono">Sep 2022</span><p>Ethereum moved to proof of stake. Shown for context only; it is not one of our era breaks.</p></div></div>`; }
function marketStrip(k0,slide){
  const k=k0||(HM[S.hm]?S.hm:"wallets"), M=D.mkt.months, tot=D.mkt[k].map(v=>v||0), W=1200, H=150, T=22, B=24, mx=Math.max(...tot,1);
  const x=i=>i/(M.length-1)*W, y=v=>T+(1-v/mx)*(H-T-B), line=tot.map((v,i)=>`${i?"L":"M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  const cut=k=>{ const i=M.indexOf(D.meta[k]); return i<0?null:x(i); }, tx=cut("terra"), dx=cut("dencun");
  const era=(a,b,t)=>`<text x="${((a+b)/2).toFixed(0)}" y="12" text-anchor="middle" class="h-era">${t}</text>`;
  const years=[...new Set(M.map(m=>m.slice(0,4)))].map(yr=>{ const i=M.indexOf(yr+"-01"); return i<0?"":`<text x="${x(i).toFixed(0)}" y="${H-6}" class="h-yr">${yr}</text>`; }).join("");
  const hov=M.map((m,i)=>`<rect x="${(x(i)-W/M.length/2).toFixed(1)}" y="0" width="${(W/M.length).toFixed(1)}" height="${H}" fill="transparent" data-tip="${monthLabel(m)}
${fmtN(tot[i])} ${HM[k][1]}"/>`).join("");
  /* phones: the latest month as one big number, set against the peak, for whichever measure is on */
  const big=n=>n>=1e12?(n/1e12).toFixed(1)+"T":fmtN(n), last=tot[tot.length-1], pi=tot.indexOf(mx), atPeak=pi===tot.length-1;
  /* the measure is named in the same serif beside the big number ("11M transactions"); the month and the change sit on one line under it */
  const kpi=`<div class="h-kpi"><div class="h-kline"><b>${big(last)}</b><strong class="h-kunit">${HM[k][1]}</strong></div><em>${monthLabel(M[M.length-1])} · ${atPeak?"the highest month yet":`${sgn(last/mx-1)} from the ${big(mx)} peak in ${monthLabel(M[pi])}`}</em></div>`;
  const story=slide?"":marketStory();
  return `${kpi}<figure class="h-mkt"><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="Monthly ${HM[k][1]} across all DApps, ${monthLabel(M[0])} to ${monthLabel(M[M.length-1])}">
    <path d="${line} L${W} ${H-B} L0 ${H-B}Z" fill="#ECE7E0"/>
    ${(()=>{ const mi=M.indexOf("2022-09"); if(mi<0) return ""; const mx2=x(mi); return `<line x1="${mx2}" x2="${mx2}" y1="30" y2="${H-B}" class="h-merge" vector-effect="non-scaling-stroke"/><text x="${mx2+6}" y="${H-B-6}" class="h-mlab" data-tip="The Merge, September 2022: Ethereum moved from proof of work to proof of stake. Shown for context; it is not one of our era breaks.">The Merge</text>`; })()}
    ${tx!=null?`<line x1="${tx}" x2="${tx}" y1="18" y2="${H-B}" class="h-cut" vector-effect="non-scaling-stroke"/>`:""}${dx!=null?`<line x1="${dx}" x2="${dx}" y1="18" y2="${H-B}" class="h-cut" vector-effect="non-scaling-stroke"/>`:""}
    <path d="${line}" fill="none" stroke="#1A1A1A" stroke-width="1.6" vector-effect="non-scaling-stroke"/>
    ${tx!=null&&dx!=null?era(0,tx,"Before Terra")+era(tx,dx,"Terra → Dencun")+era(dx,W,"After Dencun"):""}${years}${hov}</svg>
    ${(()=>{ /* the peak only: a solid orange dot centred on the line's highest point, with "peak" beside it (on its left near an era name or the right edge); at the very edge half the dot sits in the 16px page gutter, so it never reaches the next slide */
      const px=x(pi)/W*100, side=(px>85||[tx,dx].some(c=>c!=null&&x(pi)>=c&&x(pi)-c<W*.1))?" left":"", pos=`left:${px.toFixed(2)}%;top:${(y(tot[pi])/H*100).toFixed(2)}%`;
      return `<span class="h-peak" style="${pos}" title="Peak: ${big(mx)} in ${monthLabel(M[pi])}"></span><span class="h-peaklab${side}" style="${pos}">peak</span>`; })()}
    ${tx!=null&&dx!=null?`<span class="h-cutlab" style="left:${(tx/W*100).toFixed(2)}%">Terra</span><span class="h-cutlab" style="left:${(dx/W*100).toFixed(2)}%">Dencun</span>`:""}</figure>${story}`;
}
const successRate = () => D.q4.n.success/(D.q4.n.success+D.q4.n.other);
const GROUPS = [
  ["Size",7,"Average, peak and last-month wallets; transactions, gas and fees (log scale)","How big it is"],
  ["Movement",4,"Growth slope, how far below the peak, month-to-month swings, months since the peak","Which way it is heading"],
  ["Stickiness",7,"Returning and new wallets, transactions per wallet, gas per transaction, apps used together","Whether users come back"],
  ["Concentration",2,"Share held by the top 10 wallets and by heavy wallets","How much rests on a few wallets"],
  ["Context",7,"Category and ecosystem share, market growth at launch, new version of an app, has a token, launch year","The market around it at launch"],
  ["Off-chain",6,"Audit, open source, contract verified (today's snapshot); governance proposals counted up to month k","Audits, open code and governance"],
];
const fmtFeat=(v,k)=>{ if(v==null) return "–";
  if(k==="log"||k==="big") return fmtN(v);
  if(k==="logf") return v<1 ? v.toFixed(2) : fmtN(v);
  if(k==="pct"||k==="yes") return v>0 && v<0.001 ? "<0.1%" : pct(v, v<0.1 && v>0 ? 1 : 0);
  if(Number.isInteger(v)) return String(v);
  if(k==="spct") return sgn(v);
  if(k==="year") return String(Math.round(v));
  if(k==="avg") return v.toFixed(1);
  return Math.abs(v)<10 ? v.toFixed(2) : fmtN(v); };
/* DragonQuest: a made-up game, drawn to show how the success rule is read */
function dragonFig(){
  const DQ=[5000,4200,3000,2100,1500,1000,700,450,320,230,200,180], PASS=[2200,2600,2900,2700,2500,2400,2300,2200,2100,2000,1950,1900];
  /* phones: a 560-wide canvas so the labels stay readable (see PHONE) */
  const ph=PHONE(), W=ph?560:980,H=ph?460:400,m=ph?{l:50,r:150,t:34,b:76}:{l:60,r:170,t:30,b:50}, iw=W-m.l-m.r, ih=H-m.t-m.b, X=i=>m.l+(i-1)/11*iw, Y=v=>m.t+ih-v/5500*ih, NR=ph?15:11, NF=ph?15:12;
  const line=(a,c,w,d)=>`<polyline points="${a.map((v,i)=>`${X(i+1)},${Y(v)}`).join(" ")}" fill="none" stroke="${c}" stroke-width="${w}" ${d?`stroke-dasharray="${d}"`:""} stroke-linejoin="round" stroke-linecap="round"/>`;
  const num=(x,y,n)=>`<circle cx="${x}" cy="${y}" r="${NR}" fill="#1A1A1A"/><text x="${x}" y="${y+NF/3}" text-anchor="middle" style="font:600 ${NF}px 'JetBrains Mono',monospace;fill:#F5F3EE">${n}</text>`;
  let g=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="DragonQuest's monthly wallets against the success rule">`;
  [0,1000,2000,3000,4000,5000].forEach(t=>{ g+=`<line x1="${m.l}" x2="${m.l+iw}" y1="${Y(t)}" y2="${Y(t)}" stroke="#E2DDD4"/><text class="ax" x="${m.l-10}" y="${Y(t)+4}" text-anchor="end">${t?fmtN(t):0}</text>`; });
  for(let i=1;i<=12;i++) if(!ph||i%2===0) g+=`<text class="ax" x="${X(i)}" y="${m.t+ih+(ph?24:20)}" text-anchor="middle">M${i}</text>`;
  (ph?["months after launch","monthly active wallets"]:["months after launch · monthly active wallets"]).forEach((l,k)=>{ g+=`<text class="ax" x="${m.l+iw}" y="${m.t+ih+(ph?48+k*21:42)}" text-anchor="end">${l}</text>`; });
  /* 2: the window we judge */
  g+=`<g class="dq-p s1 s4"><rect x="${X(9.5)}" y="${m.t}" width="${X(12)+14-X(9.5)}" height="${ih}" fill="#E2DDD4" opacity=".55"/>${num(X(11),m.t+18,1)}</g>`;
  /* 3: the two bars */
  g+=`<g class="dq-p s2 s4"><line x1="${m.l}" x2="${m.l+iw+14}" y1="${Y(1000)}" y2="${Y(1000)}" stroke="#1A1A1A" stroke-width="1.5"/><text class="axl" x="${m.l+iw+22}" y="${Y(1000)+4}" fill="#1A1A1A">1,000 wallets</text>${num(X(8),Y(1000),2)}</g>`;
  g+=`<g class="dq-p s3 s4">`;
  g+=`<line x1="${m.l}" x2="${m.l+iw+14}" y1="${Y(1250)}" y2="${Y(1250)}" stroke="#1A1A1A" stroke-width="1.2" stroke-dasharray="5 4"/><text class="axl" x="${m.l+iw+22}" y="${Y(1250)-6}" fill="#1A1A1A">¼ of the peak</text>`;
  g+=`</g>`;
  /* lines */
  g+=`<g class="dq-p s4">`+line(PASS,"#A39E95",2,"6 5")+`<text class="axl" x="${m.l+iw+22}" y="${Y(1900)+4}" fill="#6F6B64">${ph?"Passing DApp":"A DApp that passes"}</text></g>`;
  g+=`<g class="dq-p s1 s2 s3 s4">`+line(DQ,"#9C4A26",3)+`<text class="axl" x="${m.l+iw+22}" y="${Y(180)+4}" fill="#9C4A26">DragonQuest</text></g>`;
  /* 1: the early peak */
  g+=`<g class="dq-p s3"><circle cx="${X(1)}" cy="${Y(5000)}" r="5" fill="#9C4A26"/>${num(X(1)+26,Y(5000)-4,3)}</g>`;
  g+=`<g class="dq-p s1 s2 s4">`; [9,10,11].forEach(i=>{ g+=`<circle cx="${X(i+1)}" cy="${Y(DQ[i])}" r="4" fill="#9C4A26"/>`; }); g+=`</g>`;
  return g+`</svg>`;
}
/* Method › success example: a four-step walkthrough card on the chart instead of three numbered notes */
const DQT=[["Twelve months after launch","We judge only months 10–12, the end of the first year. How a DApp started does not count."],
  ["At least 1,000 wallets","In those three months it must average at least 1,000 wallets a month."],
  ["A quarter of its early peak","And it must keep at least a quarter of its early peak. DragonQuest peaked at 5,000, so its bar is 1,250."],
  ["DragonQuest: <em class=\"k\">not a success</em>","It averages about 200 wallets a month in months 10–12, below both bars. A strong start is not enough."],
  ["The grey DApp: <em class=\"k\">a success</em>","It averages about 1,950 a month in months 10–12, above both bars, so it still counts a year later."]];
function dqTour(){ const n=S.dqt===undefined?1:S.dqt;
  /* once the walkthrough is closed, the verdict stays on the page */
  if(!n) return `<button class="dq-replay" data-dqt="1" aria-label="Walk me through it again" title="Walk me through it again"><svg viewBox="0 0 24 24" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 4 21 10 15 10"/><path d="M19.5 15a8 8 0 1 1-1.9-8.3L21 10"/></g></svg></button>`;
  const [t,x]=DQT[n-1];
  return `<div class="tour" role="dialog" aria-label="Walkthrough"><div class="tour-h"><span class="s-mono">Walkthrough · ${n} / ${DQT.length}</span><button class="tour-x" data-dqt="0">End</button></div>
    <b>${t}</b><p>${x}</p><div class="tour-bar">${DQT.map((_,i)=>`<i class="${i<n?"on":""}"></i>`).join("")}</div>
    <div class="tour-btns"><button class="tour-back" data-dqt="${n-1}" ${n===1?"disabled":""}>Back</button><button class="tour-next" data-dqt="${n<DQT.length?n+1:0}">${n<DQT.length?"Next":"Done"}</button></div></div>`; }
/* small line icons (same 32px grid and stroke as Home's "More ways in") */
const ICO={
  success:`<svg class="h-ico" viewBox="0 0 32 32" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19h24" stroke-dasharray="2 3"/><path d="M5 26 C 11 24, 13 12, 19 11 S 26 8, 28 6"/></g><circle cx="28" cy="6" r="2.2" fill="#CF4500"/></svg>`,
  signals:`<svg class="h-ico" viewBox="0 0 32 32" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="13.5" cy="13.5" r="8"/><path d="M19.5 19.5 L27 27"/><path d="M9.5 15.5v-2M13.5 15.5v-5M17.5 15.5v-3.5"/></g></svg>`,
  data:`<svg class="h-ico" viewBox="0 0 32 32" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"><path d="M4 6h24l-9 11v8l-6 3V17Z"/></g></svg>`,
  list:`<svg class="h-ico" viewBox="0 0 32 32" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M11 9h16M11 16h16M11 23h12"/></g><g fill="currentColor"><circle cx="6" cy="9" r="1.6"/><circle cx="6" cy="16" r="1.6"/><circle cx="6" cy="23" r="1.6"/></g></svg>`,
  chain:`<svg class="h-ico" viewBox="0 0 32 32" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><rect x="3" y="12" width="8" height="8" rx="1.5"/><rect x="21" y="12" width="8" height="8" rx="1.5"/><path d="M11 16h3M18 16h3"/></g><rect x="14" y="13" width="4" height="6" rx="1" fill="currentColor"/></svg>`};
function vMethod(){
  const NB=(()=>{ const ok=(m,v)=>v!=null&&isFinite(v)&&(!MET[m].log||v>0), a=Object.values(D.snap).filter(d=>d.s!=null&&ok("wallets",MET.wallets.get(d))&&ok("returning",MET.returning.get(d))); return {n:a.length,s:a.filter(d=>d.s).length}; })();
  const M=D.method, ORDER=["Size","Movement","Stickiness","Concentration","Context","Off-chain"];
  const cats=Object.entries(M.by_cat).sort((a,b)=>b[1]-a[1]), cmax=cats[0][1];
  const catBars=cats.map(([c,n])=>`<div class="hb"><span>${c}</span><i><b style="width:${n/cmax*100}%"></b></i><em>${n}</em></div>`).join("");
  const yrs=Object.entries(M.by_year), ymax=Math.max(...yrs.map(y=>y[1]));
  let ysvg=`<svg viewBox="0 0 320 170" role="img" aria-label="DApps by launch year">`;
  yrs.forEach(([y,n],i)=>{ const h=n/ymax*104, x=10+i*51; /* 104 leaves room above the tallest bar for its number */ ysvg+=`<rect x="${x}" y="${130-h}" width="38" height="${h}" rx="0" fill="${C.q1}"/><text class="ax" x="${x+19}" y="${124-h}" text-anchor="middle">${n}</text><text class="ax" x="${x+19}" y="150" text-anchor="middle">${y}</text>`; });
  ysvg+=`</svg>`;
  const hmax=Math.max(...M.peak_hist), bw=300/M.peak_hist.length;
  let hsvg=`<svg viewBox="0 0 320 170" role="img" aria-label="Distribution of peak monthly wallets">`;
  M.peak_hist.forEach((n,i)=>{ const h=n/hmax*120; hsvg+=`<rect x="${10+i*bw}" y="${130-h}" width="${bw-3}" height="${h}" rx="0" fill="${M.peak_edges[i]>=3?C.q1:"#D6D1C7"}"/>`; });
  [0,2,4,6].forEach(e=>{ const x=10+e/0.5*bw; hsvg+=`<text class="ax" x="${x}" y="150" text-anchor="middle">${fmtN(10**e)}</text>`; });
  hsvg+=`</svg>`;
  const big=M.peak_hist.reduce((a,n,i)=>a+(M.peak_edges[i]>=3?n:0),0);
  const fs=M.features;
  /* each signal as two thin bars, successful (rust) over others (grey), scaled within its own row; size measures on a log scale */
  const card=(g,bare)=>{ const rows=fs.filter(f=>f.group===g);
    const bar=f=>{ if(f.kind==="year") return `<div class="sg-yr"><span class="s">${fmtFeat(f.success,f.kind)}</span><span>${fmtFeat(f.other,f.kind)}</span></div>`;
      const t=v=>/^(log|logf|big)$/.test(f.kind)?Math.log10(1+Math.max(0,v)):Math.max(0,v), a=t(f.success), b=t(f.other), m=Math.max(a,b)||1;
      return `<div class="sg-bars"><i class="s" style="width:${(a/m*100).toFixed(1)}%"></i><em class="s">${fmtFeat(f.success,f.kind)}</em><i style="width:${(b/m*100).toFixed(1)}%"></i><em>${fmtFeat(f.other,f.kind)}</em></div>`; };
    const note=(GROUPS.find(x=>x[0]===g)||[])[2]||"";
    return `<div class="group ${g==="Off-chain"?"hi":""}">${bare?"":`<h3>${g} <span>${rows.length}</span></h3><p class="sg-sum">${note}</p>`}
      <div class="sg">${rows.map(f=>`<div class="sg-row"><span class="sg-l">${f.label}</span>${bar(f)}</div>`).join("")}</div></div>`; };
  const TABS=[["success","What counts as success"],["signals","What we look at"],["data","The data behind it"]];
  const tab=TABS.some(t=>t[0]===S.mtab)?S.mtab:"success";
  const L=M.lifecycle||{};
  const funnel=[[M.n_registry,"in the DeFiLlama registry",""],
    [M.n_static,"with contracts we could map",`Together they own ${comma(M.n_contracts)} contracts. Shared plumbing (WETH, USDC), exchanges and chain entries are dropped.`],
    [M.n_active,"with any on-chain activity","Behind every market chart here."],
    [M.n_old,"old enough to judge",`Drops the ${M.n_2025} apps launched in 2025: under 12 months of follow-up.`],
    [M.n_study,"used for the model",`Also drops ${M.n_pre2020} apps launched before 2020, whose start we cannot see.`]];
  const fmax=funnel[0][0];
  const PANES={
    success:`      <div class="define"><p>Twelve months after launch, a DApp still averages <b>at least 1,000 wallets</b> in months 10–12, and keeps <b>at least a quarter</b> of its early peak.</p>
        <span class="tiny">A spike that fades does not count.</span></div>
      <div class="example">
        <figure class="dq dq-tour ${(S.dqt===undefined?1:S.dqt)?"f"+Math.min(4,S.dqt===undefined?1:S.dqt):""}"><h2 class="msec dq-h">The rule, step by step</h2>${dragonFig()}${dqTour()}</figure>
        </div>
      ${(()=>{ /* phones: one sort per slide with its key number; Learn more opens the detail in a sheet */
        const S3=[["Success",`${M.n_success}<small> of ${M.n_study}</small>`,"still a success a year on",`<p>Used on Q2 Survival, Q4 Speed and your card.</p><p><b>Why not “ever reached 10K wallets”?</b> For flash apps the peak happens inside the months we watch, so predicting it would be partly cheating.</p>`],
          ["Lifecycle label",`${L.sustained}<small> of ${comma(M.n_active)}</small>`,"sustained over their whole history",`<p>Of ${M.n_active}: never adopted ${L.never_adopted}, gradual decline ${L.gradual_decline}, flash ${L.flash}, sustained ${L.sustained}.</p>`],
          ["Shape",`${D.q2.counts.grower}<small> of ${D.q2.n}</small>`,"kept growing after the first peak",`<p>Widely used means it once hit 1,000 monthly wallets.</p><p>One-hit ${D.q2.counts.flash} (${pct(D.q2.counts.flash/D.q2.n)}), kept growing ${D.q2.counts.grower} (${pct(D.q2.counts.grower/D.q2.n)}). Used on Q2 Survival.</p>`]];
        /* one heading, one "Read more ›" for all three (K4); the sheet holds each label's details in turn */
        return `<div class="s-sec m-sec"><h2>Three labels, only one is success</h2><button class="srt-rm" data-act="fold" data-title="Three labels" aria-label="Read more about the three labels"><span>Read more</span><i>›</i></button><div hidden>${S3.map(([t,big,line,detail])=>`<div class="i-item"><b class="i-name">${t}</b>${detail}</div>`).join("")}</div></div>
        <div class="srt srt-def" aria-label="Three labels, only one is success">${S3.map(([t,big,line])=>`<div class="srt-s"><span class="s-mono">${t}</span><b>${big}</b><p>${line}</p></div>`).join("")}</div><div class="srt-dots" aria-hidden="true">${S3.map((x,i)=>`<i class="${i?"":"on"}"></i>`).join("")}</div>`; })()}
      <div class="groups three">
        <div class="group hi"><h3>Success</h3><p>The rule above.</p><p class="small">Used on Q2 Survival, Q4 Speed and your card.</p></div>
        <div class="group"><h3>Lifecycle label</h3><p>Sorts every app by its whole history.</p><p class="small">Of ${M.n_active}: never adopted ${L.never_adopted}, gradual decline ${L.gradual_decline}, flash ${L.flash}, sustained ${L.sustained}.</p></div>
        <div class="group"><h3>Shape</h3><p>Groups the ${D.q2.n} apps that ever hit 1,000 wallets by the shape of their curve.</p><p class="small">One-hit ${D.q2.counts.flash} (${pct(D.q2.counts.flash/D.q2.n)}), kept growing ${D.q2.counts.grower} (${pct(D.q2.counts.grower/D.q2.n)}). Used on Q2 Survival.</p></div>
      </div>
      <p class="rules"><b>Why not “ever reached 10K wallets”?</b> For flash apps the peak happens inside the months we watch, so predicting it would be partly cheating.</p>`,
    signals:`    <p class="tiny sg-key" style="margin:-6px 0 0"><span><i class="s"></i>Successful</span><span><i></i>Others</span>Each bar is the typical DApp in its group: the median for numbers, the share that said yes for yes/no signals, the average for proposal counts. All from the first three months.</p>
    ${(()=>{ /* phones: one group per slide (its name and a plain gist, GROUPS[i][3]); ⋯ opens its signals */
      const key=`<p class="tiny sg-key sg-key-s"><span><i class="s"></i>Successful</span><span><i></i>Others</span>Each bar is the typical DApp in its group: the median for numbers, the share that said yes for yes/no signals, the average for proposal counts. All from the first three months.</p>`;
      /* inside a group's sheet: its share of the model's weight in each era (the same numbers as Q2), when the model uses the group */
      const gWeight=g=>{ const W=D.q5.weights, es=["before","between","after"].filter(e=>W[e]&&W[e][g]); if(!es.length) return "";
        return `<div class="sg-w"><span class="s-mono">Share of the model's weight</span>${es.map(e=>`<div class="sg-wr"><span>${PERIOD[e]}</span><i><b style="width:${(W[e][g][0]/.35*100).toFixed(1)}%"></b></i><em>${pct(W[e][g][0])}</em></div>`).join("")}</div>`; };
      return `<div class="srt srt-sg" aria-label="What we look at">${ORDER.map((g,i)=>{ const n=fs.filter(f=>f.group===g).length, G=GROUPS.find(x=>x[0]===g)||[], note=G[2]||"", gist=G[3]||note;
        return `<div class="srt-s"><b><button class="term sg-term" data-act="isheet" aria-label="The ${g} signals">${g}</button></b><p>${gist}</p><div class="srt-d" hidden><h3>${g}</h3><span class="s-mono i-sub">${n} signal${n===1?"":"s"}</span><p>${note}</p>${gWeight(g)}${key}${card(g,true)}</div></div>`; }).join("")}</div><div class="srt-dots" aria-hidden="true">${ORDER.map((g,i)=>`<i class="${i?"":"on"}"></i>`).join("")}</div>`; })()}
    <div class="groups">${ORDER.map(card).join("")}</div>
    <div class="m-rules"><p class="rules"><b>Rules.</b> Only the first k months are used. TVL and peak metrics never are: they give the answer away. Off-chain flags are today's snapshot.</p></div>
    `,
    data:`      ${(()=>{ /* phones: the funnel steps and the three charts as paged rows */
        const dots=n=>`<div class="srt-dots" aria-hidden="true">${[...Array(n)].map((x,i)=>`<i class="${i?"":"on"}"></i>`).join("")}</div>`;
        const steps=funnel.map(([n,l,why],i)=>`<div class="srt-s${i===funnel.length-1?" srt-key":""}"><span class="s-mono">Step ${i+1}</span><b>${comma(n)}</b><p>${l}</p><div class="fbar-row"><div class="fbar-s"><i style="width:${Math.max(4,n/fmax*100).toFixed(1)}%"></i></div><span class="fpct" aria-label="${Math.round(n/fmax*100)}% of the registry">${Math.round(n/fmax*100)}%</span></div>${why?`<p class="srt-why">${why}</p>`:""}</div>`).join("");
        const charts=[["By category",`<div class="hbars">${catBars}</div>`,"DeFi alone is more than half of all apps."],["By launch year",ysvg,"Launches never stopped, bull or bear."],["Peak monthly wallets",hsvg,`Log-normal: most stay small; ${big} of ${M.n_active} ever pass 1K wallets (dark).`]]
          .map(([l,fig,cap],i)=>`<div class="srt-s srt-ch"><span class="s-mono">${l}</span><div class="mfig">${fig}</div><p class="srt-why">${cap}</p></div>`).join("");
        return `<div class="srt srt-fn" aria-label="How the data was narrowed">${steps}</div>${dots(funnel.length)}<div class="srt srt-chs" aria-label="The DApps we kept">${charts}</div>${dots(3)}`; })()}
      <ol class="funnel">${funnel.map(([n,l,why],i)=>`<li><div class="fbar"><i style="width:${Math.max(8,n/fmax*100)}%"></i></div><b>${comma(n)}</b><span class="fl">${l}</span><span class="fw">${why}</span></li>`).join("")}</ol>
      <div class="mcharts">
        <div class="mchart"><span class="lbl">By category</span><div class="mfig"><div class="hbars">${catBars}</div></div><p class="tiny">DeFi alone is more than half of all apps.</p></div>
        <div class="mchart"><span class="lbl">By launch year</span><div class="mfig">${ysvg}</div><p class="tiny">Launches never stopped, bull or bear.</p></div>
        <div class="mchart"><span class="lbl">Peak monthly wallets</span><div class="mfig">${hsvg}</div><p class="tiny">Log-normal: most stay small; ${big} of ${M.n_active} ever pass 1K wallets (dark).</p></div>
      </div>
      <div class="m-rules"><p class="rules"><b>Scope.</b> Ethereum mainnet only. An app counts only if we can tie contracts to it.</p>
      <p class="rules"><b>What we cannot see.</b> Who is behind a wallet, anything off-chain, and spending on other chains. A wallet is our stand-in for a user.</p>
      <p class="rules"><b>Neighbours and the game.</b> ${NB.n} DApps launched 2020–2024 with a known outcome; ${NB.s} were still a success a year later (${pct(NB.s/NB.n)}). Every value is from each DApp's third month. Neighbours are matched on the two measures shown only: this describes the past, not a forecast.</p></div>`};
  const n=TABS.findIndex(t=>t[0]===tab), next=TABS[n+1];
  return `<section class="sheet" style="max-width:1200px">
    <h1 style="margin-top:14px">How we <em class="o-word">measured</em> it</h1>
    <p class="s-lede">${{success:"What counts as a success, shown on one DApp, and how it differs from two other labels we use.",
      signals:"The 33 early signals we read in a DApp's first three months, in six groups.",
      data:`How ${comma(M.n_registry)} listed DApps became the ${M.n_study} we could judge.`}[tab]}</p>
    <div class="mcards" role="tablist">${[
      ["success", `${M.n_success}<small> of ${M.n_study}</small>`, "apps count as a success a year on", "What counts as success"],
      ["signals", `33`, "early signals, 27 of them on-chain", "What we look at"],
      ["data", `${comma(M.n_registry)}<small> → ${M.n_study}</small>`, "listed apps, narrowed to the ones we can judge", "The data behind it"],
    ].map(([k,num,sub,t])=>`<button class="mcard ${k===tab?"on":""}" role="tab" aria-selected="${k===tab}" data-mtab="${k}">${ICO[k]}<span class="mct">${t}</span><b>${num}</b><span class="mcs">${sub}</span><span class="mgo" aria-hidden="true">${k===tab?"↓":"→"}</span></button>`).join("")}</div>
    ${PANES[tab]}
    <nav class="q-bar m-tabbar" aria-label="Method sections">${[["success","Success",`${M.n_success} of ${M.n_study}`],["signals","Signals","33 signals"],["data","Data",`${comma(M.n_registry)} → ${M.n_study}`]].map(([k,l,n])=>`<button class="${k===tab?"on":""}" data-mtab="${k}"${k===tab?' aria-current="page"':""}><b>${l}</b>${k===tab?`<span>${n}</span>`:""}</button>`).join("")}</nav>
  </section>`;
}
/* roles: fill in the second value when they are settled */
const TEAM=[["Anishwar Chakraborty",""],["Austin Lee",""],["William Chen",""],["Ting-Yu Kao",""],["Ved Mistry",""],["Victor Wu",""]];
/* "Take it with you": a QR code to the live site, for visitors at the booth screen (desktop only; on a phone you are already there) */
const QR_SVG=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 29 29" class="qr-svg" role="img" aria-label="QR code for ethereum-dapp-trends.vercel.app"><path stroke="#1a1a1a" d="M0 0.5h7m2 0h2m2 0h2m2 0h1m4 0h7m-29 1h1m5 0h1m1 0h2m1 0h2m7 0h1m1 0h1m5 0h1m-29 1h1m1 0h3m1 0h1m1 0h1m5 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h3m1 0h1m-29 1h1m1 0h3m1 0h1m1 0h3m1 0h2m1 0h3m1 0h2m1 0h1m1 0h3m1 0h1m-29 1h1m1 0h3m1 0h1m3 0h3m1 0h1m4 0h1m2 0h1m1 0h3m1 0h1m-29 1h1m5 0h1m2 0h1m2 0h1m4 0h2m3 0h1m5 0h1m-29 1h7m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h7m-21 1h1m1 0h1m1 0h1m3 0h1m1 0h1m-19 1h1m5 0h1m1 0h3m2 0h2m2 0h1m2 0h3m2 0h3m-28 1h3m2 0h1m2 0h1m1 0h2m3 0h1m2 0h2m1 0h1m1 0h2m1 0h2m-27 1h3m1 0h2m1 0h5m2 0h2m4 0h1m1 0h2m-24 1h3m4 0h2m2 0h1m3 0h1m5 0h4m-26 1h1m3 0h13m2 0h1m2 0h2m4 0h1m-28 1h3m5 0h2m4 0h6m1 0h3m2 0h2m-29 1h2m3 0h2m2 0h3m3 0h3m2 0h1m3 0h3m-24 1h1m3 0h1m2 0h2m2 0h3m1 0h1m1 0h3m3 0h1m1 0h1m-28 1h3m2 0h3m1 0h1m4 0h1m1 0h1m7 0h2m-27 1h1m1 0h4m1 0h1m1 0h1m3 0h1m1 0h2m1 0h7m1 0h3m-29 1h2m1 0h1m1 0h4m2 0h2m2 0h3m1 0h2m1 0h4m2 0h1m-29 1h1m2 0h3m2 0h6m1 0h1m2 0h1m1 0h2m1 0h2m-25 1h1m1 0h2m1 0h2m4 0h1m2 0h4m2 0h5m1 0h3m-21 1h1m1 0h1m1 0h1m1 0h2m4 0h1m3 0h2m-26 1h7m8 0h6m1 0h1m1 0h3m-27 1h1m5 0h1m3 0h1m3 0h1m1 0h1m2 0h2m3 0h1m2 0h2m-29 1h1m1 0h3m1 0h1m2 0h1m2 0h5m1 0h8m2 0h1m-29 1h1m1 0h3m1 0h1m2 0h1m4 0h6m1 0h1m1 0h1m1 0h2m1 0h1m-29 1h1m1 0h3m1 0h1m4 0h3m1 0h1m1 0h1m1 0h9m-28 1h1m5 0h1m2 0h2m1 0h4m2 0h1m2 0h1m1 0h4m1 0h1m-29 1h7m1 0h1m4 0h1m1 0h3m5 0h2m1 0h1"/></svg>`;
const qrBlock=()=>`<section class="qr-take"><div class="qr-box">${QR_SVG}</div><div class="qr-txt"><h2>Take it with you</h2><p>Scan to open this site on your phone and keep reading.</p></div></section>`;
function vAbout(){
  const ini=n=>n.split(/\s+/).map(w=>w[0]).join("").slice(0,2).toUpperCase();
  return `<main class="study s-wrap ab">
    
    <section class="ab-hero"><div><h1 class="s-qtitle">About this <em class="o-word">project</em></h1>
      <p class="ab-lede s-lede">Thousands of DApps launch on Ethereum, and most fade within a year. We followed ${D.meta.n_dapps} of them month by month to see how categories rise and fall, who leads them, and whether a DApp's first three months on chain already show if it will last.</p></div>${qrBlock()}</section>
    <div class="s-sec"><h2>University</h2></div>
    <div class="ab-advisor"><b>University of California, Irvine</b></div>
    <div class="s-sec"><h2>Course</h2></div>
    <div class="ab-advisor"><b>DATA 296P / 297P</b><span>Capstone project</span></div>
    <div class="s-sec"><h2>Advisor</h2></div>
    <div class="ab-advisor"><b>Prof. Faisal Nawab</b></div>
    <div class="s-sec"><h2>Team · Group 9</h2></div>
    <ul class="ab-people">${TEAM.map(([n,r])=>`<li><b>${n}</b>${r?`<span class="ab-role">${r}</span>`:""}</li>`).join("")}</ul>
    <div class="s-sec"><h2>Data</h2><span class="ab-range">Ethereum mainnet · ${monthLabel(D.meta.panel_start)} – ${monthLabel(D.meta.panel_end)}</span></div>
    <div class="ab-srcs">
      <div class="ab-src2">${ICO.list}<span class="s-mono">Which DApps exist</span><b>DeFiLlama</b><p>The DApp list, with each one's category and launch date.</p></div>
      <div class="ab-src2">${ICO.chain}<span class="s-mono">What they did on chain</span><b>AWS Public Blockchain Data</b><p>Every month of wallets, transactions, gas and fees for each DApp's own contracts.</p></div>
      <div class="ab-src2 ab-go">${ICO.signals}<span class="s-mono">How we turned it into answers</span><b>Method</b><p>What counts as success, which signals we read, and how the data was narrowed.</p><button class="ab-arrow" data-go="method" aria-label="Open Method"></button></div>
    </div>
</main>`;
}
function vPick(){
  const all=Object.entries(D.dapps), q=S.query.trim().toLowerCase();
  const pc=S.pickCat||"featured";
  const counts=Object.fromEntries(CATS.map(c=>[c,all.filter(([s,d])=>d.cat===c).length]));
  const rows = q ? all.filter(([s,d])=>d.name.toLowerCase().includes(q)).slice(0,20)
    : pc==="featured" ? D.featured.map(s=>[s,D.dapps[s]])
    : all.filter(([s,d])=>d.cat===pc).sort((a,b)=>b[1].peak-a[1].peak).slice(0,12);
  const chips=[["featured","Featured",D.featured.length],...CATS.filter(c=>counts[c]).map(c=>[c,c,counts[c]])]
    .map(([k,l,n])=>`<button class="pchip ${k===pc&&!q?"on":""}" data-pickcat="${k}">${l}<em>${n}</em></button>`).join("");
  if(S.pickTab==="enter") return vMap("place");
  /* a slow river of real DApp names behind one big "Surprise me"; names are clickable text, not buttons */
  const byPeak=all.slice().sort((a,b)=>b[1].peak-a[1].peak), lanes=[0,1,2].map(l=>byPeak.filter((_,i)=>i%3===l).slice(0,28));
  const now=Date.now()/1000, DUR=[90,120,105];
  const lane=(r,l)=>{ const items=r.map(([k,d])=>`<button class="pk-name" data-dapp="${k}" tabindex="-1">${esc(d.name)}<em>${d.cat}</em></button>`).join("");
    return `<div class="pk-lane ${l%2?"rev":""}"><div class="pk-track" style="animation-duration:${DUR[l]}s;animation-delay:-${(now%DUR[l]).toFixed(1)}s">${items}${items}</div></div>`; };
  const hits=q?all.filter(([k,d])=>d.name.toLowerCase().includes(q)).sort((a,b)=>b[1].peak-a[1].peak).slice(0,8):[];
  return `<main class="study s-wrap pk">
    <h1 class="s-qtitle">Pick a DApp that's already live.</h1>
    <p class="pk-lede s-lede">Choose one of ${all.length} widely used DApps and look inside it: its shape, its standing, its lookalikes and how it ended up.</p>
    <div class="pk-stage">
      <div class="pk-river">${lanes.map(lane).join("")}</div>
      <div class="pk-center">
        <span class="s-mono">${all.length} DApps on chain</span>
        <button class="pk-rand" data-act="pkrand"><span id="pk-roll">Surprise me</span> →</button>
        <div class="pk-search"><input class="search" id="q" placeholder="or search, e.g. Uniswap" value="${esc(S.query)}" aria-label="Search DApps" autocomplete="off">
          ${q?`<div class="pk-res">${hits.map(([k,d])=>`<button data-dapp="${k}"><span>${esc(d.name)}</span><em>${d.cat} · ${d.launch}</em></button>`).join("")||`<p class="tiny">No match among the ${all.length} DApps.</p>`}</div>`:""}</div>
        <span class="pk-hint">or click any name drifting by</span>
      </div>
    </div>
    <p class="pk-alt"><button data-tab="enter"><span>Not listed yet?</span> <b>Place your own numbers ›</b></button></p></main>`;
}

function sentence(q){
  const d=me(), cat = S.scen==="s1"&&d ? d.cat : S.cat;
  if(q==="q2"){ if(S.scen==="s1"&&d) return d.group?`${esc(d.name)} follows the ${d.group==="grower"?"kept-growing":"one-hit"} shape. ${pct(D.q2.counts.flash/D.q2.n)} of widely used DApps faded after an early peak.`:`Three months is too early to call your shape; ${pct(D.q2.counts.flash/D.q2.n)} of widely used DApps faded after an early peak.`;
    const b=D.q2.by_cat[cat], wt=D.q5.weights[era()], top=Object.keys(wt).sort((x,y)=>wt[y][0]-wt[x][0])[0];
    return `In ${cat}, ${b.flash} of ${b.flash+b.grower} widely used DApps were one-hit wonders; ${b.grower} kept growing. ${top} best tells them apart.`; }
  if(q==="q4"){ const s=D.q4.share_10k; let t=`By month 6, ${pct(s.success[6])} of successful DApps had 10K wallets, against ${pct(s.other[6])} of the rest.`;
    if(S.scen==="s1"&&d&&d.cum){ const c=d.cum.findIndex(v=>v!=null&&v>=1e4); t+= c>=0&&c<=12?` You crossed 10K in month ${c}.`:" You haven't crossed 10K yet."; } return t; }
  if(q==="q5"){ const e=era(), P=D.q5.periods[e], top=Object.entries(D.q5.weights[e]).sort((a,b)=>b[1][0]-a[1][0])[0];
    return `For DApps launched ${PERIOD_IN[e]}, the typical DApp kept ${pct(P.median[6])} of its first users at month 6${S.scen==="s1"&&d&&d.ret?`, against ${pct(d.ret[6])} for ${esc(d.name)}`:""}.`; }
  if(q==="q6") return "Around 10K wallets, growers keep their users while one-hit DApps spike on newcomers and fade.";
  if(q==="q3"){ const i=S.q3m??D.q3.months.length-1; return `In ${monthLabel(D.q3.months[i])}, the top 10 DApps held ${pct(D.q3.eco.top10_share[i])} of wallets${cat&&D.q3.cat_top10[cat][i]!=null?`; inside ${cat}, ${pct(D.q3.cat_top10[cat][i])}`:""}.`; }
  if(q==="q1"){ const f1=D.q1.months.findIndex((m,k)=>CATS.some(c=>D.q1.growth_12m[c][k]!=null)), i=Math.max(f1,S.q1m??D.q1.months.length-1), g=D.q1.growth_12m[cat][i]; return `In ${monthLabel(D.q1.months[i])}, ${cat} wallets changed ${sgn(g)} over the year.`; }
}
/* the card: the whole walk said as one sentence, plus the way into Layer 3 after a market walk */
function cardSentence(){ const P=pages(), says=S.says||{}, parts=P.map(k=>says[k]).filter(Boolean);
  if(!parts.length) return "";
  let head="", rest=parts;
  if(S.scen==="s2"&&says[P[0]]){ head=parts[0]+", "; rest=parts.slice(1); }
  const list=rest.length>1?rest.slice(0,-1).join(", ")+", and "+rest[rest.length-1]:rest[0]||"";
  const t=(list?head:head.replace(/, $/,""))+list; return t.charAt(0).toUpperCase()+t.slice(1)+"."; }
/* the walk's "block hash": a short fingerprint of this walk's choices (FNV-1a, 64-bit). Same choices, same hash. */
function cardHash(){ const key=[S.scen,era(),S.cat||"",S.dapp||"",S.leader||"",...pages().map(pg=>((S.path||{})[pg]||["",""])[1])].join("|");
  let h1=0x811c9dc5, h2=0x01000193^0x5bd1e995; for(let i=0;i<key.length;i++){ const c=key.charCodeAt(i); h1=Math.imul(h1^c,16777619)>>>0; h2=Math.imul(h2^c,2246822519)>>>0; }
  const hx=(h1.toString(16).padStart(8,"0")+h2.toString(16).padStart(8,"0")); return `0x${hx.slice(0,6)}…${hx.slice(-6)}`; }
/* the walk's card, set like a business card. DApp cards the visitor saves with the bookmark are kept in this browser for the wall. */
const WALL_KEY="dapp-wall";
function wallLoad(){ try{ return JSON.parse(localStorage.getItem(WALL_KEY)||"[]"); }catch(e){ return []; } }
/* only Layer 3 (one DApp) cards go on the wall, and only when the visitor saves them with the bookmark */
const DAPP_NAMES=new Set(Object.values(D.dapps).map(x=>x.name));
function wallToday(){ const d=new Date().toDateString(); return wallLoad().filter(c=>new Date(c.t).toDateString()===d&&(c.s?c.s==="s1":DAPP_NAMES.has(c.n))); }
function wallHas(h){ return wallToday().some(c=>c.h===h); }
function cardData(){ const d=me(), all=pages();
  /* market walks are named by the category they followed (Moment already gives the era), DApp walks by the DApp */
  const name=S.scen==="s1"?(d?d.name:"Your DApp"):(S.cat||"The market");
  const sub=S.scen==="s1"&&d?`${d.cat} · ${PERIOD[era()]}`:"";
  return {h:cardHash(), n:name, sub, line:cardSentence(), facts:all.map(pg=>[QNAME[pg],((S.path||{})[pg]||[])[1]||"–"]), t:Date.now(), s:S.scen}; }
/* two example cards from real walks, so the tank is never empty: one success, one not */
let WALL_EX=null;
function wallExamples(){ if(WALL_EX) return WALL_EX;
  const keys=["scen","dapp","era","custom","path","says","cat","leader"], keep=Object.fromEntries(keys.map(k=>[k,S[k]])); WALL_EX=[];
  ["Uniswap V3","Beanstalk"].forEach(nm=>{ const k=Object.keys(D.dapps).find(k=>D.dapps[k].name===nm); if(!k) return;
    Object.assign(S,{scen:"s1",dapp:k,custom:null,era:null,cat:null,leader:null,path:{},says:{}});
    try{ pages().forEach(pg=>{ const r=PAGES[pg](); if(r&&r.path) S.path[pg]=r.path; if(r&&r.say) S.says[pg]=r.say; }); WALL_EX.push({...cardData(),ex:true}); }catch(e){} });
  Object.assign(S,keep); return WALL_EX; }
function wallCards(){ const T=wallToday(), seen=new Set(T.map(c=>c.n)); return wallExamples().filter(c=>!seen.has(c.n)).concat(T); }
/* how many cards a tank shows at once (newest first), so a busy day never slows the page: Home 4 on phones / 6 on desktop, the booth page 8 / 12 */
function wallMax(){ return S.view==="wall"?(PHONE()?8:12):(PHONE()?4:6); }
function wallTank(id){ const all=wallCards(), max=wallMax(), W=all.length>max?all.slice(-max):all;
  return `<div class="tank" id="${id}">${W.map((c,i)=>`<button class="tk-card" data-wall="${all.length-W.length+i}" aria-label="${esc(c.n)} card">${bizCard(c,true)}</button>`).join("")}</div>`; }
function wallSave(){ const c=cardData(); if(c.s!=="s1"||!c.facts.some(f=>f[1]!=="–")) return;
  try{ const w=wallLoad().filter(x=>x.h!==c.h); w.push(c); localStorage.setItem(WALL_KEY,JSON.stringify(w.slice(-40))); }catch(e){} }
const ETH_MARK=`<svg class="bc-eth" viewBox="0 0 20 32" aria-hidden="true"><path d="M10 1 L19 16 L10 21.5 L1 16 Z M10 1 V21.5 M1 16 L10 11.5 L19 16 M1 18.5 L10 31 L19 18.5 L10 24 Z" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>`;
function bizCard(c,mini){
  if(mini) return `<div class="bcard bc-mini"><b class="bc-name">${esc(c.n)}</b><code>${c.h}</code></div>`;
  return `<div class="bcard">
    <div class="bc-top"><span class="s-mono">DApp research</span>${c.s==="s1"&&!c.ex&&c.facts.some(f=>f[1]!=="–")?(()=>{ const on=wallHas(c.h), pop=on&&S.justSaved===c.h;
      /* the Ethereum mark is the save button: an ink outline that nudges a few times with "Tap to save", then fills orange (you / now) with a small pop */
      return `<span class="bc-savewrap">${on?"":`<span class="bc-hint s-mono">Tap to save</span>`}<button class="bc-save${on?" on":""}${pop?" pop":""}" data-act="cardsave" aria-pressed="${on}" aria-label="${on?"Saved to today at the booth. Tap to remove":"Save to today at the booth"}"><svg viewBox="0 0 20 32" aria-hidden="true"><path d="M10 1 L19 16 L10 21.5 L1 16 Z M1 18.5 L10 31 L19 18.5 L10 24 Z" fill="${on?"#CF4500":"none"}" stroke="${on?"#CF4500":"#1A1A1A"}" stroke-width="1.3" stroke-linejoin="round"/><path d="M10 1 V21.5 M1 16 L10 11.5 L19 16" fill="none" stroke="${on?"#FBFAF7":"#1A1A1A"}" stroke-width="1.1" stroke-linejoin="round"/></svg></button></span>`; })():ETH_MARK}</div>
    <b class="bc-name">${esc(c.n)}</b>${c.sub||c.ex?`<span class="s-mono bc-sub">${esc(c.sub)}${c.ex?`${c.sub?" · ":""}Example walk`:""}</span>`:""}
    ${mini||c.facts.some(f=>f[1]!=="–")?"":`<p class="bc-line bc-empty">Walk at least one step to fill your card.</p>`}
    ${mini?"":`<dl class="bc-facts">${c.facts.map(([k,v])=>`<div class="${v==="–"?"":"on"}${v==="Success"?" ok":""}"><dt class="s-mono">${k}</dt><dd>${v}</dd></div>`).join("")}</dl>`}
    <div class="bc-foot"><code title="Made from your choices on this walk: the same choices always give the same hash">${c.h}</code></div></div>`; }
function vCard(){
  const deep=S.scen==="s2"?deepOf():null, c=cardData();
  const head = `${esc(c.n)}, <em class="o-word">dug down</em>`;
  return `<section class="sheet" style="max-width:980px">
    <h1 style="margin-top:14px">${head}</h1>
    <p class="s-lede bc-lede">${S.scen==="s1"?"Your walk on one card. Tap the Ethereum mark to save it to today's booth.":"Your walk through the market on one card."}</p>
    <div class="bc-stage">${bizCard(c)}</div>
    <div class="bc-act">${deep?`<button class="bc-deep" data-deeper="${deep}">Dig into ${esc(D.dapps[deep].name)} →</button>`:`<button class="bc-deep" data-go="pick" data-tab="pick" data-start-diag="1">Walk another DApp →</button>`}
      ${S.scen==="s1"&&wallHas(c.h)?`<p class="bc-saved">Saved to today's booth. <button class="s-link" data-go="wall">See it ›</button></p>`:""}</div></section>`;
}
/* the wall: today's cards drift slowly around a tank and bounce off its sides; tap one to read it */
function vWall(){ const W=wallToday();
  return `<main class="study s-wrap wall"><section class="s-hero s-hero2"><h1>Today at the <em class="o-word">booth</em></h1>
    <p>Cards and scores from this screen today. To add a card, walk a DApp to the end and tap its Ethereum mark.</p></section>
    <div class="wb"><div class="wb-p"><div class="s-sec"><h2>Saved cards</h2><button class="fold-more tk-link" data-start="s1"><span>Walk a DApp</span><i>›</i></button></div>
    ${wallTank("tank")}
    ${W.length?`<div class="tk-foot tk-foot-x"><button class="tk-clear" data-act="wallclear">Clear today</button></div>`:""}
    </div><div class="wb-p"><div class="s-sec"><h2>Top scores today</h2><button class="fold-more tk-link" data-go="game"><span>Play the game</span><i>›</i></button></div>
    ${topToday(10,true)}</div></div></main>`; }
let tankRAF=0;
function tankStart(){ cancelAnimationFrame(tankRAF); const tank=document.getElementById("tank"); if(!tank) return;
  const els=[...tank.querySelectorAll(".tk-card")]; if(!els.length) return;
  const TW=tank.clientWidth, TH=tank.clientHeight;
  const B=els.map((el,i)=>{ const w=el.offsetWidth, h=el.offsetHeight, a=Math.random()*Math.PI*2, sp=CALM()?0:(.18+Math.random()*.22);
    const C=Math.max(1,Math.min(els.length,Math.round(TW/(w*1.05)))), R=Math.ceil(els.length/C), cw=TW/C, rh=TH/R;
    return {el,w,h,x:Math.min(TW-w,Math.max(0,(i%C)*cw+(cw-w)/2+(Math.random()-.5)*10)),y:Math.min(TH-h,Math.max(0,Math.floor(i/C)*rh+(rh-h)/2+(Math.random()-.5)*10)),vx:Math.cos(a)*sp,vy:Math.sin(a)*sp,r:(Math.random()-.5)*8,vr:(Math.random()-.5)*.02}; });
  let vis=true; if("IntersectionObserver" in window){ const io=new IntersectionObserver(es=>{ vis=es[0].isIntersecting; }); io.observe(tank); }
  const step=()=>{ if(!document.body.contains(tank)) return;
    if(!vis||document.hidden){ tankRAF=requestAnimationFrame(step); return; }
    B.forEach(b=>{ b.x+=b.vx; b.y+=b.vy; b.r+=b.vr;
      if(b.x<0){b.x=0;b.vx=Math.abs(b.vx);} if(b.x>TW-b.w){b.x=TW-b.w;b.vx=-Math.abs(b.vx);}
      if(b.y<0){b.y=0;b.vy=Math.abs(b.vy);} if(b.y>TH-b.h){b.y=TH-b.h;b.vy=-Math.abs(b.vy);}
      if(Math.abs(b.r)>6) b.vr=-b.vr;
      b.el.style.transform=`translate(${b.x}px,${b.y}px) rotate(${b.r}deg)`; });
    if(!CALM()) tankRAF=requestAnimationFrame(step); };
  step(); }

/* decorative orbit lines behind everything (cream theme only): thin light-orange arcs, as in the reference */
function orbits(){
  return `<svg class="orbits" viewBox="0 0 1000 1000" preserveAspectRatio="xMaxYMin slice" aria-hidden="true" focusable="false">
    <circle cx="930" cy="330" r="560" fill="none" stroke="#F37338" stroke-width="1.2" vector-effect="non-scaling-stroke"/>
    <circle cx="880" cy="560" r="330" fill="none" stroke="#F37338" stroke-width="1.2" vector-effect="non-scaling-stroke"/>
    <path d="M -40 920 C 220 760, 420 780, 640 980" fill="none" stroke="#F37338" stroke-width="1.2" vector-effect="non-scaling-stroke" opacity=".7"/></svg>`;
}
