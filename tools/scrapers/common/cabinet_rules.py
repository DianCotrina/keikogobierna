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


def _load_portfolio_registry() -> tuple:
    """(folded ministry name -> registry id, id -> short display name), built
    from the committed registry so the parser can never invent a cartera.

    `aliases` carries what the press actually prints — "MTC", "Minem",
    "canciller" — none of which appears in any ministry's own name. Keeping them
    in the registry rather than in Python means the data stays the single
    authority on what a cartera is called.
    """
    data = json.loads(PORTFOLIOS_PATH.read_text(encoding="utf-8"))
    lookup, short = {}, {}
    for portfolio in data["portfolios"]:
        short[portfolio["id"]] = portfolio["short"]
        names = [portfolio["name"], portfolio["short"], portfolio["slug"].replace("-", " ")]
        names += portfolio.get("aliases", [])
        for name in names:
            lookup[_strip_article(_fold(name))] = portfolio["id"]
    return lookup, short


_PORTFOLIOS, PORTFOLIO_SHORT = _load_portfolio_registry()

# The registry's own ids, so callers do not re-read portfolios.json to get them.
PORTFOLIO_IDS = frozenset(_PORTFOLIOS.values())


def read_cabinet(filename: str, key: str) -> list:
    """Rows of one cabinet registry file (ministers/tenures/announcements).

    The single reader of src/data/cabinet/*.json, so a registry-shape change
    lands in one place. Read fresh on each call rather than cached — the
    callers are one-shot CLI runs, and a stale registry would silently narrow
    what they see.
    """
    return json.loads((CABINET_DIR / filename).read_text(encoding="utf-8"))[key]


def roster_names() -> list:
    """Everyone the site already tracks: appointed ministers and announced ones."""
    return sorted({m["name"] for m in read_cabinet("ministers.json", "ministers")}
                  | {a["person_name"] for a in read_cabinet("announcements.json", "announcements")})


def roster() -> list:
    """Every cartera with a named holder — appointed or announced.

    Appointments first, announcements only for a cartera the gazette has not
    filled. Reading announcements alone was right while the cabinet was merely
    proclaimed and wrong the moment it was sworn in: a tenure supersedes its
    announcement and the validator then requires the announcement's deletion,
    so an all-appointed cabinet emptied that file and the profile reader
    returned nothing at all — "0 carteras con material" on every run, looking
    like a quiet news day.
    """
    ministers = {m["slug"]: m for m in read_cabinet("ministers.json", "ministers")}

    rows, seen = [], set()
    for tenure in read_cabinet("tenures.json", "tenures"):
        if tenure.get("end"):
            continue  # a past holder is not who covers the cartera now
        person = ministers.get(tenure.get("person") or "")
        if not person:
            continue
        seen.add(tenure["portfolio"])
        rows.append({
            "portfolio": tenure["portfolio"],
            "person_name": person["name"],
            "slug": person["slug"],
            "has_ficha": bool(person.get("bio")),
        })
    for entry in read_cabinet("announcements.json", "announcements"):
        if entry["portfolio"] in seen:
            continue
        linked = ministers.get(entry.get("person") or "")
        rows.append({
            "portfolio": entry["portfolio"],
            "person_name": (linked or {}).get("name") or entry["person_name"],
            "slug": (linked or {}).get("slug"),
            "has_ficha": bool((linked or {}).get("bio")),
        })
    return rows


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


def resolve_portfolio_prefix(phrase: str):
    """Longest prefix of a running phrase that resolves to a registry id.

    Press text seldom stops at the ministry — "Economía y Finanzas de su primer
    gabinete" — so rather than maintain a stoplist of trailing clauses, try the
    longest prefix first and shorten until the registry resolves one. An
    ambiguous prefix ("Desarrollo", which matches two carteras) resolves to
    nothing because portfolio_id() requires a unique hit. One helper because
    two rules modules each grew a copy of this loop and their strip charsets
    had already drifted apart.
    """
    words = (phrase or "").split()
    for length in range(len(words), 0, -1):
        resolved = portfolio_id(" ".join(words[:length]).strip(" ,.;:"))
        if resolved:
            return resolved
    return None


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


def clean_name(name: str) -> str:
    """Collapse whitespace and strip the punctuation a capture drags along."""
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

    person = clean_name(person)
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


def slugify(name: str) -> str:
    """Person name -> ministers.json slug."""
    return re.sub(r"[^a-z0-9]+", "-", _fold(name)).strip("-")


def _same_person(gazette: str, announced: str) -> bool:
    """Do a gazette name and a press-reported one denote the same person?

    The press drops middle names and gets them wrong -- it printed "Mara
    Seminario Marón" for María Magdalena, and "Roger" for Rogers Martín -- so
    equality is useless here. Surnames are what survives: Peruvian names carry
    two, and the gazette prints the full legal name, so the announced name's
    last two tokens must both appear in it.
    """
    gazette_tokens = set(_fold(gazette).split())
    announced_tokens = _fold(announced).split()
    if len(announced_tokens) < 2:
        return False
    return all(token in gazette_tokens for token in announced_tokens[-2:])


def reconcile(acts: list, announcements: list, ministers: list) -> dict:
    """Match gazette appointments to the announced roster.

    Returns the ministers.json and tenures.json entries the gazette supports,
    plus every disagreement a person needs to look at. Nothing here writes: the
    caller prints it and a human merges, the same gate the norma -> tracking
    path uses.

    A minister entry carries only what the gazette actually states -- slug, name
    and the norma as its source. `profession` and `bio` stay empty because the
    gazette says nothing about either, and a blank field is honest where an
    invented one is not.
    """
    by_slug = {m.get("slug") for m in ministers}
    announced_by_portfolio = {a.get("portfolio"): a for a in announcements}

    new_ministers, tenures, conflicts = [], [], []
    seen: set = set()

    for act in acts:
        if act.get("action") != "nombramiento":
            continue
        portfolio, name = act.get("portfolio"), act.get("person")
        if not portfolio or not name:
            continue
        slug = slugify(name)
        if slug in seen:
            conflicts.append({"kind": "duplicado", "portfolio": portfolio, "gazette": name,
                              "detail": f"'{slug}' aparece dos veces en el barrido"})
            continue
        seen.add(slug)

        announced = announced_by_portfolio.get(portfolio)
        if announced is None:
            conflicts.append({"kind": "sin-anuncio", "portfolio": portfolio, "gazette": name,
                              "detail": "la norma nombra una cartera que nadie anunció"})
        elif not _same_person(name, announced.get("person_name", "")):
            conflicts.append({"kind": "nombre-distinto", "portfolio": portfolio, "gazette": name,
                              "announced": announced.get("person_name", ""),
                              "detail": "la prensa y la norma no coinciden en la persona"})

        if slug not in by_slug:
            new_ministers.append({
                "slug": slug,
                "name": name,
                "profession": "",
                "bio": "",
                "sources": [{
                    "label": f"El Peruano — {act['norma']}",
                    "url": act["url"],
                    "kind": "primary",
                }],
                "judicial": [],
            })
        tenures.append({
            "person": slug,
            "portfolio": portfolio,
            "start": act["date"],
            "end": None,
            "appointment_norma": {"numero": act["norma"], "url": act["url"], "date": act["date"]},
            "exit_norma": None,
            "exit_reason": None,
        })

    missing = [a for pid, a in announced_by_portfolio.items()
               if pid not in {t["portfolio"] for t in tenures}]
    for a in missing:
        conflicts.append({"kind": "sin-norma", "portfolio": a.get("portfolio"),
                          "announced": a.get("person_name", ""),
                          "detail": "anunciado pero el barrido no halló su norma"})

    return {"ministers": new_ministers, "tenures": tenures, "conflicts": conflicts}
