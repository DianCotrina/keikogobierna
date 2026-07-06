# Real Plan Data Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the real "Perú con Orden 2026–2031" government plan (3 pilares, 23 temas, 635 propuestas, 67 acciones de 100 días, ~60 metas al 2031) from the official PDF into versioned, validated JSON with stable IDs, plus a seguimiento (tracking) layer — the data foundation both the current site and the upcoming Astro migration consume.

**Architecture:** Immutable plan content (what the document says) lives in `src/data/plan/` — extracted by a repeatable WAT tool, never hand-edited after curation. Living tracking state (estado/evidencia per item) lives in `src/data/seguimiento.json`, keyed by stable IDs. Two-layer tracking: all 635 propuestas are listed and trackable, but headline progress % is computed only from metas al 2031. The existing landing page and `src/data/plan.json` stay untouched (Plan 2 — Astro migration — replaces them).

**Tech Stack:** Python 3 stdlib only (tools), `pdftotext` (poppler, already installed at /opt/homebrew/bin/pdftotext), JSON.

## Global Constraints

- Source of truth: `docs/Plan-de-Gobierno-Reforzado_V2.pdf`. Text extraction command: `pdftotext -layout docs/Plan-de-Gobierno-Reforzado_V2.pdf <out>`. The extracted text has 145 form-feed-separated pages; body content is pages 14–133 (0-indexed 13–132).
- All user-facing strings (nombres, propuestas, metas) in Spanish exactly as the document says; code identifiers/comments/commits in English.
- Python 3 stdlib only; no npm packages; no new JS in this plan.
- Stable ID scheme (never changes once assigned): temas `t{pilar}-{n}` (e.g. `t1-1`), propuestas `{tema}.P{nn}` (e.g. `t1-1.P07`, ordinal within tema, zero-padded 2 digits), acciones 100 días `{tema}.C{nn}`, metas `{tema}.M{nn}`.
- Estado vocabulary unchanged: `cumplida | en_progreso | sin_avance | incumplida`.
- Expected totals (verified against the PDF by prior analysis — the extractor must reproduce them): 3 pilares, 23 temas, 635 propuestas, 67 acciones de 100 días. Per-tema propuesta counts: t1-1:43 t1-2:13 t1-3:15 t1-4:17 t2-1:43 t2-2:17 t2-3:23 t2-4:34 t2-5:26 t2-6:41 t2-7:38 t2-8:16 t2-9:15 t3-1:62 t3-2:42 t3-3:39 t3-4:12 t3-5:28 t3-6:20 t3-7:21 t3-8:19 t3-9:12 t3-10:39.
- Known document quirks the parser must handle: tema 3.7 contains a typo'd subsection heading `3.6.2. Nuestras propuestas` (belongs to 3.7); bullets are `•` and continuation lines are indented without bullet; sub-group headers inside "Nuestras propuestas" are non-bulleted title lines (e.g. "Simplificación administrativa"); metas tables are column-mangled by `-layout` and are NOT reliably machine-parseable — they are curated by hand (Task 3), not parsed.
- Stage only files each task touches; never `git add -A`. Commit messages end with: Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
- Work on branch `plan-data` created from `modular-architecture` (PR #1 not yet merged; this stacks on it).

## File Structure

```
tools/
├── extract_plan_pdf.py        # WAT tool: PDF text → index.json + 23 tema JSONs (propuestas + 100 días)
└── validate_plan_data.py      # extended: validates plan/ tree + seguimiento cross-refs (keeps old plan.json checks)
src/data/plan/
├── index.json                 # registry: pilares + temas (id, slug, nombre, pilar, counts)
├── temas/
│   └── t1-1-orden-ciudadano.json   # ×23
└── metas/
    └── metas-2031.json        # curated metas al 2031 (all temas, one file)
src/data/seguimiento.json      # tracking state, seeded sin_avance
docs/superpowers/plans/…       # this plan
```

### Data contracts (all tasks share these)

`src/data/plan/index.json`:
```json
{
  "plan": { "nombre": "Perú con Orden", "periodo": "2026–2031", "partido": "Fuerza Popular", "fuente_pdf": "docs/Plan-de-Gobierno-Reforzado_V2.pdf" },
  "pilares": [ { "id": "p1", "nombre": "Orden" }, { "id": "p2", "nombre": "Económico" }, { "id": "p3", "nombre": "Social" } ],
  "temas": [ { "id": "t1-1", "slug": "orden-ciudadano", "nombre": "Orden ciudadano", "pilar": "p1", "num_doc": "1.1", "propuestas": 43, "cien_dias": 4, "metas": 0 } ]
}
```
(`metas` counts filled by Task 3; Task 1 writes 0.)

`src/data/plan/temas/t1-1-orden-ciudadano.json`:
```json
{
  "id": "t1-1", "slug": "orden-ciudadano", "nombre": "Orden ciudadano", "pilar": "p1", "num_doc": "1.1",
  "grupos": [ { "titulo": "Control, Prevención y Fortalecimiento Institucional", "propuestas": [ { "id": "t1-1.P01", "texto": "…" } ] } ],
  "primeros_100_dias": [ { "id": "t1-1.C01", "texto": "…" } ]
}
```
(`grupos[].titulo` may be `null` for a leading ungrouped run of bullets. Propuesta ordinals are global within the tema across grupos, in document order.)

`src/data/plan/metas/metas-2031.json`:
```json
{ "metas": [ { "id": "t1-1.M01", "tema": "t1-1", "texto": "Implementar un Centro Nacional de Comando y Videovigilancia (C5i) en las 24 regiones del país.", "indicador": "Número de regiones con C5i operativo e interconectado", "tema_tabla": "Combate y control del crimen organizado." } ] }
```

`src/data/seguimiento.json`:
```json
{
  "actualizado": "2026-07-06",
  "items": { "t1-1.M01": { "estado": "sin_avance", "evidencias": [] } },
  "registro": []
}
```
(`items` seeded ONLY for metas — the headline layer. Propuestas get added here lazily when their estado first changes; absent id ⇒ `sin_avance` by default. `registro` entries: `{ "fecha": "YYYY-MM-DD", "item": "t1-1.M01", "estado": "en_progreso", "texto": "…", "fuente_url": "…" }`.)

Slugs: lowercase ASCII (strip accents), hyphens: orden-ciudadano, lucha-contra-la-corrupcion, orden-economico, orden-juridico, emprendedores-mype, mineria, energia-e-hidrocarburos, agricultura, pesca-y-acuicultura, transportes-y-comunicaciones, turismo, industria-y-comercio-exterior, desarrollo-sostenible-o-ambiente, ninos-adolescentes-y-jovenes, educacion, salud, seguridad-alimentaria, vivienda, agua-y-saneamiento, pensiones, programas-sociales, deporte, peruanos-en-el-extranjero.

Nombre casing: convert the document's ALL-CAPS heading to sentence case with proper accents kept (e.g. "LUCHA CONTRA LA CORRUPCIÓN" → "Lucha contra la corrupción"; "EMPRENDEDORES (MYPE)" → "Emprendedores (MYPE)"; "PERUANOS EN EL EXTRANJERO – PEX Y POLÍTICA" → "Peruanos en el extranjero (PEX)").

---

### Task 1: Extractor tool — `tools/extract_plan_pdf.py`

**Files:**
- Create: `tools/extract_plan_pdf.py`
- Create (generated): `src/data/plan/index.json`, `src/data/plan/temas/*.json` (23 files)

**Interfaces:**
- Produces: the index.json and tema-file contracts above.
- CLI: `python3 tools/extract_plan_pdf.py` (re)generates all output files deterministically; prints a per-tema count table and totals; exits 1 if totals ≠ expected constants.

Parsing skeleton (proven against the actual text; use as the starting point, iterate as needed):

```python
#!/usr/bin/env python3
"""Extract plan content from the official PDF into src/data/plan/."""
import json, re, subprocess, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "docs" / "Plan-de-Gobierno-Reforzado_V2.pdf"

EXPECTED = {  # tema num_doc -> expected propuesta count (Global Constraints)
  "1.1": 43, "1.2": 13, "1.3": 15, "1.4": 17, "2.1": 43, "2.2": 17, "2.3": 23,
  "2.4": 34, "2.5": 26, "2.6": 41, "2.7": 38, "2.8": 16, "2.9": 15, "3.1": 62,
  "3.2": 42, "3.3": 39, "3.4": 12, "3.5": 28, "3.6": 20, "3.7": 21, "3.8": 19,
  "3.9": 12, "3.10": 39,
}
EXPECTED_CIEN = {"1.1": 4, "1.2": 2, "1.3": 3, "1.4": 2, "3.10": 2}  # default 3 otherwise

HEADING = re.compile(r"^\s*(\d\.\d{1,2})\.\s+([A-ZÁÉÍÓÚÑ][^\n]*)$")
SUB = re.compile(r"^\s*\d\.\d{1,2}\.(\d)\.?\s")
BULLET = re.compile(r"^\s*•\s*(.*)$")

def get_text() -> list[str]:
    out = subprocess.run(["pdftotext", "-layout", str(PDF), "-"],
                         capture_output=True, text=True, check=True).stdout
    return out.split("\f")[13:133]  # body pages only
```

Parser requirements beyond the skeleton (implement inside the tool):
- Track current tema via HEADING matches (skip lines containing `.....` — TOC artifacts). Track current subsection via SUB (`1`=diagnóstico ignored, `2`=propuestas, `3`=100 días, `4`=metas ignored). The `3.6.2` typo inside tema 3.7: when a SUB heading's tema prefix ≠ current tema, keep the CURRENT tema (only the subsection number counts).
- Bullet assembly: a BULLET line starts a new item; subsequent non-bullet, non-heading, non-empty lines are continuations — join with a single space, collapse internal whitespace (`re.sub(r"\s+", " ", …)`). Stop a propuesta at the next bullet, sub-group title, SUB heading, HEADING, or page break where the next page starts with a heading. Strip trailing whitespace.
- Sub-group titles: inside subsection 2, a non-bullet line that (a) is not a continuation (i.e., appears after a completed bullet followed by a blank line, or before the first bullet), (b) is shorter than 90 chars, (c) does not end with `.` or `,`, and (d) starts with an uppercase letter — treat as a new grupo título. Everything before the first grupo título goes in a grupo with `"titulo": null`. This heuristic will need iteration: verify grupo titles against the document for at least temas 1.1, 2.1, 3.1 during development.
- Exclusions: skip lines matching `^\s*Fuente:` and URL-continuation lines inside diagnostico (subsection 1 is ignored anyway); skip standalone page-number lines (`^\s*\d{1,3}\s*$`).
- Determinism: same input ⇒ byte-identical output (sort nothing by hash; preserve document order; `json.dump(..., ensure_ascii=False, indent=2)` + trailing newline).
- Self-check: after writing, compare per-tema propuesta counts and cien_dias counts against EXPECTED/EXPECTED_CIEN; print a table; exit 1 on any mismatch (this is the acceptance gate — do NOT relax the constants to make it pass; fix the parser).

- [ ] **Step 1: Write the tool** (skeleton above + requirements)
- [ ] **Step 2: Run it** — `python3 tools/extract_plan_pdf.py`; iterate on the parser until the count table matches EXPECTED exactly and exit code is 0
- [ ] **Step 3: Spot-verify content quality** — print and read propuestas t1-1.P01–P05, t2-1.P01–P03, t3-10.P37–P39 (last tema, last items) and confirm against the PDF text that they are complete sentences, no mid-sentence truncation, no glued page artifacts; confirm grupo titles for tema 1.3 include "Simplificación administrativa"
- [ ] **Step 4: Verify determinism** — run twice, `git diff --stat src/data/plan/` between runs must be empty
- [ ] **Step 5: Commit**

```bash
git add tools/extract_plan_pdf.py src/data/plan/index.json src/data/plan/temas
git commit -m "feat: extract real plan data (23 temas, 635 propuestas) from official PDF"
```

---

### Task 2: Curate metas al 2031 — `src/data/plan/metas/metas-2031.json`

**Files:**
- Create: `src/data/plan/metas/metas-2031.json`
- Modify: `src/data/plan/index.json` (fill per-tema `metas` counts — rerunning the extractor must NOT overwrite them: extractor reads existing metas file if present to fill counts; add that to the tool if not already handled)

**Interfaces:**
- Produces: the metas-2031.json contract above. Every tema has ≥1 meta. IDs `t{p}-{n}.M{nn}` in table order.

The metas tables (subsection X.Y.4 of each tema) are column-mangled in the text extraction and CANNOT be machine-parsed reliably. Curate them by reading the PDF pages directly (Read tool with `pages`, the table pages per tema are: 1.1→p20-21, 1.2→p23, 1.3→p26, 1.4→p29-30, 2.1→p38, 2.2→p42-43, 2.3→p48, 2.4→p54, 2.5→p59-60, 2.6→p66, 2.7→p70-71, 2.8→p73-74, 2.9→p78, 3.1→p86-87, 3.2→p95, 3.3→p101, 3.4→p105-106, 3.5→p111, 3.6→p115-116, 3.7→p118-119, 3.8→p121-122, 3.9→p125-126, 3.10→p132-133 — these are text-page indexes; the PDF page numbers match the extracted page sequence).

- [ ] **Step 1: For each of the 23 temas, read its metas table from the PDF and transcribe rows** into metas-2031.json — each row: `tema_tabla` (the TEMA column label), `texto` (META AL 2031 column, full sentence), `indicador` (INDICADOR column). Expect 2–4 rows per tema, ~55–70 total.
- [ ] **Step 2: Update index.json metas counts** (and extractor if needed per Interfaces note)
- [ ] **Step 3: Sanity check** — `python3 -c "import json;d=json.load(open('src/data/plan/metas/metas-2031.json'));print(len(d['metas']),'metas');import collections;print(collections.Counter(m['tema'] for m in d['metas']))"` — every tema present, no tema with 0
- [ ] **Step 4: Commit**

```bash
git add src/data/plan/metas/metas-2031.json src/data/plan/index.json tools/extract_plan_pdf.py
git commit -m "feat: curate metas al 2031 with indicators for all 23 temas"
```

---

### Task 3: Seguimiento layer + validator extension

**Files:**
- Create: `src/data/seguimiento.json` (seeded: every meta id, `estado: "sin_avance"`, empty evidencias; `registro: []`; `actualizado` = today)
- Modify: `tools/validate_plan_data.py`

**Interfaces:**
- Validator validates BOTH the legacy `src/data/plan.json` (existing checks unchanged — landing still uses it until Plan 2) AND the new tree:
  - index.json: 3 pilares, 23 temas, every tema's `pilar` exists, slugs unique, counts match the actual tema files and metas file
  - every tema file: ids well-formed and prefixed by the tema id, ordinals contiguous from 01, texto non-empty, grupo structure valid
  - metas file: ids well-formed, every `tema` exists, ≥1 meta per tema
  - seguimiento.json: every `items` key and every `registro[].item` references an existing propuesta/meta/cien-días id; estados in the canonical set; `registro[].fecha` matches `YYYY-MM-DD`
  - Output stays `FAIL: <msg>` / final `OK:` summary line (now also reporting temas/propuestas/metas counts)

- [ ] **Step 1: Generate seguimiento.json** (small script inline or by hand from metas file — deterministic order: metas file order)
- [ ] **Step 2: Extend the validator** per Interfaces; keep stdlib-only; clean FAILs, no tracebacks (follow the existing guard style)
- [ ] **Step 3: Run** — `python3 tools/validate_plan_data.py` → OK line reporting legacy + new tree stats
- [ ] **Step 4: Negative tests** — temporarily (a) point a seguimiento item at id `t9-9.M99` → clean FAIL; (b) break a tema file ordinal → clean FAIL; restore both, OK again
- [ ] **Step 5: Commit**

```bash
git add src/data/seguimiento.json tools/validate_plan_data.py
git commit -m "feat: add seguimiento layer and extend validator to full plan tree"
```

---

### Task 4: Documentation

**Files:**
- Modify: `docs/ARCHITECTURE.md` (add "Plan data" section: the tree, ID scheme, two-layer tracking rule — headline % from metas only —, extraction/curation workflow, "immutable content vs living seguimiento" rule)
- Modify: `CLAUDE.md` (Output Defaults: data edits now distinguish `seguimiento.json` (living, edit freely + validate) from `src/data/plan/` (regenerate via tool / curated, don't hand-edit propuestas))

- [ ] **Step 1: Update both docs** (writer decides exact wording; must state the ID scheme and the metas-only headline rule verbatim)
- [ ] **Step 2: Commit**

```bash
git add docs/ARCHITECTURE.md CLAUDE.md
git commit -m "docs: document plan data tree, ID scheme, and two-layer tracking"
```
