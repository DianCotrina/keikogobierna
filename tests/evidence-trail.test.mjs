import { test } from 'node:test';
import assert from 'node:assert/strict';
import { noteSegments, splitEvidenceNote } from '../src/lib/format.mjs';
import { firstHundredDays, loadPlan, loadTopics, loadTracking } from '../src/lib/plan.mjs';

const plain = (parts) => parts.map((part) => part.text).join('');

test('noteSegments marks only the **bold** parts', () => {
  assert.deepEqual(noteSegments('aprueba el **Plan** nacional'), [
    { text: 'aprueba el ', bold: false },
    { text: 'Plan', bold: true },
    { text: ' nacional', bold: false },
  ]);
});

test('splitEvidenceNote keeps a note without the phrase whole', () => {
  const { does, pending } = splitEvidenceNote('Cumple lo prometido.');
  assert.equal(plain(does), 'Cumple lo prometido.');
  assert.deepEqual(pending, []);
});

// Against every note the site really publishes: none may lose the reason it
// stays in progress or show the raw markers.
test('every certified note splits cleanly', () => {
  const tracking = loadTracking();
  for (const [id, item] of Object.entries(tracking.items)) {
    for (const entry of item.evidence ?? []) {
      const { does, pending } = splitEvidenceNote(entry.note);
      assert.ok(does.length > 0, `${id}: nothing left of what the norm does`);
      if (item.status === 'in_progress') assert.ok(pending.length > 0, `${id}: no pending reason`);
      assert.ok(!plain([...does, ...pending]).includes('**'), `${id}: raw markers`);
      assert.ok(!plain(pending).startsWith('Queda en progreso'), `${id}: phrase kept`);
      assert.match(plain(pending).charAt(0) || 'A', /\p{Lu}/u, `${id}: pending not capitalised`);
    }
  }
});

test('firstHundredDays gives each action its evidence and the commitments sharing it', () => {
  const tracking = loadTracking();
  const actions = firstHundredDays(loadPlan(), loadTopics(), tracking)
    .flatMap((pillar) => pillar.topics.flatMap((topic) => topic.actions));
  for (const action of actions) {
    assert.deepEqual(action.evidence, tracking.items?.[action.id]?.evidence ?? []);
    assert.ok(!action.related.some((item) => item.id === action.id), `${action.id} relates to itself`);
    const norms = new Set(action.evidence.map((entry) => entry.url));
    for (const item of action.related) {
      const shared = tracking.items[item.id].evidence.some((entry) => norms.has(entry.url));
      assert.ok(shared, `${action.id} → ${item.id} share no norm`);
    }
  }
});
