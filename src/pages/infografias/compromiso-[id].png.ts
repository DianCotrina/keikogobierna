import type { APIRoute } from 'astro';
import { imageSlug, startedCommitments } from '../../lib/started.mjs';
import { renderCommitment } from '../../lib/infographic-render.mjs';
import { limaToday } from '../../lib/mandate.mjs';

// One image per started commitment: /infografias/compromiso-t2-7-c03.png.
export function getStaticPaths() {
  return startedCommitments({ today: limaToday() }).map((row) => ({ params: { id: imageSlug(row.id) }, props: { row } }));
}

export const GET: APIRoute = async ({ props }) =>
  new Response(await renderCommitment(props.row, limaToday()), { headers: { 'Content-Type': 'image/png' } });
