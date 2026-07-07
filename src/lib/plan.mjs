import { readFileSync, readdirSync } from 'node:fs';

const dataUrl = (relativePath) => new URL(`../data/${relativePath}`, import.meta.url);

function readJson(relativePath) {
  const raw = readFileSync(dataUrl(relativePath), 'utf8');
  return JSON.parse(raw);
}

export function loadPlan() {
  return readJson('plan/index.json');
}

export function loadTopics() {
  const topicsDirUrl = dataUrl('plan/topics/');
  const files = readdirSync(topicsDirUrl).filter((name) => name.endsWith('.json'));
  const topics = new Map();
  for (const file of files) {
    const raw = readFileSync(new URL(file, topicsDirUrl), 'utf8');
    const topic = JSON.parse(raw);
    topics.set(topic.id, topic);
  }
  return topics;
}

export function loadGoals() {
  return readJson('plan/goals/goals-2031.json').goals;
}

export function loadTracking() {
  return readJson('tracking.json');
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
