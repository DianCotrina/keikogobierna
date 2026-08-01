/**
 * Selecting one minister's coverage out of the published index.
 *
 * Pure and separate from the renderer for the reason search.mjs is: it can be
 * tested under `node --test`, where there is no DOM. The payload is fetched
 * from a data branch, so every shape it could arrive in has to be survivable —
 * a missing file, a half-written file, or an older schema must render an empty
 * section rather than break the dossier around it.
 */
export function entriesFor(payload, slug) {
  const map = payload && typeof payload === 'object' ? payload.ministers : null;
  if (!map || typeof map !== 'object' || Array.isArray(map)) return [];
  const entries = map[slug];
  if (!Array.isArray(entries)) return [];
  return entries.filter(
    (e) =>
      e &&
      typeof e.title === 'string' &&
      typeof e.url === 'string' &&
      typeof e.source === 'string' &&
      typeof e.published === 'string',
  );
}
