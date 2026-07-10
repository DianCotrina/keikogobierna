# Workflow: Evidence Watcher

## Objective

Surface candidate evidence that a tracked commitment may have advanced, as GitHub issues for editorial review. The watcher never changes a status: `tracking.json` is only updated by a human through the PR flow, per the site's methodology.

## How it works

1. `.github/workflows/evidence-watcher.yml` runs daily (12:00 UTC ≈ 07:00 Lima) or on manual dispatch.
2. `tools/evidence_watcher.py` reads `tools/watcher_keywords.json` — an array of `{ "query", "related": [item ids] }`.
3. For each query it fetches Google News RSS scoped to Peru (`hl=es-419&gl=PE`), keeps entries from the last 7 days, and files one issue per new candidate (label `evidencia-candidata`), capped at 5 per run.
4. Dedup is stateless: each link gets a `[ev-<sha1 prefix>]` token in the issue title; the tool searches existing issues for the token before creating.

## Inputs

- `tools/watcher_keywords.json` — tune the watcher here. Add queries for commitments entering the news cycle; remove noisy ones. Keep `related` ids accurate (they land in the issue body).
- Env: `GITHUB_TOKEN` (issues: write), `GITHUB_REPOSITORY`.

## Local testing

```bash
python3 tools/evidence_watcher.py --dry-run   # prints candidates, no GitHub calls
```

## Reviewing a candidate issue

1. Verify the fact in an official source (El Peruano, MEF, INEI, Congreso) — press coverage alone never certifies.
2. If it holds: update `src/data/tracking.json` (status + evidence + log) on a `fix/` branch, `npm run validate`, PR, merge.
3. Close the issue linking the PR, or close with a comment explaining the discard.

## Known constraints / lessons

- Google News RSS titles carry a trailing « - Fuente» suffix; links are news.google.com redirects (fine for review).
- One failing query logs a warning and is skipped; the run only fails if every query fails.
- The 5-issue cap avoids flooding the tracker after a news spike; the next run picks up the remainder (dedup keeps it safe).
- Issues created by `GITHUB_TOKEN` do not trigger other workflows (GitHub policy) — irrelevant here, no workflow listens to issues.
