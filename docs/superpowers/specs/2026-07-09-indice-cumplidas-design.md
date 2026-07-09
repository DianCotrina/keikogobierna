# Índice + certified proposals + registro de cumplidas

**Date:** 2026-07-09
**Status:** Approved by Diego (design conversation, 2026-07-09)

## Problem

Three gaps in the current site:

1. **No in-page navigation.** Topic pages (`/temas/[slug]/`) and the 100-days page are long scrolls (up to 43 proposals per topic; 3 pillars × several topics on 100 días). Readers can't jump to a section.
2. **Fulfilled proposals look almost identical to everything else.** A proposal certified as complete gets only a small stamp; the `evidence` array in `tracking.json` is never shown to visitors, so the certification carries no proof.
3. **No aggregate view of completions.** There is no place that answers "what has actually been delivered?" across all topics.

## Design

### Unit 1: `PlanIndex` component (índice block)

`src/components/PlanIndex.astro` — flat, Tailwind-only (no own CSS, so no folder per the component-folder convention).

**Props:**

```ts
interface IndexEntry {
  href: string;        // '#metas'
  label: string;       // 'Metas al 2031'
  count?: number;      // 5
  children?: { href: string; label: string }[];
}
interface Props {
  entries: IndexEntry[];
}
```

**Rendering:** a case-file "Índice" box near the top of the page: mono eyebrow header (`ÍNDICE · EXPEDIENTE`), numbered rows (01/02/03 — the sections are a real ordered sequence), dotted leaders between label and count, indented sub-links for children. Anchor links only; no JS. All visible text in Spanish.

**Usage:**

- **Topic pages** (`src/pages/temas/[slug].astro`): three entries — Metas al 2031 (`#metas`, count = goals), Propuestas (`#propuestas`, count = proposals, children = proposal group titles anchored `#grupo-<n>`), Primeros 100 días (`#cien-dias`, count = actions). The target sections gain `id` attributes and `scroll-mt-*` so anchors land comfortably.
- **100-days page** (`src/pages/primeros-100-dias.astro`): one entry per pillar (count = actions in pillar), children = the pillar's topics, anchoring to new `id`s on pillar/topic blocks.

### Unit 2: Certified proposal rows with evidence

**Evidence schema** (entries of `tracking.json` → `items[id].evidence`):

```json
{ "date": "YYYY-MM-DD", "source": "El Peruano", "url": "https://…", "note": "optional" }
```

- `date` (required, `YYYY-MM-DD`) — when verified
- `source` (required, non-empty string) — who/what certifies it
- `url` (optional, must start with `http`) — link to the source
- `note` (optional string) — verification note

**Validator** (`tools/validate_plan_data.py`): validate every evidence entry against this schema. New editorial rule: **an item with `status: "fulfilled"` must have at least one evidence entry** — no certification without proof. Applies to all tracked items (goals and proposals alike).

**`ProposalRow` component:** extract the proposal row currently inline in `[slug].astro` (id chip · text · optional stamp) into `src/components/ProposalRow.astro` (flat, Tailwind-only). Props: `proposal { id, text }`, `status?`, `evidence?`.

- Non-fulfilled rows render exactly as today (zero visual change).
- Fulfilled rows get the certified treatment: subtle verde-tinted row background, Cumplida stamp, and a native `<details>` disclosure labeled "Ver evidencia →" that reveals each evidence entry (date · source, linked when `url` present, note underneath). No JavaScript; `<details>` styled to read as a verification note inside the case file.

### Unit 3: Registro de cumplidas (home section, page-ready)

**Data:** new function in `src/lib/plan.mjs`:

```js
fulfilledItems(plan, topics, tracking)
// → { total, byPillar: [{ id, name, count }], items: [{ id, text, topicName, topicSlug, pillarName, evidence }] }
```

Only proposals/actions with `status: "fulfilled"` in `tracking.items`. Goals are excluded (they have their own display in GoalRow/home stats).

**Component:** `src/components/CumplidasRegistry.astro` — self-contained, takes the `fulfilledItems` result via props, no page-specific assumptions. Rendered as a new section on the home page (below the Avance general area) with anchor `#cumplidas`.

- **Populated state:** per-pillar counters plus a list of certified proposals — each row: id chip, text, topic link, date of certification (latest evidence date).
- **Empty state (current reality, 0 fulfilled):** the registry renders as an open case file — copy: "El registro está abierto. Cuando una propuesta se certifique como cumplida, aparecerá aquí con su evidencia." — with per-pillar counters showing 0. The zeros are shown, not hidden: that is the message.

**Graduation path:** when volume justifies it, a `/cumplidas/` page is a thin page file that imports `CumplidasRegistry` with the same props. Nothing in the component may assume it lives on the home page.

## Out of scope

- Evidence display on GoalRow or 100-days action rows (stamps only, as today).
- Filtering/sorting in the registry.
- The dedicated `/cumplidas/` page (documented path only).

## Testing

- `node --test` cases following `tests/plan.test.mjs` patterns: `fulfilledItems` (empty tracking → total 0; fixture with fulfilled proposal → correct pillar counts, topic metadata, evidence passthrough).
- Validator: `npm run validate` passes on real data; fails on a fulfilled-without-evidence fixture and on malformed evidence entries (bad date, missing source).
- `npm run build` passes.
- Visual verification (headless Brave on localhost): índice block on a topic page and the 100-days page; certified row + populated registry previewed with a temporary mock fulfilled item (reverted before commit); empty-state registry on real data.
