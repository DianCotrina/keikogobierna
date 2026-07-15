# Workflow: El Peruano Scraper

## Objective

Read the day's normas published in *El Peruano* (the primary source) and surface any that touch a tracked commitment as GitHub issues for editorial review. The reader never changes a status: `src/data/tracking.json` is only updated by a human through the PR flow.

This complements the [Evidence Watcher](evidence_watcher.md): El Peruano is the primary-source, high-precision stream; Google News is the broad-recall context stream. Both feed the same `evidencia-candidata` queue and share `tools/scrapers/watcher_keywords.json`.

## How it works

1. `.github/workflows/elperuano-scraper.yml` runs daily (13:00 UTC ≈ 08:00 Lima) or on manual dispatch.
2. `tools/scrapers/elperuano_scraper.py` runs three stages:
   - **Fetch** — GraphQL POST to `https://busquedas.elperuano.pe/api/graphql` (`getGenericPublication`), paginated over the day. Returns structured records `{tipo, numero, sector, sumilla, url_pdf, op, …}`.
   - **Keyword prefilter** — each norma's `numero + tipo + sumilla` is matched against the queries in `tools/scrapers/watcher_keywords.json` (accent/case-insensitive; ≥2 significant terms). A day with zero matches ends the run.
   - **Issues + archive** — one `evidencia-candidata` issue per surviving candidate (stateless `[np-<sha1>]` dedup token in the title, cap 10/run). Each issue embeds a text excerpt of the norma plus a ready-to-complete evidence JSON block. Text source chain: `https://busquedas.elperuano.pe/api/visor_html/<op>` (clean single-norma HTML, ~13KB, stdlib-stripped) → per-norma PDF via `pypdf` (page-scoped, may include fragments of neighboring normas) → sumilla. The day's full record set is appended to `normas/<date>.jsonl` on the `normas-archive` branch (a growing structured corpus for future analysis — not read by anything yet).

   There is **no AI stage** (a Claude judge existed briefly and was removed 2026-07-15 — decision: no API costs; deterministic scrapers + human review are enough).

## Inputs / config

- `tools/scrapers/watcher_keywords.json` — shared with the news watcher. Tune queries and `related` ids here.
- `tools/scrapers/elperuano_scraper.py` → `SKIP_TIPOS` — norma types to drop outright (empty by default; add municipal/local types if local noise appears); `EXCERPT_CHARS` — issue excerpt length.

## Local testing

```bash
python3 tools/scrapers/elperuano_scraper.py --dry-run                 # today, print records/matches, no writes
python3 tools/scrapers/elperuano_scraper.py --date 2026-07-10 --dry-run
python3 -m unittest discover -s tools/tests -p "test_*.py"        # deterministic-stage unit tests
```

## Reviewing a candidate issue

1. Read the norma (excerpt in the issue; full document via the El Peruano link) and confirm it actually cumple/avanza the compromiso.
2. If it holds: update `src/data/tracking.json` (status + evidence + log) on a `fix/` branch, `npm run validate`, PR, merge. The issue contains a ready-to-complete evidence block — write the `note` yourself.
3. Close the issue linking the PR, or with a comment explaining the discard.

## Known constraints / lessons

- The GraphQL API is **unofficial** (reverse-engineered from the site, 2026-07-12; introspection is enabled — 19 root queries, e.g. `getNormaPorOp`, `getCuadernillos`). If the endpoint, query name (`getGenericPublication`), or field names change, the run fails loudly in Actions — fix the tool and record the change here. The daily-PDF sumario parser is the documented fallback.
- **Document formats compared (2026-07-15):** the daily *cuadernillo* (booklet, ~150 pages/28MB) is the whole edition and would need fragile layout segmentation — not used. The per-norma PDF (`urlPDF`, ~400KB) is page-scoped and needs pypdf — fallback. `/api/visor_html/<op>` (~13KB) is the norma's clean single-norma HTML — primary text source. The site's "HTML" button is just a viewer page around that same endpoint (found via its `visor_id` iframe).
- `urlPDF` values point at a media proxy (`/api/media/...`) that serves the PDF regardless of the requested extension; occasionally a norma has no downloadable PDF or HTML rendition — text extraction falls back down the chain and ultimately to the sumilla.
- 483 normas on a sample day (2026-07-10), most municipal; the keyword filter is what keeps the queue relevant, so keyword quality matters more than any type allowlist.
- Issues created by `GITHUB_TOKEN` don't trigger other workflows (GitHub policy) — irrelevant here.
- The archive push goes through `tools/ci/publish_data_branch.sh` (shared with the ultimitas scraper): a `git worktree` on the orphan `normas-archive` branch, so it never touches `main` (which is protected by the `protect-main` ruleset).
