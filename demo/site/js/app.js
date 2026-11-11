/* ---------- render, page turns ---------- */
/* a bottom sheet for any content: Learn more on the sorts, and the notes and lists folded away on phones */
/* close sheets with their exit animation, then run done (at once under reduced motion) */
function sheetOut(els,done){ els=[...els].filter(e=>!e.classList.contains("out")); if(!els.length||matchMedia("(prefers-reduced-motion: reduce)").matches){ done(); return; }
  let fin=false; const end=()=>{ if(fin) return; fin=true; done(); };
  els.forEach(e=>{ e.classList.add("out"); const b=e.querySelector(".c-sbody"); if(b) b.addEventListener("animationend",end,{once:true}); }); setTimeout(end,320); }
function closeISheets(){ const els=document.querySelectorAll(".i-sheet"); sheetOut(els,()=>{ els.forEach(e=>e.remove()); if(!document.querySelector(".c-sheet:not(.out)")) document.body.classList.remove("sheet-open"); }); }
function closeCSheet(){ sheetOut(document.querySelectorAll(".c-sheet:not(.i-sheet)"),()=>{ if(!S.csheet) return; S.csheet=null; const y=window.scrollY; render(); window.scrollTo(0,y); }); }
function openSheet(html,extra=""){ const el=document.createElement("div"); el.className="c-sheet i-sheet "+extra; el.setAttribute("role","dialog"); el.setAttribute("aria-modal","true");
  el.innerHTML=`<button class="c-sscrim" data-act="isheet-x" aria-label="Close" tabindex="-1"></button><div class="c-sbody"><div class="c-shead"><span></span><button class="c-sx" data-act="isheet-x" aria-label="Close">✕</button></div><div class="i-body">${html}</div></div>`;
  document.body.appendChild(el); document.body.classList.add("sheet-open"); }
/* phones: long notes under charts and the question / path lists fold into one row that opens the sheet */
/* every chart gets a short title, like "The same model in each era": its accessible name, in small grey caps on the top row, left of "Read more ›" */
function movePicker(){
  /* walks: the "follow another …" picker moves onto the chart's top row, left of "How to read ›", as "Following Lido ▾" */
  const pick=document.querySelector("main .w-pickup"), fig=document.querySelector("main .has-ic"), det=pick&&pick.querySelector(".w-more");
  if(pick&&fig&&det&&!fig.querySelector(".w-more")){ const who=pick.querySelector("p b"), row=fig.querySelector(":scope>.fig-top");
    det.querySelector("summary").innerHTML=`Following <b>${who?esc(who.textContent):""}</b>`;
    /* the title and Read more keep the top row; the picker sits on its own line under it */
    const prow=document.createElement("div"); prow.className="fig-pick"; prow.append(det); if(row) row.after(prow); else fig.prepend(prow);
    pick.classList.add("folded"); }
}
function titleCharts(){
  /* charts with their own label (the era tables): the label and "Read more ›" share one row */
  document.querySelectorAll("main .s-erafig").forEach(fig=>{ const ic=fig.querySelector(":scope>.fold-ic"), lab=fig.querySelector(":scope>.s-figlab"); if(!ic||!lab||fig.querySelector(":scope>.fig-top")) return; const row=document.createElement("div"); row.className="fig-top"; lab.before(row); row.append(lab,ic); });
  document.querySelectorAll("main figure.s-fig:not(.m-fig)").forEach(fig=>{ if(fig.querySelector(".s-figlab,.fig-title")) return;
    const sv=fig.querySelector("svg[aria-label],table[aria-label]"); if(!sv) return; /* a chart, or a ranked table */
    const t=document.createElement("span"); t.className="s-mono fig-title"; t.textContent=sv.getAttribute("aria-label");
    const ic=fig.querySelector(":scope>.fold-ic"); if(ic){ const row=document.createElement("div"); row.className="fig-top"; row.append(t,ic); fig.prepend(row); } else fig.prepend(t); });
}
function phoneFold(){ const DESK=!PHONE(); if(DESK&&!["qpage","book","pick","game","method"].includes(S.view)) return; if(DESK){ const mn=document.querySelector("main")||document.querySelector("section.sheet"); if(mn) mn.classList.add("dfold"); }
  const fold=(el,title)=>{ if(el.classList.contains("folded")) return;
    const warn=/Small sample/.test(el.textContent)?`<em>Small sample</em>`:"";
    const b=document.createElement("button"); b._src=el; b.className="fold-more"; b.dataset.act="fold"; b.dataset.title=title; b.innerHTML=`<span>${title}${warn}</span><i>›</i>`; el.before(b); el.classList.add("folded");
    /* a chart's own note: a short "Read more ›" on its own line above the chart, at the right */
    const fig=el.closest("figure.s-fig,.s-erafig");
    /* every chart, maps and small-sample notes included: "Read more ›" at the top right (the warning is inside the note) */
    if(fig&&/^How to read/.test(title)&&!fig.querySelector(".g-cap")){ b.className="fold-ic"; b.setAttribute("aria-label",title); b.innerHTML=`<span>Read more</span><i>›</i>`; fig.classList.add("has-ic"); fig.prepend(b); } };
  /* game: the two measures open from their own words in the task line (data-act="gterm"), so the map keeps no "Read more" and its caption has the whole row */
  const tl=document.querySelector("main .t-learn"), gnote=document.querySelector("main .m-wrap[class*='g-'] .s-note");
  if(tl&&gnote){ gnote.remove(); tl.classList.add("folded"); }
  /* a note that is only a short colour key (Neighbours: success or not) stays under the chart: a sheet for two lines is not worth the tap */
  document.querySelectorAll("main .s-note").forEach(n=>{ if(n.textContent.replace(/^How to read/,"").trim().length<60){ n.classList.add("s-note-key"); return; } fold(n,n.closest(".s-erafig")?"How to read this table":"How to read this chart"); });
  /* walks: the progress strip in the eyebrow opens Your path (your choices so far). Question pages: the strip only shows where you are;
     "← All" and the row at the end already cover the six questions, so it opens nothing */
  document.querySelectorAll("main .s-trail").forEach(n=>{ n.classList.add("folded");
    const lab=document.querySelector("main .s-crumb>span.s-mono"); if(!lab) return;
    const onQ=S.view==="qpage", title=onQ?"All six questions":"Your path";
    const b=document.createElement(onQ?"span":"button"); b.className="s-crumbbtn"+(onQ?" pg-static":"");
    if(onQ) b.setAttribute("role","img"); else { b._src=n; b.dataset.act="fold"; b.dataset.title=title; }
    /* a small progress strip instead of "1 of 5 Moment": done steps ink, this step an orange flag, the rest grey.
       On question pages the six questions, the same way: the ones before this one ink. */
    const P=onQ?SQ.map(x=>x.q):pages(), cur=onQ?P.indexOf(S.sq):S.idx, seen=S.qseen||[];
    /* by position only, so the strip looks the same however you got here: before this one ink, this one the orange mark, after it grey */
    const st=i=>i===cur?"now":i<cur?"done":"";
    b.setAttribute("aria-label",`${onQ?"Question":"Step"} ${cur+1} of ${P.length}: ${QNAME[P[cur]]||""}${onQ?"":". "+title}`);
    const ETH_NOW=`<svg viewBox="0 0 20 32" aria-hidden="true"><path d="M10 1 L19 16 L10 21.5 L1 16 Z M1 18.5 L10 31 L19 18.5 L10 24 Z" fill="#CF4500"/></svg>`;
    b.innerHTML=`<span class="pg-strip" aria-hidden="true">${P.map((_,i)=>st(i)==="now"?`<span class="pg-seg now">${ETH_NOW}</span>`:`<span class="pg-seg ${st(i)}"></span>`).join("")}</span>`;
    lab.classList.add("pg-lab"); lab.replaceChildren(b); });
  document.querySelectorAll("main .t-learn:not(.folded)").forEach(n=>fold(n,(n.querySelector("h2")||{}).textContent||"The two measures"));
  document.querySelectorAll(".sheet .m-rules").forEach(n=>fold(n,"Notes and limits"));
  /* Method: "Notes and limits ›" moves up to a row of its own above the tab's cards, at the right (the tab has no section heading) */
  document.querySelectorAll(".sheet .m-rules.folded").forEach(n=>{ const b=n.previousElementSibling; if(!b||!b.classList.contains("fold-more")||b.dataset.moved) return; const sh=n.closest(".sheet"), lede=sh&&sh.querySelector(":scope>.s-lede"), first=lede&&lede.nextElementSibling; if(!first) return; b.dataset.moved="1"; b._src=n; const row=document.createElement("div"); row.className="s-sec has-note m-notesrow"; first.before(row); row.append(b); });
  /* game map: its caption ("NFT · Before Terra · 16 DApps") and a "Read more ›" share the top row, like the other charts */
  const gfig=document.querySelector("main .m-fig .g-cap")?.closest(".m-fig");
  if(gfig&&!gfig.querySelector(".fig-top")){ const cap=gfig.querySelector(".g-cap"), row=document.createElement("div"); row.className="fig-top g-captop";
    const fm=gfig.querySelector(":scope>.fold-more"); if(fm){ fm.className="fold-ic"; fm.innerHTML=`<span>Read more</span><i>›</i>`; }
    cap.before(row); row.append(cap); if(fm) row.append(fm); }
  titleCharts();
  movePicker();
  }
/* stagger the card groups only when a page is first opened (a new view or question), not when it redraws */
let stKey=null;
function staggerIn(){ const k=S.view+"|"+(S.view==="method"?S.mtab:""); if(k===stKey) return; stKey=k;
  if(reduced) return;
  document.querySelectorAll(".h-more,.s-qcards3,.ab-srcs,.srt-fn,.srt-sg,.srt-chs").forEach(g=>{ [...g.children].forEach((c,i)=>c.style.setProperty("--i",i)); g.classList.add("st-in"); setTimeout(()=>g.classList.remove("st-in"),320+30*g.children.length); }); }
function render(){
  document.body.classList.remove("menu-open");
  mapSize();
  if(S.view==="qpage"){ S.qseen=S.qseen||[]; if(!S.qseen.includes(S.sq)) S.qseen.push(S.sq); }
  document.querySelectorAll(".i-sheet").forEach(e=>e.remove());
  const tipEl=document.getElementById("tip"); if(tipEl) tipEl.classList.remove("on");
  let body;
  if(S.view==="home") body=vHome(); else if(S.view==="about") body=vAbout(); else if(S.view==="method") body=vMethod(); else if(S.view==="pick") body=vPick(); else if(S.view==="qindex") body=vQIndex(); else if(S.view==="qpage") body=vQPage(); else if(S.view==="compare") body=vCompare(); else if(S.view==="game") body=vGame(); else if(S.view==="card"){ body=vCard(); } else if(S.view==="wall") body=vWall();
  else {
    const p=pages()[S.idx]; if(!S.read.includes(p)) S.read.push(p);
    const last=S.idx===pages().length-1;
    S.notes=S.notes||{}; S.path=S.path||{};
    S.says={}; pages().slice(0,S.idx).forEach(k=>{ const r=PAGES[k](); if(r.brief) S.notes[k]=r.brief; if(r.path) S.path[k]=r.path; if(r.say) S.says[k]=r.say; });
    const pg=PAGES[p](); if(pg.brief) S.notes[p]=pg.brief; if(pg.path) S.path[p]=pg.path; if(pg.say) S.says[p]=pg.say;
    body=S.theme==="study"? slide(pg) : `<div class="stage">${slide(pg)}
      ${S.idx>0?`<button class="turn prev" data-turn="-1" aria-label="Previous page">‹</button>`:""}
      <button class="turn next" data-turn="1" aria-label="${last?"See your card":"Next page"}">›</button></div>`;
  }
  const study=S.theme==="study"||S.view==="qindex"||S.view==="qpage"; document.body.classList.toggle("is-study",study);
  const snap=figSnap(), keepX=[...document.querySelectorAll(".c-cards,.c-table,.m-top,.w-dig,.h-more,.w-eras")].map(e=>[e.className.split(" ")[0],e.scrollLeft,e.scrollTop]);
  $("#app").innerHTML=(study?studyHeader():header())+body+(study?studyFooter():footer());
  keepX.forEach(([c,x,y])=>{ const e=document.querySelector("."+c); if(e){ e.scrollLeft=x; if(y) e.scrollTop=y; } });
  /* the era row opens on the era already chosen */
  const we=document.querySelector(".w-eras"), weOn=we&&we.querySelector(".w-era.on"); if(weOn&&!keepX.some(k=>k[0]==="w-eras")) we.scrollLeft=weOn.getBoundingClientRect().left-we.getBoundingClientRect().left+we.scrollLeft-16;
  mapInit(); figMorph(snap); countUp(); drawOnce(); gScorePop(); syncHash(); phoneFold(); tankStart();
  staggerIn();
  { const mt=document.querySelector(".m-top"), k=keepX.find(x=>x[0]==="m-side"); if(mt){ if(k){ mt.scrollLeft=k[1]; mt.scrollTop=k[2]; } mt.dispatchEvent(new Event("scroll")); } }
  document.body.classList.toggle("sheet-open",!!document.querySelector(".c-sheet"));
  /* Compare: say "swipe" only when the table is actually wider than the screen */
  const csw=document.querySelector(".c-swipe"), ctb=document.querySelector(".c-table"); if(csw&&ctb) csw.hidden=ctb.scrollWidth<=ctb.clientWidth+1;
}
/* each main page has its own address (#q3, #compare …): a refresh keeps the page, links can point at it, back and forward work */
const HASH_VIEWS=["compare","game","method","about","wall"];
function hashOf(){ const v=S.view;
  if(v==="home") return "";
  if(v==="qpage") return S.sq;
  if(v==="qindex") return "questions";
  if(v==="pick") return S.pickTab==="enter"?"neighbours":"pick";
  if(HASH_VIEWS.includes(v)) return v;
  return null; /* walks, diagnosis and the card depend on choices made on the way: keep the last address */ }
function syncHash(){ const h=hashOf(); if(h===null||location.hash.slice(1)===h) return;
  history.pushState(null,"",h?"#"+h:location.pathname+location.search); }
function fromHash(){ const h=location.hash.slice(1);
  if(/^q[1-6]$/.test(h)){ S.sq=h; S.view="qpage"; }
  else if(h==="questions") S.view="qindex";
  else if(h==="neighbours"){ S.scen="s1"; S.pickTab="enter"; S.view="pick"; }
  else if(h==="pick"){ S.scen="s1"; S.pickTab="pick"; S.view="pick"; }
  else if(HASH_VIEWS.includes(h)){ if(h==="method") S.mtab="success"; S.view=h; }
  else S.view="home"; }
window.addEventListener("popstate",()=>{ fromHash(); render(); window.scrollTo(0,0); });
/* ---------- small effects: each plays once, on a change, and never under reduced motion ---------- */
const CALM=()=>window.matchMedia&&matchMedia("(prefers-reduced-motion: reduce)").matches;
const figKey=()=>S.view==="qpage"?"q:"+S.sq:S.view==="book"?`b:${S.scen}:${S.idx}:${S.cat||""}:${S.dapp||""}`:null;
const MORPH={rect:["x","y","width","height"],circle:["cx","cy","r"],path:["d"]};
function figSnap(){ const k=figKey(), svg=k&&document.querySelector("main .s-fig svg"); if(!svg) return null;
  return {k, els:[...svg.querySelectorAll("rect,circle,path")].map(e=>({t:e.tagName,a:Object.fromEntries(MORPH[e.tagName].map(n=>[n,e.getAttribute(n)]))}))}; }
/* switching era on the same chart: bars, dots and lines glide from their old values to the new ones */
function figMorph(snap){ if(!snap||CALM()||snap.k!==figKey()) return; const svg=document.querySelector("main .s-fig svg"); if(!svg) return;
  const els=[...svg.querySelectorAll("rect,circle,path")], moved=[];
  els.forEach((e,i)=>{ const o=snap.els[i]; if(!o||o.t!==e.tagName) return; if(e.__st===undefined) e.__st=e.getAttribute("style");
    MORPH[e.tagName].forEach(n=>{ const was=o.a[n], now=e.getAttribute(n); if(was==null||now==null||was===now) return;
      if(n==="d"){ if(was.replace(/[^A-Za-z]/g,"")!==now.replace(/[^A-Za-z]/g,"")) return; e.style.d=`path("${was}")`; moved.push([e,"d",`path("${now}")`]); }
      else { e.style[n]=was+"px"; moved.push([e,n,now+"px"]); } }); });
  if(!moved.length) return; svg.getBoundingClientRect();
  requestAnimationFrame(()=>{ moved.forEach(([e,n,v])=>{ e.style.transition="all .55s cubic-bezier(.2,.7,.2,1)"; e.style[n]=v; });
    setTimeout(()=>moved.forEach(([e])=>{ if(e.__st) e.setAttribute("style",e.__st); else e.removeAttribute("style"); }),650); }); }
/* "Do their users stay?": the retention lines draw themselves from launch to month 6, once per era */
const DRAWN=new Set();
function drawOnce(){ const box=document.querySelector(".draw-once"); if(!box) return; const key=S.scen+":"+era(); if(DRAWN.has(key)) return; DRAWN.add(key); if(CALM()) return;
  box.querySelectorAll('polyline[fill="none"],path[fill="none"]').forEach(pth=>{ const L=Math.ceil(pth.getTotalLength()*1.5)+10; pth.style.strokeDasharray=L; pth.style.strokeDashoffset=L;
    pth.animate([{strokeDashoffset:L},{strokeDashoffset:0}],{duration:1400,easing:"cubic-bezier(.3,.6,.2,1)",fill:"forwards"}).onfinish=()=>{ pth.style.strokeDasharray=""; pth.style.strokeDashoffset=""; }; }); }
/* game: the level's points pop and count up once, the success dots land one after another */
const GSCORED=new Set();
function gScorePop(){ const b=document.querySelector(".g-plus"); if(!b||!S.gm||PHONE()) return; const G=S.gm, key=G.lv+":"+G.picks[G.lv].join(); if(GSCORED.has(key)) return; GSCORED.add(key);
  const to=+b.dataset.to, from=G._shown&&G._shown.lv===G.lv?G._shown.v:0, n=G.picks[G.lv].length; G._shown={lv:G.lv,v:to}; if(CALM()||!n) return;
  const dot=document.querySelectorAll(".g-dots i")[n-1]; if(dot) dot.classList.add("land");
  if(to===from) return; const t0=performance.now(); b.classList.add("pop"); b.textContent="+"+from;
  const step=t=>{ const k=Math.max(0,Math.min(1,(t-t0)/600)); b.textContent="+"+Math.round(from+(to-from)*(1-Math.pow(1-k,3))); if(k<1) requestAnimationFrame(step); }; requestAnimationFrame(step); }
/* the big numbers count up from zero the first time a page shows them */
const COUNTED=new Set();
function countUp(){ const key=S.view+(S.view==="method"?":"+S.mtab:""); if(COUNTED.has(key)) return; COUNTED.add(key); if(CALM()) return;
  document.querySelectorAll(".s-fact b, .mcard b").forEach(el=>{ const tn=[...el.childNodes].find(n=>n.nodeType===3&&/\d/.test(n.nodeValue)); if(!tn) return;
    const m=tn.nodeValue.match(/[\d,]+(\.\d+)?/); if(!m) return; const end=+m[0].replace(/,/g,""); if(!(end>=10)) return;
    const dec=(m[1]||"").length?m[1].length-1:0, fmt=v=>dec?v.toFixed(dec):Math.round(v).toLocaleString("en-US"), pre=tn.nodeValue.slice(0,m.index), post=tn.nodeValue.slice(m.index+m[0].length), t0=performance.now(), T=900;
    const step=t=>{ const k=Math.min(1,(t-t0)/T), e=1-Math.pow(1-k,3); tn.nodeValue=pre+fmt(end*e)+post; if(k<1) requestAnimationFrame(step); };
    tn.nodeValue=pre+fmt(0)+post; requestAnimationFrame(step); }); }
function go(v){ if((v==="about"||v==="method") && S.view!=="about" && S.view!=="method") S.from=S.view; if(v==="method") S.mtab="success"; S.view=v; render(); window.scrollTo(0,0); }
function openBook(){ S.idx=0; S.read=[]; S.notes={}; S.path={}; if(S.scen==="s2"){ S.catPicked=false; S.leader=null; } go("book"); }

const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
/* a plain slide: the new page eases in from the side you are moving toward */
function turnTo(ni){
  if(S.view!=="book" || ni===S.idx || ni<0) return;
  if(ni>=pages().length) return go("card");
  const dir = ni>S.idx ? 1 : -1;
  S.idx=ni; render();
  if(window.scrollY>200) window.scrollTo(0,0);
  const el=$(".slide")||$(".sslide .s-fig"); if(!el) return;
  const a=el.animate(reduced ? [{opacity:.85},{opacity:1}] : [{transform:`translateX(${dir*28}px)`},{transform:"none"}],
             {duration:reduced?160:320, easing:"cubic-bezier(.2,.7,.2,1)"});
  setTimeout(()=>a.cancel(), 360); /* animations pause in background tabs; never leave a slide half-faded */
}
const turn = dir => turnTo(S.idx+dir);

document.addEventListener("click",e=>{
  if(S.view==="compare"&&S.cadd!=null&&!e.target.closest(".c-slotwrap")){ S.cadd=null; S.cquery=""; const y=window.scrollY; render(); window.scrollTo(0,y); return; }
  const t=e.target.closest("button"); if(!t) return; const ds=t.dataset;
  if(ds.act==="menu"){ document.body.classList.toggle("menu-open"); return; }
  if(ds.act==="isheet"){ const d=t.closest(".srt-s").querySelector(".srt-d"); if(d) openSheet(d.innerHTML); return; }
  if(ds.act==="fold"){ const src=t._src||t.nextElementSibling; if(src) openSheet(`<h3>${t.dataset.title}</h3>`+src.innerHTML,"i-fold"); return; }
  if(ds.act==="isheet-x"){ closeISheets(); return; }
  if(ds.act==="gterm"){ openSheet(termCard(ds.k,ds.axis),"i-term"); return; }
  if(ds.act==="sigterm"){ const h=sigCard(ds.f); if(h) openSheet(h,"i-sig"); return; }
  if(ds.turn) return turn(+ds.turn);
  if(ds.jump!=null) return turnTo(+ds.jump);
  if(ds.go==="home"){ Object.assign(S,{scen:null,dapp:null,custom:null,era:null,q1m:null,q3m:null,query:"",pickTab:"pick",pickCat:"featured"}); return go("home"); }
  if(ds.wall!=null){ const c=wallCards()[+ds.wall]; if(c) openSheet(bizCard(c),"i-card"); return; }
  if(ds.act==="mtdot"){ const w=document.querySelector(".m-top"), c=w&&[...w.querySelectorAll(".m-sum,.m-card")][+ds.i]; document.querySelectorAll(".m-topdots button").forEach((b,k)=>b.classList.toggle("on",k===+ds.i)); if(c){ const cs=getComputedStyle(w), v=cs.flexDirection==="column", cr=c.getBoundingClientRect(), wr=w.getBoundingClientRect(); const to=v?Math.max(0,Math.min(w.scrollTop+cr.top-wr.top-parseFloat(cs.paddingTop||0),w.scrollHeight-w.clientHeight)):Math.max(0,Math.min(w.scrollLeft+cr.left-wr.left-parseFloat(cs.paddingLeft||0),w.scrollWidth-w.clientWidth)); w.scrollTo(v?{top:to,behavior:CALM()?"auto":"smooth"}:{left:to,behavior:CALM()?"auto":"smooth"}); setTimeout(()=>{ if(v){ if(Math.abs(w.scrollTop-to)>4) w.scrollTop=to; } else if(Math.abs(w.scrollLeft-to)>4) w.scrollLeft=to; },600); } return; }
  if(ds.act==="hmdot"){ const w=document.querySelector(".h-more"), c=w&&w.children[+ds.i]; document.querySelectorAll(".h-moredots button").forEach((b,k)=>b.classList.toggle("on",k===+ds.i)); if(c){ const to=Math.min(c.offsetLeft-w.offsetLeft,w.scrollWidth-w.clientWidth); w.scrollTo({left:to,behavior:CALM()?"auto":"smooth"}); setTimeout(()=>{ if(Math.abs(w.scrollLeft-to)>4) w.scrollLeft=to; },600); } return; }
  if(ds.act==="hdot"){ const w=document.querySelector(".h-swipe"); document.querySelectorAll(".h-dots button").forEach((b,k)=>b.classList.toggle("on",k===+ds.i)); if(w){ const c=w.children[+ds.i], to=c?c.offsetLeft-w.children[0].offsetLeft:(+ds.i)*w.clientWidth; w.scrollTo({left:to,behavior:CALM()?"auto":"smooth"}); setTimeout(()=>{ if(Math.abs(w.scrollLeft-to)>4) w.scrollLeft=to; },600); } return; }
  if(ds.act==="hsl"){ const w=document.querySelector(".h-swipe"); if(w){ const cw=w.clientWidth, n=w.children.length, i=Math.max(0,Math.min(n-1,Math.round(w.scrollLeft/cw)+(+ds.d))); const to=i*cw; w.scrollTo({left:to,behavior:CALM()?"auto":"smooth"}); setTimeout(()=>{ if(Math.abs(w.scrollLeft-to)>4) w.scrollLeft=to; },600); } return; }
  if(ds.act==="cardsave"){ const c=cardData(); if(wallHas(c.h)){ S.justSaved=null; try{ localStorage.setItem(WALL_KEY,JSON.stringify(wallLoad().filter(x=>x.h!==c.h))); }catch(e){} } else { wallSave(); S.justSaved=c.h; } render(); S.justSaved=null; return; }
  if(ds.act==="wallclear"){ if(confirm("Clear today's saved cards from this screen? This cannot be undone.")){ try{ const d=new Date().toDateString(); localStorage.setItem(WALL_KEY,JSON.stringify(wallLoad().filter(c=>new Date(c.t).toDateString()!==d))); }catch(e){} render(); } return; }
  if(ds.go==="wall"||ds.go==="card"||ds.go==="about"||ds.go==="method"||ds.go==="qindex"||ds.go==="compare"||ds.go==="game") return go(ds.go);
  if(ds.gmode){ gStart(ds.gmode); return render(); }
  if(ds.act==="gread"){ const t=document.querySelector(".t-learn"); if(t) t.scrollIntoView({behavior:"smooth",block:"start"}); return; }
  if(ds.act==="gplay"){ const G=S.gm; G.phase="play"; G.ts=Date.now(); return render(); }
  if(ds.act==="gnext"){ const G=S.gm; G.lv++; if(G.mode==="learn"){ G.phase="intro"; } else { G.phase="play"; G.ts=Date.now(); } window.scrollTo(0,0); return render(); }
  if(ds.act==="gend"){ S.gm.phase="done"; return render(); }
  if(ds.act==="gmenu"){ S.gm=null; window.scrollTo(0,0); return render(); }
  if(ds.act==="gsave"){ const G=S.gm, n=(document.getElementById("g-name")||{}).value||"", P=mapPool();
    const score=G.picks.reduce((t,a)=>t+a.filter(k=>{ const d=P.find(x=>x.k===k); return d&&d.s; }).length,0), pts=gPts(G);
    G.id=Date.now()+""; lbSave([...lbLoad(),{id:G.id,name:n.trim().slice(0,14)||"Anonymous",mode:G.mode,score,pts,ms:G.el,at:new Date().toISOString().slice(0,10)}]); return render(); }
  if(ds.cslot!=null){ S.cadd=+ds.cslot<0?null:+ds.cslot; S.cquery=""; const y=window.scrollY; render(); window.scrollTo(0,y); const n=$("#cq"); if(n) n.focus(); return; }
  if(ds.follow){ S.cat=ds.follow; S.catPicked=true; S.leader=null; const y=window.scrollY; render(); window.scrollTo(0,y); return; }
  if(ds.deeper){ const k=ds.deeper, e=era(); S.scen="s1"; S.dapp=k; S.custom=null; S.era=e; S.fromMarket={era:e,cat:S.cat}; return openBook(); }
  if(ds.leader){ S.leader=ds.leader; const y=window.scrollY; render(); window.scrollTo(0,y); return; }
  if(ds.pera){ S.era=ds.pera; S.catPicked=false; return turn(1); }
  if(ds.cmpadd){ S.cmp=[...(S.cmp||[]),ds.cmpadd].slice(0,3); S.cquery=""; S.cadd=null; const y=window.scrollY; render(); window.scrollTo(0,y); return; }
  if(ds.cmprm){ S.cmp=(S.cmp||[]).filter(x=>x!==ds.cmprm); const y=window.scrollY; render(); window.scrollTo(0,y); return; }
  if(ds.act==="clearn"){ S.csheet=ds.k; const y=window.scrollY; render(); window.scrollTo(0,y); return; }
  if(ds.act==="csheet-x"){ closeCSheet(); return; }
  if(ds.walk){ S.csheet=null; S.scen="s1"; S.dapp=ds.walk; S.custom=null; S.era=D.dapps[ds.walk].period; return openBook(); }
  if(ds.cmpwith){ S.cmp=[ds.cmpwith]; S.cquery=""; return go("compare"); }
  if(ds.sera){ S.sera=ds.sera; const y=window.scrollY; render(); window.scrollTo(0,y); return; }
  if(ds.sq){ S.sq=ds.sq; return go("qpage"); }
  if(ds.go==="pick"){ if(ds.tab) S.pickTab=ds.tab; if(ds.startDiag){ S.scen="s1"; } return go("pick"); }
  if(ds.start){ S.fromMarket=null; S.scen=ds.start; if(ds.start==="s1") return go("pick"); return openBook(); }
  if(ds.tab){ S.pickTab=ds.tab; return render(); }
  if(ds.pickcat){ S.pickCat=ds.pickcat; S.query=""; return render(); }
  if(ds.dapp){ S.dapp=ds.dapp; S.custom=null; S.era=D.dapps[ds.dapp].period; return openBook(); }
  if(ds.era){ S.era=ds.era; return render(); }
  if(ds.cat){ S.cat=ds.cat; return render(); }
  if(ds.q6metric){ S.q6metric=ds.q6metric; return render(); }
  if(ds.hm){ /* switch the Home market strip: the line glides from one measure to the next */
    const old=[...document.querySelectorAll(".h-mkt path")].map(p=>p.getAttribute("d")); S.hm=ds.hm; const y=window.scrollY; render(); window.scrollTo(0,y);
    if(!CALM()) document.querySelectorAll(".h-mkt path").forEach((p,i)=>{ const now=p.getAttribute("d"); if(!old[i]||old[i].replace(/[^A-Z]/g,"")!==now.replace(/[^A-Z]/g,"")) return;
      p.style.d=`path("${old[i]}")`; p.getBoundingClientRect(); requestAnimationFrame(()=>{ p.style.transition="d .6s cubic-bezier(.2,.7,.2,1)"; p.style.d=`path("${now}")`; }); });
    return; }
  if(ds.dqt!==undefined){ const n=+ds.dqt, was=S.dqt===undefined?1:S.dqt, fig=document.querySelector(".dq-tour");
    /* step to step: change the chart's focus and the card in place, so the fade plays the moment the button is pressed */
    if(fig&&n>0&&was>0){ S.dqt=n; fig.classList.remove("f1","f2","f3","f4"); fig.classList.add("f"+Math.min(4,n));
      const card=fig.querySelector(".tour"), tmp=document.createElement("div"); tmp.innerHTML=dqTour(); card.innerHTML=tmp.firstElementChild.innerHTML;
      if(!CALM()) card.animate([{opacity:.35,transform:"translateY(4px)"},{opacity:1,transform:"none"}],{duration:220,easing:"ease-out"}); return; }
    S.dqt=n; const y=window.scrollY; render(); window.scrollTo(0,y); return; }
  if(ds.mtab){ S.mtab=ds.mtab; render(); window.scrollTo(0,0); return; }
  const a=ds.act;
  if(a==="reopen") return go("book");
  if(a==="aboutback") return go(S.from||"home");
  if(a==="mswap"){ const x=mAxisX(), y=mAxisY(); S.mx=y; S.my=x; const sy=window.scrollY; render(); window.scrollTo(0,sy); return; }
  if(a==="mreset"){ S.mcat="all"; S.mera="all"; const sy=window.scrollY; render(); window.scrollTo(0,sy); return; }
  if(a==="pkrand"){ const keys=Object.keys(D.dapps), pick=keys[Math.floor(Math.random()*keys.length)], el=document.getElementById("pk-roll"); let n=0;
    const t=setInterval(()=>{ if(el) el.textContent=D.dapps[keys[Math.floor(Math.random()*keys.length)]].name; if(++n>=12){ clearInterval(t); if(el) el.textContent=D.dapps[pick].name;
      setTimeout(()=>{ S.dapp=pick; S.custom=null; S.era=D.dapps[pick].period; openBook(); },380); } },70); return; }
});
document.addEventListener("keydown",e=>{
  if(e.key==="Enter"&&e.target&&e.target.id==="g-name"){ const b=document.querySelector('[data-act="gsave"]'); if(b){ e.preventDefault(); b.click(); return; } }
  if(e.key==="Escape"&&S.view==="compare"&&S.cadd!=null){ S.cadd=null; S.cquery=""; return render(); }
  if(e.target.classList && e.target.classList.contains("digits") && e.key.length===1 && !/\d/.test(e.key) && !e.metaKey && !e.ctrlKey){ e.preventDefault(); const er=$("#f-err"); if(er) er.textContent="Numbers only: letters and symbols are ignored."; return; }
  const inField = e.target.matches && e.target.matches("input,select,textarea");
  if(S.view!=="book" || inField) return;
  if(e.key==="ArrowRight"||e.key==="PageDown"){ e.preventDefault(); turn(1); }
  if(e.key==="ArrowLeft"||e.key==="PageUp"){ e.preventDefault(); turn(-1); }
});
let tx=null, ty=null;
document.addEventListener("touchstart",e=>{ if(S.view!=="book"||e.target.closest("input")) { tx=null; return; } tx=e.touches[0].clientX; ty=e.touches[0].clientY; },{passive:true});
document.addEventListener("touchend",e=>{ if(tx==null) return; const dx=e.changedTouches[0].clientX-tx, dy=e.changedTouches[0].clientY-ty; tx=null; if(Math.abs(dx)>70 && Math.abs(dx)>Math.abs(dy)*1.5) turn(dx<0?1:-1); });
document.addEventListener("change",e=>{ const t=e.target; if(!t.dataset || !t.dataset.sel) return; S[t.dataset.sel]=t.value; const y=window.scrollY; render(); window.scrollTo(0,y); });
document.addEventListener("input",e=>{
  const t=e.target;
  if(t.id==="cq"){ S.cquery=t.value; const pos=t.selectionStart; render(); const n=$("#cq"); if(n){ n.focus(); n.setSelectionRange(pos,pos); } return; }
  if(t.id==="q"){ S.query=t.value; const pos=t.selectionStart; render(); const n=$("#q"); n.focus(); n.setSelectionRange(pos,pos); return; }
  if(t.classList && t.classList.contains("digits")){ const clean=t.value.replace(/\D/g,"").slice(0,9); const er=$("#f-err"); if(clean!==t.value){ t.value=clean; if(er) er.textContent="Numbers only: letters and symbols are ignored."; } else if(er) er.textContent=""; return; }
  if(t.id && t.id.startsWith("f-")){ const er=$("#f-err"); if(er) er.textContent=""; return; }
  const r=t.dataset.range; if(!r) return;
  if(r==="eraIdx"){ S.era=["before","between","after"][+t.value]; }
  else if(r==="q3k"){ const yr=D.q3.months[S.q3m??D.q3.months.length-1].slice(0,4); S.q3k=D.q3.rank_curve[yr].k[+t.value]; }
  else if(r==="q1m"||r==="q3m"){ S.q1m=S.q3m=+t.value; }
  else S[r]=+t.value;
  const y=window.scrollY; render(); window.scrollTo(0,y);
  const n=document.querySelector(`[data-range="${r}"]`); if(n) n.focus();
});
/* floating tooltip for any element with data-tip (charts, bars); tap also works on touch screens */
(function(){ const tip=document.createElement("div"); tip.id="tip"; tip.setAttribute("role","tooltip"); document.body.appendChild(tip);
  const show=(el,x,y)=>{ const t=el.getAttribute("data-tip"); if(!t) return; const [h,...rest]=t.split("\n");
    tip.innerHTML=`<b>${esc(h)}</b>${rest.map(l=>`<span>${esc(l)}</span>`).join("")}`; tip.classList.add("on"); place(x,y); };
  /* beside the pointer, flipped when it would run off an edge, and always kept fully on screen (phones are narrow) */
  const place=(x,y)=>{ const r=tip.getBoundingClientRect(); let L=x+16, T=y+16; if(L+r.width>innerWidth-8) L=x-r.width-16; if(T+r.height>innerHeight-8) T=y-r.height-16;
    L=Math.max(8,Math.min(L,innerWidth-r.width-8)); T=Math.max(8,Math.min(T,innerHeight-r.height-8)); tip.style.left=L+"px"; tip.style.top=T+"px"; };
  document.addEventListener("mousemove",e=>{ const el=e.target.closest&&e.target.closest("[data-tip]"); if(el) show(el,e.clientX,e.clientY); else tip.classList.remove("on"); });
  document.addEventListener("click",e=>{ const el=e.target.closest&&e.target.closest("[data-tip]"); if(el){ show(el,e.clientX,e.clientY); clearTimeout(tip._t); tip._t=setTimeout(()=>tip.classList.remove("on"),2500); } });
  window.addEventListener("scroll",()=>tip.classList.remove("on"),{passive:true});
})();
S.theme = "study";
setTheme(S.theme);
document.getElementById("orbits-host").innerHTML=orbits();
document.fonts && document.fonts.ready.then(()=>{ if(S.view!=="home") render(); });
fromHash();
render();
document.addEventListener("keydown",e=>{ if(e.key!=="Escape") return; document.body.classList.remove("menu-open"); if(document.querySelector(".i-sheet")){ closeISheets(); } if(S.csheet){ closeCSheet(); } });
document.addEventListener("scroll",e=>{ const s=e.target; if(!s.classList||!s.classList.contains("srt")) return; const kids=[...s.children], o0=kids[0]?kids[0].offsetLeft:0; let i=0, best=1e9; kids.forEach((c,k)=>{ const d=Math.abs(c.offsetLeft-o0-s.scrollLeft); if(d<best){ best=d; i=k; } }); let dots=s.nextElementSibling; if(dots&&dots.classList.contains("h-erasbar")) dots=dots.nextElementSibling; /* the market carousel has its era bar between it and its dots */ if(dots) [...dots.children].forEach((d,k)=>d.classList.toggle("on",k===i)); },true);
/* desktop More ways in: the dot follows the first card in view */
document.addEventListener("scroll",e=>{ const w=e.target; if(!w.classList||!w.classList.contains("m-top")) return; const cs=getComputedStyle(w), v=cs.flexDirection==="column", kids=[...w.querySelectorAll(".m-sum,.m-card")], wr=w.getBoundingClientRect(), L=v?wr.top+parseFloat(cs.paddingTop||0):wr.left+parseFloat(cs.paddingLeft||0);
  let i=kids.findIndex(c=>{ const r=c.getBoundingClientRect(); return (v?r.top:r.left)>=L-8; }); if((v?w.scrollTop:w.scrollLeft)>4&&(v?w.scrollTop>=w.scrollHeight-w.clientHeight-4:w.scrollLeft>=w.scrollWidth-w.clientWidth-4)) i=kids.length-1; document.querySelectorAll(".m-topdots button").forEach((b,k)=>b.classList.toggle("on",k===Math.max(0,i))); },true);
document.addEventListener("scroll",e=>{ const w=e.target; if(!w.classList||!w.classList.contains("h-more")) return; const kids=[...w.children], x=w.scrollLeft;
  let i=kids.findIndex(c=>c.offsetLeft-w.offsetLeft>=x-8); if(x>=w.scrollWidth-w.clientWidth-4) i=kids.length-1; document.querySelectorAll(".h-moredots button").forEach((b,k)=>b.classList.toggle("on",k===Math.max(0,i))); },true);
{ let wasPhone=PHONE(); addEventListener("resize",()=>{ if(PHONE()!==wasPhone){ wasPhone=PHONE(); render(); } }); }
/* booth screen: open with ?kiosk (or ?kiosk=120 for seconds) and the site goes back to a fresh Home after that long with no input.
   A reload clears every choice but keeps the game's top-10 board, which lives in localStorage. */
(function(){ const q=new URLSearchParams(location.search); if(!q.has("kiosk")) return;
  const secs=Math.max(15,+q.get("kiosk")||90); let t;
  const arm=()=>{ clearTimeout(t); t=setTimeout(()=>{ if(S.view==="home"&&!location.hash) return arm(); location.replace(location.pathname+location.search); },secs*1000); };
  ["pointerdown","pointermove","keydown","wheel","touchstart","scroll"].forEach(ev=>addEventListener(ev,arm,{passive:true}));
  arm(); })();
