document.addEventListener('ready', async () => {
  const map = L.map('map').setView([-1.95, 29.9], 8);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors', maxZoom: 12 }).addTo(map);
  const layer = L.layerGroup().addTo(map), f = { p: $('#fProvince'), d: $('#fDistrict'), s: $('#fSeason'), c: $('#fCrop') };
  const ds = await api('/districts'), crops = await api('/crops'), seasons = await api('/seasons');
  fillSelect(f.p, [...new Set(ds.map(d => d.province))], 'All provinces'); fillSelect(f.d, ds.map(d => d.name), 'All districts');
  fillSelect(f.s, seasons, 'All seasons'); fillSelect(f.c, crops, 'All crops');
  async function draw() {
    const rows = await api('/map' + qs({ province: f.p.value, district: f.d.value, season: f.s.value, crop: f.c.value }));
    layer.clearLayers();
    rows.forEach(r => L.circleMarker([r.lat, r.lng], { radius: 11, color: '#1b2024', weight: 1.5, fillColor: RISK_COLOR[r.risk], fillOpacity: .9 }).addTo(layer)
      .bindPopup(`<b>${r.district}</b> (${r.province})<br>Crop: ${f.c.value || 'all'} · Season: ${f.s.value || 'all'}<br>Production: ${fmt(Math.round(r.production_kg / 1000))} t<br>Cultivated area: ${fmt(r.cultivated_ha)} ha<br>Harvested area: ${fmt(r.harvested_ha)} ha<br>Yield: ${fmt(r.yield_kg_ha)} kg/ha<br>Risk: ${badge(r.risk)} (index ${r.index})<br><span class="note">Observed differences: ${r.observed_differences.join(', ') || 'none flagged'}</span>`));
    $('#count').textContent = rows.length + ' districts shown';
  }
  Object.values(f).forEach(e => e.addEventListener('change', draw)); draw();
});
