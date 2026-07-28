/**
 * The search engine, as pure functions.
 *
 * This file runs in two places: at build time to emit the corpus, and in the
 * browser to filter it. That is deliberate — there is one matching
 * implementation, and `npm test` exercises the same code the visitor runs.
 *
 * It imports no JSON. Every caller passes data in. A static import of the plan
 * files here would drag 200 KB of commitments into the client bundle.
 */

const COMBINING_MARKS = /\p{M}/gu;

/** Lowercase and strip accents. "Educación" -> "educacion". */
export function foldText(text) {
  return (text ?? '').normalize('NFKD').replace(COMBINING_MARKS, '').toLowerCase();
}

/**
 * Fold a string while keeping a way back to the original offsets.
 *
 * Matches are found in `folded` but highlighted in the source, and folding can
 * change length (NFKD turns "ﬁ" into "fi"), so offsets cannot simply be reused.
 * Iterating by code point rather than UTF-16 unit keeps surrogate pairs intact.
 *
 * `map[i]` is the source index that produced `folded[i]`; one trailing sentinel
 * equal to the source length lets an exclusive end offset resolve.
 */
export function foldWithMap(text) {
  const source = text ?? '';
  const map = [];
  let folded = '';
  let offset = 0;
  for (const char of source) {
    const piece = foldText(char);
    for (let i = 0; i < piece.length; i += 1) map.push(offset);
    folded += piece;
    offset += char.length;
  }
  map.push(source.length);
  return { folded, map };
}
