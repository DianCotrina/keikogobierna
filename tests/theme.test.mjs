import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

function sourceFiles(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.(astro|ts|mjs|css)$/.test(name) ? [path] : [];
  });
}

const sources = sourceFiles('src').map((path) => ({ path, text: readFileSync(path, 'utf8') }));

// A colour written literally ignores the theme. The first dark build shipped
// white Ultimitas cards with pale text this way, from a class in a client script.
test('surfaces and ink come from theme tokens, in every kind of source file', () => {
  const literals = [/\bbg-white\b/, /rgba\(\s*20\s*,\s*20\s*,\s*23/, /#141417/i, /#46464D/i, /#8E8E96/i];
  for (const { path, text } of sources) {
    if (path.endsWith('global.css')) continue;
    // Shareable images are always paper and ink: they travel without the viewer's theme.
    if (path.endsWith('infographic-render.mjs')) continue;
    for (const literal of literals) {
      assert.ok(!literal.test(text), `${path} hard-codes ${literal}`);
    }
  }
});

test('every colour token has a dark value', () => {
  const css = readFileSync('src/styles/global.css', 'utf8');
  const tokens = [...css.match(/@theme \{[\s\S]*?\n\}/)[0].matchAll(/--color-[a-z]+/g)].map((m) => m[0]);
  const dark = css.match(/:root\[data-theme='dark'\] \{[\s\S]*?\n\}/)[0];
  assert.ok(tokens.length > 0);
  for (const token of tokens) assert.ok(dark.includes(`${token}:`), `${token} has no dark value`);
});

// As a module it would run after first paint and flash paper at dark-mode readers.
test('the theme is set by an inline script in the head', () => {
  const base = readFileSync('src/layouts/Base.astro', 'utf8');
  const script = base.indexOf('<script is:inline>');
  assert.ok(script > base.indexOf('<head>') && script < base.indexOf('</head>'));
  assert.ok(base.slice(script).includes('dataset.theme'));
});
