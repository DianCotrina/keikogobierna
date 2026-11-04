import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { breadcrumbs, canonicalUrl, jsonLd } from '../src/lib/seo.mjs';
import { loadTopics, loadTracking, topicStatus } from '../src/lib/plan.mjs';

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

test('jsonLd cannot close its own script tag', () => {
  const out = jsonLd({ name: '</script><script>alert(1)</script>' });
  assert.ok(!out.includes('<'));
  assert.equal(JSON.parse(out).name, '</script><script>alert(1)</script>');
});

test('breadcrumbs number from 1 and use canonical URLs', () => {
  const { itemListElement } = breadcrumbs([['Inicio', '/'], ['Turismo', '/temas/turismo']], SITE);
  assert.deepEqual(itemListElement.map((item) => [item.position, item.item]), [
    [1, `${SITE}/`],
    [2, `${SITE}/temas/turismo/`],
  ]);
});

test('topicStatus reports the real record, newest norm first', () => {
  const topics = loadTopics();
  const tracking = loadTracking();
  const turismo = topicStatus(topics, tracking, 't2-7');
  assert.ok(turismo.byStatus.in_progress >= 2);
  assert.equal(turismo.started, turismo.byStatus.in_progress + turismo.byStatus.fulfilled);
  assert.match(turismo.latestNorm.source, /El Peruano/);
  for (const id of topics.keys()) {
    const { started, latestNorm } = topicStatus(topics, tracking, id);
    if (started > 0) assert.ok(latestNorm, `${id} started with no norm`);
  }
});
