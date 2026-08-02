"""Match press items to the minister they profile.

The JNE covers only ministers who stood for election. For everyone else the
press is the only public account of who they are, and Infobae publishes a
profile for nearly the whole cabinet — with the profession in the feed's own
summary, so no article body is ever read.

Discovery only. This proposes reading material; a person writes the ficha.

Pure functions: no I/O, no network.
"""
from __future__ import annotations

import re
from datetime import datetime

from .cabinet_rules import resolve_portfolio_prefix
from .press_rules import fold

# Headline shapes that mark a piece as a profile rather than a news item.
_PROFILE = re.compile(
    r"qui[ée]n\s+es|perfil|trayectoria|hoja\s+de\s+vida|conoce\s+a|"
    r"qui[ée]nes\s+integran|este\s+es\s+su",
    re.I)

# A ministry named anywhere in the text, however the outlet writes it: in full,
# by short name, or by one of the acronyms and synonyms portfolios.json carries.
#
# Wrapped in a zero-width lookahead so matches never consume each other: a
# consuming match for "ministro de Economía Cuba y el ministro de Trabajo
# Sheput…" would swallow the second "ministro de…" inside the first match's
# capture, and finditer would resume past it — never seeing the second
# minister at all. The lookahead makes every match zero-width, so finditer
# tries again one character later instead of after a whole captured span,
# and each "ministro de…" / acronym / canciller|premier mention is examined
# on its own.
#
# The name capture itself is also bounded to stop before the next such
# mention (rather than running up to 60 chars regardless of content), so a
# sentence naming two ministers resolves both instead of one match's capture
# swallowing the other minister's name into its own prefix-matching attempt.
_MINISTRY = re.compile(
    r"(?=(?:ministr[oa]|ministerio|titular)\s+(?:de\s+la|del|de|en\s+el)?\s*"
    r"((?:(?!\bministr[oa]\b|\bministerio\b|\btitular\b)"
    r"[\wÁÉÍÓÚÑáéíóúñ.\- ]){3,60})"
    r"|\b(MTC|MEF|Minem|Minsa|Minedu|Midagri|Mincetur|Produce|Mininter|Mindef|"
    r"Minjus|Minjusdh|MTPE|Mimp|Minam|Mincul|Midis|RREE|PCM)\b"
    r"|\b(canciller[ií]a|canciller|premier)\b)",
    re.I)


def is_profile(title: str) -> bool:
    """Whether a headline reads as a profile piece rather than plain news."""
    return bool(_PROFILE.search(title or ""))


def _carteras_named(text: str) -> set:
    """Every registry id the text names, by any spelling the registry knows."""
    found = set()
    for match in _MINISTRY.finditer(text or ""):
        for group in match.groups():
            if not group:
                continue
            # A ministry phrase runs on — "ministro de Economía y Finanzas del
            # gobierno de…" — so resolve_portfolio_prefix shortens it until the
            # registry recognises one.
            pid = resolve_portfolio_prefix(group)
            if pid:
                found.add(pid)
    return found


def _surnames(person_name: str) -> list:
    """The two apellidos of a Peruvian full name, paterno and materno.

    "Mara Seminario Marón" -> ["seminario", "maron"].

    Taken from the end, not by dropping the first token. Everything before the
    apellidos is given names, and there can be more than one: the roster used to
    hold press-style names with a single one, and now holds the gazette's full
    legal names, where 16 of 19 carry two. Dropping only the first left
    "carlos", "julio", "fernando" and "manuel" standing in as surnames -- common
    enough given names to match strangers.

    Two exceptions, both real on the sitting cabinet:

    `fold` reduces punctuation to spaces, so a compound apellido arrives as
    separate tokens: "Espá y Garcés-Alvear" becomes espa / garces / alvear, and
    the last two would drop "Espá" -- the one name the press actually prints for
    him. A " y " in the original marks that compound, so the token before the
    final pair is kept as well.

    Tokens of two characters or fewer go first, which is what stops the
    conjunction itself from being read as a surname.
    """
    tokens = [t for t in fold(person_name).split() if len(t) > 2]
    if len(tokens) <= 1:
        return tokens
    joined = f" {fold(person_name)} "
    take = 3 if " y " in joined and len(tokens) > 2 else 2
    return tokens[-take:]


def names_minister(text: str, person: dict) -> bool:
    """Does this text name both the person's cartera and one of their apellidos?

    The two-key rule, asked of any text rather than only of a whole article.
    """
    if person.get("portfolio") not in _carteras_named(text):
        return False
    words = set(fold(text or "").split())
    return any(s in words for s in _surnames(person.get("person_name", "")))


def headline_names_minister(text: str, person: dict) -> bool:
    """Does this text give a reader any reason to connect it to this person?

    Either half is enough, unlike `names_minister`'s two-key AND: an apellido
    (`_surnames`, matched the same way `names_minister` does) or the cartera
    alone (`_carteras_named`, every spelling the registry knows — full name,
    short name, acronyms like Minedu and Mincetur, canciller/premier). The
    cartera alone counts because the dossier belongs to whoever holds that
    office right now: a headline naming the office names them.

    `minister_news` asks this of the headline alone, to tell a reader whether
    the headline itself connects to this minister or whether the connection
    exists only in the feed summary they never see. `"summary"` should mean
    "nothing in the headline points here" — not "the headline didn't happen to
    spell out both keys at once", which is what requiring the cartera too
    would test instead.
    """
    if person.get("portfolio") in _carteras_named(text):
        return True
    words = set(fold(text or "").split())
    return any(s in words for s in _surnames(person.get("person_name", "")))


def _epoch(published: str) -> float:
    """Sortable timestamp; an unparseable date sorts last."""
    try:
        return datetime.fromisoformat(published).timestamp()
    except (ValueError, TypeError):
        return 0.0


def profile_items(articles: list, roster: list) -> dict:
    """Articles about each minister, keyed by cartera, in feed order.

    A match needs two keys: the item must name one of the person's surnames
    *and* resolve to their cartera. Either alone is wrong in a way the live feed
    demonstrates — "María Seminario" defeats name matching because the roster
    says "Mara", and "Guardaespaldas del Rey de España" defeats surname matching
    because the transport minister is Rafael Rey Rey.

    Every minister an article names receives it. Stopping at the first was fine
    while the only caller wanted one profile per cartera; an article about two
    ministers is coverage of both, and which one won was roster order.

    Order is the caller's: a review packet wants profiles first, a dated news
    list wants the newest.
    """
    by_portfolio: dict = {}

    for article in articles:
        title = article.get("title") or ""
        summary = article.get("summary") or ""
        blob = f"{title} {summary}"
        if not _carteras_named(blob):
            continue

        for person in roster:
            if not names_minister(blob, person):
                continue
            by_portfolio.setdefault(person.get("portfolio"), []).append(article)

    return by_portfolio


def sort_for_review(items: list) -> list:
    """Profile pieces first, then newest — what a person writing a ficha wants."""
    return sorted(items, key=lambda a: (not is_profile(a.get("title") or ""),
                                        -_epoch(a.get("published") or "")))
