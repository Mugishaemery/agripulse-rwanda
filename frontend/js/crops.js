document.addEventListener('ready', async () => {
  const sel = $('#crop'); const crops = await api('/crops'); fillSelect(sel, crops);
  const rank = await api('/productivity?by=crop');
  chart('cRank', 'bar', rank.map(x => x.key), [{ data: rank.map(x => x.yield_kg_ha), backgroundColor: rank.map(x => x.key === sel.value ? '#c8f31d' : '#2a3136') }], { indexAxis: 'y', plugins: { legend: { display: false } } });
  async function show() {
    const c = sel.value, sum = rank.find(x => x.key === c);
    $('#kpis').innerHTML = [['Production (tonnes)', Math.round(sum.production_kg / 1000)], ['Cultivated area (ha)', sum.cultivated_ha], ['Harvested area (ha)', sum.harvested_ha], ['Yield (kg/ha)', sum.yield_kg_ha]].map(([l, v]) => `<div class="col-6 col-md-3"><div class="kpi"><div class="v">${fmt(v)}</div><div class="l">${l}</div></div></div>`).join('');
    const dist = await api('/productivity?by=district&crop=' + encodeURIComponent(c)), sea = await api('/productivity?by=season&crop=' + encodeURIComponent(c)), h = await api('/distribution?crop=' + encodeURIComponent(c));
    chart('cDistrict', 'bar', dist.map(x => x.key), [{ data: dist.map(x => x.yield_kg_ha), backgroundColor: '#2a3136' }], { indexAxis: 'y', plugins: { legend: { display: false } } });
    chart('cSeason', 'bar', sea.map(x => x.key), [{ data: sea.map(x => x.yield_kg_ha), backgroundColor: '#a9d11a' }], { plugins: { legend: { display: false } } });
    chart('cHist', 'bar', h.map(b => `${fmt(b.from)}–${fmt(b.to)}`), [{ data: h.map(b => b.count), backgroundColor: '#1b2024' }], { plugins: { legend: { display: false } } });
    $('#best').innerHTML = dist.length ? `Highest observed: <b>${dist[0].key}</b> (${fmt(dist[0].yield_kg_ha)} kg/ha) · Lowest: <b>${dist.at(-1).key}</b> (${fmt(dist.at(-1).yield_kg_ha)} kg/ha)` : '';
  }
  sel.addEventListener('change', show); show();
});
