# Gabinete — cabinet roster and judicial dossiers

**Date:** 2026-07-27
**Status:** approved, ready for planning

## Problem

The site tracks 764 commitments but never says who is accountable for them. The cabinet
proclaimed on 2026-07-27 puts a name on every ministry, and those names carry public
judicial histories that are material to whether the plan gets executed.

Two things are missing:

1. **Who holds each portfolio, and for how long.** Peruvian cabinets churn. A minister's
   tenure length is itself an accountability fact, and today's roster will not be next
   year's.
2. **What is documented against each of them.** Investigations, charges, and convictions
   are public record, but scattered across the Poder Judicial, the Ministerio Público, and
   the press.

## Goal

A `/gabinete/` section that answers "who is running each ministry, what are they
responsible for in the plan, and what does the public record say about them" — held to the
same evidentiary standard as the rest of the site: nothing published without a linked
source, nothing certified without a human.

## Non-goals

- Scraping judicial records. El Peruano publishes appointments, not criminal histories.
  The `judicial[]` record is hand-curated by a person, permanently.
- Reordering the headline progress metric. The two-layer tracking rule stands: the
  percentage is computed only from goals. Ministers add context, never arithmetic.
- Editorializing. The site states stages and sources. It does not characterize guilt.

## Constraints

- **No AI in any pipeline.** Parsing is deterministic regex over formulaic gazette text.
- **Discovery ≠ certification.** No scraper writes cabinet data; it files issues.
- **Legal exposure is real.** These are named living people in Peru. Conflating
  *investigación preliminar* with *sentencia firme* is defamatory. The design treats the
  distinction as structural, not editorial.

---

## Data model

Three entities under `src/data/cabinet/`, mirroring the plan data's registry / detail /
living-state split:

```
src/data/cabinet/
├── portfolios.json          # Registry: the ministries + PCM. Frozen ids.
├── people/
│   └── nombre-apellido.json # ×N — one dossier per person
└── tenures.json             # Living state: who held what, when
```

**Why three entities and not one.** A person can hold two portfolios across a term, and a
portfolio outlives its holders. Collapsing them would duplicate a judicial dossier every
time someone changes desks. The dossier belongs to the *person*; the tenure is the *edge*
between person and portfolio.

### `portfolios.json`

```json
{
  "portfolios": [
    {
      "id": "m-interior",
      "name": "Ministerio del Interior",
      "slug": "interior",
      "topics": ["t1-1"]
    }
  ]
}
```

`topics[]` links each ministry to the plan topics it owns. That field is what ties the
roster to the tracker. Ids are frozen once assigned — `tenures.json` references them.

### `people/<slug>.json`

```json
{
  "slug": "nombre-apellido",
  "name": "Nombre Apellido",
  "profession": "Abogado",
  "bio": "Two neutral sentences.",
  "sources": [{ "label": "Hoja de vida JNE", "url": "https://…", "kind": "primary" }],
  "judicial": [
    {
      "id": "caso-01",
      "case": "Caso Cócteles",
      "expediente": "00299-2017-36-5001-JR-PE-01",
      "stage": "sentencia_firme",
      "crime": "lavado de activos",
      "body": "Poder Judicial · 1er Juzgado Penal",
      "date": "2026-03-12",
      "summary": "One neutral paragraph of fact.",
      "sources": [{ "label": "…", "url": "https://…", "kind": "primary" }]
    }
  ]
}
```

`crime` is the offense **as charged**, verbatim. `summary` states what happened without
characterizing it. `sources[]` is required and non-empty on every entry, and each source
carries `kind: "primary" | "press"`. `id` is a per-person stable slug used as the fragment
anchor for deep-linking a single entry.

### `tenures.json`

```json
{
  "tenures": [
    {
      "person": "nombre-apellido",
      "portfolio": "m-interior",
      "start": "2026-07-28",
      "end": null,
      "appointment_norma": {
        "numero": "R.S. N° 001-2026-PCM",
        "url": "https://busquedas.elperuano.pe/…",
        "date": "2026-07-28"
      },
      "exit_norma": null,
      "exit_reason": null
    }
  ]
}
```

`end: null` means currently serving. Days served is **derived, never stored**.

### Provenance split

| Data | Source | Who writes it |
|---|---|---|
| Names, portfolios, dates, norma ids | El Peruano gazette | Scraper proposes → human PRs |
| Bio, profession | JNE hoja de vida, public record | Human |
| `judicial[]` | Poder Judicial, Ministerio Público, press | Human, always |

---

## Discovery

`tools/scrapers/cabinet_rules.py` — pure functions, no I/O, unit-tested against real
captured normas.

Appointment normas are formulaic:

> **Resolución Suprema N° 001-2026-PCM** — *sumilla:* "Nombran Ministro de Estado en el
> Despacho del Interior"
> *body:* "Artículo 1.- Nombrar al señor NOMBRE APELLIDO como Ministro de Estado en el
> Despacho del Interior."

Two functions:

- `is_cabinet_norma(record)` — gates on `tipo == "RESOLUCIÓN SUPREMA"`, sector PCM, and a
  sumilla matching `nombran?|designan?|aceptan la renuncia` near `Ministr[oa] de Estado`.
- `parse_cabinet_act(record, text)` → `{action, person, portfolio, norma, date, url}` or
  `None`. `action` is `nombramiento` or `renuncia`.

`cabinet_rules.py` holds only these pure functions. Both entry points below import it and
supply the I/O, reusing the existing `fetch_normas()` (GraphQL, returns `sumilla` /
`nombreDispositivo` / `fecha` / `op`) and `norma_text()` (full body via `visor_html`).

### Two entry points

| Mode | Command | Use |
|---|---|---|
| Backfill | `cabinet_scraper.py --from 2026-07-28 --to <hoy>` | Seeds the initial roster in one sweep |
| Daily | folded into `elperuano_scraper.py`'s existing run | Files an issue labeled `cambio-de-gabinete` |

Both support `--dry-run`, consistent with every other scraper.

### The human gate

The scraper **never writes `tenures.json`**. It files a GitHub issue containing a
ready-to-paste JSON block plus the norma link; a person opens the PR. Identical to how
norma → `tracking.json` already works.

**Known limit:** matching a name across normas (appointed, resigns, returns) is fuzzy. The
validator flags a tenure whose `person` does not resolve to an existing `people/` slug
rather than the scraper guessing at identity.

---

## The stage ladder

`src/lib/judicial.mjs` — a `STAGES` map shaped like `statuses.mjs`, plus a `rank` field.

| Stage | Label | Color | Rank |
|---|---|---|---|
| `sentencia_firme` | Sentencia firme | rojo | 6 |
| `sentencia_no_firme` | Sentencia en apelación | rojo | 5 |
| `juicio_oral` | En juicio oral | ambar | 4 |
| `acusacion_fiscal` | Acusación fiscal | ambar | 3 |
| `investigacion_preparatoria` | Investigación preparatoria | ambar | 2 |
| `investigacion_preliminar` | Investigación preliminar | ambar | 1 |
| `absuelto` | Absuelto | verde | 0 |
| `archivado` | Archivado | plomo | 0 |
| `prescrito` | Prescrito | plomo | 0 |

**Rank 0 is load-bearing.** Exculpatory outcomes can never drive the badge. Someone
investigated and then absolved does not carry an amber badge for it — otherwise the site
punishes people for accusations that failed, the exact failure mode this section must
avoid.

### `recordBadge(person)`

Three shapes:

| Condition | Label | Color | Detail line |
|---|---|---|---|
| No entries | Sin registro público | plomo | "No hallamos procesos documentados" |
| All entries rank 0 | Sin procesos activos | verde | "1 absuelto · 1 archivado" |
| Otherwise | Highest-rank active stage | its color | "1 condena · 2 procesos abiertos" |

*Sin registro público* is worded as the limit of our search, never as a claim of
innocence.

---

## Pages

### `/gabinete/`

Masthead in the `fuentes.astro` idiom: mono eyebrow, display `h1` with the pen-stroke SVG,
lead paragraph. Then, **before any name appears**, the presumption-of-innocence notice.
Then:

- Stat strip — ministerios · con procesos activos · días desde la juramentación ·
  cambios de gabinete. "Con procesos activos" counts ministers holding at least one entry
  of rank ≥ 1; someone whose only entries are absuelto/archivado/prescrito is not counted.
- Card grid, one `MinisterCard` per portfolio (including vacant ones)
- **"Pasaron por aquí"** — ended tenures with days served

### `/gabinete/[slug]/`

Via `getStaticPaths()`, keyed on **person**, not portfolio — the dossier follows the human,
who may change desks.

1. Name, current portfolio (or *ex-ministro*), badge
2. **Responsable de** — the portfolio's plan topics with live progress, reusing
   `topicSummaries()` from `plan.mjs`
3. **Paso por el cargo** — tenure timeline, each row linking its Resolución Suprema
4. **Registro judicial** — entries by rank then date: stage chip, offense as charged, court
   + date, neutral summary, source links. Exculpatory entries get identical visual weight.
5. Corrections / right-of-reply block

### Elsewhere

- `/api/gabinete.json` alongside the two existing open-data endpoints
- "Gabinete" link in the header nav in `Base.astro`
- `fuentes.astro` gains the judicial sources under *Contraste · revisión humana*:
  Poder Judicial (CEJ), Ministerio Público, JNE hoja de vida

### Components

`MinisterCard`, `RecordBadge`, `JudicialEntry`, `TenureTimeline`, `PresuncionNotice` — all
Tailwind-only, therefore all flat files per the folder-module convention.

### Library

`src/lib/cabinet.mjs` — `loadPortfolios`, `loadPeople`, `loadTenures`, `currentCabinet`,
`pastTenures`, `tenureDays`, `personBySlug`, `portfolioTopics`. Pure functions, JSON via
static ESM imports (`fs` reads break under the bundler — see the comment in `plan.mjs`).

---

## Validation

`tools/cabinet/validate_cabinet_data.py`, run by `npm run validate` alongside the plan
validator. CI needs no edit — the `checks` job already runs `npm test`, `npm run validate`,
and `unittest discover`.

Hard failures:

- A `judicial[]` entry with zero sources, or any non-`https` source URL
- A source whose `kind` is not `primary` or `press`
- Duplicate `judicial[].id` within one person
- `stage` outside the enum
- Any date non-ISO or in the future
- A tenure whose `person` or `portfolio` does not resolve
- Overlapping tenures on one portfolio, or more than one open tenure per portfolio
- A tenure with no `appointment_norma`
- `portfolios[].topics[]` referencing a plan topic id that does not exist
- A `people/` filename that does not match its `slug`, or duplicate slugs

**The first rule is the point:** publishing an unsourced accusation becomes a build
failure, not a matter of discipline.

## Tests

- `tests/cabinet.test.mjs` — `recordBadge` across all three shapes, with explicit coverage
  that rank-0 entries never drive it; `tenureDays`; `currentCabinet`; `pastTenures`
- `tools/tests/test_cabinet_rules.py` — `is_cabinet_norma` and `parse_cabinet_act` against
  **real captured normas** saved into the existing `tools/tests/fixtures/`, not invented
  strings

## Editorial guardrails

Enforced in code, not only in documentation:

- Presumption-of-innocence notice renders before any name on both pages
- `crime` is the charge verbatim, never paraphrased
- Exculpatory outcomes get identical visual weight; rank 0 enforces it in the badge
- *Sin registro público* is phrased as the limit of our search
- Right-of-reply block on every dossier

## Documentation

`docs/ARCHITECTURE.md` gains the cabinet data described alongside the plan data, and the
cabinet rule noted in the discovery pipeline table.

---

## Rollout

Five phases, each independently shippable:

| # | Phase | Ships |
|---|---|---|
| 1 | Data model, validator, `cabinet.mjs` + `judicial.mjs`, tests | Nothing visible |
| 2 | `cabinet_rules.py` + backfill sweep | Roster data lands from El Peruano |
| 3 | Pages + components | `/gabinete/` goes live |
| 4 | Daily cabinet rule in `elperuano_scraper.py` | Churn detection |
| 5 | Judicial curation | Ongoing, per-person PRs |

Phase 5 is deliberately last and gates nothing — pages render with empty `judicial[]`,
every badge honestly reading *Sin registro público*. The roster is worth shipping before a
single judicial entry exists.

## Open question deferred

Whether each topic page (`temas/[slug]`) gains a "responsable" backlink naming the
accountable minister. Deferred until the roster is live and stable — the link is trivial to
add later and the reverse direction (`Responsable de` on the dossier) already delivers the
connection.
