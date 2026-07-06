import { renderTrackerCard } from './modules/tracker-card.js';
import { renderEjes } from './modules/ejes.js';
import { renderRegistro } from './modules/registro.js';
import { initReveal } from './modules/reveal.js';
import { initDonate } from './modules/donate.js';

async function boot() {
  const res = await fetch('./src/data/plan.json');
  if (!res.ok) throw new Error(`plan.json: HTTP ${res.status}`);
  const data = await res.json();

  renderTrackerCard(document.getElementById('tracker-card'), data);
  renderEjes(document.getElementById('ejes-grid'), data);
  renderRegistro(document.getElementById('registro-list'), data);

  initReveal();
  initDonate();
}

boot().catch((err) => {
  console.error(err);
  // Static shell still shows headline/copy; dynamic sections stay empty.
});
