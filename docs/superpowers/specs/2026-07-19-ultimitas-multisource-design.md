# Ultimitas multi-source: La República + filterable merged feed

**Date:** 2026-07-19
**Status:** Design approved in conversation (Diego, 2026-07-19); spec review pending

## Problem

"Las ultimitas" is a single-outlet hemeroteca: only El Comercio feeds it. Diego wants
La República as a second source, with a UI that lets the reader tell sources apart and
filter between them.

**Approved UX (decided over alternatives):** one merged chronological feed — readers scan
news by recency, not by outlet — with a source chip on every card and filter chips above
the list (*Todas / El Comercio / La República*). A two-button per-outlet toggle and
stacked per-source sections were considered and rejected (hides half the news, or doubles
page length). **Text wordmark chips, not image logos** — third-party logos on a politically
charged site are a trademark exposure with no UX gain.

## Reconnaissance (2026-07-19, verified live)

- `https://larepublica.pe/rss/politica.xml` → **200**, ~310 KB, classic RSS. This is the
  feed. (`larepublica.pe/arc/outboundfeeds/rss/...` returns 301 — La República does not
  expose the Arc XP outbound feeds El Comercio uses.)
- Field mapping (title/link/description/pubDate/dc:creator) is confirmed against the real
  feed during implementation, per the real-data-testing rule — no invented fixtures; the
  committed test fixture is a captured slice of the actual feed.

## Design

### One scraper, not two (architecture decision)

`tools/scrapers/elcomercio_scraper.py` generalizes into **`ultimitas_scraper.py`** with a
`SOURCES` config list; it is not duplicated per outlet. The controlling reason: two
scrapers publishing to the same `ultimitas-data` branch on independent schedules would
race in `publish_data_branch.sh` (non-fast-forward pushes). One tool, one run, one write.

```python
SOURCES = [
  # El Comercio keeps its two existing Arc XP feeds (política + general),
  # exactly as in today's FEEDS constant.
  {"name": "El Comercio",  "feeds": [
    "https://elcomercio.pe/arc/outboundfeeds/rss/category/politica/?outputType=xml",
    "https://elcomercio.pe/arc/outboundfeeds/rss/?outputType=xml",
  ]},
  {"name": "La República", "feeds": ["https://larepublica.pe/rss/politica.xml"]},
]
KEYWORDS = ["keiko fujimori", "keiko", "fuerza popular", "fujimorismo"]  # shared
```

- Same keyword filter, same `canonical_url()` cleanup, same Lima-day selection.
- **Per-source failure isolation:** each source fetches inside its own `try/except`; one
  outlet's outage or format drift must not block the other's publication. A failed source
  is logged loudly in the run output.
- **Copyright rule unchanged and applies to La República identically:** only title, link,
  description snippet, author and date are stored — never full article bodies.

### Data contract: `source` on every article

`ultimitas.json` (history) and `today.json` (what the page fetches) gain one field per
article: `"source": "El Comercio" | "La República"`. Dedup key stays the canonical URL.

**Backward compatibility:** the page treats a missing `source` as `"El Comercio"` (all
existing records are El Comercio), so the UI ships safely regardless of which deploys
first — old data renders correctly, new data renders labeled.

### UI: `src/components/Ultimitas/`

- **Card meta line** becomes `HH:MM · {source} · {author}` — the hardcoded "El Comercio"
  is replaced by the article's source.
- **Source chip:** small mono wordmark chip on each card (same visual family as the
  tema/status chips — `font-mono`, uppercase, bordered; no images).
- **Filter chips** above the list: *Todas / El Comercio / La República*. Client-side
  filtering over the already-rendered cards via a `data-source` attribute — no refetch.
  Buttons carry `aria-pressed`; "Todas" is the default. If a filter yields zero cards for
  the loaded day, show the existing empty-day message scoped to that source.
- All third-party text still renders via `textContent`; article URLs still pass
  `safeHttpUrl()`.
- Page subtitle updates to name both outlets.

### Fuentes page

Ships **in the same PR** as the scraper: a La República card is added to the
*Fuentes automáticas* section, and the Google News entry's example list drops
"La República" (it graduates to a named source). The fuentes page must never lead the
pipelines — it changes only when the pipeline change lands.

### Unchanged

`ultimitas-scraper.yml` cadence (4×/day) and the data-branch publish flow; the
`ultimitas-data` branch layout; the CORS/no-rebuild delivery via raw.githubusercontent.com.

## Testing (real data)

- Unit: `parse_rss_items` mapping against a captured real La República feed slice;
  merge/dedup with mixed-source history; source-default backward compat ("article without
  source renders as El Comercio").
- Live: `--dry-run` against both real feeds prints per-source match counts.
- Visual: screenshots of the page with real mixed-source data — chips, filtering, and the
  zero-result state — desktop and 390px.

## Failure modes / maintenance

- La República's RSS is an unofficial-stability interface like every other source here:
  if it changes shape, that source's fetch fails loudly in the Action log while El
  Comercio keeps publishing.
- Adding outlet #3 later = one `SOURCES` entry + a fuentes card (the UI chips render from
  the sources present in the data, not from a hardcoded list).

## Out of scope

- Image logos (wordmarks only, by decision) · more outlets now · per-source pages ·
  any change to the evidence pipeline (this is the news plane only).

## Decisions log (conversation, 2026-07-19)

- Merged feed + filter chips over per-outlet toggle/sections — Diego approved the
  recommended option.
- Wordmark chips over logos (trademark caution accepted).
- Single generalized scraper over parallel scrapers (branch-race avoidance).
- `source` field with El Comercio default for backward compatibility.
