# El Peruano reader — primary-source evidence pipeline

**Date:** 2026-07-10
**Status:** Design approved in conversation; plan review pending (Diego, 2026-07-10)

## Problem

The evidence watcher reads press coverage (Google News) — a delayed, noisy echo. El Peruano publishes the primary record daily: every ley, decreto and resolución, as born-digital PDFs (Normas Legales ~40–80 pages; Edición Extraordinaria when present; Boletín Oficial is legal notices — out of scope). Reading it directly upgrades discovery from "the news mentioned it" to "the state published it."

This is **not** classic RAG: there are no user questions over a corpus. It is reverse matching — 764 fixed commitments are the queries, the day's normas are the documents — plus editorial judgment, which stays human.

## Design — four-stage pipeline, one daily run

`tools/elperuano_reader.py` (new), scheduled by `.github/workflows/elperuano-reader.yml` (daily, after publication — 13:00 UTC ≈ 08:00 Lima; plus `workflow_dispatch`).

### Stage 1 — fetch (deterministic, GraphQL)

Reconnaissance (2026-07-12, verified live) found an unauthenticated GraphQL API at `https://busquedas.elperuano.pe/api/graphql`. The query `getGenericPublication(fechaIni, fechaFin, paginatedBy, start, tipoDispositivo, institucion, query, …)` returns structured per-norma records — no PDF parsing needed for discovery:

- POST the day's date range (`fechaIni == fechaFin == YYYYMMDD`); paginate over `hasNext` at `paginatedBy: 100`.
- Each hit → `{ tipo: tipoDispositivo, numero: nombreDispositivo, sector, rubro, sumilla, url_pdf: urlPDF, fecha: fechaPublicacion }`. The **sumilla** (official one-line summary) is the matching signal; `urlPDF` is a per-norma single-document link (used only by the optional judge).
- Verified: 483 hits for 2026-07-10, with sumillas and per-norma PDF links.
- Noise control: a national-government allowlist on `tipoDispositivo`/`sector` (skip municipal ordenanzas etc.), tunable in tool config.
- Tested against a committed real JSON response fixture (`tools/fixtures/graphql_sample.json`) — stdlib only, no PDF dependency at this stage.
- The daily-PDF sumario parser is kept as a documented fallback if the API changes (unofficial interface: a break fails the run loudly and we fix the tool, per the WAT loop). `pypdf` becomes a judge-stage-only dependency.

### Stage 2 — keyword prefilter (free gate)

- Match records against `tools/watcher_keywords.json` (shared with the news watcher; keys reused as plain keyword sets — query text minus operators) over **titulo + sumilla**. A day with zero matches ends the run at zero cost.

### Stage 3 — Claude judge (optional, graceful)

- Activates only when `ANTHROPIC_API_KEY` is set; otherwise the pipeline files keyword-only issues (Phase-1 behavior).
- For each matched norma: fetch its per-norma PDF from `url_pdf` and extract text with `pypdf` (small, single-document); if extraction fails, judge on the sumilla alone and note that in the issue. Call the Claude API (official Python SDK, `claude-opus-4-8`, adaptive thinking, structured output via `output_config.format` json_schema).
- Input: the norma text + the matched keywords' related commitments (full text of those ~5–20 commitments — no need for the whole corpus; prompt caching is useless at daily cadence given 5-min TTL).
- Output schema: `{ norma, commitment_id, relation: "implements"|"advances"|"mentions"|"unrelated", confidence: 0–1, rationale, evidence_draft: { date, source, url, note } }` — one entry per candidate pairing. `unrelated` verdicts are dropped.
- Cost reality (grounded 2026-06 pricing, Opus 4.8 $5/$25 per MTok): a few thousand tokens per triggered norma → cents per triggered day, realistically **$1–3/month**.

### Stage 4 — review queue (existing pattern)

- One GitHub issue per surviving candidate, label `evidencia-candidata`, stateless dedup token `[np-<sha1(norma id+date)>]` in the title (same mechanism as the news watcher).
- Issue body: norma (tipo/número/sector/título), El Peruano date + link, matched commitments; when the judge ran: relation + confidence + rationale + the **ready-to-paste evidence block** for `tracking.json`. Review checklist identical to the watcher's. The pipeline never changes a status.

### Archive (Phase-3 groundwork, cheap now)

- Each run appends the day's parsed records as JSONL and pushes to a **`normas-archive` branch** (rulesets protect only `main`; the workflow gets `contents: write`). Accumulates a structured corpus of government activity — the substrate for a future true RAG ("every norma touching MYPE since inauguración") without building any of that now.

## Relationship to the news watcher

Complementary streams into the same queue: El Peruano = primary-source (high precision), Google News = context (broad recall). Both tunable via `watcher_keywords.json`.

## Failure modes / maintenance

- El Peruano URL or layout changes → run fails loudly in Actions; fix the tool, record the lesson in `workflows/elperuano_reader.md` (WAT loop).
- Judge API errors → fall back to keyword-only issue for that norma (never lose a candidate to an API blip).
- Caps: max 10 issues/run; per-norma failures logged and skipped.

## Out of scope

- Automatic status changes (never).
- Boletín Oficial; scraping beyond the daily dispositivos page.
- RAG query interface over the archive (Phase 3, later).

## Verification

- Fixture test for the sumario parser (`node`-style: `python3 -m unittest` or plain assert script run in CI).
- Local end-to-end `--dry-run` against the real site: prints parsed records + matches, no GitHub/API calls.
- Judge stage tested once with the real key locally (`--judge-one <norma>`) before scheduling.
- Post-merge: `workflow_dispatch` run; verify issues + archive branch commit; second run verifies dedup.
