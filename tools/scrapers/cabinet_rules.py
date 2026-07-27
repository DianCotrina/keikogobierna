"""Detect cabinet appointments and resignations in El Peruano normas.

Ministers are appointed and relieved by Resolución Suprema, and the gazette
writes those in a fixed grammar:

    sumilla: "Nombran Ministro de Estado en el Despacho del Interior"
    body:    "Artículo 1.- Nombrar al señor NOMBRE APELLIDO como Ministro de
              Estado en el Despacho del Interior."

That regularity is what lets this stay deterministic regex — no model calls,
per the no-AI-in-pipelines invariant.

Pure functions only: no I/O, no GitHub, no network. Callers supply the record
and the norma body. When anything is ambiguous these return None; filing
nothing is always better than inventing a name or a ministry.
"""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PORTFOLIOS_PATH = ROOT / "src" / "data" / "cabinet" / "portfolios.json"

CABINET_TIPO = "RESOLUCIÓN SUPREMA"

# "Ministro/Ministra de Estado" is the phrase that marks a cabinet member.
# Viceministers are appointed constantly and are not cabinet members, so they
# are excluded explicitly rather than left to chance.
_MINISTER = re.compile(r"\bMinistr[oa]\s+de\s+Estado\b", re.I)
_VICE = re.compile(r"\bVice\s?ministr[oa]\b", re.I)
_APPOINT_VERB = re.compile(r"\b(nombran?|nombrar)\b", re.I)
_RESIGN_VERB = re.compile(r"\b(acepta\w*\s+(la\s+)?renuncia|renuncia)\b", re.I)

# Alternations are ordered longest-first throughout: Python's regex takes the
# first matching branch, so "(?:l|la)" against "la señora" would match just "l"
# and leave "a señora" inside the captured name.
_HONORIFIC = r"(?:se[ñn]or(?:a)?|doctor(?:a)?|ingenier[oa])?\s*"

# "Nombrar al señor NOMBRE APELLIDO como Ministro de Estado en el Despacho de X"
_APPOINT_BODY = re.compile(
    r"Nombrar\s+(?:a\s+la|a\s+el|al|a)\s+" + _HONORIFIC +
    r"(?P<person>[^,]{3,90}?)\s+(?:como|en\s+el\s+cargo\s+de)\s+Ministr[oa]\s+de\s+Estado\s+"
    r"en\s+el\s+Despacho\s+(?:de\s+la|del|de)\s+(?P<portfolio>[^.\n]{3,90})",
    re.I)

# "Aceptar la renuncia del señor NOMBRE APELLIDO al cargo de Ministro ... Despacho de X"
_RESIGN_BODY = re.compile(
    r"Aceptar\s+la\s+renuncia\s+(?:de\s+la|del|de)\s+" + _HONORIFIC +
    r"(?P<person>[^,]{3,90}?)\s+al\s+cargo\s+de\s+Ministr[oa]\s+de\s+Estado\s+"
    r"en\s+el\s+Despacho\s+(?:de\s+la|del|de)\s+(?P<portfolio>[^.\n]{3,90})",
    re.I)


def _fold(text: str) -> str:
    """Lowercase and strip accents so portfolio matching survives the gazette's
    inconsistent accenting."""
    stripped = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in stripped if unicodedata.category(c) != "Mn").strip()


def _load_portfolio_lookup() -> dict:
    """Map folded ministry names -> registry id, built from the committed registry
    so the parser can never invent a ministry."""
    data = json.loads(PORTFOLIOS_PATH.read_text(encoding="utf-8"))
    lookup = {}
    for portfolio in data["portfolios"]:
        for name in (portfolio["name"], portfolio["short"], portfolio["slug"].replace("-", " ")):
            key = _fold(name)
            for prefix in ("ministerio de la ", "ministerio de los ", "ministerio del ",
                           "ministerio de ", "ministerio "):
                if key.startswith(prefix):
                    key = key[len(prefix):]
                    break
            lookup[key] = portfolio["id"]
    return lookup


_PORTFOLIOS = _load_portfolio_lookup()


def portfolio_id(name: str):
    """Resolve a gazette ministry name to a registry id, or None if unknown."""
    key = _fold(name)
    if key in _PORTFOLIOS:
        return _PORTFOLIOS[key]
    # The gazette says "Despacho de Economía y Finanzas" where the registry says
    # "Ministerio de Economía y Finanzas"; allow a containment match in either
    # direction, but only when it is unambiguous.
    hits = {pid for known, pid in _PORTFOLIOS.items() if known in key or key in known}
    return hits.pop() if len(hits) == 1 else None


def is_cabinet_norma(record: dict) -> bool:
    """True when a norma looks like a cabinet appointment or resignation."""
    if (record.get("tipo") or "").upper() != CABINET_TIPO:
        return False
    sumilla = record.get("sumilla") or ""
    if _VICE.search(sumilla) or not _MINISTER.search(sumilla):
        return False
    return bool(_APPOINT_VERB.search(sumilla) or _RESIGN_VERB.search(sumilla))


def _iso_date(yyyymmdd: str) -> str:
    raw = (yyyymmdd or "").strip()
    return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}" if len(raw) == 8 and raw.isdigit() else ""


def parse_cabinet_act(record: dict, text: str):
    """Extract a cabinet act from a norma, or None when it cannot be read cleanly.

    Returns {action, person, portfolio, norma, date, url}, where `portfolio` is a
    portfolios.json id and `action` is "nombramiento" or "renuncia".
    """
    if not is_cabinet_norma(record):
        return None

    body = re.sub(r"\s+", " ", text or "")
    if _VICE.search(body):
        return None

    match = _APPOINT_BODY.search(body)
    action = "nombramiento"
    if not match:
        match = _RESIGN_BODY.search(body)
        action = "renuncia"
    if not match:
        return None

    person = " ".join(match.group("person").split()).strip(" .,")
    pid = portfolio_id(match.group("portfolio"))
    if not person or not pid:
        return None

    return {
        "action": action,
        "person": person,
        "portfolio": pid,
        "norma": (record.get("numero") or "").strip(),
        "date": _iso_date(record.get("fecha")),
        "url": (record.get("url_pdf") or "").strip(),
    }
