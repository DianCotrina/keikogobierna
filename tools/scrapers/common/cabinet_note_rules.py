"""Read a whole cabinet from El Peruano's news note.

The gazette lags. A cabinet is sworn in hours before the Resoluciones Supremas
that appoint it reach Normas Legales, and in that window the only complete,
structured account is El Peruano's own news desk:

    Presidente del Consejo de Ministros: Luis Galarreta Velarde
    Ministro de Economía y Finanzas: Elmer Cuba Bustinza
    Ministro de Relaciones Exteriores: Carlos Espá y Garcés-Alvear
    ...

One note carries all nineteen carteras with full names, which is a far better
source than nineteen separate press headlines — and it comes from Editora Perú,
the state publisher, rather than a commercial outlet.

It is still not the norma. Everything read here is provisional and belongs in
announcements.json until the Resolución Suprema publishes, exactly like a press
announcement. Discovery, never certification.

Pure functions: no I/O, no network. Transport lives in cabinet_scraper.py.
"""
from __future__ import annotations

import html
import re

from .cabinet_rules import portfolio_id

# The note gives one "<role>: <person>" per block, so a line is the natural
# right-hand boundary for a name. Reading the whole page as one flat string
# instead lets the last name run on into the prose that follows it — that is
# how "Juan Carlos Requejo Alemán" first came out as "…Alemán Lea", swallowing
# the "Lea también en El Peruano" that comes next. Never guess a name's length;
# let the markup end it.
_BLOCK = re.compile(r"(?i)</?(?:p|div|br|li|h[1-6]|tr|section|article|figcaption)[^>]*>")

_ENTRY = re.compile(
    r"^(?P<role>"
    r"Presidente\s+del\s+Consejo\s+de\s+Ministros"
    r"|Ministr[oa]\s+(?:de\s+la|del|de)\s+.{3,70}?"
    r")\s*:\s*(?P<name>\S.*)$",
    re.I,
)

# Guards against a line that merely mentions a ministry in passing.
_NAME_SHAPE = re.compile(
    r"^[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.'-]*"
    r"(?:\s+(?:y|de|del|la)?\s*[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.'-]*){1,5}$",
)


def _lines(markup: str) -> list:
    """The page as text, one line per block-level element."""
    without_code = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", markup or "")
    blocks = _BLOCK.sub("\n", without_code)
    text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", blocks))
    return [" ".join(line.split()) for line in text.split("\n")]


def parse_cabinet_note(markup: str) -> list:
    """Every "<role>: <person>" the note states, resolved to registry ids.

    Returns [{portfolio, person_name, role}] in the order the note lists them.
    A role that does not resolve to a known cartera is dropped rather than
    guessed at — the registry is the authority on what a cartera is.
    """
    entries, seen = [], set()

    for line in _lines(markup):
        match = _ENTRY.match(line)
        if not match:
            continue

        name = match.group("name").strip(" .;")
        if not _NAME_SHAPE.match(name):
            continue

        pid = portfolio_id(" ".join(match.group("role").split()))
        if not pid or pid in seen:
            continue
        seen.add(pid)
        entries.append({
            "portfolio": pid,
            "person_name": name,
            "role": " ".join(match.group("role").split()),
        })

    return entries
