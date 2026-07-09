import planIndex from '../data/plan/index.json' with { type: 'json' };
import goalsFile from '../data/plan/goals/goals-2031.json' with { type: 'json' };
import trackingData from '../data/tracking.json' with { type: 'json' };

import topicT11 from '../data/plan/topics/t1-1-orden-ciudadano.json' with { type: 'json' };
import topicT12 from '../data/plan/topics/t1-2-lucha-contra-la-corrupcion.json' with { type: 'json' };
import topicT13 from '../data/plan/topics/t1-3-orden-economico.json' with { type: 'json' };
import topicT14 from '../data/plan/topics/t1-4-orden-juridico.json' with { type: 'json' };
import topicT21 from '../data/plan/topics/t2-1-emprendedores-mype.json' with { type: 'json' };
import topicT22 from '../data/plan/topics/t2-2-mineria.json' with { type: 'json' };
import topicT23 from '../data/plan/topics/t2-3-energia-e-hidrocarburos.json' with { type: 'json' };
import topicT24 from '../data/plan/topics/t2-4-agricultura.json' with { type: 'json' };
import topicT25 from '../data/plan/topics/t2-5-pesca-y-acuicultura.json' with { type: 'json' };
import topicT26 from '../data/plan/topics/t2-6-transportes-y-comunicaciones.json' with { type: 'json' };
import topicT27 from '../data/plan/topics/t2-7-turismo.json' with { type: 'json' };
import topicT28 from '../data/plan/topics/t2-8-industria-y-comercio-exterior.json' with { type: 'json' };
import topicT29 from '../data/plan/topics/t2-9-desarrollo-sostenible-o-ambiente.json' with { type: 'json' };
import topicT31 from '../data/plan/topics/t3-1-ninos-adolescentes-y-jovenes.json' with { type: 'json' };
import topicT32 from '../data/plan/topics/t3-2-educacion.json' with { type: 'json' };
import topicT33 from '../data/plan/topics/t3-3-salud.json' with { type: 'json' };
import topicT34 from '../data/plan/topics/t3-4-seguridad-alimentaria.json' with { type: 'json' };
import topicT35 from '../data/plan/topics/t3-5-vivienda.json' with { type: 'json' };
import topicT36 from '../data/plan/topics/t3-6-agua-y-saneamiento.json' with { type: 'json' };
import topicT37 from '../data/plan/topics/t3-7-pensiones.json' with { type: 'json' };
import topicT38 from '../data/plan/topics/t3-8-programas-sociales.json' with { type: 'json' };
import topicT39 from '../data/plan/topics/t3-9-deporte.json' with { type: 'json' };
import topicT310 from '../data/plan/topics/t3-10-peruanos-en-el-extranjero.json' with { type: 'json' };

// loadPlan/loadTopics/loadGoals/loadTracking all use static JSON imports (not
// fs.readFileSync) so Vite/Rollup can trace and inline them correctly during
// Astro's static build — a runtime `readFileSync(new URL(..., import.meta.url))`
// breaks once the bundler relocates this module into a build chunk, since the
// sibling data files never travel with it. Topic files are listed explicitly
// (rather than a directory read) for the same reason.
const TOPIC_FILES = [
  topicT11, topicT12, topicT13, topicT14,
  topicT21, topicT22, topicT23, topicT24, topicT25, topicT26, topicT27, topicT28, topicT29,
  topicT31, topicT32, topicT33, topicT34, topicT35, topicT36, topicT37, topicT38, topicT39, topicT310,
];

export function loadPlan() {
  return planIndex;
}

export function loadTopics() {
  const topics = new Map();
  for (const topic of TOPIC_FILES) {
    topics.set(topic.id, topic);
  }
  return topics;
}

export function loadGoals() {
  return goalsFile.goals;
}

export function loadTracking() {
  return trackingData;
}

export function statusOf(id, tracking) {
  return tracking.items?.[id]?.status ?? 'no_progress';
}

export function goalStats(goals, tracking, topicId) {
  const scoped = topicId ? goals.filter((goal) => goal.topic === topicId) : goals;
  const byStatus = { fulfilled: 0, in_progress: 0, no_progress: 0, unfulfilled: 0 };

  for (const goal of scoped) {
    const status = statusOf(goal.id, tracking);
    byStatus[status] = (byStatus[status] ?? 0) + 1;
  }

  const total = scoped.length;
  const progressPct = total > 0 ? Math.round((100 * byStatus.fulfilled) / total) : 0;

  return { total, byStatus, progressPct };
}

export function topicSummaries(plan, goals, tracking) {
  return plan.topics.map((topic) => {
    const pillar = plan.pillars.find((p) => p.id === topic.pillar);
    return {
      id: topic.id,
      slug: topic.slug,
      name: topic.name,
      pillar: topic.pillar,
      pillarName: pillar?.name,
      proposals: topic.proposals,
      first_100_days: topic.first_100_days,
      goals: topic.goals,
      progressPct: goalStats(goals, tracking, topic.id).progressPct,
    };
  });
}

export function updatesLog(tracking) {
  const log = tracking.log ?? [];
  return [...log].sort((a, b) => new Date(b.date) - new Date(a.date));
}

// First-100-days actions (the `.C` items) grouped by pillar then topic, in plan order.
export function firstHundredDays(plan, topics, tracking) {
  return plan.pillars.map((pillar, index) => ({
    id: pillar.id,
    name: pillar.name,
    index: index + 1,
    topics: plan.topics
      .filter((topic) => topic.pillar === pillar.id)
      .map((topic) => {
        const file = topics.get(topic.id);
        return {
          id: topic.id,
          slug: topic.slug,
          name: topic.name,
          doc_section: file.doc_section,
          actions: file.first_100_days.map((action) => ({
            id: action.id,
            text: action.text,
            status: statusOf(action.id, tracking),
          })),
        };
      })
      .filter((topic) => topic.actions.length > 0),
  }));
}

// Tally of every first-100-days action by status (a launch-window metric,
// distinct from the goal-only headline progress).
export function firstHundredDaysStats(topics, tracking) {
  const byStatus = { fulfilled: 0, in_progress: 0, no_progress: 0, unfulfilled: 0 };
  let total = 0;
  for (const file of topics.values()) {
    for (const action of file.first_100_days) {
      total += 1;
      byStatus[statusOf(action.id, tracking)] += 1;
    }
  }
  return { total, byStatus };
}

// Certified (fulfilled) proposals and 100-days actions with their evidence,
// in plan order, for the registro de cumplidas. Goals (.M items) never appear
// here — they are covered by the headline goal stats.
export function fulfilledItems(plan, topics, tracking) {
  const items = [];
  for (const pillar of plan.pillars) {
    for (const topicMeta of plan.topics.filter((t) => t.pillar === pillar.id)) {
      const file = topics.get(topicMeta.id);
      const entries = [
        ...file.groups.flatMap((group) => group.proposals),
        ...file.first_100_days,
      ];
      for (const entry of entries) {
        const tracked = tracking.items?.[entry.id];
        if (tracked?.status !== 'fulfilled') continue;
        items.push({
          id: entry.id,
          text: entry.text,
          topicName: topicMeta.name,
          topicSlug: topicMeta.slug,
          pillarId: pillar.id,
          pillarName: pillar.name,
          evidence: tracked.evidence ?? [],
        });
      }
    }
  }
  const byPillar = plan.pillars.map((pillar) => ({
    id: pillar.id,
    name: pillar.name,
    count: items.filter((item) => item.pillarId === pillar.id).length,
  }));
  return { total: items.length, byPillar, items };
}
