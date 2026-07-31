#!/usr/bin/env python3
"""Read the day's El Peruano normas (primary source) and file candidate-evidence issues.

Discovery, not certification: every matched norma becomes a GitHub issue for human
review; statuses in tracking.json change only through the PR flow. Three stages —
fetch (public search page) -> keyword prefilter -> issues (with a text excerpt) + archive.
No AI anywhere: reviewing a candidate is a human job, by design.
See workflows/elperuano_scraper.md.

Reconnaissance (2026-07-31): El Peruano rebuilt busquedas.elperuano.pe as a React
Router app and removed the old unauthenticated /api/graphql endpoint (now 404).
The public search page still serves the day's normas as server-rendered cards at
  /?fechaIni=YYYYMMDD&fechaFin=YYYYMMDD&tipoPublicacion=<NL|BO|PC>&ci=ONLY&start=<n>
20 cards/page, paginated by `start`. Each card carries the sector, tipo, numero,
sumilla and the norma's `op` (via /dispositivo/<tipoPub>/<op>). The dispositivo
page embeds the clean single-norma rendition inside a #visor-html box — the same
document the retired /api/visor_html/<op> served. All unofficial: if the markup
changes, the run fails loudly in Actions and we fix the tool.

Usage:
  python3 tools/scrapers/elperuano_scraper.py --dry-run   # today, print records/matches, no writes
  python3 tools/scrapers/elperuano_scraper.py --date 2026-07-10 --dry-run
  GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo python3 tools/scrapers/elperuano_scraper.py
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
from datetime import date, datetime, timezone
from pathlib import Path

from matcher import load_matcher
from watcher_common import (
    DEFAULT_REPO,
    LABEL,
    create_issue,
    dedup_token,
    ensure_label,
    http_get,
    issue_exists,
)

BASE = "https://busquedas.elperuano.pe"
SEARCH_URL = BASE + "/?fechaIni={d}&fechaFin={d}&tipoPublicacion={tipo}&ci=ONLY&start={start}"
DISPOSITIVO_URL = BASE + "/dispositivo/{tipo_pub}/{op}"
# The three daily editions the site exposes: Normas Legales, Boletín Oficial, PC.
TIPOS_PUBLICACION = ("NL", "BO", "PC")
PAGE_SIZE = 20   # cards per search page (site-fixed)
MAX_PAGES = 60   # safety cap per edition: 60*20 = 1200 normas/day
MAX_NEW_ISSUES = 10
EXCERPT_CHARS = 1200  # norma-text excerpt embedded in each issue for review

# Tunable noise gate: norma types to skip outright (municipal/local acts rarely
# touch national commitments). Empty by default — the matcher is the real
# relevance gate; add tipos here only if local noise shows up in the queue.
SKIP_TIPOS: set[str] = set()


# ---- Stage 1: fetch (public search page) --------------------------------------

def _text(match: "re.Match | None") -> str:
    """Inner text of a regex capture: strip tags, unescape entities, collapse space."""
    if not match:
        return ""
    stripped = re.sub(r"<[^>]+>", " ", match.group(1))
    return re.sub(r"\s+", " ", html.unescape(stripped)).strip()


def parse_search_cards(page: str, tipo_pub: str, iso_date: str) -> list[dict]:
    """Map one search-results page -> records. Shared by fetch and tests.

    Each result is a `rounded-xl border bg-card` block carrying the norma's sector,
    tipo, numero, sumilla and its `op` (from the /dispositivo/<tipoPub>/<op> link).
    """
    records: list[dict] = []
    for chunk in page.split('<div class="rounded-xl border bg-card')[1:]:
        href = re.search(r"/dispositivo/[A-Za-z]+/(\d+-\d+)", chunk)
        if not href:
            continue
        op = href.group(1)
        records.append({
            "tipo": _text(re.search(r'<p class="text-xs text-muted-foreground">(.*?)</p>', chunk, re.S)),
            "numero": _text(re.search(r'font-medium text-muted-foreground">(.*?)</p>', chunk, re.S)),
            "sector": _text(re.search(r'text-primary[^>]*>(.*?)</p>', chunk, re.S)),
            "rubro": "",  # the old GraphQL had a rubro; the cards don't expose one
            "sumilla": _text(re.search(r'line-clamp-3[^>]*>(.*?)</a>', chunk, re.S)),
            "url": DISPOSITIVO_URL.format(tipo_pub=tipo_pub, op=op),
            "fecha": iso_date,
            "op": op,
            "tipo_pub": tipo_pub,
        })
    return records


RETRY_ATTEMPTS = 4  # the site returns transient 404s/5xx under load; one blip must not kill the day


def _get_page(url: str) -> str:
    """GET a search page, retrying transient HTTP/network errors with backoff."""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return http_get(url).decode("utf-8", "replace")
        except (urllib.error.HTTPError, urllib.error.URLError) as err:
            if attempt == RETRY_ATTEMPTS - 1:
                raise
            print(f"WARN: {url} failed ({err}); retry {attempt + 1}/{RETRY_ATTEMPTS - 1}", file=sys.stderr)
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
    raise AssertionError("unreachable")  # loop either returns or raises


def fetch_normas(yyyymmdd: str, iso_date: str) -> list[dict]:
    """The day's normas across all three editions, de-duplicated by op."""
    records: list[dict] = []
    seen: set[str] = set()
    for tipo_pub in TIPOS_PUBLICACION:
        for page_no in range(MAX_PAGES):
            url = SEARCH_URL.format(d=yyyymmdd, tipo=tipo_pub, start=page_no * PAGE_SIZE)
            try:
                page = _get_page(url)
            except urllib.error.HTTPError as err:
                # A normal edition-end is a short page, not a 404; a 404 that persists
                # past page 0 is the pagination tail — stop this edition instead of failing.
                if err.code == 404 and page_no > 0:
                    print(f"WARN: {tipo_pub} start={page_no * PAGE_SIZE}: 404 after retries — end of edition", file=sys.stderr)
                    break
                raise
            cards = parse_search_cards(page, tipo_pub, iso_date)
            for rec in cards:
                if rec["op"] not in seen:
                    seen.add(rec["op"])
                    records.append(rec)
            if len(cards) < PAGE_SIZE:  # short page => last page of this edition
                break
    return [r for r in records if r["tipo"] not in SKIP_TIPOS]


# ---- Stage 2: match against plan commitments ---------------------------------
# Matching lives in tools/scrapers/matcher.py (shared). A norma's numero + tipo +
# sumilla is matched against the distinctive-phrase index built from the plan.


# ---- Stage 3: norma text (for the issue excerpt) ------------------------------

def html_to_text(raw: bytes) -> str:
    """Plain text from a single-norma HTML rendition (stdlib only).

    The <head> goes too: the rendition's <title> carries an unrelated norma's name.
    """
    text = re.sub(r"<head\b.*?</head>", " ", raw.decode("utf-8", "replace"), flags=re.S | re.I)
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def extract_visor_html(page: bytes) -> bytes:
    """The embedded single-norma document from a /dispositivo/ page's #visor-html box."""
    text = page.decode("utf-8", "replace")
    i = text.find('id="visor-html"')
    if i < 0:
        return b""
    m = re.search(r"<html\b.*?</html>", text[i:], re.S)
    return m.group(0).encode("utf-8") if m else b""


def norma_text(record: dict) -> str:
    """Full norma text from the /dispositivo/ page's embedded rendition; sumilla on failure.

    The dispositivo page inlines the clean single-norma document in #visor-html;
    everything else on that page (toolbar, sibling normas) is stripped by working
    from that box only. Any fetch/parse blip falls back to the sumilla so a
    candidate is never lost to it.
    """
    try:
        visor = extract_visor_html(http_get(record["url"]))
        if visor:
            text = html_to_text(visor)
            if len(text) > len(record["sumilla"]):
                return text[:15000]
    except Exception as err:  # noqa: BLE001 - never lose a candidate to a fetch blip
        print(f"WARN: dispositivo fetch failed for {record['numero']}: {err}", file=sys.stderr)
    return record["sumilla"]


# ---- Stage 4: issue body ------------------------------------------------------

def draft_note(record: dict) -> str:
    """A non-blank starting note for the evidence block: the norma's own summary,
    which the reviewer refines into how it cumple/avanza the commitment."""
    sumilla = record["sumilla"].strip()
    if sumilla:
        return sumilla if sumilla.endswith(".") else sumilla + "."
    return f"{record['tipo']} {record['numero']} (El Peruano, {record['fecha']})."


def issue_body(record: dict, related: list[str], iso_date: str, excerpt: str) -> str:
    related_lines = "\n".join(f"- `{cid}`" for cid in related) or "- (sin ids asociados)"
    evidence = {
        "date": iso_date,
        "source": f"El Peruano — {record['tipo']} {record['numero']}".strip(),
        "url": record["url"],
        "note": draft_note(record),
    }

    excerpt_section = ""
    if excerpt and excerpt != record["sumilla"]:
        excerpt_section = f"""

<details>
<summary>Texto de la norma (extracto)</summary>

> {excerpt}

</details>"""

    return f"""**Norma:** {record['tipo']} {record['numero']}
**Sector:** {record['sector']}
**Publicado:** {iso_date} · [El Peruano]({record['url']})
**Sumilla:** {record['sumilla'] or '(sin sumilla)'}

**Compromisos posiblemente relacionados:**
{related_lines}{excerpt_section}

Evidencia lista para `src/data/tracking.json` — la `note` trae un borrador (la sumilla de la norma); revísala y ajústala al compromiso antes de certificar:
```json
{json.dumps(evidence, ensure_ascii=False, indent=2)}
```

---

**Revisión editorial:**
- [ ] Confirmar que la norma efectivamente cumple/avanza el compromiso
- [ ] Actualizar `src/data/tracking.json` (estado + evidencia + log) vía PR
- [ ] Cerrar este issue enlazando el PR o explicando el descarte

_Generado por el scraper de El Peruano. Este issue no cambia ningún estado._"""


# ---- Orchestration ------------------------------------------------------------

def write_archive(archive_dir: str, iso_date: str, records: list[dict]) -> None:
    path = Path(archive_dir)
    path.mkdir(parents=True, exist_ok=True)
    out = path / f"{iso_date}.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Archived {len(records)} records to {out}")


def run(target: date, dry_run: bool, archive_dir: str | None) -> int:
    yyyymmdd = target.strftime("%Y%m%d")
    iso_date = target.isoformat()
    matcher = load_matcher()

    repo = os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO)
    gh_token = os.environ.get("GITHUB_TOKEN", "")
    if not dry_run and not gh_token:
        print("ERROR: GITHUB_TOKEN required unless --dry-run", file=sys.stderr)
        return 1

    records = fetch_normas(yyyymmdd, iso_date)
    if archive_dir:
        write_archive(archive_dir, iso_date, records)
    matched = [
        (r, rel) for r in records
        if (rel := matcher.match(f"{r['numero']} {r['tipo']} {r['sumilla']}"))
    ]
    print(f"{iso_date}: {len(records)} normas, {len(matched)} matched")

    if not matched:
        print("No matches; nothing to file.")
        return 0

    if not dry_run:
        ensure_label(repo, gh_token)

    created = 0
    for record, related in matched:
        token_str = dedup_token("np", f"{record['tipo']}|{record['numero']}|{iso_date}")

        if dry_run:
            print(f"[{token_str}] {record['tipo']} {record['numero']} — {record['sumilla'][:70]}")
            continue

        if created >= MAX_NEW_ISSUES:
            print(f"Reached cap of {MAX_NEW_ISSUES} new issues; stopping.")
            break
        if issue_exists(token_str, repo, gh_token):
            continue
        tema_labels = sorted({f"tema:{s}" for cid in related if (s := matcher.tema_slug(cid))})
        for tl in tema_labels:
            ensure_label(repo, gh_token, name=tl, color="6B6F7B",
                         description=f"Compromisos del tema «{tl.split(':', 1)[1]}»")
        excerpt = " ".join(norma_text(record).split())[:EXCERPT_CHARS]
        title = f"Norma candidata: {record['tipo']} {record['numero']} [{token_str}]"[:250]
        issue = create_issue(repo, gh_token, title, issue_body(record, related, iso_date, excerpt),
                             labels=[LABEL] + tema_labels)
        created += 1
        print(f"Created issue #{issue['number']}: {record['tipo']} {record['numero']}")

    print("Dry run complete." if dry_run else f"Done: {created} issue(s) created.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="YYYY-MM-DD (default: today, UTC)")
    parser.add_argument("--dry-run", action="store_true", help="print records/matches without writing issues")
    parser.add_argument("--archive-dir", help="write the day's records as <dir>/<date>.jsonl")
    args = parser.parse_args()

    if args.date:
        target = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        target = datetime.now(timezone.utc).date()

    return run(target, args.dry_run, args.archive_dir)


if __name__ == "__main__":
    sys.exit(main())
