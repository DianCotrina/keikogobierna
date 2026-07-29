"""The press feeds the site reads, and how to read them.

Shared deliberately: /ultimitas/ shows these headlines, cabinet_scraper --press
mines them for announcements, and judicial_signals scans them for coverage of
sitting ministers. One list, so adding an outlet reaches every consumer at once.

Metadata only — headline, summary, link, timestamp. Article bodies are never
read or stored; they belong to each outlet, and the site says so to its readers.
"""
from __future__ import annotations

import sys
import urllib.parse

from .watcher_common import http_get, parse_rss_items

SOURCES = [
    {"name": "El Comercio", "feeds": [
        "https://elcomercio.pe/arc/outboundfeeds/rss/category/politica/?outputType=xml",
        "https://elcomercio.pe/arc/outboundfeeds/rss/?outputType=xml",
    ]},
    {"name": "La República", "feeds": [
        "https://larepublica.pe/rss/politica.xml",
    ]},
    {"name": "RPP", "feeds": [
        "https://rpp.pe/feed",
    ]},
    {"name": "Gestión", "feeds": [
        "https://gestion.pe/arc/outboundfeeds/rss/?outputType=xml",
    ]},
]
BROWSER_UA = "Mozilla/5.0 (compatible; keikogobierna-ultimitas; +https://github.com/DianCotrina/keikogobierna)"


# ---- Stage 1: fetch + parse ----------------------------------------------------

def canonical_url(url: str) -> str:
    """Scheme + host + path only — El Comercio appends ?ref=… tracking params."""
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def parse_feed(raw: bytes, source: str) -> list[dict]:
    return [{
        "title": rec["title"],
        "url": canonical_url(rec["link"]),
        "summary": rec["summary"],
        "author": rec["author"],
        "published": rec["published"].isoformat(),
        "source": source,
    } for rec in parse_rss_items(raw)]


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
