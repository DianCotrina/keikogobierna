#!/usr/bin/env python3
"""Extract plan content from the official PDF into src/data/plan/.

Reads docs/Plan-de-Gobierno-Reforzado_V2.pdf via `pdftotext -layout`, parses the
23 topics (proposals + first-100-days actions), and writes:
  - src/data/plan/index.json
  - src/data/plan/topics/t{pillar}-{n}-{slug}.json  (x23)

Re-run any time the source PDF changes; output is deterministic (same input ->
byte-identical output).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PDF = ROOT / "docs" / "Plan-de-Gobierno-Reforzado_V2.pdf"
OUT_DIR = ROOT / "src" / "data" / "plan"
TOPICS_DIR = OUT_DIR / "topics"
GOALS_FILE = OUT_DIR / "goals" / "goals-2031.json"
OVERRIDES_FILE = OUT_DIR / "overrides.json"

EXPECTED = {  # doc_section -> expected proposal count (Global Constraints), RAW extraction
    "1.1": 43, "1.2": 13, "1.3": 15, "1.4": 17, "2.1": 43, "2.2": 17, "2.3": 23,
    "2.4": 34, "2.5": 26, "2.6": 41, "2.7": 38, "2.8": 16, "2.9": 15, "3.1": 62,
    "3.2": 42, "3.3": 39, "3.4": 12, "3.5": 28, "3.6": 20, "3.7": 21, "3.8": 19,
    "3.9": 12, "3.10": 39,
}
# POST-override (curated) expected proposal counts. Identical to EXPECTED except
# 3.7, where the curation-overrides mechanism merges 4 raw proposals (the bare
# "Programa Juntos:" label + its 3 mis-parsed sub-item fragments) into 1,
# dropping the topic's count from 21 to 18 (see src/data/plan/overrides.json).
EXPECTED_CURATED = {**EXPECTED, "3.7": 18}
EXPECTED_CIEN_OVERRIDES = {"1.1": 4, "1.2": 2, "1.3": 3, "1.4": 2, "3.10": 2}
EXPECTED_CIEN = {doc_section: EXPECTED_CIEN_OVERRIDES.get(doc_section, 3) for doc_section in EXPECTED}

TOPIC_ORDER = list(EXPECTED.keys())

# Document order matches Global Constraints slug list exactly.
SLUGS = {
    "1.1": "orden-ciudadano", "1.2": "lucha-contra-la-corrupcion", "1.3": "orden-economico",
    "1.4": "orden-juridico", "2.1": "emprendedores-mype", "2.2": "mineria",
    "2.3": "energia-e-hidrocarburos", "2.4": "agricultura", "2.5": "pesca-y-acuicultura",
    "2.6": "transportes-y-comunicaciones", "2.7": "turismo",
    "2.8": "industria-y-comercio-exterior", "2.9": "desarrollo-sostenible-o-ambiente",
    "3.1": "ninos-adolescentes-y-jovenes", "3.2": "educacion", "3.3": "salud",
    "3.4": "seguridad-alimentaria", "3.5": "vivienda", "3.6": "agua-y-saneamiento",
    "3.7": "pensiones", "3.8": "programas-sociales", "3.9": "deporte",
    "3.10": "peruanos-en-el-extranjero",
}

# Name casing per Global Constraints rule ("LUCHA CONTRA LA CORRUPCIÓN" ->
# "Lucha contra la corrupción" etc.); hardcoded verbatim to avoid heuristic
# drift on acronyms/parentheticals (e.g. "(MYPE)", the 3.10 renaming rule).
NAMES = {
    "1.1": "Orden ciudadano",
    "1.2": "Lucha contra la corrupción",
    "1.3": "Orden económico",
    "1.4": "Orden jurídico",
    "2.1": "Emprendedores (MYPE)",
    "2.2": "Minería",
    "2.3": "Energía e hidrocarburos",
    "2.4": "Agricultura",
    "2.5": "Pesca y acuicultura",
    "2.6": "Transportes y comunicaciones",
    "2.7": "Turismo",
    "2.8": "Industria y comercio exterior",
    "2.9": "Desarrollo sostenible o ambiente",
    "3.1": "Niños, adolescentes y jóvenes",
    "3.2": "Educación",
    "3.3": "Salud",
    "3.4": "Seguridad alimentaria",
    "3.5": "Vivienda",
    "3.6": "Agua y saneamiento",
    "3.7": "Pensiones",
    "3.8": "Programas sociales",
    "3.9": "Deporte",
    "3.10": "Peruanos en el extranjero (PEX)",
}

PILLAR_NAMES = {"p1": "Orden", "p2": "Económico", "p3": "Social"}

HEADING = re.compile(r"^\s*(\d\.\d{1,2})\.\s+([A-ZÁÉÍÓÚÑ][^\n]*)$")
SUB = re.compile(r"^\s*(\d)\.(\d{1,2})\.(\d)\.?\s")
BULLET = re.compile(r"^\s*•\s*(.*)$")
PAGENUM = re.compile(r"^\s*\d{1,3}\s*$")


def get_text() -> list[str]:
    out = subprocess.run(["pdftotext", "-layout", str(PDF), "-"],
                          capture_output=True, text=True, check=True).stdout
    return out.split("\f")[13:133]  # body pages only


def pillar_of(doc_section: str) -> str:
    return f"p{doc_section.split('.')[0]}"


def topic_id(doc_section: str) -> str:
    pillar, n = doc_section.split(".")
    return f"t{pillar}-{n}"


def flatten_lines(pages: list[str]) -> list[str]:
    """Concatenate all pages into one line stream, dropping each page's
    trailing footer (blank lines + page number) before the seam.

    A proposal can wrap across a page break with nothing but blank lines
    and a footer page-number between the last visible line and its
    continuation on the next page. If that footer noise were kept, a
    genuine mid-sentence continuation and a real paragraph break would look
    identical (blank line immediately before the next content line) and the
    group-title heuristic below could not tell them apart. Stripping the
    footer before the pages are joined removes that false separator, so the
    only blank lines left in the stream are real paragraph breaks.
    """
    lines: list[str] = []
    for page in pages:
        page_lines = page.split("\n")
        while page_lines and (not page_lines[-1].strip() or PAGENUM.match(page_lines[-1])):
            page_lines.pop()
        lines.extend(page_lines)
    return lines


def parse(pages: list[str]) -> dict:
    """Walk the flattened line stream once, tracking topic/subsection state."""
    topics: dict[str, dict] = {}
    current_topic = None
    mode = None  # None | 'diagnostico' | 'proposals' | 'cien' | 'metas'
    active_group = None
    pending_title = None
    boundary = True  # True right after a blank line / section transition
    current_item: list[str] | None = None
    current_item_target: list | None = None

    def finalize_item():
        nonlocal current_item, current_item_target
        if current_item is not None and current_item_target is not None:
            text = re.sub(r"\s+", " ", " ".join(current_item)).strip()
            if text:
                current_item_target.append(text)
        current_item = None
        current_item_target = None

    for raw_line in flatten_lines(pages):
        line = raw_line.rstrip()

        if PAGENUM.match(line):
            continue  # stray page-number line (footer already stripped at seams)

        if not line.strip():
            # A real paragraph break: closes whatever proposal was open and
            # marks the next content line as a group-title candidate.
            finalize_item()
            boundary = True
            continue

        if "....." in line:
            continue  # TOC leader artifact guard (defensive; not present in body)

        if re.match(r"^\s*Fuente:", line):
            continue  # citation line (relevant only inside ignored diagnostico)

        m = HEADING.match(line)
        if m and m.group(1) in EXPECTED:
            finalize_item()
            current_topic = m.group(1)
            topics.setdefault(current_topic, {"groups": [], "cien": []})
            mode = None
            active_group = None
            pending_title = None
            boundary = True
            continue

        m = SUB.match(line)
        if m and current_topic is not None:
            finalize_item()
            sub_num = m.group(3)
            # 3.6.2 typo inside topic 3.7: keep CURRENT topic regardless of the
            # heading's own topic prefix; only the subsection digit counts.
            if sub_num == "2":
                mode = "proposals"
                active_group = None
                pending_title = None
            elif sub_num == "3":
                mode = "cien"
            elif sub_num == "1":
                mode = "diagnostico"
            elif sub_num == "4":
                mode = "metas"
            else:
                mode = None
            boundary = True
            continue

        mb = BULLET.match(line)
        if mb and current_topic is not None and mode in ("proposals", "cien"):
            finalize_item()
            text0 = mb.group(1).strip()
            if mode == "proposals":
                if active_group is None:
                    active_group = {"title": pending_title, "proposals": []}
                    topics[current_topic]["groups"].append(active_group)
                    pending_title = None
                current_item = [text0]
                current_item_target = active_group["proposals"]
            else:
                current_item = [text0]
                current_item_target = topics[current_topic]["cien"]
            boundary = False
            continue

        # Plain content line: group-title candidate, continuation, or stray.
        if current_topic is not None and mode == "proposals" and boundary:
            candidate = line.strip()
            # Some group titles are wrapped in quotes in the document (e.g. the
            # seven program names in section 3.8.2: “Agua que Cuida la Vida”).
            # The quotes are typography, not content: strip a matching
            # surrounding pair so the first-letter-uppercase check sees the
            # actual title text, and store the title unquoted.
            if len(candidate) >= 2 and candidate[0] in "“\"" and candidate[-1] in "”\"":
                candidate = candidate[1:-1].strip()
            if (candidate and len(candidate) < 90
                    and not candidate.endswith(".")
                    and not candidate.endswith(",")
                    and candidate[0].isupper()):
                pending_title = candidate
                active_group = None
                continue
            # else: stray non-title line right after a paragraph break
            # (e.g. leading text before the first group); ignore.
            continue

        if current_topic is not None and mode in ("proposals", "cien") and current_item is not None:
            current_item.append(line.strip())
            continue

        # else: outside proposals/cien (diagnostico/metas/none), or a stray
        # line with no open item to continue; ignore.

    finalize_item()
    return topics


def load_overrides() -> list[dict]:
    """Read the hand-written curation rules (committed, English identifiers).

    See src/data/plan/overrides.json for the contract and Plan B's shared
    context for the exact rule semantics.
    """
    data = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
    return data["rules"]


def _override_fail(message: str) -> None:
    print(f"FAIL: override error: {message}", file=sys.stderr)
    sys.exit(1)


def _apply_merge_bullets(topics: dict, rule: dict) -> None:
    """Merge `merge_count` consecutive raw proposals (an anchor label + its
    following mis-parsed sub-item fragments) into a single proposal, in place,
    at the anchor's original position.
    """
    topic = rule["topic"]
    anchor = rule["anchor_starts_with"]
    merge_count = rule["merge_count"]
    join_with = rule["join_with"]

    groups = topics.get(topic, {}).get("groups", [])
    flat = [(g_idx, p_idx, text)
            for g_idx, g in enumerate(groups)
            for p_idx, text in enumerate(g["proposals"])]

    # A "bare label" match: the proposal text starts with the anchor AND
    # nothing meaningful follows it (i.e. the whole proposal IS the label).
    # A plain substring/prefix test is not enough here: this same topic also
    # has a fully-formed, unrelated proposal that happens to start with the
    # identical label text (e.g. "Programa Juntos: aumento de S/ 200 a S/
    # 400 ..."), which is a complete proposal, not a mis-split label -- it
    # must NOT match.
    matches = [i for i, (_, _, text) in enumerate(flat)
               if text.startswith(anchor) and text[len(anchor):].strip() == ""]
    if len(matches) != 1:
        _override_fail(f"merge_bullets topic {topic}: anchor {anchor!r} (bare-label match) "
                        f"matched {len(matches)} proposals (expected exactly 1).")

    start = matches[0]
    if start + merge_count > len(flat):
        _override_fail(f"merge_bullets topic {topic}: only {len(flat) - start} "
                        f"proposals available after anchor {anchor!r}, need {merge_count}.")

    window = flat[start:start + merge_count]
    g_indices = {g_idx for g_idx, _, _ in window}
    if len(g_indices) != 1:
        _override_fail(f"merge_bullets topic {topic}: anchor window spans multiple "
                        f"groups; not supported.")

    g_idx = next(iter(g_indices))
    p_indices = sorted(p_idx for _, p_idx, _ in window)
    if p_indices != list(range(p_indices[0], p_indices[0] + merge_count)):
        _override_fail(f"merge_bullets topic {topic}: matched proposals are not "
                        f"contiguous within their group.")

    fragments = [text for _, _, text in window]
    label, *following = fragments
    if following:
        stripped = [f[:-1] if f.endswith(".") else f for f in following[:-1]]
        stripped.append(following[-1])
        joined = join_with.join(stripped)
        merged_text = f"{label} {joined}" if label.endswith(":") else f"{label}{join_with}{joined}"
    else:
        merged_text = label

    g = groups[g_idx]
    start_p = p_indices[0]
    g["proposals"] = g["proposals"][:start_p] + [merged_text] + g["proposals"][start_p + merge_count:]


def _apply_split_trailing_group_header(topics: dict, rule: dict) -> None:
    """Split a proposal whose text has a section header glued onto its end
    (missing blank line in the PDF text layer) into: the truncated proposal,
    plus a new group (titled `header`) that absorbs the rest of the original
    group's subsequent proposals.
    """
    topic = rule["topic"]
    suffix = rule["proposal_ends_with"]
    header = rule["header"]

    groups = topics.get(topic, {}).get("groups", [])
    matches = [(g_idx, p_idx)
               for g_idx, g in enumerate(groups)
               for p_idx, text in enumerate(g["proposals"])
               if text.endswith(suffix)]

    if len(matches) != 1:
        _override_fail(f"split_trailing_group_header topic {topic}: suffix "
                        f"{suffix!r} matched {len(matches)} proposals (expected exactly 1).")

    g_idx, p_idx = matches[0]
    g = groups[g_idx]
    text = g["proposals"][p_idx]
    glued = f" {header}"
    if not text.endswith(glued):
        _override_fail(f"split_trailing_group_header topic {topic}: matched proposal "
                        f"does not end with {glued!r}.")

    truncated = text[:-len(glued)]
    if not truncated.endswith("."):
        _override_fail(f"split_trailing_group_header topic {topic}: truncated text "
                        f"does not end with a period: {truncated!r}")

    moved = g["proposals"][p_idx + 1:]
    g["proposals"] = g["proposals"][:p_idx] + [truncated]
    groups.insert(g_idx + 1, {"title": header, "proposals": moved})


_OVERRIDE_HANDLERS = {
    "merge_bullets": _apply_merge_bullets,
    "split_trailing_group_header": _apply_split_trailing_group_header,
}


def apply_overrides(topics: dict, rules: list[dict]) -> None:
    """Apply curation rules in file order, after the raw gate and before ID
    assignment (so ordinals come out compact). Mutates `topics` in place.
    Unknown rule types, or rules matching zero/multiple times, are hard
    errors -- silent no-ops are forbidden.
    """
    for rule in rules:
        rtype = rule.get("type")
        handler = _OVERRIDE_HANDLERS.get(rtype)
        if handler is None:
            _override_fail(f"unknown rule type {rtype!r}")
        handler(topics, rule)


def load_goal_counts() -> dict[str, int]:
    """Read curated goals-2031.json (Task 2, hand-curated from the PDF's
    metas tables) and count goals per topic id.

    The metas tables are column-mangled by `pdftotext -layout` and are not
    machine-parseable (see Global Constraints), so this extractor cannot
    derive goal counts from the PDF text itself. If the curated file is
    absent (e.g. before Task 2 has run), every topic's count is 0 -- the
    same placeholder Task 1 always wrote. If present, re-running this
    extractor must not clobber Task 2's curation work, so counts are read
    back from that file instead of being reset to 0.
    """
    if not GOALS_FILE.exists():
        return {}
    data = json.loads(GOALS_FILE.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for goal in data.get("goals", []):
        counts[goal["topic"]] = counts.get(goal["topic"], 0) + 1
    return counts


def build_output(topics: dict) -> tuple[dict, dict]:
    """Return (index_dict, {doc_section: topic_file_dict})."""
    goal_counts = load_goal_counts()
    index = {
        "plan": {
            "name": "Perú con Orden",
            "period": "2026–2031",
            "party": "Fuerza Popular",
            "source_pdf": "docs/Plan-de-Gobierno-Reforzado_V2.pdf",
        },
        "pillars": [{"id": pid, "name": name} for pid, name in PILLAR_NAMES.items()],
        "topics": [],
    }
    topic_files = {}

    for doc_section in TOPIC_ORDER:
        topic = topics.get(doc_section, {"groups": [], "cien": []})
        tid = topic_id(doc_section)
        slug = SLUGS[doc_section]
        name = NAMES[doc_section]
        pillar = pillar_of(doc_section)

        groups_out = []
        proposal_count = 0
        for group in topic["groups"]:
            props_out = []
            for text in group["proposals"]:
                proposal_count += 1
                props_out.append({"id": f"{tid}.P{proposal_count:02d}", "text": text})
            groups_out.append({"title": group["title"], "proposals": props_out})

        cien_out = [{"id": f"{tid}.C{i:02d}", "text": text}
                    for i, text in enumerate(topic["cien"], start=1)]

        index["topics"].append({
            "id": tid, "slug": slug, "name": name, "pillar": pillar, "doc_section": doc_section,
            "proposals": proposal_count, "first_100_days": len(cien_out),
            "goals": goal_counts.get(tid, 0),
        })

        topic_files[doc_section] = {
            "id": tid, "slug": slug, "name": name, "pillar": pillar, "doc_section": doc_section,
            "groups": groups_out, "first_100_days": cien_out,
        }

    return index, topic_files


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _check_gate(label: str, get_counts, expected_prop: dict, expected_total_prop: int) -> bool:
    """Print a proposal/100-days count table against an expected table and
    return whether every row (plus totals) matches. `get_counts(doc_section)`
    returns (proposal_count, cien_count) for that topic.
    """
    ok = True
    print(f"\n{label} gate")
    print(f"{'topic':<6} {'proposals':>10} {'expected':>8}  {'100days':>7} {'expected':>8}")
    total_prop = total_prop_exp = total_cien = total_cien_exp = 0
    for doc_section in TOPIC_ORDER:
        got_prop, got_cien = get_counts(doc_section)
        exp_prop = expected_prop[doc_section]
        exp_cien = EXPECTED_CIEN[doc_section]
        mark = "OK" if (got_prop == exp_prop and got_cien == exp_cien) else "MISMATCH"
        if mark == "MISMATCH":
            ok = False
        print(f"{doc_section:<6} {got_prop:>10} {exp_prop:>8}  {got_cien:>7} {exp_cien:>8}  {mark}")
        total_prop += got_prop
        total_prop_exp += exp_prop
        total_cien += got_cien
        total_cien_exp += exp_cien

    print(f"\nTOTAL proposals ({label.lower()}): {total_prop} (expected {total_prop_exp})")
    print(f"TOTAL 100 days:              {total_cien} (expected {total_cien_exp})")
    if label == "RAW":
        print(f"TOTAL topics:                {len(TOPIC_ORDER)} (expected 23)")
        ok = ok and len(TOPIC_ORDER) == 23

    if not ok or total_prop != expected_total_prop or total_cien != 67:
        print(f"\nFAIL: {label} counts do not match expected ground truth.")
        return False

    print(f"\nOK: {label} counts match.")
    return True


def main() -> int:
    pages = get_text()
    topics = parse(pages)

    def raw_counts(doc_section: str) -> tuple[int, int]:
        topic = topics.get(doc_section, {"groups": [], "cien": []})
        prop = sum(len(g["proposals"]) for g in topic["groups"])
        return prop, len(topic["cien"])

    if not _check_gate("RAW", raw_counts, EXPECTED, 635):
        return 1

    rules = load_overrides()
    apply_overrides(topics, rules)

    index, topic_files = build_output(topics)

    def curated_counts(doc_section: str) -> tuple[int, int]:
        entry = topic_files[doc_section]
        prop = sum(len(g["proposals"]) for g in entry["groups"])
        return prop, len(entry["first_100_days"])

    # Curated gate runs BEFORE any file is written: a bad override (or a
    # tampered rule) must never clobber the last-known-good output on disk
    # with mismatched data, even though it exits 1.
    if not _check_gate("CURATED", curated_counts, EXPECTED_CURATED, 632):
        return 1

    write_json(OUT_DIR / "index.json", index)
    for doc_section in TOPIC_ORDER:
        tid = topic_id(doc_section)
        slug = SLUGS[doc_section]
        write_json(TOPICS_DIR / f"{tid}-{slug}.json", topic_files[doc_section])

    print("\nOK: all counts match (raw + curated).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
