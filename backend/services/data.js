// Data access + analytics. Three modes, chosen automatically:
//  'aggregate' : data/processed/aggregates.json  = NISR SAS 2024 published district tables (REAL)  <- current
//  'record'    : data/processed/records.json     = NISR plot-level microdata (REAL, once available)
//  'demo'      : data/demo/records.json          = synthetic UI data (DEMO)
// Row shape (all modes): district, province, crop, season, plot_area_sqm (= harvested area), cultivated_ha, production_kg, yield_kg_ha
const fs = require('fs'), path = require('path');
const districts = require('./districts');
const root = path.join(__dirname, '../..'), P = f => path.join(root, f), J = f => JSON.parse(fs.readFileSync(P(f), 'utf8'));
const mode = fs.existsSync(P('data/processed/aggregates.json')) ? 'aggregate' : fs.existsSync(P('data/processed/records.json')) ? 'record' : 'demo';
let records, inputRows = [], source = '';
if (mode === 'aggregate') {
  const a = J('data/processed/aggregates.json'); source = a.source; inputRows = a.inputs;
  records = a.rows.map(r => ({ district: r.district, province: r.province, crop: r.crop, season: r.season, cultivated_ha: r.cultivated_ha,
    plot_area_sqm: r.harvested_ha * 10000, production_kg: r.production_mt * 1000, yield_kg_ha: r.yield_kg_ha }));
} else records = J(mode === 'record' ? 'data/processed/records.json' : 'data/demo/records.json');
const demo = mode === 'demo';
const meta = { demo, mode, records: records.length, source: source || (demo ? 'Synthetic demo data' : 'NISR SAS 2024'),
  label: demo ? 'DEMO DATA — Replace with NISR SAS 2024 data' : 'NISR SAS 2024' };

const ha = r => r.plot_area_sqm / 10000, cult = r => r.cultivated_ha != null ? r.cultivated_ha : ha(r);
const uniq = k => [...new Set(records.map(r => r[k]))].sort();
const lists = { crops: uniq('crop'), seasons: uniq('season'), provinces: uniq('province'), districts: districts.map(d => d.name) };

function filter(q = {}) {
  return records.filter(r => (!q.province || r.province === q.province) && (!q.district || r.district === q.district)
    && (!q.season || r.season === q.season) && (!q.crop || r.crop === q.crop));
}
// Pooled yield = total production / total harvested area (ratio of sums) - matches NISR's definition for aggregates.
function summarize(rows) {
  const area = rows.reduce((a, r) => a + ha(r), 0), prod = rows.reduce((a, r) => a + r.production_kg, 0);
  return { n: rows.length, cultivated_ha: Math.round(rows.reduce((a, r) => a + cult(r), 0)), harvested_ha: Math.round(area),
    area_ha: Math.round(area), production_kg: Math.round(prod), yield_kg_ha: area ? Math.round(prod / area) : null };
}
function groupBy(rows, key) {
  const m = new Map(); rows.forEach(r => { const k = typeof key === 'function' ? key(r) : r[key]; (m.get(k) || m.set(k, []).get(k)).push(r); });
  return [...m].map(([k, v]) => ({ key: k, ...summarize(v) })).sort((a, b) => b.yield_kg_ha - a.yield_kg_ha);
}
// Observed/expected index: expected = harvested area x national yield of the SAME crop and season. 1.0 = national level.
const nat = Object.fromEntries(Object.entries(records.reduce((m, r) => { (m[r.crop + '|' + r.season] = m[r.crop + '|' + r.season] || []).push(r); return m; }, {})).map(([k, v]) => [k, summarize(v).yield_kg_ha]));
const index = rows => { const e = rows.reduce((a, r) => a + ha(r) * (nat[r.crop + '|' + r.season] || 0), 0); return e ? rows.reduce((a, r) => a + r.production_kg, 0) / e : null; };
// RULE-BASED thresholds (provisional; see docs/methodology.md).
const level = i => (i == null ? 'N/A' : i < 0.9 ? 'HIGH' : i < 1.0 ? 'MEDIUM' : 'LOW');

const FACTORS = { improved_seed_pct: 'improved seed', organic_fertilizer_pct: 'organic fertilizer', inorganic_fertilizer_pct: 'inorganic fertilizer', pesticide_pct: 'pesticide',
  irrigation_pct: 'irrigation', erosion_protection_pct: 'erosion protection', mechanization_pct: 'mechanization' };
const inputFor = (d, season) => { const rs = inputRows.filter(x => x.district === d && (!season || x.season === season));
  const avg = k => { const v = rs.map(x => x[k]).filter(x => x != null); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
  return Object.fromEntries([...Object.keys(FACTORS), 'erosion_severe_pct', 'erosion_moderate_pct'].map(k => [k, avg(k)])); };
const pearson = (x, y) => { const n = x.length, mx = x.reduce((a, b) => a + b) / n, my = y.reduce((a, b) => a + b) / n;
  let sxy = 0, sxx = 0, syy = 0; x.forEach((v, i) => { sxy += (v - mx) * (y[i] - my); sxx += (v - mx) ** 2; syy += (y[i] - my) ** 2; }); return sxx && syy ? sxy / Math.sqrt(sxx * syy) : null; };

// Aggregate mode: association between district input shares and the district productivity index (30 districts, same season).
function inputs(q = {}) {
  if (mode !== 'aggregate') return { available: false, message: 'District input shares need the aggregate tables.' };
  const season = q.season || 'A', tbl = riskTable({ season, crop: q.crop });
  const out = Object.entries(FACTORS).map(([k, label]) => { const pts = tbl.map(t => [inputFor(t.district, season)[k], t.index]).filter(p => p[0] != null && p[1] != null);
    return { factor: k, label, r: pts.length > 4 ? +pearson(pts.map(p => p[0]), pts.map(p => p[1])).toFixed(2) : null, n: pts.length }; });
  return { available: true, season, factors: out };
}
function riskTable(q) {
  const rows = filter({ season: q.season, crop: q.crop, province: q.province });
  const share = (rs, f) => rs.length ? rs.filter(r => r[f]).length / rs.length : 0;
  const nationalIn = k => { const v = districts.map(d => inputFor(d.name, q.season)[k]).filter(x => x != null); return v.reduce((a, b) => a + b, 0) / (v.length || 1); };
  return districts.map(d => {
    const rs = rows.filter(r => r.district === d.name); const i = index(rs); let flags = [];
    if (mode === 'aggregate') { const inp = inputFor(d.name, q.season);
      flags = Object.entries(FACTORS).filter(([k]) => inp[k] != null && inp[k] + 5 < nationalIn(k)).map(([, l]) => 'lower use of ' + l);
      const er = (inp.erosion_severe_pct || 0) + (inp.erosion_moderate_pct || 0), erN = (nationalIn('erosion_severe_pct') || 0) + (nationalIn('erosion_moderate_pct') || 0);
      if (er - 3 > erN) flags.push('more plots with severe/moderate erosion');
    } else if (mode === 'record' || demo) {
      flags = ['irrigated', 'fertilizer_inorganic', 'improved_seed', 'mechanized'].filter(f => share(rs, f) + 0.05 < share(rows, f)).map(f => 'lower use of ' + f.replace('_', ' '));
    }
    return { district: d.name, province: d.province, lat: d.lat, lng: d.lng, ...summarize(rs), index: i == null ? null : +i.toFixed(2), risk: level(i), observed_differences: flags };
  }).filter(r => r.n > 0).sort((a, b) => a.index - b.index);
}
// Estimator. aggregate: OFFICIAL district yield for crop+season (a baseline, NOT a model). demo/record: similar-record average.
function predict(x) {
  if (mode === 'aggregate') {
    const cell = records.find(r => r.district === x.district && r.crop === x.crop && r.season === x.season && r.yield_kg_ha);
    const natR = records.filter(r => r.crop === x.crop && r.season === x.season);
    if (!cell && !natR.length) return null;
    const y = cell ? Math.round(cell.yield_kg_ha) : summarize(natR).yield_kg_ha;
    const ys = natR.map(r => r.yield_kg_ha).filter(Boolean).sort((a, b) => a - b);
    return { predicted_yield_kg_ha: y, range_kg_ha: [ys[Math.floor(ys.length * .25)], ys[Math.floor(ys.length * .75)]], predicted_production_kg: Math.round(y * x.plot_area_sqm / 10000),
      matched_records: cell ? 1 : natR.length, matched_on: cell ? ['district', 'crop', 'season'] : ['crop', 'season'],
      method: cell ? 'Official NISR district yield for this crop and season (baseline, not a trained model)' : 'National yield for this crop and season (no district value published)' };
  }
  const tries = [['crop', 'season', 'district', 'improved_seed', 'fertilizer_inorganic', 'irrigated', 'erosion', 'mechanized'], ['crop', 'season', 'district'], ['crop', 'season'], ['crop']];
  for (const keys of tries) {
    const m = records.filter(r => keys.every(k => r[k] === x[k]));
    if (m.length >= 20) { const ys = m.map(r => r.yield_kg_ha).sort((a, b) => a - b), mean = ys.reduce((a, b) => a + b, 0) / ys.length;
      return { predicted_yield_kg_ha: Math.round(mean), range_kg_ha: [ys[Math.floor(ys.length * .25)], ys[Math.floor(ys.length * .75)]],
        predicted_production_kg: Math.round(mean * x.plot_area_sqm / 10000), matched_records: m.length, matched_on: keys,
        method: demo ? 'demo-lookup (similar-record average, NOT a trained model)' : 'similar-record average' }; }
  }
  return null;
}
const officialYield = (d, c, se) => { const r = records.find(x => x.district === d && x.crop === c && x.season === se && x.yield_kg_ha); return r ? Math.round(r.yield_kg_ha) : null; };
module.exports = { officialYield, meta, lists, districts, records, filter, summarize, groupBy, inputs, riskTable, predict, level };
