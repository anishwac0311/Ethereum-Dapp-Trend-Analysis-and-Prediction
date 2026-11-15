/* =====================================================================
   The success map. Every DApp we can judge, placed by two signals from its third month.
   The axes can be swapped (wallets, returning share, transactions, gas, fees ...), and each one is
   explained under the map, so the page doubles as a glossary.
   Used twice: Diagnose (drag your DApp onto the map, meet its nearest neighbours) and the Game
   (three levels: could you have spotted the winners from these two numbers alone?).
   ===================================================================== */
/* map canvas: wide on desktop, square on phones so the map is taller and its labels readable (set by mapSize at each render) */
let MAPW=980, MAPH=540, MM={l:70,r:24,t:40,b:56}, IW=0, IH=0;
function mapSize(){ if(PHONE()){ MAPW=560; MAPH=560; MM={l:54,r:26,t:44,b:76}; } else { MAPW=980; MAPH=540; MM={l:70,r:24,t:40,b:56}; } IW=MAPW-MM.l-MM.r; IH=MAPH-MM.t-MM.b; }
mapSize();
const MET={
  wallets:{label:"Active wallets", plain:"How many different people (wallets) used it that month.", hi:"Lots of users", lo:"Only a few users", why:"Size. Bigger DApps last more often, but plenty of big ones still fade.", get:d=>d.w&&d.w[2], log:true, fmt:fmtN, def:"Distinct addresses that used the DApp in the month."},
  returning:{label:"Returning share", plain:"Of this month's users, the share who had used it before.", hi:"Users keep coming back", lo:"Mostly first-timers", why:"Stickiness. After Terra it is the model's strongest signal.", get:d=>d.ns&&d.ns[2]!=null?1-d.ns[2]:null, share:true, fmt:v=>pct(v), def:"Share of the month's wallets that had used it before. A stand-in for stickiness."},
  tx:{label:"Transactions", plain:"How many transactions touched its contracts.", hi:"Busy", lo:"Quiet", why:"Activity. It can come from many users or a handful of bots.", get:d=>d.t&&d.t[2], log:true, fmt:fmtN, def:"Transactions that touched its contracts in the month."},
  txpw:{label:"Transactions per wallet", plain:"How many times the average user came back within the month.", hi:"Used again and again", lo:"Used once and gone", why:"Habit. Repeat use within a month hints at real need.", get:d=>d.t&&d.w&&d.w[2]?d.t[2]/d.w[2]:null, log:true, fmt:v=>v>=10?Math.round(v)+"":v.toFixed(1), def:"How many times the average wallet used it in the month."},
  whale:{label:"Whale share", plain:"How much of its activity comes from its 10 biggest wallets.", hi:"A few wallets carry it", lo:"Spread across many users", why:"Concentration. If a few whales leave, the activity leaves with them.", get:d=>d.wh&&d.wh[2], share:true, fmt:v=>pct(v), def:"Share of activity from its 10 busiest wallets. High means a few users carry it."},
  gas:{label:"Gas used", plain:"How much Ethereum computing power its transactions used.", hi:"Heavy or busy", lo:"Light", why:"Work done on chain. It grows with both activity and complexity.", get:d=>d.m3&&d.m3.gas, log:true, fmt:fmtN, def:"Units of Ethereum computing its transactions consumed. Every operation costs gas, so more gas means more, or heavier, activity."},
  fee:{label:"Fees paid (ETH)", plain:"What its users paid the network, in ETH.", hi:"Users paid a lot", lo:"Cheap to use", why:"Willingness to pay, but fees also rise whenever the whole network is busy.", get:d=>d.m3&&d.m3.fee, log:true, fmt:v=>v>=1?fmtN(v):v>=.01?v.toFixed(2):v.toExponential(0), def:"What users paid the network, in ETH, to use it. Fees are gas times the gas price, so they also rise when the network is busy."},
  apps:{label:"Apps per transaction", plain:"How many apps a typical transaction touched at once.", hi:"Used together with other apps", lo:"Used on its own", why:"Composability. Apps that plug into others can borrow their users.", get:d=>d.m3&&d.m3.apps, lin:true, fmt:v=>v.toFixed(2), def:"How many DApps a typical transaction touched. Above 1 means it is used together with others (composability)."}};
const LIFE={sustained:{name:"Sustained",col:"#3860BE",line:"Grew and kept its users."},
  gradual_decline:{name:"Gradual decline",col:"#1A1A1A",line:"Peaked, then lost users slowly."},
  flash:{name:"Flash",col:"#F37338",line:"Spiked fast, faded fast."},
  never_adopted:{name:"Never adopted",col:"#D1CDC7",line:"Never built a real user base."},
  other:{name:"Unclear",col:"#696969",line:"Too irregular to sort."}};
const lifeOf=l=>LIFE[l]||LIFE.other;
const gAx=()=>S.view==="game"&&S.gm&&S.gm.ax?S.gm.ax:null;
const mAxisX=()=>gAx()?gAx()[0]:MET[S.mx]?S.mx:"wallets", mAxisY=()=>gAx()?gAx()[1]:MET[S.my]?S.my:"returning";
/* the scale of one metric over the pool: log decades, 0–1 shares, or a plain range */
function mScale(key,vals){
  const m=MET[key];
  if(m.share) return {lo:0,hi:1,f:v=>v,inv:u=>u,ticks:[0,.25,.5,.75,1]};
  if(m.log){ const L=vals.map(v=>Math.log10(v)), lo=Math.floor(Math.min(...L)), hi=Math.ceil(Math.max(...L)), st=hi-lo>8?2:1;
    return {lo,hi,f:v=>Math.log10(v),inv:u=>10**u,ticks:[...Array(Math.floor((hi-lo)/st)+1).keys()].map(i=>10**(lo+i*st))}; }
  const lo=Math.floor(Math.min(...vals)*2)/2, hi=Math.ceil(Math.max(...vals)*2)/2;
  return {lo,hi,f:v=>v,inv:u=>u,ticks:[...Array(5).keys()].map(i=>lo+(hi-lo)*i/4)};
}
const MAPCACHE={};
function mapPool(){
  const kx=mAxisX(), ky=mAxisY(), key=kx+"|"+ky; if(MAPCACHE[key]) return MAPCACHE[key].P;
  const ok=(m,v)=>v!=null&&isFinite(v)&&(!MET[m].log||v>0);
  const raw=Object.entries(D.snap).filter(([k,d])=>d.s!=null&&ok(kx,MET[kx].get(d))&&ok(ky,MET[ky].get(d)));
  const SX=mScale(kx,raw.map(([k,d])=>MET[kx].get(d))), SY=mScale(ky,raw.map(([k,d])=>MET[ky].get(d)));
  const nx=v=>(SX.f(v)-SX.lo)/(SX.hi-SX.lo), ny=v=>(SY.f(v)-SY.lo)/(SY.hi-SY.lo);
  const P=raw.map(([k,d])=>{ const ws=d.w.slice(0,24).map(v=>v||0), pk=Math.max(...ws), vx=MET[kx].get(d), vy=MET[ky].get(d);
    return {k,n:d.n,c:d.c,y0:d.y,lm:d.lm,s:d.s,l:d.l,vx,vy,u:nx(vx),v:ny(vy),ws,pk,pkm:ws.indexOf(pk)}; });
  MAPCACHE[key]={P,SX,SY}; return P;
}
const mapScales=()=>{ mapPool(); return MAPCACHE[mAxisX()+"|"+mAxisY()]; };
const mX=u=>MM.l+Math.max(0,Math.min(1,u))*IW, mY=v=>MM.t+(1-Math.max(0,Math.min(1,v)))*IH;
const mInvX=px=>Math.max(0,Math.min(1,(px-MM.l)/IW)), mInvY=py=>Math.max(0,Math.min(1,1-(py-MM.t)/IH));
const mapOn=d=>((S.mcat||"all")==="all"||d.c===S.mcat)&&((S.mera||"all")==="all"||(d.lm&&periodOf(d.lm)===S.mera));
const mapFiltered=()=>(S.mcat||"all")!=="all"||(S.mera||"all")!=="all";
const mapIn=()=>mapPool().filter(mapOn);
function mapNear(u,v,k=20){ return mapIn().map(d=>({d,dist:Math.hypot(d.u-u,d.v-v)})).sort((a,b)=>a.dist-b.dist).slice(0,k); }
const mValAt=(axis,t)=>{ const {SX,SY}=mapScales(), Sc=axis==="x"?SX:SY; return Sc.inv(Sc.lo+t*(Sc.hi-Sc.lo)); };
function mapAxes(){
  const {SX,SY}=mapScales(), MXm=MET[mAxisX()], MYm=MET[mAxisY()], nx=v=>(SX.f(v)-SX.lo)/(SX.hi-SX.lo), ny=v=>(SY.f(v)-SY.lo)/(SY.hi-SY.lo);
  let g="";
  SX.ticks.forEach(t=>{ g+=`<line x1="${mX(nx(t))}" x2="${mX(nx(t))}" y1="${MM.t}" y2="${MAPH-MM.b}" stroke="#ECE8E1"/><text class="ax" x="${mX(nx(t))}" y="${MAPH-MM.b+(PHONE()?26:20)}" text-anchor="middle">${MXm.fmt(t)}</text>`; });
  SY.ticks.forEach(t=>{ g+=`<line x1="${MM.l}" x2="${MAPW-MM.r}" y1="${mY(ny(t))}" y2="${mY(ny(t))}" stroke="#ECE8E1"/><text class="ax" x="${MM.l-10}" y="${mY(ny(t))+4}" text-anchor="end">${MYm.fmt(t)}</text>`; });
  g+=`<text class="ax m-lo" x="${MM.l}" y="${MAPH-12}">← ${MXm.lo.toLowerCase()}</text><text class="ax" x="${MM.l+IW/2}" y="${MAPH-12}" text-anchor="middle" style="fill:#1A1A1A">X · ${MXm.label}${MXm.log?" (log scale)":""}</text><text class="ax m-hi" x="${MAPW-MM.r}" y="${MAPH-12}" text-anchor="end">${MXm.hi.toLowerCase()} →</text>`;
  g+=`<text class="ax" x="${MM.l}" y="${MM.t-18}" style="fill:#1A1A1A">Y · ${MYm.label}${MYm.log?" (log scale)":""}</text><text class="ax m-hi" x="${MM.l+8}" y="${MM.t+14}">${MYm.hi.toLowerCase()}</text><text class="ax m-lo" x="${MM.l+8}" y="${MAPH-MM.b-8}">${MYm.lo.toLowerCase()}</text>`;
  return g;
}
const metOpts=()=>Object.entries(MET).map(([k,m])=>[k,m.label]);
function mapControls(mode,P){
  /* two groups in one bar: which two numbers the map compares, and which DApps it shows */
  const X=selectFilter("mx",`X · ${MET[mAxisX()].label}`,metOpts(),mAxisX()), Y=selectFilter("my",`Y · ${MET[mAxisY()].label}`,metOpts(),mAxisY());
  const by=`<div class="m-grp"><span class="m-ctrl-h s-mono">Compare by</span>${X}<button class="m-swap" data-act="mswap" aria-label="Swap X and Y" title="Swap X and Y">⇄</button>${Y}</div>`;
  if(mode!=="place") return `<div class="m-ctrl m-bar filters">${by}</div>`;
  const cat=S.mcat||"all", era=S.mera||"all", on=v=>v!=="all"?" m-on":"";
  const C=`<span class="m-chip${on(cat)}">${selectFilter("mcat",cat==="all"?"All categories":cat,[["all","All categories"],...CATS.filter(c=>P.some(d=>d.c===c)).map(c=>[c,c])],cat)}</span>`;
  const E=`<span class="m-chip${on(era)}">${selectFilter("mera",era==="all"?"Any launch date":`Launched ${PERIOD[era]}`,[["all","Any launch date"],["before","Before Terra"],["between","Terra → Dencun"],["after","After Dencun"]],era)}</span>`;
  const reset=cat!=="all"||era!=="all"?`<button class="s-link m-reset" data-act="mreset">Reset</button>`:"";
  return `<div class="m-ctrl m-bar filters">${by}<span class="m-div" aria-hidden="true"></span><div class="m-grp"><span class="m-ctrl-h s-mono">Only show</span>${C}${E}${reset}</div></div>`;
}
function termCard(key,axis){
  const m=MET[key], ex=["uniswap-v3","opensea-seaport","lido","aave-v2"].map(k=>[k,D.snap[k]]).find(([k,d])=>d&&m.get(d)!=null);
  return `<article class="t-card"><span class="s-mono">${axis} axis</span><h4>${m.label}</h4><p class="t-plain">${m.plain}</p>
    <div class="t-scale"><span><i class="lo"></i>Low: ${m.lo.toLowerCase()}</span><span><i class="hi"></i>High: ${m.hi.toLowerCase()}</span></div>
    <p class="t-why"><b>Why it might matter.</b> ${m.why}</p>
    ${ex?`<p class="t-ex">Example: ${esc(ex[1].n)} had ${m.fmt(m.get(ex[1]))} in its third month.</p>`:""}</article>`;
}
const dotTip=d=>{ const a=MET[mAxisX()], b=MET[mAxisY()]; return esc(`${d.n}\n${d.c} · launched ${d.y0}\n${a.label}: ${a.fmt(d.vx)} · ${b.label}: ${b.fmt(d.vy)}\n${d.s?"Still a success a year later":"Not a success a year later"} · ${lifeOf(d.l).name}`); };
function vMap(mode){
  const P=mapPool(), base=P.filter(d=>d.s).length/P.length;
  let dots="", side="";
  {
    const U=S.mp||(S.mp={u:.45,v:.4});
    dots=P.map(d=>{ const on=mapOn(d); return `<circle cx="${mX(d.u)}" cy="${mY(d.v)}" r="${on?4.8:3.5}" fill="${d.s?"#9C4A26":"#CFC9BF"}" stroke="${on&&mapFiltered()&&!d.s?"#6F6B64":"#FBFAF7"}" stroke-width="${on&&mapFiltered()?1.2:.8}" opacity="${on?1:.15}" data-tip="${dotTip(d)}"/>`; }).join("");
    side=`<div class="m-side m-top" id="m-readout">${placeReadout(U)}</div><div class="srt-dots m-topdots" aria-label="Your DApp and the three closest">${[0,1,2,3].map(i=>`<button class="${i?"":"on"}" data-act="mtdot" data-i="${i}" aria-label="${i?"Closest "+i+" of 3":"Your DApp"}"></button>`).join("")}</div>`;
  }
  const you = mode==="place" ? `<g id="m-you"></g>` : "";
  return `<main class="study s-wrap">
    <h1 class="s-qtitle">${mode==="game"?"Could you have spotted the winners?":"Not live yet? Find the DApps that looked like yours."}</h1>
    ${mode==="place"?`<p class="s-lede">Place your DApp's third-month numbers on the map and see which DApps sat closest, and how they were doing a year later.</p>`:""}
    ${mapControls(mode,P)}
    ${mode==="place"?side:""}
    <div class="m-wrap ${mode}"><figure class="s-fig m-fig"><svg id="mapsvg" class="m-svg ${mode}" viewBox="0 0 ${MAPW} ${MAPH}" role="img" aria-label="DApps by ${MET[mAxisX()].label} and ${MET[mAxisY()].label} in their third month">${mapAxes()}${dots}<g id="m-links"></g>${you}</svg><div class="s-note m-notes"><p><span class="s-mono">How to read</span><span class="m-legend"><span><i class="m-key" style="background:#9C4A26"></i>Success a year later</span><span><i class="m-key" style="background:#CFC9BF"></i>Not a success</span></span></p></div>
      </figure>
      ${mode==="place"?"":side}</div>
    ${mode==="place"?"":`<p class="t-src">${P.length} DApps launched 2020–2024 with a known outcome; ${P.filter(d=>d.s).length} were still a success a year later (${pct(base)}). Every value is from each DApp's third month. Neighbours are matched on these two measures only: this describes the past, not a forecast.</p>`}</main>`;
}
function placeReadout(U){
  const N=mapNear(U.u,U.v), mix={}; N.forEach(x=>mix[x.d.l]=(mix[x.d.l]||0)+1);
  const A=MET[mAxisX()], B=MET[mAxisY()];
  const order=["sustained","gradual_decline","flash","never_adopted","other"], top=order.slice().sort((a,b)=>(mix[b]||0)-(mix[a]||0))[0];
  const bar=`<div class="m-mix">${order.filter(k=>mix[k]).map(k=>`<i style="flex:${mix[k]};background:${LIFE[k].col}" data-tip="${LIFE[k].name}: ${mix[k]} of ${N.length}"></i>`).join("")}</div>`;
  const spark=d=>{ const W=280,H=48, mx=d.pk||1; return `<svg viewBox="0 0 ${W} ${H}" class="m-spark"><polyline points="${d.ws.map((v,i)=>`${i/23*W},${H-2-v/mx*(H-6)}`).join(" ")}" fill="none" stroke="#5A5650" stroke-width="2"/><line x1="${2/23*W}" x2="${2/23*W}" y1="0" y2="${H}" stroke="#1A1A1A" stroke-dasharray="2 3"/>${d.ws.map((v,i)=>`<g class="sp-h" data-tip="${esc(`${d.n}, month ${i}${i===2?" (the month on the map)":""}\n${fmtN(v)} active wallets\n${pct(v/mx)} of its peak`)}"><rect x="${(i-.5)/23*W}" y="0" width="${W/23}" height="${H}" fill="transparent"/><circle cx="${i/23*W}" cy="${H-2-v/mx*(H-6)}" r="3.5" fill="#1A1A1A"/></g>`).join("")}</svg>`; };
  const card=x=>{ const d=x.d, L=lifeOf(d.l), big=D.dapps[d.k];
    return `<article class="m-card"><b class="m-cname">${esc(d.n)}</b>
      <span class="s-mono m-cdate">${d.c} · ${d.lm?monthLabel(d.lm):d.y0}</span>
      <span class="m-clife"><i style="background:${L.col}"></i>${L.name}</span>
      ${spark(d)}
      <dl class="m-xy"><dt>X · ${A.label}</dt><dd>${A.fmt(d.vx)}</dd><dt>Y · ${B.label}</dt><dd>${B.fmt(d.vy)}</dd></dl>
      <p class="m-res ${d.s?"win":""}">${d.s?"Still a success a year later":"Not a success a year later"}</p>
      ${big?`<button class="s-link m-cmp" data-cmpwith="${d.k}" title="Compare ${esc(d.n)} with others" aria-label="Compare ${esc(d.n)} with others"><span class="m-cmpt">Compare ›</span><svg class="m-cmpic" viewBox="0 0 20 32" aria-hidden="true"><path d="M10 1 L19 16 L10 21.5 L1 16 Z M1 18.5 L10 31 L19 18.5 L10 24 Z" stroke="#1A1A1A" stroke-width="1.3" stroke-linejoin="round"/><path d="M10 1 V21.5 M1 16 L10 11.5 L19 16" fill="none" stroke="#1A1A1A" stroke-width="1.1" stroke-linejoin="round"/></svg></button>`:`<span class="s-link m-cmp" aria-hidden="true" style="visibility:hidden">Compare ›</span>`}</article>`; };
  if(!N.length) return `<span class="s-mono">Your DApp</span><p>No DApps match these filters.</p>`;
  return `<div class="m-sum"><span class="s-mono">Your DApp</span><h3><span class="m-sv">${A.fmt(mValAt("x",U.u))} <button class="term" data-act="gterm" data-k="${mAxisX()}" data-axis="X" aria-label="What ${A.label.toLowerCase()} means">${A.label.toLowerCase()}</button></span><span class="m-sv">${B.fmt(mValAt("y",U.v))} <button class="term" data-act="gterm" data-k="${mAxisY()}" data-axis="Y" aria-label="What ${B.label.toLowerCase()} means">${B.label.toLowerCase()}</button></span></h3>
    <div class="m-score"><b>${pct(N.filter(x=>x.d.s).length/N.length)}</b><span>of the ${N.length} nearest${(S.mcat||"all")!=="all"?` ${S.mcat}`:""} DApps${(S.mera||"all")!=="all"?` launched ${PERIOD_IN[S.mera]}`:""} were a success a year later (${mapFiltered()?"this group":"all"}: ${pct(mapIn().filter(d=>d.s).length/Math.max(1,mapIn().length))})</span></div>
    <p class="m-nb">Over their whole history, most of them were <b>${LIFE[top].name.toLowerCase()}</b> (${mix[top]} of ${N.length}).</p>
    <div class="m-line">${order.filter(k=>mix[k]).map(k=>`<i style="flex:${mix[k]};background:${LIFE[k].col}" data-tip="${LIFE[k].name}: ${mix[k]} of ${N.length}"></i>`).join("")}</div>
    <p class="m-linekey">${order.filter(k=>mix[k]).map(k=>`<span><i style="background:${LIFE[k].col}"></i>${LIFE[k].name} <b>${mix[k]}</b></span>`).join("")}</p></div>
    <div class="m-three"><span class="s-mono m-near">The three closest</span><div class="m-cards">${N.slice(0,3).map(card).join("")}</div></div>`;
}
/* drawing the crosshair and links without redrawing the page, so dragging stays smooth */
function mapDrawYou(){
  const g=document.getElementById("m-you"), L=document.getElementById("m-links"); if(!g) return;
  const U=S.mp, x=mX(U.u), y=mY(U.v), N=mapNear(U.u,U.v);
  L.innerHTML=N.slice(0,3).map(n=>`${orbArc(x,y,mX(n.d.u),mY(n.d.v))}<circle cx="${mX(n.d.u)}" cy="${mY(n.d.v)}" r="9" fill="none" stroke="#1A1A1A" stroke-width="1.5"/>`).join("");
  g.innerHTML=`<line x1="${x}" x2="${x}" y1="${MM.t}" y2="${MAPH-MM.b}" stroke="#1A1A1A" stroke-dasharray="2 4"/><line x1="${MM.l}" x2="${MAPW-MM.r}" y1="${y}" y2="${y}" stroke="#1A1A1A" stroke-dasharray="2 4"/>
    <circle cx="${x}" cy="${y}" r="13" fill="#1A1A1A" fill-opacity=".08" stroke="#1A1A1A" stroke-width="2"/><circle cx="${x}" cy="${y}" r="4" fill="#1A1A1A"/>
    <text class="axl" x="${x+18}" y="${y-14}" fill="#1A1A1A">You</text>`;
  const R=document.getElementById("m-readout"); if(R) R.innerHTML=placeReadout(U);
}
/* orbit arc (DESIGN.md accent line): a thin Light Signal Orange curve between two points, bowed to one side */
function orbArc(x1,y1,x2,y2){ const mx=(x1+x2)/2, my=(y1+y2)/2, dx=x2-x1, dy=y2-y1, L=Math.hypot(dx,dy)||1, k=Math.min(60,L*.28);
  return `<path class="orb" pathLength="1" d="M${x1.toFixed(1)} ${y1.toFixed(1)} Q${(mx-dy/L*k).toFixed(1)} ${(my+dx/L*k).toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}" fill="none" stroke="#F37338" stroke-width="1.6"/>`; }
function mapInit(){
  const svg=document.getElementById("mapsvg"); if(!svg) return;
  const pt=e=>{ const p=svg.createSVGPoint(); p.x=e.clientX; p.y=e.clientY; return p.matrixTransform(svg.getScreenCTM().inverse()); };
  if(svg.classList.contains("place")){
    if(!S.mp||S.mp.u==null) S.mp={u:.45,v:.4};
    mapDrawYou(); let drag=false;
    const move=e=>{ const q=pt(e); S.mp={u:mInvX(q.x), v:mInvY(q.y)}; mapDrawYou(); };
    svg.addEventListener("pointerdown",e=>{ drag=true; svg.classList.add("dragging"); svg.setPointerCapture(e.pointerId); move(e); });
    svg.addEventListener("pointermove",e=>{ if(drag) move(e); });
    svg.addEventListener("pointerup",()=>{ drag=false; svg.classList.remove("dragging"); mapDrawYou(); });
    /* hover any DApp: arcs to the three DApps sitting closest to it on this map */
    const orb=document.createElementNS("http://www.w3.org/2000/svg","g"); orb.id="m-orb"; svg.insertBefore(orb,document.getElementById("m-links"));
    const dots=[...svg.querySelectorAll("circle[data-tip]")].filter(c=>!c.closest("#m-links,#m-you"));
    svg.addEventListener("mouseover",e=>{ if(drag) return; const c=e.target; if(!dots.includes(c)) return; const x=+c.getAttribute("cx"), y=+c.getAttribute("cy");
      const near=dots.filter(o=>o!==c).map(o=>({o,d:Math.hypot(+o.getAttribute("cx")-x,+o.getAttribute("cy")-y)})).sort((a,b)=>a.d-b.d).slice(0,3);
      orb.innerHTML=near.map(n=>orbArc(x,y,+n.o.getAttribute("cx"),+n.o.getAttribute("cy"))).join("")+`<circle cx="${x}" cy="${y}" r="9" fill="none" stroke="#F37338" stroke-width="1.6"/>`; });
    svg.addEventListener("mouseout",e=>{ if(dots.includes(e.target)) orb.innerHTML=""; });
  } else {
    svg.addEventListener("click",e=>{ const G=S.gm; if(!G||G.phase!=="play") return; const a=G.picks[G.lv]; if(a.length>=MPICKS) return; const q=pt(e);
      const best=mapPool().filter(GLEVELS[G.lv].test).filter(d=>!a.includes(d.k)).map(d=>({d,dd:Math.hypot(mX(d.u)-q.x,mY(d.v)-q.y)})).sort((x,y)=>x.dd-y.dd)[0];
      if(best && best.dd<16){ a.push(best.d.k); if(a.length>=MPICKS&&G.ts){ G.el+=Date.now()-G.ts; G.ts=null; } const y=window.scrollY; render(); window.scrollTo(0,y); } });
  }
}
