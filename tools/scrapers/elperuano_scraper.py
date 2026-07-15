#!/usr/bin/env python3
"""Read the day's El Peruano normas (primary source) and file candidate-evidence issues.

Discovery, not certification: every matched norma becomes a GitHub issue for human
review; statuses in tracking.json change only through the PR flow. Four stages —
fetch (GraphQL) -> keyword prefilter -> optional Claude judge -> issues + archive.
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
  # add ANTHROPIC_API_KEY to enable the Claude judge (evidence drafts in each issue)
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

ROOT = Path(__file__).resolve().parent.parent.parent
KEYWORDS_PATH = Path(__file__).resolve().parent / "watcher_keywords.json"
TOPICS_DIR = ROOT / "src" / "data" / "plan" / "topics"

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
MODEL = "claude-opus-4-8"

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


# ---- Stage 3: Claude judge (optional) ----------------------------------------

def load_commitments() -> dict[str, str]:
    """id -> full text, across all topic files (proposals + first-100-days actions)."""
    out: dict[str, str] = {}
    for path in sorted(TOPICS_DIR.glob("*.json")):
        topic = json.loads(path.read_text())
        for group in topic.get("groups", []):
            for prop in group.get("proposals", []):
                out[prop["id"]] = prop["text"]
        for action in topic.get("first_100_days", []):
            out[action["id"]] = action["text"]
    return out


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
        from pypdf import PdfReader  # judge-stage-only dependency
        from io import BytesIO
        raw = http_get(record["url_pdf"])
        reader = PdfReader(BytesIO(raw))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return text.strip()[:15000] or record["sumilla"]
    except Exception as err:  # noqa: BLE001 - never lose a candidate to a PDF blip
        print(f"WARN: PDF extract failed for {record['numero']}: {err}", file=sys.stderr)
        return record["sumilla"]


JUDGE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "evaluations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "commitment_id": {"type": "string"},
                        "relation": {"type": "string", "enum": ["implements", "advances", "mentions", "unrelated"]},
                        "confidence": {"type": "number"},
                        "rationale": {"type": "string"},
                        "evidence_note": {"type": "string"},
                    },
                    "required": ["commitment_id", "relation", "confidence", "rationale", "evidence_note"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["evaluations"],
        "additionalProperties": False,
    },
}


def judge(record: dict, related: list[str], commitments: dict[str, str]) -> list[dict] | None:
    """Ask Claude which commitments this norma affects. None => judge unavailable/failed."""
    try:
        from anthropic import Anthropic
    except ImportError:
        return None

    listed = "\n".join(f"- {cid}: {commitments.get(cid, '(texto no encontrado)')}" for cid in related)
    prompt = f"""Eres analista de seguimiento del plan de gobierno peruano. Evalúa si esta norma
publicada en El Peruano guarda relación con alguno de los compromisos listados.

NORMA
Tipo: {record['tipo']}
Número: {record['numero']}
Sector: {record['sector']}
Sumilla: {record['sumilla']}
Texto:
{norma_text(record)}

COMPROMISOS A EVALUAR
{listed}

Para cada compromiso, indica la relación: "implements" (la norma lo cumple total o
sustancialmente), "advances" (avanza pero no lo completa), "mentions" (lo toca
tangencialmente) o "unrelated". Da una confianza de 0 a 1, una justificación breve, y
una nota de evidencia lista para citar (qué prueba y por qué). Responde solo el JSON."""

    try:
        client = Anthropic()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=8000,
            thinking={"type": "adaptive"},
            output_config={"format": JUDGE_SCHEMA},
            messages=[{"role": "user", "content": prompt}],
        )
        if resp.stop_reason == "refusal":
            print(f"WARN: judge refused for {record['numero']}", file=sys.stderr)
            return None
        text = "".join(b.text for b in resp.content if b.type == "text")
        evaluations = json.loads(text).get("evaluations", [])
        return [e for e in evaluations if e.get("relation") != "unrelated"]
    except Exception as err:  # noqa: BLE001 - fall back to a keyword-only issue
        print(f"WARN: judge failed for {record['numero']}: {err}", file=sys.stderr)
        return None


# ---- Stage 4: issue body ------------------------------------------------------

def issue_body(record: dict, related: list[str], verdicts: list[dict] | None, iso_date: str) -> str:
    related_lines = "\n".join(f"- `{cid}`" for cid in related) or "- (sin ids asociados)"
    header = f"""**Norma:** {record['tipo']} {record['numero']}
**Sector:** {record['sector']}
**Publicado:** {iso_date} · [El Peruano]({record['url_pdf'] or 'https://busquedas.elperuano.pe/'})
**Sumilla:** {record['sumilla'] or '(sin sumilla)'}

**Compromisos posiblemente relacionados:**
{related_lines}
"""

    if verdicts:
        blocks = []
        for v in verdicts:
            cid = v["commitment_id"]
            evidence = {
                "date": iso_date,
                "source": f"El Peruano — {record['tipo']} {record['numero']}".strip(),
                "url": record["url_pdf"] or "https://busquedas.elperuano.pe/",
                "note": v.get("evidence_note", ""),
            }
            blocks.append(
                f"""### `{cid}` — {v['relation']} (confianza {v.get('confidence', '?')})
{v.get('rationale', '')}

Evidencia lista para pegar en `src/data/tracking.json` (bajo `items["{cid}"].evidence`):
```json
{json.dumps(evidence, ensure_ascii=False, indent=2)}
```"""
            )
        judge_section = "\n\n---\n\n**Análisis (Claude):**\n\n" + "\n\n".join(blocks)
    else:
        judge_section = "\n\n_Sin análisis automático — revisar manualmente contra los compromisos listados._"

    checklist = """

---

**Revisión editorial:**
- [ ] Confirmar que la norma efectivamente cumple/avanza el compromiso
- [ ] Actualizar `src/data/tracking.json` (estado + evidencia + log) vía PR
- [ ] Cerrar este issue enlazando el PR o explicando el descarte

_Generado por el lector de El Peruano. Este issue no cambia ningún estado._"""

    return header + judge_section + checklist


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

    judge_enabled = bool(os.environ.get("ANTHROPIC_API_KEY"))
    commitments = load_commitments() if judge_enabled else {}
    if not dry_run:
        ensure_label(repo, gh_token)

    created = 0
    for record, related in matched:
        token_str = dedup_token("np", f"{record['tipo']}|{record['numero']}|{iso_date}")
        verdicts = judge(record, related, commitments) if judge_enabled else None

        if dry_run:
            tag = f"judge={len(verdicts)}" if verdicts is not None else "keyword-only"
            print(f"[{token_str}] {record['tipo']} {record['numero']} ({tag}) — {record['sumilla'][:70]}")
            continue

        if created >= MAX_NEW_ISSUES:
            print(f"Reached cap of {MAX_NEW_ISSUES} new issues; stopping.")
            break
        if issue_exists(token_str, repo, gh_token):
            continue
        title = f"Norma candidata: {record['tipo']} {record['numero']} [{token_str}]"[:250]
        issue = create_issue(repo, gh_token, title, issue_body(record, related, verdicts, iso_date))
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
