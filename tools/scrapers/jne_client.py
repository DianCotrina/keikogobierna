"""Transport for the JNE Plataforma Electoral API.

The JNE publishes an OpenAPI spec at /swagger/v1/swagger.json — 118 endpoints,
of which only seven require a captcha token. None of the ones used here do:
the candidate rolls and every hoja-de-vida section are open.

Verified 2026-07-27. Two traps for whoever maintains this next:

  - `POST /api/v1/candidato/avanzada` (the name search the website itself uses)
    IS captcha-gated. Do not build around it. `ListaCandidatos` returns the
    whole roll per election type without one, which is what this module uses.

  - `GET /api/v1/candidato/hoja-vida` (the aggregate endpoint) returns 500 for
    every id tried, including valid ones. The per-section `hv-*` endpoints all
    work, so the hoja de vida is assembled from those instead.

Elecciones Generales 2026 is idProcesoElectoral 124; its election types are
1 presidencial, 15 diputados, 3 parlamento andino, 20/21 senadores.
"""
import json
import urllib.request

BASE = "https://apiplataformaelectoral3.jne.gob.pe"
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "keikogobierna-evidence-tools",
}
TIMEOUT = 45

EG2026 = 124
ELECTION_TYPES = (1, 15, 3, 20, 21)

# The hoja de vida is assembled from these; the aggregate endpoint is broken.
#
# Only the sections jne_rules actually reads. The JNE also serves
# hv-sentenciaobliga, hv-expelaboral and hv-cargopartidario; those were fetched
# and discarded, doubling the requests per candidate for data nothing consumed.
# Work history and party posts are what a hand-written bio draws on, so if a
# bio ever needs them, add them back here *and* surface them in draft_person —
# fetching without surfacing helps nobody.
HV_SECTIONS = (
    "hv-sentenciapenal",
    "hv-formacaeduuni",
    "hv-posgrado",
)


def _get(path: str):
    request = urllib.request.Request(BASE + path, headers=HEADERS)
    return json.loads(urllib.request.urlopen(request, timeout=TIMEOUT).read())


def _post(path: str, body: dict):
    request = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"), headers=HEADERS, method="POST")
    return json.loads(urllib.request.urlopen(request, timeout=TIMEOUT).read())


def fetch_roster(proceso: int = EG2026, tipos=ELECTION_TYPES) -> list:
    """Every candidate in the given process, across election types.

    Raises on transport failure — an unofficial interface that changes shape
    should fail loudly, like the El Peruano client.
    """
    roster, seen = [], set()
    for tipo in tipos:
        rows = _post("/api/v1/candidato/ListaCandidatos",
                     {"idProcesoElectoral": proceso, "strUbiDepartamento": "", "idTipoEleccion": tipo})
        for row in rows or []:
            hv_id = row.get("idHojaVida")
            if hv_id in seen:
                continue  # a candidate appears once per election type
            seen.add(hv_id)
            roster.append(row)
    return roster


def fetch_hoja_vida(id_hoja_vida: int) -> dict:
    """All hoja-de-vida sections for one candidate, keyed by endpoint name."""
    return {
        section: _get(f"/api/v1/candidato/{section}?IdHojaVida={id_hoja_vida}")
        for section in HV_SECTIONS
    }
