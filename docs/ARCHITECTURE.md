# Architecture

Module-based landing page. No build step, no framework: native ES modules + Tailwind CDN, served by `node serve.mjs` at http://localhost:3000.

## Module map

| Path | Responsibility |
|---|---|
| `index.html` | Static shell: head, Tailwind config, custom CSS, static copy (header, hero text, metodología, alertas, footer), mount points |
| `src/main.js` | Entry point: fetches `plan.json`, calls renderers, inits behaviors |
| `src/lib/dom.js` | `esc()`, `ESTADOS` map, `stamp()` chip template |
| `src/modules/tracker-card.js` | Hero "expediente" card (`#tracker-card`) |
| `src/modules/topics.js` | Policy-area grid (`#topics-grid`) |
| `src/modules/updates.js` | Últimas actualizaciones list (`#updates-list`) |
| `src/modules/reveal.js` | Scroll-reveal behavior for `.reveal` elements |
| `src/modules/donate.js` | Donate pill share button |
| `src/data/plan.json` | Single source of truth for all tracker data (sample data for now) |
| `tools/validate_plan_data.py` | WAT tool: validates plan.json before publishing |

## Data contract

`plan.json`: `meta` (dates, period, sources) · `summary` (overall_progress, total, statuses counts — counts must sum to total) · `highlights` (hero card promise rows) · `topics` (id, name, commitments, progress) · `updates` (date, text, status).

Estados: `cumplida`→verde · `en_progreso`→ambar · `sin_avance`→plomo · `incumplida`→rojo. Add new estados in `src/lib/dom.js` (ESTADOS) and `tools/validate_plan_data.py` (VALID_ESTADOS) together.

## Plan data

The plan data layer is immutable (derived from the PDF) except for the tracking state, which is living. This separation allows reliable data restoration while enabling real-time progress updates.

**Tree structure:**
```
src/data/plan/
├── index.json              # Registry: pillars (3) + topics (23 topics, 635 proposals, 67 first-100-days actions, 65 goals)
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
- **Proposals + first-100-days actions:** Auto-extracted from PDF by `tools/extract_plan_pdf.py` (deterministic, never overwrites goals).
- **Goals (metas al 2031):** Curated by hand in `src/data/plan/goals/goals-2031.json`; the PDF tables are not machine-parseable, so goals are never auto-regenerated.
- **Tracking state:** Lives in `src/data/tracking.json`; edit freely (log your progress), then validate.
- **After any data edit:** Run `python3 tools/validate_plan_data.py` to verify tree structure, IDs, counts, and cross-references.

## Rules

- New page sections = new module in `src/modules/` exporting `render<Name>(el, data)` or `init<Name>()`, wired in `main.js`.
- All tracker content changes happen in `plan.json`, never in module markup.
- Run `python3 tools/validate_plan_data.py` after every `plan.json` edit.
- When SEO/prerendering becomes a requirement, migrate shell+modules to a static builder (e.g., Astro); the data contract and module boundaries are designed to survive that move.
