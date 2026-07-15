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
