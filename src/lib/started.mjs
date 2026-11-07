import { loadPlan, loadTopics, loadTracking, statusOf } from './plan.mjs';
import { currentCabinet } from './cabinet.mjs';
import { governmentDay } from './mandate.mjs';
import { splitEvidenceNote } from './format.mjs';
import { shortNorma } from './infographic.mjs';

// Every commitment with certified evidence (in progress or fulfilled), with all
// it took to certify it, for the open-data files and the per-commitment images.
// Goals (.M) never appear: they move on statistics, not norms.

const STATUS_LABEL = { in_progress: 'En progreso', fulfilled: 'Cumplido' };
const SITE = 'https://www.keikogobierna.com';

const plain = (segments) => segments.map((part) => part.text).join('').trim();
const DAY_MS = 86_400_000;
const daysBetween = (from, to) => Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / DAY_MS);

/** "t2-7.C03" → "t2-7-c03": the image file name for a commitment. */
export const imageSlug = (id) => id.toLowerCase().replace('.', '-');

function median(values) {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function startedCommitments({ today, plan = loadPlan(), topics = loadTopics(), tracking = loadTracking(), cabinet = currentCabinet() } = {}) {
  // A log line describes one norma once; commitments certified with the same
  // norma share it, so find it by norma URL, not by commitment id. Log dates
  // can trail the evidence date by a day, so the date isn't part of the match.
  const urlsOf = (id) => new Set((tracking.items?.[id]?.evidence ?? []).map((entry) => entry.url));
  const summaryFor = (entry) => (tracking.log ?? []).find((line) => urlsOf(line.item).has(entry.url))?.text ?? null;

  const rows = [];
  for (const pillar of plan.pillars) {
    for (const meta of plan.topics.filter((topic) => topic.pillar === pillar.id)) {
      const file = topics.get(meta.id);
      const entries = [
        ...file.groups.flatMap((group) => group.proposals.map((item) => ({ item, kind: 'proposal', group: group.title ?? 'Generales' }))),
        ...file.first_100_days.map((item) => ({ item, kind: 'first_100_days', group: 'Primeros 100 días' })),
      ];
      for (const { item, kind, group } of entries) {
        const status = statusOf(item.id, tracking);
        if (status !== 'in_progress' && status !== 'fulfilled') continue;
        const norms = [...(tracking.items[item.id].evidence ?? [])]
          .sort((a, b) => a.date.localeCompare(b.date))
          .map((entry) => {
            const { does, pending } = splitEvidenceNote(entry.note);
            return {
              date: entry.date,
              government_day: governmentDay(entry.date),
              norma: shortNorma(entry.source),
              source: entry.source,
              url: entry.url,
              summary: summaryFor(entry),
              does: plain(does),
              pending: plain(pending) || null,
            };
          });
        const first = norms[0];
        const latest = norms.at(-1);
        rows.push({
          id: item.id,
          code: item.id.split('.')[1],
          kind,
          pillar: { id: pillar.id, name: pillar.name },
          topic: { id: meta.id, name: meta.name, slug: meta.slug },
          group,
          text: item.text,
          status,
          status_label: STATUS_LABEL[status],
          started_on: first?.date ?? null,
          started_government_day: first?.government_day ?? null,
          days_since_start: first && today ? daysBetween(first.date, today) : null,
          latest_norm_on: latest?.date ?? null,
          norm_count: norms.length,
          norms,
          shares_norms_with: [],
          responsible: cabinet
            .filter((row) => row.person && row.portfolio.topics.includes(meta.id))
            .map((row) => ({ ministry: row.portfolio.name, minister: row.person.name, minister_url: `${SITE}/gabinete/${row.person.slug}/` })),
          page_url: `${SITE}/temas/${meta.slug}/#${item.id}`,
          image_url: `${SITE}/infografias/compromiso-${imageSlug(item.id)}.png`,
        });
      }
    }
  }

  for (const row of rows) {
    const mine = new Set(row.norms.map((norm) => norm.url));
    row.shares_norms_with = rows.filter((other) => other.id !== row.id && other.norms.some((norm) => mine.has(norm.url))).map((other) => other.id);
  }
  return rows;
}

/** Metrics computed from the tracker itself (no visitor data). */
export function startedSummary(rows, totals) {
  const count = (key) =>
    Object.entries(rows.reduce((acc, row) => ((acc[key(row)] = (acc[key(row)] ?? 0) + 1), acc), {}))
      .map(([name, started]) => ({ name, started }))
      .sort((a, b) => b.started - a.started || a.name.localeCompare(b.name, 'es'));
  const daysToFirst = rows.map((row) => row.started_government_day).filter((day) => day !== null);
  const distinctNorms = new Set(rows.flatMap((row) => row.norms.map((norm) => norm.url)));
  return {
    commitments_total: totals.total,
    started: rows.length,
    in_progress: rows.filter((row) => row.status === 'in_progress').length,
    fulfilled: rows.filter((row) => row.status === 'fulfilled').length,
    first_100_days_started: rows.filter((row) => row.kind === 'first_100_days').length,
    distinct_norms: distinctNorms.size,
    government_day_of_first_norm: { min: Math.min(...daysToFirst), median: median(daysToFirst), max: Math.max(...daysToFirst) },
    by_pillar: count((row) => row.pillar.name),
    by_topic: count((row) => row.topic.name),
    by_ministry: count((row) => row.responsible.map((r) => r.ministry).join(' / ') || 'Sin cartera asignada'),
  };
}

const CSV_COLUMNS = [
  ['id', (r) => r.id],
  ['tipo', (r) => (r.kind === 'first_100_days' ? 'Acción de los primeros 100 días' : 'Propuesta')],
  ['pilar', (r) => r.pillar.name],
  ['tema', (r) => r.topic.name],
  ['grupo', (r) => r.group],
  ['compromiso', (r) => r.text],
  ['estado', (r) => r.status_label],
  ['iniciado_el', (r) => r.started_on],
  ['dia_de_gobierno', (r) => r.started_government_day],
  ['dias_desde_inicio', (r) => r.days_since_start],
  ['normas', (r) => r.norm_count],
  ['primera_norma', (r) => r.norms[0]?.norma],
  ['primera_norma_url', (r) => r.norms[0]?.url],
  ['ultima_norma', (r) => r.norms.at(-1)?.norma],
  ['ultima_norma_fecha', (r) => r.latest_norm_on],
  ['ultima_norma_url', (r) => r.norms.at(-1)?.url],
  ['resumen', (r) => r.norms.at(-1)?.summary ?? r.norms.at(-1)?.does],
  ['que_falta', (r) => r.norms.at(-1)?.pending],
  ['mismas_normas_que', (r) => r.shares_norms_with.join(' | ')],
  ['ministerio', (r) => r.responsible.map((x) => x.ministry).join(' | ')],
  ['ministro', (r) => r.responsible.map((x) => x.minister).join(' | ')],
  ['pagina', (r) => r.page_url],
  ['ficha_png', (r) => r.image_url],
];

const cell = (value) => {
  const text = value === null || value === undefined ? '' : String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
};

/** RFC 4180 CSV with a UTF-8 BOM, so Excel opens accents correctly. */
export function toCsv(rows) {
  const lines = [CSV_COLUMNS.map(([name]) => name).join(',')];
  for (const row of rows) lines.push(CSV_COLUMNS.map(([, get]) => cell(get(row))).join(','));
  return `﻿${lines.join('\r\n')}\r\n`;
}
