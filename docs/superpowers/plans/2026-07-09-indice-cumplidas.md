# Índice + Certified Proposals + Registro de Cumplidas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In-page índice navigation on topic and 100-days pages, evidence-backed certified proposal rows, and a registro de cumplidas section on the home page.

**Architecture:** Three display units backed by two data-layer changes. `src/lib/format.mjs` (new) and `fulfilledItems()` in `src/lib/plan.mjs` are pure functions tested with `node:test`; the validator gains an evidence schema and a fulfilled-requires-evidence rule. Astro components (`PlanIndex`, `ProposalRow`, `CumplidasRegistry`) are flat Tailwind-only files (no own CSS → no folder, per the component-folder convention) verified via build + headless-Brave screenshots.

**Tech Stack:** Astro 5 static build, Tailwind CSS v4 (`@theme` tokens in `src/styles/global.css`), `node --test`, Python validator (`tools/validate_plan_data.py`).

**Spec:** `docs/superpowers/specs/2026-07-09-indice-cumplidas-design.md`

## Global Constraints

- **All user-facing text in Spanish (Peru).** Code, comments, commit messages in English.
- Colors only from `@theme` tokens: `papel`, `carton`, `tinta`, `tintasuave`, `tintafina`, `rojo`, `verde`, `ambar`, `plomo`. Never default Tailwind palette.
- Animations: only `transform`/`opacity`, never `transition-all`. Every clickable element needs hover, focus-visible, and active states (site-wide `a, button` transition in global.css covers most).
- ID formats: goals `t1-1.M01`, proposals `t1-1.P01`, 100-days actions `t1-1.C01`.
- Commits: end message with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`; author email must be `33852507+DianCotrina@users.noreply.github.com`.
- `$SCRATCHPAD` in commands = the session scratchpad directory (any writable temp dir outside the repo works).
- **Preflight:** the working tree contains the uncommitted Donate folder refactor + the spec doc. Before Task 1, create branch `indice-cumplidas` from main and commit the pending work as two commits (refactor, spec) so this plan starts clean.

---

### Task 1: `formatDateEs` helper (new `src/lib/format.mjs`)

Both ProposalRow (evidence dates) and CumplidasRegistry (certification dates) need Spanish long dates. `src/pages/index.astro:21-26` already hand-rolls this — extract it.

**Files:**
- Create: `src/lib/format.mjs`
- Create: `tests/format.test.mjs`
- Modify: `src/pages/index.astro:21-26`

**Interfaces:**
- Produces: `formatDateEs(iso: string) => string` — `'2027-03-12'` → `'12 de marzo de 2027'`.

- [ ] **Step 1: Write the failing test**

```js
// tests/format.test.mjs
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { formatDateEs } from '../src/lib/format.mjs';

describe('formatDateEs', () => {
  test('formats an ISO date as Spanish long date', () => {
    assert.equal(formatDateEs('2027-03-12'), '12 de marzo de 2027');
  });

  test('no leading zero on single-digit days', () => {
    assert.equal(formatDateEs('2026-07-06'), '6 de julio de 2026');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/format.test.mjs`
Expected: FAIL — `Cannot find module '../src/lib/format.mjs'`

- [ ] **Step 3: Write minimal implementation**

```js
// src/lib/format.mjs
const MONTH_NAMES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
];

export function formatDateEs(iso) {
  const [year, month, day] = iso.split('-').map(Number);
  return `${day} de ${MONTH_NAMES[month - 1]} de ${year}`;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/format.test.mjs`
Expected: PASS (2 tests)

- [ ] **Step 5: Refactor `index.astro` to use it**

In `src/pages/index.astro`, add to the imports block: `import { formatDateEs } from '../lib/format.mjs';`, delete the `MONTH_NAMES` constant and the `const [updYear, updMonth, updDay] = ...` line (lines 21-26), and replace the `updatedText` assignment with:

```js
const updatedText = `Actualizado el ${formatDateEs(tracking.updated)}`;
```

- [ ] **Step 6: Verify full suite and build**

Run: `npm test && npm run build`
Expected: all tests pass; build completes 25 pages.

- [ ] **Step 7: Commit**

```bash
git add src/lib/format.mjs tests/format.test.mjs src/pages/index.astro
git commit -m "feat: add formatDateEs helper, reuse in home page"
```

---

### Task 2: `fulfilledItems()` in `src/lib/plan.mjs`

**Files:**
- Modify: `src/lib/plan.mjs` (append after `firstHundredDaysStats`)
- Modify: `tests/plan.test.mjs`

**Interfaces:**
- Consumes: existing `loadPlan()`, `loadTopics()`, `loadTracking()`.
- Produces: `fulfilledItems(plan, topics, tracking) => { total: number, byPillar: [{ id, name, count }], items: [{ id, text, topicName, topicSlug, pillarId, pillarName, evidence }] }`. Items appear in plan order (pillar → topic → proposals then 100-days actions). Goals are never included.

- [ ] **Step 1: Write the failing tests**

Append to `tests/plan.test.mjs` (add `fulfilledItems` to the existing import from `plan.mjs`):

```js
describe('fulfilledItems', () => {
  test('real tracking data: empty registry, 3 pillars at 0', () => {
    const result = fulfilledItems(loadPlan(), loadTopics(), loadTracking());
    assert.equal(result.total, 0);
    assert.deepEqual(result.items, []);
    assert.deepEqual(result.byPillar.map((p) => p.count), [0, 0, 0]);
    assert.equal(result.byPillar[0].name, 'Orden');
  });

  test('synthetic tracking: includes fulfilled proposals and actions, excludes goals and non-fulfilled', () => {
    const tracking = {
      items: {
        't1-1.P01': { status: 'fulfilled', evidence: [{ date: '2026-09-01', source: 'El Peruano', url: 'https://elperuano.pe/ds-044' }] },
        't2-1.C01': { status: 'fulfilled', evidence: [{ date: '2026-08-15', source: 'MEF' }] },
        't1-1.M01': { status: 'fulfilled', evidence: [{ date: '2026-08-15', source: 'INEI' }] },
        't1-1.P02': { status: 'in_progress', evidence: [] },
      },
    };
    const result = fulfilledItems(loadPlan(), loadTopics(), tracking);
    assert.equal(result.total, 2);
    assert.deepEqual(result.items.map((item) => item.id), ['t1-1.P01', 't2-1.C01']);
    assert.deepEqual(result.byPillar.map((p) => p.count), [1, 1, 0]);
    assert.equal(result.items[0].topicName, 'Orden ciudadano');
    assert.equal(result.items[0].topicSlug, 'orden-ciudadano');
    assert.equal(result.items[0].pillarName, 'Orden');
    assert.equal(result.items[0].evidence[0].url, 'https://elperuano.pe/ds-044');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/plan.test.mjs`
Expected: FAIL — `fulfilledItems` is not exported.

- [ ] **Step 3: Write the implementation**

Append to `src/lib/plan.mjs`:

```js
// Certified (fulfilled) proposals and 100-days actions with their evidence,
// in plan order, for the registro de cumplidas. Goals (.M items) never appear
// here — they are covered by the headline goal stats.
export function fulfilledItems(plan, topics, tracking) {
  const items = [];
  for (const pillar of plan.pillars) {
    for (const topicMeta of plan.topics.filter((t) => t.pillar === pillar.id)) {
      const file = topics.get(topicMeta.id);
      const entries = [
        ...file.groups.flatMap((group) => group.proposals),
        ...file.first_100_days,
      ];
      for (const entry of entries) {
        const tracked = tracking.items?.[entry.id];
        if (tracked?.status !== 'fulfilled') continue;
        items.push({
          id: entry.id,
          text: entry.text,
          topicName: topicMeta.name,
          topicSlug: topicMeta.slug,
          pillarId: pillar.id,
          pillarName: pillar.name,
          evidence: tracked.evidence ?? [],
        });
      }
    }
  }
  const byPillar = plan.pillars.map((pillar) => ({
    id: pillar.id,
    name: pillar.name,
    count: items.filter((item) => item.pillarId === pillar.id).length,
  }));
  return { total: items.length, byPillar, items };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/plan.test.mjs`
Expected: PASS (all, including the 2 new).

- [ ] **Step 5: Commit**

```bash
git add src/lib/plan.mjs tests/plan.test.mjs
git commit -m "feat: add fulfilledItems() for the registro de cumplidas"
```

---

### Task 3: Evidence schema + fulfilled-requires-evidence rule in the validator

**Files:**
- Modify: `tools/validate_plan_data.py` (inside `validate_tracking`, currently lines 210-246)

**Interfaces:**
- Consumes: existing `fail()`, `DATE_RE`, `VALID_STATUSES`.
- Produces: validator enforcing evidence entries `{date (required, YYYY-MM-DD), source (required, non-empty), url (optional, http…), note (optional, non-empty)}`, no unknown keys, and `status == "fulfilled"` ⇒ `len(evidence) >= 1` for every tracked item.

- [ ] **Step 1: Add the evidence validation**

Add this function above `validate_tracking`:

```python
def validate_evidence_entry(item_id: str, i: int, entry) -> None:
    where = f"tracking.json: items['{item_id}'].evidence[{i}]"
    if not isinstance(entry, dict):
        fail(f"{where} must be an object")
    for key in ("date", "source"):
        if key not in entry:
            fail(f"{where} missing {key}")
    if not isinstance(entry["date"], str) or not DATE_RE.match(entry["date"]):
        fail(f"{where}.date must be YYYY-MM-DD, got '{entry.get('date')}'")
    if not isinstance(entry["source"], str) or not entry["source"].strip():
        fail(f"{where}.source must be a non-empty string")
    if "url" in entry and (not isinstance(entry["url"], str) or not entry["url"].startswith("http")):
        fail(f"{where}.url must be a string starting with http")
    if "note" in entry and (not isinstance(entry["note"], str) or not entry["note"].strip()):
        fail(f"{where}.note must be a non-empty string when present")
    unknown = set(entry) - {"date", "source", "url", "note"}
    if unknown:
        fail(f"{where} has unknown keys: {sorted(unknown)}")
```

Then inside the `for item_id, item in data["items"].items():` loop, directly after the existing `evidence must be a list` check (line 230-231), add:

```python
        for i, entry in enumerate(item["evidence"]):
            validate_evidence_entry(item_id, i, entry)
        if item["status"] == "fulfilled" and not item["evidence"]:
            fail(f"tracking.json: items['{item_id}'] is fulfilled but has no evidence — no certification without proof")
```

- [ ] **Step 2: Verify real data still passes**

Run: `npm run validate`
Expected: `OK: plan/ tree valid — 23 topics, 632 proposals, … tracking.json valid`

- [ ] **Step 3: Verify the rule catches violations (temporary mutation, then restore)**

```bash
cp src/data/tracking.json "$SCRATCHPAD/tracking.json.bak"
python3 - <<'EOF'
import json
p = 'src/data/tracking.json'
d = json.load(open(p))
d['items']['t1-1.M01']['status'] = 'fulfilled'   # fulfilled with empty evidence
json.dump(d, open(p, 'w'), ensure_ascii=False, indent=2)
EOF
npm run validate
```

Expected: FAIL with `items['t1-1.M01'] is fulfilled but has no evidence`.

Then test a malformed evidence entry:

```bash
python3 - <<'EOF'
import json
p = 'src/data/tracking.json'
d = json.load(open(p))
d['items']['t1-1.M01']['evidence'] = [{'date': 'marzo 2027', 'source': 'X'}]
json.dump(d, open(p, 'w'), ensure_ascii=False, indent=2)
EOF
npm run validate
```

Expected: FAIL with `evidence[0].date must be YYYY-MM-DD`.

Restore: `cp "$SCRATCHPAD/tracking.json.bak" src/data/tracking.json && npm run validate` → OK.

- [ ] **Step 4: Commit**

```bash
git add tools/validate_plan_data.py
git commit -m "feat: validate evidence schema; fulfilled requires evidence"
```

---

### Task 4: `ProposalRow` component with certified treatment

**Files:**
- Create: `src/components/ProposalRow.astro`
- Modify: `src/pages/temas/[slug].astro:105-114` (replace inline row)

**Interfaces:**
- Consumes: `Stamp.astro` (prop `status`), `formatDateEs` from Task 1.
- Produces: `<ProposalRow id text status? evidence? />` — `status`/`evidence` come straight from `tracking.items[id]`.

- [ ] **Step 1: Create the component**

```astro
---
// src/components/ProposalRow.astro
import Stamp from './Stamp.astro';
import { formatDateEs } from '../lib/format.mjs';

interface Evidence {
  date: string;
  source: string;
  url?: string;
  note?: string;
}

interface Props {
  id: string;
  text: string;
  status?: string;
  evidence?: Evidence[];
}

const { id, text, status, evidence = [] } = Astro.props;
const certified = status === 'fulfilled';
---

<li class:list={['flex items-start gap-4 py-3.5', certified && 'bg-verde/[0.05] -mx-3 px-3 rounded-md']}>
  <span class="font-mono text-xs font-semibold text-tintafina shrink-0 mt-0.5 min-w-[2.4rem]">{id.split('.')[1]}</span>
  <div class="flex-1">
    <p class="text-sm leading-[1.7]">{text}</p>
    {certified && evidence.length > 0 && (
      <details class="mt-2 group">
        <summary class="cursor-pointer list-none inline-flex items-center gap-1.5 font-mono text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-verde hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-verde/60 rounded-sm">
          Ver evidencia
          <span aria-hidden="true" class="transition-transform duration-200 group-open:rotate-90">→</span>
        </summary>
        <ul class="mt-2.5 border-l-2 border-verde/30 pl-4 space-y-3">
          {evidence.map((entry) => (
            <li>
              <p class="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-tintafina">✓ Verificado · {formatDateEs(entry.date)}</p>
              <p class="mt-0.5 text-sm font-sans font-medium">
                {entry.url
                  ? <a href={entry.url} target="_blank" rel="noopener noreferrer" class="nav-link">{entry.source} ↗</a>
                  : entry.source}
              </p>
              {entry.note && <p class="mt-0.5 text-sm leading-[1.6] text-tintasuave">{entry.note}</p>}
            </li>
          ))}
        </ul>
      </details>
    )}
  </div>
  {status && <Stamp status={status} />}
</li>
```

- [ ] **Step 2: Use it on the topic page**

In `src/pages/temas/[slug].astro`: add `import ProposalRow from '../../components/ProposalRow.astro';` to the imports, and remove the now-unused `Stamp` import (the proposal row was its only usage on this page — GoalRow handles goal statuses itself). Replace the inner map body (lines 105-114):

```astro
{group.proposals.map((proposal) => (
  <ProposalRow
    id={proposal.id}
    text={proposal.text}
    status={tracking.items?.[proposal.id]?.status}
    evidence={tracking.items?.[proposal.id]?.evidence}
  />
))}
```

(The old inline `const status = …` block and `<li>` disappear entirely.)

- [ ] **Step 3: Build and verify zero visual change on real data**

Run: `npm run build`
Expected: passes. Then screenshot `http://localhost:3000/temas/orden-ciudadano/` (headless Brave, 1280×800) and compare against main — rows must look identical (no item is fulfilled in real data).

- [ ] **Step 4: Commit**

```bash
git add src/components/ProposalRow.astro src/pages/temas/[slug].astro
git commit -m "feat: extract ProposalRow with certified evidence treatment"
```

---

### Task 5: `PlanIndex` component + topic-page índice

**Files:**
- Create: `src/components/PlanIndex.astro`
- Modify: `src/pages/temas/[slug].astro` (masthead + section `id`s)

**Interfaces:**
- Produces: `<PlanIndex entries={IndexEntry[]} />` where `IndexEntry = { href, label, count?, children?: { href, label }[] }`. Also consumed by Task 6.

- [ ] **Step 1: Create the component**

```astro
---
// src/components/PlanIndex.astro
interface IndexChild {
  href: string;
  label: string;
}

interface IndexEntry {
  href: string;
  label: string;
  count?: number;
  children?: IndexChild[];
}

interface Props {
  entries: IndexEntry[];
}

const { entries } = Astro.props;
---

<nav aria-label="Índice de la página" class="bg-white rounded-lg border border-tinta/10 shadow-card px-6 py-5">
  <p class="font-mono text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-tintasuave border-b border-dashed border-tinta/20 pb-3">Índice · Expediente</p>
  <ol class="mt-2 divide-y divide-tinta/5">
    {entries.map((entry, index) => (
      <li class="py-2.5">
        <a href={entry.href} class="nav-link group flex items-baseline gap-3 font-sans text-sm font-medium">
          <span class="font-mono text-xs font-semibold text-rojo shrink-0">{String(index + 1).padStart(2, '0')}</span>
          <span>{entry.label}</span>
          <span aria-hidden="true" class="flex-1 border-b border-dotted border-tinta/25 min-w-4 translate-y-[-3px]"></span>
          {typeof entry.count === 'number' && <span class="font-mono text-xs text-tintafina shrink-0">{entry.count}</span>}
        </a>
        {entry.children && entry.children.length > 0 && (
          <ul class="mt-1.5 ml-8 space-y-1">
            {entry.children.map((child) => (
              <li>
                <a href={child.href} class="nav-link font-sans text-[0.8rem] text-tintasuave">— {child.label}</a>
              </li>
            ))}
          </ul>
        )}
      </li>
    ))}
  </ol>
</nav>
```

- [ ] **Step 2: Wire it into the topic page**

In `src/pages/temas/[slug].astro`:

1. `import PlanIndex from '../../components/PlanIndex.astro';`
2. In frontmatter, after `pillarIndex`:

```js
const indexEntries = [
  { href: '#metas', label: 'Metas al 2031', count: topicGoals.length },
  {
    href: '#propuestas',
    label: 'Propuestas',
    count: topic.proposals,
    children: topicFile.groups.map((group, i) => ({ href: `#grupo-${i + 1}`, label: group.title ?? 'Generales' })),
  },
  { href: '#cien-dias', label: 'Primeros 100 días', count: topicFile.first_100_days.length },
];
```

3. At the end of the masthead section (after the `PenProgress` wrapper div), add:

```astro
<div class="mt-10 max-w-md">
  <PlanIndex entries={indexEntries} />
</div>
```

4. Add anchors: `id="metas" class="… scroll-mt-6"` on the Metas section, `id="propuestas" class="… scroll-mt-6"` on the Propuestas section, `id="cien-dias" class="… scroll-mt-6"` on the 100-días section, and change the groups map to `topicFile.groups.map((group, groupIndex) => (` with `id={`grupo-${groupIndex + 1}`}` and `scroll-mt-6` added to the group `<div class="reveal">`.

- [ ] **Step 3: Build + visual check**

Run: `npm run build` → passes. Screenshot `http://localhost:3000/temas/orden-ciudadano/`: índice box under the progress pen with 3 numbered rows and 3 group sub-links. Click-test one anchor in a real browser tab or by screenshotting `…/temas/orden-ciudadano/#grupo-2` and confirming scroll position.

- [ ] **Step 4: Commit**

```bash
git add src/components/PlanIndex.astro src/pages/temas/[slug].astro
git commit -m "feat: add PlanIndex índice block to topic pages"
```

---

### Task 6: Índice on the 100-days page

**Files:**
- Modify: `src/pages/primeros-100-dias.astro`

**Interfaces:**
- Consumes: `PlanIndex` from Task 5; `groups` (pillars) already computed on the page.

- [ ] **Step 1: Wire the índice**

In `src/pages/primeros-100-dias.astro`:

1. `import PlanIndex from '../components/PlanIndex.astro';`
2. In frontmatter after `startedPct`:

```js
const indexEntries = groups.map((pillar) => ({
  href: `#pilar-${pillar.index}`,
  label: pillar.name,
  count: pillar.topics.reduce((sum, topic) => sum + topic.actions.length, 0),
  children: pillar.topics.map((topic) => ({ href: `#dias-${topic.slug}`, label: topic.name })),
}));
```

3. After the Tally `</section>`, add:

```astro
<section class="mx-auto max-w-4xl px-5 sm:px-8 pt-6 pb-2">
  <PlanIndex entries={indexEntries} />
</section>
```

4. Anchors: on the pillar `<section>` inside the groups map add `id={`pilar-${pillar.index}`}` and `scroll-mt-6`; on each topic `<div class="reveal">` add `id={`dias-${topic.slug}`}` and `scroll-mt-6`.

Note: the existing `pillarCount` computed inside the template map duplicates the índice count expression — leave the template as is (it still works); do not refactor it.

- [ ] **Step 2: Build + visual check**

Run: `npm run build` → passes. Screenshot `http://localhost:3000/primeros-100-dias/`: índice between tally card and Pilar 1, 3 pillar rows with topic sub-links.

- [ ] **Step 3: Commit**

```bash
git add src/pages/primeros-100-dias.astro
git commit -m "feat: add índice to primeros 100 días page"
```

---

### Task 7: `CumplidasRegistry` + home section

**Files:**
- Create: `src/components/CumplidasRegistry.astro`
- Modify: `src/pages/index.astro` (new section after the 100-días teaser)

**Interfaces:**
- Consumes: `fulfilledItems` result (Task 2), `formatDateEs` (Task 1).
- Produces: `<CumplidasRegistry total byPillar items />` — fully self-contained; a future `/cumplidas/` page reuses it with identical props.

- [ ] **Step 1: Create the component**

```astro
---
// src/components/CumplidasRegistry.astro
// Self-contained: no assumptions about the hosting page, so it can graduate
// to a dedicated /cumplidas/ page unchanged.
import { formatDateEs } from '../lib/format.mjs';

interface Evidence {
  date: string;
  source: string;
  url?: string;
  note?: string;
}

interface FulfilledItem {
  id: string;
  text: string;
  topicName: string;
  topicSlug: string;
  pillarName: string;
  evidence: Evidence[];
}

interface PillarCount {
  id: string;
  name: string;
  count: number;
}

interface Props {
  total: number;
  byPillar: PillarCount[];
  items: FulfilledItem[];
}

const { total, byPillar, items } = Astro.props;

const latestDate = (evidence: Evidence[]) =>
  evidence.map((entry) => entry.date).sort().at(-1);
---

<div class="bg-white rounded-lg border border-tinta/10 shadow-card p-6 sm:p-7">
  <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-dashed border-tinta/20 pb-4">
    <p class="font-mono text-[0.65rem] sm:text-xs font-semibold uppercase tracking-[0.14em] text-tintasuave">Registro · Cumplidas</p>
    <p class="font-mono text-[0.65rem] sm:text-xs text-tintafina">{total} {total === 1 ? 'certificada' : 'certificadas'}</p>
  </div>

  <div class="mt-5 grid grid-cols-3 gap-2 font-mono text-center">
    {byPillar.map((pillar) => (
      <div>
        <p class:list={['text-xl font-semibold', pillar.count > 0 ? 'text-verde' : 'text-tintafina']}>{pillar.count}</p>
        <p class="text-[0.6rem] uppercase tracking-wider text-tintafina mt-1">{pillar.name}</p>
      </div>
    ))}
  </div>

  {total === 0 ? (
    <p class="mt-6 border-t border-tinta/10 pt-5 font-mono text-sm text-tintasuave leading-[1.7]">
      El registro está abierto. Cuando una propuesta se certifique como cumplida, aparecerá aquí con su evidencia.
    </p>
  ) : (
    <ul class="mt-6 border-t border-tinta/10 divide-y divide-tinta/10">
      {items.map((item) => (
        <li class="py-3.5 flex items-start gap-3.5">
          <span aria-hidden="true" class="font-mono text-sm font-semibold text-verde mt-0.5">✓</span>
          <div class="flex-1">
            <p class="text-sm leading-[1.7]">{item.text}</p>
            <p class="mt-1 font-mono text-[0.65rem] text-tintafina">
              <a href={`/temas/${item.topicSlug}/`} class="nav-link">{item.topicName}</a>
              {latestDate(item.evidence) && <> · certificada el {formatDateEs(latestDate(item.evidence)!)}</>}
            </p>
          </div>
        </li>
      ))}
    </ul>
  )}
</div>
```

- [ ] **Step 2: Add the home section**

In `src/pages/index.astro`:

1. Extend the lib import: `import { loadPlan, loadTopics, loadGoals, loadTracking, goalStats, topicSummaries, statusOf, fulfilledItems } from '../lib/plan.mjs';` and `import CumplidasRegistry from '../components/CumplidasRegistry.astro';`
2. In frontmatter after `pillarGroups`:

```js
const cumplidas = fulfilledItems(plan, loadTopics(), tracking);
```

3. Insert a new section between the 100-días teaser section and `<!-- Metodología -->`:

```astro
<!-- Registro de cumplidas -->
<section id="cumplidas" class="border-t border-tinta/10 bg-white/40 scroll-mt-6">
  <div class="mx-auto max-w-6xl px-5 sm:px-8 py-14 sm:py-20 grid lg:grid-cols-[0.9fr_1.1fr] gap-10 items-start">
    <div class="reveal">
      <p class="font-mono text-xs uppercase tracking-[0.18em] text-tintasuave">Lo entregado</p>
      <h2 class="font-display text-3xl sm:text-4xl mt-3" style="letter-spacing:-0.03em">Registro de cumplidas</h2>
      <p class="mt-4 text-lg leading-[1.7] text-tintasuave">Cada propuesta certificada como cumplida, con la evidencia que lo respalda. Sin evidencia no hay certificación.</p>
    </div>
    <div class="reveal">
      <CumplidasRegistry total={cumplidas.total} byPillar={cumplidas.byPillar} items={cumplidas.items} />
    </div>
  </div>
</section>
```

- [ ] **Step 3: Build + visual check (empty state)**

Run: `npm test && npm run build` → all pass. Screenshot `http://localhost:3000/`: new section shows the three pillar zeros and the "El registro está abierto…" copy.

- [ ] **Step 4: Commit**

```bash
git add src/components/CumplidasRegistry.astro src/pages/index.astro
git commit -m "feat: add registro de cumplidas section to home"
```

---

### Task 8: End-to-end visual verification with mock certified data

**Files:**
- Temporarily modify: `src/data/tracking.json` (reverted at the end — never committed)

- [ ] **Step 1: Inject a mock certified proposal**

```bash
cp src/data/tracking.json "$SCRATCHPAD/tracking.json.bak"
python3 - <<'EOF'
import json
p = 'src/data/tracking.json'
d = json.load(open(p))
d['items']['t1-1.P01'] = {
    'status': 'fulfilled',
    'evidence': [{
        'date': '2026-09-01',
        'source': 'El Peruano — D.S. N.º 044-2026-IN',
        'url': 'https://elperuano.pe/',
        'note': 'Norma publicada que formaliza el programa.',
    }],
}
json.dump(d, open(p, 'w'), ensure_ascii=False, indent=2)
EOF
npm run validate
```

Expected: OK (the mock satisfies the evidence rule).

- [ ] **Step 2: Screenshot all three surfaces**

Headless Brave at 1280×800 (dev server already picks up the data change):
- `http://localhost:3000/temas/orden-ciudadano/` — proposal P01 shows the verde-tinted certified row, Cumplida stamp, "Ver evidencia →". Also screenshot with the details forced open (same-origin iframe harness from the Donate verification, calling `doc.querySelector('details').open = true`) to check the evidence layout: date line, linked source, note.
- `http://localhost:3000/` — registry shows Orden = 1, item row with topic link and "certificada el 1 de septiembre de 2026".
- Mobile width (390px via the iframe trick from memory): índice block and registry don't overflow.

- [ ] **Step 3: Restore real data**

```bash
cp "$SCRATCHPAD/tracking.json.bak" src/data/tracking.json
npm run validate && npm test && npm run build
git status --short   # src/data/tracking.json must NOT appear
```

Expected: everything green, tracking.json clean.

- [ ] **Step 4: Commit the spec/plan docs if not yet committed, then wrap up**

```bash
git status --short
git add docs/superpowers/plans/2026-07-09-indice-cumplidas.md
git commit -m "docs: implementation plan for índice + cumplidas"
```

Then use superpowers:finishing-a-development-branch — offer PR to main (the repo's PR-based flow).
