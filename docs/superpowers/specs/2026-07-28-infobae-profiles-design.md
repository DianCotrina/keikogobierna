# Infobae profiles — design

**Date:** 2026-07-28
**Branch:** `feat/gabinete`
**Status:** approved

## Problem

The roster names all 19 ministers but carries one ficha. Eighteen cards read:

> *Aún no publicamos su ficha: falta confirmar de qué persona se trata en los
> registros públicos.*

The JNE path cannot close that gap. A hoja de vida exists only for people who
stood for election, and the tool correctly reports *"sin hoja de vida en el
padrón (no fue candidato)"* for Vinelli, Espá and Cuba among others. Ministers
appointed from outside politics have no declaration at all.

Meanwhile Infobae publishes a dedicated profile for nearly every one of them,
and the biographical fact we need most — `profession` — sits in the feed's own
`<description>`:

| Minister | Infobae summary opens with |
|---|---|
| Vinelli | «El **economista y docente universitario**, con amplia trayectoria en agronegocios…» |
| Shinno | «El **ingeniero** llega… tras haber ocupado cargos en el mismo Minem, Osinergmin…» |
| Seminario | «La **administradora piurana** asumió el cargo…» |
| Requejo | «El **abogado** llega al gabinete tras desempeñarse como viceministro de Mype…» |
| Astudillo | «**exjefe del Comando Conjunto de las FF.AA.**» |

Measured on the live feed: **100 items, 24 mentioning a minister**, profiles
present for at least 15 of the 19.

## The constraint that shapes everything

The project makes three commitments that a naive "scrape Infobae for bios" would
break:

| Rule | Where |
|---|---|
| Article bodies are never read or stored | `common/press_rules.py` |
| Never full article bodies (they belong to each outlet) | `common/press_feeds.py` |
| «Este sitio no reproduce artículos completos.» | `Ultimitas.astro`, shown to visitors |
| No AI in any pipeline | `docs/ARCHITECTURE.md` |

The resolution: **the RSS `<description>` is metadata, not the body.** It is the
same `summary` field `press_feeds.parse_feed` already reads and `/ultimitas/`
already displays, and the visitor-facing wording explicitly covers it — *"los
titulares y **resúmenes** pertenecen a cada medio"*. The feed also carries
`content:encoded`, which **is** the full body. This design never reads it.

Facts are free to use; Infobae's sentences are theirs. So the tool surfaces
material and a person writes the ficha. `bio` is never machine-generated.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| How much is automated | Review packet; a person writes `profession` and `bio` | Keeps metadata-only, no-AI, and "discovery is not certification" intact, and avoids copying Infobae's prose into our `bio` |
| Feed scope | Infobae joins the shared `SOURCES` | `/ultimitas/`, `cabinet_scraper --press` and `judicial_signals` all gain it at once — which is how the Arnillas conviction gets surfaced rather than stumbled on |
| Matching | Surname **and** portfolio, both required | Name-only fails in both directions; see below |

## Architecture

Four pieces, all landing in homes the recent restructure created.

### 1. Infobae joins `common/press_feeds.py`

```python
{"name": "Infobae", "feeds": [
    "https://www.infobae.com/arc/outboundfeeds/rss/category/peru/?outputType=xml"]},
```

Verified live: 100 items, standard RSS, `title` / `description` / `link` /
`pubDate` all present. A fifth outlet is visitor-facing, so `fuentes.astro` and
the Ultimitas source chips gain it too.

### 2. Portfolio aliases in the registry

Infobae writes acronyms — *"titular del MTC"*, *"cargos en el mismo Minem"*,
*"Ministerio de la Producción (Produce)"* — and synonyms: *"oficializado como
**canciller**"*. `portfolio_id()` knows none of them. This is the same gap that
made the press scraper miss *"ministro del **Midagri**"* on the day of the
swearing-in.

Each portfolio in `portfolios.json` gains an `aliases` array:

```json
{"id": "m-transportes", "name": "Ministerio de Transportes y Comunicaciones",
 "aliases": ["MTC", "Transportes"]}
```

`common/cabinet_rules._load_portfolio_lookup()` folds aliases into the same
lookup it already builds from `name`, `short` and `slug`. Every existing caller
improves; nothing new is hardcoded in Python.

### 3. `common/infobae_rules.py` — pure matching

```python
def profile_items(articles, roster) -> dict
# roster: [{portfolio, person_name}]  (from announcements + people)
# → {portfolio: [{title, summary, url, published, source}]}, best first
```

**Matching needs two keys.** The live feed proves each failure mode:

| Case | Single-key outcome |
|---|---|
| Roster «Mara Seminario Marón» vs Infobae «María Seminario» | all-tokens name matching **misses her** |
| *"**Guardaespaldas del Rey** de España se roba la atención"* | surname-only matching **hits Rafael Rey Rey** |

So an item matches a minister only when it names a **roster surname** *and*
resolves to **that minister's cartera** via `portfolio_id`. The bodyguard story
resolves to no cartera and is rejected; Seminario matches on surname + cartera
despite the given-name variant.

Ranking within a portfolio: items whose title contains a profile marker
(`perfil`, `quién es`, `trayectoria`, `hoja de vida`, `conoce a`) first, then
most recent.

### 4. `tools/scrapers/infobae_profiles.py` — the CLI

Prints, per cartera: the minister, every matched item (headline, summary, link,
date), and a draft `people.json` entry with `profession` and `bio` blank.

```
DESARROLLO AGRARIO Y RIEGO — Marco Vinelli Ruiz
  Infobae · 2026-07-28
  «¿Quién es Marco Vinelli Ruiz? Perfil y hoja de vida del nuevo ministro…»
   El economista y docente universitario, con amplia trayectoria en
   agronegocios y gestión pública, fue designado ministro de…
   https://www.infobae.com/peru/2026/07/28/…

  borrador:
    "slug": "marco-vinelli-ruiz",
    "profession": "",          ← escríbela tú
    "bio": "",                 ← escríbela tú
    "sources": [{"label": "Infobae", "url": "…", "kind": "press"}]
```

It writes nothing. `--portfolio <id>` narrows to one cartera.

## The Arnillas fix

Infobae is carrying:

> **"Ministro Mauricio Arnillas recibió prisión suspendida…"** — *"El nuevo
> titular de Vivienda **declaró una condena por lesiones culposas**…"*

A conviction on a sitting minister, and the strongest single argument for
joining `SOURCES`. But `judicial_signals()` requires **every** token of the
roster name, and the roster now reads *"Mauricio Arnillas Gonzales"* (from El
Peruano) while the headline says *"Mauricio Arnillas"*. **It would silently miss
it.** Adopting full official names made the matcher stricter and, here, worse.

`_mentions` changes to require the **given name and first surname** — the first
two tokens — rather than all of them. `"Mauricio Arnillas"` matches; `"Rafael
Rey"` still rejects the Spanish king's bodyguard because *"Rafael"* is absent.

Single-token roster names are rejected outright, as today.

## Testing

Against a real captured Infobae feed fixture, per the project's practice of
never asserting on invented strings:

| Case | Expectation |
|---|---|
| Profiles found | ≥ 12 of 19 carteras matched |
| Given-name variant | Seminario matched despite `Mara` vs `María` |
| False positive | *"Guardaespaldas del Rey de España"* matches **nothing** |
| Aliases | `MTC` → `m-transportes`, `Minem` → `m-energia-minas`, `Produce` → `m-produccion`, `canciller` → `m-relaciones-exteriores` |
| Ranking | a «¿Quién es…?» item outranks a same-day news item for the same cartera |
| Purity | `profile_items` performs no I/O; the CLI writes no file |
| Regression | `judicial_signals` finds Arnillas; `"Rafael Rey"` still rejects the bodyguard headline |
| Existing behaviour | the four current outlets still parse; `SOURCES` names stay unique |

## Out of scope

Reading `content:encoded` or any article body. Machine-written `bio`. Fetching
Infobae article pages. Storing article text. Any automatic write to
`people.json`.

## Follow-on, not included

`fuentes.astro` and the Ultimitas source chips gain a fifth outlet; that is
visitor-facing copy and ships with this change but is not the subject of it.
