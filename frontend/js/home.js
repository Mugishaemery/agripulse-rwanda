// Hero snapshot: yield by crop, straight from the API (shows DEMO label while demo data is in use).
document.addEventListener('ready', async () => {
  const d = (await api('/productivity?by=crop')).sort((a, b) => b.cultivated_ha - a.cultivated_ha).slice(0, 6), max = Math.max(...d.map(x => x.yield_kg_ha));
  $('#snap').innerHTML = `<h2>Yield of the six most-cultivated crops (kg/ha)</h2>` + d.map(x => `<div class="row-b"><span>${x.key}</span><div class="bar"><i style="width:${Math.round(x.yield_kg_ha / max * 100)}%"></i></div><span class="v">${fmt(x.yield_kg_ha)}</span></div>`).join('')
    + `<div class="foot">${window.META && META.demo ? 'DEMO DATA — not official NISR results' : 'Source: NISR SAS 2024'}</div>`;
});
