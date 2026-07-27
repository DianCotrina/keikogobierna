"""Read cabinet announcements from press headlines.

The gazette is the site's source of truth, but it lags: a cabinet is presented
in public a day or two before the Resolución Suprema that appoints it is
published. This module reads that announcement so the roster can show an
`anunciado` state in the meantime — always provisional, always superseded by
the norma when it lands.

Deterministic regex over headline text only, per the no-AI-in-pipelines
invariant and the metadata-only rule for press sources (article bodies are
never read or stored).

The pattern is deliberately structural: it requires an announcing verb, then a
name, then a linking word, then an office. That shape is what separates a real
announcement from the headlines that surround it. All of these ran in the same
feeds on the same day and none of them match:

    "Waldo Mendoza, exministro de Economía: ..."          (a quote)
    "La Premier League alista una revolucionaria regla"   (football)
    "¿Quién es Luis Galarreta, el nuevo presidente ...?"  (a profile)
    "Luis Galarreta, del círculo de confianza ... a
     próximo presidente del Consejo de Ministros"         (background piece)

No blocklist is needed to reject those, and none is used — a blocklist would
rot as coverage changes, while the structure holds.
"""
import re

from cabinet_rules import PCM_ID, portfolio_id

# A person: two to four capitalised words. Accented capitals included, since
# Peruvian names carry them.
_NAME = r"(?P<person>(?:[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.'-]+\s+){1,3}[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.'-]+)"

# An office: the PCM presidency, or a ministry named directly.
_OFFICE = (r"(?P<office>presidente\s+del\s+consejo\s+de\s+ministros"
           r"|ministr[oa]\s+d[ee]l?\s+[^,:.\"“”]{3,60})")

# "<verb> a NOMBRE como próximo <office>" / "<verb> que NOMBRE será el <office>"
_ANNOUNCEMENT = re.compile(
    r"(?:presenta|anuncia|designa|confirma|nombra)\s+(?:a\s+|que\s+)?" + _NAME +
    r"\s+(?:como|ser[áa]|es)\s+(?:el\s+|la\s+)?(?:pr[óo]xim[oa]\s+|nuev[oa]\s+)?" + _OFFICE,
    re.I)

_PCM_HEAD = re.compile(r"presidente\s+del\s+consejo\s+de\s+ministros", re.I)


def _office_to_portfolio(office: str):
    if _PCM_HEAD.search(office):
        return PCM_ID
    return portfolio_id(re.sub(r"(?i)^ministr[oa]\s+d[ee]l?\s+", "", office).strip())


def parse_announcement(article: dict):
    """Read one press item, or None if it does not announce a cabinet member.

    Returns {portfolio, person_name, announced, sources[]}. `person_name` is the
    raw name as printed — announcements deliberately do not reference a
    people.json slug, since a dossier may not exist yet.
    """
    title = (article.get("title") or "").strip()
    match = _ANNOUNCEMENT.search(title)
    if not match:
        return None

    portfolio = _office_to_portfolio(match.group("office"))
    person = " ".join(match.group("person").split()).strip(" .,;")
    if not portfolio or not person:
        return None

    url = (article.get("url") or "").strip()
    if not url.startswith("https://"):
        return None

    return {
        "portfolio": portfolio,
        "person_name": person,
        "announced": (article.get("published") or "")[:10],
        "sources": [{
            "label": article.get("source") or "Prensa",
            "url": url,
            "kind": "press",
        }],
    }


def announcements_from(articles: list) -> list:
    """Collapse a feed into one announcement per portfolio, accumulating sources.

    Two outlets reporting the same appointment is corroboration, not two
    appointments — and the number of independent sources is worth keeping.
    """
    by_portfolio: dict = {}
    for article in articles:
        parsed = parse_announcement(article)
        if not parsed:
            continue
        existing = by_portfolio.get(parsed["portfolio"])
        if not existing:
            by_portfolio[parsed["portfolio"]] = parsed
            continue
        seen = {s["url"] for s in existing["sources"]}
        for source in parsed["sources"]:
            if source["url"] not in seen:
                existing["sources"].append(source)
        # Keep the earliest date: when the announcement was first reported.
        if parsed["announced"] and parsed["announced"] < existing["announced"]:
            existing["announced"] = parsed["announced"]
    return list(by_portfolio.values())
