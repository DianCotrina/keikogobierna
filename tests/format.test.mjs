import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { formatDateEs } from '../src/lib/format.mjs';

describe('formatDateEs', () => {
  test('formats an ISO date as Spanish long date', () => {
    assert.equal(formatDateEs('2027-03-12'), '12 de marzo de 2027');
  });

  test('no leading zero on single-digit days', () => {
    assert.equal(formatDateEs('2026-07-06'), '6 de julio de 2026');
  });
});
