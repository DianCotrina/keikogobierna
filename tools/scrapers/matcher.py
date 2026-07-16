#!/usr/bin/env python3
"""Match free text against the plan's commitments via the distinctive-phrase index.

The single place matching logic lives; every document-stream source (El Peruano
now, any future gap-driven source) calls it. A commitment matches when the text
contains one of its distinctive phrases. Deterministic, stdlib only.
See workflows/elperuano_scraper.md.
"""
from __future__ import annotations

import json
from pathlib import Path

from watcher_common import phrases_of, significant_tokens

INDEX_PATH = Path(__file__).resolve().parent / "commitment_index.json"
OVERLAY_PATH = Path(__file__).resolve().parent / "commitment_overlay.json"


class Matcher:
    def __init__(self, phrase_to_ids: dict[str, set[str]], temas: dict[str, str], suppress: frozenset):
        self._phrase_to_ids = phrase_to_ids
        self._temas = temas
        self._suppress = suppress

    def match(self, text: str) -> list[str]:
        present = phrases_of(significant_tokens(text, extra_stop=self._suppress))
        ids: set[str] = set()
        for phrase in present:
            ids |= self._phrase_to_ids.get(phrase, set())
        return sorted(ids)

    def tema_slug(self, commitment_id: str) -> str:
        return self._temas.get(commitment_id.split(".")[0], "")


def _muted(cid: str, muted: set[str]) -> bool:
    """A commitment is muted by its own id or by its tema id (the part before '.')."""
    return cid in muted or cid.split(".")[0] in muted


def load_matcher(index_path: Path = INDEX_PATH, overlay_path: Path = OVERLAY_PATH) -> Matcher:
    index = json.loads(Path(index_path).read_text())
    overlay = json.loads(Path(overlay_path).read_text()) if Path(overlay_path).exists() else {}
    suppress = frozenset(overlay.get("suppress_terms", []))
    suppress_phrases = set(overlay.get("suppress_phrases", []))  # generic gov phrases to ignore
    muted = set(overlay.get("mute_commitments", []))

    phrase_to_ids: dict[str, set[str]] = {}
    for cid, entry in index["commitments"].items():
        if _muted(cid, muted):
            continue
        for phrase in entry["phrases"]:
            if phrase in suppress_phrases:
                continue
            phrase_to_ids.setdefault(phrase, set()).add(cid)
    # boost: hand-curated phrases (incl. distinctive single words) run through the
    # same tokenizer as the corpus — the only route by which a unigram can match
    for cid, raw_phrases in overlay.get("boost", {}).items():
        if _muted(cid, muted):
            continue
        for raw in raw_phrases:
            for phrase in phrases_of(significant_tokens(raw, extra_stop=suppress)):
                if phrase not in suppress_phrases:
                    phrase_to_ids.setdefault(phrase, set()).add(cid)
    return Matcher(phrase_to_ids, index.get("temas", {}), suppress)
