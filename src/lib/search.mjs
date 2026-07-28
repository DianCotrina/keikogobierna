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

/** Terms shorter than this are dropped; a query of only such terms is idle. */
const MIN_TERM = 2;

/** Items shown per tema before the "N más" affordance. */
export const MAX_PER_GROUP = 3;

/**
 * Fold the corpus once, up front. That is the expensive half of a search; the
 * per-keystroke scan that follows costs about 0.02 ms over all 764 records, so
 * no inverted index is built — it would be ceremony.
 */
export function prepare(corpus) {
  return {
    topics: new Map(corpus.topics.map((topic, order) => [
      topic.s, { slug: topic.s, name: topic.n, order },
    ])),
    records: corpus.items.map((item) => ({ item, ...foldWithMap(item.q ?? item.x) })),
  };
}

function queryTerms(query) {
  return foldText(query).split(/\s+/).filter((term) => term.length >= MIN_TERM);
}

/** Every occurrence of `term` in `folded`, as [start, end) offsets. */
function occurrences(folded, term) {
  const found = [];
  let from = 0;
  for (;;) {
    const at = folded.indexOf(term, from);
    if (at === -1) return found;
    found.push([at, at + term.length]);
    from = at + term.length;
  }
}

function score(record, terms) {
  const hits = [];
  let matched = 0;
  let first = Infinity;
  for (const term of terms) {
    const found = occurrences(record.folded, term);
    if (found.length === 0) continue;
    matched += 1;
    first = Math.min(first, found[0][0]);
    hits.push(...found);
  }
  return { matched, first, hits };
}

/** Translate folded offsets back to source offsets, then merge what overlaps. */
function sourceRanges(hits, map) {
  const merged = [];
  for (const [start, end] of [...hits].sort((a, b) => a[0] - b[0])) {
    const range = [map[start], map[end]];
    const last = merged[merged.length - 1];
    if (last && range[0] <= last[1]) last[1] = Math.max(last[1], range[1]);
    else merged.push(range);
  }
  return merged;
}

const IDLE = { mode: 'idle', total: 0, terms: [], groups: [] };

/**
 * Filter a prepared corpus, grouped by tema.
 *
 * Every term must appear (`strict`). If no item carries all of them but some
 * carry a few, widen to the best partial matches and say so — a visitor who
 * types one word too many should see near misses, not a dead end.
 *
 * `limitPerGroup` caps the items returned per tema without touching `count`,
 * so the UI can show three and offer the rest.
 */
export function searchCorpus(prepared, query, { limitPerGroup = MAX_PER_GROUP } = {}) {
  const terms = queryTerms(query);
  if (terms.length === 0) return IDLE;

  const scored = [];
  for (const record of prepared.records) {
    const result = score(record, terms);
    if (result.matched > 0) scored.push({ record, ...result });
  }
  if (scored.length === 0) return { mode: 'strict', total: 0, terms, groups: [] };

  const best = Math.max(...scored.map((row) => row.matched));
  const kept = scored.filter((row) => row.matched === best);

  const byTopic = new Map();
  for (const row of kept) {
    const slug = row.record.item.t;
    if (!byTopic.has(slug)) byTopic.set(slug, []);
    byTopic.get(slug).push(row);
  }

  const groups = [...byTopic].map(([slug, rows]) => {
    const topic = prepared.topics.get(slug);
    rows.sort((a, b) => b.matched - a.matched
      || a.first - b.first
      || a.record.item.i.localeCompare(b.record.item.i));
    return {
      slug,
      name: topic?.name ?? slug,
      order: topic?.order ?? Number.MAX_SAFE_INTEGER,
      count: rows.length,
      items: rows.slice(0, limitPerGroup).map((row) => ({
        item: row.record.item,
        ranges: sourceRanges(row.hits, row.record.map),
      })),
    };
  });
  groups.sort((a, b) => b.count - a.count || a.order - b.order);

  return { mode: best === terms.length ? 'strict' : 'widened', total: kept.length, terms, groups };
}
