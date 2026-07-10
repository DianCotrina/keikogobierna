import type { APIRoute } from 'astro';
import { loadPlan, loadTopics, loadGoals } from '../../lib/plan.mjs';
import pkg from '../../../package.json';

// Static datos-abiertos endpoint: rendered once at build into dist/api/plan.json.
export const GET: APIRoute = () => {
  const { plan, pillars, topics } = loadPlan();
  const topicFiles = [...loadTopics().values()];

  const payload = {
    meta: {
      version: pkg.version,
      generated: new Date().toISOString(),
      source: 'https://github.com/DianCotrina/keikogobierna',
      license: 'Datos del plan: documento público inscrito ante el JNE. Seguimiento: keikogobierna.',
    },
    plan,
    pillars,
    topics: topicFiles,
    topic_index: topics,
    goals: loadGoals(),
  };

  return new Response(JSON.stringify(payload), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
