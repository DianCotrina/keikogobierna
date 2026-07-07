# Plan C — Tracking Workflow Implementation Plan

> **For agentic workers:** Read [EXECUTION-CONTEXT.md](EXECUTION-CONTEXT.md) first. REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** Make the tracker operable: a WAT tool that records status changes with evidence into `src/data/tracking.json`, a workflow document that defines the evidence standard, a `/registro/` page listing the full log, and the landing's updates section switching automatically from the empty state to real entries.

**Architecture:** Pure WAT: the workflow doc (`workflows/update_tracking.md`) is the SOP a human/agent follows; the tool (`tools/update_tracking.py`) is the only writer of tracking.json (hand edits remain possible but the tool guarantees shape, ordering, and validation); the site consumes the log at build time through the existing `updatesLog()`. No new runtime JS.

**Branch:** `tracking-workflow` off `main` (after PR #3; independent of Plans A/B, but if Plan A already landed remember all internal links go through `withBase()` and preview URLs live under `/keikogobierna/`).

## Global Constraints

- Everything in EXECUTION-CONTEXT.md. Two-layer rule and honest-data rule are load-bearing here.
- tracking.json contract (unchanged): `updated` (YYYY-MM-DD), `items` (id → `{status, evidence: []}`), `log` (entries `{date, item, status, text, source_url}`). Tool additions must preserve key order/indentation style (2-space, ensure_ascii=False, trailing newline) so diffs stay minimal.
- `log[].text` is user-facing Spanish (it renders on the site). `source_url` must be http(s).
- Evidence standard (bakes into the workflow doc): only publicly verifiable sources — El Peruano, MEF/consulta amigable, INEI, Congreso, official gazettes/portals; news media allowed only as secondary corroboration, never sole evidence for `fulfilled`/`unfulfilled`.
- Status semantics (workflow doc must state them): `in_progress` = concrete official action exists (norm published, budget assigned, contract signed); `fulfilled` = the goal/proposal's own success criterion met per its indicator; `unfulfilled` = deadline/term expired or officially cancelled; `no_progress` = default absence of evidence. Downgrades are allowed (history stays in `log`).
- The tool never deletes or rewrites existing log entries; it only appends and updates `items`. Corrections are new entries.
- CLAUDE.md rule stands: workflows are precious — this plan CREATES `workflows/update_tracking.md` with the user's blanket approval of this plan; future edits to it follow the CLAUDE.md rules.

## File Structure

```
tools/update_tracking.py         # NEW — the only sanctioned writer of tracking.json
workflows/update_tracking.md     # NEW — the SOP (Spanish content quotes, English prose ok — it's dev-facing: write it in English with Spanish examples)
tests/tracking.test.mjs          # NEW — fixture tests for updatesLog sorting + goalStats branches (closes deferred gap #4)
src/pages/registro.astro         # NEW — full log page
src/pages/index.astro            # updates section: real entries when log non-empty; + "Ver todo el registro" restored
src/lib/plan.mjs                 # if needed: nothing — updatesLog already exists; do not add speculative helpers
docs/ARCHITECTURE.md, CLAUDE.md  # workflow pointer + commands
```

### Tool CLI contract

```
python3 tools/update_tracking.py \
  --item t1-1.M02 \
  --status in_progress \
  --date 2026-08-01 \
  --text "Decreto publicado en El Peruano crea el programa C5i con presupuesto inicial." \
  --source-url "https://busquedas.elperuano.pe/..."
```

Behavior:
- Validates: item id exists in the plan tree (goals, proposals, or first-100-days ids — load them the same way the validator does); status in the canonical four; date matches `YYYY-MM-DD` and is not in the future (compare to today, local); text non-empty; source_url starts with http(s)://.
- Appends `{date, item, status, text, source_url}` to `log`; sets/creates `items[id] = {status, evidence: [...existing, source_url]}` (evidence de-duplicated, order preserved); sets top-level `updated` to today.
- Writes the file, then RUNS the validator (`tools/validate_plan_data.py`) as a subprocess; if the validator fails, restores the previous file content (keep a pre-write copy in memory) and exits 1 with the validator's message. Exit 0 prints one summary line: `OK: t1-1.M02 → in_progress (log #N)`.
- `--dry-run` flag prints the would-be entry and touches nothing.
- Stdlib only. Clean `FAIL:`-style errors, no tracebacks on bad input.

---

### Task 1: The tool + its negative tests

**Files:** create `tools/update_tracking.py`.

- [ ] **Step 1:** Implement per the contract.
- [ ] **Step 2:** Happy path on a THROWAWAY branch state: run once with a real goal id and a plausible official-source URL and TEST text, verify the diff (`git diff src/data/tracking.json`) shows exactly one log entry + items update + updated bump; then `git checkout -- src/data/tracking.json` (the repo's tracked data must stay empty of test entries — this plan ships an OPERABLE tool, not fake data).
- [ ] **Step 3:** Negative paths, each expecting clean FAIL + unchanged file: unknown id (`t9-9.M99`), bad status, future date, malformed date, empty text, `ftp://` URL, and a simulated validator failure (temporarily point `--item` at a proposal id AFTER hand-breaking the file? — simpler: monkey test by making tracking.json temporarily invalid JSON, expect the tool to fail cleanly before writing; restore).
- [ ] **Step 4:** `--dry-run` leaves file byte-identical (`git status --short` clean).
- [ ] **Step 5:** Commit: `feat: add update_tracking tool as sole writer of tracking state`.

### Task 2: Fixture tests for the lib's dormant branches

**Files:** create `tests/tracking.test.mjs`.

- [ ] **Step 1:** Using in-memory fixture objects (NOT the real files): `updatesLog` sorts multi-entry logs date-desc and is stable for equal dates (3 entries, two sharing a date — assert order); `goalStats` with a fixture goals array where some are fulfilled → correct byStatus + progressPct rounding (e.g., 2 of 3 fulfilled → 67); `goalStats` topicId filter with zero matching goals → `{total: 0, progressPct: 0}` without crash; `statusOf` on a tracking fixture with a proposal id present → returns its status (proves the topic-page stamp path).
- [ ] **Step 2:** `npm test` → all green (13 existing + new).
- [ ] **Step 3:** Commit: `test: cover updatesLog sorting and goalStats edge branches with fixtures`.

### Task 3: /registro page + landing integration

**Files:** create `src/pages/registro.astro`; modify `src/pages/index.astro`.

Registro page (design: same expediente/ledger language — consistent, not novel):
- Base layout; title `Registro de seguimiento — keikogobierna`; description Spanish (`Historial completo de actualizaciones del seguimiento del plan de gobierno 2026–2031, con evidencia.`).
- Masthead: breadcrumb "← Volver al tablero", mono eyebrow `REGISTRO · {N} ACTUALIZACIONES`, display heading "Registro de seguimiento", one serif line explaining every entry links its evidence.
- Entries grouped by month (Spanish month headings, e.g. "Agosto 2026", derived from `date`), newest first, each row: mono date, the entry `text`, `Stamp` of its status, and an evidence link "Ver evidencia →" (`source_url`, `rel="noopener"`, `target="_blank"`) plus a mono reference to the item id linking to its topic page anchor (`/temas/{slug}/#{item-id}` — add `id={goal.id}`/`id={proposal.id}` anchors to GoalRow and the proposal rows in `[slug].astro` if not present; check first).
- Empty state (log empty today): same honest sentence used on the landing, so the page ships working before data exists.

Landing updates section: when `updatesLog(tracking)` is non-empty render the latest 3 entries in the existing ledger-row style (date, text, stamp); always render the "Ver todo el registro" button → `/registro/` (restore it; it was removed while no destination existed) — use `withBase()` if Plan A already landed, raw `/registro/` otherwise (check `src/lib/url.mjs` existence).

- [ ] **Step 1:** Implement page + landing conditional + anchors.
- [ ] **Step 2:** Build → `dist/registro/index.html` exists with the empty state; landing has the button linking to it. Now the full-pipeline rehearsal: on the branch, run the Task-1 tool once with a real goal id and clearly-marked rehearsal text (`"[ENSAYO] Entrada de prueba del flujo de seguimiento."`), rebuild, and verify: landing shows the entry (empty state gone), registro shows it under the right month with stamp + evidence link, the topic page shows the goal's new stamp color, tracker card distribution shifts. Screenshot registro + landing updates section, VIEW them. Then revert the data (`git checkout -- src/data/tracking.json`) and rebuild — empty states return. This rehearsal is the acceptance test of the whole plan; capture it in the report.
- [ ] **Step 3:** `npm test` + `npm run validate` green; commit: `feat: add registro page and wire live updates into the landing`.

### Task 4: Workflow doc + docs ripple

**Files:** create `workflows/update_tracking.md`; modify `docs/ARCHITECTURE.md`, `CLAUDE.md`.

- [ ] **Step 1:** `workflows/update_tracking.md` — the SOP with: objective; when to record (any verifiable status change on a goal/proposal/100-days item); required inputs (item id — how to find it in `src/data/plan/`, status per the semantics table from Global Constraints, date of the OFFICIAL event not the recording date, Spanish one-sentence text written for site visitors, evidence URL per the evidence standard); exact tool invocation; post-steps (validator runs automatically; `npm run build` locally to eyeball; commit as `data: <item> → <status> (<short reason>)`; push via PR); edge cases (conflicting evidence → keep current status + log nothing until resolved; downgrade allowed with evidence; correction = new entry, never rewrite history).
- [ ] **Step 2:** ARCHITECTURE.md: tracking flow sentence + tool in the module map; CLAUDE.md: add the tool to Output Defaults data-edit guidance ("record status changes with tools/update_tracking.py per workflows/update_tracking.md — never hand-append log entries").
- [ ] **Step 3:** Commit: `docs: add update-tracking workflow and wire references`.

### Final

- [ ] Whole-branch review (most capable model): tool correctness is the risk center (it writes the public dataset) — reviewer independently runs the negative matrix and the rehearsal cycle; confirms tracked tracking.json in the final diff is UNCHANGED vs main (no rehearsal residue); visual gate on registro page.
- [ ] Push, open PR `Tracking workflow: recording tool, evidence SOP, and registro page`. Do not merge yourself.
