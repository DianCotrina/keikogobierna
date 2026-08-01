import test from 'node:test';
import assert from 'node:assert/strict';

import { entriesFor } from '../src/lib/minister-news.mjs';

const ENTRY = {
  title: 'El ministro de Economía Cuba anuncia medidas',
  url: 'https://gestion.pe/n/',
  source: 'Gestión',
  published: '2026-08-01T09:00:00-05:00',
};
const PAYLOAD = { ministers: { 'elmer-rafael-cuba-bustinza': [ENTRY] } };

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
