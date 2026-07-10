# Hero banner — Palacio de Gobierno photo

**Date:** 2026-07-10
**Status:** Approved by Diego (design conversation; simplified from an earlier illustrated-collage idea to a single provided photo)

## Problem

The Resumen (hero) section is pure typography + tracker card on flat papel. Diego wants the Palacio de Gobierno photo (`assets/palace_peru.jpg`, 1800×1200 night shot) as an elegant banner for the section.

## Design

**Placement:** background layer behind the whole hero (decided earlier in the collage exploration; carries over). The headline, body, buttons, and TrackerCard sit above it, unaffected.

**Component:** `src/components/HeroBanner.astro` — flat, Tailwind-only:

- `<Image>` from `astro:assets` (build-time optimization: the 334 KB source becomes a responsive WebP; decorative `alt=""`), `object-cover`, positioned to favor the façade (`object-position: center 30%`).
- Ink treatment: `grayscale` + slight `contrast` filter, `mix-blend-multiply`, opacity ~0.16 — the night photo prints into the papel like an engraving instead of sitting on top like a stock photo.
- Readability overlays: a left→right gradient (solid papel → transparent) keeping the headline column clean, and a bottom fade to papel so the section melts into the page. Top stays light (header border provides the edge).
- Mobile (< sm): opacity drops to ~0.10 — text over texture at narrow widths stays effortless.
- `aria-hidden="true"`, `pointer-events-none`, no animation (the hero's existing load-in stays the only motion).

**Integration:** the hero `<section>` in `src/pages/index.astro` gains `relative overflow-hidden`; `<HeroBanner />` is its first child; the two grid columns get `relative` to stack above.

## Out of scope

- The censored-newspapers collage (dropped by Diego in favor of the single photo).
- Banners on other pages.

## Verification

- `npm run build` (image pipeline runs at build).
- Screenshots desktop 1280px and mobile 390px: palace visible but subordinate; headline/tracker contrast unchanged; no layout shift.
