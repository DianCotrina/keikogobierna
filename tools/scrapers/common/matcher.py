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

from .watcher_common import bigrams_of, phrases_of, significant_tokens

INDEX_PATH = Path(__file__).resolve().parent.parent / "commitment_index.json"
OVERLAY_PATH = Path(__file__).resolve().parent.parent / "commitment_overlay.json"


class Matcher:
    def __init__(self, phrase_to_ids: dict[str, set[str]], temas: dict[str, str], suppress: frozenset):
        self._phrase_to_ids = phrase_to_ids
        self._temas = temas
        self._suppress = suppress

    def match(self, text: str) -> list[str]:
        present = phrases_of(significant_tokens(text, extra_stop=self._suppress))
        ids: set[str] = set()
        for phrase in present & self._phrase_to_ids.keys():
            ids |= self._phrase_to_ids[phrase]
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
    # boost: hand-curated phrases run through the same tokenizer as the corpus,
    # so what lands in the index is what a norma can actually produce.
    #
    # A boost is authored as the phrase it *means*, and only that phrase belongs
    # in the index. Expanding it with phrases_of() also injected every unigram:
    # boosting "ejecutor compras" for Compras MyPerú (t2-1.P22) put a bare
    # "compras" in the index, and PERÚ COMPRAS publishes every resolution under a
    # number containing that word — so the agency's entire output matched the
    # commitment forever (issues #316, #317). "nucleo" and "ejecutor" leaked the
    # same way, the latter catching every Ejecutor Coactivo designation.
    #
    # A one-token boost is a deliberate unigram — "c5i" is the reason this layer
    # accepts single words at all. Anything longer contributes only its adjacent
    # bigrams, which is exactly what phrases_of() derives from a norma, so the
    # authored phrase still matches while its parts no longer do.
    for cid, raw_phrases in overlay.get("boost", {}).items():
        if _muted(cid, muted):
            continue
        for raw in raw_phrases:
            tokens = significant_tokens(raw, extra_stop=suppress)
            if not tokens:
                continue
            phrases = {tokens[0]} if len(tokens) == 1 else bigrams_of(tokens)
            for phrase in phrases:
                if phrase not in suppress_phrases:
                    phrase_to_ids.setdefault(phrase, set()).add(cid)
    return Matcher(phrase_to_ids, index.get("temas", {}), suppress)
