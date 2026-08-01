import test from 'node:test';
import assert from 'node:assert/strict';

import { entriesFor, resolveCoverage, isStale, STALE_AFTER_HOURS } from '../src/lib/minister-news.mjs';

const ENTRY = {
  title: 'El ministro de Economía Cuba anuncia medidas',
  url: 'https://gestion.pe/n/',
  source: 'Gestión',
  published: '2026-08-01T09:00:00-05:00',
};
const NOW = new Date('2026-08-01T12:00:00Z');
const FRESH_GENERATED = '2026-08-01T06:00:00+00:00'; // 6h old at NOW
const PAYLOAD = { generated: FRESH_GENERATED, ministers: { 'elmer-rafael-cuba-bustinza': [ENTRY] } };

// --- entriesFor: unchanged shape, plus the malformed-date guard (finding 6) --

test('returns this slug\'s entries', () => {
  assert.deepEqual(entriesFor(PAYLOAD, 'elmer-rafael-cuba-bustinza'), [ENTRY]);
});

test('a minister absent from the map has no coverage, not an error', () => {
  assert.deepEqual(entriesFor(PAYLOAD, 'rafael-rey-rey'), []);
});

test('a malformed payload yields nothing rather than throwing', () => {
  for (const bad of [null, undefined, {}, { ministers: null }, { ministers: [] }, 'nope', 42]) {
    assert.deepEqual(entriesFor(bad, 'elmer-rafael-cuba-bustinza'), [], String(bad));
  }
});

test('a non-array value for a slug yields nothing', () => {
  assert.deepEqual(entriesFor({ ministers: { x: 'not an array' } }, 'x'), []);
});

test('an entry missing its title or url is dropped', () => {
  const payload = { ministers: { x: [ENTRY, { url: 'https://a/' }, { title: 'sin url' }] } };
  assert.deepEqual(entriesFor(payload, 'x'), [ENTRY]);
});

test('an entry with a non-string published is dropped, siblings survive', () => {
  const bad1 = { ...ENTRY, title: 'sin fecha (null)', published: null };
  const bad2 = { ...ENTRY, title: 'sin fecha (numero)', published: 1234567890 };
  const good = { ...ENTRY, title: 'con fecha' };
  const payload = { ministers: { x: [bad1, good, bad2] } };
  assert.deepEqual(entriesFor(payload, 'x'), [good]);
});

test('an entry with a non-string source is dropped, siblings survive', () => {
  const bad = { ...ENTRY, title: 'sin fuente', source: null };
  const good = { ...ENTRY, title: 'con fuente' };
  const payload = { ministers: { x: [bad, good] } };
  assert.deepEqual(entriesFor(payload, 'x'), [good]);
});

test('surviving entries keep their original relative order', () => {
  const a = { ...ENTRY, title: 'a' };
  const bad = { ...ENTRY, title: 'malo', published: null };
  const b = { ...ENTRY, title: 'b' };
  const c = { ...ENTRY, title: 'c' };
  const payload = { ministers: { x: [a, bad, b, c] } };
  assert.deepEqual(entriesFor(payload, 'x'), [a, b, c]);
});

// Finding 6: `published` must at least look like a date before it reaches
// formatDateEs, which does `iso.split('-').map(Number)` unguarded.
test('an entry whose published is not a well-formed date is dropped', () => {
  const bad = { ...ENTRY, title: 'fecha invalida', published: 'not-a-date' };
  const good = { ...ENTRY, title: 'fecha valida' };
  const payload = { ministers: { x: [bad, good] } };
  assert.deepEqual(entriesFor(payload, 'x'), [good]);
});

test('a published value merely prefixed with a date still passes (time part unchecked)', () => {
  const ok = { ...ENTRY, published: '2026-08-01T09:00:00-05:00' };
  assert.deepEqual(entriesFor({ ministers: { x: [ok] } }, 'x'), [ok]);
});

// --- isStale: the staleness guard (finding 1) ---------------------------------

test('a payload generated moments ago is fresh', () => {
  assert.equal(isStale({ generated: '2026-08-01T11:59:00Z' }, NOW), false);
});

test('a payload generated 37 hours ago is stale', () => {
  const generated = new Date(NOW.getTime() - 37 * 60 * 60 * 1000).toISOString();
  assert.equal(isStale({ generated }, NOW), true);
});

test('a missing generated is unusable', () => {
  assert.equal(isStale({ ministers: {} }, NOW), true);
  assert.equal(isStale({}, NOW), true);
});

test('a garbage generated is unusable', () => {
  assert.equal(isStale({ generated: 'not a timestamp' }, NOW), true);
  assert.equal(isStale({ generated: 42 }, NOW), true);
  assert.equal(isStale({ generated: null }, NOW), true);
});

test('the boundary: exactly the limit is still fresh, one second past it is stale', () => {
  const atLimit = new Date(NOW.getTime() - STALE_AFTER_HOURS * 60 * 60 * 1000).toISOString();
  const pastLimit = new Date(NOW.getTime() - STALE_AFTER_HOURS * 60 * 60 * 1000 - 1000).toISOString();
  assert.equal(isStale({ generated: atLimit }, NOW), false);
  assert.equal(isStale({ generated: pastLimit }, NOW), true);
});

// --- resolveCoverage: the load()-testable decision (finding 4, 5) -------------

test('a fresh payload with entries resolves to the list', () => {
  assert.deepEqual(resolveCoverage(PAYLOAD, 'elmer-rafael-cuba-bustinza', NOW), {
    status: 'list',
    entries: [ENTRY],
  });
});

test('a fresh payload where the minister is absent resolves to empty', () => {
  assert.deepEqual(resolveCoverage(PAYLOAD, 'rafael-rey-rey', NOW), { status: 'empty' });
});

test('a stale payload resolves to error even when it has entries for the slug', () => {
  const stale = { ...PAYLOAD, generated: '2026-07-01T00:00:00+00:00' };
  assert.deepEqual(resolveCoverage(stale, 'elmer-rafael-cuba-bustinza', NOW), { status: 'error' });
});

test('an unparseable payload resolves to error', () => {
  for (const bad of [null, undefined, 'nope', 42, {}]) {
    assert.deepEqual(resolveCoverage(bad, 'elmer-rafael-cuba-bustinza', NOW), { status: 'error' });
  }
});

// Finding 5: an all-malformed entry list must not read as confirmed no-coverage.
test('a slug whose every entry is malformed resolves to error, not empty', () => {
  const payload = {
    generated: FRESH_GENERATED,
    ministers: { x: [{ title: 'sin url' }, { url: 'https://a/' }] },
  };
  assert.deepEqual(resolveCoverage(payload, 'x', NOW), { status: 'error' });
});

test('a slug whose entries are partially malformed still resolves to the surviving list', () => {
  const good = { ...ENTRY, title: 'sobrevive' };
  const payload = { generated: FRESH_GENERATED, ministers: { x: [{ title: 'sin url' }, good] } };
  assert.deepEqual(resolveCoverage(payload, 'x', NOW), { status: 'list', entries: [good] });
});

test('a slug present but not an array resolves to error', () => {
  const payload = { generated: FRESH_GENERATED, ministers: { x: 'not an array' } };
  assert.deepEqual(resolveCoverage(payload, 'x', NOW), { status: 'error' });
});
