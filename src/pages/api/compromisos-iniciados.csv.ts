import type { APIRoute } from 'astro';
import { startedCommitments, toCsv } from '../../lib/started.mjs';
import { limaToday } from '../../lib/mandate.mjs';

// One row per started commitment, for spreadsheets. Same data as the JSON.
export const GET: APIRoute = () =>
  new Response(toCsv(startedCommitments({ today: limaToday() })), {
    headers: { 'Content-Type': 'text/csv; charset=utf-8' },
  });
