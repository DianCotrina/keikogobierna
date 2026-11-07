"""Show a promise in its place in the plan PDF, not as the extracted sentence.

The topic files keep one sentence per commitment. The neighbouring bullets
often say what the promise means (scope, regions, partner programs), and a
norma can fit a neighbour better than the commitment the matcher chose.

Usage:
  python3 -m tools.review.plan_context t3-2.P12 [t3-2.P08 ...] [--chars 1600]
  python3 -m tools.review.plan_context --grep "comando|mixto"   # find the right id in any topic
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "docs" / "Plan-de-Gobierno-Reforzado_V2.pdf"
TOPICS = ROOT / "src" / "data" / "plan" / "topics"


def commitments() -> dict[str, str]:
    found = {}
    for path in sorted(TOPICS.glob("*.json")):
        topic = json.loads(path.read_text())
        for item in [p for g in topic["groups"] for p in g["proposals"]] + topic["first_100_days"]:
            found[item["id"]] = item["text"]
    return found


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def locate(pages: list[str], text: str) -> tuple[int, int] | None:
    # The first words survive PDF line-wrapping best; shorten until one page matches.
    words = flat(text).split()
    for size in (12, 9, 6):
        needle = " ".join(words[:size]).lower()
        for number, page in enumerate(pages, start=1):
            at = flat(page).lower().find(needle)
            if at >= 0:
                return number, at
    return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ids", nargs="*")
    parser.add_argument("--grep", help="regex over every commitment text; lists matching ids")
    parser.add_argument("--chars", type=int, default=1600)
    args = parser.parse_args(argv)
    known = commitments()
    if args.grep:
        pattern = re.compile(args.grep, re.I)
        for cid, sentence in known.items():
            if pattern.search(sentence):
                print(f"{cid}\t{sentence[:200]}")
        if not args.ids:
            return 0
    text = subprocess.run(["pdftotext", "-layout", str(PDF), "-"], capture_output=True, text=True, check=True).stdout
    pages = text.split("\f")
    for cid in args.ids:
        sentence = known.get(cid)
        if not sentence:
            print(f"## {cid}: unknown commitment id\n")
            continue
        hit = locate(pages, sentence)
        if not hit:
            print(f"## {cid}: not found in the PDF text\n{sentence}\n")
            continue
        number, at = hit
        page = flat(pages[number - 1])
        half = args.chars // 2
        print(f"## {cid} (plan p. {number})\n…{page[max(0, at - half):at + half]}…\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
