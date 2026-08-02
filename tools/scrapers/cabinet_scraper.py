#!/usr/bin/env python3
"""Sweep El Peruano for cabinet appointments and resignations.

Seeds the roster from the official gazette so names, portfolios, dates and
norma numbers are derived rather than typed. Detection is deterministic
(cabinet_rules.py); this file only supplies the I/O.

This tool never writes src/data/cabinet/tenures.json. It prints — or files as a
GitHub issue — a ready-to-paste tenure block for a human to review and merge,
the same human gate the norma -> tracking.json path already uses.

Usage:
  python3 -m tools.scrapers.cabinet_scraper --from 2026-07-28 --to 2026-08-15 --dry-run
  GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo \
    python3 -m tools.scrapers.cabinet_scraper --from 2026-07-28 --to 2026-07-31
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta

from tools.scrapers.common.cabinet_note_rules import parse_cabinet_note
from tools.scrapers.common.cabinet_rules import (
    PORTFOLIO_IDS, is_cabinet_norma, parse_cabinet_act, read_cabinet, reconcile, roster_names)
from tools.scrapers.common.press_feeds import fetch_sources
from tools.scrapers.common.press_rules import announcements_from, judicial_signals
from tools.scrapers.common.elperuano_client import fetch_normas, norma_text
from tools.scrapers.common.watcher_common import (
    DEFAULT_REPO, create_issue, dedup_token, ensure_label, http_get, issue_exists)

LABEL = "cambio-de-gabinete"
LABEL_COLOR = "8250DF"


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def fetch_day(day: date) -> list[dict]:
    """Everything the gazette published on one day.

    Pagination, the three editions and the retry-on-transient-error live in the
    shared transport, so a fix there reaches the evidence reader and this sweep
    together. That was the point of moving it: El Peruano has already changed
    shape twice, and having one reader to repair is the whole benefit.
    """
    return fetch_normas(day.strftime("%Y%m%d"), day.isoformat())


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
        "una persona ya registrada en `ministers.json`, o crear su ficha primero.",
        "",
        f"<!-- {token} -->",
    ])


def announcement_block(announcements: list) -> str:
    """The JSON a reviewer pastes into announcements.json."""
    return json.dumps({"announcements": announcements}, ensure_ascii=False, indent=2)


def run_note(url: str, announced: str) -> int:
    """Read a whole cabinet from an El Peruano news note.

    The gazette lags a swearing-in by a day or so. In that window El Peruano's
    own news desk publishes the full roster in one structured list, which beats
    reconstructing it from nineteen separate press headlines. Still provisional:
    a note is not a Resolución Suprema, so this feeds `anunciado` like any other
    press source and is superseded the moment the norma publishes.
    """
    entries = parse_cabinet_note(http_get(url).decode("utf-8", "replace"))
    if not entries:
        print(f"No se reconoció ningún cargo en {url}", file=sys.stderr)
        print("Revisa que la nota liste «Ministro de <cartera>: <nombre>».", file=sys.stderr)
        return 1

    print(f"{len(entries)} carteras leídas de la nota ({len(PORTFOLIO_IDS)} en el registro)")
    for entry in entries:
        print(f"  {entry['portfolio']:26s} {entry['person_name']}")

    missing = PORTFOLIO_IDS - {e["portfolio"] for e in entries}
    if missing:
        print(f"\nSin titular en la nota: {', '.join(sorted(missing))}")

    announcements = [{
        "portfolio": entry["portfolio"],
        "person_name": entry["person_name"],
        "announced": announced,
        "sources": [{"label": "El Peruano", "url": url, "kind": "press"}],
    } for entry in entries]

    print("\nBloque propuesto para src/data/cabinet/announcements.json:\n")
    print(announcement_block(announcements))
    print("\nLa nota informativa de El Peruano no es la Resolución Suprema. Cuando el "
          "nombramiento se publique en Normas Legales, mueve cada entrada a tenures.json.")
    return 0


def run_press(dry_run: bool) -> int:
    """Read the press feeds for a cabinet presented in public but not yet
    appointed by norma. Always provisional: these feed the `anunciado` state and
    are superseded the moment the Resolución Suprema publishes."""
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
    roster = roster_names()
    signals = judicial_signals(articles, roster)
    print(f"\nseñales judiciales sobre el gabinete: {len(signals)} "
          f"(sobre {len(roster)} persona(s) en el padrón)")
    for s in signals:
        print(f"  {s['person_name']} — {s['matched']}")
        print(f"      «{s['title'][:100]}»")
        print(f"      {s['source']} · {s['published']} · {s['url']}")
    if signals:
        print("\nNinguna de estas señales es un hecho probado. Contrasta cada una contra "
              "el expediente en el Poder Judicial antes de anotar nada en ministers.json, "
              "y registra la etapa que diga la resolución, no el titular.")

    if not dry_run:
        print("\nNota: este modo no escribe datos ni crea issues; copia el bloque en un PR.")
    return 0


def sweep_acts(start: date, end: date):
    """Every readable cabinet act in a date range, yielded as it is found.

    A generator so `run` can interleave its per-act output with the per-day
    lines this prints; `run_fill` just drains it. Both modes used to carry
    their own copy of this loop, and a fix to one kept missing the other.
    """
    for day in daterange(start, end):
        records = fetch_day(day)
        candidates = [r for r in records if is_cabinet_norma(r)]
        print(f"{day.isoformat()}: {len(records)} normas, {len(candidates)} candidatas")
        for record in candidates:
            act = parse_cabinet_act(record, norma_text(record))
            if act:
                yield act
            else:
                # Detected as cabinet-shaped but unreadable. Say so loudly rather
                # than guessing at a name.
                print(f"  ! no se pudo leer {record['numero']} (op={record['op']})")


def run_fill(start: date, end: date) -> int:
    """Turn announced ministers into gazette-backed entries, for a person to merge.

    The announcements are provisional -- a proclamation is not a Resolución
    Suprema. This reconciles them against the gazette and prints the
    ministers.json and tenures.json entries the normas actually support, plus
    every disagreement. It writes nothing: the same human gate as everywhere
    else, and here it earns its keep, because the press had five of the
    nineteen names wrong.
    """
    acts = list(sweep_acts(start, end))
    result = reconcile(acts, read_cabinet("announcements.json", "announcements"),
                       read_cabinet("ministers.json", "ministers"))

    print(f"\n{len(result['tenures'])} nombramiento(s) con norma; "
          f"{len(result['ministers'])} ficha(s) nueva(s).")

    if result["conflicts"]:
        print("\nRevisar antes de fusionar:")
        for c in result["conflicts"]:
            extra = f" — anunciado: «{c['announced']}»" if c.get("announced") else ""
            gazette = f" — norma: «{c['gazette']}»" if c.get("gazette") else ""
            print(f"  [{c['kind']}] {c['portfolio']}{gazette}{extra}\n      {c['detail']}")
    else:
        print("\nSin discrepancias: cada cartera anunciada tiene su norma.")

    print("\n--- src/data/cabinet/ministers.json (entradas nuevas) ---")
    print(json.dumps({"ministers": result["ministers"]}, ensure_ascii=False, indent=2))
    print("\n--- src/data/cabinet/tenures.json ---")
    print(json.dumps({"tenures": result["tenures"]}, ensure_ascii=False, indent=2))
    print("\n`profession` y `bio` van vacíos a propósito: la norma no dice nada de "
          "eso. Escríbelos tú y cita la fuente. Este comando no escribe nada.")
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
    for act in sweep_acts(start, end):
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
    parser.add_argument("--noticia", metavar="URL",
                        help="read a whole cabinet from an El Peruano news note")
    parser.add_argument("--announced", metavar="YYYY-MM-DD",
                        help="date the cabinet was presented (default: today)")
    parser.add_argument("--fill", action="store_true",
                        help="reconcile the announced roster against the gazette and print "
                             "the ministers.json + tenures.json entries to merge")
    parser.add_argument("--dry-run", action="store_true",
                        help="print proposed blocks without creating issues")
    args = parser.parse_args()

    if args.noticia:
        return run_note(args.noticia, args.announced or date.today().isoformat())
    if args.press:
        return run_press(args.dry_run)
    if not args.start:
        print("--from is required unless --press or --noticia", file=sys.stderr)
        return 2

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end) if args.end else start
    if end < start:
        print("--to precedes --from", file=sys.stderr)
        return 2
    if args.fill:
        return run_fill(start, end)
    return run(start, end, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
