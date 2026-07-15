# Workflow: El Comercio "Las ultimitas"

## Objective

Keep the public `/ultimitas` page fed with El Comercio's coverage of Keiko Fujimori /
Fuerza Popular. Unlike the evidence watcher and the El Peruano reader (which file
review issues), this pipeline publishes directly to a data branch — it is a news
listing, not evidence; it never touches `tracking.json` or `main`.

## How it works

1. `.github/workflows/ultimitas-scraper.yml` runs 4×/day (Lima 00:00/06:00/12:00/18:00)
   or on manual dispatch.
2. `tools/scrapers/elcomercio_scraper.py` fetches the Arc XP RSS feeds in `FEEDS` (política +
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

- `KEYWORDS` / `FEEDS` in `tools/scrapers/elcomercio_scraper.py`. Alberto/Kenji Fujimori
  false positives are accepted at launch; tighten keywords if they annoy.
- Copyright rule: only title, link, description snippet, author, date. Never store
  or render `content:encoded` (full article body) or hotlink their images.

## Local testing

```bash
python3 tools/scrapers/elcomercio_scraper.py --dry-run              # live feeds, print matches
python3 tools/scrapers/elcomercio_scraper.py --data-dir /tmp/ult    # write both JSON files
python3 -m unittest discover -s tools/tests -p "test_*.py"       # offline unit tests
```

## Known constraints / lessons

- The feeds are Arc XP's standard outbound RSS (`/arc/outboundfeeds/rss/...`) —
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
