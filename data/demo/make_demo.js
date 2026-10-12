// Generates SYNTHETIC records for UI development ONLY. NOT NISR DATA.
// Output: data/demo/records.json  (record shape = what data/processed/records.json must follow)
const fs = require('fs'), path = require('path');
const districts = require('../../backend/services/districts');
let s = 42; const rnd = () => { s |= 0; s = (s + 0x6D2B79F5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const crops = { Maize: 1800, Beans: 900, Cassava: 5000, 'Irish potato': 8000, 'Sweet potato': 6000, Banana: 7000 };
const dFactor = Object.fromEntries(districts.map(d => [d.name, 0.7 + rnd() * 0.6]));
const sFactor = { A: 1.05, B: 1.0, C: 0.85 };
const out = [];
for (let i = 0; i < 4000; i++) {
  const d = districts[Math.floor(rnd() * 30)], crop = Object.keys(crops)[Math.floor(rnd() * 6)];
  const season = ['A', 'B', 'B', 'A', 'C'][Math.floor(rnd() * 5)];
  const f = { improved_seed: rnd() < .4, fertilizer_inorganic: rnd() < .35, irrigated: rnd() < .12, mechanized: rnd() < .1 };
  const erosion = ['None', 'Low', 'High'][Math.floor(rnd() * 3)];
  const area = Math.round(200 + rnd() * rnd() * 8000);
  let y = crops[crop] * dFactor[d.name] * sFactor[season] * (1 + .12 * f.improved_seed + .1 * f.fertilizer_inorganic + .08 * f.irrigated - .08 * (erosion === 'High')) * (0.7 + rnd() * 0.6);
  y = Math.round(y);
  out.push({ district: d.name, province: d.province, crop, season, plot_area_sqm: area, ...f, erosion,
    yield_kg_ha: y, production_kg: Math.round(y * area / 10000) });
}
fs.writeFileSync(path.join(__dirname, 'records.json'), JSON.stringify(out));
console.log('DEMO DATA written:', out.length, 'synthetic records');
