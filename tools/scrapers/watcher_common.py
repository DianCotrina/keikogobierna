"""Shared helpers for the discovery tools (evidence_watcher, elperuano_scraper, elcomercio_scraper).

HTTP, RSS-item parsing and GitHub plumbing common to every discovery source;
each tool keeps only its own filtering and output (issues vs data branch).
Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

API = "https://api.github.com"
DEFAULT_REPO = "DianCotrina/keikogobierna"
RSS_NS = {"dc": "http://purl.org/dc/elements/1.1/"}
LABEL = "evidencia-candidata"
LABEL_COLOR = "1F7A4D"
TIMEOUT = 20
USER_AGENT = "keikogobierna-evidence-tools"


def http_get(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def http_post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read() or "{}")


def gh_request(method: str, path: str, token: str, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            **({"Content-Type": "application/json"} if data else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read() or "{}")


def dedup_token(prefix: str, key: str) -> str:
    """Stable title token, e.g. dedup_token('np', 'LEY 31234|2026-07-10') -> 'np-<sha1[:10]>'."""
    return f"{prefix}-" + hashlib.sha1(key.encode()).hexdigest()[:10]


def normalize(text: str) -> str:
    """Lowercase + strip accents (NFKD) — shared matching normalizer."""
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


STOPWORDS = {
    "de", "la", "el", "en", "y", "para", "con", "los", "las", "del", "por",
    "un", "una", "que", "a", "su", "se", "al", "o", "e", "sus", "es",
}


def significant_tokens(text: str, extra_stop: frozenset = frozenset()) -> list[str]:
    """Normalized tokens minus stopwords and short tokens.

    Tokens <= 3 chars are dropped as noise, except ones containing a digit —
    short acronyms like "c5i" are distinctive (generic numbers like "100" or a
    year survive here but get dropped later by the index's document-frequency gate).
    """
    return [t for t in normalize(text).split()
            if (len(t) > 3 or any(c.isdigit() for c in t))
            and t not in STOPWORDS and t not in extra_stop]


def phrases_of(tokens: list[str]) -> set[str]:
    """Unigrams plus adjacent bigrams over a filtered token list."""
    out = set(tokens)
    out.update(f"{a} {b}" for a, b in zip(tokens, tokens[1:]))
    return out


def parse_rss_items(raw: bytes) -> list[dict]:
    """RSS bytes -> [{title, link, summary, author, published(datetime)}].

    Items missing a title, link or parseable pubDate are skipped. Callers keep
    their own filtering (keywords, age cutoff) and output mapping.
    """
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
            "link": link,
            "summary": (item.findtext("description") or "").strip(),
            "author": (item.findtext("dc:creator", default="", namespaces=RSS_NS) or "").strip(),
            "published": published,
        })
    return out


def issue_exists(token_str: str, repo: str, gh_token: str) -> bool:
    q = urllib.parse.quote(f'repo:{repo} in:title "{token_str}"')
    result = gh_request("GET", f"/search/issues?q={q}", gh_token)
    return result.get("total_count", 0) > 0


def ensure_label(repo: str, gh_token: str, name: str = LABEL, color: str = LABEL_COLOR,
                 description: str = "Evidencia candidata detectada por un watcher; requiere revisión editorial") -> None:
    try:
        gh_request("GET", f"/repos/{repo}/labels/{name}", gh_token)
    except urllib.error.HTTPError as err:
        if err.code != 404:
            raise
        gh_request("POST", f"/repos/{repo}/labels", gh_token, {
            "name": name,
            "color": color,
            "description": description,
        })


def create_issue(repo: str, gh_token: str, title: str, body: str, labels: list | None = None) -> dict:
    return gh_request("POST", f"/repos/{repo}/issues", gh_token, {
        "title": title,
        "body": body,
        "labels": labels or [LABEL],
    })
