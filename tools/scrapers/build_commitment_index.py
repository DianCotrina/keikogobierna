#!/usr/bin/env python3
"""Build the distinctive-phrase index the matcher uses, from the plan's commitments.

Reads src/data/plan (proposals + first_100_days + goals-2031), keeps each
commitment's phrases (unigrams/adjacent-bigrams) that are rare across all
commitments, and writes tools/scrapers/commitment_index.json. Regenerate when
the plan changes; CI --check guards against drift. Stdlib only.

Usage:
  python3 tools/scrapers/build_commitment_index.py            # regenerate the file
  python3 tools/scrapers/build_commitment_index.py --check    # exit 1 if stale
  python3 tools/scrapers/build_commitment_index.py --report   # list zero-phrase commitments
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from watcher_common import bigrams_of, significant_tokens

ROOT = Path(__file__).resolve().parent.parent.parent
PLAN = ROOT / "src" / "data" / "plan"
INDEX_PATH = Path(__file__).resolve().parent / "commitment_index.json"
# Phrases are distinctive BIGRAMS only. Single words are too ambiguous against
# ~600 daily normas even when rare in the plan ("fiscal", "horario" are plan-rare
# but norma-common), so unigram matching is left to hand-curated overlay boosts.
DF_MAX_BIGRAM = 12


def load_plan() -> tuple[dict[str, str], dict[str, str]]:
    """One pass over the plan → (commitments id→text, temas id→slug).

    Commitments span proposals, first-100-days actions and goals; the tema of a
    commitment is derivable from its id prefix, so only the id→text map is kept.
    """
    commitments: dict[str, str] = {}
    temas: dict[str, str] = {}
    for path in sorted((PLAN / "topics").glob("*.json")):
        topic = json.loads(path.read_text())
        temas[topic["id"]] = topic["slug"]
        for group in topic.get("groups", []):
            for prop in group.get("proposals", []):
                commitments[prop["id"]] = prop["text"]
        for action in topic.get("first_100_days", []):
            commitments[action["id"]] = action["text"]
    goals = json.loads((PLAN / "goals" / "goals-2031.json").read_text())
    for goal in goals["goals"]:
        commitments[goal["id"]] = goal["text"]
    return commitments, temas


def build_index(commitments: dict[str, str], temas: dict[str, str]) -> dict:
    per = {cid: bigrams_of(significant_tokens(text)) for cid, text in commitments.items()}
    df: Counter = Counter()
    for bis in per.values():
        df.update(bis)  # document frequency: commitments containing each bigram

    out_commitments: dict[str, dict] = {}
    for cid, bis in per.items():
        out_commitments[cid] = {"phrases": sorted(bg for bg in bis if df[bg] <= DF_MAX_BIGRAM)}

    return {
        "generated": date.today().isoformat(),
        "params": {"df_max_bigram": DF_MAX_BIGRAM},
        "temas": dict(sorted(temas.items())),
        "commitments": dict(sorted(out_commitments.items())),
    }


def _dump(index: dict) -> str:
    return json.dumps(index, ensure_ascii=False, indent=1) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed index is stale")
    ap.add_argument("--report", action="store_true", help="list commitments with zero phrases")
    args = ap.parse_args()

    index = build_index(*load_plan())

    if args.report:
        empty = [c for c, v in index["commitments"].items() if not v["phrases"]]
        print(f"{len(empty)} of {len(index['commitments'])} commitments have zero phrases:")
        for c in empty:
            print(" ", c)
        return 0

    if args.check:
        committed = json.loads(INDEX_PATH.read_text()) if INDEX_PATH.exists() else {}
        a = {k: v for k, v in committed.items() if k != "generated"}
        b = {k: v for k, v in index.items() if k != "generated"}
        if a != b:
            print("ERROR: commitment_index.json is stale; run build_commitment_index.py", file=sys.stderr)
            return 1
        print("commitment_index.json is in sync.")
        return 0

    INDEX_PATH.write_text(_dump(index), encoding="utf-8")
    print(f"Wrote {INDEX_PATH.name}: {len(index['commitments'])} commitments.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
