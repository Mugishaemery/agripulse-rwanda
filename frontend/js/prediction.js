const FLAGS = [['improved_seed', 'Improved seed'], ['organic_fert', 'Organic fertilizer'], ['pesticide', 'Pesticide / fungicide'],
  ['anti_erosion', 'Anti-erosion measures'], ['irrigated', 'Irrigated'], ['mechanized', 'Mechanized / animal traction'], ['consolidated_land', 'Land consolidation site']];
document.addEventListener('ready', async () => {
  const o = await api('/model/options');
  fillSelect($('#district'), o.districts); fillSelect($('#crop'), o.crops); fillSelect($('#season'), o.seasons); fillSelect($('#erosion_degree'), o.erosion_levels); if (o.model) { fillSelect($('#cropping_system'), o.cropping_systems); fillSelect($('#fert_rate_band'), o.fert_bands); }
  $('#flags').innerHTML = FLAGS.map(([k, l]) => `<div class="col-6"><div class="form-check"><input class="form-check-input" type="checkbox" id="${k}"><label class="form-check-label" for="${k}">${l}</label></div></div>`).join('');
  if (!o.model) { document.querySelectorAll('.ml-only').forEach(e => e.hidden = true); $('#mlnote').hidden = false; }
  $('#form').addEventListener('submit', async e => {
    e.preventDefault(); const out = $('#out');
    const body = { district: $('#district').value, crop: $('#crop').value, season: $('#season').value, plot_area_sqm: $('#area').value, erosion_degree: $('#erosion_degree').value, cropping_system: $('#cropping_system').value, fert_rate_band: $('#fert_rate_band').value };
    FLAGS.forEach(([k]) => body[k] = $('#' + k).checked);
    try { const r = await api('/predict', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      out.innerHTML = `<div class="kpi"><div class="v">${fmt(r.predicted_yield_kg_ha)} kg/ha</div><div class="l">${r.model ? 'Predicted yield (model estimate)' : 'Baseline value (not a model prediction)'}</div></div>
        <p class="mt-3">${r.interpretation}</p>
        <p class="mb-1">Likely range (80%): ${fmt(r.range_kg_ha[0])}–${fmt(r.range_kg_ha[1])} kg/ha · Estimated production for this area: ${fmt(r.predicted_production_kg)} kg</p>
        ${r.typical_error_pct ? `<p class="mb-1">Typical error of this model on plots it had not seen: about ${r.typical_error_pct}% (median). Treat the value as a rough guide, not a forecast.</p>` : ''}
        ${r.model ? (r.crop_check ? (r.crop_check.model_mdape >= r.crop_check.baseline_mdape
          ? `<div class="alert alert-warning py-2 mb-2">For ${$('#crop').value}, this model was <b>not more accurate</b> than a simple crop-and-season average on test plots (${r.crop_check.model_mdape.toFixed(1)}% vs ${r.crop_check.baseline_mdape.toFixed(1)}% median error). Treat this estimate with extra caution.</div>`
          : `<p class="mb-1 note">For ${$('#crop').value}, the model lowered the median error on test plots from ${r.crop_check.baseline_mdape.toFixed(1)}% (simple average) to ${r.crop_check.model_mdape.toFixed(1)}%.</p>`)
          : `<p class="mb-1 note">Too few test plots to check the model separately for ${$('#crop').value}.</p>`) : ''}
        ${r.official_district_yield_kg_ha ? `<p class="mb-1">For comparison, NISR&rsquo;s official ${$('#district').value} yield for this crop and season is ${fmt(r.official_district_yield_kg_ha)} kg/ha.</p>` : ''}
        <p class="note">Method: ${r.method}.${r.meta.demo ? ' <b>DEMO DATA — not an official result.</b>' : ''}</p>`;
    } catch (err) { out.innerHTML = `<div class="alert alert-warning mb-0">${err.message}</div>`; }
  });
});
