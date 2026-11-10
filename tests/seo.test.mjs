import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { breadcrumbs, canonicalUrl, graph, jsonLd, minister, webPage } from '../src/lib/seo.mjs';
import { latestDate, ministerLastModified, pageLastModified, topicLastModified } from '../src/lib/freshness.mjs';
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
  assert.match(readFileSync('astro.config.mjs', 'utf8'), /integrations: \[\s*sitemap\(/);
});

test('latestDate picks the newest day and ignores blanks', () => {
  assert.equal(latestDate(['2026-08-01', null, '2026-10-31T12:00:00Z', 'pendiente', '2026-09-15']), '2026-10-31');
  assert.equal(latestDate([]), null);
});

test('topicLastModified reads log, evidence and measurements of that topic only', () => {
  const tracking = {
    log: [{ date: '2026-09-01', item: 't2-1.P01' }, { date: '2026-12-01', item: 't2-10.P01' }],
    items: { 't2-1.C03': { evidence: [{ date: '2026-10-05' }] } },
    measurements: { 't2-1.P22': { points: [{ date: '2026-10-20' }] } },
  };
  assert.equal(topicLastModified(tracking, 't2-1'), '2026-10-20');
  assert.equal(topicLastModified(tracking, 't3-3'), null);
});

test('ministerLastModified covers tenures, normas and judicial entries', () => {
  const data = {
    ministers: [{ slug: 'a', judicial: [{ date: '2026-08-30' }] }],
    tenures: [{ person: 'a', start: '2026-07-28', end: null, appointment_norma: { date: '2026-07-28' } }],
    announcements: [],
  };
  assert.equal(ministerLastModified('a', data), '2026-08-30');
});

test('every lastmod date names a page that is built', () => {
  const map = pageLastModified();
  assert.equal(map.get('/'), loadTracking().updated);
  for (const [path, date] of map) {
    assert.match(date, /^\d{4}-\d{2}-\d{2}$/);
    assert.match(path, /^\/(temas\/[a-z0-9-]+\/|gabinete\/([a-z0-9-]+\/)?|primeros-100-dias\/|fuentes\/)?$/);
  }
});

test('graph drops nested @context and keeps one at the top', () => {
  const out = graph(breadcrumbs([['Inicio', '/']], SITE), { '@type': 'Thing' });
  assert.equal(out['@context'], 'https://schema.org');
  assert.ok(out['@graph'].every((node) => !('@context' in node)));
});

test('webPage omits dateModified when no record backs it', () => {
  assert.ok(!('dateModified' in webPage({ path: '/temas/salud', name: 'Salud', dateModified: null }, SITE)));
  const page = webPage({ path: '/temas/salud', name: 'Salud', dateModified: '2026-10-01' }, SITE);
  assert.equal(page.url, `${SITE}/temas/salud/`);
  assert.equal(page.dateModified, '2026-10-01');
});

test('only a sitting minister is marked up with a post', () => {
  const serving = minister({ name: 'A', slug: 'a', portfolioName: 'Ministerio de Salud', serving: true }, SITE);
  assert.equal(serving.worksFor.name, 'Ministerio de Salud');
  const former = minister({ name: 'B', slug: 'b', portfolioName: 'Ministerio de Salud', serving: false }, SITE);
  assert.ok(!('jobTitle' in former) && !('worksFor' in former));
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
