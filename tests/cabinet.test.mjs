import test from 'node:test';
import assert from 'node:assert/strict';

import {
  loadPortfolios,
  portfolioById,
  portfolioTopics,
  tenureDays,
  currentCabinet,
  pastTenures,
  cabinetStats,
} from '../src/lib/cabinet.mjs';

// Fixtures shaped like the real files, kept local so the tests stay true even
// while src/data/cabinet/ is still empty of a real roster.
const PEOPLE = [
  { slug: 'ana-torres', name: 'Ana Torres', judicial: [{ id: 'c1', stage: 'sentencia_firme' }] },
  { slug: 'beto-lima', name: 'Beto Lima', judicial: [{ id: 'c1', stage: 'archivado' }] },
  { slug: 'cira-paz', name: 'Cira Paz', judicial: [] },
];
const TENURES = [
  { person: 'ana-torres', portfolio: 'm-interior', start: '2026-07-28', end: null },
  { person: 'beto-lima', portfolio: 'm-salud', start: '2026-07-28', end: '2026-09-30' },
  { person: 'cira-paz', portfolio: 'm-salud', start: '2026-10-01', end: null },
];

test('portfolios registry loads and ids are unique', () => {
  const portfolios = loadPortfolios();
  assert.ok(portfolios.length > 0);
  assert.equal(new Set(portfolios.map((p) => p.id)).size, portfolios.length);
});

test('every portfolio topic id resolves against the real plan', () => {
  for (const portfolio of loadPortfolios()) {
    const topics = portfolioTopics(portfolio.id);
    assert.equal(topics.length, portfolio.topics.length, portfolio.id);
    for (const topic of topics) assert.ok(topic.name, `${portfolio.id} -> ${topic.id}`);
  }
});

test('portfolioById returns undefined for an unknown id instead of throwing', () => {
  assert.equal(portfolioById('m-nope'), undefined);
});

test('tenureDays counts an open tenure up to today', () => {
  const days = tenureDays({ start: '2026-07-28', end: null }, new Date('2026-08-04T00:00:00Z'));
  assert.equal(days, 7);
});

test('tenureDays counts a closed tenure to its end, ignoring today', () => {
  const days = tenureDays({ start: '2026-07-28', end: '2026-08-04' }, new Date('2027-01-01T00:00:00Z'));
  assert.equal(days, 7);
});

test('a tenure that started today counts as zero days, not negative', () => {
  assert.equal(tenureDays({ start: '2026-07-28', end: null }, new Date('2026-07-28T00:00:00Z')), 0);
});

test('currentCabinet has one row per portfolio, including the vacant ones', () => {
  const rows = currentCabinet({ people: PEOPLE, tenures: TENURES });
  assert.equal(rows.length, loadPortfolios().length);
  const interior = rows.find((r) => r.portfolio.id === 'm-interior');
  assert.equal(interior.person.slug, 'ana-torres');
  const defensa = rows.find((r) => r.portfolio.id === 'm-defensa');
  assert.equal(defensa.person, null);
  assert.equal(defensa.tenure, null);
});

test('currentCabinet picks the open tenure when a portfolio has had several holders', () => {
  const rows = currentCabinet({ people: PEOPLE, tenures: TENURES });
  assert.equal(rows.find((r) => r.portfolio.id === 'm-salud').person.slug, 'cira-paz');
});

test('pastTenures returns only closed tenures, most recent first', () => {
  const past = pastTenures({ people: PEOPLE, tenures: TENURES });
  assert.equal(past.length, 1);
  assert.equal(past[0].person.slug, 'beto-lima');
  assert.equal(past[0].days, 64);
});

test('cabinetStats counts only ministers with a live proceeding', () => {
  // Ana has a firm conviction; Beto's only entry is archived, so he is not counted.
  const stats = cabinetStats({ people: PEOPLE, tenures: TENURES }, new Date('2026-10-05T00:00:00Z'));
  assert.equal(stats.portfolios, loadPortfolios().length);
  assert.equal(stats.withActiveCases, 1);
  assert.equal(stats.changes, 1);
});

test('cabinetStats on an empty roster reports zeroes rather than throwing', () => {
  const stats = cabinetStats({ people: [], tenures: [] }, new Date('2026-10-05T00:00:00Z'));
  assert.equal(stats.withActiveCases, 0);
  assert.equal(stats.changes, 0);
  assert.equal(stats.serving, 0);
});

// --- announcements: provisional, always subordinate to the gazette -----------

const ANNOUNCEMENTS = [
  {
    portfolio: 'pcm',
    person_name: 'Luis Galarreta',
    announced: '2026-07-27',
    sources: [{ label: 'El Comercio', url: 'https://elcomercio.pe/x', kind: 'press' }],
  },
  {
    portfolio: 'm-interior',
    person_name: 'Otra Persona',
    announced: '2026-07-27',
    sources: [{ label: 'La República', url: 'https://larepublica.pe/x', kind: 'press' }],
  },
];

test('an announced portfolio with no tenure shows as announced, not as filled', () => {
  const rows = currentCabinet({ people: [], tenures: [], announcements: ANNOUNCEMENTS });
  const pcm = rows.find((r) => r.portfolio.id === 'pcm');
  assert.equal(pcm.person, null);
  assert.equal(pcm.announcement.person_name, 'Luis Galarreta');
  assert.equal(pcm.days, null);
});

test('a gazette tenure supersedes the announcement for that portfolio', () => {
  // m-interior is both announced and actually appointed; the norma wins and the
  // provisional marking must disappear.
  const rows = currentCabinet(
    { people: PEOPLE, tenures: TENURES, announcements: ANNOUNCEMENTS },
    new Date('2026-08-04T00:00:00Z'),
  );
  const interior = rows.find((r) => r.portfolio.id === 'm-interior');
  assert.equal(interior.person.slug, 'ana-torres');
  assert.equal(interior.announcement, null);
});

test('a portfolio that is neither appointed nor announced stays vacant', () => {
  const rows = currentCabinet({ people: [], tenures: [], announcements: ANNOUNCEMENTS });
  const defensa = rows.find((r) => r.portfolio.id === 'm-defensa');
  assert.equal(defensa.person, null);
  assert.equal(defensa.announcement, null);
});

test('announced ministers are counted separately from serving ones', () => {
  const stats = cabinetStats(
    { people: [], tenures: [], announcements: ANNOUNCEMENTS },
    new Date('2026-07-27T00:00:00Z'),
  );
  assert.equal(stats.serving, 0);
  assert.equal(stats.announced, 2);
});

test('an announcement already confirmed by a norma is not double-counted', () => {
  const stats = cabinetStats(
    { people: PEOPLE, tenures: TENURES, announcements: ANNOUNCEMENTS },
    new Date('2026-08-04T00:00:00Z'),
  );
  // m-interior is served; only the pcm announcement is still outstanding.
  assert.equal(stats.announced, 1);
});
