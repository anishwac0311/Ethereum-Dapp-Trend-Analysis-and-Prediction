/* every walk step: its page function, by key (v1–v5 for a DApp, w0–w4 for the market) */
const PAGES={};
/* =====================================================================
   The two scenario walks. Not the six questions again: each step's answer picks what the next step
   looks at, so the visitor digs down instead of reading six separate facts.
     Market (s2): a moment → who is hot → who runs that category → what the leaders share → do users stay
     My DApp (s1): its category → its rivals → the gap to the leaders → do its users stay
   ===================================================================== */
const STEP={
  w0:{short:"Moment", ask:"Pick a moment in the market.", kind:"Describe"},
  w1:{short:"Hot or fading", ask:"Who's hot, and who's fading?", kind:"Describe"},
  w2:{short:"Leaders", ask:"Who runs it?", kind:"Describe"},
  w3:{short:"What they share", ask:"What do the leaders share?", kind:"Predict"},
  w4:{short:"Retention", ask:"Do their users stay?", kind:"Describe"},
  v1:{short:"Category", ask:"Is its category hot or fading?", kind:"Describe"},
  v2:{short:"Rivals", ask:"Who are its rivals?", kind:"Describe"},
  v3:{short:"The gap", ask:"How does it compare with the leaders?", kind:"Predict"},
  v4:{short:"Retention", ask:"Will its users stay?", kind:"Describe"}};
Object.entries(STEP).forEach(([k,v])=>{ ASK[k]=v.ask; QNAME[k]=v.short; PNAME[k]=v.short; KIND[k]=v.kind; });
BOOKS.s1.pages=["v1","v2","v3","v4"]; BOOKS.s2.pages=["w0","w1","w2","w3","w4"];
BOOKS.s1.time="Your DApp, dug down"; BOOKS.s2.time="The market, dug down";

const ERAWIN={before:["2020-01","2022-04"],between:["2022-05","2024-02"],after:["2024-03","2025-12"]};
function eraCats(e){
  const M=D.q1.months, [f,t]=ERAWIN[e], a=M.indexOf(f), b=M.indexOf(t);
  return CATS.map(c=>{ const W=D.q1.wallets[c], s0=W.slice(a,a+3).filter(v=>v!=null), s1=W.slice(b-2,b+1).filter(v=>v!=null);
    const m0=s0.reduce((x,y)=>x+y,0)/(s0.length||1), m1=s1.reduce((x,y)=>x+y,0)/(s1.length||1);
    return {c, v:m0>0?m1/m0-1:null, w0:m0, w1:m1}; }).filter(r=>r.v!=null&&r.w0>=1000).sort((x,y)=>y.v-x.v);
}
const chg=v=>v==null?"–":v>=1?`×${(1+v).toFixed(v>=9?0:1)}`:sgn(v);
const leadOf=(e,c)=>(D.lead[e]||{})[c]||null;
const FEATS=[["ret","Returning share",v=>pct(v),"Stickiness"],["txpw","Transactions per wallet",v=>v>=10?Math.round(v)+"":v.toFixed(1),"Stickiness"],
  ["wal","Active wallets",v=>fmtN(v),"Size"],["whale","Whale share",v=>pct(v),"Concentration"]];
function featOf(slug){ const d=D.snap[slug]; if(!d) return null; const w=d.w&&d.w[2];
  return {ret:d.ns&&d.ns[2]!=null?1-d.ns[2]:null, wal:w||null, txpw:d.t&&w?d.t[2]/w:null, whale:d.wh?d.wh[2]:null}; }
function featMed(slugs){ const F=slugs.map(featOf).filter(Boolean), o={}; FEATS.forEach(([k])=>o[k]=med(F.map(f=>f[k]))); o.n=F.length; return o; }
const catSlugs=c=>Object.entries(D.snap).filter(([k,d])=>d.c===c).map(([k])=>k);

/* a row per measure, one thin bar per group, each row scaled to its own largest value */
function retFig(e, extra){
  const Pd=D.q5.periods[e], xs=D.q5.months;
  return chart({tipx:t=>t===0?"Launch month":`Month ${t}`,w:980,h:380,r:150,x:[0,6],y:[0,1],xticks:xs,fx:t=>t===0?"launch":`M${t}`,yticks:[0,.25,.5,.75,1],fy:t=>pct(t),xlabel:"months after launch · first users still active",
    bands:[{lo:xs.map(i=>[i,Pd.lo[i]]),hi:xs.map(i=>[i,Pd.hi[i]]),color:"#E2DDD4",op:.7}],
    series:[{pts:xs.map(i=>[i,Pd.median[i]]),color:"#1A1A1A",w:2.5,label:`Typical · ${pct(Pd.median[6])}`,tip:`Typical DApp launched ${PERIOD_IN[e]}`},...(extra||[])],aria:"First users still active"});
}

/* ---------- the market walk ---------- */
function wEra(){ const e=era(); return e; }
function pW0(){
  const e=wEra(), M=D.q1.months, tot=i=>CATS.reduce((s,c)=>s+(D.q1.wallets[c][i]||0),0);
  const cards=SERAS.map(x=>{ const r=eraCats(x.k), [f,t]=ERAWIN[x.k], a=M.indexOf(f), b=M.indexOf(t), ch=tot(b)/Math.max(1,tot(a))-1, on=x.k===e;
    /* the era's whole market, month by month: a small picture of what happened inside it */
    const ys=[]; for(let i=a;i<=b;i++) ys.push(tot(i)); const mx=Math.max(...ys,1), W=240, H=64, px=i=>i/(ys.length-1)*W, py=v=>H-4-v/mx*(H-10);
    const line=ys.map((v,i)=>`${i?"L":"M"}${px(i).toFixed(1)} ${py(v).toFixed(1)}`).join(" ");
    const spark=`<svg class="w-spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true"><path d="${line} L${W} ${H} L0 ${H}Z" fill="${on?"#E8E2DA":"#EFEBE5"}"/><path d="${line}" fill="none" stroke="${on?"#1A1A1A":"#A39E95"}" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>`;
    return `<button class="w-era ${on?"on":""}" data-pera="${x.k}" aria-pressed="${on}" aria-label="${on?"Selected":"Choose"}: ${x.name}"><div class="w-art"><span class="s-mono">${x.span}</span><div class="ax-wrap w-chart"><span class="ax-y ax-top">${fmtN(mx)}</span><span class="ax-y ax-bot">0</span>${spark}</div><div class="ax-x w-axx"><span>${monthLabel(M[a])}</span><span>monthly wallets</span><span>${monthLabel(M[b])}</span></div></div><b>${x.name}</b><p>${x.note}</p>
      <div class="w-big"><strong>${chg(ch)}</strong><span>market wallets, first vs last 3 months</span></div>
      <div class="w-hot"><span class="s-mono">Hottest</span><span>${r[0]?r[0].c:"–"}</span></div></button>`; }).join("");
  return {head:T("w0.head",{era:PERIOD[e]}), read:T("w0.read"),
    fig:`<div class="w-eras w-eras2">${cards}</div><p class="w-cap">Market wallets: the first three months of each era against its last three.</p>`, bare:true,
    brief:`${PERIOD[e]}: ${SERAS.find(x=>x.k===e).note}.`, say:PERIOD_IN[e][0].toUpperCase()+PERIOD_IN[e].slice(1), path:["Moment",PERIOD[e]]};
}
function pW1(){
  const e=wEra(), rows=eraCats(e); if(!S.catPicked && rows[0]) S.cat=rows[0].c;
  const top=rows[0], bot=rows[rows.length-1], me_=rows.find(r=>r.c===S.cat)||top;
  const fig=sBars(rows.map(r=>({label:r.c,v:r.v,hi:r.c===S.cat,tip:`${r.c}, ${PERIOD[e]}\n${chg(r.v)} across the era\n${fmtN(r.w0)} → ${fmtN(r.w1)} monthly wallets`})),v=>chg(v),{aria:"Change by category"});
  const chips=`<div class="w-pickrow w-pickup"><p><span class="s-mono">Next steps follow</span> <b>${S.cat}</b>${S.cat===top.c?", the hottest this era.":"."}</p>
    <details class="w-more"${S.wopen==="cat"?" open":""}><summary>Follow another category</summary><div class="w-menu">${rows.map(r=>`<button class="${r.c===S.cat?"on":""}" data-follow="${r.c}"><span>${r.c}</span><em>${chg(r.v)}</em></button>`).join("")}</div></details></div>`;
  /* the conclusion is about the category you follow; the hottest one keeps the short form */
  const Era=PERIOD_IN[e].charAt(0).toUpperCase()+PERIOD_IN[e].slice(1), crank=rows.indexOf(me_)+1, moved=v=>v>=0?T("w1.moved.grew",{x:chg(v).replace(/^\+/,"")}):T("w1.moved.shrank",{x:pct(-v)});
  return {head:me_===top?T("w1.head.top",{Era, top:top.c, topChg:chg(top.v), bot:bot.c, botMove:T(bot.v<0?"w.fadedMost":"w.grewLeast"), botChg:chg(bot.v)})
      :T("w1.head.follow",{Era, cat:S.cat, moved:moved(me_.v), rank:crank, n:rows.length, top:top.c, topChg:chg(top.v)}),
    /* the line under it says what the bars are, and where the category you follow sits */
    read:me_===top?T("w1.read.top",{n:rows.length, era:PERIOD_IN[e], top:top.c}):T("w1.read.follow",{n:rows.length, era:PERIOD_IN[e], top:top.c, cat:S.cat, ord:["","first","second","third","fourth","fifth","sixth","seventh"][crank]||"#"+crank}),
    fig, pick:chips, how:"Change in monthly active wallets, first three months of the era against the last three.",
    src:`Category activity · n = ${rows.length} categories, monthly active wallets.`, careful:rows.length<CATS.length?`${CATS.length-rows.length} small categories are hidden: too few wallets at the start to measure change.`:"",
    brief:`${S.cat} ${me_.v>=0?"grew":"shrank"} ${chg(me_.v)} ${PERIOD_IN[e]}.`, say:`${S.cat} ${me_.v>=0?`grew ${chg(me_.v).replace(/^\+/,"")}`:`shrank ${pct(-me_.v)}`}`, path:["Hot or fading",`${S.cat}, wallets ${chg(me_.v)} in the era`]};
}
function pW2(){
  const e=wEra(), L=leadOf(e,S.cat);
  if(!L) return {head:T("w2.none",{cat:S.cat, era:PERIOD_IN[e]}), fig:"", brief:"No leaders.", path:["Leaders","–"]};
  if(!L.top.some(t=>t[0]===S.leader)) S.leader=L.top[0][0];
  const t5=L.top.reduce((s,t)=>s+t[3],0), lead=L.top.find(t=>t[0]===S.leader);
  const fig=sBars(L.top.map(t=>({label:t[1].length>18?t[1].slice(0,17)+"…":t[1],v:t[3],hi:t[0]===S.leader,tip:`${t[1]}\n${pct(t[3],1)} of ${S.cat} wallets\n${fmtN(t[2])} monthly wallets on average`})),v=>pct(v),{aria:"Share of the category's wallets"});
  const chips=`<div class="w-pickrow w-pickup"><p><span class="s-mono">Next steps follow</span> <b>${esc(lead[1])}</b>${S.leader===L.top[0][0]?", the leader.":"."}</p>
    <details class="w-more"><summary>Follow another leader</summary><div class="w-menu">${L.top.map(t=>`<button class="${t[0]===S.leader?"on":""}" data-leader="${t[0]}"><span>${esc(t[1])}</span><em>${pct(t[3])}</em></button>`).join("")}</div></details></div>`;
  /* the conclusion is about the leader you follow; the first one keeps the short form */
  const rank=L.top.findIndex(t=>t[0]===S.leader)+1, ORD=["","first","second","third","fourth","fifth"];
  return {head:rank<=1?T("w2.head.first",{first:esc(L.top[0][1]), firstShare:pct(L.top[0][3]), cat:S.cat, era:PERIOD_IN[e], top5:pct(t5)})
      :T("w2.head.follow",{lead:esc(lead[1]), leadShare:pct(lead[3]), cat:S.cat, era:PERIOD_IN[e], ord:ORD[rank], first:esc(L.top[0][1]), firstShare:pct(L.top[0][3]), top5:pct(t5)}),
    /* the line under it says what the chart shows, so "the top 5" is not a mystery */
    read:rank<=1?T("w2.read.first",{cat:S.cat, era:PERIOD_IN[e], first:esc(L.top[0][1])}):T("w2.read.follow",{cat:S.cat, era:PERIOD_IN[e], first:esc(L.top[0][1]), lead:esc(lead[1]), ord:ORD[rank]}),
    fig, pick:chips, how:"Each bar is one DApp's share of the category's monthly active wallets, averaged over the era.",
    src:`Leaders · n = ${L.n} ${S.cat} DApps active in the era.`, careful:t5>.8?`The top 5 hold most of ${S.cat}: a newcomer competes with a few giants.`:`${S.cat} is spread out: beyond the top 5 there is still ${pct(1-t5)} to win.`,
    brief:`${esc(L.top[0][1])} leads ${S.cat} with ${pct(L.top[0][3])}; the top 5 hold ${pct(t5)}.`, say:`${esc(lead[1])} led it with ${pct(lead[3])} of its wallets`, path:["Leader",`${esc(lead[1])}, ${pct(lead[3])} of ${S.cat} wallets`]};
}
function watchOf(e){ const Wt=D.q5.weights[e], top=Object.keys(Wt).sort((a,b)=>Wt[b][0]-Wt[a][0])[0]; return {top, w:Wt[top][0]}; }
function pW3(){
  const e=wEra(), L=leadOf(e,S.cat), w=watchOf(e), TM=featMed(catSlugs(S.cat));
  /* the leader you followed is the first, blue row; the top 5 and the typical DApp of the category stay as the yardsticks */
  const fl=L?(L.top.find(t=>t[0]===S.leader)||L.top[0]):null, FM=fl?featMed([fl[0]]):null;
  /* the yardstick is the OTHER four leaders, so the leader is never compared with a median that includes itself */
  const LM=featMed(L?L.top.map(t=>t[0]).filter(k=>!fl||k!==fl[0]):[]);
  const fk=(FEATS.find(f=>f[3]===w.top)||FEATS[0]);
  /* the chart: each group's share of the model's weight in each era (all its signals added up); the era you picked is marked */
  const EO=["before","between","after"], ei=EO.indexOf(e), GW=D.q5.weights, groups=Object.keys(GW[e]).sort((a,b)=>GW[e][b][0]-GW[e][a][0]);
  const fig=chart({w:980,h:380,r:150,x:[-.12,2.12],y:[0,.4],xticks:[0,1,2],fx:i=>["Before Terra","Terra → Dencun","After Dencun"][i],yticks:[0,.1,.2,.3,.4],fy:v=>pct(v),
    bands:[{lo:[[Math.max(-.12,ei-.5),0],[Math.min(2.12,ei+.5),0]],hi:[[Math.max(-.12,ei-.5),.4],[Math.min(2.12,ei+.5),.4]],color:"#E2DDD4",op:.55}], tipx:i=>["Before Terra","Terra → Dencun","After Dencun"][i],
    series:groups.map(g=>({pts:EO.map((k,i)=>[i,GW[k][g][0]]),color:g===w.top?"#1A1A1A":"#A39E95",w:g===w.top?3.5:1.6,label:g,tip:g})), marks:[{x:ei,y:w.w,fill:"#1A1A1A"}],
    xlabel:"share of the model's weight",aria:"The model's weight by group and era"});
  const lv=LM[fk[0]], tv=TM[fk[0]], fv=FM?FM[fk[0]]:null;
  const prevE=ei>0?EO[ei-1]:null, second=groups[1];
  const change=prevE?`${GW[prevE][w.top][0]<w.w?"up":"down"} from ${pct(GW[prevE][w.top][0])} ${PERIOD_IN[prevE]}`:`ahead of ${second.toLowerCase()} (${pct(GW[e][second][0])})`;
  /* the signal where the leader is closest to the other leaders, and the one where it is furthest (ratio, so shares and counts compare alike) */
  const gap=FEATS.filter(f=>FM&&FM[f[0]]!=null&&LM[f[0]]!=null&&FM[f[0]]>0&&LM[f[0]]>0).map(f=>({f,d:Math.abs(Math.log(FM[f[0]]/LM[f[0]]))})).sort((a,b)=>a.d-b.d);
  const Era=PERIOD_IN[e].charAt(0).toUpperCase()+PERIOD_IN[e].slice(1), nm=fl?esc(fl[1]):null, vs=f=>`${f[2](FM[f[0]])} against ${f[2](LM[f[0]])}`;
  /* the Conclusion is how the model's weight moved (the group it now leans on most is the keyword); the leader you follow is in the line under it */
  const model=(()=>{ const t=w.top.toLowerCase();
    if(!prevE) return T("w3.head.first",{Era, group:t, share:pct(w.w), second:second.toLowerCase(), secondShare:pct(GW[e][second][0])});
    const d=g=>GW[e][g][0]-GW[prevE][g][0], others=groups.filter(g=>g!==w.top), fall=others.slice().sort((a,b)=>d(a)-d(b))[0], rise=others.slice().sort((a,b)=>d(b)-d(a))[0], ft=(g)=>T("w3.move",{from:pct(GW[prevE][g][0]), to:pct(GW[e][g][0])});
    return d(w.top)>0?T("w3.head.rose",{Era, group:t, groupMove:ft(w.top), fall:fall.toLowerCase(), fallMove:ft(fall)})
      :T("w3.head.stays",{Era, group:t, groupMove:ft(w.top), rise:rise.toLowerCase(), riseMove:ft(rise)}); })();
  /* the leader, in plain words: on the strongest group's signal, then the group where it differs most from the other four leaders */
  const plain=(f,v)=>T("w3.plain."+({ret:"ret",txpw:"txpw",wal:"wal"}[f[0]]||"whale"),{v:f[2](v)});
  const t0=f=>f[3].toLowerCase();
  const leaderLine=(()=>{ const tf=FEATS.find(f=>f[3]===w.top&&gap.some(g=>g.f===f)), out=gap.filter(g=>g.f[3]!==w.top), df=out.length?out[out.length-1].f:null;
    if(!nm||!tf||!df) return T("w3.read.none",{cat:S.cat});
    const verb=T(tf[2](FM[tf[0]])===tf[2](LM[tf[0]])?"w3.verb.matches":FM[tf[0]]>LM[tf[0]]?"w3.verb.above":"w3.verb.below");
    return T("w3.read",{lead:nm, verb, cat:S.cat, group:t0(tf), mine:plain(tf,FM[tf[0]]), theirs:tf[2](LM[tf[0]]), group2:df[3].toLowerCase(), mine2:plain(df,FM[df[0]]), theirs2:df[2](LM[df[0]])}); })();
  return {ask:nm?T("w3.ask",{lead:nm}):undefined,
    head:model,
    read:leaderLine,
    fig, define:true, how:`Each line is one group of the model's 33 early signals: its share of the model's weight in each era, all of the group's signals added up. The grey band marks the era you picked; the darker line is the group the model leans on most in it. The Conclusion compares the leader you follow with the median of the category's other four leaders, in their third month.`,
    src:`Model weights · n = ${LM.n} other leaders and ${TM.n} ${S.cat} DApps with early data.`,
    careful:lv!=null&&tv!=null&&lv<tv?`Here the leaders were below typical on ${fk[1].toLowerCase()}: in ${S.cat}, being early and big mattered more than what the model weighs most across all DApps.`:"Leaders that launched before 2020 have no early months in our data, so they drop out of the black bars.",
    brief:`Watch ${w.top.toLowerCase()}: ${fk[1].toLowerCase()} ${lv!=null?fk[2](lv):"–"} for leaders vs ${tv!=null?fk[2](tv):"–"} typical.`, say:lv!=null&&tv!=null?`its leaders differed most on ${fk[1].toLowerCase()} (${fk[2](lv)} vs ${fk[2](tv)} typical)`:`its leaders differed most on ${fk[1].toLowerCase()}`, path:["Watch",`${w.top}, ${pct(w.w)} of the model's weight`]};
}
function pW4(){
  const e=wEra(), Pd=D.q5.periods[e], ld=D.dapps[S.leader];
  /* the leader you followed is set against the typical DApp launched in its own era (its first users came then) */
  if(ld&&ld.ret){ const le=D.q5.periods[ld.period]?ld.period:e, Pl=D.q5.periods[le], up=ld.ret[6]>=Pl.median[6];
    const extra=[{pts:ld.ret.map((v,i)=>[i,v]),color:"#3860BE",w:2.5,label:`${ld.name.length>14?ld.name.slice(0,13)+"…":ld.name} · ${pct(ld.ret[6])}`,tip:ld.name,dot:true}];
    return {head:T("w4.head",{lead:esc(ld.name), kept:pct(ld.ret[6]), launchEra:PERIOD_IN[le], typical:pct(Pl.median[6])}),
      read:T("w4.read",{side:T(up?"w4.side.above":"w4.side.below"), otherEra:le!==e?T("w4.otherEra",{launchEra:PERIOD_IN[le], era:PERIOD_IN[e]}):""}),
      fig:`<div class="draw-once">${retFig(le,extra)}</div>`, how:`Black: the typical DApp launched ${PERIOD_IN[le]}, with the middle half shaded. Blue: ${esc(ld.name)}.`,
      src:`Retention · n = ${Pl.n} DApps with 100+ wallets in their first month.`, careful:`Most of the drop happens in the first month: only ${pct(Pl.median[1])} are left after one month.`,
      brief:`${esc(ld.name)} kept ${pct(ld.ret[6])} after six months (typical ${pct(Pl.median[6])}).`, say:`${esc(ld.name)} kept ${pct(ld.ret[6])} of its first users after six months (typical ${pct(Pl.median[6])})`, path:["Retention",`${pct(ld.ret[6])} of first users at month 6`]}; }
  const nm=ld?esc(ld.name):"the leader you followed";
  return {head:T("w4.head.typical",{era:PERIOD_IN[e], month6:pct(Pd.median[6])}),
    read:T("w4.read.cannot",{lead:nm, why:ld&&ld.launch?(ld.launch<=D.meta.panel_start?T("w4.why.early"):T("w4.why.small",{min:D.q5.min_cohort})):""}),
    fig:`<div class="draw-once">${retFig(e,[])}</div>`, how:"Black: the typical DApp launched in this era, with the middle half shaded.",
    src:`Retention · n = ${Pd.n} DApps with 100+ wallets in their first month.`, careful:`Most of the drop happens in the first month: only ${pct(Pd.median[1])} are left after one month.`,
    brief:`Typical retention after six months: ${pct(Pd.median[6])}.`, say:`the typical DApp kept ${pct(Pd.median[6])} of its first users after six months`, path:["Retention",`${pct(Pd.median[6])} of first users at month 6`]};
}

Object.assign(PAGES,{w0:pW0,w1:pW1,w2:pW2,w3:pW3,w4:pW4});
/* ---------- the my-DApp walk: one DApp looking outward ----------
   shape → where it stands → who it looked like early on → what to watch → did it make it */
Object.assign(STEP,{
  v1:{short:"Shape", ask:"What shape is it?", kind:"Describe"},
  v2:{short:"Standing", ask:"Where does it stand in its category?", kind:"Describe"},
  v3:{short:"Lookalikes", ask:"Who did it look like early on?", kind:"Describe"},
  v4:{short:"Watch", ask:"What should it watch?", kind:"Predict"},
  v5:{short:"Outcome", ask:"Did it make it?", kind:"Describe"}});
Object.entries(STEP).forEach(([k,v])=>{ ASK[k]=v.ask; QNAME[k]=v.short; PNAME[k]=v.short; KIND[k]=v.kind; });
BOOKS.s1.pages=["v1","v2","v3","v4","v5"];
const YOU="#3860BE";
const shortName=(n,k=16)=>n.length>k?n.slice(0,k-1)+"…":n;

function pV1(){
  const d=me(), q2=D.q2, xs=[...Array(24).keys()], nm=d.norm&&d.norm.length?d.norm:null;
  const series=[{pts:xs.map(i=>[i,q2.median.grower[i]]),color:"#1A1A1A",w:2.5,label:"Kept growing",tip:"Kept growing (median)"},{pts:xs.map(i=>[i,q2.median.flash[i]]),color:"#A39E95",w:2,dash:"5 4",label:"One-hit",tip:"One-hit (median)"}];
  if(nm) series.push({pts:nm.map((v,i)=>[i,v]),color:YOU,w:2.5,label:shortName(d.name,14),tip:d.name,dot:true});
  const pk=nm?nm.indexOf(Math.max(...nm.filter(v=>v!=null))):null, last=nm?nm.filter(v=>v!=null).slice(-1)[0]:null;
  const shape=T(d.group==="grower"?"v1.shape.grower":"v1.shape.flash");
  return {head:T(d.group==="grower"?"v1.head.grower":"v1.head.flash",{name:esc(d.name), shape}),
    read:nm?T("v1.read",{peakMonth:pk, held:pct(last), grower:pct(q2.median.grower[23]), flash:pct(q2.median.flash[23])}):"",
    fig:chart({tipx:t=>t===0?"Launch month":`Month ${t}`,w:980,h:380,r:150,x:[0,23],y:[0,1],xticks:[0,3,6,9,12,15,18,21,23],fx:t=>t===0?"launch":`M${t}`,yticks:[0,.25,.5,.75,1],fy:t=>pct(t),xlabel:"months after launch · share of its own peak",series,aria:"Its shape vs the typical shapes"}),
    how:`Every widely used DApp falls into one of two shapes. Black: the median DApp that kept growing. Grey dashed: the median one-hit DApp. Blue: ${esc(d.name)}.`,
    src:`Shape · n = ${q2.n} widely used DApps (${q2.counts.grower} kept growing, ${q2.counts.flash} one-hit).`,
    brief:`${esc(d.name)} ${shape}.`, say:`${esc(d.name)} ${d.group==="grower"?"kept growing":"was a one-hit"}`, path:["Shape",d.group==="grower"?"Kept growing":"One-hit"]};
}
function pV2(){
  const d=me(), e=era(), L=leadOf(e,d.cat), mine=L&&L.all[d.slug];
  if(!L) return {head:T("v2.none",{cat:d.cat, era:PERIOD_IN[e]}), fig:"", brief:"–", path:["Standing","–"]};
  const rows=L.top.map(t=>({label:shortName(t[1],18),v:t[3],hi:t[0]===d.slug,tip:`${t[1]}\n${pct(t[3],1)} of ${d.cat} wallets`}));
  if(mine&&mine[2]>5) rows.push({label:`#${mine[2]} ${shortName(d.name,14)}`,v:mine[1],hi:true,tip:`${d.name}\nrank ${mine[2]} of ${L.n}\n${pct(mine[1],1)} of ${d.cat} wallets`});
  const rs=eraCats(e), r=rs.find(x=>x.c===d.cat);
  return {head:mine?T("v2.head",{name:esc(d.name), rank:T("v2.rank",{rank:mine[2], n:L.n}), cat:d.cat, era:PERIOD_IN[e], share:pct(mine[1],1)}):T("v2.head.idle",{name:esc(d.name), era:PERIOD_IN[e]}),
    read:T("v2.read",{first:esc(L.top[0][1]), firstShare:pct(L.top[0][3]), top5:pct(L.top.reduce((s,t)=>s+t[3],0)), catNote:r?T("v2.catNote",{cat:d.cat, catMove:T(r.v>=0?"w.grew":"w.shrank"), catChg:chg(r.v)}):""}),
    fig:sBars(rows,v=>pct(v,1),{aria:"Share of the category's wallets"}), how:"Share of the category's monthly active wallets, averaged over the era it launched in. Highlighted: this DApp.",
    src:`Standing · average monthly wallets of every ${d.cat} DApp active in the era.`, brief:mine?`#${mine[2]} of ${L.n} in ${d.cat}, ${pct(mine[1],1)} of its wallets.`:"–", say:mine?`ranked #${mine[2]} of ${L.n} in ${d.cat}`:"", path:["Standing",mine?`#${mine[2]} of ${L.n} in ${d.cat}`:"–"]};
}
/* lookalikes: nearest DApps in its third month, on wallets (log) and returning share */
function lookalikes(slug,k=20){
  const pt=s=>{ const x=D.snap[s]; if(!x||!x.w||!(x.w[2]>0)||!x.ns||x.ns[2]==null) return null; return {u:Math.log10(x.w[2])/6, v:1-x.ns[2]}; };
  const me0=pt(slug); if(!me0) return null;
  const all=Object.keys(D.snap).filter(s=>s!==slug&&D.snap[s].s!=null).map(s=>({s,p:pt(s)})).filter(x=>x.p);
  return {me:me0, all, near:all.map(x=>({...x,d:Math.hypot(x.p.u-me0.u,x.p.v-me0.v)})).sort((a,b)=>a.d-b.d).slice(0,k)};
}
function lookFig(LA,name){
  const ph=PHONE(), W=ph?560:980,H=ph?430:380,m={l:64,r:24,t:ph?40:34,b:50}, X=u=>m.l+Math.min(1,Math.max(0,u))*(W-m.l-m.r), Y=v=>m.t+(1-v)*(H-m.t-m.b), near=new Set(LA.near.map(n=>n.s));
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="DApps in their third month">`;
  [0,1,2,3,4,5,6].forEach(t=>{ s+=`<line x1="${X(t/6)}" x2="${X(t/6)}" y1="${m.t}" y2="${H-m.b}" stroke="#ECE8E1"/><text class="ax" x="${X(t/6)}" y="${H-m.b+18}" text-anchor="middle">${fmtN(10**t)}</text>`; });
  [0,.5,1].forEach(t=>{ s+=`<text class="ax" x="${m.l-10}" y="${Y(t)+4}" text-anchor="end">${pct(t)}</text><line x1="${m.l}" x2="${W-m.r}" y1="${Y(t)}" y2="${Y(t)}" stroke="#ECE8E1"/>`; });
  s+=`<text class="ax" x="${W-m.r}" y="${H-8}" text-anchor="end">active wallets in month 3 (log) →</text><text class="ax" x="${m.l}" y="${m.t-16}">↑ returning share</text>`;
  LA.all.forEach(x=>{ const n=near.has(x.s), d=D.snap[x.s]; s+=`<circle cx="${X(x.p.u)}" cy="${Y(x.p.v)}" r="${n?5:3}" fill="${d.s?"#9C4A26":"#CFC9BF"}" opacity="${n?1:.35}" ${n?`stroke="#1A1A1A" stroke-width="1"`:""} data-tip="${esc(`${d.n}\n${d.s?"Still a success a year later":"Not a success a year later"}`)}"/>`; });
  const mx=X(LA.me.u), my=Y(LA.me.v);
  s+=`<circle cx="${mx}" cy="${my}" r="8" fill="${YOU}" stroke="#FBFAF7" stroke-width="2"/>`;
  /* legend: every mark on the chart, in one row */
  const key=[[`<circle r="6" fill="${YOU}"/>`,esc(name||"This DApp")],[`<circle r="5" fill="#9C4A26" stroke="#1A1A1A"/>`,"Lookalike · success"],[`<circle r="5" fill="#CFC9BF" stroke="#1A1A1A"/>`,"Lookalike · not a success"],[`<circle r="3" fill="#9C4A26" opacity=".35"/><circle cx="8" r="3" fill="#CFC9BF" opacity=".6"/>`,"Every other DApp"]];
  /* phones: the legend moves into How to read (see lookKey), so the chart starts right under its top row */
  let kx=W-m.r; const kf=12, parts=ph ? [] : key.slice().reverse().map(([g,t])=>{ const w=t.length*6.6+26; kx-=w; return `<g transform="translate(${kx+6},${m.t-20})">${g}<text x="${g.includes('cx="8"')?18:12}" y="4" style="font:500 ${kf}px 'Plus Jakarta Sans',system-ui,sans-serif;fill:#5A5650">${t}</text></g>`; });
  s+=parts.join("");
  return s+"</svg>";
}
/* the lookalikes legend as lines for the How to read sheet on phones: one mark and its meaning per line */
function lookKey(name){ const dot=(bg,extra="")=>`<i class="m-key" style="background:${bg};${extra}"></i>`;
  return `<span class="m-legend"><span>${dot(YOU)}${esc(name||"This DApp")}</span><span>${dot("#9C4A26","border:1px solid #1A1A1A")}Lookalike · success</span><span>${dot("#CFC9BF","border:1px solid #1A1A1A")}Lookalike · not a success</span><span>${dot("#CFC9BF","opacity:.6")}Every other DApp</span></span>`; }
function pV3(){
  const d=me(), LA=lookalikes(d.slug);
  if(!LA) return {head:T("v3.none",{name:esc(d.name)}), fig:"", brief:"No third-month data.", path:["Lookalikes","No month-3 data"]};
  const win=LA.near.filter(x=>D.snap[x.s].s).length, base=LA.all.filter(x=>D.snap[x.s].s).length/LA.all.length;
  const top3=LA.near.slice(0,3).map(x=>D.snap[x.s].n);
  return {head:T("v3.head",{name:esc(d.name), three:top3.map(esc).join(", ").replace(/, ([^,]*)$/," and $1")}),
    read:T("v3.read",{win, winShare:pct(win/20), base:pct(base)}),
    fig:lookFig(LA,d.name), how:`${PHONE()?lookKey(d.name)+"<br>":""}Each dot is one DApp in its third month. The ringed dots are its closest lookalikes on these two numbers; rust means still a success a year later, grey means not. Faint dots are every other DApp.`,
    src:`Lookalikes · n = ${LA.all.length} DApps launched 2020–2024 with a known outcome.`, careful:"Looking alike early is not ending alike: the lookalikes went different ways.",
    brief:`Looked like ${top3.map(esc).join(", ")}; ${win} of 20 lookalikes lasted.`, say:`${win} of its 20 lookalikes succeeded`, path:["Lookalikes",`${win} of 20 succeeded`]};
}
/* one signal of the era's model, for its sheet: what it measures (the plain line where the site has one, else its group), and the typical values from Method's Signals tab */
const SIG_MET={log_mean_wallets:"wallets",log_mean_tx:"tx",log_mean_gas:"gas",log_mean_fees:"fee",early_returning_share:"returning",early_tx_per_wallet:"txpw",early_whale_share:"whale",avg_n_protocols_in_tx:"apps"};
function sigCard(feature){ const e=era(), x=(window.SIGNALS[e]||[]).find(s=>s.feature===feature), f=D.method.features.find(m=>m.feature===feature); if(!x||!f) return "";
  const m=MET[SIG_MET[feature]], note=(GROUPS.find(g=>g[0]===x.group)||[])[2]||"";
  return `<span class="s-mono">${T("sig.sub",{group:x.group, rank:x.rank, n:window.SIGNALS[e].length, era:PERIOD_IN[e]})}</span><h3>${f.label}</h3>
    <p>${m?m.plain:T("sig.group",{group:x.group.toLowerCase(), note:note.charAt(0).toLowerCase()+note.slice(1)})}</p>
    <p class="t-ex">${T("sig.typical",{s:fmtFeat(f.success,f.kind), o:fmtFeat(f.other,f.kind)})}</p>`; }
function pV4(){
  const d=me(), e=era();
  const coh=Object.entries(D.snap).filter(([k,x])=>x.s!=null&&x.lm&&periodOf(x.lm)===e&&k!==d.slug);
  const YM=featOf(d.slug)||{}, SM=featMed(coh.filter(([k,x])=>x.s===1).map(([k])=>k));
  const Era=PERIOD_IN[e].charAt(0).toUpperCase()+PERIOD_IN[e].slice(1);
  /* the era's model, signal by signal (script/build_signals.py): the five that carry the most weight */
  const SIG=window.SIGNALS[e], top5=SIG.slice(0,5), GW=D.q5.weights[e], groups=Object.keys(GW).sort((a,b)=>GW[b][0]-GW[a][0]);
  const label=f=>{ const m=(D.method.features.find(x=>x.feature===f)||{}).label||f; return m.charAt(0).toLowerCase()+m.slice(1); };
  const leadOfGroup=g=>SIG.find(x=>x.group===g);
  const [g1,g2]=groups;
  const head=T("v4.head",{Era, group:g1.toLowerCase(), share:pct(GW[g1][0]), signal:label(leadOfGroup(g1).feature), group2:g2.toLowerCase(), share2:pct(GW[g2][0]), signal2:label(leadOfGroup(g2).feature)});
  /* the line under it: this DApp on the first of the five we hold per-DApp numbers for */
  const FMAP={early_returning_share:"ret", early_tx_per_wallet:"txpw", early_whale_share:"whale"};
  const hit=top5.find(x=>FMAP[x.feature]&&YM[FMAP[x.feature]]!=null&&SM[FMAP[x.feature]]!=null), hf=hit&&FEATS.find(f=>f[0]===FMAP[hit.feature]);
  const lineV=hit&&{signal:label(hit.feature), rank:hit.rank, n:SIG.length, name:esc(d.name), mine:hf[2](YM[hf[0]]), theirs:hf[2](SM[hf[0]])};
  const cap=x=>x.charAt(0).toUpperCase()+x.slice(1);
  const read=hit?T("v4.read",lineV):T("v4.read.none",{name:esc(d.name)});
  const fig=`<table class="ft sig-t" aria-label="${T("v4.table.aria",{era:PERIOD_IN[e]})}"><thead><tr><th>#</th><th>${T("v4.th.signal")}</th><th class="s">${T("v4.th.group")}</th><th>${T("v4.th.share")}</th><th class="sig-cum">${T("v4.th.cum")}</th></tr></thead><tbody>${top5.map(x=>`<tr><td>${x.rank}</td><td class="s"><button class="term" data-act="sigterm" data-f="${x.feature}" aria-label="What ${label(x.feature)} means">${label(x.feature).charAt(0).toUpperCase()+label(x.feature).slice(1)}</button></td><td class="s">${x.group}</td><td>${pct(x.share,1)}</td><td class="sig-cum">${pct(x.cum,1)}</td></tr>`).join("")}</tbody></table>`;
  return {head, read, fig, define:true,
    how:T("v4.how",{era:PERIOD_IN[e], n:SIG.length, cum:pct(top5[4].cum)}),
    src:`Model weights · the ${PERIOD_IN[e]} model, fitted on DApps launched in that era; ${SIG.length} on-chain signals.`,
    brief:hit?T("v4.brief",lineV):T("v4.brief.none",{group:g1.toLowerCase()}),
    say:hit?T("v4.say",lineV):"", path:[T("v4.path.label"), hit?T("v4.path",{...lineV, Signal:cap(lineV.signal)}):g1]};
}
function pV5(){
  const d=me(), sn=D.snap[d.slug], L=lifeOf(sn&&sn.l), ws=d.wallets||[], xs=[...Array(24).keys()];
  const avg=[10,11,12].map(i=>ws[i]).filter(v=>v!=null), a=avg.length?avg.reduce((x,y)=>x+y,0)/avg.length:null, peak=Math.max(...ws.filter(v=>v!=null)), q=peak/4;
  const top=Math.max(peak,1000)*1.1;
  const fig=chart({tipx:t=>t===0?"Launch month":`Month ${t}`,w:980,h:380,r:150,x:[0,23],y:[0,top],xticks:[0,3,6,9,12,15,18,21,23],fx:t=>t===0?"launch":`M${t}`,yticks:[0,top/4,top/2,top*3/4,top],fy:fmtN,
    bands:[{lo:[[10,0],[12,0]],hi:[[10,top],[12,top]],color:"#E2DDD4",op:.6}], hline:{y:1000,label:"1,000 wallets"},
    series:[{pts:xs.map(i=>[i,ws[i]]),color:YOU,w:2.5,label:shortName(d.name,14),tip:d.name,dot:true}],xlabel:"months after launch · monthly active wallets",aria:"Its first two years"});
  const pass1=a!=null&&a>=1000, pass2=a!=null&&a>=q;
  return {head:T("v5.head",{name:esc(d.name), verdict:T(d.success?"v5.verdict.yes":"v5.verdict.no")}),
    read:a!=null?T("v5.read",{avg:fmtN(a), pass1:T(pass1?"w.above":"w.below"), pass2:T(pass2?"w.above":"w.below"), quarter:fmtN(q), life:L.name.toLowerCase()}):T("v5.read.short",{life:L.name.toLowerCase()}),
    fig, how:"Blue: its monthly active wallets in the first two years. Shaded: months 10–12, the months we judge. Dashed line: 1,000 wallets.",
    src:`Outcome · ${esc(d.name)}'s own monthly on-chain activity.`, careful:d.ret?`It kept ${pct(d.ret[6])} of its first users after six months; the typical DApp launched ${PERIOD_IN[era()]} kept ${pct(D.q5.periods[era()].median[6])}.`:"",
    brief:`${d.success?"A success":"Not a success"} a year later; ${L.name.toLowerCase()} over its whole history.`, say:`a year later it was ${d.success?"a success":"not a success"}`, path:["Outcome",d.success?"Success":"Not a success"]};
}
Object.assign(PAGES,{v1:pV1,v2:pV2,v3:pV3,v4:pV4,v5:pV5});

