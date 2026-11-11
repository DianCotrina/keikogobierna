import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadPlan, loadTracking } from '../src/lib/plan.mjs';
import { timelineEntries } from '../src/lib/timeline.mjs';
import { formatDayMonthEs, formatMonthEs } from '../src/lib/format.mjs';

test('the committed log becomes one row per entry, newest first', () => {
  const tracking = loadTracking();
  const rows = timelineEntries(tracking, loadPlan());
  assert.equal(rows.length, tracking.log.length);
  for (let i = 1; i < rows.length; i++) assert.ok(rows[i - 1].date >= rows[i].date);
  assert.equal(new Set(rows.map((row) => row.id)).size, rows.length, 'row ids must be unique');
  for (const row of rows) {
    assert.ok(row.href?.startsWith('/temas/') && row.href.endsWith(`#${row.item}`), `${row.item} has no topic link`);
    assert.equal(row.month, row.date.slice(0, 7));
  }
});

test('same day and item still get distinct ids; an unknown topic gets no link', () => {
  const plan = { topics: [{ id: 't2-1', slug: 'emprendedores-mype', name: 'Emprendedores' }] };
  const log = [
    { date: '2026-10-31', item: 't2-1.C03', status: 'in_progress', text: 'a' },
    { date: '2026-10-31', item: 't2-1.C03', status: 'in_progress', text: 'b' },
    { date: '2026-09-01', item: 't9-9.P01', status: 'in_progress', text: 'c' },
  ];
  const rows = timelineEntries({ log }, plan);
  assert.deepEqual(rows.map((row) => row.id), ['2026-10-31-t2-1.C03', '2026-10-31-t2-1.C03-2', '2026-09-01-t9-9.P01']);
  assert.equal(rows[2].href, null);
  assert.equal(rows[0].href, '/temas/emprendedores-mype/#t2-1.C03');
});

test('month headings and day labels are Spanish', () => {
  assert.equal(formatMonthEs('2026-10-31'), 'octubre de 2026');
  assert.equal(formatDayMonthEs('2026-09-05'), '5 set');
});
