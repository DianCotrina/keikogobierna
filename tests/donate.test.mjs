import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const css = readFileSync(new URL('../src/components/Donate/donate.css', import.meta.url), 'utf8');

describe('donate dialog', () => {
  test('nothing that holds content is hidden behind a mask', () => {
    // The donation dialog is the site's only funding path, and it was invisible
    // on iOS Safari: .donate-dialog and .donate-card are both transparent by
    // design, so every visible surface came from .ticket — which was drawn
    // through a two-layer `mask` shorthand. Verified by experiment: a mask that
    // resolves to anything not covering the element takes the whole dialog with
    // it, QR included, leaving only a shadow. `mask: none` loses two decorative
    // notches and nothing else.
    //
    // So: no masking in this component. A flourish must never decide whether
    // content renders, in any engine.
    const offenders = css
      .split('\n')
      .map((line, i) => [i + 1, line])
      .filter(([, line]) => /(^|[^-\w])(-webkit-)?mask(-image|-size|-composite)?\s*:/.test(line));

    assert.deepEqual(offenders, [], `donate.css must not mask content:\n${
      offenders.map(([n, l]) => `  ${n}: ${l.trim()}`).join('\n')}`);
  });

  test('the seam still reads as a perforated ticket', () => {
    // What replaces the notches: the dashed rule between the two panels is now
    // the only thing carrying the ticket metaphor, so it has to stay.
    assert.match(css, /border-top:\s*2px dashed/);
  });
});
