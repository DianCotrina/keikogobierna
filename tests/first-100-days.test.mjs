import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  loadPlan,
  loadTopics,
  loadTracking,
  firstHundredDays,
  firstHundredDaysStats,
} from '../src/lib/plan.mjs';

test('firstHundredDaysStats tallies all 67 actions, all no_progress at launch', () => {
  const stats = firstHundredDaysStats(loadTopics(), loadTracking());
  assert.equal(stats.total, 67);
  assert.equal(stats.byStatus.no_progress, 67);
  assert.equal(stats.byStatus.fulfilled, 0);
  assert.equal(stats.byStatus.in_progress, 0);
  assert.equal(stats.byStatus.unfulfilled, 0);
});

test('firstHundredDays groups by the 3 pillars in order', () => {
  const groups = firstHundredDays(loadPlan(), loadTopics(), loadTracking());
  assert.equal(groups.length, 3);
  assert.deepEqual(groups.map((g) => g.id), ['p1', 'p2', 'p3']);
  assert.deepEqual(groups.map((g) => g.index), [1, 2, 3]);
  assert.equal(groups[0].name, 'Orden');
});

test('pillar 1 holds its 4 topics; t1-1 leads with its 4 actions', () => {
  const groups = firstHundredDays(loadPlan(), loadTopics(), loadTracking());
  const pillar1 = groups[0];
  assert.equal(pillar1.topics.length, 4);

  const first = pillar1.topics[0];
  assert.equal(first.id, 't1-1');
  assert.equal(first.actions.length, 4);
  for (const action of first.actions) {
    assert.match(action.id, /^t1-1\.C\d\d$/);
    assert.equal(action.status, 'no_progress');
    assert.ok(action.text.trim().length > 0);
  }
});

test('every action across the grouping sums to 67', () => {
  const groups = firstHundredDays(loadPlan(), loadTopics(), loadTracking());
  const total = groups.reduce(
    (sum, pillar) =>
      sum + pillar.topics.reduce((s, topic) => s + topic.actions.length, 0),
    0,
  );
  assert.equal(total, 67);
});
