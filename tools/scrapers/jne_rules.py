"""Turn a JNE hoja de vida into a draft the reviewer finishes.

Candidates file a Declaración Jurada de Hoja de Vida with the JNE: education,
work history, party roles, and any criminal or civil sentences against them.
It is a primary source — the person's own sworn statement to the state — and
the JNE publishes it openly.

**Nothing here assigns a judicial stage, deliberately.** The form is filled
inconsistently and its fields contradict each other in practice. Real records
from the Elecciones Generales 2026 rolls:

    delito "TERRORISMO", fallo "ABSUELTO", modalidad "EFECTIVA"
        — an acquittal filed under the modality of an effective prison term.
          Any mapper keyed on modalidad would publish a terrorism conviction
          against a man the court acquitted.

    delito "0", fallo "0", órgano "0", comentario "1. Causa penal prescrita."
        — the fields are placeholders and the substance is in free text.

So `declared_sentences()` emits entries with `stage` set to None and the whole
raw declaration attached under `_declaracion`. The cabinet validator rejects an
entry whose stage is unset, so a draft physically cannot reach the site until a
person reads the fallo, the modalidad and the comentario together and decides.
That is the same human gate the norma -> tracking.json path already uses.

Pure functions: no I/O. Transport lives in jne_client.py.
"""
import re
import unicodedata

# The JNE platform is an Angular SPA whose hoja-de-vida view is reachable only
# by navigating its (captcha-gated) search — verified headless: no path or query
# form renders a candidate, they all serve the empty shell. So there is no page
# to deep-link. The open API endpoint is cited instead: same primary source, it
# actually resolves, and it returns the declaration itself.
HV_URL = ("https://apiplataformaelectoral3.jne.gob.pe"
          "/api/v1/candidato/hv-sentenciapenal?IdHojaVida={id_hoja_vida}")
HV_SOURCE_LABEL = "Hoja de vida JNE (datos abiertos)"

# Spanish minor words stay lowercase inside a title; the rolls are all caps.
_MINOR = {"de", "del", "la", "las", "los", "el", "y", "e", "en", "a",
          "con", "por", "para", "un", "una"}


def title_es(text: str) -> str:
    """Title-case Spanish without capitalising the joining words.

    str.title() turns "BACHILLER EN DERECHO Y CIENCIA POLITICA" into
    "Bachiller En Derecho Y Ciencia Politica", which reads wrong in Spanish.
    """
    words = (text or "").strip().split()
    out = []
    for i, word in enumerate(words):
        lowered = word.lower()
        out.append(lowered if i > 0 and lowered in _MINOR else lowered.capitalize())
    return " ".join(out)


def fold(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace. The rolls are inconsistent
    about accents and the press is inconsistent about everything."""
    stripped = unicodedata.normalize("NFD", (text or "").lower())
    bare = "".join(c for c in stripped if unicodedata.category(c) != "Mn")
    return " ".join(bare.split())


def _full_name(candidate: dict) -> str:
    parts = [candidate.get("txNom"), candidate.get("txApePat"), candidate.get("txApeMat")]
    return " ".join(p.strip() for p in parts if p and p.strip())


def match_candidates(query: str, roster: list) -> list:
    """Candidates whose name contains every token of the query.

    Deterministic containment, never fuzzy: the press prints "Luis Galarreta"
    where the roll says "LUIS FERNANDO GALARRETA VELARDE", so a subset match is
    required — but a token the roll does not carry rules the person out. An
    ambiguous query returns every hit rather than picking one; choosing is the
    caller's job.
    """
    tokens = [t for t in fold(query).split() if t]
    if not tokens:
        return []

    hits, seen = [], set()
    for candidate in roster:
        name = fold(_full_name(candidate))
        if not all(t in name.split() for t in tokens):
            continue
        # A candidate appears once per election type; one person, one entry.
        hv_id = candidate.get("idHojaVida")
        if hv_id in seen:
            continue
        seen.add(hv_id)
        hits.append(candidate)
    return hits


def _iso_date(value: str) -> str:
    """JNE writes dd/mm/yyyy."""
    match = re.match(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$", value or "")
    if not match:
        return ""
    day, month, year = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def _section(hoja_vida: dict, endpoint: str, key: str) -> list:
    payload = (hoja_vida.get(endpoint) or {}).get(key)
    return payload if isinstance(payload, list) else []


def _summary(record: dict) -> str:
    """Quote the declaration; never characterise it.

    Every field the reviewer needs to spot a contradiction goes in the sentence,
    verbatim — including the fallo and the modalidad when they disagree.
    """
    bits = []
    fallo = (record.get("txFalloPenal") or "").strip()
    if fallo and fallo != "0":
        bits.append(f"fallo «{fallo}»")
    modalidad = (record.get("txModalidad") or "").strip()
    if modalidad:
        otra = (record.get("txOtraModalidad") or "").strip()
        bits.append(f"modalidad {modalidad}" + (f" ({otra})" if otra else ""))
    cumple = (record.get("txCumpleFallo") or "").strip()
    if cumple:
        bits.append(cumple.lower())

    detail = "; ".join(bits) if bits else "sin detalle en la declaración"
    text = f"Así lo declaró ante el JNE en su hoja de vida: {detail}."
    comentario = (record.get("txComentario") or "").strip()
    if comentario:
        text += f" Comentario del declarante: «{' '.join(comentario.split())}»"
    return text


def declared_sentences(hoja_vida: dict) -> list:
    """Draft judicial entries from the declared criminal sentences.

    `stage` is always None: see the module docstring. The raw declaration rides
    along under `_declaracion` so the reviewer decides from the source text.
    """
    entries = []
    records = _section(hoja_vida, "hv-sentenciapenal", "sentenciaPenal")
    for i, record in enumerate(records, start=1):
        expediente = (record.get("txExpedientePenal") or "").strip()
        crime = (record.get("txDelitoPenal") or "").strip()
        entries.append({
            "id": f"jne-penal-{i:02d}",
            "case": f"Sentencia declarada ante el JNE ({crime or 'delito no especificado'})",
            "expediente": expediente if expediente and expediente != "0" else None,
            "stage": None,  # a person must set this
            "crime": crime,
            "body": (record.get("txOrganoJudiPenal") or "").strip(),
            "date": _iso_date(record.get("feSentenciaPenal")),
            "summary": _summary(record),
            "sources": [{
                "label": HV_SOURCE_LABEL,
                "url": HV_URL.format(id_hoja_vida=record.get("idHojaVida", "")),
                "kind": "primary",
            }],
            "_declaracion": {
                "txFalloPenal": record.get("txFalloPenal"),
                "txModalidad": record.get("txModalidad"),
                "txOtraModalidad": record.get("txOtraModalidad"),
                "txCumpleFallo": record.get("txCumpleFallo"),
                "txComentario": record.get("txComentario"),
            },
        })
    return entries


def profession_of(hoja_vida: dict) -> str:
    """The declared professional qualification.

    The university degree wins over a postgraduate one: Galarreta declares a
    law bachelor's and an unfinished master's in political marketing, and the
    former is what names his profession. A postgrado is used only when there is
    no university degree, and only if it was completed.
    """
    academic = "formacionAcademica"

    uni = ((hoja_vida.get("hv-formacaeduuni") or {}).get(academic) or {}).get("educacionUniversitaria")
    for row in (uni if isinstance(uni, list) else []):
        value = (row.get("carreraUni") or "").strip()
        if value:
            return value

    posgrado = ((hoja_vida.get("hv-posgrado") or {}).get(academic) or {}).get("educacionPosgrado")
    for row in (posgrado if isinstance(posgrado, list) else []):
        if (row.get("concluidoPosgrado") or "").strip().upper() != "SI":
            continue
        value = (row.get("txEspecialidadPosgrado") or "").strip()
        if value:
            return value
    return ""


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", fold(name)).strip("-")


def draft_person(candidate: dict, hoja_vida: dict) -> dict:
    """A people.json entry ready for review — never for merging as-is."""
    name = _full_name(candidate)
    hv_id = candidate.get("idHojaVida")
    return {
        "slug": _slug(name),
        "name": title_es(name),
        "profession": title_es(profession_of(hoja_vida)),
        "bio": "",  # written by a person; the declaration carries no prose
        "sources": [{
            "label": HV_SOURCE_LABEL,
            "url": HV_URL.format(id_hoja_vida=hv_id),
            "kind": "primary",
        }],
        "judicial": declared_sentences(hoja_vida),
    }
