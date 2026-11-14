const D = window.DEMO;
const CATS = D.meta.categories;
const PERIOD = {before:"Before Terra", between:"Terra → Dencun", after:"After Dencun"};
const PERIOD_IN = {before:"before Terra", between:"between Terra and Dencun", after:"after Dencun"};
const QNAME = {q1:"Categories", q2:"Survival", q3:"Concentration", q4:"Speed", q5:"Retention", q6:"Take-off"};
const PNAME = {q5:"Retention", q3:"Concentration", q1:"Categories", q2:"Survival", q3a:"Who holds the wallets", q3b:"A long tail", q4:"Speed", q5a:"Retention", q5b:"What predicts success", q6:"Take-off"};
const BOOKS = {
  s1:{pages:["q2","q4","q5","q6","q3","q1"], time:"The DApp's own time", title:"Your DApp"},
  s2:{pages:["q1","q3","q2","q5","q4"], time:"The market's time", title:"The market"},
};
let C = {};
function setTheme(){
  document.documentElement.dataset.theme="study";
  const cs=getComputedStyle(document.documentElement), v=n=>cs.getPropertyValue(n).trim();
  C={ref:v("--ref")||v("--ink"), event:v("--event")||v("--loud"), band:v("--band")||v("--q1-soft"), ink:v("--ink"), ink2:v("--ink-2"), q1:v("--q1"), q1s:v("--q1-soft"), q2:v("--q2"), loud:v("--loud"), muted:v("--muted"), rule:v("--rule"), paper:v("--paper")};
}

const S = {view:"home", scen:null, idx:0, read:[], dapp:null, custom:null, cat:"DeFi", era:null,
           q1m:null, q3m:null, q3k:10, q4m:6, q6metric:"retention_prev_month", pickTab:"pick", query:"", from:"home"};

const $ = s => document.querySelector(s);
const pct = (x,d=0) => x==null ? "–" : (x*100).toFixed(d)+"%";
const sgn = (x,d=0) => x==null ? "–" : (x>0?"+":x<0?"−":"")+Math.abs(x*100).toFixed(d)+"%";
const fmtN = n => n==null ? "–" : n>=1e9 ? (n/1e9).toFixed(n>=1e10?0:1)+"B" : n>=1e6 ? (n/1e6).toFixed(n>=1e7?0:1)+"M" : n>=1e3 ? (n/1e3).toFixed(n>=1e4?0:1)+"K" : String(Math.round(n));
const comma = n => Math.round(n).toLocaleString("en-US");
const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const monthLabel = m => { const [y,mm]=m.split("-"); return MON[+mm-1]+" "+y; };
const periodOf = m => m < D.meta.terra ? "before" : m < D.meta.dencun ? "between" : "after";
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const K = s => `<em class="k">${s}</em>`;
const qOf = p => p.slice(0,2);

function me(){ return S.custom || (S.dapp ? {...D.dapps[S.dapp], slug:S.dapp} : null); }
function pages(){ return BOOKS[S.scen].pages; }
function era(){ const d=me(); return S.era || (d?d.period:"between"); }

