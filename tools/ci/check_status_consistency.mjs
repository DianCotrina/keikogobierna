// Every status count the built site shows must agree with src/data/tracking.json.
//
// A reader reported that Turismo, Minería and Emprendedores announced more
// commitments "en progreso" than their pages marked: the topic page drew its
// 100-day actions as empty boxes whatever their status. This reads the built
// HTML (what visitors get), recounts each figure from the data, and fails the
// build on any disagreement. Run after `npm run build`.

import { readFileSync } from 'node:fs';
import { loadPlan, loadTopics, loadTracking, statusOf } from '../../src/lib/plan.mjs';

const DIST = new URL('../../dist/', import.meta.url);
const read = (path) => readFileSync(new URL(path, DIST), 'utf8');
const plan = loadPlan();
const topics = loadTopics();
const tracking = loadTracking();
const failures = [];

const expect = (where, label, shown, actual) => {
  if (shown !== actual) failures.push(`${where}: ${label} shows ${shown}, data says ${actual}`);
};

// The text between an element's opening id and the next section boundary.
const section = (html, id) => {
  const start = html.indexOf(`id="${id}"`);
  if (start < 0) return '';
  const end = html.indexOf('</section>', start);
  return html.slice(start, end < 0 ? undefined : end);
};

const stamps = (html, label) => (html.match(new RegExp(`class="stamp[^"]*"[^>]*>${label}<`, 'g')) ?? []).length;

const count = (items) => {
  const byStatus = { fulfilled: 0, in_progress: 0 };
  for (const item of items) {
    const status = statusOf(item.id, tracking);
    if (status in byStatus) byStatus[status] += 1;
  }
  return byStatus;
};

const home = read('index.html');
const hundred = read('primeros-100-dias/index.html');
let total = { fulfilled: 0, in_progress: 0 };
let hundredTotal = { fulfilled: 0, in_progress: 0 };

for (const meta of plan.topics) {
  const file = topics.get(meta.id);
  const proposals = count(file.groups.flatMap((group) => group.proposals));
  const actions = count(file.first_100_days);
  const started = proposals.fulfilled + proposals.in_progress + actions.fulfilled + actions.in_progress;
  total = { fulfilled: total.fulfilled + proposals.fulfilled + actions.fulfilled, in_progress: total.in_progress + proposals.in_progress + actions.in_progress };
  hundredTotal = { fulfilled: hundredTotal.fulfilled + actions.fulfilled, in_progress: hundredTotal.in_progress + actions.in_progress };

  const page = read(`temas/${meta.slug}/index.html`);
  const where = `/temas/${meta.slug}/`;
  expect(where, 'proposals marked en progreso', stamps(section(page, 'propuestas'), 'En progreso'), proposals.in_progress);
  expect(where, 'proposals marked cumplido', stamps(section(page, 'propuestas'), 'Cumplid[oa]'), proposals.fulfilled);
  expect(where, '100-day actions marked en progreso', stamps(section(page, 'cien-dias'), 'En progreso'), actions.in_progress);
  expect(where, '100-day actions marked cumplido', stamps(section(page, 'cien-dias'), 'Cumplid[oa]'), actions.fulfilled);

  const note = page.match(/De los (\d+) compromisos[\s\S]*?(?:(\d+) se ha(?:n)? iniciado: (\d+) (?:está|están) en progreso y (\d+)|ninguno)/);
  if (!note) failures.push(`${where}: status note missing`);
  else {
    expect(where, 'status note total', Number(note[1]), file.groups.flatMap((g) => g.proposals).length + file.first_100_days.length);
    expect(where, 'status note iniciados', Number(note[2] ?? 0), started);
    expect(where, 'status note en progreso', Number(note[3] ?? 0), proposals.in_progress + actions.in_progress);
    expect(where, 'status note cumplidos', Number(note[4] ?? 0), proposals.fulfilled + actions.fulfilled);
  }

  const cardAt = home.indexOf(`href="/temas/${meta.slug}/" class="card-hover`);
  const card = cardAt < 0 ? '' : home.slice(cardAt, home.indexOf('</a>', cardAt));
  const shownStarted = Number((card.match(/(\d+) compromisos? iniciados?/) ?? [0, 0])[1]);
  expect(`/ (card ${meta.name})`, 'compromisos iniciados', shownStarted, started);

  if (file.first_100_days.length > 0) {
    const block = section(hundred, `dias-${meta.slug}`).split('id="dias-')[1] ?? '';
    expect(`/primeros-100-dias/ (${meta.name})`, 'actions marked en progreso', stamps(block, 'En progreso'), actions.in_progress);
  }
}

const tally = (html, label) => Number((html.match(new RegExp(`(\\d+)</p><p[^>]*>${label}<`)) ?? [0, NaN])[1]);
expect('/primeros-100-dias/ (tally)', 'en progreso', tally(hundred, 'En progreso'), hundredTotal.in_progress);
expect('/primeros-100-dias/ (tally)', 'cumplidas', tally(hundred, 'Cumplidas'), hundredTotal.fulfilled);

if (failures.length > 0) {
  console.error(`${failures.length} status count(s) disagree with tracking.json:\n- ${failures.join('\n- ')}`);
  process.exit(1);
}
console.log(`Status counts agree with tracking.json across ${plan.topics.length} topics (${total.in_progress} in progress, ${total.fulfilled} fulfilled).`);
