# Evidence watcher — candidate-evidence discovery

**Date:** 2026-07-10
**Status:** Approved by Diego ("proceed with 2 and 3", 2026-07-10)

## Problem

Keeping `tracking.json` current requires noticing when the government acts on a tracked promise. Certification stays human (editorial judgment over official sources), but *discovery* can be automated: a scheduled job that surfaces candidate evidence into the review queue.

## Design

**Discovery pipeline (v1): Google News RSS → GitHub issues.**

- **Source:** Google News RSS search (`news.google.com/rss/search?q=<query>&hl=es-419&gl=PE&ceid=PE:es-419`) — stable XML, no fragile scraping, Peru-scoped. Direct El Peruano/Congreso scrapers can be added later behind the same interface.
- **Keywords:** `tools/watcher_keywords.json` — hand-curated array of `{ "query": str, "related": [proposal/action ids] }`, seeded from first-100-days actions (the near-term commitments). Tuning the watcher = editing this file.
- **Tool:** `tools/evidence_watcher.py`, Python stdlib only (urllib, xml.etree, hashlib, json). For each query: fetch RSS, keep entries newer than 7 days, dedup, and file a GitHub issue per new candidate.
- **Dedup, stateless:** each candidate gets a stable token `[ev-<sha1(link)[:10]>]` in the issue title; before creating, the tool queries the GitHub search API for that token. No state file to commit (which branch protection would block anyway).
- **Issue format:** title `Evidencia candidata: <headline> [ev-…]`; body: link, publication date, matching query, related item ids, and a review checklist (verify against official sources → update `tracking.json` with evidence → close). Label `evidencia-candidata` (created by the tool if missing).
- **Noise control:** max 5 new issues per run; per-query failures logged and skipped (one bad feed never kills the run).
- **Schedule:** `.github/workflows/evidence-watcher.yml` — daily cron (12:00 UTC ≈ 07:00 Lima) + `workflow_dispatch` for manual runs; `permissions: issues: write`; auth via `GITHUB_TOKEN`.
- **Local dry-run:** `python3 tools/evidence_watcher.py --dry-run` prints candidates without touching GitHub (no token needed).
- **WAT doc:** `workflows/evidence_watcher.md` — purpose, how to tune keywords, failure modes, and the editorial rule: the watcher only *suggests*; states change exclusively through the human PR flow.

## Out of scope

- Automatic status changes (never).
- Direct official-source scrapers (later, same keyword config).
- Notifications beyond GitHub issues.

## Verification

- Local: `--dry-run` against the real config prints plausible candidates (or none) without errors.
- E2E after merge: one `workflow_dispatch` run; confirm issues appear with label + dedup token, and a second run creates no duplicates.
