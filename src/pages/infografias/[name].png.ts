import type { APIRoute } from 'astro';
import { loadPlan } from '../../lib/plan.mjs';
import { planInfographic, topicInfographic } from '../../lib/infographic.mjs';
import { renderInfographic } from '../../lib/infographic-render.mjs';
import { limaToday } from '../../lib/mandate.mjs';

// Written once per build, like every page: /infografias/plan-vertical.png,
// /infografias/turismo-enlace.png… "vertical" fits a WhatsApp or Instagram
// post, "enlace" is the 1200×630 card shown when a link is shared.
export function getStaticPaths() {
  const sources = [{ slug: 'plan', data: () => planInfographic() }];
  for (const topic of loadPlan().topics) {
    sources.push({ slug: topic.slug, data: () => topicInfographic(topic.id) });
  }
  return sources.flatMap(({ slug, data }) =>
    ['vertical', 'enlace'].map((format) => ({ params: { name: `${slug}-${format}` }, props: { data, format } })),
  );
}

export const GET: APIRoute = async ({ props }) => {
  const png = await renderInfographic(props.data(), props.format, limaToday());
  return new Response(png, { headers: { 'Content-Type': 'image/png' } });
};
