import type { APIRoute } from 'astro';
import { commitmentStats, loadTopics, loadTracking } from '../../lib/plan.mjs';
import { startedCommitments, startedSummary } from '../../lib/started.mjs';
import { limaToday } from '../../lib/mandate.mjs';
import pkg from '../../../package.json';

// Static datos-abiertos endpoint: every started commitment with the norms that
// certify it, plus metrics computed from the tracker. Same rows as the CSV.
export const GET: APIRoute = () => {
  const today = limaToday();
  const rows = startedCommitments({ today });
  const payload = {
    meta: {
      version: pkg.version,
      generated: new Date().toISOString(),
      as_of: today,
      source: 'https://github.com/DianCotrina/keikogobierna',
      license: 'Datos del plan: documento público inscrito ante el JNE. Seguimiento: keikogobierna.',
      definitions: {
        started: 'En progreso o cumplido, según una norma publicada en El Peruano y revisada por una persona.',
        government_day: 'Día de gobierno de la norma; el 28 de julio de 2026 es el día 1.',
        csv: 'https://www.keikogobierna.com/api/compromisos-iniciados.csv',
      },
    },
    summary: startedSummary(rows, commitmentStats(loadTopics(), loadTracking())),
    commitments: rows,
  };
  return new Response(JSON.stringify(payload), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
};
