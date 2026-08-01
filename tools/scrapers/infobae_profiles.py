#!/usr/bin/env python3
"""Gather what the press says about each minister, for a person to write the ficha.

Eighteen of nineteen ministers have no dossier, and the JNE cannot supply one:
a hoja de vida exists only for people who stood for election. The press is the
remaining public account, and Infobae profiles nearly the whole cabinet.

This prints a review packet — headline, summary, link, per cartera — and a
draft ministers.json entry with `profession` and `bio` left blank.

It never writes. It never reads an article body either: the summaries below come
from the feed's own <description>, the same field /ultimitas/ already displays.
The site tells its readers it does not reproduce full articles, and this keeps
that promise. The facts in these notes are yours to use; the sentences are
Infobae's, so write the ficha in your own words and cite the note.

Usage:
  python3 -m tools.scrapers.infobae_profiles
  python3 -m tools.scrapers.infobae_profiles --portfolio m-vivienda
"""
from __future__ import annotations

import argparse
import json
import sys

from tools.scrapers.common.cabinet_rules import CABINET_DIR, PORTFOLIOS_PATH
from tools.scrapers.common.infobae_rules import profile_items
from tools.scrapers.common.jne_rules import _slug
from tools.scrapers.common.press_feeds import fetch_sources

OUTLET = "Infobae"


def roster() -> list:
    """Every cartera with a named holder — appointed or announced.

    Appointments first, announcements only for a cartera the gazette has not
    filled. Reading announcements alone was right while the cabinet was merely
    proclaimed and wrong the moment it was sworn in: a tenure supersedes its
    announcement and the validator then requires the announcement's deletion,
    so an all-appointed cabinet emptied that file and this returned nothing at
    all. The tool reported "0 carteras con material" on every run and looked
    like a quiet news day.
    """
    ministers = {m["slug"]: m for m in json.loads(
        (CABINET_DIR / "ministers.json").read_text(encoding="utf-8"))["ministers"]}
    tenures = json.loads(
        (CABINET_DIR / "tenures.json").read_text(encoding="utf-8"))["tenures"]
    announcements = json.loads(
        (CABINET_DIR / "announcements.json").read_text(encoding="utf-8"))["announcements"]

    rows, seen = [], set()
    for tenure in tenures:
        if tenure.get("end"):
            continue  # a past holder is not who covers the cartera now
        person = ministers.get(tenure.get("person") or "")
        if not person:
            continue
        seen.add(tenure["portfolio"])
        rows.append({
            "portfolio": tenure["portfolio"],
            "person_name": person["name"],
            "has_ficha": bool(person.get("bio")),
        })
    for entry in announcements:
        if entry["portfolio"] in seen:
            continue
        linked = ministers.get(entry.get("person") or "")
        rows.append({
            "portfolio": entry["portfolio"],
            "person_name": (linked or {}).get("name") or entry["person_name"],
            "has_ficha": bool((linked or {}).get("bio")),
        })
    return rows


def portfolio_names() -> dict:
    return {p["id"]: p["short"] for p in json.loads(
        PORTFOLIOS_PATH.read_text(encoding="utf-8"))["portfolios"]}


def draft(person_name: str, url: str) -> str:
    """The ministers.json skeleton, with what only a person can write left blank."""
    return json.dumps({
        "slug": _slug(person_name),
        "name": person_name,
        "profession": "",
        "bio": "",
        "sources": [{"label": OUTLET, "url": url, "kind": "press"}],
        "judicial": [],
    }, ensure_ascii=False, indent=2)


def run(only: str | None) -> int:
    articles, failed = fetch_sources()
    if failed:
        print(f"AVISO: fuentes caídas: {', '.join(failed)}", file=sys.stderr)

    items_by_outlet = [a for a in articles if a.get("source") == OUTLET]
    print(f"{len(articles)} notas en total, {len(items_by_outlet)} de {OUTLET}\n")

    ministers = [m for m in roster() if not only or m["portfolio"] == only]
    found = profile_items(items_by_outlet, ministers)
    names = portfolio_names()

    shown = 0
    for person in ministers:
        pid = person["portfolio"]
        hits = found.get(pid, [])
        if not hits:
            continue
        shown += 1

        mark = " · ya tiene ficha" if person["has_ficha"] else ""
        print(f"{names.get(pid, pid).upper()} — {person['person_name']}{mark}")
        for hit in hits:
            print(f"  {OUTLET} · {hit['published'][:10]}")
            print(f"  «{' '.join(hit['title'].split())}»")
            if hit["summary"]:
                print(f"   {' '.join(hit['summary'].split())[:220]}")
            print(f"   {hit['url']}")
        if not person["has_ficha"]:
            print("\n  borrador para src/data/cabinet/ministers.json:")
            print("  " + draft(person["person_name"], hits[0]["url"]).replace("\n", "\n  "))
        print()

    missing = [m for m in ministers if m["portfolio"] not in found]
    if missing:
        print("Sin nota de perfil en el feed de hoy:")
        for person in missing:
            label = names.get(person["portfolio"], person["portfolio"])
            print(f"  {label:28s} {person['person_name']}")
        print()

    print(f"{shown} cartera(s) con material. Escribe `profession` y `bio` con tus propias "
          f"palabras y cita la nota: los hechos son públicos, las frases son de {OUTLET}. "
          "Este comando no escribe nada.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio", help="limita el informe a una cartera (id del registro)")
    args = parser.parse_args()
    return run(args.portfolio)


if __name__ == "__main__":
    sys.exit(main())
