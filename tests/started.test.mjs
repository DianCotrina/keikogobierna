import { test } from 'node:test';
import assert from 'node:assert/strict';
import { commitmentStats, loadTopics, loadTracking, statusOf } from '../src/lib/plan.mjs';
import { imageSlug, startedCommitments, startedSummary, toCsv } from '../src/lib/started.mjs';

const rows = startedCommitments({ today: '2026-11-07' });

test('exactly the started proposals and 100-day actions, never goals', () => {
  const tracking = loadTracking();
  const expected = Object.entries(tracking.items)
    .filter(([id, item]) => !id.includes('.M') && (item.status === 'in_progress' || item.status === 'fulfilled'))
    .map(([id]) => id)
    .sort();
  assert.deepEqual(rows.map((row) => row.id).sort(), expected);
  for (const row of rows) assert.equal(row.status, statusOf(row.id, tracking));
});

test('each row carries every norma of its evidence, oldest first, with a summary', () => {
  const tracking = loadTracking();
  for (const row of rows) {
    assert.equal(row.norm_count, tracking.items[row.id].evidence.length);
    assert.deepEqual(row.norms.map((n) => n.date), [...row.norms.map((n) => n.date)].sort());
    assert.equal(row.started_on, row.norms[0].date);
    // Every norma certified so far has a human-written log line.
    for (const norm of row.norms) assert.ok(norm.summary, `${row.id}: no log summary for ${norm.norma}`);
  }
});

test('commitments certified with the same norma point at each other', () => {
  const byId = Object.fromEntries(rows.map((row) => [row.id, row]));
  assert.deepEqual(byId['t2-7.C03'].shares_norms_with, ['t2-7.P23']);
  for (const row of rows) for (const other of row.shares_norms_with) assert.ok(byId[other].shares_norms_with.includes(row.id));
});

test('summary metrics add up', () => {
  const summary = startedSummary(rows, commitmentStats(loadTopics(), loadTracking()));
  assert.equal(summary.started, rows.length);
  assert.equal(summary.in_progress + summary.fulfilled, summary.started);
  assert.equal(summary.by_topic.reduce((sum, t) => sum + t.started, 0), summary.started);
  assert.ok(summary.government_day_of_first_norm.min <= summary.government_day_of_first_norm.median);
});

test('the CSV parses back to one row per commitment', () => {
  const csv = toCsv(rows);
  assert.ok(csv.startsWith('﻿id,'));
  // Minimal RFC 4180 reader: quoted fields may hold commas and doubled quotes.
  const records = [];
  let field = '', record = [], quoted = false;
  for (let i = 1; i < csv.length; i += 1) {
    const ch = csv[i];
    if (quoted) {
      if (ch === '"' && csv[i + 1] === '"') { field += '"'; i += 1; } else if (ch === '"') quoted = false; else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { record.push(field); field = ''; }
    else if (ch === '\r') continue;
    else if (ch === '\n') { record.push(field); records.push(record); record = []; field = ''; }
    else field += ch;
  }
  const [header, ...data] = records;
  assert.equal(data.length, rows.length);
  for (const line of data) assert.equal(line.length, header.length);
  assert.equal(data[0][header.indexOf('id')], rows[0].id);
});

test('image slugs are filename-safe', () => {
  assert.equal(imageSlug('t2-7.C03'), 't2-7-c03');
});
