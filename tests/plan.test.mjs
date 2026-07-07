import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  loadPlan,
  loadTopics,
  loadGoals,
  loadTracking,
  statusOf,
  goalStats,
  topicSummaries,
  updatesLog,
} from '../src/lib/plan.mjs';
import { STATUSES, statusMeta } from '../src/lib/statuses.mjs';

describe('loadPlan', () => {
  test('returns 3 pillars and 23 topics', () => {
    const { plan, pillars, topics } = loadPlan();
    assert.ok(plan);
    assert.equal(pillars.length, 3);
    assert.equal(topics.length, 23);
  });
});

describe('loadTopics', () => {
  test('returns 23 entries keyed by topic id', () => {
    const topics = loadTopics();
    assert.equal(topics.size, 23);
    assert.ok(topics.has('t1-1'));
  });

  test('t1-1 has 43 proposals across its groups', () => {
    const topics = loadTopics();
    const t11 = topics.get('t1-1');
    const proposalCount = t11.groups.reduce((sum, group) => sum + group.proposals.length, 0);
    assert.equal(proposalCount, 43);
  });
});

describe('loadGoals', () => {
  test('returns 65 goals', () => {
    const goals = loadGoals();
    assert.equal(goals.length, 65);
  });
});

describe('statusOf', () => {
  test("returns 'no_progress' for a known goal id (real tracking data)", () => {
    const tracking = loadTracking();
    assert.equal(statusOf('t1-1.M01', tracking), 'no_progress');
  });

  test("returns 'no_progress' for an absent id", () => {
    const tracking = loadTracking();
    assert.equal(statusOf('nonexistent', tracking), 'no_progress');
  });
});

describe('goalStats', () => {
  test('overall stats: total 65, all no_progress, progressPct 0', () => {
    const goals = loadGoals();
    const tracking = loadTracking();
    const stats = goalStats(goals, tracking);
    assert.equal(stats.total, 65);
    assert.equal(stats.byStatus.no_progress, 65);
    assert.equal(stats.byStatus.fulfilled, 0);
    assert.equal(stats.byStatus.in_progress, 0);
    assert.equal(stats.byStatus.unfulfilled, 0);
    assert.equal(stats.progressPct, 0);
  });

  test('filtered stats for t1-2: total 1', () => {
    const goals = loadGoals();
    const tracking = loadTracking();
    const stats = goalStats(goals, tracking, 't1-2');
    assert.equal(stats.total, 1);
  });
});

describe('topicSummaries', () => {
  test('returns 23 rows, first is t1-1 with pillarName Orden', () => {
    const plan = loadPlan();
    const goals = loadGoals();
    const tracking = loadTracking();
    const summaries = topicSummaries(plan, goals, tracking);
    assert.equal(summaries.length, 23);
    assert.equal(summaries[0].id, 't1-1');
    assert.equal(summaries[0].pillarName, 'Orden');
  });
});

describe('updatesLog', () => {
  test('returns empty array for current tracking data', () => {
    const tracking = loadTracking();
    assert.deepEqual(updatesLog(tracking), []);
  });
});

describe('statusMeta', () => {
  test("statusMeta('fulfilled').label === 'Cumplida'", () => {
    assert.equal(statusMeta('fulfilled').label, 'Cumplida');
  });

  test("statusMeta('bogus').color === 'plomo'", () => {
    assert.equal(statusMeta('bogus').color, 'plomo');
  });

  test('STATUSES map has all four statuses', () => {
    assert.deepEqual(Object.keys(STATUSES).sort(), [
      'fulfilled',
      'in_progress',
      'no_progress',
      'unfulfilled',
    ]);
  });
});
