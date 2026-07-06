# Architecture

Module-based landing page. No build step, no framework: native ES modules + Tailwind CDN, served by `node serve.mjs` at http://localhost:3000.

## Module map

| Path | Responsibility |
|---|---|
| `index.html` | Static shell: head, Tailwind config, custom CSS, static copy (header, hero text, metodología, alertas, footer), mount points |
| `src/main.js` | Entry point: fetches `plan.json`, calls renderers, inits behaviors |
| `src/lib/dom.js` | `esc()`, `ESTADOS` map, `stamp()` chip template |
| `src/modules/tracker-card.js` | Hero "expediente" card (`#tracker-card`) |
| `src/modules/ejes.js` | Policy-area grid (`#ejes-grid`) |
| `src/modules/registro.js` | Últimas actualizaciones list (`#registro-list`) |
| `src/modules/reveal.js` | Scroll-reveal behavior for `.reveal` elements |
| `src/modules/donate.js` | Donate pill share button |
| `src/data/plan.json` | Single source of truth for all tracker data (sample data for now) |
| `tools/validate_plan_data.py` | WAT tool: validates plan.json before publishing |

## Data contract

`plan.json`: `meta` (dates, periodo, fuentes) · `resumen` (avance_general, total, estados counts — counts must sum to total) · `destacados` (hero card promise rows) · `ejes` (id, nombre, compromisos, avance) · `actualizaciones` (fecha, texto, estado).

Estados: `cumplida`→verde · `en_progreso`→ambar · `sin_avance`→plomo · `incumplida`→rojo. Add new estados in `src/lib/dom.js` (ESTADOS) and `tools/validate_plan_data.py` (VALID_ESTADOS) together.

## Rules

- New page sections = new module in `src/modules/` exporting `render<Name>(el, data)` or `init<Name>()`, wired in `main.js`.
- All tracker content changes happen in `plan.json`, never in module markup.
- Run `python3 tools/validate_plan_data.py` after every `plan.json` edit.
- When SEO/prerendering becomes a requirement, migrate shell+modules to a static builder (e.g., Astro); the data contract and module boundaries are designed to survive that move.
