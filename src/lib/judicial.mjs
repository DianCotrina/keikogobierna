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
import { plural } from './format.mjs';

export const STAGES = {
  sentencia_firme: { label: 'Sentencia firme', color: 'rojo', rank: 6 },
  // "no firme" rather than "en apelación": the key is only that the sentence
  // has not become final. It covers one under appeal, one still within the term
  // to appeal, and one whose finality we have not been able to establish --
  // three different situations that "en apelación" asserted wrongly for two.
  sentencia_no_firme: { label: 'Sentencia no firme', color: 'rojo', rank: 5 },
  juicio_oral: { label: 'En juicio oral', color: 'ambar', rank: 4 },
  acusacion_fiscal: { label: 'Acusación fiscal', color: 'ambar', rank: 3 },
  investigacion_preparatoria: { label: 'Investigación preparatoria', color: 'ambar', rank: 2 },
  investigacion_preliminar: { label: 'Investigación preliminar', color: 'ambar', rank: 1 },
  absuelto: { label: 'Absuelto', color: 'verde', rank: 0 },
  archivado: { label: 'Archivado', color: 'plomo', rank: 0 },
  prescrito: { label: 'Prescrito', color: 'plomo', rank: 0 },
};

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

/**
 * Is the crime in this entry still an accusation rather than a fact?
 *
 * The stage is a fact -- a case really is in investigación preliminar -- but
 * the crime attributed inside it is not, until a sentence is final. So the
 * qualifier belongs to the crime and is derived from the stage, never typed
 * into an entry's prose, or the data drifts from the disclaimer above it.
 *
 * `sentencia_firme` is excluded on purpose: it is res judicata, and calling it
 * "presunto" would misstate the record and cheapen the word everywhere else it
 * appears. Rank 0 is excluded too -- an absolución needs no hedging, and
 * qualifying a favourable outcome would read as insinuation.
 */
export function isAlleged(stage) {
  const { rank } = stageMeta(stage);
  return rank >= 1 && stage !== 'sentencia_firme';
}

/**
 * Does this entry rest only on press reporting, with no primary document?
 *
 * The workflow says to use a press signal to go looking for the resolution and
 * never to stage from a headline. Sometimes the resolution cannot be reached:
 * the Poder Judicial's search is captcha-gated and needs an expediente number
 * the article did not print. Publishing anyway is defensible -- it is a public
 * report about a public official, attributed -- but publishing it as though we
 * had read the ruling is not, and until now the page rendered both identically.
 *
 * So the reader is told which one they are looking at, and the entry's date is
 * labelled as the report's rather than the ruling's, because that is the only
 * date we actually have.
 */
export function isPressOnly(entry) {
  const sources = (entry && Array.isArray(entry.sources)) ? entry.sources : [];
  return sources.length > 0 && !sources.some((s) => s && s.kind === 'primary');
}

const entriesOf = (person) => (person && Array.isArray(person.judicial)) ? person.judicial : [];

/** Entries that represent a live proceeding — everything above rank 0. */
export function activeEntries(person) {
  return entriesOf(person).filter((e) => stageMeta(e.stage).rank > 0);
}

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

  // A non-final sentence is counted apart from a firm one. Both used to read
  // "condena", which stated as settled fact the very thing the entry below
  // qualifies as presunto -- the summary and the entry have to agree, and the
  // one that must give is the summary.
  const firm = active.filter((e) => e.stage === 'sentencia_firme').length;
  const notFirm = active.filter((e) => e.stage === 'sentencia_no_firme').length;
  const open = active.length - firm - notFirm;
  const detail = [
    firm > 0 ? plural(firm, 'condena firme', 'condenas firmes') : null,
    notFirm > 0 ? plural(notFirm, 'sentencia no firme', 'sentencias no firmes') : null,
    open > 0 ? plural(open, 'proceso abierto', 'procesos abiertos') : null,
  ].filter(Boolean).join(' · ');

  return { label: meta.label, color: meta.color, detail };
}
