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

## Rules

- New page sections = new module in `src/modules/` exporting `render<Name>(el, data)` or `init<Name>()`, wired in `main.js`.
- All tracker content changes happen in `plan.json`, never in module markup.
- Run `python3 tools/validate_plan_data.py` after every `plan.json` edit.
- When SEO/prerendering becomes a requirement, migrate shell+modules to a static builder (e.g., Astro); the data contract and module boundaries are designed to survive that move.
