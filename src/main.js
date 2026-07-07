import { renderTrackerCard } from './modules/tracker-card.js';
import { renderTopics } from './modules/topics.js';
import { renderUpdates } from './modules/updates.js';
import { initReveal } from './modules/reveal.js';
import { initDonate } from './modules/donate.js';

async function boot() {
  const res = await fetch('./src/data/plan.json');
  if (!res.ok) throw new Error(`plan.json: HTTP ${res.status}`);
  const data = await res.json();

  renderTrackerCard(document.getElementById('tracker-card'), data);
  renderTopics(document.getElementById('topics-grid'), data);
  renderUpdates(document.getElementById('updates-list'), data);
}

boot()
  .catch((err) => {
    console.error(err);
    // Dynamic sections stay empty; static sections still reveal below.
  })
  .finally(() => {
    initReveal();
    initDonate();
  });
