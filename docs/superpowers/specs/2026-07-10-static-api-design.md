# Static API endpoints (datos abiertos)

**Date:** 2026-07-10
**Status:** Approved by Diego ("proceed with 2 and 3", 2026-07-10)

## Problem

The tracking data should be consumable by third parties (journalists, researchers). The site is static, so instead of building a server API, the build emits JSON endpoints — the repo remains the single source of truth and the site becomes the API.

## Design

Two Astro static file endpoints (built into `dist/` as plain JSON):

- **`/api/plan.json`** (`src/pages/api/plan.json.ts`): `{ meta, plan, pillars, topics, goals }` — `topics` is the full topic files array (groups/proposals/first_100_days), `goals` the 65 metas.
- **`/api/tracking.json`** (`src/pages/api/tracking.json.ts`): `{ meta, ...tracking.json }` — statuses, evidence, log, verbatim.

`meta` on both: `{ version (package.json), generated (ISO date), source: "https://github.com/DianCotrina/keikogobierna", license: "Datos del plan: documento público del JNE. Seguimiento: keikogobierna." }`.

Implementation: `export const GET: APIRoute` returning `new Response(JSON.stringify(payload), { headers: { 'Content-Type': 'application/json; charset=utf-8' } })`. Data via the existing `plan.mjs` loaders. No runtime — Astro renders these once at build.

**/fuentes/ page**: new closing card «Datos abiertos» linking both endpoints, so the API is discoverable.

CORS note: static hosting decides response headers; when Vercel is set up, add `Access-Control-Allow-Origin: *` for `/api/*` in `vercel.json` (out of scope here, noted for the deploy task).

## Verification

- Build emits `dist/api/plan.json` and `dist/api/tracking.json`; both parse with `jq`; spot-check counts (23 topics, 65 goals, 65 tracked items).
- /fuentes/ shows the datos abiertos card with working links.
