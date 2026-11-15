/* ---------- chart helper ---------- */
/* phones: draw the 980-wide charts on a 560-wide canvas so their labels stay readable */
const PHONE=()=>innerWidth<=600;
function chart(o){
  if(o.w===560){ o={...o,w:980,h:380,r:150};
    if(!o.log && o.yticks && o.yticks.length<=3){ const a=o.yticks[0], b=o.y[1], nice=raw=>{ const mag=10**Math.floor(Math.log10(raw)); return [1,2,2.5,5,10].map(x=>x*mag).find(x=>x>=raw-1e-12); }, s4=nice((b-a)/4), st=(b-a)/s4>=3.5?s4:nice((b-a)/5);
      o.yticks=[...Array(6).keys()].map(i=>a+i*st).filter(t=>t<=b+1e-9); }
    o.marks=(o.marks||[]).map(k=>({...k,r:4}));
    o.series=(o.series||[]).map(se=>({...se,w:se.w>=2.5?2.5:se.w})); }
  if(o.w===980) o.series=(o.series||[]).map(se=>({...se,w:se.w>=2.5?2.5:se.w}));
  const ph=PHONE() && o.w===980;
  if(ph) o={...o,w:560,h:Math.round((o.h||380)*1.1)+30,r:30}; /* phones: the line names sit on the lines, so the plot takes the full width */
  /* study theme, every screen: line names sit on their lines, so desktop drops the label column too */
  if(!ph&&(o.series||[]).some(se=>se.label)) o={...o,r:36};
  if(ph && (o.xticks||[]).length>8) o={...o,xticks:o.xticks.filter((x,i)=>i%2===0)};
  const W=o.w||640, H=o.h||340, m={l:52,r:o.r||118,t:26,b:ph?74:44}, xty=ph?24:20;
  const iw=W-m.l-m.r, ih=H-m.t-m.b;
  const ly = v => o.log ? Math.log10(Math.max(v,o.y[0])) : v;
  const y0=ly(o.y[0]), y1=ly(o.y[1]);
  const X = v => m.l + (v-o.x[0])/(o.x[1]-o.x[0])*iw;
  const Y = v => m.t + ih - (ly(v)-y0)/(y1-y0)*ih;
  let s = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMinYMid meet" role="img" aria-label="${esc(o.aria||"chart")}">`;
  (o.yticks||[]).forEach(t=>{ s+=`<line x1="${m.l}" x2="${m.l+iw}" y1="${Y(t)}" y2="${Y(t)}" stroke="${C.rule}"/><text class="ax" x="${m.l-10}" y="${Y(t)+4}" text-anchor="end">${o.fy?o.fy(t):t}</text>`; });
  (o.xticks||[]).forEach(t=>{ s+=`<text class="ax" x="${X(t)}" y="${m.t+ih+xty}" text-anchor="middle">${o.fx?o.fx(t):t}</text>`; });
  if(o.xlabel){ const xl=ph?o.xlabel.split(" · "):[o.xlabel]; xl.forEach((l,k)=>{ s+=`<text class="ax" x="${m.l+iw}" y="${m.t+ih+(ph?46+k*21:40)}" text-anchor="end">${l}</text>`; }); }
  (o.events||[]).forEach(e=>{ s+=`<line x1="${X(e.x)}" x2="${X(e.x)}" y1="${m.t-6}" y2="${m.t+ih}" stroke="${C.event}" stroke-width="1.5" stroke-dasharray="3 4"/><text class="ax" x="${X(e.x)}" y="${m.t-10}" text-anchor="middle" style="fill:${C.event};font-weight:500">${e.label}</text>`; });
  /* phones: the reference line's name is drawn after the data, outlined, so a line never runs through it */
  const hlText=o.hline?`<text class="axl" x="${m.l+8}" y="${Y(o.hline.y)-8}" fill="${C.ink2}" paint-order="stroke" stroke="#F5F3EE" stroke-width="6" stroke-linejoin="round">${o.hline.label}</text>`:"";
  if(o.hline) s+=`<line x1="${m.l}" x2="${m.l+iw}" y1="${Y(o.hline.y)}" y2="${Y(o.hline.y)}" stroke="${C.ink2}" stroke-dasharray="5 5"/>`;
  (o.bands||[]).forEach(b=>{
    const pts = b.hi.map(p=>`${X(p[0])},${Y(p[1])}`).concat(b.lo.slice().reverse().map(p=>`${X(p[0])},${Y(p[1])}`));
    s+=`<polygon points="${pts.join(" ")}" fill="${b.color}" opacity="${b.op||.35}"/>`;
  });
  if(o.vline!=null) s+=`<line x1="${X(o.vline)}" x2="${X(o.vline)}" y1="${m.t}" y2="${m.t+ih}" stroke="${C.muted}" stroke-width="1" stroke-dasharray="2 4"/>`;
  const labels=[];
  (o.series||[]).forEach(se=>{
    const pts = se.pts.filter(p=>p[1]!=null && (!o.log || p[1]>0));
    if(!pts.length) return;
    s+=`<polyline points="${pts.map(p=>`${X(p[0])},${Y(p[1])}`).join(" ")}" fill="none" stroke="${se.color}" stroke-width="${se.w||2.5}" stroke-linejoin="round" stroke-linecap="round" opacity="${se.op||1}"/>`;
    const last = pts[pts.length-1];
    if(se.label) labels.push({x:X(last[0]), pts:pts.map(p=>[X(p[0]),Y(p[1])]), color:se.color, text:se.label});
    if(se.dot) s+=`<circle cx="${X(last[0])}" cy="${Y(last[1])}" r="5" fill="${se.color}"/>`;
  });
  /* end-of-line labels: push apart so two lines ending close together stay readable */
  { const CW=ph?9.6:7.6, LG=ph?22:18;
    /* phones: each name sits just above the end of its line, right-aligned; when two lines end close together the lower name goes under its line */
    /* the name clears every point of its own line under it (about 9.6 units per character at 16px mono) */
    /* try above its own line, then under it, then above every line; keep the first spot that touches no line and no other name */
    const yIn=(pts,x0,x1)=>{ const out=[]; for(let i=1;i<pts.length;i++){ const [ax,ay]=pts[i-1],[bx,by]=pts[i]; for(let t=0;t<=1;t+=.1){ const x=ax+(bx-ax)*t; if(x>=x0&&x<=x1) out.push(ay+(by-ay)*t); } } if(pts.length===1&&pts[0][0]>=x0) out.push(pts[0][1]); return out; };
    const placed=[];
    /* coloured names (the DApp itself) pick their spot before the grey reference lines, so they sit nearest their own line */
    const greyL=l=>String(l.color).toUpperCase()===String(SC.grey).toUpperCase()||String(l.color).toUpperCase()===String(C.q2).toUpperCase();
    labels.sort((a,b)=>(greyL(a)-greyL(b))||(a.pts[a.pts.length-1][1]-b.pts[b.pts.length-1][1])).forEach(l=>{
      const w=l.text.length*CW+6, x0=l.x-w, own=yIn(l.pts,x0,l.x), all=labels.flatMap(o=>yIn(o.pts,x0,l.x));
      const top=Math.min(...own), bot=Math.max(...own);
      const free=y=>y>=16&&y<=m.t+ih-4&&all.every(v=>v<y-17||v>y+6)&&placed.every(p=>Math.abs(p-y)>=LG);
      /* a name never drifts more than about 90 units from the end of its own line */
      let y=[top-10,bot+24,Math.min(...all)-10,Math.min(...all)-32,Math.max(...all)+24].filter(v=>Math.abs(v-(top-10))<=90).find(free), halo=false;
      /* no clean spot: sit above its own line with a page-coloured outline so a crossing line passes behind the name */
      if(y==null){ const want=top-10, ys=[]; for(let v=16; v<=m.t+ih-4; v+=2) ys.push(v);
        const near=(a,b)=>Math.abs(a-want)-Math.abs(b-want);
        /* any clear spot within about 90 units of the line's end, else the nearest spot clear of other names, outlined */
        y=ys.filter(v=>free(v)&&Math.abs(v-want)<=90).sort(near)[0];
        if(y==null){ halo=true; y=ys.filter(v=>placed.every(p=>Math.abs(p-v)>=LG)).sort(near)[0] ?? Math.max(16,want); } }
      placed.push(y);
      s+=`<text class="axl" x="${l.x}" y="${y}" fill="${l.color}" text-anchor="end"${halo?` paint-order="stroke" stroke="#F5F3EE" stroke-width="6" stroke-linejoin="round"`:""}>${esc(l.text)}</text>`; });
    s+=hlText;
  }
  (o.marks||[]).forEach(k=>{ s+=`<circle cx="${X(k.x)}" cy="${Y(k.y)}" r="${k.r||5.5}" fill="${k.fill||C.ink}" stroke="${C.paper}" stroke-width="2"/>${k.label?`<text class="axl" x="${X(k.x)+(k.dx??10)}" y="${Y(k.y)+(k.dy??-10)}" fill="${k.fill||C.ink}" text-anchor="${k.anchor||"start"}">${esc(k.label)}</text>`:""}`; });
  /* hover columns: one per x value, each carrying the values of every labelled line at that x */
  const tipSeries=(o.series||[]).filter(se=>se.label||se.tip);
  if(tipSeries.length && o.tip!==false){
    const xsAll=[...new Set(tipSeries.flatMap(se=>se.pts.map(p=>p[0])))].sort((a,b)=>a-b);
    const fy=o.tipy||o.fy||(v=>v), hx=o.tipx||(o.fx?(x=>o.fx(x)):(x=>x));
    xsAll.forEach((x,k)=>{ const l=k?(X(xsAll[k-1])+X(x))/2:X(x)-(xsAll.length>1?(X(xsAll[1])-X(x))/2:8), r=k<xsAll.length-1?(X(x)+X(xsAll[k+1]))/2:X(x)+(xsAll.length>1?(X(x)-X(xsAll[k-1]))/2:8);
      const lines=tipSeries.map(se=>{ const pt=se.pts.find(p=>p[0]===x); return pt&&pt[1]!=null?`${se.tip||se.label}: ${fy(pt[1])}`:null; }).filter(Boolean);
      if(!lines.length) return;
      s+=`<rect class="hov" x="${Math.max(m.l,l)}" y="${m.t}" width="${Math.max(1,Math.min(m.l+iw,r)-Math.max(m.l,l))}" height="${ih}" data-tip="${esc(hx(x)+"\n"+lines.join("\n"))}"/>`; });
  }
  return s+"</svg>";
}

function seg(name, opts, cur){ return `<div class="seg">${opts.map(o=>`<button class="${o[0]===cur?"on":""}" data-${name}="${o[0]}">${o[1]}</button>`).join("")}</div>`; }
function control(label, inner){ return `<div class="control"><span class="lbl">${label}</span>${inner}</div>`; }


