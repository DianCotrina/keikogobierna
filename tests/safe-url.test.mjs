import test from 'node:test';
import assert from 'node:assert/strict';

import { safeHttpUrl } from '../src/lib/safe-url.mjs';

test('https and http pass through', () => {
  assert.equal(safeHttpUrl('https://elcomercio.pe/nota/'), 'https://elcomercio.pe/nota/');
  assert.equal(safeHttpUrl('http://rpp.pe/nota'), 'http://rpp.pe/nota');
});

test('a javascript: url is rejected', () => {
  assert.equal(safeHttpUrl('javascript:alert(1)'), '');
});

test('a data: url is rejected', () => {
  assert.equal(safeHttpUrl('data:text/html,<script>alert(1)</script>'), '');
});

test('an unparseable value is rejected rather than thrown on', () => {
  assert.equal(safeHttpUrl('not a url'), '');
  assert.equal(safeHttpUrl(''), '');
});
