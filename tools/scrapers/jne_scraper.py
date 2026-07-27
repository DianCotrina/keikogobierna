#!/usr/bin/env python3
"""Draft a minister's dossier from their JNE hoja de vida.

Reads the Declaración Jurada de Hoja de Vida — the candidate's own sworn
statement to the state, published openly by the JNE — and emits a people.json
entry for review.

It never produces publishable data. Declared sentences come out with `stage`
unset, and the cabinet validator refuses to build while any stage is missing,
so a draft cannot reach the site until a person reads the declaration and
decides what each entry actually is. See the module docstring in jne_rules.py
for why that is not automatable.

Only ministers who stood for election have a hoja de vida; ministers appointed
from outside politics have none, and this tool will say so rather than guess.

Two phases, because a name match is not an identity match. Searching only ever
lists candidates with their party; drafting requires an idHojaVida you have
confirmed yourself:

  # 1. who might this be?
  python3 tools/scrapers/jne_scraper.py --cabinet
  python3 tools/scrapers/jne_scraper.py --name "Luis Galarreta"

  # 2. draft the one you verified
  python3 tools/scrapers/jne_scraper.py --id 246699
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jne_client import fetch_hoja_vida, fetch_roster
from jne_rules import draft_person, match_candidates

ROOT = Path(__file__).resolve().parent.parent.parent
CABINET_DIR = ROOT / "src" / "data" / "cabinet"


def cabinet_names() -> list:
    """Everyone currently on the roster: appointed ministers and announced ones."""
    names = []
    people = json.loads((CABINET_DIR / "people.json").read_text(encoding="utf-8"))["people"]
    names += [p["name"] for p in people]
    announcements = json.loads(
        (CABINET_DIR / "announcements.json").read_text(encoding="utf-8"))["announcements"]
    names += [a["person_name"] for a in announcements]
    return sorted(set(names))


def show_matches(name: str, roster: list) -> None:
    """List candidates whose name matches, with the party, so a person can judge.

    A name match is not an identity match. "Carlos Espá" matches "ALFONSO
    CARLOS ESPA Y GARCES-ALVEAR" of PARTIDO SICREO — a different man entirely,
    whose declaration must never end up on a minister's page. Only a person can
    tell those apart, so the tool never drafts from a name; it reports the
    candidates and waits for --id.
    """
    hits = match_candidates(name, roster)
    if not hits:
        print(f"  {name}: sin hoja de vida en el padrón (no fue candidato)")
        return
    print(f"  {name}: {len(hits)} coincidencia(s) — confirma cuál es antes de continuar")
    for hit in hits:
        full = f"{hit['txNom']} {hit['txApePat']} {hit['txApeMat']}".strip()
        print(f"      idHojaVida={hit['idHojaVida']:<8} {full}  ·  {hit['txOrgPol']}")


def draft_for_id(id_hoja_vida: int, roster: list) -> dict | None:
    candidate = next((c for c in roster if c.get("idHojaVida") == id_hoja_vida), None)
    if not candidate:
        print(f"  idHojaVida={id_hoja_vida}: no está en el padrón EG2026")
        return None

    draft = draft_person(candidate, fetch_hoja_vida(id_hoja_vida))
    pending = sum(1 for e in draft["judicial"] if e["stage"] is None)
    print(f"  {draft['name']} ({candidate['txOrgPol']}) — "
          f"{len(draft['judicial'])} sentencia(s) declarada(s), {pending} por clasificar")
    return draft


def run(names: list, ids: list) -> int:
    print("Descargando el padrón de candidatos (EG2026)…")
    roster = fetch_roster()
    print(f"{len(roster)} candidatos.\n")

    if names:
        print("Coincidencias por nombre (ninguna se usa hasta que la confirmes):")
        for name in names:
            show_matches(name, roster)
        print("\nVuelve a ejecutar con --id <idHojaVida> para las que correspondan.")
        print("Verifica el partido: un homónimo de otra agrupación NO es la misma persona.")

    if not ids:
        return 0

    drafts = [d for d in (draft_for_id(i, roster) for i in ids) if d]
    if not drafts:
        print("\nNada que proponer.")
        return 0

    print("\nBorrador para src/data/cabinet/people.json "
          "(REVISAR antes de fusionar):\n")
    print(json.dumps({"people": drafts}, ensure_ascii=False, indent=2))

    pending = sum(1 for d in drafts for e in d["judicial"] if e["stage"] is None)
    if pending:
        print(f"\n⚠  {pending} entrada(s) judicial(es) sin etapa. Lee el fallo, la modalidad "
              "y el comentario de cada declaración y asigna `stage` a mano; la validación "
              "falla mientras quede alguna sin clasificar. Un fallo puede decir «ABSUELTO» "
              "aunque la modalidad diga «EFECTIVA»: manda el fallo, no la modalidad.")
    print("Falta también escribir `bio` a mano: la declaración no trae prosa.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", action="append", help="nombre a buscar (repetible)")
    parser.add_argument("--id", action="append", type=int, dest="ids",
                        help="idHojaVida ya verificado, del que sí se genera borrador (repetible)")
    parser.add_argument("--cabinet", action="store_true",
                        help="busca a todas las personas del gabinete (nombradas y anunciadas)")
    args = parser.parse_args()

    names = list(args.name or [])
    if args.cabinet:
        names += cabinet_names()
    if not names and not args.ids:
        print("Indica --name, --cabinet o --id", file=sys.stderr)
        return 2
    return run(sorted(set(names)), list(args.ids or []))


if __name__ == "__main__":
    sys.exit(main())
