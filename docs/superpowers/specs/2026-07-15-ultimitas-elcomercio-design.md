# "Las ultimitas" — El Comercio scraper + today's-news page

**Date:** 2026-07-15
**Status:** Design approved in conversation (Diego, 2026-07-15); spec review pending

## Problem

The two existing scrapers feed an internal review queue (GitHub issues). Nothing on the site itself shows visitors what the press is saying about Keiko Fujimori / Fuerza Popular *today*. "Las ultimitas" is a new public page that does exactly that, sourced from El Comercio — and doubles as the reference exercise for understanding the scraping architecture end to end.

Hard rule carried over from the rest of the system: **the scraper never touches `main` or `tracking.json`** — it only writes news data to its own branch.

## Reconnaissance (2026-07-15, verified live)

- El Comercio runs on Arc XP and exposes official, unauthenticated RSS feeds (`application/xml`, no paywall):
  - General: `https://elcomercio.pe/arc/outboundfeeds/rss/?outputType=xml` — 100 items, ~1.5 MB.
  - Política: `https://elcomercio.pe/arc/outboundfeeds/rss/category/politica/?outputType=xml` — 28 items, ~200 KB.
- Item fields: `title`, `link`, `guid`, `pubDate` (RFC 2822), `description` (one-line snippet), `dc:creator`, `content:encoded` (**full article HTML — copyrighted, never stored or republished**), media image.
- Sample day: 21 of 28 política items mentioned Keiko/Fuerza Popular somewhere in the item.
- Tag feeds (`/arc/outboundfeeds/rss/tags/keiko-fujimori/`) respond 200 but empty — useless; section feed + our own filter is the way.
- Unofficial-interface caveat as always: if Arc XP feed paths or fields change, the run fails loudly and we fix the tool (WAT loop).

## Design

### Component 1 — scraper: `tools/elcomercio_scraper.py`

Stdlib-only, same conventions as the other tools (`--dry-run`, loud failures, argparse). Three stages:

1. **Fetch** — download the feeds in a tunable `FEEDS` list (política + general), parse with `xml.etree`, map each item to `{title, url, summary, author, published, captured}`:
   - `summary` = the `description` snippet only. `content:encoded` is read never — not even into memory structures we persist.
   - `published` = pubDate parsed via `email.utils` → ISO 8601; `captured` = run timestamp.
   - `url` canonicalized: scheme+host+path, query/tracking params stripped (El Comercio appends `?ref=…`). Canonical URL is the dedup key.
2. **Filter** — keep items whose normalized **title + description** contain any keyword in a tunable `KEYWORDS` constant: `keiko fujimori`, `keiko`, `fuerza popular`, `fujimorismo`. Accent/case-insensitive via `normalize()`, which **moves from `elperuano_reader.py` into `watcher_common.py`** so both tools share it (reader keeps importing it; existing tests unchanged).
3. **Merge + emit** — the tool reads/writes plain files in `--data-dir` (git-free; the workflow owns branching):
   - `ultimitas.json` — full accumulated history: merge new matches into existing by canonical URL, sort newest-first. Grows forever; **never downloaded by the page**, so its size costs visitors nothing.
   - `today.json` — what the page fetches: `{generated, date, articles}` where `date` is the **most recent Lima-time day (`America/Lima`, via `zoneinfo`) that has matches** and `articles` are only that day's items. Today when there is news today; otherwise the latest news day (page labels the date, so it is never misleading and never empty). Payload stays small and constant regardless of history size.

### Component 2 — pipeline: `.github/workflows/ultimitas-scraper.yml`

- Cron `0 5,11,17,23 * * *` (Lima 00:00/06:00/12:00/18:00 — a news page stale all day defeats "today's news") + `workflow_dispatch`. `permissions: contents: write`. Cost: $0 (public repo).
- Checks out the **`ultimitas-data` branch** into a `git worktree` (orphan-created on first run — the exact `normas-archive` pattern; rulesets only protect `main`), runs the scraper with `--data-dir` pointing at it, commits/pushes as `github-actions[bot]` only when files changed.

### Component 3 — page: `/ultimitas`

- `src/pages/ultimitas.astro` + `src/components/Ultimitas/` folder module (own CSS + TS, per the component convention). Nav gains an "Ultimitas" entry. All copy Spanish, existing design tokens, `frontend-design` skill invoked before any of it.
- On load, client JS fetches `https://raw.githubusercontent.com/DianCotrina/keikogobierna/ultimitas-data/today.json` (CORS `*`, ~5-min edge cache). States:
  - **Loading** — skeleton cards.
  - **Loaded** — dated header ("Ultimitas del 15 de julio de 2026"); one card per article: date/time, title, snippet, author when present, "Leer en El Comercio →" (opens elcomercio.pe).
  - **Error** (fetch fails / branch missing) — friendly fallback with a direct link to El Comercio política. The static site itself can never break from scraper failures.
- Visible attribution line: headlines and snippets are El Comercio's; this page only links to the source.

### Component 4 — tests + docs

- `tools/test_elcomercio_scraper.py` + committed fixture `tools/fixtures/elcomercio_rss_sample.xml` (**trimmed: `content:encoded` bodies stripped** — we don't commit their copyrighted text). Covers: item mapping, keyword filter incl. accents/case, URL canonicalization, merge/dedup by canonical URL, today-selection incl. the fallback-to-latest-day rule, Lima-day bucketing.
- CI already runs `python3 -m unittest discover -s tools -p "test_*.py"` — the new tests gate PRs with no CI change.
- WAT SOP: `workflows/elcomercio_ultimitas.md` (tuning `KEYWORDS`/`FEEDS`, failure modes, how the branch/page relate).

## Failure modes / maintenance

- Feed down or Arc XP structure changed → run fails red in Actions; page keeps serving the last committed `today.json`.
- One feed fails, the other works → warn and continue (same policy as the news watcher).
- Browser fetch fails → error state with outbound link; nothing else on the site affected.
- Keyword false positives (e.g. Alberto/Kenji Fujimori pieces) → acceptable at launch; tune `KEYWORDS`.

## Out of scope

- Other outlets (the `FEEDS`/data-model shape allows adding them later; not now).
- Any connection to `tracking.json` / the evidence queue — this is a news page, not evidence discovery.
- Storing or displaying article bodies or images (copyright; hotlinking their CDN also declined).
- Site deploy concerns — the page works identically in dev and any future hosting.

## Decisions log (conversation, 2026-07-15)

- Entry content: headline + El Comercio's snippet + date + author + attribution link (not headline-only, not image cards).
- Delivery: data branch + browser fetch (not daily bot PRs to main, not build-time fetch).
- Retention: full history accumulates on the branch; **page fetches only the current news day** (Diego: showing a long window "will consume too much resources to our page").
- Empty day: fall back to the most recent day with matches, clearly dated.
