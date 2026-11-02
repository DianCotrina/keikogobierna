import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  loadPlan,
  loadTopics,
  loadTracking,
  firstHundredDays,
  firstHundredDaysStats,
  topicActionMark,
} from '../src/lib/plan.mjs';
import { STATUSES } from '../src/lib/statuses.mjs';

// Asserts the tally's shape, not its emptiness. This test hard-coded 67
// no_progress and broke the day the first 100-days action was certified
// (t2-2.C03, the Madre de Dios command) — the one moment it should have stayed
// green. Same failure the updatesLog test had on the first certification.
test('firstHundredDaysStats tallies all 67 actions across valid statuses', () => {
  const stats = firstHundredDaysStats(loadTopics(), loadTracking());
  assert.equal(stats.total, 67);
  for (const status of Object.keys(STATUSES)) {
    assert.ok(Number.isInteger(stats.byStatus[status]), `missing count for ${status}`);
    assert.ok(stats.byStatus[status] >= 0, `negative count for ${status}`);
  }
  const summed = Object.keys(STATUSES).reduce((n, s) => n + stats.byStatus[s], 0);
  assert.equal(summed, stats.total, 'every action lands in exactly one status');
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
    assert.ok(Object.hasOwn(STATUSES, action.status), `bad status ${action.status}`);
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

describe('topicActionMark', () => {
  const actions = (...statuses) => statuses.map((status) => ({ status }));

  test('no mark until something has started', () => {
    assert.equal(topicActionMark(actions('no_progress', 'no_progress')), undefined);
  });

  test('an unfulfilled action does not earn a check', () => {
    assert.equal(topicActionMark(actions('unfulfilled', 'no_progress')), undefined);
  });

  test('in progress when any action is in progress', () => {
    assert.equal(topicActionMark(actions('no_progress', 'in_progress')), 'in_progress');
  });

  test('in progress wins over fulfilled: the topic still has work open', () => {
    assert.equal(topicActionMark(actions('fulfilled', 'in_progress')), 'in_progress');
  });

  test('fulfilled when that is the only started status', () => {
    assert.equal(topicActionMark(actions('fulfilled', 'no_progress')), 'fulfilled');
  });
});
