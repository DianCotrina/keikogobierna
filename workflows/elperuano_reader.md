# Workflow: El Peruano Reader

## Objective

Read the day's normas published in *El Peruano* (the primary source) and surface any that touch a tracked commitment as GitHub issues for editorial review. The reader never changes a status: `src/data/tracking.json` is only updated by a human through the PR flow.

This complements the [Evidence Watcher](evidence_watcher.md): El Peruano is the primary-source, high-precision stream; Google News is the broad-recall context stream. Both feed the same `evidencia-candidata` queue and share `tools/scrapers/watcher_keywords.json`.

## How it works

1. `.github/workflows/elperuano-reader.yml` runs daily (13:00 UTC ≈ 08:00 Lima) or on manual dispatch.
2. `tools/scrapers/elperuano_reader.py` runs four stages:
   - **Fetch** — GraphQL POST to `https://busquedas.elperuano.pe/api/graphql` (`getGenericPublication`), paginated over the day. Returns structured records `{tipo, numero, sector, sumilla, url_pdf, …}`.
   - **Keyword prefilter** — each norma's `numero + tipo + sumilla` is matched against the queries in `tools/scrapers/watcher_keywords.json` (accent/case-insensitive; ≥2 significant terms). A day with zero matches ends at zero cost.
   - **Claude judge (optional)** — only if `ANTHROPIC_API_KEY` is set. For each matched norma it fetches the per-norma PDF, extracts the text (`pypdf`), and asks Claude (`claude-opus-4-8`, structured output) which commitments the norma implements/advances/mentions, with a ready-to-paste evidence draft. Without the key, issues are keyword-only.
   - **Issues + archive** — one `evidencia-candidata` issue per surviving candidate (stateless `[np-<sha1>]` dedup token in the title, cap 10/run); the day's full record set is appended to `normas/<date>.jsonl` on the `normas-archive` branch (a growing structured corpus for future analysis — not read by anything yet).

## Inputs / config

- `tools/scrapers/watcher_keywords.json` — shared with the news watcher. Tune queries and `related` ids here.
- `tools/scrapers/elperuano_reader.py` → `SKIP_TIPOS` — norma types to drop outright (empty by default; add municipal/local types if local noise appears).
- Repo secret `ANTHROPIC_API_KEY` — enables the judge (~$1–3/month at current Opus pricing). Absent ⇒ keyword-only, still useful.

## Local testing

```bash
python3 tools/scrapers/elperuano_reader.py --dry-run                 # today, print records/matches, no writes
python3 tools/scrapers/elperuano_reader.py --date 2026-07-10 --dry-run
ANTHROPIC_API_KEY=... python3 tools/scrapers/elperuano_reader.py --date 2026-07-10 --dry-run   # exercises the judge
python3 -m unittest discover -s tools/tests -p "test_*.py"        # deterministic-stage unit tests
```

## Reviewing a candidate issue

1. Read the norma (link in the issue) and confirm it actually cumple/avanza the compromiso — the judge suggests, it does not decide.
2. If it holds: update `src/data/tracking.json` (status + evidence + log) on a `fix/` branch, `npm run validate`, PR, merge. When the judge ran, the issue already contains a ready-to-paste evidence block.
3. Close the issue linking the PR, or with a comment explaining the discard.

## Known constraints / lessons

- The GraphQL API is **unofficial** (reverse-engineered from the site, 2026-07-12). If the endpoint, query name (`getGenericPublication`), or field names change, the run fails loudly in Actions — fix the tool and record the change here. The daily-PDF sumario parser is the documented fallback.
- `urlPDF` values point at a media proxy (`/api/media/...`); occasionally a norma has no downloadable PDF — the judge falls back to the sumilla and says so.
- 483 normas on a sample day (2026-07-10), most municipal; the keyword filter is what keeps the queue relevant, so keyword quality matters more than any type allowlist.
- Issues created by `GITHUB_TOKEN` don't trigger other workflows (GitHub policy) — irrelevant here.
- The archive push uses a `git worktree` on an orphan `normas-archive` branch so it never touches `main` (which is protected by the `protect-main` ruleset).
