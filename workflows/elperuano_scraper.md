# Workflow: El Peruano Scraper

## Objective

Read the day's normas published in *El Peruano* (the primary source) and surface any that touch a tracked commitment as GitHub issues for editorial review. The reader never changes a status: `src/data/tracking.json` is only updated by a human through the PR flow.

El Peruano is the primary-source, high-precision stream feeding the `evidencia-candidata` queue: it *matches* each norma against the plan's own commitments via the shared `matcher.py` (below).

## How it works

1. `.github/workflows/elperuano-scraper.yml` runs daily (13:00 UTC ≈ 08:00 Lima) or on manual dispatch.
2. `tools/scrapers/elperuano_scraper.py` runs three stages:
   - **Fetch** — GET the public search page `https://busquedas.elperuano.pe/?fechaIni&fechaFin&tipoPublicacion=<NL|BO|PC>&ci=ONLY&start`, paginated 20 cards/page across the day's three editions. Each server-rendered result card is parsed into `{tipo, numero, sector, sumilla, url, op, …}` (`url` is the norma's `/dispositivo/<tipoPub>/<op>` page).
   - **Match against plan commitments** — each norma's `numero + tipo + sumilla` is matched by the shared `tools/scrapers/matcher.py` against `commitment_index.json`, a distinctive-**bigram** index built from all 764 plan commitments (see below). A norma matches a commitment when it contains one of that commitment's distinctive bigrams. A day with zero matches ends the run.
   - **Issues + archive** — one `evidencia-candidata` issue per surviving candidate (stateless `[np-<sha1>]` dedup token in the title, cap 10/run), also labeled `tema:<slug>` per matched commitment so a tema's queue is one GitHub filter. Each issue embeds a text excerpt of the norma plus a ready-to-complete evidence JSON block. Text source: the `/dispositivo/<tipoPub>/<op>` page embeds the clean single-norma rendition in a `#visor-html` box (the same document the retired `/api/visor_html` endpoint served), stdlib-stripped; falls back to the sumilla when unavailable. The day's full record set is appended to `normas/<date>.jsonl` on the `normas-archive` branch (a growing structured corpus for future analysis — not read by anything yet).

   There is **no AI stage** (a Claude judge existed briefly and was removed 2026-07-15 — decision: no API costs; deterministic scrapers + human review are enough).

## The commitment matcher

`matcher.py` is shared (the only place matching logic lives; any future source uses it). Its index is built from the plan, not hand-written:

- `tools/scrapers/build_commitment_index.py` reads `src/data/plan/` (proposals + first-100-days + goals) and writes `commitment_index.json`: for each commitment, the **bigrams** (adjacent significant-word pairs) that are rare across the other commitments (`DF_MAX_BIGRAM`). Regenerate it whenever the plan changes: `python3 tools/scrapers/build_commitment_index.py`. CI runs `--check` to fail if the committed file drifts from the plan.
- **Why bigrams only:** a single word rare in the plan ("fiscal", "horario") is still common in daily normas, so unigram matching floods the queue. Multiword phrases ("unidades flagrancia", "ventanilla consular") are the precise signal. Matching is on filtered-token subsequences, so `"unidades flagrancia"` still matches "unidades **de** flagrancia".
- `tools/scrapers/commitment_overlay.json` is the hand-tune layer:
  - `suppress_phrases` — generic government bigrams the plan-frequency can't catch (they appear once in the plan but constantly in normas: "poder judicial", "servicios publicos", "direccion general", …). This is the main precision knob; add offenders here.
  - `boost` — extra phrases per commitment, including distinctive **single words** (e.g. `c5i`), the only route by which a unigram matches.
  - `mute_commitments` — silence a noisy commitment id, or a whole tema id (`t1-1`).
  - `suppress_terms` — extra global stopwords dropped during tokenization.
- Precision reference: over 4 real days this yields ~5–13 matched normas/day out of 300–650 (favor precision; misses are acceptable and caught by the news watcher or manual review).

## Inputs / config

- `tools/scrapers/commitment_index.json` — generated from the plan; regenerate with `build_commitment_index.py` when the plan changes.
- `tools/scrapers/commitment_overlay.json` — hand-tune: `suppress_phrases`, `boost`, `mute_commitments`, `suppress_terms` (see the matcher section).
- `tools/scrapers/elperuano_scraper.py` → `SKIP_TIPOS` — norma types to drop outright (empty by default; add municipal/local types if local noise appears); `EXCERPT_CHARS` — issue excerpt length.

## Local testing

```bash
python3 tools/scrapers/elperuano_scraper.py --dry-run                 # today, print records/matches, no writes
python3 tools/scrapers/elperuano_scraper.py --date 2026-07-10 --dry-run
python3 tools/scrapers/build_commitment_index.py --report            # commitments with zero phrases
python3 tools/scrapers/build_commitment_index.py --check             # fail if index drifts from the plan
python3 -m unittest discover -s tools/tests -p "test_*.py"        # deterministic-stage unit tests
```

## Tuning precision

When the daily queue is noisy, inspect a day (`--dry-run`) and either add the offending generic bigram to `suppress_phrases`, or `mute` a commitment/tema in the overlay. When a real match is missed, add a `boost` phrase to that commitment. No index rebuild is needed for overlay edits; rebuild only when the plan text changes.

## Reviewing a candidate issue

1. Read the norma (excerpt in the issue; full document via the El Peruano link) and confirm it actually cumple/avanza the compromiso.
2. If it holds: update `src/data/tracking.json` (status + evidence + log) on a `fix/` branch, `npm run validate`, PR, merge. The issue contains a ready-to-complete evidence block — write the `note` yourself.
3. Close the issue linking the PR, or with a comment explaining the discard.

## Known constraints / lessons

- The search page is **unofficial** and its markup can change. **History:** El Peruano exposed an unauthenticated GraphQL API (`/api/graphql`, `getGenericPublication`) until ~2026-07-26, when the site was rebuilt as a React Router app and that endpoint was removed (`404`) — the scraper failed daily 07-26…07-31 until repointed at the public search page (2026-07-31). If the card markup or the `?fechaIni&fechaFin&tipoPublicacion&start` params change, the run fails loudly in Actions — fix the parser in `parse_search_cards` and record the change here.
- **Editions:** the day's normas are split across three `tipoPublicacion` values — `NL` (Normas Legales), `BO` (Boletín Oficial), `PC` — so the fetch loops all three and de-dups by `op`. Verified 2026-07-31: the search page reproduces the 07-25 archive (183/183 real normas; the only diff was 2 op-less records in the old GraphQL data).
- **Norma text:** the `/dispositivo/<tipoPub>/<op>` page inlines the clean single-norma HTML in a `#visor-html` box; its `<head>` `<title>` belongs to a neighboring norma, so `html_to_text` strips the head. No PDF path anymore (the old per-norma `urlPDF` proxy is gone) — text extraction falls back to the sumilla when the box is absent.
- 483 normas on a sample day (2026-07-10), most municipal; the matcher's bigram index + `suppress_phrases` stoplist are what keep the queue relevant.
- Issues created by `GITHUB_TOKEN` don't trigger other workflows (GitHub policy) — irrelevant here.
- The archive push goes through `tools/ci/publish_data_branch.sh` (shared with the ultimitas scraper): a `git worktree` on the orphan `normas-archive` branch, so it never touches `main` (which is protected by the `protect-main` ruleset).
