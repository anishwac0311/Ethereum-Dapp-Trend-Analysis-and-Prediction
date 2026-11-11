/* =====================================================================
   Compare: up to three widely used DApps side by side, like comparing products in a shop.
   Every row is one of the six questions, read for that DApp. Higher-is-better rows mark the leader.
   ===================================================================== */
const CMP_COL=["#1A1A1A","#3860BE","#696969"];
function cmpFacts(slug){
  const d=D.dapps[slug], c10=d.cum?d.cum.findIndex(v=>v!=null&&v>=1e4):-1, k6=d.event?d.event.rel.indexOf(6):-1;
  const lastv=d.norm&&d.norm.length?d.norm.filter(v=>v!=null).slice(-1)[0]:null;
  return {d,
    peak:d.peak, launch:d.launch, period:d.period,
    shape:d.group, success:d.success,
    hold:lastv,
    to10k:c10>=0?c10:null, cum6:d.cum?d.cum[Math.min(6,d.cum.length-1)]:null,
    ret6:d.ret?d.ret[6]:null,
    after10k:k6>=0&&d.event.retention_prev_month?d.event.retention_prev_month[k6]:null};
}
function vCompare(){
  S.cmp=(S.cmp||["uniswap-v3","blur"]).filter(x=>D.dapps[x]).slice(0,3);
  const slots=[0,1,2].map(i=>S.cmp[i]||null), F=S.cmp.map(cmpFacts), q=(S.cquery||"").trim().toLowerCase(), all=Object.entries(D.dapps).filter(([k])=>!S.cmp.includes(k));
  /* the add box: search, or the biggest few of each category */
  const addBox=()=>{ const hits=q?all.filter(([k,d])=>d.name.toLowerCase().includes(q)).sort((a,b)=>b[1].peak-a[1].peak).slice(0,12):null;
    const groups=hits?[["Matches",hits]]:CATS.map(c=>[c,all.filter(([k,d])=>d.cat===c).sort((a,b)=>b[1].peak-a[1].peak).slice(0,4)]).filter(g=>g[1].length);
    return `<div class="c-add"><input class="search" id="cq" placeholder="Search 170 DApps" value="${esc(S.cquery||"")}" autocomplete="off" aria-label="Search DApps to compare">
      <div class="c-list">${groups.map(([g,rows])=>`<span class="s-mono c-grp">${g}</span>${rows.map(([k,d])=>`<button data-cmpadd="${k}"><span>${esc(d.name)}</span><em>${fmtN(d.peak)} peak</em></button>`).join("")}`).join("")||`<p class="tiny">No match.</p>`}</div>
</div>`; };
  const slotHead=i=>{ const k=slots[i];
    if(!k){ const open=S.cadd===i; return `<div class="c-slotwrap"><button class="c-slot ${open?"on":""}" data-cslot="${open?-1:i}"><b>+</b><span>Add a DApp</span></button>${open?addBox():""}</div>`; }
    const f=cmpFacts(k); return `<div class="c-col"><i style="background:${CMP_COL[i]}"></i><b>${esc(f.d.name)}</b>
      <button class="c-x" data-cmprm="${k}" aria-label="Remove ${esc(f.d.name)}">×</button></div>`; };
  /* rows: label, value, formatter, better ("hi" | "lo" | null) */
  const R=[
    ["Category",f=>f.d.cat],
    ["Launched",f=>PERIOD[f.period]],
    ["Peak monthly wallets",f=>fmtN(f.peak),"peak","hi"],
    ["Shape",f=>f.shape==="grower"?"Kept growing":"One-hit"],
    ["Months to 10K wallets",f=>f.to10k==null?"Not within a year":f.to10k===0?"First month":`Month ${f.to10k}`,"to10k","lo"],
    ["First users kept at month 6",f=>f.ret6==null?"<small>Under 100 first-month users</small>":pct(f.ret6),"ret6","hi"],
    ["Success a year later",f=>f.success==null?"Too recent":f.success?`<span class="c-yes">Yes</span>`:"No"]];
  const lead=(key,dir)=>{ const v=F.map(f=>f[key]).filter(x=>x!=null); if(F.length<2||v.length<2) return null; return dir==="hi"?Math.max(...v):Math.min(...v); };
  const SF=slots.map(k=>k?cmpFacts(k):null);
  const cols=PHONE()?`96px repeat(3,118px)`:`minmax(220px,1.1fr) repeat(3,minmax(0,1fr))`;
  const head=`<div class="c-row c-head" style="grid-template-columns:${cols}"><span></span>${[0,1,2].map(slotHead).join("")}</div>`;
  const body=R.map(([label,fn,key,dir])=>{ if(!fn) return `<div class="c-sec s-mono">${label}</div>`; const L=key?lead(key,dir):null;
    return `<div class="c-row" style="grid-template-columns:${cols}"><span class="c-lab">${label}</span>${SF.map(f=>f?`<span class="c-val ${L!=null&&f[key]===L?"best":""}">${fn(f)}</span>`:`<span class="c-val c-none"></span>`).join("")}</div>`; }).join("")
    + `<div class="c-sec s-mono">Go deeper · dig into Layer 3</div><div class="c-row c-dig" style="grid-template-columns:${cols}"><span class="c-lab"></span>${SF.map((f,i)=>f?`<span><button class="w-go" data-walk="${slots[i]}"><span class="c-long">Layer 3 · dig into ${esc(f.d.name)} →</span><span class="c-short">Dig in →</span></button></span>`:`<span></span>`).join("")}</div>`;
  /* phones: a card per DApp to swipe through (its own curve, key facts, Dig in / Learn more) above the table,
     and Learn more opens that DApp's full numbers in a sheet with a Dig in bar at the bottom */
  const ph=PHONE(), SOFT=["#ECE9E3","#E6ECF8","#EEEDEB"];
  /* also: the other DApps as thin lines under this one (the Learn more sheet), each in its own colour; all on a share-of-own-peak scale */
  const spark=(f,i,h=96,also=[])=>{ const W=300,H=110,P=8;
    const line=(g,c,w)=>{ const v=g.d.norm||[], n=v.length; if(n<2) return "";
      const pts=v.map((y,k)=>y==null?null:`${(P+k/(n-1)*(W-2*P)).toFixed(1)},${(P+(1-y)*(H-2*P)).toFixed(1)}`).filter(Boolean).join(" ");
      return `<polyline points="${pts}" fill="none" stroke="${c}" stroke-width="${w}" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>`; };
    const me=line(f,CMP_COL[i],2.5); if(!me) return "";
    return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="height:${h}px" aria-hidden="true">${also.map(([g,j])=>line(g,CMP_COL[j],1.4)).join("")}${me}</svg>`; };
  const verdict=f=>f.success==null?"Too recent to judge":f.success?`<span class="c-yes">Still a success a year later</span>`:"Not a success a year later";
  const cards=`<div class="c-cards">${slots.map((k,i)=>{
      if(!k) return S.cmp.length!==i?"":S.cadd===i?`<div class="c-card c-addcard c-addopen c-slotwrap"><button class="c-sx c-addx" data-cslot="-1" aria-label="Close search">✕</button>${addBox()}</div>`:`<button class="c-card c-addcard" data-cslot="${i}"><b>+</b><span>Add a DApp</span></button>`;
      const f=cmpFacts(k);
      return `<article class="c-card" style="--tint:${SOFT[i]}">${i>0?`<button class="c-cardx" data-cmprm="${k}" aria-label="Remove ${esc(f.d.name)}" title="Remove"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4.5 4.5l7 7M11.5 4.5l-7 7" stroke="#1A1A1A" stroke-width="1.6" stroke-linecap="round"/></svg></button>`:""}<div class="c-art" style="background:${SOFT[i]}">${spark(f,i)}<span class="s-mono">First 2 years · share of peak</span></div>
        <b class="c-cn">${esc(f.d.name)}</b><span class="s-mono c-cm">${f.d.cat} · ${monthLabel(f.launch)}</span>
        <p class="c-cf">Peak ${fmtN(f.peak)} wallets · ${f.shape==="grower"?"Kept growing":"One-hit"}</p><p class="c-cv">${verdict(f)}</p>
        <div class="c-cb"><button class="c-go" data-walk="${k}">Dig in</button><button class="c-more" data-act="clearn" data-k="${k}">Learn more</button></div><button class="c-moreic" data-act="clearn" data-k="${k}" aria-label="Learn more about ${esc(f.d.name)}"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3.5l4.5 4.5L6 12.5" fill="none" stroke="#1A1A1A" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg></button></article>`; }).join("")}</div>`;
  const sk=S.csheet&&S.cmp.includes(S.csheet)?S.csheet:null;
  const sheet=!sk?"":(()=>{ const i=S.cmp.indexOf(sk), f=cmpFacts(sk);
    const others=S.cmp.filter(x=>x!==sk), cols=[sk,...others], gcols=`style="grid-template-columns:repeat(3,minmax(0,1fr))"`, flat=v=>String(v).replace(/<small>/g," · ").replace(/<\/small>/g,"").replace(/^ · /,"");
    const rows=R.map(([label,fn,key,dir])=>{ if(!fn) return `<div class="c-ssec s-mono">${label}</div>`; const L=key?lead(key,dir):null, up=g=>L!=null&&g[key]===L?`<span class="c-up" data-tip="Leads this row" aria-label="Leads this row">▲</span>`:"";
      /* one column per DApp, this one first, so every value sits under its own name */
      if(others.length) return `<div class="c-sitem"><span class="c-slab">${label}</span><div class="c-sgrid" ${gcols}>${cols.map((x,j)=>{ const g=j?cmpFacts(x):f; return `<b class="${j?"":"me"}">${up(g)}${fn(g)}</b>`; }).join("")}</div></div>`;
      return `<div class="c-sitem"><div class="c-srow"><span>${label}</span><b>${up(f)}${fn(f)}</b></div></div>`; }).join("");
    return `<div class="c-sheet" role="dialog" aria-modal="true" aria-label="${esc(f.d.name)}"><button class="c-sscrim" data-act="csheet-x" aria-label="Close" tabindex="-1"></button>
      <div class="c-sbody"><div class="c-shead"><div><b>${esc(f.d.name)}</b><span class="s-mono c-cm">${f.d.cat} · ${monthLabel(f.launch)}</span></div><button class="c-sx" data-act="csheet-x" aria-label="Close">✕</button></div>
      <div class="c-art" style="background:${SOFT[i]}"><div class="ax-wrap"><span class="ax-y ax-top">Peak</span><span class="ax-y ax-bot">0</span>${spark(f,i,120,others.map(x=>[cmpFacts(x),S.cmp.indexOf(x)]))}</div><div class="ax-x"><span>Launch</span><span>Year 1</span><span>Year 2</span></div><span class="s-mono">First 2 years · share of ${others.length?"each one's peak":"peak"}</span></div>${others.length?`<div class="c-shdrw"><div class="c-sgrid c-shdr" ${gcols}>${cols.map((x,j)=>`<span class="${j?"":"me"}"><i style="background:${CMP_COL[S.cmp.indexOf(x)]}"></i>${esc(D.dapps[x].name)}</span>`).join("")}</div></div>`:""}${rows}
      <p class="c-snote">Widely used DApps only: ${Object.keys(D.dapps).length} that reached 1,000 monthly wallets with a year of history.</p>
      <div class="c-buy"><span>Walk ${esc(f.d.name)}, step by step.</span><button class="c-go" data-walk="${sk}">Dig in</button></div></div></div>`; })();
  const xs=[...Array(24).keys()];
  const fig=chart({tipx:t=>t===0?"Launch month":`Month ${t}`,w:980,h:380,r:150,x:[0,23],y:[10,2e6],log:true,xticks:[0,3,6,9,12,15,18,21,23],fx:t=>t===0?"launch":`M${t}`,yticks:[10,100,1e3,1e4,1e5,1e6],fy:fmtN,xlabel:"months after launch · monthly active wallets, log scale",
    series:SF.map((f,i)=>f&&({pts:xs.map(k=>[k,f.d.wallets[k]!=null&&f.d.wallets[k]>0?f.d.wallets[k]:null]),color:CMP_COL[i],w:2.5,dash:i===2?"5 4":null,label:f.d.name.length>16?f.d.name.slice(0,15)+"…":f.d.name,tip:f.d.name})).filter(Boolean),aria:"Monthly active wallets of the compared DApps"});
  return `<main class="study s-wrap">
    <h1 class="s-qtitle">Compare DApps <em class="o-word">side by side</em></h1>
    <p class="s-lede">Put up to three widely used DApps next to each other and read the six questions for each, row by row.</p>
    ${cards}
    <p class="c-note" hidden>▲ marks the leader in rows where higher (or, for months to 10K, lower) is better. Widely used DApps only: ${Object.keys(D.dapps).length} that reached 1,000 monthly wallets with a year of history.</p>
    ${sheet}</main>`;
}
