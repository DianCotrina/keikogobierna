# Astro Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the site from a no-build ES-module landing page to a statically generated Astro site: the landing rewired from sample data to the real plan tree, plus 23 topic detail pages at `/temas/{slug}/` with per-page Spanish metadata — so every page is real HTML with working social previews.

**Architecture:** Astro 5 static output (no adapter, no SSR). All data is read at build time from the existing tree (`src/data/plan/**`, `src/data/tracking.json`) by a plain-JS data library (`src/lib/plan.mjs`, unit-tested with `node --test`). The established "tinta" design system (black-ink newspaper on paper, pen strokes, rubber stamps, Peru-red accents) is ported verbatim into global CSS + components — this is a re-platform, not a redesign; the landing's only content change is real data (3 pillars / 23 topics / 65 goals instead of 6 sample ejes). Client JS stays tiny: scroll-reveal and the donate/share widget.

**Tech Stack:** Astro latest stable (^7 as of 2026-07; originally drafted as ^5 — superseded for the npm-audit high-severity advisory fixed in 7.0.6), Tailwind CSS v4 via `@tailwindcss/vite`, Node ≥ 20, `node --test` for the data lib. Deployment intentionally out of scope (decided later) — everything must work with `npm run build` + `npm run preview` locally.

## Global Constraints

- Language policy: identifiers/comments/commits English; ALL user-facing strings Spanish (Peru) — page titles, meta descriptions, headings, buttons, empty states, alt text. URL paths user-facing → Spanish (`/temas/orden-ciudadano/`).
- Zero design regression on ported elements: same palette (`papel #F5F3EE`, `tinta #141417`, `tintasuave #46464D`, `tintafina #8E8E96`, `rojo #C8102E`, `verde #1F7A4D`, `ambar #A35E00`, `plomo #6B6F7B`), same fonts (Archivo Black / Archivo / Source Serif 4 / IBM Plex Mono via Google Fonts), same signature elements (paper grain, pen-stroke underline + progress bar, rubber-stamp status chips, layered ink-tinted shadows), same interaction rules (transform/opacity only, spring easing, hover/focus-visible/active on every interactive element, `prefers-reduced-motion` respected). The authoritative source for all of this is the current `index.html` (its `tailwind.config`, `<style>` block, and markup) and `src/modules/*.js` template literals AT COMMIT `ff4038b` — port from them verbatim, adapting only Tailwind-config syntax to v4 `@theme`.
- Status vocabulary: `fulfilled | in_progress | no_progress | unfulfilled`; Spanish labels only in the STATUSES map (Cumplida / En progreso / Sin avance / Incumplida). Colors: verde / ambar / plomo / rojo.
- Two-layer rule: any progress % (headline or per-topic) counts ONLY goals (metas al 2031); proposals are listed as content, their tracking states shown when present but never in the %.
- Honest data: tracking is all `no_progress` today → the landing shows 0% and an "Aún no hay actualizaciones registradas" empty state for the updates section. Never fabricate progress or events.
- Data files are read-only for this plan: do NOT modify anything under `src/data/plan/`, `src/data/tracking.json`, or the two Python tools (except the stated validator legacy-section removal in Task 6).
- Astro dev/preview server port: 3000 (`server: { port: 3000 }` in astro.config) so existing docs/screenshot workflow stay true. Never run two instances.
- Headless screenshots: Brave (`/Applications/Brave Browser.app/Contents/MacOS/Brave Browser`), min window width 500px (use iframe trick for mobile).
- Work on branch `astro-migration` from `main`. Stage only files each task touches; commit trailer: Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
- `package-lock.json` is committed. `node_modules/`, `dist/`, `.astro/` must be git-ignored (existing .gitignore covers node_modules and dist; add `.astro/` if missing).

## File Structure

```
astro.config.mjs               # static output, port 3000, @tailwindcss/vite plugin
package.json                   # astro, @tailwindcss/vite, tailwindcss; scripts: dev/build/preview/test/validate
tsconfig.json                  # astro/tsconfigs/base (scaffold default)
src/
├── styles/global.css          # Tailwind v4 @theme tokens + ported custom CSS (grain, stamps, pen, reveal, buttons)
├── lib/
│   ├── plan.mjs               # build-time data access + aggregates (pure functions, no Astro imports)
│   └── statuses.mjs           # STATUSES map + stampClass helper (port of old dom.js, minus esc — Astro escapes)
├── layouts/
│   └── Base.astro             # <head> (title/description/OG/lang es-PE, fonts, global.css), header, footer, donate widget, reveal script
├── components/
│   ├── Stamp.astro            # rubber-stamp status chip
│   ├── PenProgress.astro      # pen-stroke progress bar (dynamic width)
│   ├── TrackerCard.astro      # hero expediente card (real aggregates)
│   ├── TopicCard.astro        # one topic card in the landing grid
│   ├── GoalRow.astro          # goal + indicator + stamp row (topic pages)
│   └── Donate.astro           # donate pill + share button (with its client script)
├── pages/
│   ├── index.astro            # landing
│   └── temas/[slug].astro     # 23 static topic pages (getStaticPaths)
tests/
└── plan.test.mjs              # node --test suite for src/lib/plan.mjs
```

**Deleted in Task 6 (legacy layer):** `index.html`, `serve.mjs`, `src/main.js`, `src/lib/dom.js`, `src/modules/` (all 5), `src/data/plan.json`.

### Shared interfaces (all tasks)

`src/lib/plan.mjs` exports (pure, synchronous, read JSON with `fs.readFileSync` + `JSON.parse` relative to repo root via `new URL('../data/…', import.meta.url)`):

```js
loadPlan()      // → { plan, pillars, topics } (index.json contents)
loadTopics()    // → Map<topicId, topicFile>  (23 files from src/data/plan/topics/)
loadGoals()     // → goals array (goals-2031.json)
loadTracking()  // → tracking.json contents
statusOf(id, tracking)            // → item status; absent id ⇒ 'no_progress'
goalStats(goals, tracking, topicId?)  // → { total, byStatus: {fulfilled, in_progress, no_progress, unfulfilled}, progressPct }
                                      //   progressPct = Math.round(100 * fulfilled / total); topicId filters to one topic
topicSummaries(plan, goals, tracking) // → [{ id, slug, name, pillar, pillarName, proposals, first_100_days, goals, progressPct }] in index order
updatesLog(tracking)                  // → tracking.log sorted by date desc (may be empty)
```

`src/lib/statuses.mjs`:

```js
export const STATUSES = {
  fulfilled:   { label: 'Cumplida',    color: 'verde' },
  in_progress: { label: 'En progreso', color: 'ambar' },
  no_progress: { label: 'Sin avance',  color: 'plomo' },
  unfulfilled: { label: 'Incumplida',  color: 'rojo' },
};
export function statusMeta(status) {
  return STATUSES[status] ?? { label: String(status), color: 'plomo' };
}
```

`Base.astro` props: `{ title: string, description: string, activeNav?: string }` — renders full head (`<html lang="es-PE">`, `<title>`, meta description, `og:title`, `og:description`, `og:type=website`, `og:locale=es_PE`), Google Fonts links (same families as current index.html), header (wordmark + nav: Tablero, Temas, Metodología, Actualizaciones — hrefs `/#tablero`, `/#temas`, `/#metodologia`, `/#actualizaciones`), red flag band, footer (independence disclaimer — remove the old "datos de ejemplo" line: data is now real; ADD instead "Datos extraídos del plan de gobierno oficial. El seguimiento se actualiza con evidencia pública."), donate widget, and the reveal `<script>` (IntersectionObserver, ported from the old reveal.js, inline `<script>` in the layout).

---

### Task 1: Scaffold — Astro + Tailwind v4 + design tokens

**Files:**
- Create: `package.json`, `package-lock.json`, `astro.config.mjs`, `tsconfig.json`, `src/styles/global.css`
- Modify: `.gitignore` (ensure `.astro/` ignored)

**Steps:**

- [ ] **Step 1:** `npm create astro@latest . -- --template minimal --no-install --no-git --typescript strict` may refuse a non-empty dir — if so, init manually: `npm init -y` then `npm install astro @tailwindcss/vite tailwindcss`. package.json scripts: `"dev": "astro dev"`, `"build": "astro build"`, `"preview": "astro preview"`, `"test": "node --test tests/"`, `"validate": "python3 tools/validate_plan_data.py"`. Delete any scaffold sample pages EXCEPT keep the existing repo files untouched (index.html etc. remain until Task 6 — Astro ignores them since pages live in src/pages/).
- [ ] **Step 2:** `astro.config.mjs`:

```js
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  output: 'static',
  server: { port: 3000 },
  vite: { plugins: [tailwindcss()] },
});
```

- [ ] **Step 3:** `src/styles/global.css` — `@import "tailwindcss";` then a `@theme` block defining the palette (`--color-papel: #F5F3EE; --color-carton: #ECE9E1; --color-tinta: #141417; --color-tintasuave: #46464D; --color-tintafina: #8E8E96; --color-rojo: #C8102E; --color-verde: #1F7A4D; --color-ambar: #A35E00; --color-plomo: #6B6F7B;`), font families (`--font-display: "Archivo Black", Archivo, sans-serif; --font-sans: Archivo, sans-serif; --font-serif: "Source Serif 4", Georgia, serif; --font-mono: "IBM Plex Mono", ui-monospace, monospace;`), and shadows (`--shadow-card`, `--shadow-lift`, `--shadow-chip` — copy exact values from index.html's tailwind.config at ff4038b). Then port the ENTIRE current `<style>` block from index.html verbatim (ease-spring var, body background radials, `.grain::before`, `.pen-stroke`, `.stamp`, `.reveal`, `.hero-in`+delays, interactive states incl. `.btn-primary/.btn-ghost/.nav-link/.card-hover/.donate-icon`, reduced-motion block).
- [ ] **Step 4:** Temporary smoke page `src/pages/index.astro` (will be replaced in Task 4) that imports global.css and renders `<h1 class="font-display text-tinta">keikogobierna</h1>` on papel background.
- [ ] **Step 5:** Verify: `npm run build` exits 0; `dist/index.html` contains the h1; grep built CSS for `.stamp` and `#141417` (tokens + custom CSS made it through). `git status` shows no junk (node_modules/dist/.astro ignored).
- [ ] **Step 6:** Commit: `feat: scaffold Astro 5 with Tailwind v4 and ported design tokens` (stage package.json, package-lock.json, astro.config.mjs, tsconfig.json, src/styles/global.css, src/pages/index.astro, .gitignore).

---

### Task 2: Data library + tests

**Files:**
- Create: `src/lib/plan.mjs`, `src/lib/statuses.mjs`, `tests/plan.test.mjs`

**Steps:**

- [ ] **Step 1:** Implement `src/lib/statuses.mjs` exactly per Shared interfaces.
- [ ] **Step 2:** Implement `src/lib/plan.mjs` per Shared interfaces. Read files once per call (no caching needed at build scale). `topicSummaries` joins index topics with pillar names and per-topic `goalStats(...).progressPct`.
- [ ] **Step 3:** `tests/plan.test.mjs` with `node:test` + `node:assert/strict`, asserting against the REAL committed data (it's deterministic fixture data): loadPlan → 3 pillars/23 topics; loadTopics → 23 entries, t1-1 has 43 proposals across its groups; loadGoals → 65; statusOf('t1-1.M01', loadTracking()) === 'no_progress'; statusOf('nonexistent', …) === 'no_progress'; goalStats overall → { total: 65, byStatus.no_progress: 65, progressPct: 0 }; goalStats for t1-2 → total 1; topicSummaries → 23 rows, first is t1-1 with pillarName 'Orden'; updatesLog → []; statusMeta('fulfilled').label === 'Cumplida'; statusMeta('bogus').color === 'plomo'.
- [ ] **Step 4:** Run `npm test` → all pass, pristine output.
- [ ] **Step 5:** Commit: `feat: add build-time plan data library with tests`.

---

### Task 3: Layout + shared components

**Files:**
- Create: `src/layouts/Base.astro`, `src/components/Stamp.astro`, `src/components/PenProgress.astro`, `src/components/Donate.astro`

**Steps:**

- [ ] **Step 1:** `Stamp.astro` — props `{ status }`; uses `statusMeta`; renders the exact `.stamp` markup from old `dom.js` (`<span class="stamp text-{color} shrink-0">{label}</span>`).
- [ ] **Step 2:** `PenProgress.astro` — props `{ pct, label }`; the pen-stroke SVG bar from old tracker-card.js (track path + filled path with `filled = Math.round(4 + 392 * pct/100)`), `role="img"` `aria-label={label}` (Spanish label passed by caller).
- [ ] **Step 3:** `Donate.astro` — port the donate widget markup verbatim from index.html (heart, "Apóyame con un", Yape icon, PayPal SVG, share button, toast) plus its share `<script>` (from old donate.js, adapted to plain inline module script).
- [ ] **Step 4:** `Base.astro` per Shared interfaces (head/meta/OG, fonts, flag band, header/nav, `<slot />`, footer with the new disclaimer line, Donate, reveal script). Nav hrefs use `/#…` so they work from topic pages too.
- [ ] **Step 5:** Point the smoke index.astro at Base (`<Base title="keikogobierna — Seguimiento del plan de gobierno" description="…">`) to render header/footer; `npm run build` → 0; dump-dom the preview (`npm run preview` in background, then headless Brave) → header nav, footer disclaimer, donate widget present; `<html lang="es-PE">`; `og:title` present. Kill preview after.
- [ ] **Step 6:** Commit: `feat: add base layout and shared components`.

---

### Task 4: Landing page with real data

**Files:**
- Create: `src/components/TrackerCard.astro`, `src/components/TopicCard.astro`
- Modify: `src/pages/index.astro` (replace smoke content with the full landing)

Landing structure (port section markup from index.html at ff4038b, adapting only the data-driven parts):
- Hero: unchanged copy ("Lo prometido es deuda." + pen underline, eyebrow, sub, CTAs — "Ver el tablero" → `#tablero`, "Cómo verificamos" → `#metodologia`).
- `TrackerCard` (id="tablero"): real aggregates — `goalStats` overall (0% today), "65 metas al 2031 · 635 propuestas rastreadas" (real counts from data, not hardcoded), distribution row from byStatus, and as list rows the first goal of each pillar (t1-1.M01, t2-1.M01, t3-1.M01) with `Stamp`; sources line from `plan.plan` meta ("Fuente: Plan de Gobierno oficial 2026–2031").
- Topics section (id="temas", replaces old "ejes" section; heading "El plan, tema por tema"): for each of the 3 pillars, a pillar heading row (mono eyebrow "PILAR 1 · ORDEN" style) followed by its topics as `TopicCard`s in the same 3-col grid — card shows name, `{proposals} propuestas`, thin progress bar (progressPct), `% de avance`, and links to `/temas/{slug}/`.
- Metodología: unchanged copy, updated step 1 wording already true ("Extraemos cada compromiso…").
- Actualizaciones (id="actualizaciones"): `updatesLog` is empty → render the honest empty state inside the same card frame: mono date-less row "Aún no hay actualizaciones registradas. El seguimiento comienza con el gobierno en funciones." Keep "Ver todo el registro" button OUT until a registry page exists (remove it).
- Alertas CTA + footer: unchanged (footer disclaimer per Base).

**Steps:**

- [ ] **Step 1:** Build TrackerCard + TopicCard + index.astro per above, data via plan.mjs at build time.
- [ ] **Step 2:** `npm run build` → 0. Assert real numbers in dist/index.html: grep for `65` near "metas", `635`, "Orden ciudadano", "Peruanos en el extranjero (PEX)" (all 23 cards), `href="/temas/educacion/"`, the empty-state sentence.
- [ ] **Step 3:** Visual verification: `npm run preview` (background); full-page desktop screenshot (1440×4800) + mobile (iframe trick, 390px); compare against the pre-migration look (scratchpad `final-modular.png` or a fresh capture of ff4038b) — same visual system; new content (pillar groupings, 23 cards) must look intentional: consistent spacing, cards aligned, stamps rendering. Fix and re-screenshot until clean.
- [ ] **Step 4:** Commit: `feat: rebuild landing on Astro with real plan data`.

---

### Task 5: Topic detail pages

**Files:**
- Create: `src/pages/temas/[slug].astro`, `src/components/GoalRow.astro`

Page design (consistent with the expediente language):
- `getStaticPaths` from `topicSummaries` → 23 pages. Title: `{name} — keikogobierna`; description (Spanish, dynamic): `Seguimiento del tema {name} del plan de gobierno 2026–2031: {goals} metas, {proposals} propuestas verificables.`
- Masthead: breadcrumb (`← Volver al tablero` → `/`), mono eyebrow `PILAR {n} · {pillarName} · TEMA {doc_section}`, display-font topic name with pen-stroke underline, `PenProgress` with `{progressPct}% de avance` + `{goals} metas al 2031`.
- Section "Metas al 2031": `GoalRow` per goal — text (serif), indicator (mono, "Indicador: …"), `Stamp` of its tracked status.
- Section "Propuestas" ({proposals} total): each group as a subheading (`title`, or "Generales" when null) with its proposals as ledger rows (mono id badge `P01` + text); if a proposal has a tracked status in tracking.json, show its stamp, otherwise no stamp (avoid 635 gray stamps of noise).
- Section "Primeros 100 días": the C-items as a compact checklist card.
- Footer nav: prev/next topic links in index order ("← {prev}" / "{next} →").

**Steps:**

- [ ] **Step 1:** Implement GoalRow + [slug].astro per above.
- [ ] **Step 2:** `npm run build` → 0 and exactly 23 files `dist/temas/*/index.html`. Grep checks on `dist/temas/orden-ciudadano/index.html`: og:title contains "Orden ciudadano", 43 `P\d\d` badges, 3 goal rows, "Primeros 100 días" section with 4 items; on `dist/temas/pensiones/index.html`: 21 proposals across its groups.
- [ ] **Step 3:** Visual verification via preview: desktop + mobile screenshots of `/temas/orden-ciudadano/` and `/temas/programas-sociales/` (the 7-group topic) — typography hierarchy, group headings, stamps, spacing all coherent; fix and re-shoot until clean.
- [ ] **Step 4:** Commit: `feat: add 23 topic detail pages with goals and proposals`.

---

### Task 6: Legacy removal + docs

**Files:**
- Delete: `index.html`, `serve.mjs`, `src/main.js`, `src/lib/dom.js`, `src/modules/` (5 files), `src/data/plan.json`
- Modify: `tools/validate_plan_data.py` (remove the legacy plan.json section: `validate_legacy` and its call + the legacy part of the OK line; new-tree validation untouched), `docs/ARCHITECTURE.md` (rewrite: Astro structure, module map → components/layouts/lib table, commands, data flow build-time diagram in prose; Plan data section stays), `CLAUDE.md` (commands: `npm install`, `npm run dev` (port 3000), `npm run build`, `npm run preview`, `npm test`, `npm run validate`, single test: `node --test tests/plan.test.mjs`; Output Defaults: pages/components in Astro, frontend-design skill rule unchanged; Local Server section: `npm run dev` replaces serve.mjs)

**Steps:**

- [ ] **Step 1:** Delete legacy files (`git rm`), update validator, run `npm run validate` → OK line now new-tree-only; `npm run build` + `npm test` still green (proves nothing imported the deleted files).
- [ ] **Step 2:** Update both docs per above.
- [ ] **Step 3:** Full sweep: `grep -rn "serve.mjs\|plan.json\|renderTopics\|dom.js\|main.js" src docs CLAUDE.md --include="*.astro" --include="*.mjs" --include="*.md"` → no stale references (the plan-data docs' historical mentions in docs/superpowers/plans/ are fine — scope the fix to ARCHITECTURE.md/CLAUDE.md).
- [ ] **Step 4:** Commit: `refactor: remove legacy no-build layer and update docs for Astro`.
