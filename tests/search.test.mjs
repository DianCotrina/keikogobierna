import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { buildCorpus, foldText, foldWithMap, prepare, searchCorpus } from '../src/lib/search.mjs';
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

const prepared = prepare(corpus);
const find = (q) => searchCorpus(prepared, q);

describe('searchCorpus — idle', () => {
  test('a query under two characters searches nothing', () => {
    for (const q of ['', '  ', 'a']) {
      const result = find(q);
      assert.equal(result.mode, 'idle');
      assert.equal(result.total, 0);
      assert.deepEqual(result.groups, []);
    }
  });
});

describe('searchCorpus — strict', () => {
  test('"beca" finds 19 commitments across 6 temas', () => {
    // 16 propuestas, 2 acciones de 100 días and 1 meta. The meta only turns up
    // because metas are in the corpus at all — scanning propuestas alone
    // undercounts, which is the whole reason this number is asserted.
    const result = find('beca');
    assert.equal(result.mode, 'strict');
    assert.equal(result.total, 19);
    assert.equal(result.groups.length, 6);
  });

  test('"beca" reaches temas nobody would think to open', () => {
    const slugs = find('beca').groups.map((g) => g.slug);
    assert.ok(slugs.includes('orden-ciudadano'), slugs.join(','));
    assert.ok(slugs.includes('orden-juridico'), slugs.join(','));
  });

  test('"beca 18" requires both words', () => {
    const result = find('beca 18');
    assert.equal(result.mode, 'strict');
    assert.equal(result.total, 2);
  });

  test('accents are irrelevant', () => {
    assert.deepEqual(
      find('educación').groups.map((g) => g.slug),
      find('educacion').groups.map((g) => g.slug),
    );
  });

  test('a term matches inside a longer word', () => {
    // "beca" must reach PRONABEC and "becas"; Spanish inflection makes
    // prefix-only matching useless here.
    assert.ok(find('beca').total > find('becas').total);
  });

  test('nothing at all is an empty strict result, not a widened one', () => {
    const result = find('zzzzq');
    assert.equal(result.mode, 'strict');
    assert.equal(result.total, 0);
  });
});

describe('searchCorpus — grouping and ranges', () => {
  test('groups are ordered by hit count and capped at three items', () => {
    const result = find('beca');
    const counts = result.groups.map((g) => g.count);
    assert.deepEqual(counts, [...counts].sort((a, b) => b - a));
    for (const group of result.groups) {
      assert.ok(group.items.length <= 3);
      assert.ok(group.count >= group.items.length);
      assert.ok(group.name.length > 0);
    }
  });

  test('the cap can be lifted for one tema', () => {
    const capped = find('beca').groups.find((g) => g.slug === 'ninos-adolescentes-y-jovenes');
    const full = searchCorpus(prepared, 'beca', { limitPerGroup: Infinity })
      .groups.find((g) => g.slug === 'ninos-adolescentes-y-jovenes');
    assert.equal(capped.items.length, 3);
    assert.equal(full.items.length, full.count);
    assert.ok(full.count > 3);
  });

  test('ranges point at the matched text in the original string', () => {
    const hit = find('educación').groups.flatMap((g) => g.items)
      .find((r) => foldText(r.item.x).includes('educacion'));
    assert.ok(hit, 'expected at least one hit containing the word');
    const [start, end] = hit.ranges[0];
    assert.equal(foldText(hit.item.x.slice(start, end)), 'educacion');
  });
});

describe('searchCorpus — widening', () => {
  test('an impossible combination widens instead of returning nothing', () => {
    const result = find('beca dental');
    assert.equal(result.mode, 'widened');
    assert.ok(result.total > 0);
  });

  test('every widened hit really matched something', () => {
    for (const group of find('beca dental').groups) {
      for (const { item, ranges } of group.items) {
        assert.ok(ranges.length > 0, `${item.i} kept with no match`);
      }
    }
  });

  test('a single term never widens', () => {
    assert.equal(find('beca').mode, 'strict');
    assert.equal(find('zzzzq').mode, 'strict');
  });

  test('terms under two characters are ignored, not failed on', () => {
    // "beca 1" must behave like "beca": the stray digit is dropped, not
    // treated as an unmatchable term that forces widening.
    const result = find('beca 1');
    assert.equal(result.mode, 'strict');
    assert.equal(result.total, 19);
  });
});
