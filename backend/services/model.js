// Evaluates the trained yield model exported by ml/models/train_models.py (ml/models/model.json). No Python needed at run time.
const fs = require('fs'), path = require('path');
const dir = path.join(__dirname, '../../ml/models');
let model = null, metrics = null;
try { model = JSON.parse(fs.readFileSync(path.join(dir, 'model.json'), 'utf8')); metrics = JSON.parse(fs.readFileSync(path.join(dir, 'metrics.json'), 'utf8')); } catch (e) { /* not trained yet */ }
const BIN = ['improved_seed', 'inorganic_fert', 'organic_fert', 'pesticide', 'anti_erosion', 'irrigated', 'mechanized', 'consolidated_land'];
const idx = model ? Object.fromEntries(model.features.map((n, i) => [n, i])) : {};

function vector(x) {
  const v = new Float64Array(model.features.length);
  for (const c of ['district', 'crop', 'season', 'erosion_degree', 'cropping_system', 'fert_rate_band']) { const i = idx[c + '=' + x[c]]; if (i !== undefined) v[i] = 1; }
  for (const b of BIN) v[idx[b]] = x[b] ? 1 : 0;
  v[idx.log_area_ha] = Math.log(x.crop_area_ha);
  return v;
}
function predictLog(x) {
  const v = vector(x);
  if (model.kind === 'linear') return model.coef.reduce((s, c, i) => s + c * v[i], model.intercept);
  let s = model.init;
  for (const t of model.trees) { let n = 0; while (t.f[n] >= 0) n = v[t.f[n]] <= t.t[n] ? t.l[n] : t.r[n]; s += model.scale * t.v[n]; }
  return s;
}
function predict(x) {
  const s = predictLog(x);
  return { yield: Math.exp(s), low: Math.exp(s + model.resid_q10), high: Math.exp(s + model.resid_q90) };
}
module.exports = { available: !!model, model, metrics, predict, predictLog };
