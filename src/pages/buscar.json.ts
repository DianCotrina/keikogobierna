import type { APIRoute } from 'astro';
import { loadPlan, loadTopics, loadGoals } from '../lib/plan.mjs';
import { buildCorpus } from '../lib/search.mjs';
import pkg from '../../package.json';

// The search corpus, rendered once at build into dist/buscar.json and fetched
// by the overlay the first time a visitor opens it.
//
// Deliberately not under /api/. That path is the documented datos-abiertos
// contract, with CORS and s-maxage headers set in vercel.json; search is an
// internal artifact and must never drive changes to a public API.
export const GET: APIRoute = () => {
  const corpus = buildCorpus(loadPlan(), loadTopics(), loadGoals(), pkg.version);
  return new Response(JSON.stringify(corpus), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
