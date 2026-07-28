import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { buildCorpus, foldText, foldWithMap } from '../src/lib/search.mjs';
import { loadPlan, loadTopics, loadGoals } from '../src/lib/plan.mjs';

// Built from the real committed plan, not a fixture: the guarantees that matter
// here are about the actual 764 commitments a visitor searches.
const corpus = buildCorpus(loadPlan(), loadTopics(), loadGoals(), '9.9.9');

describe('foldText', () => {
  test('strips accents and lowercases', () => {
    assert.equal(foldText('Educación'), 'educacion');
    assert.equal(foldText('NIÑOS Y JÓVENES'), 'ninos y jovenes');
  });

  test('handles null and empty input', () => {
    assert.equal(foldText(''), '');
    assert.equal(foldText(null), '');
    assert.equal(foldText(undefined), '');
  });
});

describe('foldWithMap', () => {
  test('maps folded offsets back to the source', () => {
    const source = 'Beca Educación';
    const { folded, map } = foldWithMap(source);
    assert.equal(folded, 'beca educacion');
    const at = folded.indexOf('educacion');
    assert.equal(map[at], 5);
    assert.equal(map[at + 'educacion'.length], source.length);
  });

  test('survives a fold that changes length', () => {
    // NFKD expands the ligature to two characters; the map must still point
    // back at the single source character, or the highlight drifts.
    const { folded, map } = foldWithMap('eﬁcaz');
    assert.equal(folded, 'eficaz');
    assert.equal(map[1], 1);
    assert.equal(map[2], 1);
    assert.equal(map[3], 2);
  });

  test('has a sentinel so an end offset always resolves', () => {
    const { folded, map } = foldWithMap('beca');
    assert.equal(map[folded.length], 4);
  });
});

describe('buildCorpus', () => {
  test('covers every commitment in the plan', () => {
    assert.equal(corpus.items.length, 764);
    assert.equal(corpus.version, '9.9.9');
  });

  test('lists the 23 topics in plan order', () => {
    assert.equal(corpus.topics.length, 23);
    assert.equal(corpus.topics[0].s, 'orden-ciudadano');
    assert.ok(corpus.topics.every((t) => t.s && t.n));
  });

  test('every item points at a topic that exists', () => {
    // The guard that matters: a dangling slug would send search into a 404.
    const slugs = new Set(corpus.topics.map((t) => t.s));
    assert.deepEqual(corpus.items.filter((item) => !slugs.has(item.t)), []);
  });

  test('every id is unique', () => {
    assert.equal(new Set(corpus.items.map((item) => item.i)).size, corpus.items.length);
  });

  test('carries all three kinds', () => {
    const kinds = corpus.items.reduce((acc, item) => {
      acc[item.k] = (acc[item.k] ?? 0) + 1;
      return acc;
    }, {});
    assert.deepEqual(kinds, { p: 632, c: 67, m: 65 });
  });

  test('a meta searches its indicator but does not display it', () => {
    const meta = corpus.items.find((item) => item.i === 't1-1.M01');
    assert.ok(!meta.x.includes('INEI'), 'display text stays clean');
    assert.ok(meta.q.includes('INEI'), 'indicator is searchable');
    assert.ok(meta.q.startsWith(meta.x), 'q must extend x so offsets align');
  });

  test('propuestas carry their group title', () => {
    const proposal = corpus.items.find((item) => item.i === 't1-1.P01');
    assert.equal(proposal.k, 'p');
    assert.equal(proposal.t, 'orden-ciudadano');
    assert.equal(proposal.g, 'Prevención del delito');
  });
});
