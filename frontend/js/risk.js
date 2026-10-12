document.addEventListener('ready', async () => {
  const f = { s: $('#fSeason'), c: $('#fCrop') }; fillSelect(f.s, await api('/seasons'), 'All seasons'); fillSelect(f.c, await api('/crops'), 'All crops');
  async function load() {
    const r = await api('/risk' + qs({ season: f.s.value, crop: f.c.value })); $('#method').textContent = r.method;
    const rows = r.rows; const cnt = l => rows.filter(x => x.risk === l).length;
    $('#kpis').innerHTML = ['HIGH', 'MEDIUM', 'LOW'].map(l => `<div class="col-4"><div class="kpi"><div class="v">${cnt(l)}</div><div class="l">${badge(l)} districts</div></div></div>`).join('');
    $('#tbody').innerHTML = rows.map(x => `<tr><td>${x.district}</td><td>${x.province}</td><td>${fmt(x.yield_kg_ha)}</td><td>${x.index}</td><td>${badge(x.risk)}</td><td>${fmt(x.n)}</td></tr>`).join('');
    const pri = rows.filter(x => x.risk === 'HIGH').slice(0, 5);
    $('#intervene').innerHTML = pri.length ? pri.map(x => `<div class="col-md-6"><div class="panel h-100"><h3>${x.district} <small class="note">${x.province}</small></h3>
      <p class="mb-1"><b>Reason:</b> observed yield is ${Math.round((1 - x.index) * 100)}% below the level expected from the national yield for the same crops.</p>
      <p class="mb-0"><b>Potential area for investigation:</b> ${x.observed_differences.length ? 'observed differences vs. other districts: ' + x.observed_differences.join('; ') : 'no input difference flagged in this data; check other local factors'}. <span class="note">Association only, not proof of cause.</span></p></div></div>`).join('')
      : '<p class="note">No HIGH-risk districts for this selection.</p>';
  }
  Object.values(f).forEach(e => e.addEventListener('change', load)); load();
});
