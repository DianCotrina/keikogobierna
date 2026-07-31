"""Detect cabinet appointments and resignations in El Peruano normas.

Ministers are appointed and relieved by Resolución Suprema. The gazette's
grammar is fixed, which is what keeps this deterministic regex — no model
calls, per the no-AI-in-pipelines invariant. Verified against the 2026-03-18
edition, a full-cabinet reshuffle carrying 25 cabinet acts:

    sumilla  "Nombran Ministro del Interior"
             "Nombran Presidente del Consejo de Ministros"
             "Aceptan renuncia de Ministra de Cultura"
    body     "Nombrar Ministro de Estado en el Despacho del Interior,
              al señor José Mercedes Zapata Morante."
             "Nombrar Presidente del Consejo de Ministros,
              al señor Luis Enrique Arroyo Sánchez."
             "Aceptar la renuncia que, al cargo de Ministro de Estado en el
              Despacho del Interior, formula el señor Hugo Alberto Begazo de
              Bedoya, dándosele las gracias por los servicios prestados."

Three details that are easy to get wrong, each of which broke an earlier
version of this file:
  - The sumilla names the ministry directly ("Ministro del Interior"), never
    "Ministro de Estado". Only the body uses the longer formula.
  - The head of cabinet is "Presidente del Consejo de Ministros" and is never
    called a minister in the sumilla at all.
  - The person's name comes *after* the portfolio, and is Title Case.

`tipoDispositivo` arrives both accented and unaccented depending on the record's
age, so the type check folds accents too.

Pure functions only: no I/O, no GitHub, no network. When anything is ambiguous
these return None; filing nothing is always better than inventing a name.
"""
import json
import re
from pathlib import Path

from .watcher_common import fold as _fold

ROOT = Path(__file__).resolve().parent.parent.parent.parent
CABINET_DIR = ROOT / "src" / "data" / "cabinet"
PORTFOLIOS_PATH = CABINET_DIR / "portfolios.json"

PCM_ID = "pcm"

# Viceministers are appointed constantly and are not cabinet members.
_VICE = re.compile(r"\bvice\s?ministr[oa]\b", re.I)
# Public: press_rules matches the same office and must not keep its own copy.
PCM_HEAD = re.compile(r"presidente\s+del\s+consejo\s+de\s+ministros", re.I)

# Sumilla forms. Anchored at the start so "Autorizan viaje de Ministro de
# Relaciones Exteriores" cannot be mistaken for an appointment.
_SUMILLA_APPOINT = re.compile(r"^\s*nombran\s+(?P<who>.+)$", re.I)
_SUMILLA_RESIGN = re.compile(r"^\s*aceptan\s+(?:la\s+)?renuncia\s+(?:de|del)\s+(?P<who>.+)$", re.I)
_IS_MINISTER = re.compile(r"^ministr[oa]\b", re.I)

_HONORIFIC = r"(?:se[ñn]or(?:a)?|doctor(?:a)?|ingenier[oa])?\s*"

# The gazette writes "al señor", contracted. Alternations are ordered
# longest-first throughout: Python takes the first matching branch, so a bare
# "a" listed early would strip the contraction and swallow "l" into the name.
_ADDRESSEE = r"(?:a\s+la|a\s+el|al|a)\s+" + _HONORIFIC

# "Nombrar Ministro de Estado en el Despacho del Interior, al señor NOMBRE."
# The portfolio capture is lazy and may contain commas -- "Vivienda,
# Construcción y Saneamiento" is one ministry -- so it runs to the last comma
# before the addressee rather than the first comma it meets.
_BODY_APPOINT_SECTORAL = re.compile(
    r"Nombrar\s+Ministr[oa]\s+de\s+Estado\s+en\s+el\s+Despacho\s+(?:de\s+la|del|de)\s+"
    r"(?P<portfolio>[^.;]{3,90}?)\s*,\s*" + _ADDRESSEE +
    r"(?P<person>[^.,;]{3,90})",
    re.I)

# "Nombrar Presidente del Consejo de Ministros, al señor NOMBRE."
_BODY_APPOINT_PCM = re.compile(
    r"Nombrar\s+Presidente\s+del\s+Consejo\s+de\s+Ministros\s*,\s*" + _ADDRESSEE +
    r"(?P<person>[^.,;]{3,90})",
    re.I)

# "Aceptar la renuncia que, al cargo de Ministro ... del Interior, formula el señor NOMBRE,"
# The comma before "formula" is inconsistent in the gazette -- present for
# Interior, absent for Cultura in the very same edition -- so it is optional.
# Same lazy portfolio capture as above, for ministries whose names carry commas.
_BODY_RESIGN = re.compile(
    r"Aceptar\s+la\s+renuncia\s+.{0,120}?al\s+cargo\s+de\s+"
    r"(?:Ministr[oa]\s+de\s+Estado\s+en\s+el\s+Despacho\s+(?:de\s+la|del|de)\s+(?P<portfolio>[^.;]{3,90}?)"
    r"|(?P<pcm>Presidente\s+del\s+Consejo\s+de\s+Ministros))"
    r"\s*,?\s*formula\s+(?:la|el)?\s*" + _HONORIFIC + r"(?P<person>[^.,;]{3,90})",
    re.I)


def _strip_article(key: str) -> str:
    for prefix in ("ministerio de la ", "ministerio de los ", "ministerio del ",
                   "ministerio de ", "ministerio ", "de la ", "del ", "de "):
        if key.startswith(prefix):
            return key[len(prefix):]
    return key


def _load_portfolio_lookup() -> dict:
    """Folded ministry name -> registry id, built from the committed registry so
    the parser can never invent a cartera.

    `aliases` carries what the press actually prints — "MTC", "Minem",
    "canciller" — none of which appears in any ministry's own name. Keeping them
    in the registry rather than in Python means the data stays the single
    authority on what a cartera is called.
    """
    data = json.loads(PORTFOLIOS_PATH.read_text(encoding="utf-8"))
    lookup = {}
    for portfolio in data["portfolios"]:
        names = [portfolio["name"], portfolio["short"], portfolio["slug"].replace("-", " ")]
        names += portfolio.get("aliases", [])
        for name in names:
            lookup[_strip_article(_fold(name))] = portfolio["id"]
    return lookup


_PORTFOLIOS = _load_portfolio_lookup()

# The registry's own ids, so callers do not re-read portfolios.json to get them.
PORTFOLIO_IDS = frozenset(_PORTFOLIOS.values())


def roster_names() -> list:
    """Everyone the site already tracks: appointed ministers and announced ones.

    Read fresh on each call rather than cached — the callers are one-shot CLI
    runs, and a stale roster would silently narrow what they look for.
    """
    def read(filename: str, key: str, field: str) -> list:
        data = json.loads((CABINET_DIR / filename).read_text(encoding="utf-8"))
        return [row[field] for row in data[key]]

    return sorted(set(read("people.json", "people", "name")
                      + read("announcements.json", "announcements", "person_name")))


def portfolio_id(name: str):
    """Resolve a gazette ministry name to a registry id, or None if unknown."""
    if not name:
        return None
    if PCM_HEAD.search(name):
        return PCM_ID
    key = _strip_article(_fold(name))
    if key in _PORTFOLIOS:
        return _PORTFOLIOS[key]
    # "Desarrollo Agrario y Riego" vs "Ministerio de Desarrollo Agrario y Riego":
    # allow containment either way, but only when it is unambiguous.
    hits = {pid for known, pid in _PORTFOLIOS.items() if known and (known in key or key in known)}
    return hits.pop() if len(hits) == 1 else None


def _is_supreme(tipo: str) -> bool:
    # Records carry both "RESOLUCION SUPREMA" and "RESOLUCIÓN SUPREMA".
    return _fold(tipo) == "resolucion suprema"


def _cabinet_office(sumilla: str):
    """The office named by a cabinet sumilla, or None if it is not one."""
    text = (sumilla or "").strip()
    if _VICE.search(text):
        return None
    for pattern in (_SUMILLA_APPOINT, _SUMILLA_RESIGN):
        match = pattern.match(text)
        if match:
            who = match.group("who").strip()
            if PCM_HEAD.match(who) or _IS_MINISTER.match(who):
                return who
    return None


def is_cabinet_norma(record: dict) -> bool:
    """True when a norma is a ministerial appointment or resignation."""
    if not _is_supreme(record.get("tipo") or ""):
        return False
    return _cabinet_office(record.get("sumilla") or "") is not None


def _iso_date(value: str) -> str:
    """Accept either gazette date shape.

    The retired single-fetch route gave `20260318`; the search-page reader gives
    `2026-03-18` already. Records captured under the old transport survive in
    normas-archive, so both must keep working — and a shape this function does
    not recognise must return "" rather than something plausible-but-wrong.
    """
    raw = (value or "").strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
    if len(raw) == 10 and raw[4] == raw[7] == "-" and raw.replace("-", "").isdigit():
        return raw
    return ""


def _clean(name: str) -> str:
    return " ".join((name or "").split()).strip(" .,;")


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

    # Flat rather than nested: the gazette keeps producing new phrasings, and
    # each one used to cost another level of indentation.
    if (match := _BODY_APPOINT_SECTORAL.search(body)):
        action, person = "nombramiento", match.group("person")
        pid = portfolio_id(match.group("portfolio"))
    elif (match := _BODY_APPOINT_PCM.search(body)):
        action, person, pid = "nombramiento", match.group("person"), PCM_ID
    elif (match := _BODY_RESIGN.search(body)):
        action, person = "renuncia", match.group("person")
        pid = PCM_ID if match.group("pcm") else portfolio_id(match.group("portfolio"))
    else:
        return None

    person = _clean(person)
    if not action or not person or not pid:
        return None

    return {
        "action": action,
        "person": person,
        "portfolio": pid,
        "norma": (record.get("numero") or "").strip(),
        "date": _iso_date(record.get("fecha")),
        # `url` is the search-page reader's field; `url_pdf` the retired one's.
        "url": (record.get("url") or record.get("url_pdf") or "").strip(),
    }
