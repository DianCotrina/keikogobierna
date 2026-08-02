"""Press coverage of each sitting minister, for their dossier page.

Coverage and nothing more: an article is here because an outlet named this
minister and their cartera, not because anyone judged it important or true.
The dossier says so in its own words, and this module must not imply otherwise
by filtering for tone or topic.

Pure: no I/O, no network. The caller supplies the articles and the roster.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .infobae_rules import headline_names_minister, profile_items

WINDOW_DAYS = 7

# What the dossier renders, and therefore all it is given. The feed summary and
# author stay out: shipping text no page displays would be carrying an outlet's
# prose for no reason. `matched_in` is derived rather than copied from the
# article (see build_index below), so it is documented here but not produced
# by the same dict-comprehension the other fields are.
PUBLISHED_FIELDS = ("title", "url", "source", "published", "matched_in")


def _published_at(article: dict):
    """Timezone-aware publication time, or None when it cannot be read."""
    try:
        parsed = datetime.fromisoformat(article.get("published") or "")
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else None


def build_index(articles: list, roster: list, now: datetime,
                window_days: int = WINDOW_DAYS) -> dict:
    """Coverage per minister slug, newest first, within the trailing window.

    Ministers with no coverage are absent rather than present with an empty
    list: the page renders both the same way, and absence keeps the file small.

    A roster row with no slug is skipped. That is an announced cartera whose
    holder has no ficha, so there is no dossier for the coverage to appear on.

    `now` must be timezone-aware; the only caller builds it from
    `datetime.now(timezone.utc)`, so this function does not guard against a
    naive `now`.
    """
    cutoff = now - timedelta(days=window_days)
    # The parsed instant travels with its article (as a copy's "_at" field)
    # so the sort below can reuse it instead of parsing `published` a second
    # time. PUBLISHED_FIELDS copies by name, so "_at" never reaches the file.
    fresh = []
    for article in articles:
        at = _published_at(article)
        if at is not None and at >= cutoff:
            fresh.append({**article, "_at": at})

    people = {row["portfolio"]: row for row in roster}
    index: dict = {}
    for pid, items in profile_items(fresh, roster).items():
        person = people[pid]
        slug = person.get("slug")
        if not slug:
            continue
        # Feeds don't share an offset (Lima local vs. UTC), so the sort must
        # compare parsed, timezone-aware instants rather than the raw ISO
        # strings — string order and chronological order disagree across
        # offsets.
        items = sorted(items, key=lambda item: item["_at"], reverse=True)
        entries = []
        for item in items:
            entry = {k: item.get(k) for k in PUBLISHED_FIELDS if k != "matched_in"}
            # profile_items matched on the headline + summary blob; whether
            # the *headline* gives a reader anything connecting it to this
            # person is a narrower, separate question — a reader who never
            # opens the summary must not read presence as aboutness. Apellido
            # OR cartera, not the full two-key AND: requiring both in the
            # headline is stricter than "does the headline connect to this
            # minister", and against live data it misclassified headlines
            # that plainly name either the minister ("Beingolea señala
            # que...") or their office ("Ministro de Cultura: 'No voy a
            # cerrar el LUM'") as summary-only.
            entry["matched_in"] = (
                "title" if headline_names_minister(item.get("title") or "", person)
                else "summary"
            )
            entries.append(entry)
        index[slug] = entries
    return index
