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

/**
 * Flatten the plan into one searchable array. Build time only.
 *
 * Keys are single letters because they repeat 764 times: across the whole
 * corpus the short names are worth several KB on the wire.
 *
 *   i  id          k  kind: p propuesta, c 100 días, m meta
 *   t  topic slug  g  group title (propuestas only)
 *   x  the text shown to the reader
 *   q  the text searched, present only when it differs from `x`
 */
export function buildCorpus(plan, topics, goals, version) {
  const slugById = new Map(plan.topics.map((topic) => [topic.id, topic.slug]));
  const items = [];

  for (const topic of plan.topics) {
    const file = topics.get(topic.id);
    if (!file) continue;
    for (const group of file.groups ?? []) {
      for (const proposal of group.proposals ?? []) {
        items.push({ i: proposal.id, k: 'p', t: topic.slug, g: group.title ?? '', x: proposal.text });
      }
    }
    for (const action of file.first_100_days ?? []) {
      items.push({ i: action.id, k: 'c', t: topic.slug, x: action.text });
    }
  }

  for (const goal of goals) {
    const slug = slugById.get(goal.topic);
    if (!slug) continue;
    // A meta's indicator is worth searching but not worth showing. It goes in
    // `q`, which extends `x`, so offsets into the two agree for the whole of
    // `x` and a match in the indicator simply renders no highlight.
    const item = { i: goal.id, k: 'm', t: slug, x: goal.text };
    if (goal.indicator) item.q = `${goal.text} ${goal.indicator}`;
    items.push(item);
  }

  return {
    version,
    topics: plan.topics.map((topic) => ({ s: topic.slug, n: topic.name })),
    items,
  };
}
