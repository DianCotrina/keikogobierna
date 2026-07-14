"""Shared helpers for the evidence discovery tools (evidence_watcher, elperuano_reader).

HTTP + GitHub-issue plumbing common to every discovery source. Both tools file
'evidencia-candidata' issues for human review with a stateless dedup token in
the title; the discovery half (RSS vs GraphQL) differs, this half does not.
Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
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
            "description": "Evidencia candidata detectada por un watcher; requiere revisión editorial",
        })


def create_issue(repo: str, gh_token: str, title: str, body: str) -> dict:
    return gh_request("POST", f"/repos/{repo}/issues", gh_token, {
        "title": title,
        "body": body,
        "labels": [LABEL],
    })
