# Modular Architecture (Landing Page) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the single-file landing page into a module-based architecture — a JSON data layer and ES-module renderers — with zero visual change, so future pages and real data plug in without rewrites.

**Architecture:** `index.html` stays the static shell (head, Tailwind config, custom CSS, static copy: header, hero text, metodología, alertas CTA, footer). Everything data-driven (tracker card, ejes grid, actualizaciones list, donate widget, reveal behavior) moves to ES modules under `src/modules/`, rendered by `src/main.js` from a single source of truth `src/data/plan.json`. No build step, no framework: native ES modules served by `serve.mjs`. A WAT tool (`tools/validate_plan_data.py`) validates the data file.

**Tech Stack:** Vanilla ES modules, Tailwind CSS via CDN, JSON data file, Python 3 (stdlib only) for validation, headless Brave for visual verification.

## Global Constraints

- All user-facing strings in Spanish (Peru); code identifiers, comments, and commits in English (per CLAUDE.md Language Policy).
- No build step, no npm dependencies, no framework. Native ES modules only.
- Tailwind via CDN: `<script src="https://cdn.tailwindcss.com"></script>` stays in `index.html`.
- Zero visual regression: the rendered page must look identical to the current static version (verified by screenshot).
- Page is always served via `node serve.mjs` at `http://localhost:3000` — ES modules and `fetch` do not work from `file://`.
- Headless screenshots use Brave (`/Applications/Brave Browser.app/Contents/MacOS/Brave Browser`); headless windows clamp to 500px min width — use the iframe trick for mobile widths.
- Estado palette (canonical, used everywhere): `cumplida` → `verde`, `en_progreso` → `ambar`, `sin_avance` → `plomo`, `incumplida` → `rojo`.
- Do not commit unrelated pre-existing untracked files; stage only files each task touches.

## File Structure

```
/
├── index.html                  # static shell + mount points (modified)
├── serve.mjs                   # unchanged
├── src/
│   ├── main.js                 # entry point: fetch data, render modules, init behaviors
│   ├── lib/
│   │   └── dom.js              # esc(), ESTADOS map, stamp() template helper
│   ├── data/
│   │   └── plan.json           # single source of truth for all tracker data
│   └── modules/
│       ├── tracker-card.js     # hero "expediente" card
│       ├── ejes.js             # policy-area grid
│       ├── registro.js         # últimas actualizaciones list
│       ├── donate.js           # donate pill + share button behavior
│       └── reveal.js           # IntersectionObserver scroll reveal
├── tools/
│   └── validate_plan_data.py   # WAT tool: schema + consistency checks for plan.json
└── docs/
    └── ARCHITECTURE.md         # module map + data contract (created)
```

---

### Task 1: Data layer — `plan.json` + validation tool

**Files:**
- Create: `src/data/plan.json`
- Create: `tools/validate_plan_data.py`

**Interfaces:**
- Produces: `plan.json` shape consumed by all render modules:
  - `meta: { actualizado: "YYYY-MM-DD", actualizado_texto: string, periodo: string, fuentes: string[] }`
  - `resumen: { avance_general: number, total: number, estados: { cumplida: number, en_progreso: number, sin_avance: number, incumplida: number } }`
  - `destacados: Array<{ texto: string, estado: EstadoId }>`
  - `ejes: Array<{ id: string, nombre: string, compromisos: number, avance: number }>`
  - `actualizaciones: Array<{ fecha: "YYYY-MM-DD", fecha_texto: string, texto: string, estado: EstadoId }>`
  - `EstadoId = "cumplida" | "en_progreso" | "sin_avance" | "incumplida"`

- [ ] **Step 1: Create `src/data/plan.json`** (current sample data, marked as such in CLAUDE.md/footer already)

```json
{
  "meta": {
    "actualizado": "2026-07-06",
    "actualizado_texto": "Act. 06 jul 2026",
    "periodo": "2026–2031",
    "fuentes": ["El Peruano", "MEF", "INEI", "Congreso de la República"]
  },
  "resumen": {
    "avance_general": 27,
    "total": 87,
    "estados": { "cumplida": 12, "en_progreso": 34, "sin_avance": 28, "incumplida": 13 }
  },
  "destacados": [
    { "texto": "Hospitales bicentenario en 10 regiones priorizadas", "estado": "en_progreso" },
    { "texto": "Devolución del 100 % de aportes FONAVI", "estado": "cumplida" },
    { "texto": "50 000 nuevos policías en el primer año", "estado": "sin_avance" }
  ],
  "ejes": [
    { "id": "economia", "nombre": "Economía y empleo", "compromisos": 18, "avance": 33 },
    { "id": "seguridad", "nombre": "Seguridad ciudadana", "compromisos": 15, "avance": 13 },
    { "id": "salud", "nombre": "Salud pública", "compromisos": 14, "avance": 29 },
    { "id": "educacion", "nombre": "Educación", "compromisos": 12, "avance": 25 },
    { "id": "agro", "nombre": "Agro y riego", "compromisos": 16, "avance": 38 },
    { "id": "anticorrupcion", "nombre": "Lucha anticorrupción", "compromisos": 12, "avance": 17 }
  ],
  "actualizaciones": [
    { "fecha": "2026-07-04", "fecha_texto": "04 jul 2026", "texto": "Ley de devolución de aportes FONAVI publicada en El Peruano.", "estado": "cumplida" },
    { "fecha": "2026-06-28", "fecha_texto": "28 jun 2026", "texto": "Licitación de 3 hospitales bicentenario adjudicada en Cusco, Piura y Loreto.", "estado": "en_progreso" },
    { "fecha": "2026-06-19", "fecha_texto": "19 jun 2026", "texto": "Sin partida presupuestal para los 50 000 nuevos policías anunciados.", "estado": "sin_avance" }
  ]
}
```

- [ ] **Step 2: Create `tools/validate_plan_data.py`**

```python
#!/usr/bin/env python3
"""Validate src/data/plan.json: schema, estado ids, and count consistency."""
import json
import sys
from pathlib import Path

VALID_ESTADOS = {"cumplida", "en_progreso", "sin_avance", "incumplida"}
DATA_PATH = Path(__file__).resolve().parent.parent / "src" / "data" / "plan.json"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        fail(f"cannot read/parse {DATA_PATH}: {e}")

    for key in ("meta", "resumen", "destacados", "ejes", "actualizaciones"):
        if key not in data:
            fail(f"missing top-level key: {key}")

    estados = data["resumen"]["estados"]
    if set(estados) != VALID_ESTADOS:
        fail(f"resumen.estados keys must be exactly {sorted(VALID_ESTADOS)}")
    if sum(estados.values()) != data["resumen"]["total"]:
        fail(f"estado counts {sum(estados.values())} != total {data['resumen']['total']}")
    if not 0 <= data["resumen"]["avance_general"] <= 100:
        fail("resumen.avance_general must be 0..100")

    for i, item in enumerate(data["destacados"] + data["actualizaciones"]):
        if item["estado"] not in VALID_ESTADOS:
            fail(f"invalid estado '{item['estado']}' at destacados/actualizaciones[{i}]")
        if not item["texto"].strip():
            fail(f"empty texto at destacados/actualizaciones[{i}]")

    seen_ids = set()
    for eje in data["ejes"]:
        if eje["id"] in seen_ids:
            fail(f"duplicate eje id: {eje['id']}")
        seen_ids.add(eje["id"])
        if not 0 <= eje["avance"] <= 100:
            fail(f"eje '{eje['id']}' avance must be 0..100")

    print(f"OK: {DATA_PATH.name} valid — {data['resumen']['total']} compromisos, {len(data['ejes'])} ejes")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the validator, verify it passes**

Run: `python3 tools/validate_plan_data.py`
Expected: `OK: plan.json valid — 87 compromisos, 6 ejes`

- [ ] **Step 4: Verify the validator actually catches errors** (temporarily change `"total": 87` to `88`, rerun, expect `FAIL: estado counts 87 != total 88`, then restore `87` and rerun to see OK)

- [ ] **Step 5: Commit**

```bash
git add src/data/plan.json tools/validate_plan_data.py
git commit -m "feat: add plan.json data layer and validation tool"
```

---

### Task 2: DOM helpers — `src/lib/dom.js`

**Files:**
- Create: `src/lib/dom.js`

**Interfaces:**
- Produces:
  - `esc(value: unknown): string` — HTML-escapes `& < > " '`
  - `ESTADOS: Record<EstadoId, { label: string, color: string }>` — `color` is the Tailwind color token name (`verde` | `ambar` | `plomo` | `rojo`)
  - `stamp(estado: EstadoId): string` — returns the stamp chip HTML string

- [ ] **Step 1: Create `src/lib/dom.js`**

```js
export function esc(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

export const ESTADOS = {
  cumplida:    { label: 'Cumplida',    color: 'verde' },
  en_progreso: { label: 'En progreso', color: 'ambar' },
  sin_avance:  { label: 'Sin avance',  color: 'plomo' },
  incumplida:  { label: 'Incumplida',  color: 'rojo' },
};

export function stamp(estado) {
  const { label, color } = ESTADOS[estado];
  return `<span class="stamp text-${color} shrink-0">${esc(label)}</span>`;
}
```

- [ ] **Step 2: Syntax-check**

Run: `node --check src/lib/dom.js`
Expected: no output, exit 0

- [ ] **Step 3: Commit**

```bash
git add src/lib/dom.js
git commit -m "feat: add dom helpers (esc, ESTADOS, stamp)"
```

> Note: `text-plomo`, `text-verde`, `text-ambar`, `text-rojo` are produced dynamically; Tailwind CDN JIT only sees classes present in the DOM at scan time — the CDN build re-scans on DOM mutation, so dynamically inserted classes work. No safelist needed.

---

### Task 3: Render modules — tracker card, ejes, registro

**Files:**
- Create: `src/modules/tracker-card.js`
- Create: `src/modules/ejes.js`
- Create: `src/modules/registro.js`

**Interfaces:**
- Consumes: `esc`, `stamp` from `../lib/dom.js`; the `plan.json` shape from Task 1.
- Produces:
  - `renderTrackerCard(el: HTMLElement, data: Plan): void`
  - `renderEjes(el: HTMLElement, data: Plan): void`
  - `renderRegistro(el: HTMLElement, data: Plan): void`

Each render function sets `el.innerHTML` to markup identical to the current static HTML in `index.html` (copy the exact classes from there — the markup below is the source of truth going forward).

- [ ] **Step 1: Create `src/modules/tracker-card.js`**

```js
import { esc, stamp } from '../lib/dom.js';

export function renderTrackerCard(el, data) {
  const { meta, resumen, destacados } = data;
  const filled = Math.round(4 + (396 - 4) * (resumen.avance_general / 100));
  el.innerHTML = `
    <div class="bg-white/85 backdrop-blur rounded-lg shadow-lift border border-tinta/10 p-6 sm:p-7">
      <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-dashed border-tinta/20 pb-4">
        <p class="font-mono text-[0.65rem] sm:text-xs font-semibold uppercase tracking-[0.14em] text-tintasuave">Expediente · Avance general</p>
        <p class="font-mono text-[0.65rem] sm:text-xs text-tintafina whitespace-nowrap">${esc(meta.actualizado_texto)}</p>
      </div>
      <div class="mt-5 flex flex-wrap items-end justify-between gap-x-4 gap-y-1">
        <p class="font-display text-5xl sm:text-6xl" style="letter-spacing:-0.03em">${esc(resumen.avance_general)}<span class="text-3xl">%</span></p>
        <p class="font-mono text-xs text-tintasuave mb-1.5">${esc(resumen.total)} compromisos rastreados</p>
      </div>
      <div class="mt-3 h-4 relative" role="img" aria-label="Avance general: ${esc(resumen.avance_general)} por ciento">
        <svg class="absolute inset-0 w-full h-full" viewBox="0 0 400 16" fill="none" preserveAspectRatio="none" aria-hidden="true">
          <path d="M2 8 H 398" stroke="rgba(20,20,23,0.14)" stroke-width="10" stroke-linecap="round"/>
          <path d="M2 9 C 30 5, 60 12, ${filled} 7" stroke="#141417" stroke-width="9" stroke-linecap="round"/>
        </svg>
      </div>
      <div class="mt-6 grid grid-cols-4 gap-2 font-mono text-center">
        <div><p class="text-xl font-semibold text-verde">${esc(resumen.estados.cumplida)}</p><p class="text-[0.6rem] uppercase tracking-wider text-tintafina mt-1">Cumplidos</p></div>
        <div><p class="text-xl font-semibold text-ambar">${esc(resumen.estados.en_progreso)}</p><p class="text-[0.6rem] uppercase tracking-wider text-tintafina mt-1">En progreso</p></div>
        <div><p class="text-xl font-semibold text-plomo">${esc(resumen.estados.sin_avance)}</p><p class="text-[0.6rem] uppercase tracking-wider text-tintafina mt-1">Sin avance</p></div>
        <div><p class="text-xl font-semibold text-rojo">${esc(resumen.estados.incumplida)}</p><p class="text-[0.6rem] uppercase tracking-wider text-tintafina mt-1">Incumplidos</p></div>
      </div>
      <ul class="mt-6 space-y-3 border-t border-dashed border-tinta/20 pt-5">
        ${destacados.map((d) => `
        <li class="flex items-start justify-between gap-3">
          <p class="text-sm leading-snug">${esc(d.texto)}</p>
          ${stamp(d.estado)}
        </li>`).join('')}
      </ul>
      <p class="mt-5 font-mono text-[0.6rem] text-tintafina leading-relaxed">Fuentes: ${meta.fuentes.map(esc).join(' · ')}</p>
    </div>`;
}
```

- [ ] **Step 2: Create `src/modules/ejes.js`**

```js
import { esc } from '../lib/dom.js';

export function renderEjes(el, data) {
  el.innerHTML = data.ejes.map((eje) => `
    <a href="#" class="card-hover reveal block bg-white rounded-lg border border-tinta/10 shadow-card p-6" data-eje="${esc(eje.id)}">
      <div class="flex items-baseline justify-between">
        <h3 class="font-sans font-bold text-lg">${esc(eje.nombre)}</h3>
        <span class="font-mono text-xs text-tintafina">${esc(eje.compromisos)} comp.</span>
      </div>
      <div class="mt-4 h-1.5 rounded-full bg-tinta/10 overflow-hidden"><div class="h-full rounded-full bg-tinta" style="width:${esc(eje.avance)}%"></div></div>
      <p class="mt-3 font-mono text-xs text-tintasuave">${esc(eje.avance)} % de avance</p>
    </a>`).join('');
}
```

- [ ] **Step 3: Create `src/modules/registro.js`**

```js
import { esc, stamp } from '../lib/dom.js';

export function renderRegistro(el, data) {
  el.innerHTML = data.actualizaciones.map((a) => `
    <li class="reveal flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-6 p-5 sm:p-6">
      <span class="font-mono text-xs text-tintafina shrink-0 sm:w-28">${esc(a.fecha_texto)}</span>
      <p class="flex-1 text-sm sm:text-base">${esc(a.texto)}</p>
      ${stamp(a.estado)}
    </li>`).join('');
}
```

- [ ] **Step 4: Syntax-check all three**

Run: `node --check src/modules/tracker-card.js && node --check src/modules/ejes.js && node --check src/modules/registro.js`
Expected: no output, exit 0

- [ ] **Step 5: Commit**

```bash
git add src/modules/tracker-card.js src/modules/ejes.js src/modules/registro.js
git commit -m "feat: add render modules for tracker card, ejes, registro"
```

---

### Task 4: Behavior modules — reveal + donate/share

**Files:**
- Create: `src/modules/reveal.js`
- Create: `src/modules/donate.js`

**Interfaces:**
- Produces:
  - `initReveal(): void` — observes all `.reveal` elements (call AFTER render modules run, so dynamically rendered `.reveal` cards are included)
  - `initDonate(): void` — wires `#share-btn` click to `navigator.share` with clipboard + `#share-toast` fallback

- [ ] **Step 1: Create `src/modules/reveal.js`** (moved verbatim from the inline script in `index.html`)

```js
export function initReveal() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });
  document.querySelectorAll('.reveal').forEach((el) => observer.observe(el));
}
```

- [ ] **Step 2: Create `src/modules/donate.js`** (moved verbatim from the inline script in `index.html`)

```js
export function initDonate() {
  const btn = document.getElementById('share-btn');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const data = { title: document.title, url: location.href };
    if (navigator.share) {
      try { await navigator.share(data); } catch {}
    } else {
      await navigator.clipboard.writeText(location.href);
      const toast = document.getElementById('share-toast');
      toast.classList.remove('opacity-0');
      setTimeout(() => toast.classList.add('opacity-0'), 1800);
    }
  });
}
```

- [ ] **Step 3: Syntax-check**

Run: `node --check src/modules/reveal.js && node --check src/modules/donate.js`
Expected: no output, exit 0

- [ ] **Step 4: Commit**

```bash
git add src/modules/reveal.js src/modules/donate.js
git commit -m "feat: add reveal and donate behavior modules"
```

---

### Task 5: Entry point + shell — `main.js` and `index.html` mount points

**Files:**
- Create: `src/main.js`
- Modify: `index.html` (three dynamic sections become mount points; inline `<script>` at the bottom is removed)

**Interfaces:**
- Consumes: everything from Tasks 2–4.
- Produces: mount-point contract — `index.html` must contain elements with ids `tracker-card`, `ejes-grid`, `registro-list`.

- [ ] **Step 1: Create `src/main.js`**

```js
import { renderTrackerCard } from './modules/tracker-card.js';
import { renderEjes } from './modules/ejes.js';
import { renderRegistro } from './modules/registro.js';
import { initReveal } from './modules/reveal.js';
import { initDonate } from './modules/donate.js';

async function boot() {
  const res = await fetch('./src/data/plan.json');
  if (!res.ok) throw new Error(`plan.json: HTTP ${res.status}`);
  const data = await res.json();

  renderTrackerCard(document.getElementById('tracker-card'), data);
  renderEjes(document.getElementById('ejes-grid'), data);
  renderRegistro(document.getElementById('registro-list'), data);

  initReveal();
  initDonate();
}

boot().catch((err) => {
  console.error(err);
  // Static shell still shows headline/copy; dynamic sections stay empty.
});
```

- [ ] **Step 2: Edit `index.html` — replace the three static blocks with mount points**

Replace the hero card `<div id="tablero" class="hero-in d4">` inner card `<div class="bg-white/85 ...">...</div>` (everything inside the `#tablero` wrapper) with:

```html
      <div id="tablero" class="hero-in d4">
        <div id="tracker-card"></div>
      </div>
```

Replace the ejes grid `<div class="mt-12 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">` and all six `<a>` cards inside it with:

```html
        <div id="ejes-grid" class="mt-12 grid sm:grid-cols-2 lg:grid-cols-3 gap-5"></div>
```

Replace the registro `<ul class="mt-10 divide-y ...">` and its three `<li>` items with:

```html
        <ul id="registro-list" class="mt-10 divide-y divide-tinta/10 bg-white rounded-lg border border-tinta/10 shadow-card"></ul>
```

- [ ] **Step 3: Edit `index.html` — replace the entire inline `<script>...</script>` before `</body>` (IntersectionObserver + share-btn listener) with:**

```html
  <script type="module" src="./src/main.js"></script>
```

- [ ] **Step 4: Verify rendering end-to-end** (server must be running: `node serve.mjs`)

Run:
```bash
BRAVE="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
"$BRAVE" --headless --disable-gpu --dump-dom --virtual-time-budget=8000 http://localhost:3000/ 2>/dev/null | grep -o 'compromisos rastreados\|Economía y empleo\|Ley de devolución' | sort | uniq -c
```
Expected: each of the three strings appears (count ≥ 1) — proves all three modules rendered from JSON.

- [ ] **Step 5: Visual regression check**

Run:
```bash
SCRATCH=<session scratchpad dir>
"$BRAVE" --headless --disable-gpu --hide-scrollbars --window-size=1440,4200 --virtual-time-budget=8000 --screenshot="$SCRATCH/after-modular.png" http://localhost:3000/ 2>/dev/null
```
Then view the screenshot and compare against the pre-refactor capture (`desktop-ink.png` in the scratchpad): tracker card, ejes grid, registro list, donate widget, and stamps must be visually identical. Note: `sin_avance` stamps are now `plomo` (gray) per the canonical estado palette — this is the one intended visual change.

- [ ] **Step 6: Run the data validator once more**

Run: `python3 tools/validate_plan_data.py`
Expected: `OK: plan.json valid — 87 compromisos, 6 ejes`

- [ ] **Step 7: Commit**

```bash
git add index.html src/main.js
git commit -m "feat: wire landing page to modular renderers via main.js"
```

---

### Task 6: Documentation — `docs/ARCHITECTURE.md` + CLAUDE.md update

**Files:**
- Create: `docs/ARCHITECTURE.md`
- Modify: `CLAUDE.md` (replace the "Output Defaults" bullet about single-file output; add architecture pointer)

- [ ] **Step 1: Create `docs/ARCHITECTURE.md`**

```markdown
# Architecture

Module-based landing page. No build step, no framework: native ES modules + Tailwind CDN, served by `node serve.mjs` at http://localhost:3000.

## Module map

| Path | Responsibility |
|---|---|
| `index.html` | Static shell: head, Tailwind config, custom CSS, static copy (header, hero text, metodología, alertas, footer), mount points |
| `src/main.js` | Entry point: fetches `plan.json`, calls renderers, inits behaviors |
| `src/lib/dom.js` | `esc()`, `ESTADOS` map, `stamp()` chip template |
| `src/modules/tracker-card.js` | Hero "expediente" card (`#tracker-card`) |
| `src/modules/ejes.js` | Policy-area grid (`#ejes-grid`) |
| `src/modules/registro.js` | Últimas actualizaciones list (`#registro-list`) |
| `src/modules/reveal.js` | Scroll-reveal behavior for `.reveal` elements |
| `src/modules/donate.js` | Donate pill share button |
| `src/data/plan.json` | Single source of truth for all tracker data (sample data for now) |
| `tools/validate_plan_data.py` | WAT tool: validates plan.json before publishing |

## Data contract

`plan.json`: `meta` (dates, periodo, fuentes) · `resumen` (avance_general, total, estados counts — counts must sum to total) · `destacados` (hero card promise rows) · `ejes` (id, nombre, compromisos, avance) · `actualizaciones` (fecha, texto, estado).

Estados: `cumplida`→verde · `en_progreso`→ambar · `sin_avance`→plomo · `incumplida`→rojo. Add new estados in `src/lib/dom.js` (ESTADOS) and `tools/validate_plan_data.py` (VALID_ESTADOS) together.

## Rules

- New page sections = new module in `src/modules/` exporting `render<Name>(el, data)` or `init<Name>()`, wired in `main.js`.
- All tracker content changes happen in `plan.json`, never in module markup.
- Run `python3 tools/validate_plan_data.py` after every `plan.json` edit.
- When SEO/prerendering becomes a requirement, migrate shell+modules to a static builder (e.g., Astro); the data contract and module boundaries are designed to survive that move.
```

- [ ] **Step 2: Update `CLAUDE.md`** — in "Output Defaults", replace:

```
- Single `index.html` file, all styles inline, unless user says otherwise
```

with:

```
- Landing page follows the module architecture in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): static shell in `index.html`, data in `src/data/plan.json`, renderers in `src/modules/`. One-off mockups/sketches may still be single files.
- Data edits go in `src/data/plan.json`; run `python3 tools/validate_plan_data.py` afterwards.
```

- [ ] **Step 3: Commit**

```bash
git add docs/ARCHITECTURE.md CLAUDE.md
git commit -m "docs: document module architecture and update CLAUDE.md defaults"
```
