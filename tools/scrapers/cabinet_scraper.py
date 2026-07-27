#!/usr/bin/env python3
"""Sweep El Peruano for cabinet appointments and resignations.

Seeds the roster from the official gazette so names, portfolios, dates and
norma numbers are derived rather than typed. Detection is deterministic
(cabinet_rules.py); this file only supplies the I/O.

This tool never writes src/data/cabinet/tenures.json. It prints — or files as a
GitHub issue — a ready-to-paste tenure block for a human to review and merge,
the same human gate the norma -> tracking.json path already uses.

Usage:
  python3 tools/scrapers/cabinet_scraper.py --from 2026-07-28 --to 2026-08-15 --dry-run
  GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo \
    python3 tools/scrapers/cabinet_scraper.py --from 2026-07-28 --to 2026-07-31
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta

from cabinet_rules import is_cabinet_norma, parse_cabinet_act
from singlefetch import MAX_PAGE_SIZE, fetch_page
from watcher_common import DEFAULT_REPO, create_issue, dedup_token, ensure_label, issue_exists

LABEL = "cambio-de-gabinete"
LABEL_COLOR = "8250DF"


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def fetch_day(day: date) -> list[dict]:
    """All Normas Legales published on one day."""
    stamp = day.strftime("%Y%m%d")
    records: list[dict] = []
    start = 0
    while True:
        page, has_next = fetch_page(stamp, stamp, start=start, paginated_by=MAX_PAGE_SIZE)
        records.extend(page)
        if not has_next or not page:
            break
        start += MAX_PAGE_SIZE
    return records


def norma_text(op: str) -> str:
    """Full norma body. Imported lazily so a --dry-run listing costs no extra
    requests when nothing matched."""
    from elperuano_scraper import VISOR_HTML_URL, html_to_text
    from watcher_common import http_get
    return html_to_text(http_get(VISOR_HTML_URL.format(op=op)))


def tenure_block(act: dict) -> str:
    """The JSON a reviewer pastes into tenures.json."""
    if act["action"] == "nombramiento":
        payload = {
            "person": "<slug-de-la-persona>",
            "portfolio": act["portfolio"],
            "start": act["date"],
            "end": None,
            "appointment_norma": {"numero": act["norma"], "url": act["url"], "date": act["date"]},
            "exit_norma": None,
            "exit_reason": None,
        }
    else:
        payload = {
            "_comment": "cierra la tenure abierta de esta cartera",
            "portfolio": act["portfolio"],
            "end": act["date"],
            "exit_norma": {"numero": act["norma"], "url": act["url"], "date": act["date"]},
            "exit_reason": "renuncia",
        }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def issue_body(act: dict, token: str) -> str:
    return "\n".join([
        f"**Acto:** {act['action']}",
        f"**Persona (según la norma):** {act['person']}",
        f"**Cartera:** `{act['portfolio']}`",
        f"**Norma:** {act['norma']} ({act['date']})",
        f"**Fuente:** {act['url']}",
        "",
        "Bloque propuesto para `src/data/cabinet/tenures.json`:",
        "",
        "```json",
        tenure_block(act),
        "```",
        "",
        "Revisa contra la norma antes de abrir el PR. El nombre debe corresponder a "
        "una persona ya registrada en `people.json`, o crear su ficha primero.",
        "",
        f"<!-- {token} -->",
    ])


def run(start: date, end: date, dry_run: bool) -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO)
    gh_token = os.environ.get("GITHUB_TOKEN")
    if not dry_run and not gh_token:
        print("GITHUB_TOKEN is required unless --dry-run", file=sys.stderr)
        return 2

    if not dry_run:
        ensure_label(repo, gh_token, LABEL, LABEL_COLOR,
                     "Nombramiento o renuncia ministerial detectada en El Peruano")

    found = 0
    for day in daterange(start, end):
        records = fetch_day(day)
        candidates = [r for r in records if is_cabinet_norma(r)]
        print(f"{day.isoformat()}: {len(records)} normas, {len(candidates)} candidatas")

        for record in candidates:
            act = parse_cabinet_act(record, norma_text(record["op"]))
            if not act:
                # Detected as cabinet-shaped but unreadable. Say so loudly rather
                # than guessing at a name.
                print(f"  ! no se pudo leer {record['numero']} (op={record['op']})")
                continue

            found += 1
            title = (f"Gabinete: {act['action']} — {act['person']} "
                     f"({act['portfolio']}) {act['date']}")
            token = dedup_token("cab", f"{act['norma']}|{act['portfolio']}|{act['action']}")

            if dry_run:
                print(f"  [{token}] {title}")
                print(tenure_block(act))
                continue
            if issue_exists(token, repo, gh_token):
                print(f"  [{token}] ya existe, omitido")
                continue
            create_issue(repo, gh_token, title, issue_body(act, token), [LABEL])
            print(f"  [{token}] issue creada: {title}")

    print(f"{'Dry run complete' if dry_run else 'Listo'}: {found} actos de gabinete.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--to", dest="end", help="YYYY-MM-DD (default: --from)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print proposed tenure blocks without creating issues")
    args = parser.parse_args()

    start = parse_date(args.start)
    end = parse_date(args.end) if args.end else start
    if end < start:
        print("--to precedes --from", file=sys.stderr)
        return 2
    return run(start, end, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
