/**
 * Build-time access to the cabinet data, plus the aggregates the pages need.
 *
 * Three entities, mirroring the plan data's registry / detail / living-state
 * split: `portfolios` is a frozen registry, `people` carries the dossiers, and
 * `tenures` is the edge between them and the only file that changes often.
 *
 * JSON arrives through static ESM imports, like plan.mjs — `fs` reads break
 * under the bundler. People live in one file rather than one file per person
 * because static imports cannot enumerate a directory that grows every time
 * the cabinet changes.
 *
 * The loader-shaped functions take an optional `data` argument so tests can
 * supply a roster without depending on whatever is committed today.
 */
import portfoliosFile from '../data/cabinet/portfolios.json' with { type: 'json' };
import peopleFile from '../data/cabinet/people.json' with { type: 'json' };
import tenuresFile from '../data/cabinet/tenures.json' with { type: 'json' };
import announcementsFile from '../data/cabinet/announcements.json' with { type: 'json' };

import { loadPlan } from './plan.mjs';
import { activeEntries } from './judicial.mjs';
import { plural } from './format.mjs';

const MS_PER_DAY = 86_400_000;

export function loadPortfolios() {
  return portfoliosFile.portfolios;
}

export function loadPeople() {
  return peopleFile.people;
}

export function loadTenures() {
  return tenuresFile.tenures;
}

/**
 * Cabinet members named in public but not yet appointed by norma.
 *
 * Provisional by construction: a proclamation is not a Resolución Suprema.
 * Every consumer treats these as subordinate to `tenures` -- an announcement is
 * only ever shown for a portfolio that has no open tenure, so the gazette
 * silently supersedes it the moment the norma publishes.
 */
export function loadAnnouncements() {
  return announcementsFile.announcements;
}

const dataset = (data) => ({
  people: data?.people ?? loadPeople(),
  tenures: data?.tenures ?? loadTenures(),
  announcements: data?.announcements ?? loadAnnouncements(),
});

export function portfolioById(id) {
  return loadPortfolios().find((p) => p.id === id);
}

/** The plan topics a ministry is accountable for, in plan order. */
export function portfolioTopics(portfolioId) {
  const portfolio = portfolioById(portfolioId);
  if (!portfolio) return [];
  const ids = new Set(portfolio.topics);
  return loadPlan().topics.filter((t) => ids.has(t.id));
}

const atUtc = (iso) => Date.parse(`${iso}T00:00:00Z`);

/** Whole days served. An open tenure counts to `today`; a closed one to its end. */
export function tenureDays(tenure, today = new Date()) {
  const start = atUtc(tenure.start);
  const end = tenure.end ? atUtc(tenure.end) : today.getTime();
  return Math.max(0, Math.floor((end - start) / MS_PER_DAY));
}

/** Spanish label for a day count, shared so the card and the dossier agree. */
export function daysLabel(days) {
  if (days === null || days === undefined) return '';
  if (days === 0) return 'Asume hoy';
  return `${plural(days, 'día', 'días')} en el cargo`;
}

/**
 * One row per portfolio, vacancies included — the roster is about the offices,
 * not only the people currently filling them.
 */
export function currentCabinet(data, today = new Date()) {
  const { people, tenures, announcements } = dataset(data);
  return loadPortfolios().map((portfolio) => {
    const tenure = tenures.find((t) => t.portfolio === portfolio.id && !t.end) ?? null;
    const person = tenure ? people.find((p) => p.slug === tenure.person) ?? null : null;
    // An announcement only surfaces while the gazette is silent.
    const announced = tenure
      ? null
      : announcements.find((a) => a.portfolio === portfolio.id) ?? null;
    // `person` on an announcement is set by hand once someone has confirmed the
    // press-reported name is that ficha — a name match is not an identity
    // match. Absent or unresolvable, the card shows the raw reported name only.
    const announcement = announced
      ? { ...announced, person: people.find((p) => p.slug === announced.person) ?? null }
      : null;
    return {
      portfolio,
      person,
      tenure,
      announcement,
      days: tenure ? tenureDays(tenure, today) : null,
    };
  });
}

/** Closed tenures, most recently ended first. */
export function pastTenures(data) {
  const { people, tenures } = dataset(data);
  return tenures
    .filter((t) => t.end)
    .sort((a, b) => b.end.localeCompare(a.end))
    .map((tenure) => ({
      tenure,
      person: people.find((p) => p.slug === tenure.person) ?? null,
      portfolio: portfolioById(tenure.portfolio) ?? null,
      days: tenureDays(tenure),
    }));
}

export function cabinetStats(data, today = new Date()) {
  const { people, tenures, announcements } = dataset(data);
  const serving = tenures.filter((t) => !t.end);
  const servedPortfolios = new Set(serving.map((t) => t.portfolio));
  const servingSlugs = new Set(serving.map((t) => t.person));

  return {
    portfolios: loadPortfolios().length,
    serving: serving.length,
    // Counts sitting ministers with at least one live proceeding. Someone whose
    // only entries are archived, prescribed or acquitted is deliberately absent.
    withActiveCases: people
      .filter((p) => servingSlugs.has(p.slug))
      .filter((p) => activeEntries(p).length > 0).length,
    // Outstanding announcements only: once the norma lands the portfolio has a
    // tenure and the announcement stops counting.
    announced: announcements.filter((a) => !servedPortfolios.has(a.portfolio)).length,
    changes: tenures.filter((t) => t.end).length,
    daysSinceStart: serving.length
      ? Math.max(...serving.map((t) => tenureDays(t, today)))
      : 0,
  };
}
