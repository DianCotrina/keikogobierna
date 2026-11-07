import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadPlan, loadTopics, loadTracking, commitmentStats } from '../src/lib/plan.mjs';
import { planInfographic, shortNorma, topicInfographic, truncate } from '../src/lib/infographic.mjs';

test('every topic image counts exactly what its page counts', () => {
  const topics = loadTopics();
  const tracking = loadTracking();
  for (const meta of loadPlan().topics) {
    const image = topicInfographic(meta.id);
    const stats = commitmentStats(topics, tracking, meta.id);
    assert.equal(image.total, stats.total, meta.slug);
    assert.equal(image.started, stats.started, meta.slug);
    assert.equal(image.items.length, image.started, `${meta.slug}: every started item is listed`);
    assert.equal(image.inProgress + image.fulfilled, image.started, meta.slug);
  }
});

test('the plan image adds up across topics', () => {
  const image = planInfographic();
  const stats = commitmentStats(loadTopics(), loadTracking());
  assert.equal(image.started, stats.started);
  assert.equal(image.total, stats.total);
  assert.equal(image.topics.reduce((sum, topic) => sum + topic.started, 0), image.started);
});

test('Turismo lists its 100-day action, the one its page used to leave blank', () => {
  const ids = topicInfographic('t2-7').items.map((item) => item.id);
  assert.ok(ids.includes('t2-7.C03'));
});

test('shortNorma abbreviates the act type and keeps the number', () => {
  assert.equal(shortNorma('El Peruano — DECRETO SUPREMO N° 121-2026-PCM'), 'D.S. N° 121-2026-PCM');
  assert.equal(shortNorma('El Peruano — DECRETO DE URGENCIA N° 015-2026'), 'D.U. N° 015-2026');
});

test('truncate cuts on a word and marks the cut', () => {
  assert.equal(truncate('corto', 50), 'corto');
  const cut = truncate('Implementación del Plan Nacional de Orden Turístico, integrando PNP', 40);
  assert.ok(cut.length <= 40 && cut.endsWith('…') && !cut.includes(', …'));
});
