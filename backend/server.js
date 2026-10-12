require('dotenv').config();
const express = require('express'), cors = require('cors'), path = require('path');
const D = require('./services/data'), M = require('./services/model');
D.meta.model = M.available;
const app = express();
const origins = (process.env.CORS_ORIGINS || '').split(',').filter(Boolean);
app.use(cors(origins.length ? { origin: origins } : undefined));
app.use(express.json({ limit: '10kb' }));
app.use(express.static(path.join(__dirname, '../frontend'), { extensions: ['html'] }));

// Only whitelisted filters are read from the query string.
const q = r => Object.fromEntries(['province', 'district', 'season', 'crop'].filter(k => r.query[k]).map(k => [k, String(r.query[k])]));
const api = express.Router();
api.get('/overview', (req, res) => { const rows = D.filter(q(req));
  res.json({ meta: D.meta, districts: new Set(rows.map(r => r.district)).size, crops: new Set(rows.map(r => r.crop)).size,
    seasons: new Set(rows.map(r => r.season)).size, ...D.summarize(rows) }); });
api.get('/districts', (req, res) => res.json(D.districts));
api.get('/crops', (req, res) => res.json(D.lists.crops));
api.get('/seasons', (req, res) => res.json(D.lists.seasons));
api.get('/productivity', (req, res) => {
  const by = req.query.by || 'crop';
  if (!['crop', 'season', 'district', 'province'].includes(by)) return res.status(400).json({ error: 'by must be crop|season|district|province' });
  res.json(D.groupBy(D.filter(q(req)), by)); });
api.get('/productivity/district/:district', (req, res) => res.json(D.groupBy(D.filter({ ...q(req), district: req.params.district }), 'crop')));
api.get('/productivity/crop/:crop', (req, res) => res.json(D.groupBy(D.filter({ ...q(req), crop: req.params.crop }), 'district')));
api.get('/inputs', (req, res) => res.json(D.inputs(q(req))));
api.get('/distribution', (req, res) => { // histogram of plot yields
  const ys = D.filter(q(req)).map(r => r.yield_kg_ha).filter(Boolean); if (!ys.length) return res.json([]);
  const max = Math.max(...ys), w = Math.ceil(max / 10 / 100) * 100, b = Array.from({ length: 10 }, (_, i) => ({ from: i * w, to: (i + 1) * w, count: 0 }));
  ys.forEach(y => b[Math.min(9, Math.floor(y / w))].count++); res.json(b); });
api.get('/map', (req, res) => res.json(D.riskTable(q(req))));
api.get('/risk', (req, res) => res.json({ method: 'Rule-based (not ML): index = observed production / expected production, where expected = harvested area x national yield of the same crop and season. HIGH if index < 0.90, MEDIUM if < 1.00, otherwise LOW. Thresholds are provisional.', rows: D.riskTable(q(req)) }));
api.post('/predict', (req, res) => {
  const b = req.body || {}, errs = [], ok = M.available ? M.model.meta : null;
  if (!(ok ? ok.crops : D.lists.crops).includes(b.crop)) errs.push('crop invalid');
  if (!D.lists.districts.includes(b.district)) errs.push('district invalid');
  if (!D.lists.seasons.includes(b.season)) errs.push('season invalid');
  if (!(Number(b.plot_area_sqm) > 0 && Number(b.plot_area_sqm) <= 1e6)) errs.push('plot_area_sqm must be 1..1000000');
  const levels = ok ? ok.erosion_levels : ['None', 'Low', 'High'];
  if (b.erosion_degree && !levels.includes(b.erosion_degree)) errs.push('erosion_degree invalid');
  if (ok && b.cropping_system && !ok.cropping_systems.includes(b.cropping_system)) errs.push('cropping_system invalid');
  if (ok && b.fert_rate_band && !ok.fert_bands.includes(b.fert_rate_band)) errs.push('fert_rate_band invalid');
  if (errs.length) return res.status(400).json({ errors: errs });
  const flags = ['improved_seed', 'inorganic_fert', 'organic_fert', 'pesticide', 'anti_erosion', 'irrigated', 'mechanized', 'consolidated_land'];
  const x = { district: b.district, crop: b.crop, season: b.season, erosion_degree: b.erosion_degree || 'Low', cropping_system: b.cropping_system || 'Pure', fert_rate_band: b.fert_rate_band || 'None', crop_area_ha: Number(b.plot_area_sqm) / 10000 };
  flags.forEach(k => x[k] = !!b[k]);
  x.inorganic_fert = x.fert_rate_band !== 'None';          // derived from the fertilizer rate
  const official = D.officialYield(b.district, b.crop, b.season);
  if (M.available) { // trained model
    const p = M.predict(x), bm = M.metrics.models.find(m => m.name === M.metrics.best) || {}, r2 = bm.r2;
    return res.json({ meta: D.meta, model: true, predicted_yield_kg_ha: Math.round(p.yield), range_kg_ha: [Math.round(p.low), Math.round(p.high)],
      predicted_production_kg: Math.round(p.yield * x.crop_area_ha), official_district_yield_kg_ha: official, typical_error_pct: bm.mdape, crop_check: (M.metrics.by_crop || []).find(c => c.crop === b.crop) || null,
      method: `${M.metrics.best} trained on ${M.metrics.n_train.toLocaleString()} NISR SAS 2024 plots (median error on unseen plots: ${bm.mdape}%)`,
      interpretation: `Based on the characteristics provided, the model estimate for expected yield is approximately ${Math.round(p.yield).toLocaleString()} kg/ha. This is an estimate, not a guarantee.` });
  }
  const p = D.predict({ ...x, plot_area_sqm: Number(b.plot_area_sqm) }); if (!p) return res.status(422).json({ error: 'Not enough similar records to estimate.' });
  res.json({ meta: D.meta, model: false, ...p, official_district_yield_kg_ha: official,
    interpretation: `No trained model is loaded. The baseline value shown is approximately ${p.predicted_yield_kg_ha.toLocaleString()} kg/ha. This is not a model prediction.` });
});
api.get('/model/performance', (req, res) => res.json(M.available ? M.metrics : { available: false, message: 'No trained model yet. Run ml/models/train_models.py after building the microdata set.' }));
api.get('/model/features', (req, res) => res.json(M.available ? { available: true, features: M.metrics.feature_importance } : { available: false, message: 'Feature importance is generated when the model is trained.' }));
api.get('/model/options', (req, res) => res.json(M.available ? { model: true, ...M.model.meta } : { model: false, crops: D.lists.crops, districts: D.lists.districts, seasons: D.lists.seasons, erosion_levels: ['None', 'Low', 'High'] }));
app.use('/api', api);
app.use('/api', (req, res) => res.status(404).json({ error: 'Not found' }));
app.use((err, req, res, next) => { console.error(err); res.status(500).json({ error: 'Server error' }); });
const port = process.env.PORT || 3000;
if (require.main === module) app.listen(port, () => console.log(`AgriPulse on :${port} [${D.meta.label}]`));
module.exports = app;
