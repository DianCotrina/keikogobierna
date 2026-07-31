# Workflow: "Las ultimitas" multi-source press scraper

## Objective

Keep the public `/ultimitas` page fed with press coverage of Keiko Fujimori /
Fuerza Popular from the outlets in SOURCES (El Comercio, La República, RPP, Gestión e Infobae). Unlike the evidence watcher and the El Peruano scraper (which file
review issues), this pipeline publishes directly to a data branch — it is a news
listing, not evidence; it never touches `tracking.json` or `main`.

## How it works

1. `.github/workflows/ultimitas-scraper.yml` runs 4×/day (Lima 00:00/06:00/12:00/18:00)
   or on manual dispatch.
2. `tools/scrapers/ultimitas_scraper.py` fetches every feed of every source in `SOURCES`
   (El Comercio: Arc XP política + general; La República: rss/politica.xml; RPP: /feed;
   Gestión: Arc XP general), keeps items
   whose title+description match `KEYWORDS` (accent/case-insensitive), stamps each article
   with its source, and merges them into the `ultimitas-data` branch via a git worktree:
   - `ultimitas.json` — full accumulated history, deduped by canonical URL (tracking
     params stripped). Never downloaded by the page.
   - `today.json` — the latest Lima-calendar day with matches. This is the only file
     the page fetches (from raw.githubusercontent.com, CORS-open, ~5-min edge cache).
   - Every article carries its `source`; the page's filter chips are built from the
     sources present in the data, not a hardcoded outlet list.
3. `src/components/Ultimitas/ultimitas.ts` renders it client-side: dated header
   (labeled "último día con noticias" when it isn't today), one card per article,
   error fallback linking to El Comercio. Third-party text is rendered with
   `textContent` only.

## Tuning

- `SOURCES` in `tools/scrapers/common/press_feeds.py` — shared, so an outlet added there
  also reaches the cabinet sweep's `--press` pass. `KEYWORDS` stays in
  `tools/scrapers/ultimitas_scraper.py`: it is what this page keeps, not what gets fetched.
  Adding an outlet = one `SOURCES` entry + a fuentes card (+ optionally a captured-fixture test).
  Alberto/Kenji Fujimori false positives are accepted at launch; tighten keywords if
  they annoy.
- Copyright rule: only title, link, description snippet, author, date. Never store
  or render `content:encoded` (full article body) or hotlink their images.

## Local testing

```bash
python3 -m tools.scrapers.ultimitas_scraper --dry-run              # live feeds, print matches
python3 -m tools.scrapers.ultimitas_scraper --data-dir /tmp/ult    # write both JSON files
python3 -m unittest discover -s tools/tests -t . -p "test_*.py"       # offline unit tests
```

## Known constraints / lessons

- Per-source isolation: a source only fails when all its feeds fail, and the run only
  fails when all sources fail. A failed source is a WARN in the Action log — check it
  when one outlet's news goes quiet.
- La República's feed is classic RSS at larepublica.pe/rss/politica.xml (the Arc
  outbound paths El Comercio uses return 301 there).
- El Comercio's feeds are Arc XP's standard outbound RSS (`/arc/outboundfeeds/rss/...`) —
  official but undocumented; if paths or fields change, the run fails loudly in
  Actions. Tag feeds (`/tags/keiko-fujimori/`) exist but return empty (2026-07-15).
- The general feed is ~1.5 MB; both feeds parse in memory fine.
- Live feed `pubDate` values arrive in UTC (+0000) even though the site is Lima-based —
  day bucketing always converts to `America/Lima` before grouping.
- The branch push goes through `tools/ci/publish_data_branch.sh` (shared with the
  El Peruano archive): a `git worktree` on the orphan `ultimitas-data` branch that
  never touches `main` (protected by the `protect-main` ruleset) and only commits
  when the data actually changed — the scraper itself also exits early on a
  no-news run, so quiet runs produce no commits at all.
- A scraper failure can never break the site: the page serves the last committed
  `today.json`, and its error state links to El Comercio.
