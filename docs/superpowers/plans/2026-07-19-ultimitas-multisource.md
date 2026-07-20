# Multi-source Ultimitas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** La República joins El Comercio in the ultimitas pipeline, and the page shows one merged feed with a source chip per card and Todas/El Comercio/La República filters.

**Architecture:** The existing `elcomercio_scraper.py` generalizes into `ultimitas_scraper.py` driven by a `SOURCES` config (one tool, one run, one write — two scrapers would race on the `ultimitas-data` branch). Every article gains a `source` field; the client script defaults missing sources to "El Comercio" so UI and scraper can ship in either order. Filter chips are built from the sources present in the loaded day, not a hardcoded list.

**Tech Stack:** Python stdlib (scraper), Astro + vanilla TS (page), unittest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-07-19-ultimitas-multisource-design.md`

## Global Constraints

- **Copyright:** only title, link, description snippet, author and date are stored — never full article bodies. Applies to La República identically.
- **No new dependencies** — scraper stays stdlib-only; page stays vanilla TS.
- Third-party text renders via `textContent` only; article URLs pass the existing `safeHttpUrl()`.
- **Wordmark chips, never image logos.**
- User-facing copy in Spanish (Peru); code/comments/commits in English.
- Branch `feat/ultimitas-multisource` (already created). Conventional commits, rebase-and-merge. Merging will auto-release a minor bump.
- Fixture rule: the committed La República fixture is a **captured slice of the real feed** — never hand-written XML.
- Per-source failure isolation: one outlet failing entirely must not block the other; the run fails only when *every* source fails.

## File Structure

| File | Change |
|---|---|
| `tools/scrapers/ultimitas_scraper.py` | `git mv` from `elcomercio_scraper.py`; `SOURCES` config; `source` on every article; per-source isolation; file-level `"source"` key → `"sources"` list |
| `tools/tests/test_ultimitas_scraper.py` | `git mv` from `test_elcomercio_scraper.py`; updated signatures; La República fixture tests; isolation test |
| `tools/tests/fixtures/larepublica_rss_sample.xml` | New — captured slice of the real feed |
| `.github/workflows/ultimitas-scraper.yml` | Tool path update |
| `workflows/ultimitas_scraper.md` | `git mv` from `elcomercio_ultimitas.md`; multi-source rewrite |
| `docs/ARCHITECTURE.md` | Tool name, source list, mermaid P2 label |
| `src/components/Ultimitas/ultimitas.ts` | `source` in interface + default; card chip + `data-source`; dynamic filter chips |
| `src/components/Ultimitas/Ultimitas.astro` | Filters container + filter-empty message element |
| `src/components/Ultimitas/ultimitas.css` | `.ultimitas-filter` + `.ultimitas-source` styles |
| `src/pages/ultimitas.astro` | Copy names both outlets |
| `src/pages/fuentes.astro` | La República card added; Google News card example list adjusted |

---

### Task 1: Scraper carries a source on every article

**Files:**
- Rename: `tools/scrapers/elcomercio_scraper.py` → `tools/scrapers/ultimitas_scraper.py`
- Rename: `tools/tests/test_elcomercio_scraper.py` → `tools/tests/test_ultimitas_scraper.py`

**Interfaces:**
- Consumes: `watcher_common.http_get`, `normalize`, `parse_rss_items` (unchanged).
- Produces (later tasks rely on these exact names): module `ultimitas_scraper`; `SOURCES: list[dict]` with keys `name: str`, `feeds: list[str]`; `parse_feed(raw: bytes, source: str) -> list[dict]` where each dict has keys `title,url,summary,author,published,source`; `fetch_sources() -> tuple[list[dict], list[str]]` (items, names-of-fully-failed-sources); JSON payloads carry top-level `"sources": [str, ...]` instead of `"source": str`.

- [ ] **Step 1: Rename both files with git so history follows**

```bash
git mv tools/scrapers/elcomercio_scraper.py tools/scrapers/ultimitas_scraper.py
git mv tools/tests/test_elcomercio_scraper.py tools/tests/test_ultimitas_scraper.py
```

- [ ] **Step 2: Update the test file to the new module and signatures (failing first)**

In `tools/tests/test_ultimitas_scraper.py`:
- Docstring: `"""Unit tests for the ultimitas scraper's deterministic stages (no network)."""`
- Replace `import elcomercio_scraper as ec` with `import ultimitas_scraper as us` and every `ec.` with `us.`.
- Every `us.parse_feed(FIXTURE)` becomes `us.parse_feed(FIXTURE, "El Comercio")`.
- In `ParseFeedTest.test_maps_all_items_with_expected_fields`, the expected key set becomes:

```python
        self.assertEqual(set(items[0]), {"title", "url", "summary", "author", "published", "source"})
```

- Add to `ParseFeedTest`:

```python
    def test_stamps_the_given_source_on_every_item(self):
        items = us.parse_feed(FIXTURE, "El Comercio")
        self.assertTrue(all(i["source"] == "El Comercio" for i in items))
```

- In `MergeTest.test_existing_entry_wins_and_keeps_captured`, add `"source": "El Comercio"` to both the `existing` and `new` dicts (merge must not care about the field, but the records should look real).

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m unittest tools.tests.test_ultimitas_scraper -v 2>&1 | tail -5`
Expected: errors — `parse_feed() takes 1 positional argument` (module still has the old signature).

- [ ] **Step 4: Generalize the scraper**

In `tools/scrapers/ultimitas_scraper.py`, replace the header docstring, the `SOURCE`/`FEEDS` constants, `parse_feed`, and the fetch section of `run()` as follows. `canonical_url`, `item_matches`, `merge_history`, `lima_day`, `select_today`, `main()` stay byte-identical.

Docstring (replaces the current one):

```python
"""Scrape Peruvian press RSS for Keiko Fujimori / Fuerza Popular coverage.

Feeds the public "Las ultimitas" page from the outlets in SOURCES (El Comercio,
La República): matched headlines accumulate in ultimitas.json (full history) and
today.json (latest Lima news day — the only file the page downloads), each
article stamped with its source. One tool for all outlets: parallel scrapers
would race on the ultimitas-data branch. Git-free: it reads/writes --data-dir
and the Action owns the branch. Stdlib only.
See workflows/ultimitas_scraper.md.

Copyright: only title, link, description snippet, author and date are stored —
never full article bodies (they belong to each outlet).

Usage:
  python3 tools/scrapers/ultimitas_scraper.py --dry-run           # print matches, no writes
  python3 tools/scrapers/ultimitas_scraper.py --data-dir <dir>    # merge into <dir>/*.json
"""
```

Constants (replace `SOURCE = ...` and `FEEDS = [...]`):

```python
SOURCES = [
    {"name": "El Comercio", "feeds": [
        "https://elcomercio.pe/arc/outboundfeeds/rss/category/politica/?outputType=xml",
        "https://elcomercio.pe/arc/outboundfeeds/rss/?outputType=xml",
    ]},
    {"name": "La República", "feeds": [
        "https://larepublica.pe/rss/politica.xml",
    ]},
]
```

`parse_feed` (replaces the current one):

```python
def parse_feed(raw: bytes, source: str) -> list[dict]:
    return [{
        "title": rec["title"],
        "url": canonical_url(rec["link"]),
        "summary": rec["summary"],
        "author": rec["author"],
        "published": rec["published"].isoformat(),
        "source": source,
    } for rec in parse_rss_items(raw)]
```

New function after `parse_feed`:

```python
def fetch_sources() -> tuple[list[dict], list[str]]:
    """Items across all SOURCES, plus the names of sources that failed entirely.

    One outlet's outage must never silence the other: failures are per-feed,
    and a source only counts as failed when none of its feeds delivered.
    """
    items: list[dict] = []
    failed: list[str] = []
    for source in SOURCES:
        got_any = False
        for feed in source["feeds"]:
            try:
                items.extend(parse_feed(http_get(feed, headers={"User-Agent": BROWSER_UA}), source["name"]))
                got_any = True
            except Exception as err:  # noqa: BLE001 — any feed error is survivable
                print(f"WARN: feed failed: {feed}: {err}", file=sys.stderr)
        if not got_any:
            failed.append(source["name"])
            print(f"WARN: source failed entirely: {source['name']}", file=sys.stderr)
    return items, failed
```

In `run()`, replace everything from `items: list[dict] = []` through the `if failed == len(FEEDS):` block with:

```python
    items, failed = fetch_sources()
    if len(failed) == len(SOURCES):
        print("ERROR: every source failed", file=sys.stderr)
        return 1
```

Replace the dry-run print block with a per-source count:

```python
    if dry_run:
        for item in matched:
            print(f"[{item['published']}] [{item['source']}] {item['title'][:80]}")
        by_source = {s["name"]: sum(1 for i in matched if i["source"] == s["name"]) for s in SOURCES}
        print(f"Per source: {by_source}. Dry run complete.")
        return 0
```

And in both `write_text` payloads, replace `"source": SOURCE` with:

```python
        {"generated": now_iso, "sources": [s["name"] for s in SOURCES], "articles": articles},
```

(and the same `"sources"` key in the `today.json` payload, keeping its `"date"` field).

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m unittest tools.tests.test_ultimitas_scraper -v 2>&1 | tail -3`
Expected: `OK` (all tests pass; count is previous suite + 1 new).

- [ ] **Step 6: Full offline suite still green**

Run: `python3 -m unittest discover -s tools/tests -p "test_*.py" 2>&1 | tail -3`
Expected: `OK`. If `test_watcher_common.py` or others import nothing renamed, nothing else changes.

- [ ] **Step 7: Commit**

```bash
git add -A tools/
git commit -m "feat: ultimitas scraper carries a source on every article

elcomercio_scraper generalizes into ultimitas_scraper driven by a
SOURCES config; one tool for all outlets so nothing races on the
ultimitas-data branch. File-level source key becomes a sources list.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: La República as a live source, with a real captured fixture

**Files:**
- Create: `tools/tests/fixtures/larepublica_rss_sample.xml`
- Modify: `tools/tests/test_ultimitas_scraper.py` (append two test classes)

**Interfaces:**
- Consumes: `ultimitas_scraper.parse_feed(raw, source)`, `fetch_sources()`, `SOURCES` from Task 1.
- Produces: nothing new — proves the second source against real data.

- [ ] **Step 1: Capture a real feed slice as the fixture**

```bash
curl -s --max-time 20 -A "Mozilla/5.0 (compatible; keikogobierna-ultimitas; +https://github.com/DianCotrina/keikogobierna)" \
  "https://larepublica.pe/rss/politica.xml" -o /tmp/lr_full.xml
python3 - <<'EOF'
import xml.etree.ElementTree as ET
ET.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')
ET.register_namespace('atom', 'http://www.w3.org/2005/Atom')
ET.register_namespace('media', 'http://search.yahoo.com/mrss/')
tree = ET.parse('/tmp/lr_full.xml')
channel = tree.getroot().find('channel')
for item in channel.findall('item')[4:]:
    channel.remove(item)
tree.write('tools/tests/fixtures/larepublica_rss_sample.xml', encoding='utf-8', xml_declaration=True)
EOF
wc -c tools/tests/fixtures/larepublica_rss_sample.xml
```

Expected: a file of a few KB (4 items). If the curl fails, stop and report — do not hand-write the fixture.

- [ ] **Step 2: Append the failing tests**

At the end of `tools/tests/test_ultimitas_scraper.py` (before the `__main__` block):

```python
LR_FIXTURE = (Path(__file__).resolve().parent / "fixtures" / "larepublica_rss_sample.xml").read_bytes()


class LaRepublicaFeedTest(unittest.TestCase):
    """Structural assertions against a captured slice of the real feed —
    exact strings vary with the news cycle, the shape must not."""

    def test_real_feed_slice_parses_with_all_fields(self):
        items = us.parse_feed(LR_FIXTURE, "La República")
        self.assertGreater(len(items), 0)
        for item in items:
            self.assertEqual(set(item), {"title", "url", "summary", "author", "published", "source"})
            self.assertTrue(item["title"])
            self.assertTrue(item["url"].startswith("https://larepublica.pe/"))
            datetime.fromisoformat(item["published"])  # raises if unparseable
            self.assertEqual(item["source"], "La República")

    def test_larepublica_is_configured(self):
        names = [s["name"] for s in us.SOURCES]
        self.assertIn("La República", names)
        self.assertIn("El Comercio", names)


class SourceIsolationTest(unittest.TestCase):
    def test_one_dead_source_does_not_kill_the_other(self):
        real_http_get = us.http_get

        def stub(url, headers=None):
            if "larepublica" in url:
                raise OSError("simulated outage")
            return FIXTURE

        us.http_get = stub
        try:
            items, failed = us.fetch_sources()
        finally:
            us.http_get = real_http_get
        self.assertEqual(failed, ["La República"])
        self.assertTrue(items)  # El Comercio still delivered
        self.assertTrue(all(i["source"] == "El Comercio" for i in items))
```

Add `from datetime import datetime` to the test file's imports.

- [ ] **Step 3: Run to verify the new tests run and pass**

Run: `python3 -m unittest tools.tests.test_ultimitas_scraper -v 2>&1 | tail -5`
Expected: `OK`. (These pass immediately if Task 1 is correct — they are guarding the *fixture's* reality, and `SourceIsolationTest` exercises `fetch_sources` for the first time. If `LaRepublicaFeedTest` fails, the real feed's shape differs from assumptions — fix `parse_rss_items` handling or the mapping, not the test.)

- [ ] **Step 4: Live dry-run against both real feeds**

Run: `python3 tools/scrapers/ultimitas_scraper.py --dry-run`
Expected: fetch counts for both outlets and a final line like `Per source: {'El Comercio': N, 'La República': M}. Dry run complete.` — N, M ≥ 0 depending on the news day; the run must not error.

- [ ] **Step 5: Commit**

```bash
git add tools/tests/fixtures/larepublica_rss_sample.xml tools/tests/test_ultimitas_scraper.py
git commit -m "feat: La República joins the ultimitas scraper

Captured-slice fixture from the real feed, structural parse tests, and
an isolation test proving one dead outlet never silences the other.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Workflow, SOP and ARCHITECTURE follow the rename

**Files:**
- Modify: `.github/workflows/ultimitas-scraper.yml`
- Rename: `workflows/elcomercio_ultimitas.md` → `workflows/ultimitas_scraper.md`
- Modify: `docs/ARCHITECTURE.md`

**Interfaces:**
- Consumes: the module name `ultimitas_scraper.py` from Task 1.
- Produces: nothing other tasks rely on.

- [ ] **Step 1: Point the Action at the renamed tool**

In `.github/workflows/ultimitas-scraper.yml`, change the run line:

```yaml
            bash -c 'python3 tools/scrapers/ultimitas_scraper.py --data-dir "$DATA_DIR"'
```

(only `elcomercio_scraper.py` → `ultimitas_scraper.py` changes).

- [ ] **Step 2: Rename and update the SOP**

```bash
git mv workflows/elcomercio_ultimitas.md workflows/ultimitas_scraper.md
```

Then apply these content updates (the rest of the SOP stays):
- Title: `# Workflow: "Las ultimitas" multi-source press scraper`
- Objective first sentence: `Keep the public /ultimitas page fed with press coverage of Keiko Fujimori / Fuerza Popular from the outlets in SOURCES (El Comercio, La República).`
- "How it works" step 2 opening: `tools/scrapers/ultimitas_scraper.py fetches every feed of every source in SOURCES (El Comercio: Arc XP política + general; La República: rss/politica.xml), keeps items whose title+description match KEYWORDS ...` and add to the bullet list: `Every article is stamped with its source; the page's filter chips are built from the sources present in the data.`
- "Tuning" first bullet: `SOURCES / KEYWORDS in tools/scrapers/ultimitas_scraper.py. Adding an outlet = one SOURCES entry + a fuentes card + (optionally) a fixture test.`
- "Local testing" commands: replace both `elcomercio_scraper.py` occurrences with `ultimitas_scraper.py`.
- "Known constraints" add: `- Per-source isolation: a source only fails when all its feeds fail, and the run only fails when all sources fail. A failed source is a WARN in the Action log — check it when one outlet's news goes quiet.` and `- La República's feed is classic RSS at larepublica.pe/rss/politica.xml (the Arc outbound paths El Comercio uses return 301 there).`

- [ ] **Step 3: Update ARCHITECTURE**

In `docs/ARCHITECTURE.md`:
- Discovery-pipeline table row: `| `ultimitas_scraper.py` | El Comercio Arc XP RSS + La República RSS | 4×/day (Lima 00/06/12/18) | `ultimitas-data` branch |` (replaces the `elcomercio_scraper.py` row).
- Mermaid P2 subgraph: replace the El Comercio node/edge with:

```
        EC["El Comercio + La República<br/>RSS"] -->|"ultimitas_scraper.py<br/>4×/day"| UD["ultimitas-data branch<br/>today.json"]
```

- Grep for leftovers: `grep -rn "elcomercio_scraper\|elcomercio_ultimitas" docs/ workflows/ .github/ tools/ src/` — expected: no hits (the SOP's own decision-log line referencing the old name, if kept, is fine; everything operational must point at the new name).

- [ ] **Step 4: Validate and commit**

```bash
python3 -c "import yaml; w=yaml.safe_load(open('.github/workflows/ultimitas-scraper.yml')); print([s for j in w['jobs'].values() for s in j['steps']][-1]['run'])" | grep ultimitas_scraper.py
git add -A .github/workflows/ultimitas-scraper.yml workflows/ docs/ARCHITECTURE.md
git commit -m "chore: point workflow and docs at ultimitas_scraper

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Source chips and filters on the page

**Files:**
- Modify: `src/components/Ultimitas/ultimitas.ts`
- Modify: `src/components/Ultimitas/Ultimitas.astro`
- Modify: `src/components/Ultimitas/ultimitas.css`
- Modify: `src/pages/ultimitas.astro`

**Interfaces:**
- Consumes: `today.json` articles that MAY carry `source: string` (Task 1's contract) — and MAY NOT (records written before the field existed).
- Produces: `DEFAULT_SOURCE = 'El Comercio'` backward-compat rule; filter chips built from data.

- [ ] **Step 1: Replace `src/components/Ultimitas/ultimitas.ts` with**

```ts
import { formatDateEs } from '../../lib/format.mjs';

const DATA_URL = 'https://raw.githubusercontent.com/DianCotrina/keikogobierna/ultimitas-data/today.json';
// Records written before the source field existed are all El Comercio.
const DEFAULT_SOURCE = 'El Comercio';

interface Article {
  title: string;
  url: string;
  summary: string;
  author: string;
  published: string;
  source?: string;
}

const LIMA = 'America/Lima';
const timeFmt = new Intl.DateTimeFormat('es-PE', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: LIMA });

function limaToday(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: LIMA }).format(new Date());
}

// Third-party URLs: only http(s) may reach an href — the feed is external data,
// and canonical_url() upstream preserves schemes like javascript:/data: as-is.
function safeHttpUrl(raw: string): string {
  try {
    const url = new URL(raw);
    if (url.protocol === 'https:' || url.protocol === 'http:') return url.href;
  } catch {
    // unparseable — fall through to ''
  }
  return '';
}

// Third-party text: build every node with textContent — never innerHTML.
function card(article: Article): HTMLElement {
  const source = article.source ?? DEFAULT_SOURCE;
  const el = document.createElement('article');
  el.className = 'ultimitas-card bg-white rounded-lg border border-tinta/10 shadow-card p-6 sm:p-7';
  el.dataset.source = source;

  const head = document.createElement('div');
  head.className = 'flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5';
  const meta = document.createElement('p');
  meta.className = 'font-mono text-[0.65rem] uppercase tracking-[0.14em] text-tintafina';
  meta.textContent = `${timeFmt.format(new Date(article.published))}${article.author ? ` · ${article.author}` : ''}`;
  const chip = document.createElement('span');
  chip.className = 'ultimitas-source';
  chip.textContent = source;
  head.append(meta, chip);
  el.append(head);

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

  const safeUrl = safeHttpUrl(article.url);
  if (safeUrl) {
    const linkWrap = document.createElement('p');
    linkWrap.className = 'mt-3';
    const link = document.createElement('a');
    link.href = safeUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.className = 'nav-link font-sans text-sm font-medium';
    link.textContent = `Leer en ${source} →`;
    linkWrap.append(link);
    el.append(linkWrap);
  }

  return el;
}

function applyFilter(list: HTMLElement, emptyEl: HTMLElement, filter: string): void {
  let visible = 0;
  for (const el of list.querySelectorAll<HTMLElement>('.ultimitas-card')) {
    const show = filter === 'all' || el.dataset.source === filter;
    el.hidden = !show;
    if (show) visible += 1;
  }
  emptyEl.textContent = `Sin titulares de ${filter} este día.`;
  emptyEl.classList.toggle('hidden', filter === 'all' || visible > 0);
}

function renderFilters(bar: HTMLElement, list: HTMLElement, emptyEl: HTMLElement, sources: string[]): void {
  // Chips come from the data, not a hardcoded outlet list; skip on single-source days.
  if (sources.length < 2) return;
  const options = ['all', ...sources];
  for (const option of options) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'ultimitas-filter';
    btn.textContent = option === 'all' ? 'Todas' : option;
    btn.setAttribute('aria-pressed', String(option === 'all'));
    btn.addEventListener('click', () => {
      for (const other of bar.querySelectorAll('button')) other.setAttribute('aria-pressed', 'false');
      btn.setAttribute('aria-pressed', 'true');
      applyFilter(list, emptyEl, option);
    });
    bar.append(btn);
  }
  bar.hidden = false;
}

async function load(): Promise<void> {
  const list = document.getElementById('ultimitas-list');
  const dateEl = document.getElementById('ultimitas-date');
  const errorEl = document.getElementById('ultimitas-error');
  const filtersEl = document.getElementById('ultimitas-filters');
  const filterEmptyEl = document.getElementById('ultimitas-filter-empty');
  if (!list || !dateEl || !errorEl || !filtersEl || !filterEmptyEl) return;

  try {
    const resp = await fetch(DATA_URL, { cache: 'no-cache' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data: { date: string; articles: Article[] } = await resp.json();
    if (!data.date || !Array.isArray(data.articles) || data.articles.length === 0) {
      throw new Error('empty payload');
    }
    const suffix = data.date === limaToday() ? '' : ' · último día con noticias';
    dateEl.textContent = `Ultimitas del ${formatDateEs(data.date)}${suffix}`;
    list.replaceChildren(...data.articles.map(card));
    const sources = [...new Set(data.articles.map((a) => a.source ?? DEFAULT_SOURCE))];
    renderFilters(filtersEl, list, filterEmptyEl, sources);
  } catch (err) {
    console.error('ultimitas:', err);
    dateEl.textContent = 'Ultimitas';
    list.classList.add('hidden');
    errorEl.classList.remove('hidden');
  }
}

load();
```

- [ ] **Step 2: Add the filters bar and empty message to `Ultimitas.astro`**

Between the `#ultimitas-date` paragraph and the `#ultimitas-list` div, insert:

```html
  <div id="ultimitas-filters" class="mt-5 flex flex-wrap gap-2" role="group" aria-label="Filtrar por medio" hidden></div>
  <p id="ultimitas-filter-empty" class="hidden mt-6 font-mono text-sm text-tintasuave" aria-live="polite"></p>
```

- [ ] **Step 3: Add chip styles to `ultimitas.css`**

Append:

```css
/* Source wordmark on each card + filter chips. Wordmarks by design — never logos. */
.ultimitas-source {
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--color-tintasuave);
  border: 1.5px solid color-mix(in srgb, var(--color-tinta) 25%, transparent);
  border-radius: 0.25rem;
  padding: 0.15rem 0.5rem;
  white-space: nowrap;
}

.ultimitas-filter {
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--color-tintasuave);
  border: 1.5px solid color-mix(in srgb, var(--color-tinta) 25%, transparent);
  border-radius: 0.25rem;
  padding: 0.35rem 0.75rem;
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease, background-color 0.15s ease;
}
.ultimitas-filter:hover { color: var(--color-tinta); border-color: color-mix(in srgb, var(--color-tinta) 50%, transparent); }
.ultimitas-filter:focus-visible { outline: 2px solid color-mix(in srgb, var(--color-verde) 60%, transparent); outline-offset: 2px; }
.ultimitas-filter[aria-pressed="true"] { background: var(--color-tinta); border-color: var(--color-tinta); color: var(--color-papel); }
```

- [ ] **Step 4: Page copy names both outlets — `src/pages/ultimitas.astro`**

- `description`: `'Lo último que publican El Comercio y La República sobre Keiko Fujimori y Fuerza Popular, actualizado varias veces al día, con enlace directo a cada nota.'`
- Eyebrow: `Hemeroteca · Prensa peruana`
- Body paragraph: `Lo que la prensa dice hoy sobre Keiko Fujimori y Fuerza Popular: titulares de El Comercio y La República con enlace directo a cada nota.`
- In `Ultimitas.astro`, if the error block's fallback link says only El Comercio, add a La República link beside it in the same style (`https://larepublica.pe/politica/`).

- [ ] **Step 5: Build + visual verification with real mixed data**

```bash
npm run build 2>&1 | tail -2   # expect 28 pages
python3 tools/scrapers/ultimitas_scraper.py --data-dir /tmp/ult-preview
cp /tmp/ult-preview/today.json public/_preview-today.json
```

Temporarily (never committed) point `DATA_URL` in `ultimitas.ts` at `'/_preview-today.json'`, then screenshot `http://localhost:3000/ultimitas/` at 1280px and 390px (Brave headless; the standard iframe harness for mobile width). Verify: chips row shows Todas + both outlets (when the day has both), each card carries its wordmark chip, clicking a chip filters and `aria-pressed` moves, an outlet with no articles that day shows `Sin titulares de … este día.`

Then **revert the DATA_URL edit and delete the preview file**:

```bash
rm -f public/_preview-today.json
git diff --stat   # DATA_URL change must NOT appear; only the intended files
```

- [ ] **Step 6: Commit**

```bash
git add src/components/Ultimitas/ src/pages/ultimitas.astro
git commit -m "feat: source chips and filters on the ultimitas page

Cards carry their outlet as a wordmark chip; filter chips (Todas + each
source present in the day) appear on multi-source days. Records without
a source default to El Comercio, so old data renders correctly.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Fuentes card + ship

**Files:**
- Modify: `src/pages/fuentes.astro`

**Interfaces:**
- Consumes: the `sections` array structure already in the file (heading/blurb/sources).

- [ ] **Step 1: Add the La República card and adjust the Google News card**

In the `Fuentes automáticas` section's `sources`, after the El Comercio entry, insert:

```js
      {
        name: 'La República — sección Política',
        org: 'Prensa',
        verifies: 'Cobertura política de La República sobre Keiko Fujimori y Fuerza Popular; sus titulares se suman a «Las ultimitas» junto a los de El Comercio.',
        links: [{ label: 'larepublica.pe/politica', url: 'https://larepublica.pe/politica/' }],
      },
```

And in the Google News entry, `verifies` becomes (La República graduates to a named source):

```js
        verifies: 'Vigila la cobertura del resto de la prensa peruana — RPP, Gestión y demás medios — en busca de avances sobre compromisos concretos.',
```

- [ ] **Step 2: Build, full checks, screenshot fuentes**

```bash
npm run build 2>&1 | tail -2 && npm test 2>&1 | grep -E "^ℹ (pass|fail)"
npm run validate && python3 tools/scrapers/build_commitment_index.py --check
python3 -m unittest discover -s tools/tests -p "test_*.py" 2>&1 | tail -3
```

Expected: 28 pages, 21/21 node, validator OK, index in sync, python suite OK. Screenshot `/fuentes/` — the automáticas section shows El Peruano, El Comercio, La República, Google News in that order.

- [ ] **Step 3: Commit, push, PR**

```bash
git add src/pages/fuentes.astro
git commit -m "feat: La República card in fuentes automáticas

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git pull --rebase origin main
git push -u origin feat/ultimitas-multisource
gh pr create --base main --head feat/ultimitas-multisource \
  --title "feat: multi-source ultimitas — La República joins El Comercio" \
  --body "Implements docs/superpowers/specs/2026-07-19-ultimitas-multisource-design.md: one generalized ultimitas_scraper (SOURCES config, per-source failure isolation, source on every article, sources list at file level), captured-slice La República fixture with structural tests, wordmark source chips + data-driven filter chips with El Comercio backward-compat default, and the fuentes card. Copyright rule unchanged for the new outlet."
```

- [ ] **Step 4: Post-merge E2E (after Diego merges)**

```bash
gh workflow run ultimitas-scraper.yml && sleep 90
curl -s https://raw.githubusercontent.com/DianCotrina/keikogobierna/ultimitas-data/today.json | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('sources'), sorted({a.get('source','—') for a in d['articles']}))"
```

Expected: `['El Comercio', 'La República']` and the per-article source set (both outlets when the day has both). Then screenshot the live `/ultimitas/` page: chips render, filtering works. The auto-release will have cut a minor version; confirm the live footer moved.

---

## Plan self-review

**Spec coverage:** one-scraper architecture (T1) · La República feed + real fixture (T2) · per-source isolation (T1 code, T2 test) · `source` field + backward-compat default (T1/T4) · merged feed, wordmark chips, data-driven filters, empty-filter state (T4) · page copy (T4) · fuentes same-PR rule (T5) · workflow/SOP/ARCHITECTURE (T3) · copyright + textContent + safeHttpUrl constraints (Global + T4 code) · post-merge E2E (T5). The spec's file-level `"source"` key ambiguity is resolved as `"sources"` (list) — an addition beyond the spec's letter, noted here deliberately.

**Placeholders:** none; every step carries the code or the exact command. The LR fixture's exact contents are unknowable pre-capture by design — tests assert structure, and Step 1 of Task 2 refuses a hand-written fallback.

**Type consistency:** `parse_feed(raw: bytes, source: str)` used identically in T1/T2; `fetch_sources()` returns `(items, failed)` in T1 and is stubbed with that shape in T2; `DEFAULT_SOURCE`/`data-source`/`.ultimitas-card` names match across T4's ts/astro/css; element ids `ultimitas-filters`/`ultimitas-filter-empty` match between astro and ts.
