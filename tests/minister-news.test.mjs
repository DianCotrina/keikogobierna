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
