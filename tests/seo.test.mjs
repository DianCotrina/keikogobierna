import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { canonicalUrl } from '../src/lib/seo.mjs';

const SITE = 'https://www.keikogobierna.com';

test('canonicalUrl matches the trailing-slash URL Vercel redirects to', () => {
  assert.equal(canonicalUrl('/', SITE), `${SITE}/`);
  assert.equal(canonicalUrl('/fuentes/', SITE), `${SITE}/fuentes/`);
  assert.equal(canonicalUrl('/fuentes', SITE), `${SITE}/fuentes/`);
  assert.equal(canonicalUrl('/temas/turismo', SITE), `${SITE}/temas/turismo/`);
});

test('canonicalUrl leaves file paths alone', () => {
  assert.equal(canonicalUrl('/api/plan.json', SITE), `${SITE}/api/plan.json`);
});

test('robots.txt allows crawling and declares the sitemap Astro generates', () => {
  const robots = readFileSync('public/robots.txt', 'utf8');
  assert.match(robots, /^Allow: \/$/m);
  assert.ok(!/^Disallow: \S/m.test(robots), 'nothing may be blocked');
  assert.match(robots, new RegExp(`^Sitemap: ${SITE}/sitemap-index\\.xml$`, 'm'));
  assert.match(readFileSync('astro.config.mjs', 'utf8'), /integrations: \[sitemap\(\)\]/);
});

test('the layout points at icon and social files that exist', () => {
  const base = readFileSync('src/layouts/Base.astro', 'utf8');
  for (const file of ['og.png', 'favicon.ico', 'favicon.svg', 'apple-touch-icon.png']) {
    assert.ok(base.includes(`/${file}`), `Base.astro does not reference ${file}`);
    assert.ok(existsSync(`public/${file}`), `public/${file} is missing`);
  }
});
