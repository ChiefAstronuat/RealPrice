const qs = new URLSearchParams(location.search);
const state = {
  region: qs.get('region') || '11',
  spec: qs.get('spec') || 'SP001',
  range: qs.get('range') || '90',
  mode: qs.get('mode') || 'both',
  band: qs.get('band') === '1',
  smooth: qs.get('smooth') === '1'
};

const el = (id) => document.getElementById(id);

function fmt(v){ return v == null ? '-' : `${Math.round(v).toLocaleString()} KRW/kg`; }

function applyQuery(){
  const p = new URLSearchParams({
    region: state.region, spec: state.spec, range: state.range, mode: state.mode,
    band: state.band ? '1':'0', smooth: state.smooth ? '1':'0'
  });
  history.replaceState(null,'',`/sweetpotato?${p.toString()}`);
}

function movingMedian(data, key, w=3){
  return data.map((_,i)=>{
    const s=Math.max(0,i-w), e=Math.min(data.length-1,i+w);
    const arr=data.slice(s,e+1).map(d=>d[key]).filter(v=>v!=null).sort((a,b)=>a-b);
    if(!arr.length) return null;
    return arr[Math.floor(arr.length/2)];
  });
}

function drawChart(points){
  const canvas = el('chart');
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0,0,w,h);
  if(!points.length) return;

  const vals = [];
  points.forEach(p=>{ if(p.final!=null) vals.push(p.final); if(p.nowcast!=null) vals.push(p.nowcast); if(state.mode!=='final'&&p.retail!=null) vals.push(p.retail); if(state.band){vals.push(p.p10,p.p90);} });
  const min = Math.min(...vals)*0.95;
  const max = Math.max(...vals)*1.05;
  const x = i => 50 + (i/(points.length-1||1))*(w-80);
  const y = v => h-40 - ((v-min)/(max-min||1))*(h-80);

  // recent 3-day shade
  const startRecent = Math.max(0, points.length-3);
  ctx.fillStyle = 'rgba(242,201,76,0.25)';
  ctx.fillRect(x(startRecent),20,w-x(startRecent)-30,h-60);

  // p10 p90 band
  if(state.band){
    ctx.beginPath();
    points.forEach((p,i)=>{ const xx=x(i), yy=y(p.p10); if(i===0) ctx.moveTo(xx,yy); else ctx.lineTo(xx,yy);});
    for(let i=points.length-1;i>=0;i--){ const p=points[i]; ctx.lineTo(x(i),y(p.p90)); }
    ctx.closePath();
    ctx.fillStyle = 'rgba(79,129,189,0.15)';
    ctx.fill();
  }

  const finalSeries = state.smooth ? movingMedian(points,'final') : points.map(p=>p.final);
  const nowcastSeries = state.smooth ? movingMedian(points,'nowcast') : points.map(p=>p.nowcast);
  const retailSeries = points.map(p=>p.retail);

  function line(series, color, dashed=false){
    ctx.beginPath();
    ctx.setLineDash(dashed?[6,6]:[]);
    ctx.strokeStyle = color; ctx.lineWidth=2;
    let started=false;
    series.forEach((v,i)=>{ if(v==null) return; const xx=x(i), yy=y(v); if(!started){ctx.moveTo(xx,yy); started=true;} else ctx.lineTo(xx,yy);});
    ctx.stroke(); ctx.setLineDash([]);
  }

  line(finalSeries,'#2563eb',false);
  if(state.mode!=='final') line(nowcastSeries,'#ef4444',true);
  if(state.mode!=='final') line(retailSeries,'#16a34a',false);

  // axes
  ctx.strokeStyle='#777'; ctx.lineWidth=1;
  ctx.beginPath(); ctx.moveTo(50,20); ctx.lineTo(50,h-40); ctx.lineTo(w-30,h-40); ctx.stroke();
  ctx.fillStyle='#444'; ctx.font='12px sans-serif';
  ctx.fillText(`${Math.round(max).toLocaleString()}`,8,24);
  ctx.fillText(`${Math.round(min).toLocaleString()}`,8,h-40);
}

async function load(){
  const [specs, regions] = await Promise.all([
    fetch('/api/v1/sweetpotato/specs').then(r=>r.json()),
    fetch('/api/v1/regions?level=si_do').then(r=>r.json())
  ]);

  el('spec').innerHTML = specs.map(s=>`<option value="${s.spec_id}">${s.label}</option>`).join('');
  el('region').innerHTML = regions.map(r=>`<option value="${r.region_id}">${r.region_name}</option>`).join('');

  el('spec').value = state.spec; el('region').value = state.region;
  el('range').value = state.range; el('mode').value = state.mode;
  el('band').checked = state.band; el('smooth').checked = state.smooth;

  const summary = await fetch(`/api/v1/sweetpotato/summary?spec_id=${state.spec}&region_id=${state.region}`).then(r=>r.json());
  el('final').textContent = fmt(summary.final);
  el('nowcast').textContent = fmt(summary.nowcast);
  el('confidence').textContent = `신뢰도 ${Math.round(summary.confidence*100)}%`;
  el('rangeText').textContent = `범위 ${summary.p10} ~ ${summary.p90}`;
  el('delta').textContent = `전일 ${summary.delta_day > 0 ? '+' : ''}${summary.delta_day}, 전주 ${summary.delta_week > 0 ? '+' : ''}${summary.delta_week}`;
  el('asof').textContent = summary.as_of;
  el('note').textContent = summary.note;

  const end = new Date(summary.date);
  const start = new Date(end);
  if(Number(state.range) < 9999) start.setDate(end.getDate() - Number(state.range));
  else start.setFullYear(end.getFullYear()-10);
  const startStr = start.toISOString().slice(0,10);
  const points = await fetch(`/api/v1/sweetpotato/timeseries?spec_id=${state.spec}&region_id=${state.region}&start=${startStr}&end=${summary.date}&mode=${state.mode}`).then(r=>r.json());
  drawChart(points);

  const market = await fetch(`/api/v1/sweetpotato/market_breakdown?spec_id=${state.spec}&date=${summary.date}`).then(r=>r.json());
  el('marketTable').querySelector('tbody').innerHTML = market.markets.map(m =>
    `<tr><td>${m.market_name}</td><td>${m.median_price}</td><td>${Math.round(m.volume_kg)}</td><td>${m.p10}/${m.p90}</td><td>${m.trades}</td></tr>`
  ).join('');
}

['region','spec','range','mode','band','smooth'].forEach(id=>{
  el(id).addEventListener('change',()=>{
    state.region=el('region').value; state.spec=el('spec').value; state.range=el('range').value;
    state.mode=el('mode').value; state.band=el('band').checked; state.smooth=el('smooth').checked;
    applyQuery(); load();
  });
});

load();
