import { commitmentStats, goalStats, firstHundredDaysStats, loadGoals, loadPlan, loadTopics, loadTracking, statusOf } from './plan.mjs';

// What each shareable image says, computed from the same functions the pages
// use so an image can never disagree with the site. Rendering lives in
// infographic-render.mjs; this module only decides content.

const SHORT_NORMA = [
  [/^RESOLUCIÓN MINISTERIAL/i, 'R.M.'],
  [/^RESOLUCIÓN DIRECTORAL/i, 'R.D.'],
  [/^DECRETO SUPREMO/i, 'D.S.'],
  [/^DECRETO DE URGENCIA/i, 'D.U.'],
  [/^DECRETO LEGISLATIVO/i, 'D. Leg.'],
];

/** "El Peruano — DECRETO SUPREMO N° 121-2026-PCM" → "D.S. N° 121-2026-PCM". */
export function shortNorma(source) {
  const name = source.replace(/^El Peruano — /, '');
  for (const [pattern, short] of SHORT_NORMA) {
    if (pattern.test(name)) return name.replace(pattern, short);
  }
  return name;
}

/** Cut at a word boundary so the image never shows half a word. */
export function truncate(text, max) {
  if (text.length <= max) return text;
  const cut = text.slice(0, max - 1);
  return `${cut.slice(0, cut.lastIndexOf(' ')).replace(/[,;:.]$/, '')}…`;
}

function startedItems(file, tracking) {
  return [...file.groups.flatMap((group) => group.proposals), ...file.first_100_days]
    .map((item) => ({ item, status: statusOf(item.id, tracking) }))
    .filter(({ status }) => status === 'in_progress' || status === 'fulfilled')
    .map(({ item, status }) => {
      const evidence = tracking.items[item.id].evidence ?? [];
      const latest = [...evidence].sort((a, b) => b.date.localeCompare(a.date))[0];
      return {
        id: item.id,
        code: item.id.split('.')[1],
        status,
        text: item.text,
        norma: latest ? shortNorma(latest.source) : null,
        date: latest?.date ?? null,
      };
    });
}

export function topicInfographic(topicId, data = {}) {
  const plan = data.plan ?? loadPlan();
  const topics = data.topics ?? loadTopics();
  const tracking = data.tracking ?? loadTracking();
  const goals = data.goals ?? loadGoals();
  const meta = plan.topics.find((topic) => topic.id === topicId);
  const file = topics.get(topicId);
  const stats = commitmentStats(topics, tracking, topicId);
  const goalCounts = goalStats(goals, tracking, topicId);
  return {
    kind: 'topic',
    slug: meta.slug,
    name: meta.name,
    section: file.doc_section,
    total: stats.total,
    fulfilled: stats.byStatus.fulfilled,
    inProgress: stats.byStatus.in_progress,
    started: stats.started,
    goals: { total: goalCounts.total, fulfilled: goalCounts.byStatus.fulfilled },
    items: startedItems(file, tracking),
    path: `/temas/${meta.slug}/`,
  };
}

export function planInfographic(data = {}) {
  const plan = data.plan ?? loadPlan();
  const topics = data.topics ?? loadTopics();
  const tracking = data.tracking ?? loadTracking();
  const stats = commitmentStats(topics, tracking);
  const hundred = firstHundredDaysStats(topics, tracking);
  const byTopic = plan.topics
    .map((meta) => ({ name: meta.name, ...commitmentStats(topics, tracking, meta.id) }))
    .filter((topic) => topic.started > 0)
    .sort((a, b) => b.started - a.started || a.name.localeCompare(b.name, 'es'));
  return {
    kind: 'plan',
    total: stats.total,
    fulfilled: stats.byStatus.fulfilled,
    inProgress: stats.byStatus.in_progress,
    started: stats.started,
    hundred: { total: hundred.total, inProgress: hundred.byStatus.in_progress, fulfilled: hundred.byStatus.fulfilled },
    topics: byTopic.map(({ name, started, total }) => ({ name, started, total })),
    path: '/',
  };
}
