import type { APIRoute } from 'astro';
import { loadTracking } from '../../lib/plan.mjs';
import pkg from '../../../package.json';

// Static datos-abiertos endpoint: rendered once at build into dist/api/tracking.json.
export const GET: APIRoute = () => {
  const payload = {
    meta: {
      version: pkg.version,
      generated: new Date().toISOString(),
      source: 'https://github.com/DianCotrina/keikogobierna',
      license: 'Datos del plan: documento público inscrito ante el JNE. Seguimiento: keikogobierna.',
    },
    ...loadTracking(),
  };

  return new Response(JSON.stringify(payload), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
