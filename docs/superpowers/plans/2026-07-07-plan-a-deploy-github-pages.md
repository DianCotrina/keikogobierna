# Plan A — Deploy to GitHub Pages + Social Metadata Implementation Plan

> **For agentic workers:** Read [EXECUTION-CONTEXT.md](EXECUTION-CONTEXT.md) first. REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** Publish the site at **https://diancotrina.github.io/keikogobierna/** via GitHub Actions on every push to `main`, with complete social/SEO metadata (og:url, og:image, canonical, sitemap, robots) and no dead UI (alertas form, footer links) on the live site.

**Architecture:** GitHub Pages *project site* ⇒ the app lives under the `/keikogobierna/` base path. Astro handles this via `site` + `base` config, but **every internal absolute link in our components is currently base-blind** (`/`, `/temas/{slug}/`, `/#tablero`…) and will 404 in production while still working locally — the single most dangerous pitfall of this plan. All internal URLs must flow through one helper. CI runs validate + tests + build, then deploys `dist/` with the official Pages actions. The og:image is a 1200×630 branded card produced in-house by screenshotting a purpose-built HTML file with headless Brave — same design system, no external tooling.

**User decisions already made:** GitHub Pages; platform URL (no custom domain yet — when one arrives, changing `site`/`base` + DNS is a small follow-up).

**Branch:** `deploy-pages` off `main` (after PR #3 — and Plan B if it ran first — are merged).

## Global Constraints

- Everything in EXECUTION-CONTEXT.md.
- `site: 'https://diancotrina.github.io'`, `base: '/keikogobierna'` — exact values.
- One URL helper, used EVERYWHERE an internal href/src is emitted. No raw `href="/..."` may remain in any `.astro` file (root-relative links bypass `base` and break in production). External URLs (fonts, placehold, GitHub) unaffected.
- Local behavior must not regress: `npm run dev`/`preview` serve under `/keikogobierna/` once `base` is set — all verification URLs change to `http://localhost:3000/keikogobierna/…` (update your habits; a bare `localhost:3000/` returning Astro's 404 is EXPECTED, not a bug).
- User-facing copy Spanish; workflow/CI files and identifiers English.
- CI must fail the deploy if validate, tests, or build fail. Node 26 in CI to match dev.
- Never `git push` to main from CI or locally; deploy happens only via the workflow on merge.

## File Structure

```
astro.config.mjs                 # + site, base
src/lib/url.mjs                  # NEW — withBase(path) helper
src/layouts/Base.astro           # all hrefs via helper; + canonical, og:url, og:image, twitter:card
src/components/TopicCard.astro   # href via helper
src/pages/index.astro            # internal hrefs via helper (donate/share untouched — uses location.href)
src/pages/temas/[slug].astro     # breadcrumb + prev/next via helper
src/pages/404.astro              # NEW — branded Spanish 404 (GH Pages serves 404.html)
public/robots.txt                # NEW
public/og-default.png            # NEW — generated 1200×630 card
scratch (not committed): og-card.html used to render the PNG
.github/workflows/deploy.yml     # NEW — validate + test + build + deploy-pages
package.json                     # + @astrojs/sitemap integration
docs/ARCHITECTURE.md, CLAUDE.md  # live URL, deploy section, base-path rule
```

### url.mjs contract

```js
// src/lib/url.mjs
const base = import.meta.env.BASE_URL.replace(/\/$/, ''); // '/keikogobierna'
/** Prefix an internal path ('/', '/temas/x/', '/#tablero') with the deploy base. */
export function withBase(path) {
  if (!path.startsWith('/')) throw new Error(`withBase expects a root-relative path, got: ${path}`);
  return `${base}${path === '/' ? '/' : path}`;
}
```

---

### Task 1: Base path + URL helper sweep

**Files:** `astro.config.mjs`, create `src/lib/url.mjs`, modify `Base.astro`, `TopicCard.astro`, `index.astro`, `[slug].astro`, add test to `tests/` (new `tests/url.test.mjs` is NOT possible — `import.meta.env` is Vite-only; instead verify via build greps below).

- [ ] **Step 1:** Add `site`/`base` to astro.config.mjs; create url.mjs.
- [ ] **Step 2:** Sweep every `.astro` file: `grep -rn 'href="/' src --include='*.astro'` and `grep -rn "href={\`/" src --include='*.astro'` — route each internal link through `withBase()` (nav, wordmark link, footer links, CTA buttons, TopicCard, breadcrumb, prev/next). Re-run the greps until only `withBase`-wrapped or external URLs remain.
- [ ] **Step 3:** `npm run build` → pages emit under `dist/` with links prefixed. Executable gate: `grep -rL 'href="/keikogobierna' dist/temas/educacion/index.html` — then stronger: `grep -o 'href="/[^k"][^"]*"' dist/**/*.html | sort -u` → EMPTY (no un-prefixed internal root link anywhere; anchors like `href="#..."` and external `https://` are fine and excluded by the pattern).
- [ ] **Step 4:** `npm run preview` (background, kill port first) → headless-Brave dump-dom `http://localhost:3000/keikogobierna/` and `/keikogobierna/temas/educacion/` → content renders; click-path check: every `href` found in the landing dump resolves to an existing `dist/` file (small shell loop). Kill server. `npm test` green.
- [ ] **Step 5:** Commit: `feat: configure GitHub Pages base path and route all internal links through withBase`.

### Task 2: SEO + social metadata

**Files:** `package.json` (+`@astrojs/sitemap`), `astro.config.mjs` (integration), `Base.astro`, `public/robots.txt`, `public/og-default.png`, create `src/pages/404.astro`.

- [ ] **Step 1:** Install `@astrojs/sitemap`, register in config. robots.txt:

```
User-agent: *
Allow: /
Sitemap: https://diancotrina.github.io/keikogobierna/sitemap-index.xml
```

- [ ] **Step 2:** Base.astro head additions (all derived, no hardcoded page URLs): `<link rel="canonical" href={new URL(Astro.url.pathname, Astro.site)} />`, `og:url` same value, `og:image` = `new URL(withBase('/og-default.png'), Astro.site)`, `og:image:width/height` 1200/630, `og:image:alt` Spanish ("keikogobierna — seguimiento del plan de gobierno 2026–2031"), `twitter:card` = `summary_large_image`.
- [ ] **Step 3:** Generate the og:image in-house: write a scratch `og-card.html` (1200×630, papel background with the grain, flag-red top band, display-font "keikogobierna" wordmark, headline "Lo prometido es deuda." with the pen-stroke underline, mono sub-line "Seguimiento del plan de gobierno 2026–2031 · 65 metas · 23 temas" — inline CSS copying tokens from global.css, Google Fonts link is allowed since Brave renders online). Screenshot at exactly `--window-size=1200,630` with headless Brave → `public/og-default.png`. VIEW the PNG; iterate until it looks like the brand (≥2 rounds if needed). Keep it under 300 KB (re-render or `sips -s formatOptions` if larger).
- [ ] **Step 4:** `src/pages/404.astro` on Base: Spanish copy — title "Página no encontrada — keikogobierna", stamp-style "404" treatment, line "Esta página no existe o fue movida.", button "Volver al tablero" → `withBase('/')`. GH Pages automatically serves `404.html` at the site root.
- [ ] **Step 5:** Build; verify `dist/sitemap-index.xml` exists and lists 24+ URLs with the full `https://diancotrina.github.io/keikogobierna/...` form; dist grep on a topic page for `canonical`, `og:url`, `og:image` absolute URLs; `dist/404.html` exists. `npm test` green.
- [ ] **Step 6:** Commit: `feat: add sitemap, robots, canonical/og metadata, og image, and 404 page`.

### Task 3: Honest live UI (no dead controls)

**Files:** `src/pages/index.astro` (alertas section), `Base.astro` (footer links).

- [ ] **Step 1:** Alertas section: the email `<form>` has no backend — replace it (keep the section's card design) with: line "Las alertas por correo estarán disponibles próximamente." styled as the mono note, plus two real actions: primary button "Seguir el proyecto en GitHub" → `https://github.com/DianCotrina/keikogobierna` and the existing share affordance remains in the donate widget. Remove the `<form>`/input entirely (an input that goes nowhere is dishonest UI).
- [ ] **Step 2:** Footer: "Fuentes" → `https://github.com/DianCotrina/keikogobierna/blob/main/docs/Plan-de-Gobierno-Reforzado_V2.pdf` (the actual source document); "Contacto" → `https://github.com/DianCotrina/keikogobierna/issues` (title attribute "Abrir un issue en GitHub"). "Metodología" stays `withBase('/#metodologia')`.
- [ ] **Step 3:** Build + preview + screenshot the alertas section and footer (desktop); VIEW: the section must still look designed, not amputated. `npm test` green.
- [ ] **Step 4:** Commit: `feat: replace dead alertas form and wire footer links for launch`.

### Task 4: CI/CD + go live

**Files:** create `.github/workflows/deploy.yml`; modify `docs/ARCHITECTURE.md`, `CLAUDE.md`.

- [ ] **Step 1:** Workflow:

```yaml
name: Deploy to GitHub Pages
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 26, cache: npm }
      - run: npm ci
      - run: python3 tools/validate_plan_data.py
      - run: npm test
      - run: npm run build
      - uses: actions/upload-pages-artifact@v3
        with: { path: dist }
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2:** Enable Pages for Actions-based deploys: `gh api -X POST repos/DianCotrina/keikogobierna/pages -f build_type=workflow` (if 409 already-exists, `gh api -X PUT … -f build_type=workflow`).
- [ ] **Step 3:** Docs: ARCHITECTURE.md gains a Deployment section (live URL, workflow file, base-path rule: "all internal links MUST go through `withBase()` — a raw `/…` href works locally under preview but 404s in production"); CLAUDE.md Local Server section notes preview URLs live under `/keikogobierna/`.
- [ ] **Step 4:** Commit: `feat: add GitHub Pages deploy workflow and docs`. Push branch, open PR `Deploy: GitHub Pages with full social metadata`. Do not merge yourself.
- [ ] **Step 5 (post-merge verification — run after the user merges):** watch `gh run watch` for the deploy; then against the LIVE site: `curl -s -o /dev/null -w "%{http_code}" https://diancotrina.github.io/keikogobierna/` → 200; same for `/temas/educacion/` and `/temas/orden-ciudadano/`; curl the landing HTML and confirm og:image absolute URL + canonical; fetch `sitemap-index.xml` → 200; headless-Brave screenshot the live landing and VIEW it (fonts, grain, stamps render over HTTPS). Report the live URL + evidence to the user.

### Final

- [ ] Whole-branch review before the PR (most capable model): the base-path sweep is the risk center — reviewer must independently grep dist for un-prefixed internal links and click-path-verify hrefs↔files; visual gates on og-default.png, alertas section, 404 page.
