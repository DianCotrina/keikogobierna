#!/usr/bin/env python3
"""Discover candidate evidence for tracked commitments and file GitHub issues.

Fetches Google News RSS (Peru-scoped) for each query in tools/watcher_keywords.json,
keeps recent entries, and opens one issue per new candidate for human review.
The watcher only suggests: statuses in tracking.json change exclusively through
the PR flow. Stdlib only. See workflows/evidence_watcher.md.

Usage:
  python3 tools/evidence_watcher.py --dry-run   # print candidates, no GitHub calls
  GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo python3 tools/evidence_watcher.py
"""

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYWORDS_PATH = ROOT / "tools" / "watcher_keywords.json"
RSS_URL = "https://news.google.com/rss/search?q={query}&hl=es-419&gl=PE&ceid=PE:es-419"
API = "https://api.github.com"
LABEL = "evidencia-candidata"
LABEL_COLOR = "1F7A4D"
MAX_NEW_ISSUES = 5
MAX_AGE_DAYS = 7
TIMEOUT = 20


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "keikogobierna-evidence-watcher"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def gh_request(method: str, path: str, token: str, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "keikogobierna-evidence-watcher",
            **({"Content-Type": "application/json"} if data else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read() or "{}")


def fetch_candidates(query: str):
    url = RSS_URL.format(query=urllib.parse.quote(query))
    root = ET.fromstring(http_get(url))
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_raw = item.findtext("pubDate") or ""
        if not title or not link:
            continue
        try:
            published = parsedate_to_datetime(pub_raw)
        except (TypeError, ValueError):
            continue
        if published >= cutoff:
            out.append({"title": title, "link": link, "published": published})
    return out


def dedup_token(link: str) -> str:
    return "ev-" + hashlib.sha1(link.encode()).hexdigest()[:10]


def issue_exists(token_str: str, repo: str, gh_token: str) -> bool:
    q = urllib.parse.quote(f'repo:{repo} in:title "{token_str}"')
    result = gh_request("GET", f"/search/issues?q={q}", gh_token)
    return result.get("total_count", 0) > 0


def ensure_label(repo: str, gh_token: str) -> None:
    try:
        gh_request("GET", f"/repos/{repo}/labels/{LABEL}", gh_token)
    except urllib.error.HTTPError as err:
        if err.code != 404:
            raise
        gh_request("POST", f"/repos/{repo}/labels", gh_token, {
            "name": LABEL,
            "color": LABEL_COLOR,
            "description": "Evidencia candidata detectada por el watcher; requiere revisión editorial",
        })


def create_issue(repo: str, gh_token: str, cand: dict, query: str, related: list) -> dict:
    token_str = dedup_token(cand["link"])
    related_lines = "\n".join(f"- `{item_id}`" for item_id in related) or "- (sin ids asociados)"
    body = f"""**Titular:** {cand['title']}
**Enlace:** {cand['link']}
**Publicado:** {cand['published'].date().isoformat()}
**Búsqueda:** `{query}`

**Compromisos posiblemente relacionados:**
{related_lines}

---

**Revisión editorial:**
- [ ] Verificar el hecho en una fuente oficial (El Peruano, MEF, INEI, Congreso)
- [ ] Si aplica, actualizar `src/data/tracking.json` (estado + evidencia + log) vía PR
- [ ] Cerrar este issue enlazando el PR o explicando el descarte

_Generado por el evidence watcher. Este issue no cambia ningún estado._"""
    return gh_request("POST", f"/repos/{repo}/issues", gh_token, {
        "title": f"Evidencia candidata: {cand['title'][:120]} [{token_str}]",
        "body": body,
        "labels": [LABEL],
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print candidates without touching GitHub")
    args = parser.parse_args()

    keywords = json.loads(KEYWORDS_PATH.read_text())
    repo = os.environ.get("GITHUB_REPOSITORY", "DianCotrina/keikogobierna")
    gh_token = os.environ.get("GITHUB_TOKEN", "")
    if not args.dry_run and not gh_token:
        print("ERROR: GITHUB_TOKEN required unless --dry-run", file=sys.stderr)
        return 1

    if not args.dry_run:
        ensure_label(repo, gh_token)

    seen_tokens = set()
    created = 0
    failed_queries = 0

    for entry in keywords:
        query, related = entry["query"], entry.get("related", [])
        try:
            candidates = fetch_candidates(query)
        except Exception as err:  # one bad feed never kills the run
            print(f"WARN: query '{query}' failed: {err}", file=sys.stderr)
            failed_queries += 1
            continue

        for cand in candidates:
            token_str = dedup_token(cand["link"])
            if token_str in seen_tokens:
                continue
            seen_tokens.add(token_str)

            if args.dry_run:
                print(f"[{token_str}] ({query}) {cand['published'].date()} — {cand['title']}")
                continue

            if created >= MAX_NEW_ISSUES:
                print(f"Reached cap of {MAX_NEW_ISSUES} new issues; stopping.")
                print(f"Done: {created} issue(s) created.")
                return 0
            if issue_exists(token_str, repo, gh_token):
                continue
            issue = create_issue(repo, gh_token, cand, query, related)
            created += 1
            print(f"Created issue #{issue['number']}: {cand['title'][:80]}")

    if failed_queries == len(keywords):
        print("ERROR: every query failed", file=sys.stderr)
        return 1
    print(f"Done: {created} issue(s) created." if not args.dry_run else "Dry run complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
