import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  INAUGURATION,
  DEADLINE,
  governmentDay,
  limaToday,
  mandateClock,
  mandateCopy,
} from '../src/lib/mandate.mjs';

describe('governmentDay', () => {
  test('inauguration day is day 1', () => {
    assert.equal(governmentDay(INAUGURATION), 1);
  });

  test('counts across month boundaries', () => {
    assert.equal(governmentDay('2026-10-22'), 87);
  });

  test('the day before inauguration is day 0', () => {
    assert.equal(governmentDay('2026-07-27'), 0);
  });
});

describe('DEADLINE', () => {
  test('day 100 falls on 4 November 2026', () => {
    assert.equal(DEADLINE, '2026-11-04');
    assert.equal(governmentDay(DEADLINE), 100);
  });
});

describe('limaToday', () => {
  test('uses Lima time, not UTC: 03:00 UTC is still the previous day in Lima', () => {
    assert.equal(limaToday(new Date('2026-10-23T03:00:00Z')), '2026-10-22');
  });

  test('rolls over at Lima midnight (05:00 UTC)', () => {
    assert.equal(limaToday(new Date('2026-10-23T05:00:00Z')), '2026-10-23');
  });
});

describe('mandateClock', () => {
  test('before inauguration nothing has elapsed', () => {
    const c = mandateClock('2026-07-20');
    assert.equal(c.phase, 'before');
    assert.equal(c.elapsed, 0);
    assert.equal(c.remaining, 100);
  });

  test('inside the window', () => {
    assert.deepEqual(mandateClock('2026-10-22'), {
      day: 87, phase: 'running', elapsed: 87, remaining: 13, overdue: 0,
    });
  });

  test('day 100 is its own phase', () => {
    const c = mandateClock(DEADLINE);
    assert.equal(c.phase, 'deadline');
    assert.equal(c.remaining, 0);
  });

  test('after the window the ruler stays full and overdue days accrue', () => {
    const c = mandateClock('2026-11-16');
    assert.equal(c.phase, 'over');
    assert.equal(c.day, 112);
    assert.equal(c.elapsed, 100);
    assert.equal(c.overdue, 12);
  });
});

describe('mandateCopy', () => {
  test('counts down inside the window', () => {
    const copy = mandateCopy(mandateClock('2026-10-22'));
    assert.equal(copy.day, '87');
    assert.equal(copy.note, 'Faltan 13 días para que venza el plazo, el 4 de noviembre de 2026.');
  });

  test('singular on the last day before the deadline', () => {
    assert.match(mandateCopy(mandateClock('2026-11-03')).note, /^Falta 1 día /);
  });

  test('switches to days of government once the window closes', () => {
    const copy = mandateCopy(mandateClock('2026-11-05'));
    assert.equal(copy.of, 'de gobierno');
    assert.equal(copy.note, 'El plazo de los 100 días venció el 4 de noviembre de 2026, hace 1 día.');
  });
});
