#!/usr/bin/env python3
"""Scrape Peruvian press RSS for Keiko Fujimori / Fuerza Popular coverage.

Feeds the public "Las ultimitas" page from the outlets in OUTLETS (El Comercio,
La República): matched headlines accumulate in ultimitas.json (full history) and
today.json (latest Lima news day — the only file the page downloads), each
article stamped with its source. One tool for all outlets: parallel scrapers
would race on the ultimitas-data branch. Git-free: it reads/writes --data-dir
and the Action owns the branch. Stdlib only.
See workflows/ultimitas_scraper.md.

Copyright: only title, link, description snippet, author and date are stored —
never full article bodies (they belong to each outlet).

Usage:
  python3 -m tools.scrapers.ultimitas_scraper --dry-run           # print matches, no writes
  python3 -m tools.scrapers.ultimitas_scraper --data-dir <dir>    # merge into <dir>/*.json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from tools.scrapers.common.minister_news import WINDOW_DAYS, build_index
from tools.scrapers.common.press_feeds import SOURCES, canonical_url, fetch_sources, parse_feed
from tools.scrapers.common.watcher_common import normalize
from tools.scrapers.infobae_profiles import roster

# Which of the shared feeds' items belong on /ultimitas/.
KEYWORDS = ["keiko fujimori", "keiko", "fuerza popular", "fujimorismo"]

# And which outlets. SOURCES is shared with the cabinet sweep and the profile
# reader, which want every outlet they can get; this page does not, so the
# narrowing belongs here rather than in the feed list.
#
# These two carry a *política* feed that is Peruvian politics. The others do not
# and cannot be made to: Gestión's category/politica is empty, Infobae's is
# Argentine politics (its Peru desk is category/peru), and RPP has none -- so
# they arrive as general feeds and reach this page only through KEYWORDS.
# Dropping them here costs the cabinet tools nothing.
OUTLETS = ["El Comercio", "La República"]

LIMA = ZoneInfo("America/Lima")


def from_published_outlet(item: dict) -> bool:
    return item.get("source") in OUTLETS


def item_matches(item: dict) -> bool:
    haystack = normalize(f"{item['title']} {item['summary']}")
    return any(keyword in haystack for keyword in KEYWORDS)


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
    days = [(lima_day(a["published"]), a) for a in articles]
    latest = max(day for day, _ in days)
    return latest, [a for day, a in days if day == latest]


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


# ---- Orchestration ---------------------------------------------------------------

def run(data_dir: str | None, dry_run: bool) -> int:
    items, failed = fetch_sources()
    # Only this page's outlets can fail this run. A dead Gestión is the cabinet
    # sweep's problem, not the page's; both of these dead means no page.
    if all(name in failed for name in OUTLETS):
        print(f"ERROR: every published outlet failed ({', '.join(OUTLETS)})", file=sys.stderr)
        return 1

    unique: dict[str, dict] = {}
    for item in items:
        unique.setdefault(item["url"], item)
    published = [i for i in unique.values() if from_published_outlet(i)]
    matched = [i for i in published if item_matches(i)]
    print(f"{len(items)} items fetched ({len(unique)} unique), "
          f"{len(published)} from {'/'.join(OUTLETS)}, {len(matched)} matched")

    if dry_run:
        for item in matched:
            print(f"[{item['published']}] [{item['source']}] {item['title'][:80]}")
        by_source = {name: sum(1 for i in matched if i["source"] == name) for name in OUTLETS}
        print(f"Per source: {by_source}. Dry run complete.")
        return 0

    data = Path(data_dir)
    data.mkdir(parents=True, exist_ok=True)
    history_path = data / "ultimitas.json"
    existing = json.loads(history_path.read_text())["articles"] if history_path.exists() else []
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Every outlet, not just the two this page publishes: a minister's coverage
    # is wider than the front page's. Written before the early return below,
    # because the seven-day window keeps moving on a day with no new articles.
    write_ministros(data, list(unique.values()), now_iso)

    articles = merge_history(existing, matched, now_iso)
    if articles == existing and (data / "today.json").exists():
        print("No new articles; data unchanged.")
        return 0
    day, day_articles = select_today(articles)

    history_path.write_text(json.dumps(
        {"generated": now_iso, "sources": OUTLETS, "articles": articles},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (data / "today.json").write_text(json.dumps(
        {"generated": now_iso, "sources": OUTLETS, "date": day, "articles": day_articles},
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
