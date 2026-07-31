import test from 'node:test';
import assert from 'node:assert/strict';

import { STAGES, stageMeta, recordBadge, activeEntries, isAlleged, isPressOnly } from '../src/lib/judicial.mjs';

const person = (...stages) => ({ judicial: stages.map((stage, i) => ({ id: `c${i}`, stage })) });

test('every stage carries a Spanish label, a theme color and a rank', () => {
  for (const [key, meta] of Object.entries(STAGES)) {
    assert.ok(meta.label, `${key} needs a label`);
    assert.ok(['rojo', 'ambar', 'verde', 'plomo'].includes(meta.color), `${key}: ${meta.color}`);
    assert.equal(typeof meta.rank, 'number');
  }
});

test('exculpatory stages rank 0 so they can never drive a badge', () => {
  for (const stage of ['absuelto', 'archivado', 'prescrito']) {
    assert.equal(STAGES[stage].rank, 0, stage);
  }
});

test('an unknown stage degrades instead of throwing', () => {
  const meta = stageMeta('no_such_stage');
  assert.equal(meta.color, 'plomo');
  assert.equal(meta.rank, 0);
});

test('no judicial entries reads as an absence of our finding, not of fact', () => {
  const badge = recordBadge({ judicial: [] });
  assert.equal(badge.label, 'Sin registro público');
  assert.equal(badge.color, 'plomo');
  assert.match(badge.detail, /No hallamos/);
});

test('a person with no judicial key at all is treated as empty', () => {
  assert.equal(recordBadge({}).label, 'Sin registro público');
});

test('only-exculpatory entries read as resolved, not as a live accusation', () => {
  const badge = recordBadge(person('absuelto', 'archivado'));
  assert.equal(badge.label, 'Sin procesos activos');
  assert.equal(badge.color, 'verde');
  assert.match(badge.detail, /absuelto/);
  assert.match(badge.detail, /archivado/);
});

test('an exculpatory entry never outranks a live one', () => {
  const badge = recordBadge(person('absuelto', 'acusacion_fiscal'));
  assert.equal(badge.label, 'Acusación fiscal');
  assert.equal(badge.color, 'ambar');
});

test('the badge reports the most serious live stage reached', () => {
  const badge = recordBadge(person('investigacion_preliminar', 'sentencia_firme'));
  assert.equal(badge.label, 'Sentencia firme');
  assert.equal(badge.color, 'rojo');
});

test('the detail line counts convictions apart from open proceedings', () => {
  const badge = recordBadge(person('sentencia_firme', 'acusacion_fiscal', 'juicio_oral'));
  assert.match(badge.detail, /1 condena/);
  assert.match(badge.detail, /2 procesos abiertos/);
});

test('a single conviction is counted in the singular', () => {
  const badge = recordBadge(person('sentencia_firme'));
  assert.match(badge.detail, /1 condena/);
  assert.doesNotMatch(badge.detail, /condenas/);
});

test('activeEntries drops exculpatory entries', () => {
  assert.equal(activeEntries(person('absuelto', 'archivado', 'juicio_oral')).length, 1);
});


// The qualifier tracks the stage rather than blanketing the page: hedging a
// firm sentence would misstate a proven fact, and hedging an acquittal would
// read as insinuation. Both are worse than not hedging at all.
test('an open proceeding attributes the crime as presunto', () => {
  for (const stage of ['investigacion_preliminar', 'investigacion_preparatoria',
                       'acusacion_fiscal', 'juicio_oral', 'sentencia_no_firme']) {
    assert.equal(isAlleged(stage), true, stage);
  }
});

test('a final sentence is a fact, not an allegation', () => {
  assert.equal(isAlleged('sentencia_firme'), false);
});

test('an exculpatory outcome is never qualified', () => {
  for (const stage of ['absuelto', 'archivado', 'prescrito']) {
    assert.equal(isAlleged(stage), false, stage);
  }
});

test('an unknown stage is not qualified, because nothing is known about it', () => {
  assert.equal(isAlleged('no_such_stage'), false);
});

test('a sentence under appeal is still presunto — it is not yet firm', () => {
  assert.equal(stageMeta('sentencia_no_firme').rank > 0, true);
  assert.equal(isAlleged('sentencia_no_firme'), true);
});

// Provenance has to be visible: an entry read off a resolution and one read off
// a newspaper cannot render identically, or the badge overstates what we know.
test('an entry with only press sources is flagged as press-only', () => {
  assert.equal(isPressOnly({ sources: [{ kind: 'press', url: 'https://x' }] }), true);
});

test('one primary source is enough to clear the flag', () => {
  assert.equal(isPressOnly({ sources: [
    { kind: 'press', url: 'https://x' },
    { kind: 'primary', url: 'https://y' },
  ] }), false);
});

test('an entry with no sources is not flagged — the validator rejects it first', () => {
  assert.equal(isPressOnly({ sources: [] }), false);
  assert.equal(isPressOnly({}), false);
});

test('a non-final sentence is labelled by its finality, not by an assumed appeal', () => {
  assert.equal(stageMeta('sentencia_no_firme').label, 'Sentencia no firme');
});

test('the badge summary never calls a non-final sentence a condena', () => {
  const badge = recordBadge({ judicial: [{ id: 'a', stage: 'sentencia_no_firme' }] });
  assert.equal(badge.detail, '1 sentencia no firme');
  assert.ok(!badge.detail.includes('condena'), badge.detail);
});

test('a firm sentence is counted as a condena firme', () => {
  assert.equal(recordBadge({ judicial: [{ id: 'a', stage: 'sentencia_firme' }] }).detail,
               '1 condena firme');
});

test('the three counts read together, worst stage first', () => {
  const badge = recordBadge({ judicial: [
    { id: 'a', stage: 'sentencia_firme' },
    { id: 'b', stage: 'sentencia_no_firme' },
    { id: 'c', stage: 'investigacion_preliminar' },
    { id: 'd', stage: 'archivado' },
  ] });
  assert.equal(badge.detail, '1 condena firme · 1 sentencia no firme · 1 proceso abierto');
  assert.equal(badge.label, 'Sentencia firme');
});
