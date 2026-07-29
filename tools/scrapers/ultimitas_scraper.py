#!/usr/bin/env python3
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

from tools.scrapers.common.press_feeds import SOURCES, canonical_url, fetch_sources, parse_feed
from tools.scrapers.common.watcher_common import normalize

# Which of the shared feeds' items belong on /ultimitas/.
KEYWORDS = ["keiko fujimori", "keiko", "fuerza popular", "fujimorismo"]

LIMA = ZoneInfo("America/Lima")


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


# ---- Orchestration ---------------------------------------------------------------

def run(data_dir: str | None, dry_run: bool) -> int:
    items, failed = fetch_sources()
    if len(failed) == len(SOURCES):
        print("ERROR: every source failed", file=sys.stderr)
        return 1

    unique: dict[str, dict] = {}
    for item in items:
        unique.setdefault(item["url"], item)
    matched = [i for i in unique.values() if item_matches(i)]
    print(f"{len(items)} items fetched ({len(unique)} unique), {len(matched)} matched")

    if dry_run:
        for item in matched:
            print(f"[{item['published']}] [{item['source']}] {item['title'][:80]}")
        by_source = {s["name"]: sum(1 for i in matched if i["source"] == s["name"]) for s in SOURCES}
        print(f"Per source: {by_source}. Dry run complete.")
        return 0

    data = Path(data_dir)
    data.mkdir(parents=True, exist_ok=True)
    history_path = data / "ultimitas.json"
    existing = json.loads(history_path.read_text())["articles"] if history_path.exists() else []
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    articles = merge_history(existing, matched, now_iso)
    if articles == existing and (data / "today.json").exists():
        print("No new articles; data unchanged.")
        return 0
    day, day_articles = select_today(articles)

    history_path.write_text(json.dumps(
        {"generated": now_iso, "sources": [s["name"] for s in SOURCES], "articles": articles},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (data / "today.json").write_text(json.dumps(
        {"generated": now_iso, "sources": [s["name"] for s in SOURCES], "date": day, "articles": day_articles},
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
