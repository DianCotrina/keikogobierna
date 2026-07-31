#!/usr/bin/env python3
"""Validate the src/data/cabinet/ tree.

These files name living people and describe criminal proceedings against them,
so the rules here are deliberately strict. The one that matters most: every
judicial entry must carry at least one https source. Publishing an unsourced
accusation is a build failure, not a matter of editorial discipline.

`validate()` returns a list of error strings so it can be unit-tested; `main()`
loads the real files and exits non-zero on the first failing run.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CABINET_DIR = ROOT / "src" / "data" / "cabinet"
PORTFOLIOS_PATH = CABINET_DIR / "portfolios.json"
MINISTERS_PATH = CABINET_DIR / "ministers.json"
TENURES_PATH = CABINET_DIR / "tenures.json"
ANNOUNCEMENTS_PATH = CABINET_DIR / "announcements.json"
PLAN_INDEX_PATH = ROOT / "src" / "data" / "plan" / "index.json"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Keep in sync with STAGES in src/lib/judicial.mjs.
VALID_STAGES = {
    "sentencia_firme", "sentencia_no_firme", "juicio_oral", "acusacion_fiscal",
    "investigacion_preparatoria", "investigacion_preliminar",
    "absuelto", "archivado", "prescrito",
}
VALID_SOURCE_KINDS = {"primary", "press"}


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"FAIL: cannot read/parse {path}: {e}")
        sys.exit(1)


def load_all():
    portfolios = load_json(PORTFOLIOS_PATH)["portfolios"]
    ministers = load_json(MINISTERS_PATH)["ministers"]
    tenures = load_json(TENURES_PATH)["tenures"]
    announcements = load_json(ANNOUNCEMENTS_PATH)["announcements"]
    topic_ids = {t["id"] for t in load_json(PLAN_INDEX_PATH)["topics"]}
    return portfolios, ministers, tenures, topic_ids, announcements


def _check_sources(sources, where: str, errors: list) -> None:
    if not isinstance(sources, list) or not sources:
        errors.append(f"{where}: needs at least one source")
        return
    for i, source in enumerate(sources):
        url = (source or {}).get("url", "")
        if not isinstance(url, str) or not url.startswith("https://"):
            errors.append(f"{where}: sources[{i}].url must be https, got '{url}'")
        if (source or {}).get("kind") not in VALID_SOURCE_KINDS:
            errors.append(f"{where}: sources[{i}].kind must be primary or press")
        if not (source or {}).get("label"):
            errors.append(f"{where}: sources[{i}] needs a label")


def _check_date(value, where: str, errors: list, today: str, allow_future: bool = False) -> bool:
    """Validate an ISO date.

    `allow_future` is on for tenures: an appointment norma is published with an
    effective date, so a tenure legitimately starts tomorrow. It stays off for
    judicial entries, where a future date would mean a ruling that has not
    happened yet.
    """
    if not isinstance(value, str) or not DATE_RE.match(value):
        errors.append(f"{where}: date must be YYYY-MM-DD, got '{value}'")
        return False
    if not allow_future and value > today:
        errors.append(f"{where}: date '{value}' is in the future")
        return False
    return True


def validate(portfolios, ministers, tenures, topic_ids, announcements=None, today=None) -> list:
    today = today or date.today().isoformat()
    announcements = announcements or []
    errors: list = []

    # ---- portfolios: a frozen registry -------------------------------------
    seen_portfolios = set()
    for portfolio in portfolios:
        pid = portfolio.get("id")
        if pid in seen_portfolios:
            errors.append(f"portfolios: duplicate id '{pid}'")
        seen_portfolios.add(pid)
        for key in ("id", "name", "short", "slug"):
            if not portfolio.get(key):
                errors.append(f"portfolios[{pid}]: missing '{key}'")
        for topic in portfolio.get("topics", []):
            if topic not in topic_ids:
                errors.append(f"portfolios[{pid}]: topic '{topic}' is not a plan topic id")

    # ---- ministers: the dossiers -------------------------------------------
    seen_ministers = set()
    for person in ministers:
        slug = person.get("slug")
        where = f"ministers[{slug}]"
        if slug in seen_ministers:
            errors.append(f"ministers: duplicate slug '{slug}'")
        seen_ministers.add(slug)
        if not person.get("name"):
            errors.append(f"{where}: missing 'name'")

        seen_entries = set()
        for entry in person.get("judicial", []):
            eid = entry.get("id")
            ewhere = f"{where}.judicial[{eid}]"
            if eid in seen_entries:
                errors.append(f"{ewhere}: duplicate entry id '{eid}'")
            seen_entries.add(eid)
            if entry.get("stage") not in VALID_STAGES:
                errors.append(f"{ewhere}: unknown stage '{entry.get('stage')}'")
            for key in ("case", "crime", "summary"):
                if not entry.get(key):
                    errors.append(f"{ewhere}: missing '{key}'")
            _check_date(entry.get("date"), ewhere, errors, today)
            _check_sources(entry.get("sources"), ewhere, errors)

    # ---- tenures: the living state -----------------------------------------
    by_portfolio: dict = {}
    for i, tenure in enumerate(tenures):
        where = f"tenures[{i}]"
        person_slug = tenure.get("person")
        portfolio_id = tenure.get("portfolio")
        if person_slug not in seen_ministers:
            errors.append(f"{where}: person '{person_slug}' has no entry in ministers.json")
        if portfolio_id not in seen_portfolios:
            errors.append(f"{where}: portfolio '{portfolio_id}' is not a known portfolio")

        start_ok = _check_date(tenure.get("start"), f"{where}.start", errors, today, allow_future=True)
        end = tenure.get("end")
        if end is not None:
            if _check_date(end, f"{where}.end", errors, today, allow_future=True) and start_ok:
                if end < tenure["start"]:
                    errors.append(f"{where}: end '{end}' precedes start '{tenure['start']}'")

        # Provenance is mandatory: a tenure exists because the gazette says so.
        norma = tenure.get("appointment_norma")
        if not norma or not norma.get("url"):
            errors.append(f"{where}: appointment_norma with a url is required")
        elif not str(norma["url"]).startswith("https://"):
            errors.append(f"{where}: appointment_norma.url must be https")

        by_portfolio.setdefault(portfolio_id, []).append(tenure)

    for portfolio_id, rows in by_portfolio.items():
        if sum(1 for t in rows if t.get("end") is None) > 1:
            errors.append(f"tenures: portfolio '{portfolio_id}' has more than one open tenure")
        # Half-open intervals: a successor may start the day the predecessor ends.
        datable = [t for t in rows if isinstance(t.get("start"), str)]
        for a, b in ((a, b) for i, a in enumerate(datable) for b in datable[i + 1:]):
            a_end = a.get("end") or "9999-12-31"
            b_end = b.get("end") or "9999-12-31"
            if a["start"] < b_end and b["start"] < a_end:
                errors.append(
                    f"tenures: portfolio '{portfolio_id}' has overlapping tenures "
                    f"({a.get('person')} and {b.get('person')})")

    # ---- announcements: provisional, and always subordinate to the gazette --
    open_portfolios = {t.get("portfolio") for t in tenures if t.get("end") is None}
    seen_announced = set()
    for i, item in enumerate(announcements):
        where = f"announcements[{i}]"
        portfolio_id = item.get("portfolio")

        if portfolio_id in seen_announced:
            errors.append(f"{where}: duplicate announcement for portfolio '{portfolio_id}'")
        seen_announced.add(portfolio_id)

        if portfolio_id not in seen_portfolios:
            errors.append(f"{where}: portfolio '{portfolio_id}' is not a known portfolio")
        if not item.get("person_name"):
            errors.append(f"{where}: person_name is required")
        # Optional: set by hand once someone confirmed the reported name is
        # that ficha. A name match is not an identity match.
        linked = item.get("person")
        if linked is not None and linked not in seen_ministers:
            errors.append(f"{where}: person '{linked}' has no entry in ministers.json")
        _check_date(item.get("announced"), f"{where}.announced", errors, today)
        _check_sources(item.get("sources"), where, errors)

        # An announcement is a press report. Anything certified by the gazette
        # belongs in tenures.json, where provenance is enforced properly.
        for j, source in enumerate(item.get("sources") or []):
            if (source or {}).get("kind") != "press":
                errors.append(f"{where}: sources[{j}].kind must be press for an announcement")

        # Once the norma publishes, the provisional entry must be removed rather
        # than left to contradict the certified record.
        if portfolio_id in open_portfolios:
            errors.append(
                f"{where}: portfolio '{portfolio_id}' already has an open tenure — "
                f"the announcement is superseded and should be deleted")

    return errors


def main() -> None:
    portfolios, ministers, tenures, topic_ids, announcements = load_all()
    errors = validate(portfolios, ministers, tenures, topic_ids, announcements)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        sys.exit(1)
    serving = sum(1 for t in tenures if t.get("end") is None)
    print(f"OK: cabinet/ valid — {len(portfolios)} portfolios, {len(ministers)} ministers, "
          f"{len(tenures)} tenures ({serving} serving), {len(announcements)} anunciados")


if __name__ == "__main__":
    main()
