/**
 * When each page's content last changed, read off the dated records behind it.
 *
 * Feeds the sitemap's <lastmod>, `dateModified` in structured data and the
 * visible "último movimiento" lines. A date only appears where a record backs
 * it: a topic with no logged movement gets no date rather than the date of the
 * last site-wide review, which would claim a change that never happened.
 */
import { loadPlan, loadTracking } from './plan.mjs';
import { loadMinisters, loadTenures, loadAnnouncements } from './cabinet.mjs';

const ISO_DATE = /^\d{4}-\d{2}-\d{2}/;

/** Newest ISO date in the list, as YYYY-MM-DD, or null when there is none. */
export function latestDate(dates) {
  let latest = null;
  for (const date of dates) {
    if (typeof date !== 'string' || !ISO_DATE.test(date)) continue;
    const day = date.slice(0, 10);
    if (!latest || day > latest) latest = day;
  }
  return latest;
}

const topicOf = (itemId) => itemId.split('.')[0];

/** Latest log entry, evidence or measurement for any item of the topic. */
export function topicLastModified(tracking, topicId) {
  const dates = [];
  for (const entry of tracking.log ?? []) {
    if (topicOf(entry.item) === topicId) dates.push(entry.date);
  }
  for (const [id, item] of Object.entries(tracking.items ?? {})) {
    if (topicOf(id) !== topicId) continue;
    for (const evidence of item.evidence ?? []) dates.push(evidence.date);
  }
  for (const [id, series] of Object.entries(tracking.measurements ?? {})) {
    if (topicOf(id) !== topicId) continue;
    for (const point of series.points ?? []) dates.push(point.date);
  }
  return latestDate(dates);
}

/** Every dated fact on a minister's ficha: tenures, normas, judicial entries. */
export function ministerLastModified(slug, data = {}) {
  const ministers = data.ministers ?? loadMinisters();
  const tenures = data.tenures ?? loadTenures();
  const announcements = data.announcements ?? loadAnnouncements();
  const person = ministers.find((p) => p.slug === slug);
  const dates = [];
  for (const tenure of tenures) {
    if (tenure.person !== slug) continue;
    dates.push(tenure.start, tenure.end, tenure.appointment_norma?.date, tenure.exit_norma?.date);
  }
  for (const entry of person?.judicial ?? []) dates.push(entry.date);
  for (const announcement of announcements) {
    if (announcement.person === slug) dates.push(announcement.date);
  }
  return latestDate(dates);
}

/**
 * Site path → YYYY-MM-DD for every page whose date the data can vouch for.
 * Pages missing from the map (privacy, about, the client-fed news page) get
 * no <lastmod> at all.
 */
export function pageLastModified({ plan = loadPlan(), tracking = loadTracking(), ministers = loadMinisters() } = {}) {
  const map = new Map();
  if (tracking.updated) {
    for (const path of ['/', '/primeros-100-dias/', '/fuentes/']) map.set(path, tracking.updated);
  }
  for (const topic of plan.topics) {
    const date = topicLastModified(tracking, topic.id);
    if (date) map.set(`/temas/${topic.slug}/`, date);
  }
  const cabinetDates = [];
  for (const person of ministers) {
    const date = ministerLastModified(person.slug, { ministers });
    if (date) {
      map.set(`/gabinete/${person.slug}/`, date);
      cabinetDates.push(date);
    }
  }
  const cabinet = latestDate(cabinetDates);
  if (cabinet) map.set('/gabinete/', cabinet);
  return map;
}
