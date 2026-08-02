# Daily press coverage on each minister's dossier — design

**Date:** 2026-08-01
**Status:** approved, ready for an implementation plan

## Objective

Show, on each minister's page at `/gabinete/<slug>/`, the press coverage that
named them in the last seven days: headline, outlet, date, link out.

## What a listed article means

**Coverage, and nothing more** — "outlets published this about this minister".
Not a claim that it is important, that it is true, or that the minister acted.
This is the standard `/ultimitas/` already sets, applied per person.

The distinction matters because this section sits on the same page as the
judicial record. A reader must not be able to read the presence of an article as
an accusation, and the wording has to earn that.

## Non-goals

- No editorial selection, ranking by importance, or commentary.
- No article bodies. Headline, feed summary, outlet, date and link only — the
  copyright rule the press pipeline already follows.
- No sentiment, topic classification or any AI step. The site has no AI in any
  pipeline and this does not introduce one.
- No coverage counts on the roster page. One place, one purpose.

## Architecture

One tool writes, one file, the page reads it client-side — the shape
`/ultimitas/` already proves in production.

```
GitHub Action (4×/day) → ultimitas_scraper
    ├── ultimitas.json    accumulated history   2 outlets, KEYWORDS-filtered
    ├── today.json        the /ultimitas/ page  2 outlets, KEYWORDS-filtered
    └── ministros.json    NEW                   5 outlets, per-minister
                              ↓  raw.githubusercontent.com, CORS-open, ~5-min edge cache
                          /gabinete/<slug>/ fetches once, renders its own slice
```

**No new scheduled job.** `ultimitas_scraper`'s docstring records why: parallel
scrapers would race on the `ultimitas-data` branch, which a single Action owns.
The new file is written in the same pass over the same fetched articles.

### Why the site cannot build this in

`/gabinete/<slug>/` is a static page. News changes four times a day. Baking
coverage into the build would mean a commit and a rebuild on every run, against
a `main` protected by the `protect-main` ruleset and versioned by
release-please. That cost is not worth a news list, and the client-side fetch
pattern already exists for exactly this reason.

### Why matching stays in Python

Matching needs the cartera lexicon from `portfolios.json` (including aliases
like MTC, Minem, canciller) and the Peruvian surname rules. Reimplementing that
in TypeScript to match in the browser would be a second implementation of the
same judgement, guaranteed to drift from the first.

## Which outlets

All five in `press_feeds.SOURCES`: El Comercio, La República, RPP, Gestión,
Infobae.

This is deliberately wider than `/ultimitas/`, which publishes only El Comercio
and La República because only those two have a *política* feed that is Peruvian
politics. For per-minister coverage the extra three carry real weight — Gestión
covers the economic carteras, Infobae covers ministers the others do not — and
the two-key matcher, not the feed's section, is what supplies precision.

## Matching

Reuses the two-key rule in `infobae_rules.profile_items()`: an article matches a
minister only when it names **both** their cartera and one of their apellidos.

Three things about that function have to change, and none of them is the rule:

- It stops at the first minister an article matches (`break`). For a profile
  packet that is reasonable; for coverage it is not — an article naming two
  ministers is coverage of both, and which one currently wins is roster order,
  which is arbitrary. The `break` goes, and the profile reader gets strictly
  more material, which serves it.
- It orders profile pieces before news. That is right for a reader writing a
  ficha and wrong for a dated news list, so ordering moves to the caller: the
  profile reader keeps profiles-first, this feature sorts newest-first.
- It returns a map keyed by **cartera id**. This feature keys by minister slug,
  so the caller maps one to the other through the roster it already built.

Measured against the live feed on 2026-08-01: 441 unique articles produced 11
links across 7 of 19 ministers in one day. Over a rolling week most dossiers
carry something; some will not, and that is the honest result.

**Precision is not traded for fuller pages.** Matching on a surname alone was
measured and rejected: it produced 329 links, attributing *"Canales TV que
transmiten Real Madrid vs Fiorentina"* to the Desarrollo Social minister and
*"Andrea Llosa habla de su nuevo libro"* to the Defence minister. On a page
carrying a judicial record, a wrongly attributed headline is the failure mode
worth engineering against.

An article naming two ministers appears under both. That is correct: it covers
both.

## Data contract — `ministros.json`

Written to the `ultimitas-data` branch beside the existing two files.

```json
{
  "generated": "2026-08-01T06:00:12+00:00",
  "window_days": 7,
  "sources": ["El Comercio", "La República", "RPP", "Gestión", "Infobae"],
  "ministers": {
    "elmer-rafael-cuba-bustinza": [
      {
        "title": "Elmer Cuba: lo que recomendaba el nuevo ministro antes de ser titular del MEF",
        "url": "https://gestion.pe/economia/...",
        "source": "Gestión",
        "published": "2026-08-01T08:37:00-05:00",
        "matched_in": "title"
      }
    ]
  }
}
```

- Keyed by **minister slug**, not cartera id: the page knows its own slug, and a
  cartera changing hands must not carry the previous holder's coverage forward.
  The matcher works in cartera ids; the caller translates using the same roster
  it matched against.
- `summary` and `author` are omitted. The dossier shows headline, outlet and
  date; carrying the summary would ship text the page never renders.
- `matched_in` is `"title"` or `"summary"`: the two-key match (cartera *and*
  apellido) runs against the headline plus the feed summary together, so an
  article can match while its headline names someone else entirely.
  `matched_in` asks a narrower question than the match itself — does one of
  the minister's apellidos appear in the headline, cartera aside — so the
  page can avoid implying the headline is about this minister when it plainly
  is not, without also qualifying headlines that already lead with their own
  name but never spell out the ministry.
- Sorted newest first per minister.
- A minister with no coverage is absent from the map rather than present with an
  empty list — the page treats both identically, and absence keeps the file small.

## The section on the page

Placed after **Paso por el cargo** and before **Registro judicial**: the factual
record first, then coverage, then the sensitive material.

Per item: headline (linked, `target="_blank"`, `rel="noopener noreferrer"`),
outlet and date. Third-party text is rendered with `textContent` only, and the
URL passes the existing `safeHttpUrl()` scheme guard before becoming an `href` —
both are established rules in `ultimitas.ts`, and this is third-party text from
the same feeds. `safeHttpUrl()` is currently a private function inside
`ultimitas.ts`; it moves to a shared module so both renderers use one guard
rather than two copies that can drift.

Copy is Spanish (Peru):

- Heading: **Cobertura de prensa**
- Blurb: *Notas publicadas sobre este ministro en los últimos 7 días. Que una
  nota aparezca aquí no significa que este sitio la respalde.*
- Empty: *Sin cobertura en los últimos 7 días.* — the limit of the search,
  worded like the existing «sin registro público», not a claim that nothing
  happened.

## Failure handling

Progressive enhancement throughout. If `ministros.json` is missing, malformed,
stale, or the request fails, the section renders nothing and every other part of
the dossier is untouched. This mirrors `/ultimitas/`, whose error state the site
already ships. A scraper outage can never break a minister's page, and the page
must never show a spinner that outlives the request.

The scraper side inherits the per-source isolation already in `fetch_sources`:
one outlet's outage removes that outlet's coverage and nothing else.

## Testing

Python, in `tools/tests/`:

- The 7-day window keeps an article dated 6 days ago and drops one dated 8.
- The window is measured in Lima days, consistent with `select_today`.
- Keying is by slug, and a closed tenure's holder does not receive coverage.
- An article naming two ministers lands under both, not only the first.
- The profile reader still orders profile pieces first after ordering moved out.
- Output shape: required keys present, `summary` and `author` absent.
- A minister with no matches is absent from the map.

Node, in `tests/`:

- Rendering an empty map produces the empty-state copy, not a broken section.
- A malformed payload renders nothing and throws nothing.
- A `javascript:` URL in a payload is rejected by the scheme guard.

## Dependencies

Requires the three fixes on `fix/infobae-roster-after-appointment`, without
which the roster this feature matches against is empty:

- `roster()` reading open tenures rather than announcements
- `_surnames()` taking apellidos from the end of the name
- `fetch_sources()` de-duplicating across an outlet's feeds

## Open questions

None. Placement, window, outlet set and matching strictness are settled above.
