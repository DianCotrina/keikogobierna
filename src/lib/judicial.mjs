/**
 * The judicial stage ladder.
 *
 * `rank` orders how serious a stage is, and rank 0 marks the exculpatory
 * outcomes. That distinction is load-bearing: a case that was archived or that
 * ended in acquittal must never colour a minister's badge, or the site would
 * punish people for accusations that failed. Only stages of rank >= 1 can drive
 * a badge; rank 0 entries are still published, with equal visual weight.
 *
 * Shape mirrors src/lib/statuses.mjs. Colors are @theme tokens.
 */
export const STAGES = {
  sentencia_firme: { label: 'Sentencia firme', color: 'rojo', rank: 6 },
  sentencia_no_firme: { label: 'Sentencia en apelación', color: 'rojo', rank: 5 },
  juicio_oral: { label: 'En juicio oral', color: 'ambar', rank: 4 },
  acusacion_fiscal: { label: 'Acusación fiscal', color: 'ambar', rank: 3 },
  investigacion_preparatoria: { label: 'Investigación preparatoria', color: 'ambar', rank: 2 },
  investigacion_preliminar: { label: 'Investigación preliminar', color: 'ambar', rank: 1 },
  absuelto: { label: 'Absuelto', color: 'verde', rank: 0 },
  archivado: { label: 'Archivado', color: 'plomo', rank: 0 },
  prescrito: { label: 'Prescrito', color: 'plomo', rank: 0 },
};

const CONVICTIONS = new Set(['sentencia_firme', 'sentencia_no_firme']);

/**
 * The live stages in order, rank 1 upward — the rungs a proceeding climbs.
 * Rank-0 outcomes are deliberately absent: they end a case rather than
 * advance it, and the UI shows them off the ladder for that reason.
 */
export const LADDER = Object.entries(STAGES)
  .filter(([, meta]) => meta.rank > 0)
  .sort((a, b) => a[1].rank - b[1].rank)
  .map(([stage, meta]) => ({ stage, ...meta }));

export function stageMeta(stage) {
  return STAGES[stage] ?? { label: String(stage), color: 'plomo', rank: 0 };
}

const entriesOf = (person) => (person && Array.isArray(person.judicial)) ? person.judicial : [];

/** Entries that represent a live proceeding — everything above rank 0. */
export function activeEntries(person) {
  return entriesOf(person).filter((e) => stageMeta(e.stage).rank > 0);
}

const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/**
 * A one-glance summary of a person's judicial record.
 * Returns { label, color, detail } — never null, so callers can render blindly.
 */
export function recordBadge(person) {
  const entries = entriesOf(person);

  if (entries.length === 0) {
    return {
      label: 'Sin registro público',
      color: 'plomo',
      detail: 'No hallamos procesos documentados',
    };
  }

  const active = activeEntries(person);

  // Everything resolved. Say so plainly rather than leaving an amber mark
  // behind for a proceeding that went nowhere.
  if (active.length === 0) {
    const counts = new Map();
    for (const entry of entries) {
      const label = stageMeta(entry.stage).label.toLowerCase();
      counts.set(label, (counts.get(label) ?? 0) + 1);
    }
    const detail = [...counts].map(([label, n]) => `${n} ${label}`).join(' · ');
    return { label: 'Sin procesos activos', color: 'verde', detail };
  }

  const worst = active.reduce((a, b) => (stageMeta(b.stage).rank > stageMeta(a.stage).rank ? b : a));
  const meta = stageMeta(worst.stage);

  const convictions = active.filter((e) => CONVICTIONS.has(e.stage)).length;
  const open = active.length - convictions;
  const detail = [
    convictions > 0 ? plural(convictions, 'condena', 'condenas') : null,
    open > 0 ? plural(open, 'proceso abierto', 'procesos abiertos') : null,
  ].filter(Boolean).join(' · ');

  return { label: meta.label, color: meta.color, detail };
}
