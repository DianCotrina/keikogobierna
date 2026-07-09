# IndexRail Floating Tree Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Floating índice companion — desktop margin rail + mobile chip/dialog — with scrollspy, on the 100-days and topic pages.

**Architecture:** One folder-module component (`src/components/IndexRail/`) consuming the `indexEntries` arrays both pages already compute. Visibility driven by an IntersectionObserver on the inline `PlanIndex` (sentinel `id="indice"`); scrollspy by a second observer over the target sections. Tree markup rendered twice (rail + dialog), rows keyed by `data-target` so both stay in sync.

**Tech Stack:** Astro 5, plain prefixed CSS (folder-module convention), TypeScript component script, native `<dialog>`.

**Spec:** `docs/superpowers/specs/2026-07-09-index-rail-design.md`

## Global Constraints

- All user-facing text Spanish (Peru); code/comments/commits English.
- Colors from the site palette only (hex in plain CSS, like `donate.css`): tinta `#141417`, tintasuave `#46464D`, tintafina `#8E8E96`, rojo `#C8102E`, verde `#1F7A4D`, papel `#F5F3EE`.
- Animate only `transform`/`opacity`; respect `prefers-reduced-motion`; hover/focus-visible/active on every interactive element.
- Work on branch `indice-cumplidas` (extends PR #8).
- Commits end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: IndexRail component + page integration

**Files:**
- Create: `src/components/IndexRail/IndexRail.astro`
- Create: `src/components/IndexRail/index-rail.css`
- Create: `src/components/IndexRail/index-rail.ts`
- Modify: `src/components/PlanIndex.astro` (nav gains `id="indice"`)
- Modify: `src/pages/primeros-100-dias.astro`, `src/pages/temas/[slug].astro` (import + render `<IndexRail entries={indexEntries} />` before `</main>`)

**Interfaces:**
- Consumes: `indexEntries` (`{ href, label, count?, children? }[]`) already computed by both pages; inline `PlanIndex` as visibility sentinel.
- Produces: `<IndexRail entries />`; CSS classes `.index-rail`, `.index-rail-chip`, `.index-rail-dialog`, rows `.rail-link[data-target]` with `.is-current`.

- [ ] **Step 1: Write the three files** (markup/CSS/TS as designed in the spec — tree rendered twice with `data-target` rows; IO visibility toggle `is-active` via sentinel `bottom < 0`; scrollspy IO with `rootMargin: '0% 0px -65% 0px'` tracking an intersecting-ids set, current = last intersecting id in document order, child current also highlights parent via a child→parent map built from the rail DOM; chip toggles dialog with Donate-pattern close behaviors; links inside dialog close it on click.)
- [ ] **Step 2: Add `id="indice"` to PlanIndex's `<nav>`** (single sentinel per page — both pages render exactly one inline PlanIndex).
- [ ] **Step 3: Render `<IndexRail entries={indexEntries} />`** on both pages before `</main>`.
- [ ] **Step 4:** `npm run build` passes; grep dist HTML for `index-rail` markup and the bundled script tag. Also verify the Donate pattern precedent: confirm dist pages include bundled module scripts (type="module") for component scripts.
- [ ] **Step 5: Commit** `feat: add IndexRail floating tree navigation`

### Task 2: Functional + visual verification (headless harness)

**Files:**
- Temporary: `public/_rail_test.html` (deleted before commit)

- [ ] **Step 1:** Desktop 1440×900 plain screenshot of `/primeros-100-dias/` top: rail and chip both hidden.
- [ ] **Step 2:** Harness: iframe page, force `is-active` on rail, simulate scrollspy by dispatching — instead verify by adding `is-current` via the real code path: scroll can't run headless, so call the exported behavior indirectly: set classes via `contentDocument` (`rail.classList.add('is-active')`; `link.classList.add('is-current')` on one parent+child) and screenshot 1440px: rail visible in left margin, highlight correct, content unobstructed.
- [ ] **Step 3:** Mobile 390px via harness: force chip `is-active`, screenshot chip bottom-left (Donate widget bottom-right); then `chip.click()` (real event path — verifies the TS actually wired) and screenshot the open dialog panel with tree.
- [ ] **Step 4:** Confirm dialog closes via backdrop `dialog.click()` and that clicking a tree link closes it (assert `dialog.open === false` reported into harness DOM text).
- [ ] **Step 5:** Delete harness, `npm test && npm run validate && npm run build` all green, `git status` clean except intended files.
- [ ] **Step 6: Commit** any fixes; push branch to update PR #8.
