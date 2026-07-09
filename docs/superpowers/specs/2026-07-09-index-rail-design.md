# IndexRail — floating tree navigation for long pages

**Date:** 2026-07-09
**Status:** Approved by Diego (design conversation, 2026-07-09)
**Extends:** 2026-07-09-indice-cumplidas-design.md (PlanIndex inline índice)

## Problem

The inline índice block solves the landing overview, but once a reader is deep in a long scroll (100-days page ≈ 6,000px; topic pages similar) jumping to another section requires scrolling all the way back up. The índice needs an in-flight companion.

## Design

### Component: `IndexRail` (folder module)

`src/components/IndexRail/` — needs its own CSS and script, so per the component-folder convention:

- `IndexRail.astro` — markup
- `index-rail.css` — imported in frontmatter (global; every selector prefixed `.index-rail*` / `.rail-*`)
- `index-rail.ts` — referenced via `<script src="./index-rail.ts">`

**Props:** the same `entries` shape as `PlanIndex` — `{ href, label, count?, children?: { href, label }[] }[]`. Pages pass the `indexEntries` array they already compute. No new data functions.

### Desktop behavior (≥1280px)

- Slim fixed rail (~12rem) in the left margin: content column is 56rem centered, so at ≥1280px the margin fits it (`left: calc((100vw - 56rem) / 2 - 14rem)` clamped ≥ 1rem).
- Hidden at page top. Appears once the user scrolls past the inline índice block; disappears when scrolling back above it.
  - Trigger: IntersectionObserver watching the inline `PlanIndex` `<nav>`, which gains `id="indice"`. Rail is active when the índice's bottom is above the viewport (`boundingClientRect.bottom < 0`).
- Show/hide animates `transform` + `opacity` only; hidden state also sets `visibility: hidden` and `pointer-events: none`.
- Compact tree: mono eyebrow «Índice», numbered parent rows, indented children. No dotted leaders or counts (the inline índice carries those).
- If the rail tree is taller than the viewport, the rail scrolls internally (`max-height` + `overflow-y: auto`).

### Mobile/tablet behavior (<1280px)

- Floating «Índice» chip fixed bottom-left (mirrors the Donate widget bottom-right), same appear/disappear trigger as the rail.
- Tapping opens a native `<dialog>`: the same tree as a panel sliding in from the left edge (Donate dialog interaction pattern — close button, backdrop click, Esc).
- Choosing a link closes the dialog, then the browser jumps to the anchor.
- Chip has `aria-expanded`; dialog has `aria-labelledby` its «Índice» heading.

### Scrollspy (both form factors)

- IntersectionObserver over every target section (`entries[].href` and children hrefs → element ids) with `rootMargin: '0% 0px -65% 0px'` — a section is "current" while its box intersects the top ~35% of the viewport; the most recent match wins.
- Current row: verde accent + 2px left ink bar. When a child is current, its parent is highlighted too.
- Applies to both the desktop rail and the mobile panel. The tree markup is rendered **twice** (once in the rail, once in the dialog) — simplest responsive strategy. Tree rows carry `data-target="<section-id>"` attributes (no ids, so duplication is safe); the scrollspy updates every `[data-target="..."]` match, keeping both trees in sync.

### Accessibility & motion

- Rail: `<nav aria-label="Índice flotante">` (the inline índice already uses "Índice de la página" — labels must differ).
- All links/buttons: hover, focus-visible, active states.
- `prefers-reduced-motion: reduce`: no fade/slide transitions — instant show/hide, dialog without slide animation.

### Integration

One line per page, after the existing content (sibling of `<main>`'s sections):

- `src/pages/primeros-100-dias.astro`: `<IndexRail entries={indexEntries} />`
- `src/pages/temas/[slug].astro`: `<IndexRail entries={indexEntries} />`

The inline `PlanIndex` stays (landing overview); it additionally gets `id="indice"` (set on the page wrapper div or passed through) as the rail's visibility sentinel. Rendering with 0 or 1 entries is not special-cased — pages always have ≥3 entries.

## Out of scope

- Home page (short enough; has its own section nav needs).
- Persisting open/closed state.
- Smooth-scroll behavior changes (browser default stands).

## Testing

- No new data-layer functions → no new unit tests.
- `npm run build` passes.
- Headless-Brave verification (using the iframe harness with forced classes, since headless cannot scroll):
  - Rail hidden at page top (desktop 1440px).
  - Rail visible + correct current-section highlight when forced active mid-page.
  - Mobile 390px: chip visible when forced active; dialog open with tree panel.
  - Donate widget unobstructed bottom-right in all cases.
