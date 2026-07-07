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
