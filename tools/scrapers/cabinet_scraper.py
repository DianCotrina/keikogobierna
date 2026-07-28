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
from pathlib import Path

from cabinet_rules import is_cabinet_norma, parse_cabinet_act
from press_rules import announcements_from, judicial_signals
from singlefetch import MAX_PAGE_SIZE, fetch_page
from watcher_common import DEFAULT_REPO, create_issue, dedup_token, ensure_label, issue_exists

ROOT = Path(__file__).resolve().parent.parent.parent
CABINET_DIR = ROOT / "src" / "data" / "cabinet"

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


def _roster_names() -> list:
    """Everyone the site already tracks — appointed or announced."""
    people = json.loads((CABINET_DIR / "people.json").read_text(encoding="utf-8"))["people"]
    announcements = json.loads(
        (CABINET_DIR / "announcements.json").read_text(encoding="utf-8"))["announcements"]
    return sorted({p["name"] for p in people} | {a["person_name"] for a in announcements})


def announcement_block(announcements: list) -> str:
    """The JSON a reviewer pastes into announcements.json."""
    return json.dumps({"announcements": announcements}, ensure_ascii=False, indent=2)


def run_press(dry_run: bool) -> int:
    """Read the press feeds for a cabinet presented in public but not yet
    appointed by norma. Always provisional: these feed the `anunciado` state and
    are superseded the moment the Resolución Suprema publishes."""
    from ultimitas_scraper import fetch_sources

    articles, failed = fetch_sources()
    if failed:
        print(f"AVISO: fuentes caídas: {', '.join(failed)}")
    announcements = announcements_from(articles)

    print(f"prensa: {len(articles)} notas, {len(announcements)} anuncios de gabinete")
    for item in sorted(announcements, key=lambda a: a["portfolio"]):
        outlets = ", ".join(s["label"] for s in item["sources"])
        print(f"  {item['person_name']:32s} -> {item['portfolio']:26s} ({outlets})")

    if announcements:
        print("\nBloque propuesto para src/data/cabinet/announcements.json:\n")
        print(announcement_block(announcements))
        print("\nRevisa cada anuncio contra su nota antes de abrir el PR. Cuando El Peruano "
              "publique la Resolución Suprema, mueve la entrada a tenures.json y bórrala de aquí.")
    # Judicial coverage of people already on the roster. Discovery only: the
    # press reports allegations far more loosely than a court records them, so
    # each hit is a prompt to check a primary source, never a finding.
    roster = _roster_names()
    signals = judicial_signals(articles, roster)
    print(f"\nseñales judiciales sobre el gabinete: {len(signals)} "
          f"(sobre {len(roster)} persona(s) en el padrón)")
    for s in signals:
        print(f"  {s['person_name']} — {s['matched']}")
        print(f"      «{s['title'][:100]}»")
        print(f"      {s['source']} · {s['published']} · {s['url']}")
    if signals:
        print("\nNinguna de estas señales es un hecho probado. Contrasta cada una contra "
              "el expediente en el Poder Judicial antes de anotar nada en people.json, "
              "y registra la etapa que diga la resolución, no el titular.")

    if not dry_run:
        print("\nNota: este modo no escribe datos ni crea issues; copia el bloque en un PR.")
    return 0


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
    parser.add_argument("--from", dest="start", help="YYYY-MM-DD")
    parser.add_argument("--to", dest="end", help="YYYY-MM-DD (default: --from)")
    parser.add_argument("--press", action="store_true",
                        help="read announcements from the press feeds instead of the gazette")
    parser.add_argument("--dry-run", action="store_true",
                        help="print proposed blocks without creating issues")
    args = parser.parse_args()

    if args.press:
        return run_press(args.dry_run)
    if not args.start:
        print("--from is required unless --press", file=sys.stderr)
        return 2

    start = parse_date(args.start)
    end = parse_date(args.end) if args.end else start
    if end < start:
        print("--to precedes --from", file=sys.stderr)
        return 2
    return run(start, end, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
