# Workflow — documenting a minister's judicial record

**Objective.** Add or update a `judicial[]` entry in `src/data/cabinet/people.json`
so that every claim on a minister's dossier is sourced, correctly staged, and
defensible.

**Nothing in this workflow is automated end to end, by design.** Peru publishes no
queryable criminal-record database — the *Certificado de Antecedentes Penales* is
issued only to the person it concerns — and the two official systems that do exist
are closed to machines (see "Why it is manual"). Tools discover; a person certifies.

## Inputs

- The person's entry in `people.json` (create it first if absent — see step 1)
- At least one source you can link, per the evidence bar in
  `docs/superpowers/specs/2026-07-27-gabinete-design.md`

## Steps

### 1. Draft the person from the JNE, if they ran for office

```bash
python3 tools/scrapers/jne_scraper.py --name "Nombre Apellido"   # find candidates
python3 tools/scrapers/jne_scraper.py --id <idHojaVida>          # draft the one you verified
```

**Confirm the party before using an id.** A name match is not an identity match:
"Carlos Espá" matches a PARTIDO SICREO candidate who is not the Fuerza Popular
minister. If the person never stood for election they have no hoja de vida, and
this step produces nothing — that is expected, not a failure.

The draft's `bio` is empty and any `judicial[]` entries carry `stage: null`.
Both need a person. `npm run validate` fails while a stage is unset, so a draft
cannot reach the site by accident.

### 2. Classify each declared sentence

Read `_declaracion` on the entry — `txFalloPenal`, `txModalidad`, `txCumpleFallo`
and `txComentario` together — and set `stage` from the **fallo**, never the
modalidad.

> Real record: `delito: TERRORISMO`, `fallo: ABSUELTO`, `modalidad: EFECTIVA`.
> The person was **acquitted**. Staging that from `modalidad` would publish a
> terrorism conviction against him.

Another real record files `delito`, `fallo` and `órgano` all as `"0"`, with the
substance ("causa penal prescrita") in the free-text comment. When the
declaration cannot be read confidently, do not guess: leave the entry out and
open an issue instead.

Delete `_declaracion` once you have staged the entry — it is scaffolding for the
reviewer, not published data.

### 3. Check the press signals

```bash
python3 tools/scrapers/cabinet_scraper.py --press --dry-run
```

The tail of that run lists judicial coverage of people already on the roster.
Each signal is a **prompt, not a finding** — press reports allegations far more
loosely than a court records them. Use a signal to go looking for the primary
document; never stage an entry from a headline.

### 4. Verify against the primary source

Look the case up by hand:

- **Poder Judicial — CEJ**: <https://cej.pj.gob.pe/cej/forms/busquedaform.html>
  Search by *expediente*. Record the expediente number in the entry.
- **Ministerio Público**: <https://www.gob.pe/mpfn> for fiscal stages.
- **El Peruano**: some resolutions are published as normas and are already
  archived in `normas-archive`.

Set `stage` to what the resolution says. If the case was archived, absolved or
prescribed, use the exculpatory stage — those rank 0 and must never colour the
badge.

### 5. Validate and open a PR

```bash
npm run validate    # fails on an unsourced entry, an unset stage, a bad date
npm test
```

One PR per person. In the description, state which source certified each stage.

## Why it is manual

Checked 2026-07-27:

| Source | Machine access |
|---|---|
| Poder Judicial (CEJ) | **Blocked** — Radware Bot Manager; the page redirects to `validate.perfdrive.com` with an image captcha. It also has no name search: you need an expediente number already. |
| Ministerio Público | **Blocked** — `403` to non-browser clients. |
| JNE hoja de vida | **Open** — used in step 1. Self-declared and candidates only. |
| Registro Nacional de Condenas | **Not public.** Antecedentes penales are personal data; the certificate is issued only to the individual. |

Do not attempt to work around the first two. They are access controls on
government systems, and the site's evidentiary standard does not depend on
defeating them — it depends on a person reading the resolution.

## Edge cases

- **A minister with no hoja de vida and no press coverage.** Their badge reads
  *Sin registro público*, which is worded as the limit of our search, not a
  finding of innocence. That is the correct outcome; leave it.
- **A later resolution reverses an earlier one.** Add the new entry with its own
  date and stage rather than editing the old one, so the sequence stays visible.
  An acquittal after a conviction is exactly what a reader needs to see.
- **A correction request.** Every dossier carries a right-of-reply block. Treat
  documented corrections as priority work and publish them with the same
  visibility as the original entry.
