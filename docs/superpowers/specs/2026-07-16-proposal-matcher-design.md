# Proposal-derived commitment matcher (shared)

**Date:** 2026-07-16
**Status:** Design approved in conversation (Diego, 2026-07-16); spec review pending

## Problem

The El Peruano scraper matches each norma against **8 hand-written queries** in `tools/scrapers/watcher_keywords.json`. That covers a sliver of the plan and needs manual upkeep. Diego wants the scrapers to "search anything related to the proposals we already have listed" — match against the **764 commitments the plan already contains** (632 proposals + 67 first-100-days actions + 65 goals), automatically.

This matcher is the **foundation** for two later, source-specific specs (MEF adapter; Congreso adapter). Build order approved: matcher first (with El Peruano as its first consumer), then MEF, then Congreso — each its own spec/plan.

Hard constraints carried from the rest of the system: **no AI** (the Claude judge was removed 2026-07-15 — deterministic only), stdlib-only tools, and the scraper never changes `tracking.json`; it only files `evidencia-candidata` issues for human review.

## The precision problem

Commitment texts share generic government vocabulary — "programa nacional", "fortalecimiento", "implementación", "sistema", "gestión" appear across dozens of commitments and most normas. Naive term-overlap would flag nearly everything. The matcher must be **precise** (approved: favor precision — a short, high-confidence daily queue; some real evidence missed is acceptable, caught later by the news watcher or manual review).

## Design — distinctive-phrase index + shared matcher

Two deterministic pieces plus a migration, all stdlib-only.

### Component 1 — index builder: `tools/scrapers/build_commitment_index.py`

Reads the plan (`src/data/plan/topics/*.json` proposals + `first_100_days`; `src/data/plan/goals/goals-2031.json`) and writes a committed, human-readable `tools/scrapers/commitment_index.json`. Regenerated when the plan changes (rare — it's PDF-extracted), exactly like the plan data itself.

For each commitment:
- Normalize its text (reuse `watcher_common.normalize` — accent/case fold).
- Extract candidate terms: unigrams and bigrams, dropping stopwords (existing `STOPWORDS` set, moved to `watcher_common`) and tokens ≤3 chars.
- Weight by **document frequency** across all 764 commitments. A commitment's `phrases` are the ones distinctive enough to match *on their own*:
  - a **bigram** whose DF ≤ `DF_MAX_BIGRAM` (bigrams are naturally distinctive — e.g. "unidades de flagrancia", "ventanilla unica consular"), or
  - a **unigram** whose DF ≤ `DF_MAX_UNIGRAM` — a strict cutoff that keeps only rare, load-bearing single words ("flagrancia", "c5i") and drops generic ones ("programa", "nacional").

Output shape (sorted, stable — reviewable in PRs):
```json
{
  "generated": "2026-07-16",
  "params": { "df_max_unigram": 3, "df_max_bigram": 12 },
  "commitments": {
    "t1-1.C02": { "phrases": ["flagrancia", "unidades de flagrancia"] },
    "t3-10.C01": { "phrases": ["ventanilla unica consular", "consular"] }
  }
}
```
A `--check` flag regenerates in-memory and exits non-zero if the committed file is stale (CI runs it, same idea as `npm run validate`). Commitments that end up with **zero phrases** (their vocabulary was all generic) are reported by the builder and listed in the SOP — they simply won't auto-match until hand-boosted (see overlay).

### Component 2 — hand-tune overlay: `tools/scrapers/commitment_overlay.json`

Small, curated, where the existing 8 keyword queries' knowledge migrates:
```json
{
  "boost": { "t1-1.C01": ["c5i", "seguridad ciudadana"] },
  "suppress_terms": ["comuniquese", "registrese", "publiquese"],
  "mute_commitments": ["t2-3.P14"]
}
```
`boost` adds phrases to a commitment (acronyms/terms the plan text spells differently than the news); `suppress_terms` are extra global noise words; `mute_commitments` silences a commitment that keeps producing false positives. Applied on top of the generated index at load time.

### Component 3 — the matcher: `tools/scrapers/matcher.py`

```python
load_index(path=..., overlay=...) -> Matcher      # builds phrase -> ids map once
Matcher.match(text: str) -> list[str]             # sorted, unique commitment ids
```
`match` normalizes the input, then a commitment matches when the text contains **≥1 of its `phrases`**. Because every phrase already had to clear the distinctiveness cutoff to be in the index, a single hit is a high-precision signal — no counting or thresholds at match time. Bigrams carry most matches; only rare single words qualify as solo phrases. Returns the related commitment ids. This is the single place matching logic lives; every source adapter (El Peruano now; MEF, Congreso later) calls it.

### Component 4 — El Peruano migration

`tools/scrapers/elperuano_scraper.py`:
- `run()` loads the matcher (index + overlay) instead of `watcher_keywords.json`.
- Replace the local `match_record(record, keywords)` and `significant_terms` with `matcher.match(f"{numero} {tipo} {sumilla}")`; delete the now-unused `STOPWORDS` copy (moved to `watcher_common`).
- Everything downstream is unchanged: the matched commitment ids flow into the same `issue_body`, dedup token, excerpt, archive.

**Scope boundary — the news watcher keeps `watcher_keywords.json`.** `evidence_watcher.py` is a *search* source: it sends query strings to Google News RSS, it does not match a document stream. That's a fundamentally different mechanism, so it keeps its curated queries. The matcher is only for document-stream sources (El Peruano, and the coming MEF/Congreso adapters). This split is stated in the SOP.

## Testing (real data, per Diego's preference)

- `tools/tests/test_matcher.py` against a small fixture cut from the **real plan** (`tools/tests/fixtures/commitment_index_sample.json`, generated from actual commitments): distinctive-phrase extraction (a distinctive term survives, a generic one is dropped), single-phrase matching, accent/case folding, overlay boost/suppress/mute, empty-input safety.
- Builder `--check` in CI (added to `.github/workflows/ci.yml` unittest step region) guarantees the committed index never drifts from the plan.
- Verification (in the plan, not committed): dry-run the migrated El Peruano scraper over several real days and confirm the queue stays small (target ≤~15 matched/day over ~600 normas) and that known cases (a flagrancia/Tumbes norma) match the right ids; tune `DF_MAX` / `mute` until precision holds.

## Failure modes / maintenance

- Plan changes → rerun `build_commitment_index.py`; CI `--check` catches a forgotten regen.
- A commitment over-matches → add it to `mute_commitments` or tighten `DF_MAX`.
- A real match missed → add a `boost` phrase, or accept it (news watcher/manual catch it) — precision is the chosen bias.

## Out of scope (own specs)

- **MEF adapter** (gob.pe HTML listing; note: MEF normas already appear in El Peruano — value is cleaner titles + institution scoping).
- **Congreso adapter(s)** (control-político; mociones + pedidos are `api.congreso.gob.pe` apps needing endpoint discovery; three sections are static pages).
- The news watcher's search-query mechanism (unchanged here).
- Any automatic `tracking.json` change (never).

## Decisions log (conversation, 2026-07-16)

- Matching source: the 764 existing plan commitments, not hand-written queries ("search anything related to the proposals we already have listed").
- Approach: distinctive-phrase index (document-frequency weighting) over naive overlap or a 764-entry hand file.
- Architecture: one shared matcher; sources are thin adapters; El Peruano migrates onto it first.
- Build order: matcher (+ El Peruano) → MEF → Congreso, each its own spec.
- Precision over recall: short high-confidence daily queue; misses are acceptable.
- Output unchanged: `evidencia-candidata` issues for human review; statuses change only via PR.
