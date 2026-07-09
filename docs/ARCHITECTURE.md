# Architecture

Astro static site (SSG, `output: "static"`): 25 pages (1 landing + 23 topic pages + a first-100-days page) built ahead of time from JSON data, no client framework, Tailwind v4 via the Vite plugin.

## Commands

| Command | Effect |
|---|---|
| `npm install` | Install dependencies |
| `npm run dev` | Dev server with HMR at http://localhost:3000 |
| `npm run build` | Static build to `dist/` |
| `npm run preview` | Serve the `dist/` build locally |
| `npm test` | Run `node --test tests/**/*.test.mjs` (data-layer unit tests) |
| `npm run validate` | Run `python3 tools/validate_plan_data.py` (plan tree + tracking integrity) |

## Module map

| Path | Responsibility |
|---|---|
| `astro.config.mjs` | Static output, dev/preview port 3000, `@tailwindcss/vite` plugin |
| `src/lib/plan.mjs` | Build-time data access + aggregates (pure functions, read JSON via static ESM imports — `fs` reads break under the bundler, see the comment in the file): `loadPlan`, `loadTopics`, `loadGoals`, `loadTracking`, `statusOf`, `goalStats`, `topicSummaries`, `updatesLog`, `firstHundredDays`, `firstHundredDaysStats` |
| `src/lib/statuses.mjs` | `STATUSES` map (fulfilled/in_progress/no_progress/unfulfilled → Spanish label + color) and `statusMeta()` helper |
| `src/layouts/Base.astro` | `<head>` (title/description/OG, lang `es-PE`, Google Fonts, `global.css`), header, footer, donate widget, reveal `<script>` |
| `src/components/Stamp.astro` | Rubber-stamp status chip |
| `src/components/PenProgress.astro` | Pen-stroke progress bar (dynamic width) |
| `src/components/TrackerCard.astro` | Hero "expediente" card (real aggregates) |
| `src/components/TopicCard.astro` | One topic card in the landing grid |
| `src/components/GoalRow.astro` | Goal + indicator + stamp row (topic pages) |
| `src/components/Donate.astro` | Donate pill + share button (with its client script) |
| `src/pages/index.astro` | Landing page |
| `src/pages/temas/[slug].astro` | 23 static topic pages via `getStaticPaths()` |
| `src/pages/primeros-100-dias.astro` | Dedicated page: all 67 first-100-days actions grouped by pillar → topic, with a launch-window tally |
| `src/styles/global.css` | Tailwind v4 `@theme` tokens + ported custom CSS (grain, stamps, pen, reveal, buttons) |
| `tools/validate_plan_data.py` | WAT tool: validates the `plan/` tree + `tracking.json` |

## Data flow (build-time)

There is no client-side fetch and no runtime data loading. Pages import `src/lib/plan.mjs`, which reads the static JSON files under `src/data/` synchronously at build time (`loadPlan`, `loadTopics`, `loadGoals`, `loadTracking`). `src/pages/index.astro` calls `topicSummaries()` and `goalStats()` to render the hero tracker card and the 23-topic grid. `src/pages/temas/[slug].astro` uses `getStaticPaths()` to enumerate the 23 topics from `loadPlan()`, then renders each topic's proposals, first-100-days actions, and goals (with per-topic `goalStats()`) into its own static page. `astro build` executes this once per page and emits plain HTML — nothing runs in the browser except the reveal `IntersectionObserver` script and the donate widget's small client script.

## Plan data

The plan data layer is immutable (derived from the PDF) except for the tracking state, which is living. This separation allows reliable data restoration while enabling real-time progress updates.

**Tree structure:**
```
src/data/plan/
├── index.json              # Registry: pillars (3) + topics (23 topics, 632 proposals, 67 first-100-days actions, 65 goals)
├── topics/
│   └── t1-1-orden-ciudadano.json    # ×23 (file names use Spanish slugs)
└── goals/
    └── goals-2031.json     # All goals curated by hand; proposals auto-extracted from PDF
src/data/tracking.json      # Living state: goal status + progress log
```

**ID scheme** (never changes once assigned):
- Topics: `t{pillar}-{n}` (e.g. `t1-1`)
- Proposals: `{topic}.P{nn}` (e.g. `t1-1.P07`, zero-padded, ordinal within topic)
- First-100-days actions: `{topic}.C{nn}` (e.g. `t1-1.C01`)
- Goals (metas al 2031): `{topic}.M{nn}` (e.g. `t1-1.M01`)

**Two-layer tracking rule (critical):**
- All proposals are listed and trackable.
- **The headline progress % is computed ONLY from goals** (metas al 2031), not from proposals.
- `tracking.json` stores status + evidence only for goals. Proposals seeded absent; appear there only when status first changes.

**Naming rule:**
- JSON keys, identifiers, folder names: English (e.g., `proposals`, `status`, `in_progress`).
- All user-facing content (plan names, proposal text, goal text, Spanish slugs): exactly as the PDF states.

**Extraction and curation:**
- **Proposals + first-100-days actions:** Auto-extracted from PDF by `tools/extract_plan_pdf.py` (deterministic, never overwrites goals); extraction rules are applied post-extraction via `src/data/plan/overrides.json`.
- **Goals (metas al 2031):** Curated by hand in `src/data/plan/goals/goals-2031.json`; the PDF tables are not machine-parseable, so goals are never auto-regenerated.
- **Tracking state:** Lives in `src/data/tracking.json`; edit freely (log your progress), then validate.
- **Proposal IDs are frozen** as of the data-curation commit; `tracking.json` may reference proposal IDs, and renumbering is no longer permitted.
- **After any data edit:** Run `python3 tools/validate_plan_data.py` to verify tree structure, IDs, counts, and cross-references.

## Rules

- New page sections = new `.astro` component in `src/components/`, composed into `src/pages/index.astro` or `src/layouts/Base.astro`.
- All tracker content changes happen in `src/data/` (the `plan/` tree and `tracking.json`), never in component markup.
- Run `npm run validate` (`python3 tools/validate_plan_data.py`) after every data edit under `src/data/`.
- Status colors/labels live in `src/lib/statuses.mjs` (`STATUSES`); add new statuses there and in `tools/validate_plan_data.py` (`VALID_STATUSES`) together.
