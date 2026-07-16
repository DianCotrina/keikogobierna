# Proposal-derived commitment matcher — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Match every El Peruano norma against the plan's own 764 commitments via a deterministic distinctive-phrase index, replacing the 8 hand-written keyword queries, and label the resulting review issues by tema.

**Architecture:** An offline builder reads the plan and emits a committed `commitment_index.json` of distinctive phrases per commitment. A shared `matcher.py` loads it (+ a hand overlay) and matches on filtered-token subsequences. The El Peruano scraper migrates onto the matcher and adds `tema:<slug>` labels. No AI; stdlib only.

**Tech Stack:** Python 3.9+ stdlib, unittest, GitHub Actions.

## Global Constraints

- Branch `feat/proposal-matcher` (exists; spec committed). Conventional commits; rebase-only merges.
- **Stdlib only**; every new/modified Python file keeps `from __future__ import annotations` where it uses `X | None`.
- **No AI** anywhere. Scraper never edits `tracking.json` — files `evidencia-candidata` issues only.
- Spanish for anything user/issue-facing; English for code/commits.
- Tests run via `python3 -m unittest discover -s tools/tests -p "test_*.py"` (CI already runs this).
- Matching model (canonical, used by builder AND matcher): normalize (accent/case fold via `watcher_common.normalize`), split, drop `STOPWORDS` and tokens ≤3 chars → a **filtered token list**. A commitment's phrases are unigrams and *adjacent* bigrams over that list. A norma matches a phrase when the phrase appears among the norma's own unigrams+adjacent-bigrams. This makes `"unidades flagrancia"` match "unidades **de** flagrancia".

---

### Task 1: Shared tokenization primitives in `watcher_common`

Move `STOPWORDS` out of the scraper and add the two functions the builder and matcher both need, so the model lives in one place.

**Files:**
- Modify: `tools/scrapers/watcher_common.py`
- Test: `tools/tests/test_watcher_common.py`

**Interfaces:**
- Produces: `watcher_common.STOPWORDS: set[str]`; `significant_tokens(text, extra_stop=frozenset()) -> list[str]`; `phrases_of(tokens) -> set[str]` (unigrams ∪ adjacent bigrams).

- [ ] **Step 1: Failing tests** — append to `tools/tests/test_watcher_common.py`:

```python
from watcher_common import significant_tokens, phrases_of


class TokenizeTest(unittest.TestCase):
    def test_drops_stopwords_short_and_folds_accents(self):
        self.assertEqual(significant_tokens("de la MYPE en el Perú"), ["mype", "peru"])

    def test_extra_stop_removes_extra_terms(self):
        self.assertEqual(significant_tokens("comuniquese y publiquese la ley",
                                            extra_stop={"comuniquese", "publiquese"}), ["ley"])

    def test_phrases_are_unigrams_and_adjacent_bigrams(self):
        self.assertEqual(
            phrases_of(["unidades", "flagrancia", "express"]),
            {"unidades", "flagrancia", "express", "unidades flagrancia", "flagrancia express"},
        )

    def test_bigram_survives_dropped_stopword(self):
        # "unidades de flagrancia" -> de dropped -> adjacent bigram bridges the gap
        self.assertIn("unidades flagrancia", phrases_of(significant_tokens("unidades de flagrancia")))
```

- [ ] **Step 2: Run, expect fail** — `python3 -m unittest tools.tests.test_watcher_common -v` → ImportError.

- [ ] **Step 3: Implement** — in `tools/scrapers/watcher_common.py`, after `normalize`:

```python
STOPWORDS = {
    "de", "la", "el", "en", "y", "para", "con", "los", "las", "del", "por",
    "un", "una", "que", "a", "su", "se", "al", "o", "e", "sus", "es",
}


def significant_tokens(text: str, extra_stop: frozenset = frozenset()) -> list[str]:
    """Normalized tokens minus stopwords and tokens <= 3 chars."""
    return [t for t in normalize(text).split()
            if len(t) > 3 and t not in STOPWORDS and t not in extra_stop]


def phrases_of(tokens: list[str]) -> set[str]:
    """Unigrams plus adjacent bigrams over a filtered token list."""
    out = set(tokens)
    out.update(f"{a} {b}" for a, b in zip(tokens, tokens[1:]))
    return out
```

- [ ] **Step 4: Run, expect pass** — same command → OK.

- [ ] **Step 5: Commit** — `git add tools/scrapers/watcher_common.py tools/tests/test_watcher_common.py && git commit -m "feat: shared tokenization primitives in watcher_common"`

---

### Task 2: Index builder + generated `commitment_index.json`

**Files:**
- Create: `tools/scrapers/build_commitment_index.py`
- Create: `tools/scrapers/commitment_index.json` (generated, committed)
- Test: `tools/tests/test_build_commitment_index.py`

**Interfaces:**
- Consumes: `watcher_common.significant_tokens`, `phrases_of`.
- Produces: `load_commitments() -> dict[str, dict]` (id → {"text", "tema"}); `load_temas() -> dict[str, str]` (tema id → slug); `build_index(commitments, temas) -> dict`; constants `DF_MAX_UNIGRAM=3`, `DF_MAX_BIGRAM=12`. Index shape: `{"generated","params","temas":{id:slug},"commitments":{cid:{"phrases":[...]}}}`. CLI: `--check` (exit 1 if committed file stale), `--report` (print zero-phrase commitments).

- [ ] **Step 1: Failing tests** — `tools/tests/test_build_commitment_index.py`:

```python
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scrapers"))
import build_commitment_index as b


class BuildIndexTest(unittest.TestCase):
    COMMITMENTS = {
        "t1-1.C02": {"text": "Creación de unidades de flagrancia express", "tema": "t1-1"},
        "t1-1.C04": {"text": "Compra de patrulleros con cámaras inteligentes", "tema": "t1-1"},
        "t2-1.P01": {"text": "Programa nacional de fortalecimiento", "tema": "t2-1"},
        "t2-2.P01": {"text": "Programa nacional de vivienda", "tema": "t2-2"},
        "t2-3.P01": {"text": "Programa nacional de empleo", "tema": "t2-3"},
    }
    TEMAS = {"t1-1": "orden-ciudadano", "t2-1": "a", "t2-2": "b", "t2-3": "c"}

    def test_distinctive_phrases_survive_generic_dropped(self):
        idx = b.build_index(self.COMMITMENTS, self.TEMAS)
        c = idx["commitments"]
        self.assertIn("flagrancia", c["t1-1.C02"]["phrases"])
        self.assertIn("unidades flagrancia", c["t1-1.C02"]["phrases"])
        # "programa"/"nacional" appear in 3 commitments -> generic -> dropped everywhere
        self.assertNotIn("programa", c["t2-1.P01"]["phrases"])
        self.assertNotIn("nacional", c["t2-1.P01"]["phrases"])

    def test_temas_map_and_structure(self):
        idx = b.build_index(self.COMMITMENTS, self.TEMAS)
        self.assertEqual(idx["temas"]["t1-1"], "orden-ciudadano")
        self.assertEqual(set(idx["params"]), {"df_max_unigram", "df_max_bigram"})

    def test_committed_index_is_in_sync_with_plan(self):
        # the real generated file must match a fresh build (the CI --check invariant)
        fresh = b.build_index(b.load_commitments(), b.load_temas())
        import json
        committed = json.loads((Path(b.__file__).resolve().parent / "commitment_index.json").read_text())
        self.assertEqual(committed["commitments"], fresh["commitments"])
        self.assertEqual(committed["temas"], fresh["temas"])
```

- [ ] **Step 2: Run, expect fail** — module missing.

- [ ] **Step 3: Implement** — `tools/scrapers/build_commitment_index.py`:

```python
#!/usr/bin/env python3
"""Build the distinctive-phrase index the matcher uses, from the plan's commitments.

Reads src/data/plan (proposals + first_100_days + goals-2031), keeps each
commitment's phrases (unigrams/adjacent-bigrams) that are rare across all
commitments, and writes tools/scrapers/commitment_index.json. Regenerate when
the plan changes; CI --check guards against drift. Stdlib only.

Usage:
  python3 tools/scrapers/build_commitment_index.py            # regenerate the file
  python3 tools/scrapers/build_commitment_index.py --check    # exit 1 if stale
  python3 tools/scrapers/build_commitment_index.py --report   # list zero-phrase commitments
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from watcher_common import phrases_of, significant_tokens

ROOT = Path(__file__).resolve().parent.parent.parent
PLAN = ROOT / "src" / "data" / "plan"
INDEX_PATH = Path(__file__).resolve().parent / "commitment_index.json"
DF_MAX_UNIGRAM = 3
DF_MAX_BIGRAM = 12


def load_temas() -> dict[str, str]:
    return {json.loads(p.read_text())["id"]: json.loads(p.read_text())["slug"]
            for p in sorted((PLAN / "topics").glob("*.json"))}


def load_commitments() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in sorted((PLAN / "topics").glob("*.json")):
        topic = json.loads(p.read_text())
        for group in topic.get("groups", []):
            for prop in group.get("proposals", []):
                out[prop["id"]] = {"text": prop["text"], "tema": topic["id"]}
        for action in topic.get("first_100_days", []):
            out[action["id"]] = {"text": action["text"], "tema": topic["id"]}
    goals = json.loads((PLAN / "goals" / "goals-2031.json").read_text())
    for goal in goals["goals"]:
        out[goal["id"]] = {"text": goal["text"], "tema": goal["topic"]}
    return out


def _candidate_phrases(text: str) -> tuple[set[str], set[str]]:
    """(unigrams, bigrams) for one commitment."""
    toks = significant_tokens(text)
    unis = set(toks)
    bis = {f"{a} {b}" for a, b in zip(toks, toks[1:])}
    return unis, bis


def build_index(commitments: dict[str, dict], temas: dict[str, str]) -> dict:
    per: dict[str, tuple[set[str], set[str]]] = {c: _candidate_phrases(v["text"]) for c, v in commitments.items()}
    df: Counter = Counter()
    for unis, bis in per.values():
        df.update(unis | bis)  # document frequency: how many commitments contain each phrase

    out_commitments: dict[str, dict] = {}
    for cid, (unis, bis) in per.items():
        phrases = sorted(
            {u for u in unis if df[u] <= DF_MAX_UNIGRAM}
            | {bg for bg in bis if df[bg] <= DF_MAX_BIGRAM}
        )
        out_commitments[cid] = {"phrases": phrases}

    return {
        "generated": date.today().isoformat(),
        "params": {"df_max_unigram": DF_MAX_UNIGRAM, "df_max_bigram": DF_MAX_BIGRAM},
        "temas": dict(sorted(temas.items())),
        "commitments": dict(sorted(out_commitments.items())),
    }


def _dump(index: dict) -> str:
    return json.dumps(index, ensure_ascii=False, indent=1) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed index is stale")
    ap.add_argument("--report", action="store_true", help="list commitments with zero phrases")
    args = ap.parse_args()

    index = build_index(load_commitments(), load_temas())

    if args.report:
        empty = [c for c, v in index["commitments"].items() if not v["phrases"]]
        print(f"{len(empty)} of {len(index['commitments'])} commitments have zero phrases:")
        for c in empty:
            print(" ", c)
        return 0

    if args.check:
        current = INDEX_PATH.read_text() if INDEX_PATH.exists() else ""
        fresh = _dump(index)
        # compare on content, ignoring the generated date
        import copy
        a = json.loads(current or "{}"); a.pop("generated", None)
        b = copy.deepcopy(index); b.pop("generated", None)
        if a != b:
            print("ERROR: commitment_index.json is stale; run build_commitment_index.py", file=sys.stderr)
            return 1
        print("commitment_index.json is in sync.")
        return 0

    INDEX_PATH.write_text(_dump(index), encoding="utf-8")
    print(f"Wrote {INDEX_PATH.name}: {len(index['commitments'])} commitments.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Generate the real index** — `python3 tools/scrapers/build_commitment_index.py` then `python3 tools/scrapers/build_commitment_index.py --report` (note zero-phrase count for the SOP).

- [ ] **Step 5: Run tests, expect pass** — `python3 -m unittest tools.tests.test_build_commitment_index -v`.

- [ ] **Step 6: Commit** — `git add tools/scrapers/build_commitment_index.py tools/scrapers/commitment_index.json tools/tests/test_build_commitment_index.py && git commit -m "feat: distinctive-phrase index builder from plan commitments"`

---

### Task 3: The matcher + overlay

**Files:**
- Create: `tools/scrapers/matcher.py`
- Create: `tools/scrapers/commitment_overlay.json`
- Test: `tools/tests/test_matcher.py`

**Interfaces:**
- Consumes: index (Task 2), `watcher_common.significant_tokens`/`phrases_of`.
- Produces: `load_matcher(index_path=INDEX_PATH, overlay_path=OVERLAY_PATH) -> Matcher`; `Matcher.match(text) -> list[str]` (sorted commitment ids); `Matcher.tema_slug(commitment_id) -> str`.

- [ ] **Step 1: Overlay file** — `tools/scrapers/commitment_overlay.json`:

```json
{
  "boost": { "t1-1.C01": ["c5i"] },
  "suppress_terms": ["comuniquese", "registrese", "publiquese", "cumplase"],
  "mute_commitments": []
}
```

- [ ] **Step 2: Failing tests** — `tools/tests/test_matcher.py`:

```python
import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scrapers"))
import matcher as m

INDEX = {
    "temas": {"t1-1": "orden-ciudadano", "t3-10": "peruanos-exterior"},
    "commitments": {
        "t1-1.C02": {"phrases": ["flagrancia", "unidades flagrancia"]},
        "t3-10.C01": {"phrases": ["ventanilla consular", "consular"]},
        "t1-1.C99": {"phrases": ["publiquese"]},
    },
}
OVERLAY = {"boost": {"t1-1.C01": ["c5i"]}, "suppress_terms": ["publiquese"], "mute_commitments": ["t3-10.C01"]}


def _write(tmp, name, obj):
    p = Path(tmp) / name
    p.write_text(json.dumps(obj), encoding="utf-8")
    return p


class MatcherTest(unittest.TestCase):
    def _matcher(self, tmp):
        return m.load_matcher(_write(tmp, "i.json", INDEX), _write(tmp, "o.json", OVERLAY))

    def test_bigram_matches_across_dropped_stopword(self):
        with tempfile.TemporaryDirectory() as tmp:
            mt = self._matcher(tmp)
            self.assertEqual(mt.match("Autorizan unidades de flagrancia en Lima"), ["t1-1.C02"])

    def test_accent_and_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).match("Sobre FLAGRANCIA policial"), ["t1-1.C02"])

    def test_boost_adds_phrase(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).match("Sistema C5i nacional"), ["t1-1.C01"])

    def test_mute_removes_commitment(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).match("Nueva ventanilla consular"), [])

    def test_suppress_term_never_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).match("Registrese y publiquese"), [])

    def test_tema_slug_from_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).tema_slug("t1-1.C02"), "orden-ciudadano")

    def test_no_match_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._matcher(tmp).match("Feria dominical de artesanos"), [])
```

- [ ] **Step 3: Run, expect fail** — module missing.

- [ ] **Step 4: Implement** — `tools/scrapers/matcher.py`:

```python
#!/usr/bin/env python3
"""Match free text against the plan's commitments via the distinctive-phrase index.

Single place matching lives; every document-stream source (El Peruano now) calls
it. Deterministic, stdlib only. See workflows/elperuano_scraper.md.
"""
from __future__ import annotations

import json
from pathlib import Path

from watcher_common import phrases_of, significant_tokens

INDEX_PATH = Path(__file__).resolve().parent / "commitment_index.json"
OVERLAY_PATH = Path(__file__).resolve().parent / "commitment_overlay.json"


class Matcher:
    def __init__(self, phrase_to_ids: dict[str, set[str]], temas: dict[str, str], suppress: frozenset):
        self._phrase_to_ids = phrase_to_ids
        self._temas = temas
        self._suppress = suppress

    def match(self, text: str) -> list[str]:
        present = phrases_of(significant_tokens(text, extra_stop=self._suppress))
        ids: set[str] = set()
        for phrase in present:
            ids |= self._phrase_to_ids.get(phrase, set())
        return sorted(ids)

    def tema_slug(self, commitment_id: str) -> str:
        return self._temas.get(commitment_id.split(".")[0], "")


def load_matcher(index_path: Path = INDEX_PATH, overlay_path: Path = OVERLAY_PATH) -> Matcher:
    index = json.loads(Path(index_path).read_text())
    overlay = json.loads(Path(overlay_path).read_text()) if Path(overlay_path).exists() else {}
    suppress = frozenset(overlay.get("suppress_terms", []))
    muted = set(overlay.get("mute_commitments", []))

    phrase_to_ids: dict[str, set[str]] = {}
    for cid, entry in index["commitments"].items():
        if cid in muted:
            continue
        for phrase in entry["phrases"]:
            phrase_to_ids.setdefault(phrase, set()).add(cid)
    # boost: add hand-curated phrases (normalized through the same pipeline)
    for cid, phrases in overlay.get("boost", {}).items():
        if cid in muted:
            continue
        for raw in phrases:
            for phrase in phrases_of(significant_tokens(raw, extra_stop=suppress)):
                phrase_to_ids.setdefault(phrase, set()).add(cid)
    return Matcher(phrase_to_ids, index.get("temas", {}), suppress)
```

- [ ] **Step 5: Run, expect pass**.

- [ ] **Step 6: Commit** — `git add tools/scrapers/matcher.py tools/scrapers/commitment_overlay.json tools/tests/test_matcher.py && git commit -m "feat: shared commitment matcher with hand-tune overlay"`

---

### Task 4: Generalize label helpers in `watcher_common`

**Files:**
- Modify: `tools/scrapers/watcher_common.py`

**Interfaces:**
- Produces: `ensure_label(repo, gh_token, name=LABEL, color=LABEL_COLOR, description=...)` (existing 2-arg calls unaffected); `create_issue(repo, gh_token, title, body, labels=None)` (defaults to `[LABEL]`).

- [ ] **Step 1: Implement** — replace `ensure_label` and `create_issue`:

```python
def ensure_label(repo: str, gh_token: str, name: str = LABEL, color: str = LABEL_COLOR,
                 description: str = "Evidencia candidata detectada por un watcher; requiere revisión editorial") -> None:
    try:
        gh_request("GET", f"/repos/{repo}/labels/{name}", gh_token)
    except urllib.error.HTTPError as err:
        if err.code != 404:
            raise
        gh_request("POST", f"/repos/{repo}/labels", gh_token, {
            "name": name, "color": color, "description": description,
        })


def create_issue(repo: str, gh_token: str, title: str, body: str, labels: list | None = None) -> dict:
    return gh_request("POST", f"/repos/{repo}/issues", gh_token, {
        "title": title, "body": body, "labels": labels or [LABEL],
    })
```

- [ ] **Step 2: Regression check** — `python3 -m unittest discover -s tools/tests -p "test_*.py"` (evidence_watcher/elperuano still import fine).

- [ ] **Step 3: Commit** — `git add tools/scrapers/watcher_common.py && git commit -m "feat: parameterize ensure_label/create_issue for extra labels"`

---

### Task 5: Migrate the El Peruano scraper onto the matcher + tema labels

**Files:**
- Modify: `tools/scrapers/elperuano_scraper.py`
- Delete: `tools/scrapers/watcher_keywords.json` is **kept** (news watcher uses it) — do NOT delete.
- Test: `tools/tests/test_elperuano_scraper.py`

**Interfaces:**
- Consumes: `matcher.load_matcher`, `Matcher.match`, `Matcher.tema_slug`; generalized `ensure_label`/`create_issue` (Task 4).

- [ ] **Step 1: Update the test** — in `tools/tests/test_elperuano_scraper.py`, the `set(records[0])` assertion already includes `op`; add a matcher-integration test:

```python
class MatcherIntegrationTest(unittest.TestCase):
    def test_scraper_uses_shared_matcher(self):
        import matcher
        mt = matcher.load_matcher()
        # a norma sumilla mentioning a distinctive plan phrase yields its commitment id(s)
        ids = mt.match("Autorizan la creación de unidades de flagrancia")
        self.assertTrue(all(i.count(".") == 1 for i in ids))  # well-formed commitment ids
```

Remove `MatchRecordTest` (its `match_record`/keyword mechanism is gone).

- [ ] **Step 2: Run, expect fail** (old `MatchRecordTest` referenced removed code / new test needs wiring).

- [ ] **Step 3: Implement the migration** — in `tools/scrapers/elperuano_scraper.py`:
  - Imports: add `from matcher import load_matcher`; drop `normalize` if now unused (keep it — `html_to_text` doesn't use it; `significant_terms` is being deleted, so remove `normalize` from the import if nothing else uses it. Check: only `significant_terms` used it → remove `normalize` from import).
  - Delete `KEYWORDS_PATH`, `STOPWORDS`, `significant_terms`, `match_record` (STOPWORDS now lives in watcher_common).
  - In `run()`: replace `keywords = json.loads(KEYWORDS_PATH.read_text())` with `matcher = load_matcher()`, and the matched line with:

```python
    matched = [(r, rel) for r in records if (rel := matcher.match(f"{r['numero']} {r['tipo']} {r['sumilla']}"))]
```

  - In the issue-creating loop, ensure tema labels and pass them:

```python
        if created >= MAX_NEW_ISSUES:
            print(f"Reached cap of {MAX_NEW_ISSUES} new issues; stopping.")
            break
        if issue_exists(token_str, repo, gh_token):
            continue
        tema_labels = sorted({f"tema:{matcher.tema_slug(cid)}" for cid in related if matcher.tema_slug(cid)})
        for tl in tema_labels:
            ensure_label(repo, gh_token, name=tl, color="6B6F7B", description=f"Compromisos del tema {tl.split(':',1)[1]}")
        excerpt = " ".join(norma_text(record).split())[:EXCERPT_CHARS]
        title = f"Norma candidata: {record['tipo']} {record['numero']} [{token_str}]"[:250]
        issue = create_issue(repo, gh_token, title, issue_body(record, related, iso_date, excerpt), labels=[LABEL] + tema_labels)
        created += 1
        print(f"Created issue #{issue['number']}: {record['tipo']} {record['numero']}")
```

  - Add `LABEL` to the `watcher_common` import.

- [ ] **Step 4: Run, expect pass** — full suite `python3 -m unittest discover -s tools/tests -p "test_*.py"`.

- [ ] **Step 5: Live dry-run** — `python3 tools/scrapers/elperuano_scraper.py --date 2026-07-15 --dry-run` → prints matched normas; confirm count is small (precision).

- [ ] **Step 6: Commit** — `git add tools/scrapers/elperuano_scraper.py tools/tests/test_elperuano_scraper.py && git commit -m "feat: El Peruano scraper matches plan commitments; tema-labeled issues"`

---

### Task 6: CI drift check, SOP, tune, verify, ship

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `workflows/elperuano_scraper.md`
- Modify: `tools/scrapers/commitment_overlay.json` (only if tuning needs it)

- [ ] **Step 1: CI drift check** — in `.github/workflows/ci.yml`, add before the unittest line:

```yaml
      - run: python3 tools/scrapers/build_commitment_index.py --check
```

- [ ] **Step 2: Tune against real days** — run the dry-run over 3–4 recent dates:

```bash
for d in 2026-07-10 2026-07-13 2026-07-14 2026-07-15; do
  python3 tools/scrapers/elperuano_scraper.py --date "$d" --dry-run 2>/dev/null | tail -1
done
```
If any day yields a flood (>~20 matched), inspect the offenders and either lower `DF_MAX_*` in the builder (regenerate) or add `mute_commitments`. Target ≤~15/day.

- [ ] **Step 3: Update SOP** — `workflows/elperuano_scraper.md`: replace the keyword-prefilter description with the matcher (index + overlay), document `build_commitment_index.py` (regenerate on plan change; CI `--check`), the tema labels, and the zero-phrase count from Task 2 Step 4.

- [ ] **Step 4: Full verification**:

```bash
python3 -m unittest discover -s tools/tests -p "test_*.py"
python3 tools/scrapers/build_commitment_index.py --check
npm test && npm run validate && npm run build
```

- [ ] **Step 5: Commit + PR + merge**:

```bash
git add .github/workflows/ci.yml workflows/elperuano_scraper.md tools/scrapers/commitment_overlay.json
git commit -m "ci: guard commitment index drift; document the matcher"
git pull --rebase origin main
git push -u origin feat/proposal-matcher
gh pr create --title "feat: proposal-derived commitment matcher for El Peruano" --body "..."
gh pr checks --watch && gh pr merge --rebase
```

- [ ] **Step 6: Post-merge** — clean up branch; note release-please will roll these `feat:` commits into the next version.
