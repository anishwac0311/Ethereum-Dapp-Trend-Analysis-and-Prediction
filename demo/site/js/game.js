/* =====================================================================
   The game. Two ways to play, chosen on a small start screen:
     Learn: every level brings two new measures (X and Y), introduced on a card before you play.
     Guess: the same three levels on one familiar map (wallets × returning share), against the clock.
   Each pick turns into a card: who it was, its X and Y, and what happened a year later.
   Finished games go on a leaderboard kept in this browser (score first, then time).
   ===================================================================== */
const MPICKS=3;
/* levels use the research eras; each game draws one category with enough DApps (12–40, 3+ that lasted) in one era */
const ERA_NOTE={before:"Before Terra (2020 – Apr 2022): DeFi summer and the 2021 bull market, when every category grew.",
  between:"Terra → Dencun (May 2022 – Feb 2024): Terra and FTX collapsed, yet DApp wallets held steady at about 1.4M a month.",
  after:"After Dencun (Mar 2024 – 2025): blobs cut layer-2 fees, and DApp wallets fell by half, from a 2.3M peak to 1.1M."};
const G_DRAWS=[["DEX","before"],["DEX","between"],["Infrastructure","before"],["Infrastructure","between"],["NFT","before"],["Other","after"]];
const eraOf=d=>d.lm?periodOf(d.lm):null;
function makeLevels(cat,era){ return [
  {short:`${cat} · ${PERIOD[era]}`, title:"Size or stickiness?", scope:`${cat==="Other"?"DApp from the Other category,":cat+" DApp"} launched ${PERIOD_IN[era]}`, lesson:"Is being big enough, or do users need to come back?", era:ERA_NOTE[era], test:d=>d.c===cat&&eraOf(d)===era, ax:["wallets","returning"]},
  {short:`${cat} · every era`, title:"Habit or a few whales?", scope:`${cat==="Other"?"DApp from the Other category":cat+" DApp"}, from any era`, lesson:"Do apps people use again and again last, or ones carried by a handful of big wallets?", era:"All three eras at once: the bull market, the Terra and FTX crash, then cheaper fees after Dencun.", test:d=>d.c===cat, ax:["txpw","whale"]},
  {short:"Every DApp", title:"Do apps that work together last?", scope:"DApp, from any category and era", lesson:"Gas shows how heavy the use is; apps per transaction shows how often it is used together with other apps.", era:"Every category in every era.", test:()=>true, ax:["gas","apps"]}]; }
let GLEVELS=makeLevels("DEX","before");
const GMODES={learn:{name:"Game", line:"Each level brings two new measures and explains them first. Then the clock starts."}};
const fmtTime=ms=>{ const s=Math.floor(ms/1000); return `${Math.floor(s/60)}:${String(s%60).padStart(2,"0")}`; };
const gElapsed=()=>{ const G=S.gm; if(!G) return 0; return (G.el||0)+(G.ts?Date.now()-G.ts:0); };
function lbLoad(){ try{ return JSON.parse(localStorage.getItem("dapp-booth-board")||"[]"); }catch(_){ return []; } }
const lbSort=a=>a.slice().sort((x,y)=>(y.pts??0)-(x.pts??0)||x.ms-y.ms);
const lbDay=()=>new Date().toISOString().slice(0,10);
/* keep the best 50 of all time plus every score from today (so a new low score is never dropped while today's board is shown) */
function lbSave(rows){ const all=lbSort(rows), top=all.slice(0,50), td=all.filter(r=>r.at===lbDay()&&!top.includes(r)).slice(0,100);
  try{ localStorage.setItem("dapp-booth-board",JSON.stringify(top.concat(td))); }catch(_){} }
/* Home: today's best three on a podium, 2 · 1 · 3, the winner's block tallest; an empty step shows a dash */
function podium(){ const rows=lbSort(lbLoad().filter(r=>r.at===lbDay())).slice(0,3);
  const step=i=>{ const r=rows[i]; return `<div class="pd-s pd-${i+1}${r?"":" pd-none"}"><b>${r?esc(r.name):"—"}</b><span>${r?`${r.pts??0} pts · ${fmtTime(r.ms)}`:"open"}</span><div class="pd-b"><span>${i+1}</span></div></div>`; };
  return `<div class="pd" aria-label="Top three today">${step(1)}${step(0)}${step(2)}</div>`; }
/* today's best games, for the Wall: rank, name, points, time */
function topToday(n,fill){ const rows=lbSort(lbLoad().filter(r=>r.at===lbDay())).slice(0,n);
  /* fill: draw every place 1..n, empty ones as a dash, so the board shows its ten places from the start */
  if(fill) return `<ol class="tb-top">${[...Array(n).keys()].map(i=>{ const r=rows[i]; return r?`<li><span class="s-mono">${i+1}</span><b>${esc(r.name)}</b><span>${r.pts??0} pts</span><span class="s-mono">${fmtTime(r.ms)}</span></li>`:`<li class="tb-open"><span class="s-mono">${i+1}</span><b>—</b><span></span><span></span></li>`; }).join("")}</ol>`;
  return rows.length?`<ol class="tb-top">${rows.map((r,i)=>`<li><span class="s-mono">${i+1}</span><b>${esc(r.name)}</b><span>${r.pts??0} pts</span><span class="s-mono">${fmtTime(r.ms)}</span></li>`).join("")}</ol>`:`<p class="tb-empty">No games yet today. Be the first name here.</p>`; }
const gRate=i=>{ const all=Object.values(D.snap).filter(d=>d.s!=null&&GLEVELS[i].test(d)); return all.filter(d=>d.s).length/Math.max(1,all.length); };
const gWorth=i=>Math.round(100*(1-gRate(i)));
const gPts=G=>G.picks.reduce((t,a,i)=>t+a.filter(k=>D.snap[k]&&D.snap[k].s).length*gWorth(i),0);

function gStart(mode){ const dr=G_DRAWS[Math.floor(Math.random()*G_DRAWS.length)]; GLEVELS=makeLevels(dr[0],dr[1]); S.gm={draw:dr,mode,phase:mode==="learn"?"intro":"play",lv:0,picks:GLEVELS.map(()=>[]),el:0,ts:mode==="learn"?null:Date.now(),ax:mode==="learn"?GLEVELS[0].ax:["wallets","returning"],id:null}; }
function gPickCard(d,G,i){
  const A=MET[G.ax[0]], B=MET[G.ax[1]], L=lifeOf(d.l), cat=d.c==="Infrastructure"?"Infra":d.c;
  return `<article class="g-card2 ${d.s?"win":"miss"}"><div class="g2-hd"><span class="g-num">${i+1}</span><b class="g2-name" title="${esc(d.n)}">${esc(d.n)}</b></div>
    <div class="g2-row"><span class="s-mono">${cat} · ${d.lm?monthLabel(d.lm):d.y0}</span><span class="m-tag">${d.s?"Success":"Not a success"}</span></div>
    <div class="g2-xy"><span><em>X</em>${A.fmt(d.vx)}</span><span><em>Y</em>${B.fmt(d.vy)}</span></div></article>`;
}
/* menu illustration: a field of grey dots, three picked, one circled by an orange orbit (DESIGN.md accent arc) */
const GART=(()=>{ const pts=[[40,150],[70,120],[96,160],[120,96],[150,134],[176,70],[204,112],[230,84],[258,128],[286,58],[312,100],[338,74],[110,184],[196,170],[270,170],[60,190],[330,150],[150,60]];
  const pick=[5,9,7];
  return `<svg viewBox="0 0 380 220" aria-hidden="true"><line x1="24" y1="204" x2="368" y2="204" stroke="#1A1A1A"/><line x1="24" y1="204" x2="24" y2="20" stroke="#1A1A1A"/>
    <path d="M150 70 C 210 -10, 360 10, 300 66" fill="none" stroke="#F37338" stroke-width="1.5"/><circle cx="286" cy="58" r="22" fill="none" stroke="#F37338" stroke-width="1.5"/>
    ${pts.map(([x,y],i)=>`<circle cx="${x}" cy="${y}" r="${pick.includes(i)?8:6}" fill="${pick.includes(i)?"#1A1A1A":"#D1CDC7"}"/>`).join("")}
    <text x="30" y="30" style="font:500 11px 'JetBrains Mono',monospace;fill:#696969">Y ?</text><text x="344" y="196" style="font:500 11px 'JetBrains Mono',monospace;fill:#696969">X ?</text></svg>`; })();
function vGame(){
  const G=S.gm;
  if(!G||G.phase==="menu"){
    return `<main class="study s-wrap">
      <h1 class="s-qtitle">Can you spot the winners?</h1>
      <p class="g-lede s-lede">Practise reading early numbers. Each dot is a real DApp in its third month: pick the ones that were still a success a year later.</p>
      <div class="g-start"><div class="g-hero"><div class="g-art">${GART}</div><b>Three levels, nine picks</b><p>${GMODES.learn.line}</p>
        <ol class="g-steps">${GLEVELS.map((L,i)=>`<li><span class="g-num g-lvn">${i+1}</span><span class="g-stitle">${L.title}</span><span class="s-mono">Level ${i+1}</span></li>`).join("")}</ol>
        <button class="g-startbtn" data-gmode="learn">Start the game →</button></div></div></main>`;
  }
  G.ax=G.mode==="learn"?GLEVELS[G.lv].ax:["wallets","returning"];
  const P=mapPool(), lv=GLEVELS[G.lv], pool=P.filter(lv.test), picks=G.picks[G.lv].filter(k=>P.some(d=>d.k===k)), done=picks.length>=MPICKS, picked=new Set(picks);
  const find=k=>P.find(x=>x.k===k), hits=a=>a.filter(k=>{ const d=find(k); return d&&d.s; }).length, over=G.lv===GLEVELS.length-1&&done;
  const total=G.picks.reduce((t,a)=>t+hits(a),0), A=MET[G.ax[0]], B=MET[G.ax[1]];
  const order=d=>pk2i[d.k]!=null?2:lv.test(d)?1:0, pk2i={}; picks.forEach((k,i)=>pk2i[k]=i);
  const dots=P.slice().sort((a,b)=>order(a)-order(b)).map(d=>{ const inL=lv.test(d), i=pk2i[d.k], tip=!inL?"Not in this level":(i!=null||done)?dotTip(d):"A candidate: click to pick it", x=mX(d.u), y=mY(d.v);
    if(i!=null) return `<g data-tip="${tip}"><circle cx="${x}" cy="${y}" r="11" fill="${d.s?"#9C4A26":"#FBFAF7"}" stroke="#1A1A1A" stroke-width="2.5"/><circle cx="${x+11}" cy="${y-11}" r="8" fill="#1A1A1A"/><text x="${x+11}" y="${y-7.5}" text-anchor="middle" style="font:600 10px 'JetBrains Mono',monospace;fill:#F5F3EE">${i+1}</text></g>`;
    if(!inL) return `<circle cx="${x}" cy="${y}" r="2.5" fill="#CFC9BF" opacity=".35" data-tip="${tip}"/>`;
    if(done) return `<circle cx="${x}" cy="${y}" r="5" fill="${d.s?"#9C4A26":"#FBFAF7"}" stroke="${d.s?"#9C4A26":"#8E8A82"}" stroke-width="1.2" data-tip="${tip}"/>`;
    return `<circle class="g-cand" cx="${x}" cy="${y}" r="5.5" fill="#6F6B64" data-tip="${tip}"/>`; }).join("");
  const board=GLEVELS.map((L,i)=>`<li class="${i===G.lv?"cur":""}"><span class="s-mono">L<span class="lv-w">evel </span>${i+1}</span><span>${L.short}</span><b>${i<G.lv||i===G.lv&&G.phase!=="intro"?`${hits(G.picks[i])*gWorth(i)}`:"–"}</b>${i===G.lv&&G.phase!=="done"?`<i class="g-lvtime" id="g-time-m">${fmtTime(gElapsed())}</i>`:""}</li>`).join("");
  let side;
  /* the task reads left to right above the map, for the intro and while playing */
  const taskbar=G.phase==="done"?"":done?`<div class="g-taskbar g-donebar"><span class="s-mono">Level ${G.lv+1} done</span>
      <p class="g-task">${hits(picks)} of ${MPICKS} lasted · <b>+${hits(picks)*gWorth(G.lv)} points</b> · ${fmtTime(gElapsed())} so far. ${over?"Nice work, that was the last level.":"Keep going!"}</p>
      <button class="s-cardbtn g-donego" data-act="${over?"gend":"gnext"}">${over?"See my score →":"Next level →"}</button></div>`:`<div class="g-taskbar"><span class="s-mono">Your task</span>
      <p class="g-task">Pick three dark dots, reading <button class="term" data-act="gterm" data-k="${G.ax[0]}" data-axis="X" aria-label="What ${A.label.toLowerCase()} means">${A.label.toLowerCase()}</button> and <button class="term" data-act="gterm" data-k="${G.ax[1]}" data-axis="Y" aria-label="What ${B.label.toLowerCase()} means">${B.label.toLowerCase()}</button> together.</p>
</div>`;
  let fin="";
  /* the finish card sits over the map, like "Your turn" at the start */
  if(G.phase==="done"){ side=""; fin=`<div class="g-finhead"><span class="s-mono">Finished</span><button class="g-replay" data-act="gmenu" aria-label="Play again" title="Play again"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 12a8 8 0 1 1-2.34-5.66" fill="none" stroke="#1A1A1A" stroke-width="1.8" stroke-linecap="round"/><path d="M20 4v5h-5" fill="none" stroke="#1A1A1A" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button></div><h3>${gPts(G)} points in ${fmtTime(G.el)}</h3><p>${total} of ${MPICKS*GLEVELS.length} picks were a success.</p>
      ${G.id?"":`<label class="g-name"><span class="s-mono">Your name for the board</span><span class="g-namebox"><input id="g-name" maxlength="14" placeholder="e.g. Ana" autocomplete="off"><button class="g-namego" data-act="gsave" aria-label="Save my score">→</button></span></label>`}
      ${G.id?(()=>{ const today=lbSort(lbLoad().filter(r=>r.at===lbDay())), i=today.findIndex(r=>r.id===G.id);
        return `<p class="g-rankline">${i>=0?`You are <b class="o-you">#${i+1}</b> of ${today.length} today${i<3?", on the podium on Home":""}.`:"Saved."}</p><button class="fold-more g-seetop" data-go="wall"><span>See today's top scores</span><i>›</i></button>`; })():""}
`; }
  /* while playing: no separate time/score box; the level tiles carry the clock and the points */
  if(G.phase!=="done") side=`<div class="m-side g-playside">
      <div class="g-act">${done?(over?`<button class="s-cardbtn" data-act="gend">See my score →</button>`:`<button class="s-cardbtn" data-act="gnext">Next level →</button>`):""}</div>
      <div class="g-cards">${[0,1,2].map(i=>picks[i]?gPickCard(find(picks[i]),G,i):`<div class="g-card g-empty"><span class="g-num">${i+1}</span><span class="g-name">Pick ${i+1}: click a dark dot</span></div>`).join("")}</div>
</div>`;
  return `<main class="study s-wrap g-page">
    <div class="g-titlerow"><h1 class="s-qtitle">${lv.title}</h1><button class="g-quit" data-act="gmenu" aria-label="Quit the game" title="Quit the game"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="#CF4500" stroke-width="1.8" stroke-linecap="round"/></svg></button></div>
    ${taskbar}<ol class="g-levels">${board}</ol>
    <div class="m-wrap g-${G.phase}"><figure class="s-fig m-fig"><figcaption class="g-cap s-mono">${lv.short} · ${pool.length} DApps</figcaption><svg id="mapsvg" class="m-svg game ${G.phase}" viewBox="0 0 ${MAPW} ${MAPH}" role="img" aria-label="Level map">${mapAxes()}${dots}</svg>${G.phase==="intro"?`<div class="g-over"><b>Your turn</b><span>X · ${A.label} &nbsp;×&nbsp; Y · ${B.label}</span><p class="g-rule">Go with your gut.</p><button class="s-cardbtn g-go" data-act="gplay">Let\'s go →</button></div>`:""}${fin?`<div class="g-over g-fin">${fin}</div>`:""}<div class="s-note m-notes"><p><span class="s-mono">How to read</span><span><i class="m-key" style="background:#6F6B64"></i>This level <span class="g-num g-num-s">1</span>Your pick <i class="m-key" style="background:#9C4A26"></i>Success <i class="m-key" style="background:#FBFAF7;border:1px solid #1A1A1A"></i>Not a success <i class="m-key" style="background:#CFC9BF;opacity:.5"></i>Other levels</span></p></div></figure>
      ${side}</div>
    <section class="t-learn"><h2>${G.mode==="learn"?"This level's two measures":"The two measures"}</h2><div class="t-cards">${termCard(G.ax[0],"X")}${termCard(G.ax[1],"Y")}</div></section></main>`;
}
setInterval(()=>{ ["g-time","g-time-m"].forEach(id=>{ const el=document.getElementById(id); if(el) el.textContent=fmtTime(gElapsed()); }); },250);
/* a game left alone stops itself: one minute with no tap, click or key, or ten minutes of play in all, sends the screen back to the game's start, unsaved and without a message */
let gLastInput=Date.now();
["pointerdown","keydown","wheel","touchstart"].forEach(ev=>addEventListener(ev,()=>{ gLastInput=Date.now(); },{passive:true,capture:true}));
setInterval(()=>{ const G=S.gm; if(S.view!=="game"||!G||G.phase==="menu"||G.phase==="done") return;
  /* also stops once a game has run for ten minutes in all */
  if(Date.now()-gLastInput>=60000||gElapsed()>=600000){ S.gm=null; document.querySelectorAll(".i-sheet").forEach(e=>e.remove()); document.body.classList.remove("sheet-open"); render(); window.scrollTo(0,0); } },1000);
