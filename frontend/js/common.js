// Shared helpers: nav, API client, formatting, DEMO banner.
const PAGES = [['/', 'Home'], ['/dashboard', 'Dashboard'], ['/map', 'Map'], ['/crops', 'Crops'], ['/prediction', 'Prediction'], ['/risk', 'Risk'], ['/about', 'About']];
const $ = s => document.querySelector(s);
const fmt = n => n == null ? '—' : Number(n).toLocaleString();
const RISK_COLOR = { HIGH: '#b3392f', MEDIUM: '#c9871a', LOW: '#2e7d4f', 'N/A': '#667267' };
const badge = l => `<span class="badge-risk b-${l === 'N/A' ? 'NA' : l}">${l}</span>`;
async function api(path, opts) {
  const r = await fetch('/api' + path, opts), j = await r.json();
  if (!r.ok) throw new Error((j.errors || [j.error]).join(', ')); return j;
}
const qs = o => { const p = new URLSearchParams(Object.entries(o).filter(([, v]) => v)); return p.toString() ? '?' + p : ''; };
function fillSelect(el, items, allLabel) { el.innerHTML = (allLabel ? `<option value="">${allLabel}</option>` : '') + items.map(i => `<option>${i}</option>`).join(''); }
const GREENS = ['#1b2024', '#a9d11a', '#434c53', '#7ea10a', '#79838b', '#d6f56a', '#b9c2c9'];
if (window.Chart) { Chart.defaults.color = '#434c53'; Chart.defaults.font.size = 11; Chart.defaults.font.family = "'IBM Plex Sans', sans-serif"; Chart.defaults.borderColor = 'rgba(20,24,27,.08)'; }
function chart(id, type, labels, datasets, opts = {}) {
  const el = document.getElementById(id); if (el._c) el._c.destroy();
  el._c = new Chart(el, { type, data: { labels, datasets }, options: { responsive: true, maintainAspectRatio: false, ...opts } });
}
(async function init() {
  const cur = location.pathname.replace(/\/$/, '').replace(/\.html$/, '') || '/', cur2 = cur === '/index' ? '/' : cur;
  $('#nav').innerHTML = `<nav class="navbar navbar-expand-lg navbar-dark topbar"><div class="container"><a class="navbar-brand brand" href="/">AgriPulse Rwanda</a>
    <button class="navbar-toggler" data-bs-toggle="collapse" data-bs-target="#m" aria-label="Menu"><span class="navbar-toggler-icon"></span></button>
    <div class="collapse navbar-collapse" id="m"><ul class="navbar-nav ms-auto">${PAGES.map(([h, t]) => `<li class="nav-item"><a class="nav-link ${h === cur2 ? 'active' : ''}" href="${h}">${t}</a></li>`).join('')}</ul></div></div></nav>`;
  try { const o = await api('/overview'); window.META = o.meta;
    if (o.meta.demo) $('#nav').insertAdjacentHTML('afterbegin', `<div class="demo-banner" role="alert">${o.meta.label}</div>`);
  } catch (e) { $('#nav').insertAdjacentHTML('afterbegin', '<div class="demo-banner">API unavailable — start the server with npm start</div>'); }
  document.dispatchEvent(new Event('ready'));
})();
