document.addEventListener('ready', async () => {
  const o = await api('/overview');
  $('#kpis').innerHTML = [['Data cells (district × crop × season)', o.n], ['Districts', o.districts], ['Crops', o.crops], ['Seasons', o.seasons], ['Cultivated area (ha)', o.cultivated_ha], ['Production (tonnes)', Math.round(o.production_kg / 1000)]]
    .map(([l, v]) => `<div class="col-6 col-md-4 col-xl-2"><div class="kpi"><div class="v">${fmt(v)}</div><div class="l">${l}</div></div></div>`).join('');
  const noLegend = { plugins: { legend: { display: false } } };
  const crops = await api('/productivity?by=crop');
  chart('cCrop', 'bar', crops.map(x => x.key), [{ label: 'Yield (kg/ha)', data: crops.map(x => x.yield_kg_ha), backgroundColor: '#2a3136' }], noLegend);
  const seasons = await api('/seasons'), cols = { A: '#2a3136', B: '#a9d11a', C: '#79838b' };
  const bySeason = await Promise.all(seasons.map(s => api('/productivity?by=crop&season=' + s)));
  chart('cSeason', 'bar', crops.map(x => x.key), seasons.map((s, i) => ({ label: 'Season ' + s, backgroundColor: cols[s], data: crops.map(c => (bySeason[i].find(x => x.key === c.key) || {}).yield_kg_ha ?? null) })));
  const dist = (await api('/map')).sort((a, b) => b.index - a.index);
  chart('cDistrict', 'bar', dist.map(x => x.district), [{ label: 'Productivity index', data: dist.map(x => x.index), backgroundColor: dist.map(x => RISK_COLOR[x.risk]) }], { indexAxis: 'y', ...noLegend });
  const byArea = [...crops].sort((a, b) => b.cultivated_ha - a.cultivated_ha);
  chart('cDist', 'bar', byArea.map(x => x.key), [{ label: 'Cultivated area (ha)', data: byArea.map(x => x.cultivated_ha), backgroundColor: '#2a3136' }], { indexAxis: 'y', ...noLegend });
  async function inputs() {
    const r = await api('/inputs?season=' + $('#inSeason').value); if (!r.available) return;
    chart('cInput', 'bar', r.factors.map(f => f.label), [{ label: 'Correlation with productivity index', data: r.factors.map(f => f.r), backgroundColor: r.factors.map(f => f.r >= 0 ? '#a9d11a' : '#79838b') }], { ...noLegend, scales: { y: { min: -1, max: 1 } } });
  }
  fillSelect($('#inSeason'), seasons); $('#inSeason').addEventListener('change', inputs); inputs();
});
