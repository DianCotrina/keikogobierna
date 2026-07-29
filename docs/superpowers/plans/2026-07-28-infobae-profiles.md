# Infobae Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give a reviewer everything Infobae's feed says about each minister, so the eighteen ministers with no ficha can get one written by hand.

**Architecture:** Infobae joins the shared `SOURCES` list, so every press consumer gains it at once. A new pure module matches feed items to ministers on **surname + cartera** (both required), and a new CLI prints a per-cartera review packet with `profession` and `bio` blank. Nothing is written automatically and no article body is ever read.

**Tech Stack:** Python 3.9+, stdlib only. `unittest` run as `python3 -m unittest discover -s tools/tests -t . -q`. Scrapers run as `python3 -m tools.scrapers.<name>`.

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-07-28-infobae-profiles-design.md`. Read it first.
- **Never read `content:encoded`.** The feed carries the full article body; this work uses `title`, `description`, `link` and `pubDate` only. `common/press_feeds.py` already parses exactly those.
- **`bio` is never machine-generated.** The tool leaves it blank for a person to write. Facts may be used; Infobae's sentences may not be copied into our data.
- **No AI in any pipeline.** Matching is deterministic regex + registry lookup.
- **Language:** code, comments and commit messages in English; every user-facing string in Spanish (Peru). CLI output is read by the site's maintainer and is Spanish, matching the other scrapers.
- **Rules modules are pure** — no I/O, no network, no CLI. Transport lives in `common/*_client.py`, orchestration in the top-level CLI.
- Run `python3 -m unittest discover -s tools/tests -t . -q`, `npm run validate` and `npm run build` before the final commit.

## File Structure

| File | Responsibility |
|---|---|
| `src/data/cabinet/portfolios.json` | **Modify.** Each portfolio gains an `aliases` array. |
| `tools/scrapers/common/cabinet_rules.py` | **Modify.** `_load_portfolio_lookup` folds `aliases` in. |
| `tools/scrapers/common/press_feeds.py` | **Modify.** Infobae joins `SOURCES`. |
| `tools/scrapers/common/press_rules.py` | **Modify.** `_mentions` matches given name + first surname. |
| `tools/scrapers/common/infobae_rules.py` | **Create.** Pure matching: feed items → carteras. |
| `tools/scrapers/infobae_profiles.py` | **Create.** CLI printing the review packet. |
| `tools/tests/fixtures/infobae_peru_20260728.xml` | **Create.** Real captured feed. |
| `tools/tests/test_infobae_rules.py` | **Create.** |
| `tools/tests/test_press_judicial.py` | **Modify.** Arnillas regression. |
| `src/pages/fuentes.astro`, `src/pages/ultimitas.astro`, `src/components/Ultimitas/Ultimitas.astro` | **Modify.** A fifth outlet, visitor-facing. |

---

### Task 1: Portfolio aliases

Infobae writes `MTC`, `Minem`, `Produce`, `canciller`. `portfolio_id()` knows none of them — the same gap that made the press scraper miss "ministro del Midagri" on swearing-in day.

**Files:**
- Modify: `src/data/cabinet/portfolios.json`
- Modify: `tools/scrapers/common/cabinet_rules.py`
- Test: `tools/tests/test_cabinet_rules.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `portfolio_id(name)` resolves acronyms and synonyms. Unchanged signature.

- [ ] **Step 1: Write the failing test**

Append to `tools/tests/test_cabinet_rules.py`:

```python
class PortfolioAliases(unittest.TestCase):
    """Ministries are named in the press by acronym far more often than in
    full — and "canciller" is never the ministry's name at all."""

    def test_acronyms_resolve(self):
        self.assertEqual(portfolio_id("MTC"), "m-transportes")
        self.assertEqual(portfolio_id("Minem"), "m-energia-minas")
        self.assertEqual(portfolio_id("Produce"), "m-produccion")
        self.assertEqual(portfolio_id("Midagri"), "m-agrario")
        self.assertEqual(portfolio_id("Minsa"), "m-salud")
        self.assertEqual(portfolio_id("Mincetur"), "m-comercio-exterior")

    def test_canciller_is_relaciones_exteriores(self):
        self.assertEqual(portfolio_id("canciller"), "m-relaciones-exteriores")

    def test_aliases_are_case_and_accent_insensitive(self):
        self.assertEqual(portfolio_id("minem"), "m-energia-minas")
        self.assertEqual(portfolio_id("MIDAGRI"), "m-agrario")

    def test_every_alias_is_unique_across_portfolios(self):
        # A shared alias would make portfolio_id ambiguous and silently return
        # None, dropping a minister from the roster with no error.
        import json
        from tools.scrapers.common.cabinet_rules import PORTFOLIOS_PATH
        seen = {}
        for p in json.loads(PORTFOLIOS_PATH.read_text(encoding="utf-8"))["portfolios"]:
            for alias in p.get("aliases", []):
                self.assertNotIn(alias.lower(), seen,
                                 f"{alias} claimed by {seen.get(alias.lower())} and {p['id']}")
                seen[alias.lower()] = p["id"]

    def test_existing_resolution_still_works(self):
        self.assertEqual(portfolio_id("Ministerio de Educación"), "m-educacion")
        self.assertEqual(portfolio_id("Desarrollo Agrario y Riego"), "m-agrario")
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest discover -s tools/tests -t . -q`
Expected: FAIL — `portfolio_id("MTC")` returns `None`.

- [ ] **Step 3: Add aliases to the registry**

In `src/data/cabinet/portfolios.json`, add an `aliases` array to each portfolio. Exact values:

| id | aliases |
|---|---|
| `pcm` | `["PCM", "Premier"]` |
| `m-relaciones-exteriores` | `["RREE", "Cancillería", "Canciller"]` |
| `m-defensa` | `["Mindef"]` |
| `m-economia` | `["MEF"]` |
| `m-interior` | `["Mininter"]` |
| `m-justicia` | `["Minjus", "Minjusdh"]` |
| `m-educacion` | `["Minedu"]` |
| `m-salud` | `["Minsa"]` |
| `m-agrario` | `["Midagri"]` |
| `m-trabajo` | `["MTPE"]` |
| `m-produccion` | `["Produce"]` |
| `m-comercio-exterior` | `["Mincetur"]` |
| `m-energia-minas` | `["Minem"]` |
| `m-transportes` | `["MTC"]` |
| `m-vivienda` | `["Vivienda"]` |
| `m-mujer` | `["Mimp"]` |
| `m-ambiente` | `["Minam"]` |
| `m-cultura` | `["Mincul"]` |
| `m-desarrollo-social` | `["Midis"]` |

- [ ] **Step 4: Fold aliases into the lookup**

In `tools/scrapers/common/cabinet_rules.py`, change `_load_portfolio_lookup`:

```python
def _load_portfolio_lookup() -> dict:
    """Folded ministry name -> registry id, built from the committed registry so
    the parser can never invent a cartera.

    `aliases` carries the acronyms and synonyms the press actually prints —
    "MTC", "Minem", "canciller" — which no ministry's own name contains.
    """
    data = json.loads(PORTFOLIOS_PATH.read_text(encoding="utf-8"))
    lookup = {}
    for portfolio in data["portfolios"]:
        names = [portfolio["name"], portfolio["short"], portfolio["slug"].replace("-", " ")]
        names += portfolio.get("aliases", [])
        for name in names:
            lookup[_strip_article(_fold(name))] = portfolio["id"]
    return lookup
```

- [ ] **Step 5: Run the tests**

Run: `python3 -m unittest discover -s tools/tests -t . -q`
Expected: PASS. Also run `npm run validate` — the cabinet validator reads the same file and must still accept it.

- [ ] **Step 6: Commit**

```bash
git add src/data/cabinet/portfolios.json tools/scrapers/common/cabinet_rules.py tools/tests/test_cabinet_rules.py
git commit -m "feat: resolve ministries by the acronyms the press actually prints"
```

---

### Task 2: Infobae joins the shared feeds

**Files:**
- Modify: `tools/scrapers/common/press_feeds.py`
- Create: `tools/tests/fixtures/infobae_peru_20260728.xml`
- Test: `tools/tests/test_ultimitas_scraper.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `SOURCES` contains `{"name": "Infobae", "feeds": [...]}`. Every consumer of `fetch_sources()` gains it.

- [ ] **Step 1: Capture the real feed as a fixture**

```bash
python3 - <<'PY'
import urllib.request
from pathlib import Path
URL = "https://www.infobae.com/arc/outboundfeeds/rss/category/peru/?outputType=xml"
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
raw = urllib.request.urlopen(req, timeout=45).read()
Path("tools/tests/fixtures/infobae_peru_20260728.xml").write_bytes(raw)
print("saved", len(raw), "bytes")
PY
```

Do not hand-edit the file. Tests assert against what Infobae actually published.

- [ ] **Step 2: Write the failing test**

Append to `tools/tests/test_ultimitas_scraper.py`:

```python
INFOBAE_FIXTURE = (Path(__file__).resolve().parent / "fixtures" / "infobae_peru_20260728.xml").read_bytes()


class InfobaeFeedTest(unittest.TestCase):
    def test_infobae_is_configured(self):
        self.assertIn("Infobae", [s["name"] for s in us.SOURCES])

    def test_real_feed_slice_parses_with_all_fields(self):
        items = us.parse_feed(INFOBAE_FIXTURE, "Infobae")
        self.assertGreater(len(items), 50)
        for item in items:
            self.assertEqual(set(item), {"title", "url", "summary", "author", "published", "source"})
            self.assertTrue(item["title"])
            self.assertTrue(item["url"].startswith("https://"))
            self.assertEqual(item["source"], "Infobae")

    def test_summaries_carry_the_biographical_detail(self):
        # The whole point: profession sits in the feed's own description, so no
        # article body ever needs reading.
        items = us.parse_feed(INFOBAE_FIXTURE, "Infobae")
        self.assertTrue(any(len(i["summary"]) > 80 for i in items))
```

- [ ] **Step 3: Run it and watch it fail**

Run: `python3 -m unittest discover -s tools/tests -t . -q`
Expected: FAIL — `"Infobae"` not in `SOURCES`.

- [ ] **Step 4: Add the source**

In `tools/scrapers/common/press_feeds.py`, append to `SOURCES`:

```python
    {"name": "Infobae", "feeds": [
        "https://www.infobae.com/arc/outboundfeeds/rss/category/peru/?outputType=xml",
    ]},
```

- [ ] **Step 5: Run the tests, then the feeds live**

```bash
python3 -m unittest discover -s tools/tests -t . -q
python3 -m tools.scrapers.cabinet_scraper --press --dry-run | head -3
```

Expected: tests pass; the live run reports more notes than before (roughly 100 more) and no `AVISO: fuentes caídas`.

- [ ] **Step 6: Commit**

```bash
git add tools/scrapers/common/press_feeds.py tools/tests/fixtures/infobae_peru_20260728.xml tools/tests/test_ultimitas_scraper.py
git commit -m "feat: add Infobae to the shared press sources"
```

---

### Task 3: Judicial signals stop missing a sitting minister

Infobae carries *"Ministro Mauricio Arnillas recibió prisión suspendida… declaró una condena por lesiones culposas"*. `_mentions` requires every token of the roster name, and the roster says "Mauricio Arnillas Gonzales" while the headline says "Mauricio Arnillas". It misses.

**Files:**
- Modify: `tools/scrapers/common/press_rules.py`
- Test: `tools/tests/test_press_judicial.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `_mentions(words: set, name_tokens: list) -> bool` — now requires the first two tokens rather than all.

- [ ] **Step 1: Write the failing test**

Append to `tools/tests/test_press_judicial.py`:

```python
class NameVariants(unittest.TestCase):
    """Adopting full official names from El Peruano made the roster longer than
    the names headlines print. The matcher has to tolerate the tail."""

    def test_a_headline_without_the_second_surname_still_matches(self):
        article = item(
            "Ministro Mauricio Arnillas recibió prisión suspendida y denigró a una manifestante",
            summary="El nuevo titular de Vivienda declaró una condena por lesiones culposas",
        )
        signals = judicial_signals([article], ["Mauricio Arnillas Gonzales"])
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["person_name"], "Mauricio Arnillas Gonzales")

    def test_a_shared_surname_alone_is_still_not_enough(self):
        # "Guardaespaldas del Rey de España se roba la atención" must not match
        # Rafael Rey Rey, the transport minister.
        article = item("Guardaespaldas del Rey de España acusado de agredir a un fotógrafo")
        self.assertEqual(judicial_signals([article], ["Rafael Rey Rey"]), [])

    def test_a_single_token_roster_name_matches_nothing(self):
        article = item("Fiscalía investiga a Rey por presunta colusión")
        self.assertEqual(judicial_signals([article], ["Rey"]), [])

    def test_the_given_name_is_required(self):
        article = item("Fiscalía investiga a Arnillas por presunta colusión")
        self.assertEqual(judicial_signals([article], ["Mauricio Arnillas Gonzales"]), [])
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest discover -s tools/tests -t . -q`
Expected: FAIL on the first test — zero signals, because "gonzales" is absent from the headline.

- [ ] **Step 3: Relax the match to given name + first surname**

In `tools/scrapers/common/press_rules.py`, replace `_mentions`:

```python
def _mentions(words: set, name_tokens: list) -> bool:
    """Whether a folded article names this person.

    The given name and the first surname must both appear; anything after them
    is optional. Peruvian rosters carry both surnames — "Mauricio Arnillas
    Gonzales" — while headlines print one, so requiring every token missed a
    conviction on a sitting minister. Requiring two still rejects "Guardaespaldas
    del Rey de España" for Rafael Rey Rey, because "rafael" is absent.

    A single-token name is rejected: one surname is not an identification.
    """
    if len(name_tokens) < 2:
        return False
    return all(token in words for token in name_tokens[:2])
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m unittest discover -s tools/tests -t . -q`
Expected: PASS, including the existing rejections — "Putin acusa a Occidente", "La Premier League", "dos hombres acusados de vender estampillas falsas".

- [ ] **Step 5: Check it live**

```bash
python3 -m tools.scrapers.cabinet_scraper --press --dry-run | tail -8
```

Expected: at least one judicial signal now, naming Arnillas. Read the headline it reports and confirm it is genuinely about the minister.

- [ ] **Step 6: Commit**

```bash
git add tools/scrapers/common/press_rules.py tools/tests/test_press_judicial.py
git commit -m "fix: judicial signals missed a minister whose roster name is longer than the headline"
```

---

### Task 4: Matching feed items to ministers

**Files:**
- Create: `tools/scrapers/common/infobae_rules.py`
- Create: `tools/tests/test_infobae_rules.py`

**Interfaces:**
- Consumes: `portfolio_id` from `common.cabinet_rules` (alias-aware after Task 1); `fold` from `common.press_rules`.
- Produces:
  - `profile_items(articles: list, roster: list) -> dict` — `roster` is `[{"portfolio": str, "person_name": str}]`; returns `{portfolio_id: [item, ...]}`, best first. Each item is the feed record plus nothing added.
  - `is_profile(title: str) -> bool`.

- [ ] **Step 1: Write the failing test**

Create `tools/tests/test_infobae_rules.py`:

```python
"""Matching Infobae items to ministers.

Fixture is the real Peru feed captured 2026-07-28, the evening the cabinet was
sworn in. Nothing here is invented: every headline asserted on was published.
"""
import unittest
from pathlib import Path

from tools.scrapers.common import press_feeds
from tools.scrapers.common.infobae_rules import is_profile, profile_items

FIXTURE = (Path(__file__).resolve().parent / "fixtures" / "infobae_peru_20260728.xml").read_bytes()
ARTICLES = press_feeds.parse_feed(FIXTURE, "Infobae")

ROSTER = [
    {"portfolio": "pcm", "person_name": "Luis Galarreta Velarde"},
    {"portfolio": "m-economia", "person_name": "Elmer Cuba Bustinza"},
    {"portfolio": "m-relaciones-exteriores", "person_name": "Carlos Espá y Garcés-Alvear"},
    {"portfolio": "m-defensa", "person_name": "Rafael Belaunde Llosa"},
    {"portfolio": "m-interior", "person_name": "César Astudillo Salcedo"},
    {"portfolio": "m-agrario", "person_name": "Marco Vinelli Ruiz"},
    {"portfolio": "m-energia-minas", "person_name": "Guillermo Shinno Huamaní"},
    {"portfolio": "m-transportes", "person_name": "Rafael Rey Rey"},
    {"portfolio": "m-salud", "person_name": "Luis Dyer Fernández"},
    {"portfolio": "m-educacion", "person_name": "José Antonio Chang Escobedo"},
    {"portfolio": "m-cultura", "person_name": "Alberto Beingolea Delgado"},
    {"portfolio": "m-ambiente", "person_name": "Vladimiro Huaroc Portocarrero"},
    {"portfolio": "m-mujer", "person_name": "Mara Seminario Marón"},
    {"portfolio": "m-comercio-exterior", "person_name": "Roger Valencia Espinoza"},
    {"portfolio": "m-trabajo", "person_name": "Juan Sheput Moore"},
    {"portfolio": "m-vivienda", "person_name": "Mauricio Arnillas Gonzales"},
    {"portfolio": "m-justicia", "person_name": "Ernesto Álvarez Miranda"},
    {"portfolio": "m-desarrollo-social", "person_name": "Maritza Canales Martínez"},
    {"portfolio": "m-produccion", "person_name": "Juan Carlos Requejo Alemán"},
]

FOUND = profile_items(ARTICLES, ROSTER)


class Coverage(unittest.TestCase):
    def test_most_of_the_cabinet_is_covered(self):
        self.assertGreaterEqual(len(FOUND), 12, sorted(FOUND))

    def test_every_key_is_a_roster_portfolio(self):
        self.assertTrue(set(FOUND) <= {r["portfolio"] for r in ROSTER})

    def test_no_cartera_comes_back_empty(self):
        for pid, items in FOUND.items():
            self.assertTrue(items, pid)


class MatchingIsTwoKeyed(unittest.TestCase):
    def test_a_given_name_variant_still_matches_on_surname_plus_cartera(self):
        # The roster says "Mara Seminario Marón"; Infobae writes "María
        # Seminario". Name-only matching loses her; the cartera saves it.
        self.assertIn("m-mujer", FOUND)

    def test_a_shared_surname_without_a_cartera_matches_nothing(self):
        # "Guardaespaldas del Rey de España se roba la atención" carries the
        # surname of the transport minister and no ministry at all.
        for item in FOUND.get("m-transportes", []):
            self.assertNotIn("guardaespaldas", item["title"].lower())

    def test_an_unrelated_item_is_never_matched(self):
        for items in FOUND.values():
            for item in items:
                self.assertNotIn("Copa Federación", item["title"])


class Ranking(unittest.TestCase):
    def test_a_profile_piece_outranks_plain_news(self):
        for pid, items in FOUND.items():
            profiles = [i for i, it in enumerate(items) if is_profile(it["title"])]
            if profiles and len(items) > 1:
                self.assertEqual(profiles[0], 0, f"{pid}: {items[0]['title']}")

    def test_is_profile_recognises_the_usual_shapes(self):
        self.assertTrue(is_profile("¿Quién es Marco Vinelli Ruiz? Perfil y hoja de vida"))
        self.assertTrue(is_profile("Conoce a Juan Carlos Requejo, nuevo titular de Produce"))
        self.assertTrue(is_profile("Juan Sheput asume el Ministerio de Trabajo: trayectoria política"))
        self.assertFalse(is_profile("Perú expresa solidaridad con Japón tras terremoto"))


class Purity(unittest.TestCase):
    def test_the_matcher_never_reads_an_article_body(self):
        # The feed carries content:encoded; parse_feed does not expose it and
        # nothing here may reintroduce it.
        for items in FOUND.values():
            for item in items:
                self.assertEqual(set(item),
                                 {"title", "url", "summary", "author", "published", "source"})

    def test_an_empty_roster_matches_nothing(self):
        self.assertEqual(profile_items(ARTICLES, []), {})

    def test_no_articles_is_safe(self):
        self.assertEqual(profile_items([], ROSTER), {})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python3 -m unittest discover -s tools/tests -t . -q`
Expected: FAIL — `No module named 'tools.scrapers.common.infobae_rules'`.

- [ ] **Step 3: Implement**

Create `tools/scrapers/common/infobae_rules.py`:

```python
"""Match press items to the minister they profile.

The JNE covers only ministers who stood for election. For everyone else the
press is the only public account of who they are, and Infobae publishes a
profile for nearly the whole cabinet — with the profession in the feed's own
summary, so no article body is ever read.

Discovery only. This proposes reading material; a person writes the ficha.

Pure functions: no I/O, no network.
"""
from __future__ import annotations

import re

from .cabinet_rules import portfolio_id
from .press_rules import fold

# Headline shapes that mark a piece as a profile rather than a news item.
_PROFILE = re.compile(
    r"qui[ée]n\s+es|perfil|trayectoria|hoja\s+de\s+vida|conoce\s+a|"
    r"qui[ée]nes\s+integran|este\s+es\s+su",
    re.I)

# A ministry named anywhere in the text, however the outlet writes it: in full,
# by short name, or by the acronyms and synonyms portfolios.json now carries.
_MINISTRY = re.compile(
    r"(?:ministr[oa]|ministerio|titular)\s+(?:de\s+la|del|de|en\s+el)?\s*([\wÁÉÍÓÚÑáéíóúñ.\- ]{3,60})"
    r"|\b(MTC|MEF|Minem|Minsa|Minedu|Midagri|Mincetur|Produce|Mininter|Mindef|"
    r"Minjus|Minjusdh|MTPE|Mimp|Minam|Mincul|Midis|RREE|PCM)\b"
    r"|\b(canciller[ií]a|canciller|premier)\b",
    re.I)


def is_profile(title: str) -> bool:
    """Whether a headline reads as a profile piece rather than plain news."""
    return bool(_PROFILE.search(title or ""))


def _carteras_named(text: str) -> set:
    """Every registry id the text names, by any spelling the registry knows."""
    found = set()
    for match in _MINISTRY.finditer(text or ""):
        for group in match.groups():
            if not group:
                continue
            # A ministry phrase runs on ("ministro de Economía y Finanzas del
            # gobierno de..."), so try the longest prefix first and shorten.
            words = group.split()
            for length in range(len(words), 0, -1):
                pid = portfolio_id(" ".join(words[:length]).strip(" ,.;:"))
                if pid:
                    found.add(pid)
                    break
    return found


def _surnames(person_name: str) -> list:
    """The surname tokens of a Peruvian full name — everything after the given
    name. "Mara Seminario Marón" -> ["seminario", "maron"]."""
    tokens = [t for t in fold(person_name).split() if len(t) > 2]
    return tokens[1:] if len(tokens) > 1 else tokens


def profile_items(articles: list, roster: list) -> dict:
    """Feed items about each minister, keyed by cartera, best first.

    A match needs two keys: the item must name one of the person's surnames
    *and* resolve to their cartera. Either alone is wrong in a way the live
    feed demonstrates — "María Seminario" defeats name matching because the
    roster says "Mara", and "Guardaespaldas del Rey de España" defeats surname
    matching because the transport minister is Rafael Rey Rey.
    """
    by_portfolio: dict = {}

    for article in articles:
        title = article.get("title") or ""
        summary = article.get("summary") or ""
        blob = f"{title} {summary}"
        words = set(fold(blob).split())
        carteras = _carteras_named(blob)
        if not carteras:
            continue

        for person in roster:
            pid = person.get("portfolio")
            if pid not in carteras:
                continue
            if not any(s in words for s in _surnames(person.get("person_name", ""))):
                continue
            by_portfolio.setdefault(pid, []).append(article)
            break

    for pid, items in by_portfolio.items():
        items.sort(key=lambda a: (not is_profile(a.get("title") or ""),
                                  -_epoch(a.get("published") or "")))
    return by_portfolio


def _epoch(published: str) -> float:
    """Sortable timestamp; unparseable dates sort last."""
    from datetime import datetime
    try:
        return datetime.fromisoformat(published).timestamp()
    except (ValueError, TypeError):
        return 0.0
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m unittest discover -s tools/tests -t . -q`
Expected: PASS. If coverage is below 12, print what matched and check whether a real profile is being missed for a reason worth fixing — do not lower the threshold to make the test green.

- [ ] **Step 5: Commit**

```bash
git add tools/scrapers/common/infobae_rules.py tools/tests/test_infobae_rules.py
git commit -m "feat: match press items to the minister they profile"
```

---

### Task 5: The review-packet CLI

**Files:**
- Create: `tools/scrapers/infobae_profiles.py`

**Interfaces:**
- Consumes: `profile_items`, `is_profile` from `common.infobae_rules`; `fetch_sources` from `common.press_feeds`; `PORTFOLIOS_PATH`, `CABINET_DIR` from `common.cabinet_rules`.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Write the CLI**

Create `tools/scrapers/infobae_profiles.py`:

```python
#!/usr/bin/env python3
"""Gather what the press says about each minister, for a person to write the ficha.

Eighteen of nineteen ministers have no dossier, and the JNE cannot supply one:
a hoja de vida exists only for people who stood for election. The press is the
remaining public account, and Infobae profiles nearly the whole cabinet.

This prints a review packet — headline, summary, link, per cartera — and a
draft people.json entry with `profession` and `bio` blank.

It never writes. It never reads an article body: the summaries below come from
the feed's own <description>, the same field /ultimitas/ already displays. The
site tells its readers it does not reproduce full articles, and this keeps that
promise. Facts from these notes are yours to use; the sentences are Infobae's,
so write the ficha in your own words and cite the note.

Usage:
  python3 -m tools.scrapers.infobae_profiles
  python3 -m tools.scrapers.infobae_profiles --portfolio m-vivienda
"""
from __future__ import annotations

import argparse
import json
import sys

from tools.scrapers.common.cabinet_rules import CABINET_DIR, PORTFOLIOS_PATH
from tools.scrapers.common.infobae_rules import profile_items
from tools.scrapers.common.press_feeds import fetch_sources
from tools.scrapers.common.jne_rules import _slug


def roster() -> list:
    """Every cartera with a named holder — appointed or announced."""
    people = {p["slug"]: p for p in json.loads(
        (CABINET_DIR / "people.json").read_text(encoding="utf-8"))["people"]}
    announcements = json.loads(
        (CABINET_DIR / "announcements.json").read_text(encoding="utf-8"))["announcements"]

    rows = []
    for a in announcements:
        linked = people.get(a.get("person") or "")
        rows.append({
            "portfolio": a["portfolio"],
            "person_name": (linked or {}).get("name") or a["person_name"],
            "has_ficha": bool(linked),
        })
    return rows


def portfolio_names() -> dict:
    return {p["id"]: p["short"] for p in json.loads(
        PORTFOLIOS_PATH.read_text(encoding="utf-8"))["portfolios"]}


def draft(person_name: str, sources: list) -> str:
    """The people.json skeleton, with what only a person can write left blank."""
    return json.dumps({
        "slug": _slug(person_name),
        "name": person_name,
        "profession": "",
        "bio": "",
        "sources": sources,
        "judicial": [],
    }, ensure_ascii=False, indent=2)


def run(only: str | None) -> int:
    articles, failed = fetch_sources()
    if failed:
        print(f"AVISO: fuentes caídas: {', '.join(failed)}", file=sys.stderr)

    infobae = [a for a in articles if a.get("source") == "Infobae"]
    print(f"{len(articles)} notas en total, {len(infobae)} de Infobae\n")

    people = roster()
    found = profile_items(infobae, people)
    names = portfolio_names()

    shown = 0
    for person in people:
        pid = person["portfolio"]
        if only and pid != only:
            continue
        items = found.get(pid, [])
        if not items:
            continue
        shown += 1

        mark = " · ya tiene ficha" if person["has_ficha"] else ""
        print(f"{names.get(pid, pid).upper()} — {person['person_name']}{mark}")
        for item in items:
            print(f"  Infobae · {item['published'][:10]}")
            print(f"  «{' '.join(item['title'].split())}»")
            if item["summary"]:
                print(f"   {' '.join(item['summary'].split())[:220]}")
            print(f"   {item['url']}")
        if not person["has_ficha"]:
            print("\n  borrador para src/data/cabinet/people.json:")
            sources = [{"label": "Infobae", "url": items[0]["url"], "kind": "press"}]
            print("  " + draft(person["person_name"], sources).replace("\n", "\n  "))
        print()

    missing = [p for p in people if p["portfolio"] not in found and not (only and p["portfolio"] != only)]
    if missing:
        print("Sin nota de perfil en el feed de hoy:")
        for person in missing:
            print(f"  {names.get(person['portfolio'], person['portfolio']):28s} {person['person_name']}")

    print(f"\n{shown} cartera(s) con material. Escribe `profession` y `bio` con tus "
          "propias palabras y cita la nota: los hechos son de dominio público, las "
          "frases son de Infobae. Este comando no escribe nada.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio", help="limita el informe a una cartera (id del registro)")
    args = parser.parse_args()
    return run(args.portfolio)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it live**

```bash
python3 -m tools.scrapers.infobae_profiles | head -40
python3 -m tools.scrapers.infobae_profiles --portfolio m-vivienda
```

Expected: at least a dozen carteras with material; Arnillas' entry shows the prisión-suspendida piece; the closing line states nothing was written. Confirm no file changed: `git status --short` must show nothing but the new file.

- [ ] **Step 3: Commit**

```bash
git add tools/scrapers/infobae_profiles.py
git commit -m "feat: print a per-minister press review packet for writing fichas"
```

---

### Task 6: A fifth outlet, visitor-facing

`SOURCES` is what `/ultimitas/` renders, so adding Infobae changes what visitors are told the page covers.

**Files:**
- Modify: `src/pages/ultimitas.astro`
- Modify: `src/components/Ultimitas/Ultimitas.astro`
- Modify: `src/pages/fuentes.astro`
- Modify: `workflows/ultimitas_scraper.md`

**Interfaces:**
- Consumes: Task 2's `SOURCES` entry.
- Produces: nothing.

- [ ] **Step 1: Update the Ultimitas copy**

In `src/pages/ultimitas.astro`, both the `description` const and the intro paragraph currently read «El Comercio, La República, RPP y Gestión». Change both to «El Comercio, La República, RPP, Gestión e Infobae». Note the conjunction: Spanish uses **e** rather than **y** before a word starting with *i*.

- [ ] **Step 2: Add the outlet's fallback link**

In `src/components/Ultimitas/Ultimitas.astro`, the error block lists one link per outlet. Append, in the same shape as its siblings:

```astro
<a href="https://www.infobae.com/peru/" target="_blank" rel="noopener noreferrer" class="nav-link font-sans text-sm font-medium">Infobae — Perú ↗</a>
```

- [ ] **Step 3: Add Infobae to the sources page**

In `src/pages/fuentes.astro`, the automatic-sources list has one entry per outlet with `name` and `verifies`. Add, matching the existing shape:

```js
{
  name: 'Infobae',
  verifies: 'Cobertura política peruana de Infobae; aporta titulares y perfiles de los ministros a «Las ultimitas».',
},
```

Check the surrounding object for other required keys (e.g. a URL field) and fill them the way its siblings do.

- [ ] **Step 4: Update the workflow doc**

In `workflows/ultimitas_scraper.md`, add Infobae wherever the four outlets are enumerated.

- [ ] **Step 5: Build and look at it**

```bash
npm run build
npm run dev &
```

Screenshot `http://localhost:3000/ultimitas/` and `http://localhost:3000/fuentes/`. Confirm the fifth source chip appears and the filter still works. Do not claim it renders without looking.

- [ ] **Step 6: Commit**

```bash
git add src/pages/ultimitas.astro src/components/Ultimitas/Ultimitas.astro src/pages/fuentes.astro workflows/ultimitas_scraper.md
git commit -m "feat: Infobae joins the outlets shown on ultimitas and fuentes"
```

---

### Task 7: Documentation and full verification

**Files:**
- Modify: `docs/ARCHITECTURE.md`
- Create: `workflows/minister_profiles.md`

**Interfaces:**
- Consumes: everything above.
- Produces: nothing.

- [ ] **Step 1: Document the module**

In `docs/ARCHITECTURE.md`, add `infobae_rules` to the `common/` tree listing in the Discovery pipeline section, and Infobae to the Plane-2 mermaid node that currently reads «El Comercio · La República<br/>RPP · Gestión — RSS».

- [ ] **Step 2: Write the workflow**

Create `workflows/minister_profiles.md` covering: the objective (a ficha for every minister); why the JNE cannot supply it; running `python3 -m tools.scrapers.infobae_profiles`; the rule that `profession` and `bio` are written by hand from facts, never copied; citing the note as a `press` source; and that a minister with no profile in the feed keeps an empty ficha rather than a guessed one.

- [ ] **Step 3: Run everything**

```bash
python3 -m unittest discover -s tools/tests -t . -q
npm test
npm run validate
npm run build
```

Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add docs/ARCHITECTURE.md workflows/minister_profiles.md
git commit -m "docs: document the minister-profile reader and its manual gate"
```

---

## Self-review

**Spec coverage.** Aliases → Task 1. Infobae in `SOURCES` → Task 2. The Arnillas fix → Task 3. Two-key matching, ranking, purity → Task 4. Review packet and blank `bio` → Task 5. Visitor-facing fifth outlet → Task 6. Docs → Task 7. The "never read `content:encoded`" constraint is enforced structurally: `press_feeds.parse_feed` never exposes it, and Task 4's `Purity` test asserts the exact field set.

**Known risk.** Task 4's coverage threshold (≥12 of 19) depends on what Infobae published on 2026-07-28. The fixture freezes that, so the test is stable — but if the matcher is later changed, a drop below 12 means a real regression, not a stale expectation.

**Type consistency.** `profile_items(articles, roster) -> dict` keyed by portfolio id is produced in Task 4 and consumed in Task 5. `roster` rows are `{portfolio, person_name}` in Task 4's tests and `{portfolio, person_name, has_ficha}` in Task 5 — the extra key is ignored by the matcher, which reads only the two it needs. `is_profile(title)` is used in both Task 4's ranking and its tests.
