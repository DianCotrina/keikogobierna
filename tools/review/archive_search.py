"""Search every archived El Peruano norma for a norm's history.

The scraper appends each day's full record set to `normas/<date>.jsonl` on the
`normas-archive` branch (starting 2026-07-14). Searching it answers the credit
questions: when a program was created, by which government, and what changed
it since. It also shows related normas the matcher never surfaced.

Usage:
  git fetch origin normas-archive
  python3 -m tools.review.archive_search "0132-2026-MIDAGRI" "Escuelas Bicentenario"

Each pattern is a case-insensitive regex matched against numero and sumilla.
Absence is only a hint that a norma predates 2026-07-14: some days are missing or
partially captured. Date a norma from its own text.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

BRANCH = "origin/normas-archive"


def records():
    files = subprocess.run(
        ["git", "ls-tree", "--name-only", BRANCH, "normas/"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    for name in files:
        body = subprocess.run(["git", "show", f"{BRANCH}:{name}"], capture_output=True, text=True, check=True).stdout
        for line in body.splitlines():
            if line.strip():
                yield json.loads(line)


def normalize(record: dict) -> tuple[str, str]:
    """ISO date and op id. Early files store `url_pdf` and a compact date; later ones `op` and ISO."""
    legacy = re.search(r"/(\d+-\d+)\.pdf", record.get("url_pdf", ""), re.I)
    op = record.get("op") or (legacy.group(1) if legacy else "?")
    date = record.get("fecha", "")
    if "-" not in date:
        date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    return date, op


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("patterns", nargs="+")
    args = parser.parse_args(argv)
    compiled = [re.compile(p, re.I) for p in args.patterns]
    hits = 0
    for record in records():
        haystack = f"{record.get('numero', '')} {record.get('sumilla', '')}"
        if any(p.search(haystack) for p in compiled):
            hits += 1
            date, op = normalize(record)
            print(f"{date}\t{op}\t{record.get('numero')}\t{record.get('sumilla', '')[:160]}")
    print(f"-- {hits} match(es); archive starts 2026-07-14", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
