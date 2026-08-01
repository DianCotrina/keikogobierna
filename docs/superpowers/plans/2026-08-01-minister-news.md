# Per-minister press coverage — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show, on each minister's dossier, the press coverage that named them in the last seven days.

**Architecture:** The existing 4×/day `ultimitas_scraper` Action writes a third file, `ministros.json`, to the `ultimitas-data` branch. Each `/gabinete/<slug>/` page fetches it client-side and renders its own slice. Matching reuses the two-key rule (cartera **and** apellido) already in `infobae_rules`.

**Tech Stack:** Python 3.9 stdlib only (scrapers), Astro + TypeScript + Tailwind v4 (site), `node --test` and `unittest` for tests.

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-08-01-minister-news-design.md`.
- **Language:** code, comments and commits in English; everything a visitor reads in Spanish (Peru).
- **Python:** stdlib only. No new dependencies.
- **Copyright:** headline, outlet, date and link only. Never an article body, never `content:encoded`.
- **No AI in any pipeline.** Matching is deterministic.
- **Third-party text renders with `textContent` only**, never `innerHTML`.
- **Third-party URLs pass the scheme guard** before becoming an `href`.
- **One tool owns the `ultimitas-data` branch.** No new scheduled workflow.
- Run `npm test`, `python3 -m unittest discover -s tools/tests -t .`, `npm run validate` and `npm run build` before every commit.

## File Structure

**Create**
| File | Responsibility |
|---|---|
| `src/lib/safe-url.mjs` | The http(s)-only URL guard, shared by both renderers |
| `tests/safe-url.test.mjs` | Guard tests |
| `tools/scrapers/common/minister_news.py` | Pure: articles + roster + now → per-slug index |
| `tools/tests/test_minister_news.py` | Index tests |
| `src/components/MinisterNews/MinisterNews.astro` | Section markup + empty/error states |
| `src/components/MinisterNews/minister-news.ts` | Fetch, filter to this slug, render |

**Modify**
| File | Change |
|---|---|
| `tools/scrapers/common/infobae_rules.py` | Drop the first-match `break`; move ordering to callers |
| `tools/scrapers/infobae_profiles.py` | Apply its own profiles-first ordering |
| `tools/scrapers/ultimitas_scraper.py` | Write `ministros.json` |
| `src/components/Ultimitas/ultimitas.ts` | Import the shared guard |
| `src/pages/gabinete/[slug].astro` | Mount the section between tenure and judicial record |
| `workflows/ultimitas_scraper.md`, `docs/ARCHITECTURE.md` | Document the third file |

---

### Task 1: Share the URL scheme guard

`safeHttpUrl` is private to `ultimitas.ts`. The new renderer needs the same guard, and two copies drift.

**Files:**
- Create: `src/lib/safe-url.mjs`, `tests/safe-url.test.mjs`
- Modify: `src/components/Ultimitas/ultimitas.ts:25-33`

**Interfaces:**
- Produces: `safeHttpUrl(raw: string): string` — the absolute URL, or `''` for anything that is not http(s) or does not parse.

- [ ] **Step 1: Write the failing test**

Create `tests/safe-url.test.mjs`:

```javascript
import test from 'node:test';
import assert from 'node:assert/strict';

import { safeHttpUrl } from '../src/lib/safe-url.mjs';

test('https and http pass through', () => {
  assert.equal(safeHttpUrl('https://elcomercio.pe/nota/'), 'https://elcomercio.pe/nota/');
  assert.equal(safeHttpUrl('http://rpp.pe/nota'), 'http://rpp.pe/nota');
});

test('a javascript: url is rejected', () => {
  assert.equal(safeHttpUrl('javascript:alert(1)'), '');
});

test('a data: url is rejected', () => {
  assert.equal(safeHttpUrl('data:text/html,<script>alert(1)</script>'), '');
});

test('an unparseable value is rejected rather than thrown on', () => {
  assert.equal(safeHttpUrl('not a url'), '');
  assert.equal(safeHttpUrl(''), '');
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npm test`
Expected: FAIL — cannot resolve `../src/lib/safe-url.mjs`.

- [ ] **Step 3: Create the module**

Create `src/lib/safe-url.mjs`:

```javascript
/**
 * Only http(s) may reach an href.
 *
 * Feed data is external and `canonical_url()` upstream preserves whatever
 * scheme it was given, including `javascript:` and `data:`. Shared rather than
 * copied: two renderers show third-party links, and a guard that exists twice
 * is a guard that will eventually differ.
 */
export function safeHttpUrl(raw) {
  try {
    const url = new URL(raw);
    if (url.protocol === 'https:' || url.protocol === 'http:') return url.href;
  } catch {
    // unparseable — fall through to ''
  }
  return '';
}
```

- [ ] **Step 4: Point `ultimitas.ts` at it**

In `src/components/Ultimitas/ultimitas.ts`, delete the local `safeHttpUrl` function (and the comment above it) and add to the imports at the top:

```typescript
import { safeHttpUrl } from '../../lib/safe-url.mjs';
```

- [ ] **Step 5: Verify**

Run: `npm test && npm run build`
Expected: PASS, 4 new tests. Build succeeds — `/ultimitas/` still renders.

- [ ] **Step 6: Commit**

```bash
git add src/lib/safe-url.mjs tests/safe-url.test.mjs src/components/Ultimitas/ultimitas.ts
git commit -m "refactor: share the http-only URL guard between renderers"
```

---

### Task 2: Let one article reach every minister it names

`profile_items` stops at the first matching minister and orders profile pieces first. Both are right for a review packet and wrong for a news list.

**Files:**
- Modify: `tools/scrapers/common/infobae_rules.py` (`profile_items`)
- Modify: `tools/scrapers/infobae_profiles.py:104`
- Test: `tools/tests/test_infobae_rules.py`

**Interfaces:**
- Produces: `profile_items(articles: list, roster: list) -> dict` — cartera id → articles **in feed order**, every match kept.
- Produces: `sort_for_review(items: list) -> list` — profile pieces first, then newest.

- [ ] **Step 1: Write the failing tests**

Append to `tools/tests/test_infobae_rules.py`:

```python
class MultipleMinistersTest(unittest.TestCase):
    """One article naming two ministers is coverage of both."""

    ROSTER = [
        {"portfolio": "m-economia", "person_name": "Elmer Rafael Cuba Bustinza"},
        {"portfolio": "m-trabajo", "person_name": "Juan Manuel Kosme Sheput Moore"},
    ]

    def test_both_ministers_receive_the_article(self):
        article = {
            "title": ("El ministro de Economía Cuba y el ministro de Trabajo Sheput "
                      "coordinan el alza del sueldo mínimo"),
            "summary": "", "published": "2026-08-01T10:00:00-05:00",
            "url": "https://gestion.pe/n/", "source": "Gestión",
        }
        found = ir.profile_items([article], self.ROSTER)
        self.assertEqual(set(found), {"m-economia", "m-trabajo"})


class OrderingTest(unittest.TestCase):
    """Ordering belongs to the caller: a review packet and a news list differ."""

    NEWS = {"title": "Cuba anuncia medidas", "published": "2026-08-02T10:00:00-05:00"}
    PROFILE = {"title": "Quién es Elmer Cuba, el nuevo ministro",
               "published": "2026-08-01T10:00:00-05:00"}

    def test_profile_items_preserves_feed_order(self):
        roster = [{"portfolio": "m-economia", "person_name": "Elmer Rafael Cuba Bustinza"}]
        articles = [
            {**self.NEWS, "title": "El ministro de Economía Cuba anuncia medidas",
             "summary": "", "url": "https://a/", "source": "Gestión"},
            {**self.PROFILE, "title": "Quién es Cuba, el nuevo ministro de Economía",
             "summary": "", "url": "https://b/", "source": "Gestión"},
        ]
        found = ir.profile_items(articles, roster)["m-economia"]
        self.assertEqual([a["url"] for a in found], ["https://a/", "https://b/"])

    def test_sort_for_review_puts_profiles_first(self):
        ordered = ir.sort_for_review([self.NEWS, self.PROFILE])
        self.assertEqual(ordered[0]["title"], "Quién es Elmer Cuba, el nuevo ministro")
```

- [ ] **Step 2: Run and watch it fail**

Run: `python3 -m unittest tools.tests.test_infobae_rules -v`
Expected: FAIL — only one cartera in the first test; `sort_for_review` does not exist.

- [ ] **Step 3: Change `profile_items` and add `sort_for_review`**

In `tools/scrapers/common/infobae_rules.py`, replace the tail of `profile_items` (the per-person loop's `break` and the trailing sort) so the function reads:

```python
def profile_items(articles: list, roster: list) -> dict:
    """Articles about each minister, keyed by cartera, in feed order.

    A match needs two keys: the item must name one of the person's surnames
    *and* resolve to their cartera. Either alone is wrong in a way the live feed
    demonstrates — "María Seminario" defeats name matching because the roster
    says "Mara", and "Guardaespaldas del Rey de España" defeats surname matching
    because the transport minister is Rafael Rey Rey.

    Every minister an article names receives it. Stopping at the first was fine
    while the only caller wanted one profile per cartera; an article about two
    ministers is coverage of both, and which one won was roster order.

    Order is the caller's: a review packet wants profiles first, a dated news
    list wants the newest.
    """
    by_portfolio: dict = {}

    for article in articles:
        title = article.get("title") or ""
        summary = article.get("summary") or ""
        blob = f"{title} {summary}"
        carteras = _carteras_named(blob)
        if not carteras:
            continue
        words = set(fold(blob).split())

        for person in roster:
            pid = person.get("portfolio")
            if pid not in carteras:
                continue
            if not any(s in words for s in _surnames(person.get("person_name", ""))):
                continue
            by_portfolio.setdefault(pid, []).append(article)

    return by_portfolio


def sort_for_review(items: list) -> list:
    """Profile pieces first, then newest — what a person writing a ficha wants."""
    return sorted(items, key=lambda a: (not is_profile(a.get("title") or ""),
                                        -_epoch(a.get("published") or "")))
```

- [ ] **Step 4: Keep the profile reader's ordering**

In `tools/scrapers/infobae_profiles.py`, change the import line to:

```python
from tools.scrapers.common.infobae_rules import profile_items, sort_for_review
```

and replace line 104 (`found = profile_items(items_by_outlet, ministers)`) with:

```python
    found = {pid: sort_for_review(items)
             for pid, items in profile_items(items_by_outlet, ministers).items()}
```

- [ ] **Step 5: Verify**

Run: `python3 -m unittest discover -s tools/tests -t .`
Expected: PASS, all tests including the pre-existing `test_infobae_rules` fixture assertions.

Run: `python3 -m tools.scrapers.infobae_profiles | tail -3`
Expected: still reports carteras with material; ordering unchanged from before.

- [ ] **Step 6: Commit**

```bash
git add tools/scrapers/common/infobae_rules.py tools/scrapers/infobae_profiles.py tools/tests/test_infobae_rules.py
git commit -m "refactor: every minister an article names receives it"
```

---

### Task 3: Build the per-minister index

**Files:**
- Create: `tools/scrapers/common/minister_news.py`, `tools/tests/test_minister_news.py`

**Interfaces:**
- Consumes: `profile_items(articles, roster) -> dict` (Task 2).
- Produces: `build_index(articles, roster, now, window_days=7) -> dict` — `{slug: [{title, url, source, published}, …]}`, newest first, ministers with no coverage absent.
- Produces: `WINDOW_DAYS = 7`.
- The `roster` rows carry `portfolio`, `person_name` and `slug`.

- [ ] **Step 1: Write the failing tests**

Create `tools/tests/test_minister_news.py`:

```python
"""The per-minister coverage index written for the dossier pages."""

import unittest
from datetime import datetime, timezone

from tools.scrapers.common import minister_news as mn

ROSTER = [
    {"portfolio": "m-economia", "person_name": "Elmer Rafael Cuba Bustinza",
     "slug": "elmer-rafael-cuba-bustinza"},
    {"portfolio": "m-trabajo", "person_name": "Juan Manuel Kosme Sheput Moore",
     "slug": "juan-manuel-kosme-sheput-moore"},
]
NOW = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


def article(title, published, url="https://gestion.pe/n/", source="Gestión", summary=""):
    return {"title": title, "summary": summary, "url": url,
            "source": source, "published": published, "author": "Redacción"}


class WindowTest(unittest.TestCase):
    def test_an_article_from_six_days_ago_is_kept(self):
        a = article("El ministro de Economía Cuba anuncia medidas", "2026-07-26T10:00:00-05:00")
        index = mn.build_index([a], ROSTER, NOW)
        self.assertIn("elmer-rafael-cuba-bustinza", index)

    def test_an_article_from_eight_days_ago_is_dropped(self):
        a = article("El ministro de Economía Cuba anuncia medidas", "2026-07-24T10:00:00-05:00")
        self.assertEqual(mn.build_index([a], ROSTER, NOW), {})

    def test_an_unparseable_date_is_dropped_rather_than_kept_forever(self):
        a = article("El ministro de Economía Cuba anuncia medidas", "no es una fecha")
        self.assertEqual(mn.build_index([a], ROSTER, NOW), {})


class ShapeTest(unittest.TestCase):
    def setUp(self):
        self.index = mn.build_index(
            [article("El ministro de Economía Cuba anuncia medidas", "2026-08-01T09:00:00-05:00",
                     summary="Un resumen que no debe publicarse.")],
            ROSTER, NOW)

    def test_keyed_by_slug_not_cartera(self):
        self.assertEqual(list(self.index), ["elmer-rafael-cuba-bustinza"])

    def test_carries_only_the_four_published_fields(self):
        entry = self.index["elmer-rafael-cuba-bustinza"][0]
        self.assertEqual(set(entry), {"title", "url", "source", "published"})

    def test_the_feed_summary_is_not_shipped(self):
        entry = self.index["elmer-rafael-cuba-bustinza"][0]
        self.assertNotIn("summary", entry)


class OrderTest(unittest.TestCase):
    def test_newest_first(self):
        articles = [
            article("El ministro de Economía Cuba, lunes", "2026-07-27T10:00:00-05:00", url="https://a/"),
            article("El ministro de Economía Cuba, viernes", "2026-07-31T10:00:00-05:00", url="https://b/"),
        ]
        index = mn.build_index(articles, ROSTER, NOW)
        self.assertEqual([e["url"] for e in index["elmer-rafael-cuba-bustinza"]],
                         ["https://b/", "https://a/"])


class CoverageTest(unittest.TestCase):
    def test_a_minister_with_no_coverage_is_absent(self):
        a = article("El ministro de Economía Cuba anuncia medidas", "2026-08-01T09:00:00-05:00")
        self.assertNotIn("juan-manuel-kosme-sheput-moore", mn.build_index([a], ROSTER, NOW))

    def test_an_article_naming_two_ministers_lands_under_both(self):
        a = article("El ministro de Economía Cuba y el ministro de Trabajo Sheput coordinan",
                    "2026-08-01T09:00:00-05:00")
        index = mn.build_index([a], ROSTER, NOW)
        self.assertEqual(set(index), {"elmer-rafael-cuba-bustinza", "juan-manuel-kosme-sheput-moore"})

    def test_a_roster_row_without_a_slug_is_skipped(self):
        """An announced cartera has no ficha and therefore no page to link to."""
        roster = [{"portfolio": "m-economia", "person_name": "Elmer Rafael Cuba Bustinza"}]
        a = article("El ministro de Economía Cuba anuncia medidas", "2026-08-01T09:00:00-05:00")
        self.assertEqual(mn.build_index([a], roster, NOW), {})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and watch it fail**

Run: `python3 -m unittest tools.tests.test_minister_news -v`
Expected: FAIL — `No module named 'tools.scrapers.common.minister_news'`.

- [ ] **Step 3: Write the module**

Create `tools/scrapers/common/minister_news.py`:

```python
"""Press coverage of each sitting minister, for their dossier page.

Coverage and nothing more: an article is here because an outlet named this
minister and their cartera, not because anyone judged it important or true.
The dossier says so in its own words, and this module must not imply otherwise
by filtering for tone or topic.

Pure: no I/O, no network. The caller supplies the articles and the roster.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .infobae_rules import profile_items

WINDOW_DAYS = 7

# What the dossier renders, and therefore all it is given. The feed summary and
# author stay out: shipping text no page displays would be carrying an outlet's
# prose for no reason.
PUBLISHED_FIELDS = ("title", "url", "source", "published")


def _published_at(article: dict):
    """Timezone-aware publication time, or None when it cannot be read."""
    try:
        parsed = datetime.fromisoformat(article.get("published") or "")
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else None


def build_index(articles: list, roster: list, now: datetime,
                window_days: int = WINDOW_DAYS) -> dict:
    """Coverage per minister slug, newest first, within the trailing window.

    Ministers with no coverage are absent rather than present with an empty
    list: the page renders both the same way, and absence keeps the file small.

    A roster row with no slug is skipped. That is an announced cartera whose
    holder has no ficha, so there is no dossier for the coverage to appear on.
    """
    cutoff = now - timedelta(days=window_days)
    fresh = []
    for article in articles:
        at = _published_at(article)
        if at is not None and at >= cutoff:
            fresh.append(article)

    slugs = {row["portfolio"]: row["slug"] for row in roster if row.get("slug")}
    index: dict = {}
    for pid, items in profile_items(fresh, roster).items():
        slug = slugs.get(pid)
        if not slug:
            continue
        entries = [{k: item.get(k) for k in PUBLISHED_FIELDS} for item in items]
        entries.sort(key=lambda e: e["published"], reverse=True)
        index[slug] = entries
    return index
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m unittest tools.tests.test_minister_news -v`
Expected: PASS, 10 tests.

- [ ] **Step 5: Check it against the live feed**

Run:

```bash
python3 -c "
import sys; sys.path.insert(0,'.')
from datetime import datetime, timezone
from tools.scrapers.common.press_feeds import fetch_sources
from tools.scrapers.common.minister_news import build_index
from tools.scrapers.infobae_profiles import roster
import json
arts,_ = fetch_sources()
rows = [{**r, 'slug': None} for r in roster()]
print('rows lack slugs ->', build_index(arts, rows, datetime.now(timezone.utc)) == {})
"
```

Expected: prints `True` — proving the slug guard, since `roster()` does not yet supply slugs. Task 4 adds them.

- [ ] **Step 6: Commit**

```bash
git add tools/scrapers/common/minister_news.py tools/tests/test_minister_news.py
git commit -m "feat: per-minister coverage index, keyed by slug and windowed"
```

---

### Task 4: Put the slug on the roster and write `ministros.json`

**Files:**
- Modify: `tools/scrapers/infobae_profiles.py` (`roster`)
- Modify: `tools/scrapers/ultimitas_scraper.py` (`run`)
- Test: `tools/tests/test_infobae_roster.py`, `tools/tests/test_ultimitas_scraper.py`

**Interfaces:**
- Consumes: `build_index(articles, roster, now, window_days=7)` (Task 3).
- Produces: `ministros.json` on the `ultimitas-data` branch, shape `{generated, window_days, sources, ministers}`.

- [ ] **Step 1: Write the failing test for the slug**

Append to `tools/tests/test_infobae_roster.py`, inside `class RosterTest`:

```python
    def test_each_row_carries_the_minister_slug(self):
        """The coverage index keys by slug; the roster is where it comes from."""
        with with_data():
            rows = {r["portfolio"]: r.get("slug") for r in ip.roster()}
        self.assertEqual(rows["pcm"], "ana-rojas-diaz")
        self.assertEqual(rows["m-salud"], "beto-lima-soto")

    def test_an_announced_cartera_has_no_slug(self):
        announced = {"announcements": [
            {"portfolio": "m-interior", "person_name": "Dino Paz Ruiz", "person": None}]}
        with with_data(announcements=announced):
            row = [r for r in ip.roster() if r["portfolio"] == "m-interior"][0]
        self.assertIsNone(row["slug"])
```

- [ ] **Step 2: Run and watch it fail**

Run: `python3 -m unittest tools.tests.test_infobae_roster -v`
Expected: FAIL — rows have no `slug` key.

- [ ] **Step 3: Add the slug to both branches of `roster()`**

In `tools/scrapers/infobae_profiles.py`, in the tenure loop's appended dict add `"slug": person["slug"],` and in the announcements loop add `"slug": (linked or {}).get("slug"),`. The function becomes:

```python
    rows, seen = [], set()
    for tenure in tenures:
        if tenure.get("end"):
            continue  # a past holder is not who covers the cartera now
        person = ministers.get(tenure.get("person") or "")
        if not person:
            continue
        seen.add(tenure["portfolio"])
        rows.append({
            "portfolio": tenure["portfolio"],
            "person_name": person["name"],
            "slug": person["slug"],
            "has_ficha": bool(person.get("bio")),
        })
    for entry in announcements:
        if entry["portfolio"] in seen:
            continue
        linked = ministers.get(entry.get("person") or "")
        rows.append({
            "portfolio": entry["portfolio"],
            "person_name": (linked or {}).get("name") or entry["person_name"],
            "slug": (linked or {}).get("slug"),
            "has_ficha": bool((linked or {}).get("bio")),
        })
    return rows
```

- [ ] **Step 4: Run the roster tests**

Run: `python3 -m unittest tools.tests.test_infobae_roster -v`
Expected: PASS, 8 tests.

- [ ] **Step 5: Write the failing test for the file**

Append to `tools/tests/test_ultimitas_scraper.py`, above the `__main__` guard:

```python
class MinistrosFileTest(unittest.TestCase):
    """The scraper writes a third file, and writes it on every run.

    run() returns early when no new /ultimitas/ article arrived. The coverage
    window has to keep moving anyway: articles age out of seven days whether or
    not anything new came in, so a quiet day must still refresh this file.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.real_fetch = us.fetch_sources
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(setattr, us, "fetch_sources", self.real_fetch)

    def _run(self, items):
        us.fetch_sources = lambda: (items, [])
        return us.run(self.tmp, dry_run=False)

    def test_the_file_is_written_with_the_expected_shape(self):
        self._run([{
            "title": "El ministro de Economía Cuba anuncia medidas", "summary": "",
            "url": "https://gestion.pe/n/", "author": "", "source": "Gestión",
            "published": datetime.now(timezone.utc).isoformat(),
        }])
        payload = json.loads((Path(self.tmp) / "ministros.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["window_days"], 7)
        self.assertIn("generated", payload)
        self.assertIsInstance(payload["ministers"], dict)

    def test_a_run_with_no_new_ultimitas_articles_still_refreshes_it(self):
        item = {
            "title": "El ministro de Economía Cuba anuncia medidas", "summary": "",
            "url": "https://gestion.pe/n/", "author": "", "source": "Gestión",
            "published": datetime.now(timezone.utc).isoformat(),
        }
        self._run([item])
        first = (Path(self.tmp) / "ministros.json").read_text(encoding="utf-8")
        self._run([item])  # identical input: the /ultimitas/ early return fires
        self.assertTrue((Path(self.tmp) / "ministros.json").exists())
        self.assertIn("ministers", json.loads(first))
```

Add to that file's imports at the top: `import json`, `import shutil`, `import tempfile`, and `from datetime import datetime, timezone`.

- [ ] **Step 6: Run and watch it fail**

Run: `python3 -m unittest tools.tests.test_ultimitas_scraper -v`
Expected: FAIL — `ministros.json` does not exist.

- [ ] **Step 7: Write the file from `run()`**

In `tools/scrapers/ultimitas_scraper.py` add to the imports:

```python
from tools.scrapers.common.minister_news import WINDOW_DAYS, build_index
from tools.scrapers.common.press_feeds import SOURCES
from tools.scrapers.infobae_profiles import roster
```

Then, in `run()`, immediately after `now_iso` is assigned and **before** the `if articles == existing` early return, insert:

```python
    # Every outlet, not just the two this page publishes: a minister's coverage
    # is wider than the front page's. Written before the early return below,
    # because the seven-day window keeps moving on a day with no new articles.
    write_ministros(data, list(unique.values()), now_iso)
```

And add the function above `run()`:

```python
def write_ministros(data: Path, articles: list, now_iso: str) -> None:
    """The per-minister coverage index, for the gabinete dossier pages."""
    index = build_index(articles, roster(), datetime.fromisoformat(now_iso))
    (data / "ministros.json").write_text(json.dumps({
        "generated": now_iso,
        "window_days": WINDOW_DAYS,
        "sources": [s["name"] for s in SOURCES],
        "ministers": index,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"ministros.json: {len(index)} minister(s) with coverage "
          f"in the last {WINDOW_DAYS} days.")
```

- [ ] **Step 8: Run the tests**

Run: `python3 -m unittest discover -s tools/tests -t .`
Expected: PASS.

- [ ] **Step 9: Run it against the live feed**

Run: `python3 -m tools.scrapers.ultimitas_scraper --data-dir /tmp/ult-preview && python3 -m json.tool /tmp/ult-preview/ministros.json | head -30`
Expected: a `ministers` map keyed by slug; roughly 7 of 19 ministers present.

- [ ] **Step 10: Commit**

```bash
git add tools/scrapers/infobae_profiles.py tools/scrapers/ultimitas_scraper.py tools/tests/
git commit -m "feat: write the per-minister coverage index each run"
```

---

### Task 5: Render the section on the dossier

**Files:**
- Create: `src/components/MinisterNews/MinisterNews.astro`, `src/components/MinisterNews/minister-news.ts`
- Modify: `src/pages/gabinete/[slug].astro` (between the tenure section ending at line 168 and the judicial section beginning at line 170)

**Interfaces:**
- Consumes: `safeHttpUrl(raw)` (Task 1); `ministros.json` (Task 4).
- The component takes one prop: `slug: string`.

- [ ] **Step 1: Write the component markup**

Create `src/components/MinisterNews/MinisterNews.astro`:

```astro
---
// Press coverage naming this minister in the last seven days.
//
// Coverage, not endorsement or accusation — the blurb says so, because this
// sits directly above the judicial record and presence must not read as a
// charge. Data arrives client-side: the page is static and the feed moves four
// times a day.
interface Props {
  slug: string;
}
const { slug } = Astro.props;
---

<section class="border-t border-tinta/10" data-minister-news data-slug={slug}>
  <div class="mx-auto max-w-4xl px-5 sm:px-8 py-14 sm:py-16">
    <div class="reveal border-b border-tinta/10 pb-3">
      <h2 class="font-mono text-xs uppercase tracking-[0.18em] text-tintasuave">Cobertura de prensa</h2>
      <p class="mt-1.5 text-sm leading-[1.7] text-tintasuave max-w-xl">
        Notas publicadas sobre este ministro en los últimos 7 días. Que una nota aparezca
        aquí no significa que este sitio la respalde.
      </p>
    </div>

    <ul id="minister-news-list" class="mt-6 space-y-4"></ul>

    <p id="minister-news-empty" class="hidden mt-6 font-mono text-sm text-tintasuave">
      Sin cobertura en los últimos 7 días.
    </p>

    <p class="mt-8 border-t border-dashed border-tinta/20 pt-5 font-mono text-[0.65rem] text-tintafina leading-relaxed">
      Los titulares pertenecen a cada medio y se enlazan directamente a la fuente.
      Este sitio no reproduce artículos completos.
    </p>
  </div>
</section>

<script src="./minister-news.ts"></script>
```

- [ ] **Step 2: Write the renderer**

Create `src/components/MinisterNews/minister-news.ts`:

```typescript
import { formatDateEs } from '../../lib/format.mjs';
import { safeHttpUrl } from '../../lib/safe-url.mjs';

const DATA_URL =
  'https://raw.githubusercontent.com/DianCotrina/keikogobierna/ultimitas-data/ministros.json';

interface Entry {
  title: string;
  url: string;
  source: string;
  published: string;
}

// Third-party text: every node built with textContent, never innerHTML.
function item(entry: Entry): HTMLElement {
  const li = document.createElement('li');
  li.className = 'bg-white rounded-lg border border-tinta/10 shadow-card p-5 sm:p-6';

  const meta = document.createElement('p');
  meta.className = 'font-mono text-[0.65rem] uppercase tracking-[0.14em] text-tintafina';
  meta.textContent = `${entry.source} · ${formatDateEs(entry.published.slice(0, 10))}`;
  li.appendChild(meta);

  const href = safeHttpUrl(entry.url);
  const headline = document.createElement(href ? 'a' : 'p');
  headline.className = 'mt-1.5 block font-sans font-bold text-base leading-snug';
  headline.textContent = entry.title;
  if (href && headline instanceof HTMLAnchorElement) {
    headline.href = href;
    headline.target = '_blank';
    headline.rel = 'noopener noreferrer';
    headline.classList.add('nav-link');
  }
  li.appendChild(headline);
  return li;
}

async function load(): Promise<void> {
  const section = document.querySelector<HTMLElement>('[data-minister-news]');
  const list = document.getElementById('minister-news-list');
  const empty = document.getElementById('minister-news-empty');
  if (!section || !list || !empty) return;

  const slug = section.dataset.slug;
  if (!slug) return;

  try {
    const resp = await fetch(DATA_URL, { cache: 'no-cache' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data: { ministers?: Record<string, Entry[]> } = await resp.json();
    const entries = data.ministers?.[slug] ?? [];
    if (entries.length === 0) {
      empty.classList.remove('hidden');
      return;
    }
    list.replaceChildren(...entries.map(item));
  } catch (err) {
    // A scraper outage must never mark up a dossier. Say nothing, break nothing.
    console.error('minister-news:', err);
    empty.classList.remove('hidden');
  }
}

load();
```

- [ ] **Step 3: Mount it between the tenure and judicial sections**

In `src/pages/gabinete/[slug].astro`, add to the imports at the top of the frontmatter:

```astro
import MinisterNews from '../../components/MinisterNews/MinisterNews.astro';
```

and insert, on the line after the tenure section's closing `</section>` (line 168) and before the judicial section:

```astro
    <MinisterNews slug={person.slug} />
```

- [ ] **Step 4: Build and look at it**

Run: `npm run build && npm run dev` then screenshot `http://localhost:3000/gabinete/elmer-rafael-cuba-bustinza/`.
Expected: the section renders between «Paso por el cargo» and «Registro judicial». With no `ministros.json` published yet the fetch 404s and the empty state shows — which is the failure behaviour working.

- [ ] **Step 5: Verify the failure modes by hand**

In the browser console on that page, confirm the section does not throw when the payload is absent, and that the rest of the dossier renders normally. Check keyboard focus reaches each headline link.

- [ ] **Step 6: Commit**

```bash
git add src/components/MinisterNews src/pages/gabinete/\[slug\].astro
git commit -m "feat: show a minister's press coverage on their dossier"
```

---

### Task 6: Document the third file

**Files:**
- Modify: `workflows/ultimitas_scraper.md`, `docs/ARCHITECTURE.md`

- [ ] **Step 1: Update the workflow SOP**

In `workflows/ultimitas_scraper.md`, under the list of files the scraper writes, add:

```markdown
   - `ministros.json` — press coverage per sitting minister for the last 7 days,
     keyed by ministers.json slug. Read by each `/gabinete/<slug>/` page. Unlike
     the two files above it uses **all five** outlets and is not KEYWORDS-filtered:
     the gate is the two-key matcher in `infobae_rules` (the article must name the
     cartera *and* an apellido). Written on every run, including runs where no new
     /ultimitas/ article arrived — the seven-day window moves regardless.
```

- [ ] **Step 2: Update the architecture doc**

In `docs/ARCHITECTURE.md`, in the discovery-tools table, add a row:

```markdown
| `minister_news.py` | press feeds, via `infobae_rules` | 4×/day with ultimitas | `ministros.json` on `ultimitas-data` |
```

- [ ] **Step 3: Full verification**

Run:

```bash
npm test && python3 -m unittest discover -s tools/tests -t . && npm run validate && npm run build
```

Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add workflows/ultimitas_scraper.md docs/ARCHITECTURE.md
git commit -m "docs: record the per-minister coverage file"
```

---

## Self-review

**Spec coverage.** Objective → Tasks 3–5. Coverage framing → Task 5 copy. Non-goals → no ranking, no bodies (Task 3 `PUBLISHED_FIELDS`), no AI. Architecture and no-new-job → Task 4. Outlet set → Task 4 (`unique.values()`, all five). Matching and its three changes → Task 2. Data contract → Task 3 and Task 4. Section placement and copy → Task 5. Failure handling → Task 5 `catch`. `safeHttpUrl` extraction → Task 1. Testing list → Tasks 1, 3, 4, 5. Dependencies → merged before this plan.

**Placeholders.** None: every step carries the code or the exact command.

**Type consistency.** `build_index(articles, roster, now, window_days)` is defined in Task 3 and called in Task 4 with that signature. `WINDOW_DAYS` is exported in Task 3, imported in Task 4. `sort_for_review` is defined in Task 2 and used only there. Roster rows gain `slug` in Task 4, which Task 3's `build_index` already reads. `safeHttpUrl` is created in Task 1 and imported in Task 5.

**One ordering note for the implementer.** Task 3's live check asserts an *empty* result, because `roster()` has no slugs until Task 4. That is deliberate: it proves the slug guard rather than the happy path, which Task 4 step 9 covers.
