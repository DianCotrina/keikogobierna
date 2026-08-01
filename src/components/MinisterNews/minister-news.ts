import { formatDateEs } from '../../lib/format.mjs';
import { safeHttpUrl } from '../../lib/safe-url.mjs';
import { entriesFor } from '../../lib/minister-news.mjs';

const DATA_URL =
  'https://raw.githubusercontent.com/DianCotrina/keikogobierna/ultimitas-data/ministros.json';

interface Entry {
  title: string;
  url: string;
  source: string;
  published: string;
}

// Third-party text: every node built with textContent, never innerHTML.
function item(entry: Entry): HTMLElement {
  const li = document.createElement('li');
  li.className = 'bg-white rounded-lg border border-tinta/10 shadow-card p-5 sm:p-6';

  const meta = document.createElement('p');
  meta.className = 'font-mono text-[0.65rem] uppercase tracking-[0.14em] text-tintafina';
  meta.textContent = `${entry.source} · ${formatDateEs(entry.published.slice(0, 10))}`;
  li.appendChild(meta);

  const href = safeHttpUrl(entry.url);
  const headline = document.createElement(href ? 'a' : 'p');
  headline.className = 'mt-1.5 block font-sans font-bold text-base leading-snug';
  headline.textContent = entry.title;
  if (href && headline instanceof HTMLAnchorElement) {
    headline.href = href;
    headline.target = '_blank';
    headline.rel = 'noopener noreferrer';
    headline.classList.add('nav-link');
  }
  li.appendChild(headline);
  return li;
}

async function load(): Promise<void> {
  const section = document.querySelector<HTMLElement>('[data-minister-news]');
  const list = document.getElementById('minister-news-list');
  const empty = document.getElementById('minister-news-empty');
  if (!section || !list || !empty) return;

  const slug = section.dataset.slug;
  if (!slug) return;

  try {
    const resp = await fetch(DATA_URL, { cache: 'no-cache' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const entries: Entry[] = entriesFor(await resp.json(), slug);
    if (entries.length === 0) {
      empty.classList.remove('hidden');
      return;
    }
    list.replaceChildren(...entries.map(item));
  } catch (err) {
    // A scraper outage must never mark up a dossier. Say nothing, break nothing.
    console.error('minister-news:', err);
    empty.classList.remove('hidden');
  }
}

load();
