/**
 * Selecting one minister's coverage out of the published index, and deciding
 * what the dossier should show for it.
 *
 * Pure and separate from the renderer for the reason search.mjs is: it can be
 * tested under `node --test`, where there is no DOM. The payload is fetched
 * from a data branch, so every shape it could arrive in has to be survivable —
 * a missing file, a half-written file, a stale file, or an older schema must
 * render the load-failure state rather than assert something the site never
 * actually checked.
 */

// The scheduled job runs 4x/day; 36h is several missed runs, not a blip. A
// payload older than this must be treated exactly like a fetch failure — it
// cannot go on asserting "no coverage" (or a week-old "here is the coverage")
// once the job that keeps that claim honest has stopped running.
export const STALE_AFTER_HOURS = 36;
const STALE_AFTER_MS = STALE_AFTER_HOURS * 60 * 60 * 1000;

function generatedAtMs(payload) {
  const generated = payload && typeof payload === 'object' ? payload.generated : null;
  if (typeof generated !== 'string') return null;
  const ms = Date.parse(generated);
  return Number.isNaN(ms) ? null : ms;
}

/** A missing, unparseable, or too-old `generated` makes the whole payload unusable. */
export function isStale(payload, now = new Date()) {
  const ms = generatedAtMs(payload);
  if (ms === null) return true;
  return now.getTime() - ms > STALE_AFTER_MS;
}

function isValidEntry(e) {
  return (
    e &&
    typeof e.title === 'string' &&
    typeof e.url === 'string' &&
    typeof e.source === 'string' &&
    typeof e.published === 'string' &&
    // A malformed date must not reach formatDateEs, which does not guard
    // against one — "not-a-date" would render "NaN de undefined de NaN"
    // beside a real headline.
    /^\d{4}-\d{2}-\d{2}/.test(e.published) &&
    // One of two fixed words the scraper writes — anything else is a schema
    // this renderer does not know how to draw, same as a missing field.
    (e.matched_in === 'title' || e.matched_in === 'summary')
  );
}

/** The raw value stored under `slug`, or `undefined` when the slug is not in the map at all. */
function rawEntriesFor(payload, slug) {
  const map = payload && typeof payload === 'object' && !Array.isArray(payload) ? payload.ministers : null;
  if (!map || typeof map !== 'object' || Array.isArray(map)) return undefined;
  return map[slug];
}

/** This slug's entries that pass validation — malformed siblings are dropped. */
export function entriesFor(payload, slug) {
  const raw = rawEntriesFor(payload, slug);
  return Array.isArray(raw) ? raw.filter(isValidEntry) : [];
}

/**
 * What the dossier should render for a slug, given the fetched payload.
 *
 * The one place that decides "list" vs. "empty" vs. "error", so the decision
 * is testable without a DOM — the renderer only asks this and draws the
 * answer. Three ways to land on "error":
 *   - the payload itself is stale, missing, or unparseable (see `isStale`);
 *   - the slug is present but its value is not the array the schema promises;
 *   - the slug is present with entries, but every single one is malformed —
 *     that is "could not read this minister's coverage", not "confirmed
 *     none", and must not render as the empty state.
 * A slug absent from the map entirely is the one genuine "no coverage".
 */
export function resolveCoverage(payload, slug, now = new Date()) {
  if (isStale(payload, now)) return { status: 'error' };

  const raw = rawEntriesFor(payload, slug);
  if (raw === undefined) return { status: 'empty' };
  if (!Array.isArray(raw)) return { status: 'error' };

  const entries = raw.filter(isValidEntry);
  if (raw.length > 0 && entries.length === 0) return { status: 'error' };
  return entries.length === 0 ? { status: 'empty' } : { status: 'list', entries };
}
