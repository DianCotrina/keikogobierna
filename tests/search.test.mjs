import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { foldText, foldWithMap } from '../src/lib/search.mjs';

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
