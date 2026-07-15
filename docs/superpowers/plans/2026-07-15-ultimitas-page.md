# "Las ultimitas" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A scraper that reads El Comercio's official RSS feeds for Keiko Fujimori / Fuerza Popular coverage and a public `/ultimitas` page that shows the current news day, fetched client-side from a data branch.

**Architecture:** `tools/elcomercio_scraper.py` (stdlib-only, git-free) fetches Arc XP RSS feeds, filters by keywords, merges history, and emits `ultimitas.json` (full history) + `today.json` (latest Lima news day) into a `--data-dir`. A GitHub Action runs it 4×/day against a worktree of the orphan `ultimitas-data` branch. The Astro page fetches `today.json` from raw.githubusercontent.com in the browser. Spec: `docs/superpowers/specs/2026-07-15-ultimitas-elcomercio-design.md`.

**Tech Stack:** Python 3.9+ stdlib (`urllib`, `xml.etree`, `zoneinfo`), unittest, GitHub Actions, Astro 5 + Tailwind v4.

## Global Constraints

- Branch: `feat/ultimitas-page` (already exists; spec committed). Conventional commits; rebase-only merges.
- All user-facing copy in **Spanish (Peru)**; code/comments/commits in English.
- Scraper is **stdlib-only** and must run on local Python 3.9.6 → every new/modified Python file needs `from __future__ import annotations`.
- **Never store or render `content:encoded`** (El Comercio's full article HTML — copyright). Only title, link, description snippet, author, date.
- The scraper never touches `main` or `tracking.json`; it only writes files into `--data-dir`.
- Feed data is third-party: the page must render it via `createElement`/`textContent`, **never `innerHTML`**.
- Frontend: invoke the `frontend-design` skill before any frontend code (CLAUDE.md hard rule). Component-folder convention: `src/components/Ultimitas/Ultimitas.astro` + `ultimitas.css` + `ultimitas.ts`; CSS imported in frontmatter is global → prefix all selectors with `.ultimitas-`.
- Tests run via `python3 -m unittest discover -s tools -p "test_*.py"` (CI already runs this — no CI change needed).
- Verify frontend visually from `http://localhost:3000` (never `file:///`). Brave headless clamps width to ≥500px — use the iframe trick for mobile shots.

---

### Task 1: Share `normalize()` via `watcher_common`

**Files:**
- Create: `tools/test_watcher_common.py`
- Modify: `tools/watcher_common.py` (add `normalize`)
- Modify: `tools/elperuano_reader.py:99-101` (drop local def, import instead)

**Interfaces:**
- Produces: `watcher_common.normalize(text: str) -> str` — lowercase + NFKD accent-strip. Used by `elperuano_reader.significant_terms` and Task 3's `item_matches`.

- [ ] **Step 1: Write the failing test**

Create `tools/test_watcher_common.py`:

```python
"""Unit tests for shared watcher helpers (no network)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from watcher_common import dedup_token, normalize


class NormalizeTest(unittest.TestCase):
    def test_lowercases_and_strips_accents(self):
        self.assertEqual(
            normalize("Formalización de la MYPE en el Perú"),
            "formalizacion de la mype en el peru",
        )

    def test_plain_ascii_unchanged(self):
        self.assertEqual(normalize("fuerza popular"), "fuerza popular")


class DedupTokenTest(unittest.TestCase):
    def test_prefix_and_stability(self):
        self.assertEqual(dedup_token("ec", "x"), dedup_token("ec", "x"))
        self.assertTrue(dedup_token("ec", "x").startswith("ec-"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tools.test_watcher_common -v` (from repo root)
Expected: FAIL — `ImportError: cannot import name 'normalize' from 'watcher_common'`

- [ ] **Step 3: Move the function**

In `tools/watcher_common.py`, add `import unicodedata` to the imports and this function after `dedup_token`:

```python
def normalize(text: str) -> str:
    """Lowercase + strip accents (NFKD) — shared matching normalizer."""
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))
```

In `tools/elperuano_reader.py`: delete the local `normalize` definition (lines 99–101) and the now-unused `import unicodedata`; add `normalize` to the existing `from watcher_common import ...` line. `significant_terms` keeps working unchanged (and `er.normalize` still resolves for any caller).

- [ ] **Step 4: Run the full tool test suite**

Run: `python3 -m unittest discover -s tools -p "test_*.py" -v`
Expected: PASS — new tests plus all 7 existing `test_elperuano_reader` tests.

- [ ] **Step 5: Commit**

```bash
git add tools/watcher_common.py tools/elperuano_reader.py tools/test_watcher_common.py
git commit -m "refactor: move normalize() into watcher_common for reuse"
```

---

### Task 2: Fixture + feed parsing + URL canonicalization

**Files:**
- Create: `tools/fixtures/elcomercio_rss_sample.xml`
- Create: `tools/elcomercio_scraper.py`
- Create: `tools/test_elcomercio_scraper.py`

**Interfaces:**
- Produces: `elcomercio_scraper.parse_feed(raw: bytes) -> list[dict]` — items `{title, url, summary, author, published}` (`url` canonical, `published` ISO 8601 with offset); `elcomercio_scraper.canonical_url(url: str) -> str`; constants `FEEDS`, `SOURCE = "El Comercio"`, `BROWSER_UA`.

- [ ] **Step 1: Create the fixture** (trimmed by design: `content:encoded` bodies replaced with a placeholder — we never commit El Comercio's copyrighted text)

Create `tools/fixtures/elcomercio_rss_sample.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
<title>El Comercio - Política</title>
<link>https://elcomercio.pe/politica/</link>
<item>
  <title>Fuerza Popular evaluará si pide auditoría a gobierno de Balcázar tras concluir transferencia</title>
  <link>https://elcomercio.pe/politica/fuerza-popular-evaluara-auditoria-noticia/?ref=ecr</link>
  <guid>https://elcomercio.pe/politica/fuerza-popular-evaluara-auditoria-noticia/</guid>
  <pubDate>Wed, 15 Jul 2026 05:01:00 -0500</pubDate>
  <description>La bancada analizará los informes de la comisión de transferencia antes de decidir.</description>
  <dc:creator>Redacción EC</dc:creator>
  <content:encoded><![CDATA[cuerpo omitido en el fixture — contenido de El Comercio]]></content:encoded>
</item>
<item>
  <title>Keiko Fujimori: JNE entrega este miércoles sus credenciales como presidenta electa</title>
  <link>https://elcomercio.pe/politica/keiko-fujimori-credenciales-jne-noticia/</link>
  <guid>https://elcomercio.pe/politica/keiko-fujimori-credenciales-jne-noticia/</guid>
  <pubDate>Tue, 14 Jul 2026 18:12:00 -0500</pubDate>
  <description>La ceremonia se realizará en la sede central del Jurado Nacional de Elecciones.</description>
  <content:encoded><![CDATA[cuerpo omitido en el fixture — contenido de El Comercio]]></content:encoded>
</item>
<item>
  <title>Mirtha Vásquez advierte «mal precedente» si se otorga pensión vitalicia a presidente Balcázar</title>
  <link>https://elcomercio.pe/politica/mirtha-vasquez-pension-vitalicia-noticia/</link>
  <guid>https://elcomercio.pe/politica/mirtha-vasquez-pension-vitalicia-noticia/</guid>
  <pubDate>Wed, 15 Jul 2026 03:04:00 -0500</pubDate>
  <description>La expremier cuestionó el pedido del presidente saliente ante el Congreso.</description>
  <dc:creator>Redacción EC</dc:creator>
</item>
<item>
  <title>Fuerza Popular evaluará si pide auditoría a gobierno de Balcázar tras concluir transferencia</title>
  <link>https://elcomercio.pe/politica/fuerza-popular-evaluara-auditoria-noticia/?ref=rss&amp;outputType=xml</link>
  <guid>https://elcomercio.pe/politica/fuerza-popular-evaluara-auditoria-noticia/?ref=rss</guid>
  <pubDate>Wed, 15 Jul 2026 05:01:00 -0500</pubDate>
  <description>La bancada analizará los informes de la comisión de transferencia antes de decidir.</description>
</item>
<item>
  <title>La jornada de Keiko Fujimori: reuniones en su oficina de San Isidro</title>
  <link>https://elcomercio.pe/politica/jornada-keiko-fujimori-san-isidro-noticia/</link>
  <guid>https://elcomercio.pe/politica/jornada-keiko-fujimori-san-isidro-noticia/</guid>
  <pubDate>Tue, 14 Jul 2026 09:00:00 -0500</pubDate>
</item>
</channel>
</rss>
```

(Item 4 duplicates item 1 under a different tracking query string — canonicalization test. Item 5 has no description — default test. Item 3 is the non-match.)

- [ ] **Step 2: Write the failing tests**

Create `tools/test_elcomercio_scraper.py`:

```python
"""Unit tests for the El Comercio scraper's deterministic stages (no network)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import elcomercio_scraper as ec

FIXTURE = (Path(__file__).resolve().parent / "fixtures" / "elcomercio_rss_sample.xml").read_bytes()


class CanonicalUrlTest(unittest.TestCase):
    def test_strips_query_and_fragment(self):
        self.assertEqual(
            ec.canonical_url("https://elcomercio.pe/politica/nota/?ref=rss&outputType=xml#top"),
            "https://elcomercio.pe/politica/nota/",
        )

    def test_plain_url_unchanged(self):
        self.assertEqual(ec.canonical_url("https://elcomercio.pe/politica/nota/"),
                         "https://elcomercio.pe/politica/nota/")


class ParseFeedTest(unittest.TestCase):
    def test_maps_all_items_with_expected_fields(self):
        items = ec.parse_feed(FIXTURE)
        self.assertEqual(len(items), 5)
        self.assertEqual(set(items[0]), {"title", "url", "summary", "author", "published"})

    def test_canonicalizes_link_and_parses_date(self):
        first = ec.parse_feed(FIXTURE)[0]
        self.assertEqual(first["url"], "https://elcomercio.pe/politica/fuerza-popular-evaluara-auditoria-noticia/")
        self.assertEqual(first["published"], "2026-07-15T05:01:00-05:00")
        self.assertEqual(first["author"], "Redacción EC")

    def test_missing_creator_and_description_default_to_empty(self):
        items = ec.parse_feed(FIXTURE)
        self.assertEqual(items[1]["author"], "")
        self.assertEqual(items[4]["summary"], "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m unittest tools.test_elcomercio_scraper -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'elcomercio_scraper'`

- [ ] **Step 4: Write the implementation**

Create `tools/elcomercio_scraper.py`:

```python
#!/usr/bin/env python3
"""Scrape El Comercio's RSS for Keiko Fujimori / Fuerza Popular coverage.

Feeds the public "Las ultimitas" page: matched headlines accumulate in
ultimitas.json (full history) and today.json (latest Lima news day — the only
file the page downloads). The tool is git-free: it reads/writes --data-dir and
the Action owns the ultimitas-data branch. Stdlib only.
See workflows/elcomercio_ultimitas.md.

Copyright: only title, link, description snippet, author and date are stored —
never content:encoded (the full article body belongs to El Comercio).

Usage:
  python3 tools/elcomercio_scraper.py --dry-run           # print matches, no writes
  python3 tools/elcomercio_scraper.py --data-dir <dir>    # merge into <dir>/*.json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from watcher_common import http_get, normalize

SOURCE = "El Comercio"
FEEDS = [
    "https://elcomercio.pe/arc/outboundfeeds/rss/category/politica/?outputType=xml",
    "https://elcomercio.pe/arc/outboundfeeds/rss/?outputType=xml",
]
BROWSER_UA = "Mozilla/5.0 (compatible; keikogobierna-ultimitas; +https://github.com/DianCotrina/keikogobierna)"
KEYWORDS = ["keiko fujimori", "keiko", "fuerza popular", "fujimorismo"]
LIMA = ZoneInfo("America/Lima")
NS = {"dc": "http://purl.org/dc/elements/1.1/"}


# ---- Stage 1: fetch + parse ----------------------------------------------------

def canonical_url(url: str) -> str:
    """Scheme + host + path only — El Comercio appends ?ref=… tracking params."""
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def parse_feed(raw: bytes) -> list[dict]:
    out: list[dict] = []
    for item in ET.fromstring(raw).iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            continue
        if not title or not link:
            continue
        out.append({
            "title": title,
            "url": canonical_url(link),
            "summary": (item.findtext("description") or "").strip(),
            "author": (item.findtext("dc:creator", default="", namespaces=NS) or "").strip(),
            "published": published.isoformat(),
        })
    return out
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m unittest tools.test_elcomercio_scraper -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add tools/elcomercio_scraper.py tools/test_elcomercio_scraper.py tools/fixtures/elcomercio_rss_sample.xml
git commit -m "feat: El Comercio RSS fetch and parse stage"
```

---

### Task 3: Keyword filter

**Files:**
- Modify: `tools/elcomercio_scraper.py` (add `item_matches`)
- Modify: `tools/test_elcomercio_scraper.py` (add `MatchTest`)

**Interfaces:**
- Consumes: `watcher_common.normalize` (Task 1), items from `parse_feed` (Task 2).
- Produces: `elcomercio_scraper.item_matches(item: dict) -> bool` — True when any `KEYWORDS` phrase appears in normalized `title + summary`.

- [ ] **Step 1: Write the failing tests** — append to `tools/test_elcomercio_scraper.py`:

```python
class MatchTest(unittest.TestCase):
    def test_fixture_matches_title_and_description(self):
        items = ec.parse_feed(FIXTURE)
        matched = [i for i in items if ec.item_matches(i)]
        self.assertEqual(len(matched), 4)  # items 1, 2, 4 (dup), 5 — not the Vásquez one

    def test_case_and_accent_insensitive(self):
        self.assertTrue(ec.item_matches({"title": "El FUJIMORISMO en el Congreso", "summary": ""}))
        self.assertTrue(ec.item_matches({"title": "Análisis", "summary": "La postura de Fuerza Popular"}))

    def test_unrelated_item_does_not_match(self):
        self.assertFalse(ec.item_matches({"title": "Temblor en Lima esta madrugada", "summary": "IGP reportó 4.5"}))
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tools.test_elcomercio_scraper -v`
Expected: FAIL — `AttributeError: module 'elcomercio_scraper' has no attribute 'item_matches'`

- [ ] **Step 3: Implement** — add to `tools/elcomercio_scraper.py` after the parse section:

```python
# ---- Stage 2: keyword filter ----------------------------------------------------

def item_matches(item: dict) -> bool:
    haystack = normalize(f"{item['title']} {item['summary']}")
    return any(keyword in haystack for keyword in KEYWORDS)
```

- [ ] **Step 4: Run to verify pass** — same command, expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/elcomercio_scraper.py tools/test_elcomercio_scraper.py
git commit -m "feat: keyword filter for Keiko/Fuerza Popular coverage"
```

---

### Task 4: History merge, today selection, emit + CLI

**Files:**
- Modify: `tools/elcomercio_scraper.py` (add merge/select/emit/CLI)
- Modify: `tools/test_elcomercio_scraper.py` (add `MergeTest`, `TodayTest`)

**Interfaces:**
- Produces:
  - `merge_history(existing: list, new: list, captured_iso: str) -> list` — dedup by canonical `url` (existing entry wins, keeps its `captured`), new entries gain `captured`, result sorted by `published` desc (parsed datetimes, not string compare — offsets differ).
  - `lima_day(published_iso: str) -> str`, `select_today(articles: list) -> tuple[str, list]` — latest Lima-calendar day with articles + that day's articles.
  - CLI: `--dry-run` | `--data-dir <dir>`; writes `ultimitas.json` `{generated, source, count, articles}` and `today.json` `{generated, source, date, articles}` (the file the page fetches).

- [ ] **Step 1: Write the failing tests** — append to `tools/test_elcomercio_scraper.py`:

```python
class MergeTest(unittest.TestCase):
    def test_dedupes_by_canonical_url_and_sorts_desc(self):
        items = [i for i in ec.parse_feed(FIXTURE) if ec.item_matches(i)]
        merged = ec.merge_history([], items, "2026-07-15T12:00:00+00:00")
        self.assertEqual(len(merged), 3)  # the ?ref= duplicate collapsed
        self.assertEqual([a["published"] for a in merged],
                         ["2026-07-15T05:01:00-05:00", "2026-07-14T18:12:00-05:00", "2026-07-14T09:00:00-05:00"])
        self.assertTrue(all(a["captured"] == "2026-07-15T12:00:00+00:00" for a in merged))

    def test_existing_entry_wins_and_keeps_captured(self):
        existing = [{"title": "old", "url": "https://elcomercio.pe/politica/nota/",
                     "summary": "", "author": "", "published": "2026-07-14T10:00:00-05:00",
                     "captured": "2026-07-14T16:00:00+00:00"}]
        new = [{"title": "new crawl of same nota", "url": "https://elcomercio.pe/politica/nota/",
                "summary": "", "author": "", "published": "2026-07-14T10:00:00-05:00"}]
        merged = ec.merge_history(existing, new, "2026-07-15T12:00:00+00:00")
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["title"], "old")
        self.assertEqual(merged[0]["captured"], "2026-07-14T16:00:00+00:00")


class TodayTest(unittest.TestCase):
    def test_selects_latest_lima_day(self):
        items = [i for i in ec.parse_feed(FIXTURE) if ec.item_matches(i)]
        merged = ec.merge_history([], items, "2026-07-15T12:00:00+00:00")
        day, day_articles = ec.select_today(merged)
        self.assertEqual(day, "2026-07-15")
        self.assertEqual(len(day_articles), 1)

    def test_utc_timestamps_bucket_to_lima_days(self):
        arts = [
            {"url": "a", "published": "2026-07-15T04:30:00+00:00"},  # 23:30 Jul 14 in Lima
            {"url": "b", "published": "2026-07-15T13:00:00+00:00"},  # 08:00 Jul 15 in Lima
        ]
        day, day_articles = ec.select_today(arts)
        self.assertEqual(day, "2026-07-15")
        self.assertEqual([a["url"] for a in day_articles], ["b"])

    def test_empty_history_is_safe(self):
        self.assertEqual(ec.select_today([]), ("", []))
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tools.test_elcomercio_scraper -v`
Expected: FAIL — `AttributeError: ... no attribute 'merge_history'`

- [ ] **Step 3: Implement** — add to `tools/elcomercio_scraper.py`:

```python
# ---- Stage 3: merge + today selection -------------------------------------------

def merge_history(existing: list[dict], new: list[dict], captured_iso: str) -> list[dict]:
    by_url = {a["url"]: a for a in existing}
    for item in new:
        if item["url"] not in by_url:
            by_url[item["url"]] = {**item, "captured": captured_iso}
    return sorted(by_url.values(), key=lambda a: datetime.fromisoformat(a["published"]), reverse=True)


def lima_day(published_iso: str) -> str:
    return datetime.fromisoformat(published_iso).astimezone(LIMA).date().isoformat()


def select_today(articles: list[dict]) -> tuple[str, list[dict]]:
    """Latest Lima-calendar day that has articles — today when there is news today."""
    if not articles:
        return "", []
    latest = max(lima_day(a["published"]) for a in articles)
    return latest, [a for a in articles if lima_day(a["published"]) == latest]


# ---- Orchestration ---------------------------------------------------------------

def run(data_dir: str | None, dry_run: bool) -> int:
    items: list[dict] = []
    failed = 0
    for feed in FEEDS:
        try:
            items.extend(parse_feed(http_get(feed, headers={"User-Agent": BROWSER_UA})))
        except Exception as err:  # one bad feed never kills the run
            print(f"WARN: feed failed: {feed}: {err}", file=sys.stderr)
            failed += 1
    if failed == len(FEEDS):
        print("ERROR: every feed failed", file=sys.stderr)
        return 1

    matched = [i for i in items if item_matches(i)]
    print(f"{len(items)} items fetched, {len(matched)} matched")

    if dry_run:
        for item in matched:
            print(f"[{item['published']}] {item['title'][:90]}")
        print("Dry run complete.")
        return 0

    data = Path(data_dir)
    data.mkdir(parents=True, exist_ok=True)
    history_path = data / "ultimitas.json"
    existing = json.loads(history_path.read_text())["articles"] if history_path.exists() else []
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    articles = merge_history(existing, matched, now_iso)
    day, day_articles = select_today(articles)

    history_path.write_text(json.dumps(
        {"generated": now_iso, "source": SOURCE, "count": len(articles), "articles": articles},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (data / "today.json").write_text(json.dumps(
        {"generated": now_iso, "source": SOURCE, "date": day, "articles": day_articles},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"History: {len(articles)} articles. today.json: {day} with {len(day_articles)} article(s).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print matches without writing files")
    parser.add_argument("--data-dir", help="directory holding ultimitas.json + today.json")
    args = parser.parse_args()
    if not args.dry_run and not args.data_dir:
        parser.error("--data-dir is required unless --dry-run")
    return run(args.data_dir, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the full suite**

Run: `python3 -m unittest discover -s tools -p "test_*.py" -v`
Expected: PASS — all tests (elcomercio 13, elperuano 7, watcher_common 3).

- [ ] **Step 5: Commit**

```bash
git add tools/elcomercio_scraper.py tools/test_elcomercio_scraper.py
git commit -m "feat: history merge, Lima today selection and scraper CLI"
```

---

### Task 5: Live dry-run + bootstrap the `ultimitas-data` branch

Bootstrapping now (before the frontend) means the page's raw.githubusercontent URL serves real data during development.

**Files:** none in the repo working tree (writes to the `ultimitas-data` branch only).

- [ ] **Step 1: Live dry-run against El Comercio**

Run: `python3 tools/elcomercio_scraper.py --dry-run`
Expected: `N items fetched, M matched` with a plausible list of Keiko/FP headlines. If the feed returns HTTP 403, switch `BROWSER_UA` to a plain browser string (`Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36`) and record the lesson in the SOP (Task 8).

- [ ] **Step 2: Create the orphan branch with real data and push**

```bash
cd /Users/diegocotrina/repos/keikogobierna
tmp=$(mktemp -d)
git worktree add --detach "$tmp"
git -C "$tmp" checkout --orphan ultimitas-data
git -C "$tmp" rm -rf . >/dev/null 2>&1 || true
python3 tools/elcomercio_scraper.py --data-dir "$tmp"
git -C "$tmp" add -A
git -C "$tmp" commit -m "chore: bootstrap ultimitas data"
git -C "$tmp" push origin HEAD:ultimitas-data
git worktree remove --force "$tmp"
```

Expected: push succeeds (rulesets only protect `main`). Note: use the repo's configured author identity (GitHub noreply email) — do not set github-actions[bot] locally.

- [ ] **Step 3: Verify the raw URL serves with CORS**

Run: `curl -sI "https://raw.githubusercontent.com/DianCotrina/keikogobierna/ultimitas-data/today.json" | grep -iE "HTTP|access-control-allow-origin|content-length"`
Expected: `HTTP/2 200` and `access-control-allow-origin: *`. Also `curl -s <same url> | python3 -m json.tool | head -30` shows `date` + `articles`.

---

### Task 6: The GitHub Action

**Files:**
- Create: `.github/workflows/ultimitas-scraper.yml`

**Interfaces:**
- Consumes: `tools/elcomercio_scraper.py --data-dir` (Task 4); the `ultimitas-data` branch (Task 5; the orphan-create fallback still covers a fresh repo).

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/ultimitas-scraper.yml`:

```yaml
name: ultimitas-scraper

on:
  schedule:
    - cron: '0 5,11,17,23 * * *' # Lima 00:00 / 06:00 / 12:00 / 18:00 — a today's-news page needs intraday runs
  workflow_dispatch:

permissions:
  contents: write # push the ultimitas-data branch

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Scrape El Comercio and update the ultimitas-data branch
        run: |
          set -e
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          tmp=$(mktemp -d)
          if git fetch origin ultimitas-data 2>/dev/null; then
            git worktree add "$tmp" origin/ultimitas-data
          else
            git worktree add --detach "$tmp"
            git -C "$tmp" checkout --orphan ultimitas-data
            git -C "$tmp" rm -rf . >/dev/null 2>&1 || true
          fi
          python3 tools/elcomercio_scraper.py --data-dir "$tmp"
          git -C "$tmp" add -A
          if git -C "$tmp" diff --cached --quiet; then
            echo "no news changes"
          else
            git -C "$tmp" commit -m "chore: ultimitas $(date -u +'%F %H:%MZ')"
            git -C "$tmp" push origin HEAD:ultimitas-data
          fi
```

- [ ] **Step 2: Sanity-check the YAML**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ultimitas-scraper.yml')); print('yaml ok')"` (if PyYAML is missing locally, `npx --yes js-yaml .github/workflows/ultimitas-scraper.yml > /dev/null && echo yaml ok`)
Expected: `yaml ok`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ultimitas-scraper.yml
git commit -m "ci: schedule El Comercio scraper 4x daily"
```

---

### Task 7: The `/ultimitas` page

**REQUIRED FIRST:** invoke the `frontend-design` skill before writing any of this task's code (CLAUDE.md hard rule).

**Files:**
- Create: `src/components/Ultimitas/Ultimitas.astro`, `src/components/Ultimitas/ultimitas.css`, `src/components/Ultimitas/ultimitas.ts`
- Create: `src/pages/ultimitas.astro`
- Modify: `src/layouts/Base.astro:14-20` (navLinks array)

**Interfaces:**
- Consumes: `today.json` from `https://raw.githubusercontent.com/DianCotrina/keikogobierna/ultimitas-data/today.json` — shape `{generated, source, date, articles: [{title, url, summary, author, published, captured}]}` (Tasks 4–5).
- Produces: page at `/ultimitas/`, nav key `ultimitas`.

- [ ] **Step 1: Add the nav entry** — in `src/layouts/Base.astro`, insert before the `100dias` entry:

```js
const navLinks = [
  { key: 'tablero', label: 'Resumen', href: '/#tablero' },
  { key: 'temas', label: 'Temas', href: '/#temas' },
  { key: 'metodologia', label: 'Metodología', href: '/#metodologia' },
  { key: 'actualizaciones', label: 'Actualizaciones', href: '/#actualizaciones' },
  { key: 'ultimitas', label: 'Ultimitas', href: '/ultimitas/' },
  { key: '100dias', label: '100 días', href: '/primeros-100-dias/' }
];
```

- [ ] **Step 2: Create the component module**

`src/components/Ultimitas/Ultimitas.astro`:

```astro
---
import './ultimitas.css';
---

<section class="mx-auto max-w-4xl px-5 sm:px-8 pb-16 sm:pb-20" aria-label="Últimas noticias de El Comercio">
  <p id="ultimitas-date" class="font-mono text-xs uppercase tracking-[0.18em] text-tintasuave" aria-live="polite">Cargando titulares…</p>

  <div id="ultimitas-list" class="mt-6 space-y-5">
    <div class="ultimitas-skeleton bg-white rounded-lg border border-tinta/10 shadow-card h-32" aria-hidden="true"></div>
    <div class="ultimitas-skeleton bg-white rounded-lg border border-tinta/10 shadow-card h-32" aria-hidden="true"></div>
    <div class="ultimitas-skeleton bg-white rounded-lg border border-tinta/10 shadow-card h-32" aria-hidden="true"></div>
  </div>

  <div id="ultimitas-error" class="hidden bg-white rounded-lg border border-tinta/10 shadow-card p-6 sm:p-7">
    <h2 class="font-sans font-bold text-lg">No se pudo cargar las noticias</h2>
    <p class="mt-2 text-sm leading-[1.7] text-tintasuave">Inténtalo de nuevo en unos minutos, o visita directamente la sección de política de El Comercio.</p>
    <p class="mt-3"><a href="https://elcomercio.pe/politica/" target="_blank" rel="noopener noreferrer" class="nav-link font-sans text-sm font-medium">El Comercio — Política ↗</a></p>
  </div>

  <p class="mt-10 border-t border-dashed border-tinta/20 pt-5 font-mono text-[0.65rem] text-tintafina leading-relaxed">Los titulares y resúmenes pertenecen a El Comercio y se muestran con enlace directo a la fuente. Este sitio no reproduce artículos completos.</p>
</section>

<script src="./ultimitas.ts"></script>
```

`src/components/Ultimitas/ultimitas.css` (global once imported — every selector prefixed):

```css
/* Ultimitas module — skeleton pulse + card entrance. */
.ultimitas-skeleton { animation: ultimitas-pulse 1.4s ease-in-out infinite; }
@keyframes ultimitas-pulse {
  0%, 100% { opacity: 0.55; }
  50% { opacity: 1; }
}

.ultimitas-card { animation: ultimitas-in 0.5s var(--ease-spring) backwards; }
.ultimitas-card:nth-child(2) { animation-delay: 0.06s; }
.ultimitas-card:nth-child(3) { animation-delay: 0.12s; }
.ultimitas-card:nth-child(4) { animation-delay: 0.18s; }
@keyframes ultimitas-in {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: none; }
}

@media (prefers-reduced-motion: reduce) {
  .ultimitas-skeleton, .ultimitas-card { animation: none; }
}
```

`src/components/Ultimitas/ultimitas.ts` (third-party text → `textContent` only, never `innerHTML`):

```ts
const DATA_URL = 'https://raw.githubusercontent.com/DianCotrina/keikogobierna/ultimitas-data/today.json';

interface Article {
  title: string;
  url: string;
  summary: string;
  author: string;
  published: string;
  captured: string;
}

const LIMA = 'America/Lima';
const dayFmt = new Intl.DateTimeFormat('es-PE', { day: 'numeric', month: 'long', year: 'numeric', timeZone: LIMA });
const timeFmt = new Intl.DateTimeFormat('es-PE', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: LIMA });

function limaToday(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: LIMA }).format(new Date());
}

function formatDay(isoDay: string): string {
  // Anchor at Lima noon so the calendar date never shifts across the UTC boundary.
  return dayFmt.format(new Date(`${isoDay}T12:00:00-05:00`));
}

function card(article: Article): HTMLElement {
  const el = document.createElement('article');
  el.className = 'ultimitas-card bg-white rounded-lg border border-tinta/10 shadow-card p-6 sm:p-7';

  const meta = document.createElement('p');
  meta.className = 'font-mono text-[0.65rem] uppercase tracking-[0.14em] text-tintafina';
  meta.textContent = `${timeFmt.format(new Date(article.published))} · El Comercio${article.author ? ` · ${article.author}` : ''}`;
  el.append(meta);

  const title = document.createElement('h2');
  title.className = 'font-sans font-bold text-lg mt-1.5 leading-snug';
  title.textContent = article.title;
  el.append(title);

  if (article.summary) {
    const summary = document.createElement('p');
    summary.className = 'mt-2 text-sm leading-[1.7] text-tintasuave';
    summary.textContent = article.summary;
    el.append(summary);
  }

  const linkWrap = document.createElement('p');
  linkWrap.className = 'mt-3';
  const link = document.createElement('a');
  link.href = article.url;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  link.className = 'nav-link font-sans text-sm font-medium';
  link.textContent = 'Leer en El Comercio →';
  linkWrap.append(link);
  el.append(linkWrap);

  return el;
}

async function load(): Promise<void> {
  const list = document.getElementById('ultimitas-list');
  const dateEl = document.getElementById('ultimitas-date');
  const errorEl = document.getElementById('ultimitas-error');
  if (!list || !dateEl || !errorEl) return;

  try {
    const resp = await fetch(DATA_URL, { cache: 'no-cache' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data: { date: string; articles: Article[] } = await resp.json();
    if (!data.date || !Array.isArray(data.articles) || data.articles.length === 0) {
      throw new Error('empty payload');
    }
    const suffix = data.date === limaToday() ? '' : ' · último día con noticias';
    dateEl.textContent = `Ultimitas del ${formatDay(data.date)}${suffix}`;
    list.replaceChildren(...data.articles.map(card));
  } catch (err) {
    console.error('ultimitas:', err);
    dateEl.textContent = 'Ultimitas';
    list.classList.add('hidden');
    errorEl.classList.remove('hidden');
  }
}

load();
```

- [ ] **Step 3: Create the page**

`src/pages/ultimitas.astro`:

```astro
---
import Base from '../layouts/Base.astro';
import Ultimitas from '../components/Ultimitas/Ultimitas.astro';

const title = 'Las ultimitas — keikogobierna';
const description = 'Lo último que publica El Comercio sobre Keiko Fujimori y Fuerza Popular, actualizado varias veces al día, con enlace directo a cada nota.';
---

<Base title={title} description={description} activeNav="ultimitas">
  <main>
    <section class="mx-auto max-w-4xl px-5 sm:px-8 pt-10 pb-10 sm:pt-14">
      <a href="/" class="nav-link font-mono text-xs text-tintasuave inline-flex items-center gap-2">← Volver al tablero</a>
      <p class="mt-7 font-mono text-xs uppercase tracking-[0.18em] text-tintasuave">Hemeroteca · El Comercio</p>
      <h1 class="relative inline-block font-display text-4xl sm:text-5xl mt-4 pb-3" style="letter-spacing:-0.03em">
        Las ultimitas
        <svg class="pen-stroke absolute left-0 bottom-0 w-full h-3" viewBox="0 0 300 22" fill="none" aria-hidden="true" preserveAspectRatio="none">
          <path d="M4 14 C 60 8, 120 18, 170 12 S 270 8, 296 13" stroke="#141417" stroke-width="5" stroke-linecap="round"/>
        </svg>
      </h1>
      <p class="mt-7 text-lg leading-[1.7] text-tintasuave max-w-xl">Lo que la prensa dice hoy sobre Keiko Fujimori y Fuerza Popular: titulares de El Comercio con enlace directo a cada nota.</p>
    </section>

    <div class="border-t border-tinta/10 bg-white/40 pt-10">
      <Ultimitas />
    </div>
  </main>
</Base>
```

- [ ] **Step 4: Verify visually**

1. `npm run dev` in the background (skip if already running — never a second instance).
2. Screenshot `http://localhost:3000/ultimitas` at 1280px after a ~3s delay (data fetch) — expect dated header + real cards from the bootstrapped branch.
3. Mobile 390px via the iframe-harness trick (headless clamps width to ≥500px).
4. Error state: temporarily change `DATA_URL` to `...ultimitas-data/nope.json`, screenshot (expect the error card + El Comercio link), then **revert**.
5. Check the nav shows "Ultimitas" and hover/focus states work (nav-link underline).
Fix anything off, re-screenshot (≥2 rounds per CLAUDE.md).

- [ ] **Step 5: Commit**

```bash
git add src/layouts/Base.astro src/pages/ultimitas.astro src/components/Ultimitas/
git commit -m "feat: Las ultimitas page fed from the ultimitas-data branch"
```

---

### Task 8: SOP + spec status

**Files:**
- Create: `workflows/elcomercio_ultimitas.md`
- Modify: `docs/superpowers/specs/2026-07-15-ultimitas-elcomercio-design.md:4` (Status line)

- [ ] **Step 1: Write the SOP**

Create `workflows/elcomercio_ultimitas.md`:

```markdown
# Workflow: El Comercio "Las ultimitas"

## Objective

Keep the public `/ultimitas` page fed with El Comercio's coverage of Keiko Fujimori /
Fuerza Popular. Unlike the evidence watcher and the El Peruano reader (which file
review issues), this pipeline publishes directly to a data branch — it is a news
listing, not evidence; it never touches `tracking.json` or `main`.

## How it works

1. `.github/workflows/ultimitas-scraper.yml` runs 4×/day (Lima 00:00/06:00/12:00/18:00)
   or on manual dispatch.
2. `tools/elcomercio_scraper.py` fetches the Arc XP RSS feeds in `FEEDS` (política +
   general), keeps items whose title+description match `KEYWORDS` (accent/case-
   insensitive), and merges them into the `ultimitas-data` branch via a git worktree:
   - `ultimitas.json` — full accumulated history, deduped by canonical URL (tracking
     params stripped). Never downloaded by the page.
   - `today.json` — the latest Lima-calendar day with matches. This is the only file
     the page fetches (from raw.githubusercontent.com, CORS-open, ~5-min edge cache).
3. `src/components/Ultimitas/ultimitas.ts` renders it client-side: dated header
   (labeled "último día con noticias" when it isn't today), one card per article,
   error fallback linking to El Comercio. Third-party text is rendered with
   `textContent` only.

## Tuning

- `KEYWORDS` / `FEEDS` in `tools/elcomercio_scraper.py`. Alberto/Kenji Fujimori
  false positives are accepted at launch; tighten keywords if they annoy.
- Copyright rule: only title, link, description snippet, author, date. Never store
  or render `content:encoded` (full article body) or hotlink their images.

## Local testing

```bash
python3 tools/elcomercio_scraper.py --dry-run              # live feeds, print matches
python3 tools/elcomercio_scraper.py --data-dir /tmp/ult    # write both JSON files
python3 -m unittest discover -s tools -p "test_*.py"       # offline unit tests
```

## Known constraints / lessons

- The feeds are Arc XP's standard outbound RSS (`/arc/outboundfeeds/rss/...`) —
  official but undocumented; if paths or fields change, the run fails loudly in
  Actions. Tag feeds (`/tags/keiko-fujimori/`) exist but return empty (2026-07-15).
- The general feed is ~1.5 MB; both feeds parse in memory fine.
- The branch push uses a `git worktree` on the orphan `ultimitas-data` branch so it
  never touches `main` (protected by the `protect-main` ruleset).
- A scraper failure can never break the site: the page serves the last committed
  `today.json`, and its error state links to El Comercio.
```

- [ ] **Step 2: Update the spec status line** to:

```markdown
**Status:** Design + spec approved (Diego, 2026-07-15); implemented in this branch
```

- [ ] **Step 3: Commit**

```bash
git add workflows/elcomercio_ultimitas.md docs/superpowers/specs/2026-07-15-ultimitas-elcomercio-design.md
git commit -m "docs: SOP for the El Comercio ultimitas pipeline"
```

---

### Task 9: Full verification, PR, merge, live run

- [ ] **Step 1: Full local checks**

```bash
python3 -m unittest discover -s tools -p "test_*.py"
npm test
npm run validate
npm run build
```
Expected: all green (build renders `/ultimitas/` into `dist/`).

- [ ] **Step 2: Rebase + push + PR**

```bash
git pull --rebase origin main
git push -u origin feat/ultimitas-page
gh pr create --title "feat: Las ultimitas — El Comercio scraper + today's-news page" --body "$(cat <<'EOF'
Adds the El Comercio pipeline and the public /ultimitas page per
docs/superpowers/specs/2026-07-15-ultimitas-elcomercio-design.md:

- tools/elcomercio_scraper.py — Arc XP RSS fetch → keyword filter → history merge
  → ultimitas.json + today.json on the ultimitas-data branch (bootstrapped).
- .github/workflows/ultimitas-scraper.yml — 4×/day cron + dispatch, worktree push.
- /ultimitas page + Ultimitas component module — client-side fetch of today.json,
  skeleton/error states, El Comercio attribution, nav entry.
- normalize() shared via watcher_common; unit tests ride the existing CI step.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Wait for CI, then rebase-merge**

```bash
gh pr checks --watch
gh pr merge --rebase
```
Expected: `checks` job green; merge succeeds (linear history).

- [ ] **Step 4: Live dispatch + verify**

```bash
gh workflow run ultimitas-scraper
sleep 60 && gh run list --workflow=ultimitas-scraper --limit 1
git fetch origin ultimitas-data && git log -1 --stat origin/ultimitas-data
curl -s "https://raw.githubusercontent.com/DianCotrina/keikogobierna/ultimitas-data/today.json" | python3 -m json.tool | head -20
```
Expected: run succeeds; branch has a fresh commit only if news changed since bootstrap; `today.json` valid. Re-check `http://localhost:3000/ultimitas` renders it.
