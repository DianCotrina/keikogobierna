#!/usr/bin/env python3
"""Sweep the normas archive for each first-100-days action and report what,
if anything, the gazette has published about it.

This asks the opposite question from the daily scraper. The scraper indexes the
whole plan and asks of each norma "which commitment does this resemble?" — good
for catching evidence as it appears, useless for answering "has promise X moved
at all?", because a promise nobody legislated on simply never comes up.

Here each of the plan's first-100-days actions gets its own hand-authored probe
(see hundred_days_probes.json) and the entire archive since the inauguration is
swept for it. A promise with zero hits has left no trace in El Peruano at all.

    python3 tools/plan/audit_100_days.py
    python3 tools/plan/audit_100_days.py --json > audit.json
    python3 tools/plan/audit_100_days.py --archive /path/to/normas

Read the report with the coverage caveat in mind, and see `gazette_can_verify`:
most of these promises are campaigns, operativos and deployments that need no
published norm to happen, so silence about them is not evidence of inaction.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PLAN_TOPICS = ROOT / "src" / "data" / "plan" / "topics"
PROBES_PATH = Path(__file__).resolve().parent / "hundred_days_probes.json"

# The government took office on 2026-07-28; normas published before that are the
# previous administration's and can never evidence this plan.
INAUGURATION = date(2026, 7, 28)
WINDOW_DAYS = 100
ARCHIVE_REF = "origin/normas-archive"

# A promise whose own verb *is* a publication or a creation cannot happen
# without a norm, so silence about it in the gazette is real signal. A campaign
# launch, an operativo or a deployment can happen without ever being published,
# and for those an empty result means nothing at all. Heuristic on the promise's
# leading verb — a floor on what is checkable here, not a measurement.
_GAZETTE_VERB_RE = re.compile(
    r"^(publicacion|creacion|aprobacion|emision|establecimiento|suscripcion|presentacion)\b"
    r"|\bdecretos? de urgencia\b|\breglamento\b|\bobligatoriedad\b"
)


def fold(text: str) -> str:
    """Lowercase and strip accents, so a probe matches however it is written."""
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def load_actions() -> list[dict]:
    """Every first-100-days action in the plan, with its topic."""
    actions = []
    for path in sorted(PLAN_TOPICS.glob("*.json")):
        topic = json.loads(path.read_text(encoding="utf-8"))
        for action in topic.get("first_100_days", []):
            actions.append({
                "id": action["id"],
                "topic": topic.get("name", ""),
                "topic_slug": topic.get("slug", ""),
                "text": action["text"],
                "gazette_can_verify": bool(_GAZETTE_VERB_RE.search(fold(action["text"]))),
            })
    return actions


def load_probes() -> dict:
    return json.loads(PROBES_PATH.read_text(encoding="utf-8"))["probes"]


def check_probe_coverage(actions: list[dict], probes: dict) -> list[str]:
    """Every action needs a probe and every probe an action. A regenerated plan
    that adds an action must not silently lose coverage for it."""
    ids = {a["id"] for a in actions}
    problems = [f"no probe for {cid}" for cid in sorted(ids - set(probes))]
    problems += [f"probe for unknown action {cid}" for cid in sorted(set(probes) - ids)]
    for cid, pattern in sorted(probes.items()):
        try:
            re.compile(pattern)
        except re.error as e:
            problems.append(f"probe for {cid} is not a valid regex: {e}")
    return problems


def materialize_archive(ref: str, dest: Path) -> Path:
    """Unpack the normas archive branch, which the site never checks out."""
    proc = subprocess.run(["git", "-C", str(ROOT), "archive", ref, "normas"],
                          capture_output=True)
    if proc.returncode != 0:
        sys.exit(f"cannot read {ref}: {proc.stderr.decode().strip()}\n"
                 f"try: git fetch origin normas-archive")
    subprocess.run(["tar", "-x", "-C", str(dest)], input=proc.stdout, check=True)
    return dest / "normas"


def load_normas(archive: Path, since: date) -> list[dict]:
    records = []
    for path in sorted(archive.glob("*.jsonl")):
        if path.stem < since.isoformat():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            record["_haystack"] = fold(
                f'{record.get("tipo", "")} {record.get("numero", "")} {record.get("sumilla", "")}'
            )
            records.append(record)
    return records


def sweep(actions: list[dict], probes: dict, normas: list[dict]) -> list[dict]:
    results = []
    for action in actions:
        rx = re.compile(probes[action["id"]])
        hits = [
            {k: n[k] for k in ("fecha", "tipo", "numero", "sector", "sumilla", "url")}
            for n in normas if rx.search(n["_haystack"])
        ]
        results.append({**action, "probe": probes[action["id"]], "hits": hits})
    return results


def report(results: list[dict], normas: list[dict], today: date, since: date) -> None:
    elapsed = (today - since).days
    deadline = since + timedelta(days=WINDOW_DAYS)
    silent = [r for r in results if not r["hits"]]
    checkable = [r for r in results if r["gazette_can_verify"]]
    checkable_silent = [r for r in checkable if not r["hits"]]

    print(f"Primeros 100 días — {elapsed} días transcurridos de {WINDOW_DAYS} "
          f"(desde {since}, vence {deadline})")
    print(f"{len(normas)} normas publicadas en la ventana, "
          f"{len(results)} acciones con sonda\n")
    print(f"  {len(silent)} de {len(results)} acciones sin rastro alguno en El Peruano")
    print(f"  {len(checkable)} de {len(results)} acciones prometen un acto que "
          f"no puede existir sin norma publicada")
    print(f"  {len(checkable_silent)} de esas {len(checkable)} siguen sin norma "
          f"— ahí el silencio sí es señal\n")

    with_hits = [r for r in results if r["hits"]]
    if not with_hits:
        print("Ninguna acción tiene coincidencias. Nada que revisar.")
    for r in with_hits:
        flag = "norma esperada" if r["gazette_can_verify"] else "puede ocurrir sin norma"
        print(f"── {r['id']} · {r['topic']} · {flag} ({len(r['hits'])} coincidencia(s))")
        print(f"   {r['text'][:150]}")
        for hit in r["hits"][:6]:
            print(f"     {hit['fecha']} [{hit['sector'][:26]:26}] {hit['sumilla'][:88]}")
        if len(r["hits"]) > 6:
            print(f"     … {len(r['hits']) - 6} más")
        print()

    print("Cada coincidencia es solo un punto de partida: léela entera antes de "
          "concluir nada.\nUna acción sin coincidencias marcada «puede ocurrir sin "
          "norma» no prueba inacción\n— el diario oficial simplemente no la ve.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--archive", type=Path,
                        help="directory of <date>.jsonl files (default: the "
                             f"{ARCHIVE_REF} branch)")
    parser.add_argument("--ref", default=ARCHIVE_REF, help="git ref holding the archive")
    parser.add_argument("--since", type=date.fromisoformat, default=INAUGURATION,
                        help="first day to sweep (default: the inauguration)")
    parser.add_argument("--today", type=date.fromisoformat, default=date.today(),
                        help="treat this as the current date")
    parser.add_argument("--json", action="store_true", help="emit the sweep as JSON")
    parser.add_argument("--check-probes", action="store_true",
                        help="only verify every action has a valid probe, then exit")
    args = parser.parse_args()

    actions = load_actions()
    probes = load_probes()

    problems = check_probe_coverage(actions, probes)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        sys.exit(1)
    if args.check_probes:
        print(f"OK: {len(actions)} first-100-days actions, all probed")
        return

    with tempfile.TemporaryDirectory() as tmp:
        archive = args.archive or materialize_archive(args.ref, Path(tmp))
        normas = load_normas(archive, args.since)

    results = sweep(actions, probes, normas)
    if args.json:
        json.dump({"since": args.since.isoformat(), "today": args.today.isoformat(),
                   "normas": len(normas), "actions": results}, sys.stdout,
                  ensure_ascii=False, indent=2)
    else:
        report(results, normas, args.today, args.since)


if __name__ == "__main__":
    main()
