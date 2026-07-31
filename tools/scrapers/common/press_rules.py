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

from .cabinet_rules import PCM_HEAD, PCM_ID, portfolio_id
from .watcher_common import normalize


def fold(text: str) -> str:
    """`watcher_common.fold`, plus punctuation reduced to spaces.

    Headlines attach punctuation to names — "Delia Espinoza: Poder Judicial
    archiva…" — so a plain whitespace split would yield "espinoza:" and never
    match the roster. That extra step is why this does not just call the
    shared helper.
    """
    return " ".join(re.sub(r"[^0-9a-z]+", " ", normalize(text or "")).split())

# A person: two to four capitalised words. Accented capitals included, since
# Peruvian names carry them.
_NAME = r"(?P<person>(?:[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.'-]+\s+){1,3}[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.'-]+)"

# An office: the PCM presidency, or a ministry named directly.
_OFFICE = (r"(?P<office>presidente\s+del\s+consejo\s+de\s+ministros"
           r"|ministr[oa]\s+d[ee]l?\s+[^,:.\"“”]{3,60})")

# "<verb> a NOMBRE como próximo <office>" / "<verb> que NOMBRE será el <office>"
# Present and preterite both appear: headlines use "anuncia", ledes "anunció".
_VERB = r"(?:presenta|present[óo]|anuncia|anunci[óo]|designa|design[óo]|confirma|confirm[óo]|nombra|nombr[óo])"
_ANNOUNCEMENT = re.compile(
    _VERB + r"\s+(?:a\s+|que\s+)?" + _NAME +
    r"\s+(?:como|ser[áa]|es)\s+(?:el\s+|la\s+)?(?:pr[óo]xim[oa]\s+|nuev[oa]\s+)?" + _OFFICE,
    re.I)

def _office_to_portfolio(office: str):
    """Resolve a headline's office phrase to a portfolio id.

    A headline seldom stops at the ministry: "ministro de Economía de su primer
    gabinete". Rather than maintain a stoplist of trailing clauses, try the
    longest prefix of the phrase first and shorten until one resolves against
    the registry. The registry stays the only authority on what a ministry is,
    and an ambiguous prefix ("Desarrollo", which matches two carteras) resolves
    to nothing because portfolio_id() requires a unique hit.
    """
    if PCM_HEAD.search(office):
        return PCM_ID

    phrase = re.sub(r"(?i)^ministr[oa]\s+d[ee]l?\s+", "", office).strip()
    words = phrase.split()
    for length in range(len(words), 0, -1):
        candidate = " ".join(words[:length]).strip(" ,.;")
        resolved = portfolio_id(candidate)
        if resolved:
            return resolved
    return None


def parse_announcement(article: dict):
    """Read one press item, or None if it does not announce a cabinet member.

    Returns {portfolio, person_name, announced, sources[]}. `person_name` is the
    raw name as printed — announcements deliberately do not reference a
    ministers.json slug, since a dossier may not exist yet.
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


# Judicial language, wide on purpose: this is a discovery signal a human checks,
# so a false positive costs a glance while a miss costs a fact.
_JUDICIAL = re.compile(
    r"fiscal[ií]a|investigaci[óo]n|investigan|acusa\w*|imputa\w*|"
    r"conden\w*|sentenci\w*|absuel\w*|archiv\w*|sobresee\w*|prescri\w*|"
    r"juicio\s+oral|prisi[óo]n\s+preventiva|impedimento\s+de\s+salida|"
    r"allanamiento|poder\s+judicial|ministerio\s+p[úu]blico",
    re.I)


def _mentions(words: set, name_tokens: list) -> bool:
    """Whether a folded article names this person.

    The given name and the first surname must both appear; anything after them
    is optional. Peruvian rosters carry both surnames — "Mauricio Arnillas
    Gonzales", taken from El Peruano — while headlines print one, so requiring
    every token silently missed a conviction on a sitting minister. Requiring
    two still rejects "Guardaespaldas del Rey de España" for Rafael Rey Rey,
    because "rafael" is absent.

    A single-token name is rejected outright: one surname is not an
    identification.

    Both sides arrive folded and tokenised — the caller folds each article once
    and each roster name once, not on every comparison.
    """
    if len(name_tokens) < 2:
        return False
    return all(token in words for token in name_tokens[:2])


def judicial_signals(articles: list, roster_names: list) -> list:
    """Press items that mention a roster person alongside judicial language.

    Discovery only. Returns no stage and writes nothing: press reports
    allegations far more loosely than a court records them, so each signal is a
    prompt to check a primary source, not a finding.

    Scoped to the roster deliberately — "Putin acusa a Occidente" and "dos
    hombres acusados de vender estampillas falsas" are judicial-shaped headlines
    about people this site does not track.
    """
    folded = {name: fold(name).split() for name in roster_names}

    signals, seen = [], set()
    for article in articles:
        title = article.get("title") or ""
        summary = article.get("summary") or ""
        words = set(fold(f"{title} {summary}").split())

        # Every judicial term present, not just the first: "Poder Judicial
        # archiva…" carries both the court and the outcome, and the reviewer
        # wants to see the outcome.
        terms = list(dict.fromkeys(m.group(0) for m in _JUDICIAL.finditer(f"{title} {summary}")))
        if not terms:
            continue

        for name, name_tokens in folded.items():
            if not _mentions(words, name_tokens):
                continue
            url = (article.get("url") or "").strip()
            key = (" ".join(name_tokens), url)
            if key in seen:
                continue
            seen.add(key)
            signals.append({
                "person_name": name,
                "matched": " · ".join(terms),
                "title": " ".join(title.split()),
                "url": url,
                "source": article.get("source") or "Prensa",
                "published": (article.get("published") or "")[:10],
            })
    return signals


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
