#!/usr/bin/env python3
"""Read the day's El Peruano normas (primary source) and file candidate-evidence issues.

Discovery, not certification: every matched norma becomes a GitHub issue for human
review; statuses in tracking.json change only through the PR flow. Three stages —
fetch (GraphQL) -> keyword prefilter -> issues (with a text excerpt) + archive.
No AI anywhere: reviewing a candidate is a human job, by design.
See workflows/elperuano_scraper.md.

Reconnaissance (2026-07-12, extended 2026-07-15): busquedas.elperuano.pe exposes
an unauthenticated GraphQL API at /api/graphql. Query getGenericPublication
returns structured per-norma records (tipo, numero, sector, sumilla, urlPDF, op),
and /api/visor_html/<op> serves the norma's full text as clean single-norma HTML
(~13KB vs ~400KB for the page-scoped PDF). Both are unofficial interfaces — if
they change, the run fails loudly and we fix the tool.

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
from datetime import date, datetime, timezone
from pathlib import Path

from watcher_common import (
    DEFAULT_REPO,
    create_issue,
    dedup_token,
    ensure_label,
    http_get,
    http_post_json,
    issue_exists,
    normalize,
)

KEYWORDS_PATH = Path(__file__).resolve().parent / "watcher_keywords.json"

GRAPHQL_URL = "https://busquedas.elperuano.pe/api/graphql"
GRAPHQL_QUERY = """query Generic($fechaIni: String, $fechaFin: String, $paginatedBy: Int, $start: Int) {
  results: getGenericPublication(fechaIni: $fechaIni, fechaFin: $fechaFin, paginatedBy: $paginatedBy, start: $start) {
    totalHits start hasNext paginatedBy
    hits { fechaPublicacion nombreDispositivo tipoDispositivo sector rubro sumilla urlPDF urlPortada op }
  }
}"""
VISOR_HTML_URL = "https://busquedas.elperuano.pe/api/visor_html/{op}"
PAGE_SIZE = 100
MAX_NEW_ISSUES = 10
EXCERPT_CHARS = 1200  # norma-text excerpt embedded in each issue for review

# Tunable noise gate: norma types to skip outright (municipal/local acts rarely
# touch national commitments). Empty by default — the keyword filter is the real
# relevance gate; add tipos here only if local noise shows up in the queue.
SKIP_TIPOS: set[str] = set()

STOPWORDS = {
    "de", "la", "el", "en", "y", "para", "con", "los", "las", "del", "por",
    "un", "una", "que", "a", "su", "se", "al", "o", "e", "sus", "es",
}


# ---- Stage 1: fetch (GraphQL) -------------------------------------------------

def map_hit(hit: dict) -> dict:
    return {
        "tipo": (hit.get("tipoDispositivo") or "").strip(),
        "numero": (hit.get("nombreDispositivo") or "").strip(),
        "sector": (hit.get("sector") or "").strip(),
        "rubro": (hit.get("rubro") or "").strip(),
        "sumilla": (hit.get("sumilla") or "").strip(),
        "url_pdf": (hit.get("urlPDF") or "").strip(),
        "fecha": (hit.get("fechaPublicacion") or "").strip(),
        "op": (hit.get("op") or "").strip(),
    }


def parse_results(payload: dict) -> tuple[list[dict], bool]:
    """Map a raw GraphQL response page -> (records, has_next). Shared by fetch and tests."""
    results = (payload.get("data") or {}).get("results") or {}
    hits = results.get("hits") or []
    records = [map_hit(h) for h in hits]
    return records, bool(results.get("hasNext"))


def fetch_normas(yyyymmdd: str) -> list[dict]:
    records: list[dict] = []
    start = 0
    while True:
        payload = http_post_json(GRAPHQL_URL, {
            "query": GRAPHQL_QUERY,
            "variables": {"fechaIni": yyyymmdd, "fechaFin": yyyymmdd, "paginatedBy": PAGE_SIZE, "start": start},
        }, headers={"Origin": "https://busquedas.elperuano.pe"})
        page, has_next = parse_results(payload)
        records.extend(page)
        if not has_next or not page:
            break
        start += PAGE_SIZE
    return [r for r in records if r["tipo"] not in SKIP_TIPOS]


# ---- Stage 2: keyword prefilter ----------------------------------------------

def significant_terms(query: str) -> list[str]:
    return [t for t in normalize(query).split() if len(t) > 3 and t not in STOPWORDS]


def match_record(record: dict, keywords: list[dict]) -> list[str]:
    """Return the related commitment ids for every keyword entry this norma matches."""
    haystack = normalize(f"{record['numero']} {record['tipo']} {record['sumilla']}")
    related: list[str] = []
    for entry in keywords:
        terms = significant_terms(entry["query"])
        if not terms:
            continue
        present = sum(1 for t in terms if t in haystack)
        if present >= min(2, len(terms)):
            related.extend(entry.get("related", []))
    return sorted(set(related))


# ---- Stage 3: norma text (for the issue excerpt) ------------------------------

def html_to_text(raw: bytes) -> str:
    """Plain text from an /api/visor_html rendition (stdlib only).

    The <head> goes too: the visor's <title> carries an unrelated norma's name.
    """
    text = re.sub(r"<head\b.*?</head>", " ", raw.decode("utf-8", "replace"), flags=re.S | re.I)
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def norma_text(record: dict) -> str:
    """Full norma text: HTML rendition first, then the page PDF, then the sumilla.

    The visor_html rendition is single-norma and ~30x lighter than the PDF, which
    is page-scoped (bleeds into neighboring normas) and needs pypdf. Not every
    norma has an HTML rendition, hence the chain.
    """
    if record.get("op"):
        try:
            text = html_to_text(http_get(VISOR_HTML_URL.format(op=record["op"])))
            if len(text) > len(record["sumilla"]):
                return text[:15000]
        except Exception as err:  # noqa: BLE001 - fall through to the PDF
            print(f"WARN: visor_html failed for {record['numero']}: {err}", file=sys.stderr)
    if not record["url_pdf"]:
        return record["sumilla"]
    try:
        from pypdf import PdfReader  # only needed when a norma lacks an HTML rendition
        from io import BytesIO
        raw = http_get(record["url_pdf"])
        reader = PdfReader(BytesIO(raw))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return text.strip()[:15000] or record["sumilla"]
    except Exception as err:  # noqa: BLE001 - never lose a candidate to a PDF blip
        print(f"WARN: PDF extract failed for {record['numero']}: {err}", file=sys.stderr)
        return record["sumilla"]


# ---- Stage 4: issue body ------------------------------------------------------

def issue_body(record: dict, related: list[str], iso_date: str, excerpt: str) -> str:
    related_lines = "\n".join(f"- `{cid}`" for cid in related) or "- (sin ids asociados)"
    evidence = {
        "date": iso_date,
        "source": f"El Peruano — {record['tipo']} {record['numero']}".strip(),
        "url": record["url_pdf"] or "https://busquedas.elperuano.pe/",
        "note": "",
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
**Publicado:** {iso_date} · [El Peruano]({record['url_pdf'] or 'https://busquedas.elperuano.pe/'})
**Sumilla:** {record['sumilla'] or '(sin sumilla)'}

**Compromisos posiblemente relacionados:**
{related_lines}{excerpt_section}

Evidencia lista para completar en `src/data/tracking.json` (falta la `note`):
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
    keywords = json.loads(KEYWORDS_PATH.read_text())

    repo = os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO)
    gh_token = os.environ.get("GITHUB_TOKEN", "")
    if not dry_run and not gh_token:
        print("ERROR: GITHUB_TOKEN required unless --dry-run", file=sys.stderr)
        return 1

    records = fetch_normas(yyyymmdd)
    if archive_dir:
        write_archive(archive_dir, iso_date, records)
    matched = [(r, rel) for r in records if (rel := match_record(r, keywords))]
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
        excerpt = " ".join(norma_text(record).split())[:EXCERPT_CHARS]
        title = f"Norma candidata: {record['tipo']} {record['numero']} [{token_str}]"[:250]
        issue = create_issue(repo, gh_token, title, issue_body(record, related, iso_date, excerpt))
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
