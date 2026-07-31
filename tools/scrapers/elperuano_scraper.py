#!/usr/bin/env python3
"""Read the day's El Peruano normas (primary source) and file candidate-evidence issues.

Discovery, not certification: every matched norma becomes a GitHub issue for human
review; statuses in tracking.json change only through the PR flow. Three stages —
fetch (public search page) -> keyword prefilter -> issues (with a text excerpt) + archive.
No AI anywhere: reviewing a candidate is a human job, by design.
See workflows/elperuano_scraper.md.

Reconnaissance (2026-07-31): El Peruano rebuilt busquedas.elperuano.pe as a React
Router app and removed the old unauthenticated /api/graphql endpoint (now 404).
The public search page still serves the day's normas as server-rendered cards at
  /?fechaIni=YYYYMMDD&fechaFin=YYYYMMDD&tipoPublicacion=<NL|BO|PC>&ci=ONLY&start=<n>
20 cards/page, paginated by `start`. Each card carries the sector, tipo, numero,
sumilla and the norma's `op` (via /dispositivo/<tipoPub>/<op>). The dispositivo
page embeds the clean single-norma rendition inside a #visor-html box — the same
document the retired /api/visor_html/<op> served. All unofficial: if the markup
changes, the run fails loudly in Actions and we fix the tool.

Usage:
  python3 -m tools.scrapers.elperuano_scraper --dry-run   # today, print records/matches, no writes
  python3 -m tools.scrapers.elperuano_scraper --date 2026-07-10 --dry-run
  GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo python3 -m tools.scrapers.elperuano_scraper
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from tools.scrapers.common.elperuano_client import fetch_normas, norma_text
from tools.scrapers.common.matcher import load_matcher
from tools.scrapers.common.watcher_common import (
    DEFAULT_REPO,
    LABEL,
    create_issue,
    dedup_token,
    ensure_label,
    http_get,
    issue_exists,
)

MAX_NEW_ISSUES = 10
EXCERPT_CHARS = 1200  # norma-text excerpt embedded in each issue for review

# Tunable noise gate: norma types to skip outright (municipal/local acts rarely
# touch national commitments). Empty by default — the matcher is the real
# relevance gate; add tipos here only if local noise shows up in the queue.
SKIP_TIPOS: set[str] = set()

# A municipal/regional own-act can't evidence the *national* government's plan, yet
# its boilerplate ("beneficios tributarios", "rendicion de cuentas") keeps matching
# national commitments. Drop subnational publishers from the review queue by sector;
# they still land in the archive (this gate is applied at the match stage, not fetch).
SUBNATIONAL_SECTOR_RE = re.compile(r"^\s*(municipalidad|gobierno regional)\b", re.I)


def in_national_scope(record: dict) -> bool:
    """False for norms published by a municipality or regional government."""
    return not SUBNATIONAL_SECTOR_RE.match(record.get("sector", ""))


# ---- Stage 1: fetch (public search page) --------------------------------------

# ---- Stage 2: match against plan commitments ---------------------------------
# Matching lives in tools/scrapers/common/matcher.py (shared). A norma's numero + tipo +
# sumilla is matched against the distinctive-phrase index built from the plan.


# ---- Stage 3: norma text (for the issue excerpt) ------------------------------

# ---- Stage 4: issue body ------------------------------------------------------

def draft_note(record: dict) -> str:
    """A non-blank starting note for the evidence block: the norma's own summary,
    which the reviewer refines into how it cumple/avanza the commitment."""
    sumilla = record["sumilla"].strip()
    if sumilla:
        return sumilla if sumilla.endswith(".") else sumilla + "."
    return f"{record['tipo']} {record['numero']} (El Peruano, {record['fecha']})."


def issue_body(record: dict, related: list[str], iso_date: str, excerpt: str) -> str:
    related_lines = "\n".join(f"- `{cid}`" for cid in related) or "- (sin ids asociados)"
    evidence = {
        "date": iso_date,
        "source": f"El Peruano — {record['tipo']} {record['numero']}".strip(),
        "url": record["url"],
        "note": draft_note(record),
    }

    excerpt_section = ""
    if excerpt and excerpt != record["sumilla"]:
        excerpt_section = f"""

<details>
<summary>Texto de la norma (extracto)</summary>

> {excerpt}

</details>"""

    return f"""**Norma:** {record['tipo']} {record['numero']}
**Sector:** {record['sector']}
**Publicado:** {iso_date} · [El Peruano]({record['url']})
**Sumilla:** {record['sumilla'] or '(sin sumilla)'}

**Compromisos posiblemente relacionados:**
{related_lines}{excerpt_section}

Evidencia lista para `src/data/tracking.json` — la `note` trae un borrador (la sumilla de la norma); revísala y ajústala al compromiso antes de certificar:
```json
{json.dumps(evidence, ensure_ascii=False, indent=2)}
```

---

**Revisión editorial:**
- [ ] Confirmar que la norma efectivamente cumple/avanza el compromiso
- [ ] Actualizar `src/data/tracking.json` (estado + evidencia + log) vía PR
- [ ] Cerrar este issue enlazando el PR o explicando el descarte

_Generado por el scraper de El Peruano. Este issue no cambia ningún estado._"""


# ---- Orchestration ------------------------------------------------------------

def write_archive(archive_dir: str, iso_date: str, records: list[dict]) -> None:
    path = Path(archive_dir)
    path.mkdir(parents=True, exist_ok=True)
    out = path / f"{iso_date}.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Archived {len(records)} records to {out}")


def run(target: date, dry_run: bool, archive_dir: str | None) -> int:
    yyyymmdd = target.strftime("%Y%m%d")
    iso_date = target.isoformat()
    matcher = load_matcher()

    repo = os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO)
    gh_token = os.environ.get("GITHUB_TOKEN", "")
    if not dry_run and not gh_token:
        print("ERROR: GITHUB_TOKEN required unless --dry-run", file=sys.stderr)
        return 1

    records = [r for r in fetch_normas(yyyymmdd, iso_date) if r["tipo"] not in SKIP_TIPOS]
    if archive_dir:
        write_archive(archive_dir, iso_date, records)
    matched = [
        (r, rel) for r in records
        if in_national_scope(r)
        and (rel := matcher.match(f"{r['numero']} {r['tipo']} {r['sumilla']}"))
    ]
    print(f"{iso_date}: {len(records)} normas, {len(matched)} matched")

    if not matched:
        print("No matches; nothing to file.")
        return 0

    if not dry_run:
        ensure_label(repo, gh_token)

    created = 0
    for record, related in matched:
        token_str = dedup_token("np", f"{record['tipo']}|{record['numero']}|{iso_date}")

        if dry_run:
            print(f"[{token_str}] {record['tipo']} {record['numero']} — {record['sumilla'][:70]}")
            continue

        if created >= MAX_NEW_ISSUES:
            print(f"Reached cap of {MAX_NEW_ISSUES} new issues; stopping.")
            break
        if issue_exists(token_str, repo, gh_token):
            continue
        tema_labels = sorted({f"tema:{s}" for cid in related if (s := matcher.tema_slug(cid))})
        for tl in tema_labels:
            ensure_label(repo, gh_token, name=tl, color="6B6F7B",
                         description=f"Compromisos del tema «{tl.split(':', 1)[1]}»")
        excerpt = " ".join(norma_text(record).split())[:EXCERPT_CHARS]
        title = f"Norma candidata: {record['tipo']} {record['numero']} [{token_str}]"[:250]
        issue = create_issue(repo, gh_token, title, issue_body(record, related, iso_date, excerpt),
                             labels=[LABEL] + tema_labels)
        created += 1
        print(f"Created issue #{issue['number']}: {record['tipo']} {record['numero']}")

    print("Dry run complete." if dry_run else f"Done: {created} issue(s) created.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="YYYY-MM-DD (default: today, UTC)")
    parser.add_argument("--dry-run", action="store_true", help="print records/matches without writing issues")
    parser.add_argument("--archive-dir", help="write the day's records as <dir>/<date>.jsonl")
    args = parser.parse_args()

    if args.date:
        target = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        target = datetime.now(timezone.utc).date()

    return run(target, args.dry_run, args.archive_dir)


if __name__ == "__main__":
    sys.exit(main())
