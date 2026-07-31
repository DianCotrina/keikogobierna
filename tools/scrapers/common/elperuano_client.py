"""Transport for busquedas.elperuano.pe — the daily gazette.

Unofficial and therefore fragile: the site was rebuilt as a React Router app in
July 2026 and its GraphQL endpoint removed. The public search page still serves
each day's normas as server-rendered cards, and every /dispositivo/ page inlines
the clean single-norma rendition. If that markup changes the run fails loudly in
Actions and we fix it here — the scrapers above stay unaware of the encoding.

Shared: the evidence reader and the cabinet sweep read the same gazette, and a
transport fix must reach both. Neither imports the other.
"""
from __future__ import annotations

import html
import re
import sys
import time
import urllib.error

from .watcher_common import http_get


BASE = "https://busquedas.elperuano.pe"
SEARCH_URL = BASE + "/?fechaIni={d}&fechaFin={d}&tipoPublicacion={tipo}&ci=ONLY&start={start}"
DISPOSITIVO_URL = BASE + "/dispositivo/{tipo_pub}/{op}"
# The three daily editions the site exposes: Normas Legales, Boletín Oficial, PC.
TIPOS_PUBLICACION = ("NL", "BO", "PC")
PAGE_SIZE = 20   # cards per search page (site-fixed)
MAX_PAGES = 60   # safety cap per edition: 60*20 = 1200 normas/day
def _text(match: "re.Match | None") -> str:
    """Inner text of a regex capture: strip tags, unescape entities, collapse space."""
    if not match:
        return ""
    stripped = re.sub(r"<[^>]+>", " ", match.group(1))
    return re.sub(r"\s+", " ", html.unescape(stripped)).strip()


def parse_search_cards(page: str, tipo_pub: str, iso_date: str) -> list[dict]:
    """Map one search-results page -> records. Shared by fetch and tests.

    Each result is a `rounded-xl border bg-card` block carrying the norma's sector,
    tipo, numero, sumilla and its `op` (from the /dispositivo/<tipoPub>/<op> link).
    """
    records: list[dict] = []
    for chunk in page.split('<div class="rounded-xl border bg-card')[1:]:
        href = re.search(r"/dispositivo/[A-Za-z]+/(\d+-\d+)", chunk)
        if not href:
            continue
        op = href.group(1)
        records.append({
            "tipo": _text(re.search(r'<p class="text-xs text-muted-foreground">(.*?)</p>', chunk, re.S)),
            "numero": _text(re.search(r'font-medium text-muted-foreground">(.*?)</p>', chunk, re.S)),
            "sector": _text(re.search(r'text-primary[^>]*>(.*?)</p>', chunk, re.S)),
            "rubro": "",  # the old GraphQL had a rubro; the cards don't expose one
            "sumilla": _text(re.search(r'line-clamp-3[^>]*>(.*?)</a>', chunk, re.S)),
            "url": DISPOSITIVO_URL.format(tipo_pub=tipo_pub, op=op),
            "fecha": iso_date,
            "op": op,
            "tipo_pub": tipo_pub,
        })
    return records


RETRY_ATTEMPTS = 4  # the site returns transient 404s/5xx under load; one blip must not kill the day


def _get_page(url: str) -> str:
    """GET a search page, retrying transient HTTP/network errors with backoff."""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return http_get(url).decode("utf-8", "replace")
        except (urllib.error.HTTPError, urllib.error.URLError) as err:
            if attempt == RETRY_ATTEMPTS - 1:
                raise
            print(f"WARN: {url} failed ({err}); retry {attempt + 1}/{RETRY_ATTEMPTS - 1}", file=sys.stderr)
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
    raise AssertionError("unreachable")  # loop either returns or raises


def fetch_normas(yyyymmdd: str, iso_date: str) -> list[dict]:
    """The day's normas across all three editions, de-duplicated by op.

    Everything the gazette published that day. Relevance filtering is the
    caller's business: the evidence queue drops subnational acts and tuned-out
    tipos, the cabinet sweep wants none of that.
    """
    records: list[dict] = []
    seen: set[str] = set()
    for tipo_pub in TIPOS_PUBLICACION:
        for page_no in range(MAX_PAGES):
            url = SEARCH_URL.format(d=yyyymmdd, tipo=tipo_pub, start=page_no * PAGE_SIZE)
            try:
                page = _get_page(url)
            except urllib.error.HTTPError as err:
                # A normal edition-end is a short page, not a 404; a 404 that persists
                # past page 0 is the pagination tail — stop this edition instead of failing.
                if err.code == 404 and page_no > 0:
                    print(f"WARN: {tipo_pub} start={page_no * PAGE_SIZE}: 404 after retries — end of edition", file=sys.stderr)
                    break
                raise
            cards = parse_search_cards(page, tipo_pub, iso_date)
            for rec in cards:
                if rec["op"] not in seen:
                    seen.add(rec["op"])
                    records.append(rec)
            if len(cards) < PAGE_SIZE:  # short page => last page of this edition
                break
    return records


def html_to_text(raw: bytes) -> str:
    """Plain text from a single-norma HTML rendition (stdlib only).

    The <head> goes too: the rendition's <title> carries an unrelated norma's name.
    """
    text = re.sub(r"<head\b.*?</head>", " ", raw.decode("utf-8", "replace"), flags=re.S | re.I)
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def extract_visor_html(page: bytes) -> bytes:
    """The embedded single-norma document from a /dispositivo/ page's #visor-html box."""
    text = page.decode("utf-8", "replace")
    i = text.find('id="visor-html"')
    if i < 0:
        return b""
    m = re.search(r"<html\b.*?</html>", text[i:], re.S)
    return m.group(0).encode("utf-8") if m else b""


def norma_text(record: dict) -> str:
    """Full norma text from the /dispositivo/ page's embedded rendition; sumilla on failure.

    The dispositivo page inlines the clean single-norma document in #visor-html;
    everything else on that page (toolbar, sibling normas) is stripped by working
    from that box only. Any fetch/parse blip falls back to the sumilla so a
    candidate is never lost to it.
    """
    try:
        visor = extract_visor_html(http_get(record["url"]))
        if visor:
            text = html_to_text(visor)
            if len(text) > len(record["sumilla"]):
                return text[:15000]
    except Exception as err:  # noqa: BLE001 - never lose a candidate to a fetch blip
        print(f"WARN: dispositivo fetch failed for {record['numero']}: {err}", file=sys.stderr)
    return record["sumilla"]
