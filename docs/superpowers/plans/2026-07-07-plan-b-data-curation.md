# Plan B — Data Curation & Validator Hardening Implementation Plan

> **For agentic workers:** Read [EXECUTION-CONTEXT.md](EXECUTION-CONTEXT.md) first. REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox syntax.

**Goal:** Fix the two source-PDF extraction artifacts (`t3-7.P17` stub proposal, `t2-6.P15` glued group header) through a deterministic overrides mechanism in the extractor — never by hand-editing generated files — and harden the validator per the outstanding review recommendations.

**Architecture:** A new `src/data/plan/overrides.json` holds explicit, typed curation rules. `tools/extract_plan_pdf.py` applies them AFTER raw extraction and BEFORE writing output, keeping two count gates: the raw-extraction gate (unchanged, proves parsing fidelity to the PDF) and a new post-override gate (proves curation did exactly what the rules say). Regeneration stays byte-deterministic.

**ID-stability ruling (project decision, already made):** proposal renumbering is permitted ONLY while `src/data/tracking.json` contains no proposal ids (true today — items are all `.M` goals). This plan performs the one renumbering that curation requires; after it lands, proposal IDs are frozen like all others. The plan must ABORT (escalate to the user) if tracking.json contains any `.P` or `.C` id at execution time.

**Branch:** `data-curation` off `main` (after PR #3 is merged).

## Global Constraints

- Everything in EXECUTION-CONTEXT.md (language policy, determinism, validator-after-every-data-edit, commit rules).
- The two defects, precisely:
  1. **t3-7 (Pensiones):** the document's second "Programa Juntos:" block uses nested `•` bullets where sibling blocks use `-`, so raw extraction yields a bare-label proposal `t3-7.P17` ("Programa Juntos:") followed by 3 fragment proposals (P18–P20) that are really its sub-items. Correct content: ONE proposal whose text is the label + its sub-items joined (`"Programa Juntos: <item1>; <item2>; <item3>"` — join with `"; "`, strip trailing periods of fragments except keep the final one). Result: t3-7 has 18 proposals (P17 is the merged one; old P21 becomes P18... i.e., ordinals recompacted), totals drop 635 → 632.
  2. **t2-6 (Transportes y comunicaciones):** proposal `t2-6.P15` text ends with a glued section header: `"… Impulso del cabotaje nacional. Aeroportuaria"`. Correct content: P15 text ends at `"…cabotaje nacional."` and a NEW group titled `"Aeroportuaria"` starts with the following proposal (P16, currently first item of what should be the Aeroportuaria group — today it sits in the previous group). Count unchanged (41), group structure gains one group.
- Raw-extraction EXPECTED constants in the extractor MUST NOT change (t3-7 raw is still 21). New POST-override expected table: identical except t3-7 → 18; totals 632 proposals / 67 first-100-days.
- Ripple updates required wherever 635 appears as a fact: `docs/ARCHITECTURE.md` (counts), `CLAUDE.md` if mentioned, `src/data/plan/index.json` (regenerated), tests if they assert totals. The landing computes its number, so it updates itself — verify it shows 632 after rebuild.
- Do not touch: goals file (65 stays), tracking.json contents, page components (except none should be needed).

## File Structure

```
src/data/plan/overrides.json     # NEW — typed curation rules (committed, hand-written)
tools/extract_plan_pdf.py        # MODIFIED — apply_overrides() stage + post-override gate
src/data/plan/index.json         # regenerated (t3-7 proposals: 18)
src/data/plan/topics/t3-7-pensiones.json                    # regenerated
src/data/plan/topics/t2-6-transportes-y-comunicaciones.json # regenerated
tools/validate_plan_data.py      # MODIFIED — goals indicator/table_topic hardening
docs/ARCHITECTURE.md             # counts 635→632 where stated
```

### overrides.json contract

```json
{
  "rules": [
    {
      "type": "merge_bullets",
      "topic": "3.7",
      "anchor_starts_with": "Programa Juntos:",
      "merge_count": 4,
      "join_with": "; ",
      "note": "Source PDF uses nested bullets inconsistently; the 3 items after the label are sub-items."
    },
    {
      "type": "split_trailing_group_header",
      "topic": "2.6",
      "proposal_ends_with": "Impulso del cabotaje nacional. Aeroportuaria",
      "header": "Aeroportuaria",
      "note": "Section header glued onto the previous proposal by missing blank line in the PDF text layer."
    }
  ]
}
```

Semantics (implement in the extractor, English identifiers):
- `merge_bullets`: within the named topic's ordered proposal stream (pre-ID assignment), find the proposal whose ENTIRE text equals `anchor_starts_with` (bare-label match — general prefix matching would be ambiguous in t3-7, where a second proposal shares the label prefix); replace it and the following `merge_count - 1` proposals with ONE proposal: anchor text + `join_with` + each following text (strip one trailing `.` from all but the last joined fragment; ensure exactly one space after the label's colon). The merged proposal stays in the anchor's group position.
- `split_trailing_group_header`: find the proposal whose text ends with `proposal_ends_with`; truncate its text to end just before ` {header}` (result must end with `.`); start a NEW group titled `header` immediately after it; all subsequent proposals of the ORIGINAL group move into the new group (until the next group boundary as raw-extracted).
- Rules apply in file order, after raw extraction and its gate, before ID assignment (so ordinals come out compact) and before writing files.
- Unknown `type`, zero matches, or >1 match for any rule ⇒ hard error (exit 1) with a clear message — silent no-ops are forbidden.

---

### Task 0 (gate): Preconditions

- [ ] Verify PR #3 merged into main and branch created from fresh main.
- [ ] Verify tracking has no proposal/first-100-days ids: `python3 -c "import json; items=json.load(open('src/data/tracking.json'))['items']; bad=[k for k in items if '.P' in k or '.C' in k]; print('OK' if not bad else f'ABORT {bad}')"` → OK. If ABORT: stop, report to the user (the ID-stability window has closed; curation then needs a tombstone design instead).

### Task 1: Overrides mechanism in the extractor

**Files:** Create `src/data/plan/overrides.json` (exact content above). Modify `tools/extract_plan_pdf.py`.

- [ ] **Step 1:** Implement `load_overrides()` + `apply_overrides(topics_raw, rules)` per the semantics above; wire between the raw gate and ID assignment. Add POST-override expected table (module constant `EXPECTED_CURATED = {**EXPECTED, "3.7": 18}`) and a second self-check printing both tables; exit 1 on either mismatch.
- [ ] **Step 2:** Run `python3 tools/extract_plan_pdf.py` → both gates pass; totals line shows raw 635 → curated 632.
- [ ] **Step 3:** Read the two regenerated topic files and verify by eye: t3-7 has 18 proposals, P17 text is `"Programa Juntos: …; …; …"` (one complete sentence-like entry, no bare label, subsequent ordinals compact to P18); t2-6 has an `"Aeroportuaria"` group whose first proposal is the aeropuerto Jorge Chávez item, and P15 ends with `"cabotaje nacional."`. Compare against the PDF text (pages ~63–65 for 2.6, ~117–118 for 3.7 via `pdftotext -layout docs/Plan-de-Gobierno-Reforzado_V2.pdf -`) to confirm content fidelity.
- [ ] **Step 4:** Determinism: run twice, `git status --short src/data/plan` unchanged between runs. Negative test: temporarily change `merge_count` to 5 → clean hard error; restore.
- [ ] **Step 5:** `npm run validate` (index counts must reconcile — the extractor regenerates index.json), `npm test`, `npm run build`; grep `dist/index.html` for `632` (landing recomputed itself).
- [ ] **Step 6:** Commit: `feat: add curation overrides fixing t3-7 merge and t2-6 group header` (stage overrides.json, extractor, regenerated index + 2 topic files).

### Task 2: Validator hardening

**Files:** Modify `tools/validate_plan_data.py`.

- [ ] **Step 1:** In the goals checks add: `indicator` present, string, non-empty after strip; `table_topic` present, string, non-empty. Clean `FAIL:` messages naming the goal id. Follow the existing guard style (isinstance before subscript).
- [ ] **Step 2:** `npm run validate` → OK. Negative tests: blank an `indicator` in a temp-modified copy path (edit, run, expect FAIL, `git checkout -- src/data/plan/goals`), same for `table_topic`.
- [ ] **Step 3:** Commit: `fix: validate goal indicator and table_topic non-emptiness`.

### Task 3: Documentation ripple

**Files:** Modify `docs/ARCHITECTURE.md` (every stated 635 → 632, note the overrides stage in the extraction workflow sentence + one line on the frozen-IDs ruling), check `CLAUDE.md` for count mentions (update if any).

- [ ] **Step 1:** `grep -rn "635" docs/ARCHITECTURE.md CLAUDE.md README.md` → update hits (plans/ historical docs stay as written).
- [ ] **Step 2:** Add to ARCHITECTURE.md Plan-data section: overrides.json exists, applied by the extractor, and the ID-freeze ruling ("proposal IDs frozen as of the curation commit; tracking may reference them").
- [ ] **Step 3:** Commit: `docs: reflect curated counts and overrides mechanism`.

### Final

- [ ] Whole-branch review (most capable model): diff vs main; executable checks (both extractor gates, validate, test, build, dist grep 632, determinism); confirm no other topic's content changed byte-wise except the two curated files + index.
- [ ] Push, open PR titled `Data curation: fix the two source-PDF artifacts via extractor overrides`; body lists the two fixes, the 635→632 change and why, the ID-freeze ruling. Do not merge it yourself.
