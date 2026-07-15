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
  python3 tools/scrapers/elcomercio_scraper.py --dry-run           # print matches, no writes
  python3 tools/scrapers/elcomercio_scraper.py --data-dir <dir>    # merge into <dir>/*.json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from watcher_common import http_get, normalize, parse_rss_items

SOURCE = "El Comercio"
FEEDS = [
    "https://elcomercio.pe/arc/outboundfeeds/rss/category/politica/?outputType=xml",
    "https://elcomercio.pe/arc/outboundfeeds/rss/?outputType=xml",
]
BROWSER_UA = "Mozilla/5.0 (compatible; keikogobierna-ultimitas; +https://github.com/DianCotrina/keikogobierna)"
KEYWORDS = ["keiko fujimori", "keiko", "fuerza popular", "fujimorismo"]
LIMA = ZoneInfo("America/Lima")


# ---- Stage 1: fetch + parse ----------------------------------------------------

def canonical_url(url: str) -> str:
    """Scheme + host + path only — El Comercio appends ?ref=… tracking params."""
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def parse_feed(raw: bytes) -> list[dict]:
    return [{
        "title": rec["title"],
        "url": canonical_url(rec["link"]),
        "summary": rec["summary"],
        "author": rec["author"],
        "published": rec["published"].isoformat(),
    } for rec in parse_rss_items(raw)]


# ---- Stage 2: keyword filter ----------------------------------------------------

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

    unique: dict[str, dict] = {}
    for item in items:
        unique.setdefault(item["url"], item)
    matched = [i for i in unique.values() if item_matches(i)]
    print(f"{len(items)} items fetched ({len(unique)} unique), {len(matched)} matched")

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
    if articles == existing and (data / "today.json").exists():
        print("No new articles; data unchanged.")
        return 0
    day, day_articles = select_today(articles)

    history_path.write_text(json.dumps(
        {"generated": now_iso, "source": SOURCE, "articles": articles},
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
