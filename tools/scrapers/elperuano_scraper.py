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
    fold,
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
SUBNATIONAL_SECTOR_RE = re.compile(r"^(municipalidad|gobierno regional)\b")

# Same reasoning one level up: the plan being tracked is the *executive's*, so an
# own-act of a constitutionally autonomous control or judicial body can't evidence
# it. These publish constantly (appointments, disciplinary rulings, registry
# annexes) and kept surfacing as candidates — issues #231-#235.
#
# Deliberately narrow. INEI, BCR, RENIEC, ONPE and the JNE stay in scope: the 65
# metas 2031 are quantitative and those bodies publish the statistics that measure
# them. INEI's monthly-index noise is handled on the phrase gate instead.
#
# Matched anywhere in the sector, not anchored: an autonomous body's own organs
# publish under their own names, and "Autoridad Nacional de Control del Ministerio
# Público" slipped through an anchored match (issue #271) even though it is exactly
# the internal-control act the gate exists to drop. A sector string names the
# publisher, so containing one of these means the publisher *is* that body.
AUTONOMOUS_SECTOR_RE = re.compile(
    r"\b(contraloria|poder judicial|ministerio publico|cortes superiores"
    r"|consejo ejecutivo del poder judicial|academia de la magistratura"
    r"|junta nacional de justicia)\b"
)


def in_national_scope(record: dict) -> bool:
    """False for norms a municipality, regional government, or autonomous control
    or judicial body published as its own act."""
    sector = fold(record.get("sector", ""))
    return not (SUBNATIONAL_SECTOR_RE.match(sector) or AUTONOMOUS_SECTOR_RE.search(sector))


def is_norma_record(record: dict) -> bool:
    """False for the Boletín Oficial's section headings, which arrive shaped like
    records but carry no numero and no sumilla ("Balance Por Entidades
    Financieras", "Estudios Ambientales (suelo, agua, ruido…)"). With no sumilla
    the matcher sees only the tipo, which is a section name and matches on its
    topic words — issue #272."""
    return bool(fold(record.get("sumilla", "")))


# Routine acts that cannot evidence a commitment, gated by what the norma *does*
# rather than by who published it. Two consecutive queues (issues #246-#255 and
# #256-#265) were 20/20 false positives of just three shapes: the matcher's
# bigrams come from the entity's *name* ("desarrollo pesquero", "gestion
# publica", "infraestructura educativa"), so every routine act of a topically
# relevant body carries them. Suppressing those phrases is not the answer —
# they are the meaningful ones; the act type is what's wrong.
#
# 1. Personnel. Deliberately narrow: only acts whose object is an individual
#    post. "Designan a los integrantes de la Comision Multisectorial encargada
#    de <compromiso>" creates the body that implements a commitment and can be
#    real evidence, so that one keeps its place in the queue.
#
#    The exception needs *both* halves. A collective noun alone is not enough:
#    "Designan miembros del Directorio del Banco Central de Reserva" is ordinary
#    churn on a standing board and reached the queue on `miembros` (issue #268).
#    A task body alone is not enough either: PROMPERU's registered name is
#    "Comision de Promocion del Peru para la Exportacion y el Turismo", so
#    "Designan Presidente Ejecutivo de la Comision de Promocion..." is an
#    ordinary appointment that any bare "comision" test would wave through.
#    Every noun and participle here is optionally plural. One resolution
#    routinely retires and appoints several people at once ("Aceptan renuncias
#    y designan funcionarios en diversos puestos…"), and a singular-only
#    pattern misses exactly those: `renuncia\b` cannot match "renuncias",
#    so issue #278 reached the queue while its singular twin was gated.
#
#    The gazette names the same act with a whole family of verbs, and the gate
#    only ever learned the ones that had burned it. Replaying 197 past
#    candidates through it left five that are plainly churn: both ends of a
#    single consular rotation — "Dan por terminadas las funciones de Consul
#    General del Peru en Orlando" (issue #52) and, two months later, "Nombran
#    Consul General del Peru en Orlando" (issue #289) — plus ONP's delegations
#    of signing authority to its own staff (issues #80, #81).
#
#    Each addition stays anchored to its object, because the bare verb is not
#    always routine: "dan por concluido" governs the *Regimen de Contingencia*
#    in issue #271, a substantive act, so the pattern requires a designacion or
#    funciones; and "delegan facultades" is the phrase for handing Congress's
#    legislative power to the Executive, so it counts only when delegated down
#    to an entity's own servidores or funcionarios.
_PERSONNEL_VERB_RE = re.compile(
    r"^(designan"
    r"|nombran"
    r"|proclaman"
    r"|aceptan (?:la |las )?renuncias?"
    r"|acreditan (?:la |las )?designacion(?:es)?"
    r"|formalizan (?:la |las )?designacion(?:es)?"
    r"|encargan"
    r"|dan por (?:concluidas?|terminadas?) (?:la |las )?"
    r"(?:designacion(?:es)?|funciones)"
    r"|dejan sin efecto (?:la |las )?designacion(?:es)?"
    r"|delegan (?:facultades|atribuciones)\b.{0,60}?"
    r"\b(?:servidores|funcionarios)"
    r")\b"
)
_COLLECTIVE_OBJECT_RE = re.compile(r"\b(integrantes|miembros|representantes|vocales)\b")

#    A body only counts as a *task* body when it was convened to do something.
#    "Grupo/mesa de trabajo" says so in the name; a bare "comision" does not —
#    CONADIS's standing "Comision Consultiva" matched both halves and slipped
#    through on it (issue #285), the same way the BCRP Directorio did. So a
#    comision or comite qualifies only when it is multisectorial, especial, or
#    described as encargada de something.
_TASK_BODY_RE = re.compile(
    r"\b(grupo de trabajo|mesa de trabajo"
    r"|comision multisectorial|comision especial|comite especial"
    r"|(?:comision|comite)\b.{0,60}?\bencargad)"
)

# 2. Travel and academic authorizations: an institutional permission slip.
_TRAVEL_RE = re.compile(r"\bautorizan\b.{0,40}\bviaje\b|\bestancia academica\b|\bpasantia\b")

# 3. Recurring numeric publications. Narrow on purpose — the statistical bodies
#    stay in scope (see AUTONOMOUS_SECTOR_RE), so only the periodic series
#    themselves are dropped, not everything those bodies publish.
_RECURRING_INDEX_RE = re.compile(r"\bindice de reajuste\b|\btipo de cambio\b")

# 4. Drafts. A prepublicacion, a proyecto put out for comment, or a consulta
#    publica is a text that is *not in force* — it cannot evidence a commitment
#    the government has yet to keep, and the same instrument returns as its own
#    candidate when it is finally enacted. Not one of the plan's 699 commitments
#    names a draft as its target. Issues #295, #302, #303 in one day, and
#    #128/#134/#139 before them.
_DRAFT_RE = re.compile(
    r"\bpre ?publicacion\b"
    r"|\b(?:publicacion|difusion)\b.{0,40}?\bproyecto\b"
    r"|\bconsulta publica\b"
)

# 5. Heritage declarations. Under Ley 28296 the Ministerio de Cultura declares
#    individual objects, archives and expressions Patrimonio Cultural de la
#    Nacion continuously — three landed in a single queue (issues #298-#300).
#    The one commitment that mentions patrimonio cultural (t3-2.P35) promises
#    *promocion de la economia naranja* and Escuelas Tecnicas, not the statutory
#    declarations themselves, so gating this class blinds nothing.
_HERITAGE_DECLARATION_RE = re.compile(r"^declaran\b.{0,80}?patrimonio cultural de la nacion")

# 6. SINAGERD emergency declarations. Deliberately *not* a blanket match on
#    "estado de emergencia": the plan promises one (t1-1.P18, a Plan de
#    Emergencia against inseguridad ciudadana via delegated legislative
#    powers), so a security emergency has to keep its place in the queue. Only
#    the Ley 29664 hazard formula is gated — INDECI/CENEPRED declarations for
#    peligro inminente or a desastre, which run monthly (issue #301, declared
#    for deficit hidrico across sixteen departments).
_HAZARD_RE = re.compile(r"\bpeligro inminente\b|\bdesastre\b|\bimpacto de danos\b")

# 7. University registry paperwork: a reissued diploma is not a policy act.
_ACADEMIC_PAPERWORK_RE = re.compile(r"\bduplicado de (?:diploma|grado|titulo)\b")

# 8. Extraditions. Judicial cooperation resolved case by case, ~22 in the first
#    month of archive — the single most frequent class left. No commitment in
#    the plan mentions extradition, so no extradition can evidence one; they
#    reached the queue on "ciudadano peruano" (issues #313, #314).
_EXTRADITION_RE = re.compile(r"\bextradicion\b")

# 9. A regulator deciding one case between named parties. INDECOPI declaring a
#    specific municipal ordinance an illegal barrera burocratica, OSIPTEL
#    ordering two firms to share a tower — statutory adjudication, not policy
#    (issues #318, #319, #326, #327).
#
#    The INDECOPI half needs the anchor. t1-3.P10 promises to reinforce exactly
#    this body's barreras-burocraticas role *otorgandole facultades* — new powers
#    for preventive supervision and random audits. A resolution declaring one
#    barrier illegal is that body using the powers it already has, which is the
#    EJE trap again: identical vocabulary, opposite meaning. Granting the powers
#    would arrive as a Decreto Legislativo or a Ley, which this pattern leaves
#    alone — there is a test for it.
_ADJUDICATION_RE = re.compile(
    r"^declaran barreras? burocratica"
    r"|\bmandato de comparticion\b"
)


def is_routine_act(record: dict) -> bool:
    """True for a norma whose operative act cannot evidence a commitment —
    personnel churn, a permission slip, a periodic index, a draft still out for
    comment, a statutory declaration, or hazard-management paperwork."""
    sumilla = fold(record.get("sumilla", ""))
    if _PERSONNEL_VERB_RE.match(sumilla) and not (
        _COLLECTIVE_OBJECT_RE.search(sumilla) and _TASK_BODY_RE.search(sumilla)
    ):
        return True
    if "estado de emergencia" in sumilla and _HAZARD_RE.search(sumilla):
        return True
    return bool(
        _TRAVEL_RE.search(sumilla)
        or _RECURRING_INDEX_RE.search(sumilla)
        or _DRAFT_RE.search(sumilla)
        or _HERITAGE_DECLARATION_RE.search(sumilla)
        or _ACADEMIC_PAPERWORK_RE.search(sumilla)
        or _EXTRADITION_RE.search(sumilla)
        or _ADJUDICATION_RE.search(sumilla)
    )


# Fetching and norma text live in common/elperuano_client.py; matching lives in
# common/matcher.py (shared). A norma's numero + tipo + sumilla is matched
# against the distinctive-phrase index built from the plan.


# ---- Issue body ---------------------------------------------------------------

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
        and is_norma_record(r)
        and not is_routine_act(r)
        and (rel := matcher.match(f"{r['numero']} {r['tipo']} {r['sumilla']}"))
    ]
    gated = sum(1 for r in records if in_national_scope(r) and is_routine_act(r))
    print(f"{iso_date}: {len(records)} normas, {gated} routine acts gated, {len(matched)} matched")

    if not matched:
        print("No matches; nothing to file.")
        return 0

    if not dry_run:
        ensure_label(repo, gh_token)

    created = 0
    ensured: set[str] = set()  # temas recur across a day's matches; one API check each
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
            if tl in ensured:
                continue
            ensure_label(repo, gh_token, name=tl, color="6B6F7B",
                         description=f"Compromisos del tema «{tl.split(':', 1)[1]}»")
            ensured.add(tl)
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
