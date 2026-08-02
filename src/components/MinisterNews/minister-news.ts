import { formatDateEs } from '../../lib/format.mjs';
import { safeHttpUrl } from '../../lib/safe-url.mjs';
import { resolveCoverage } from '../../lib/minister-news.mjs';

const DATA_URL =
  'https://raw.githubusercontent.com/DianCotrina/keikogobierna/ultimitas-data/ministros.json';

interface Entry {
  title: string;
  url: string;
  source: string;
  published: string;
  matched_in: 'title' | 'summary';
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

  // The headline alone can name someone else entirely, with this minister
  // named only in the feed summary the reader never sees (see `matched_in`
  // in minister-news.mjs). Say so rather than let presence read as aboutness.
  if (entry.matched_in === 'summary') {
    const note = document.createElement('p');
    note.className = 'mt-1 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-tintafina';
    note.textContent = 'Mencionado en esta nota';
    li.appendChild(note);
  }

  return li;
}

async function load(): Promise<void> {
  const section = document.querySelector<HTMLElement>('[data-minister-news]');
  const list = document.getElementById('minister-news-list');
  const empty = document.getElementById('minister-news-empty');
  const error = document.getElementById('minister-news-error');
  if (!section || !list || !empty || !error) return;

  const slug = section.dataset.slug;
  if (!slug) return;

  try {
    const resp = await fetch(DATA_URL, { cache: 'no-cache' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const payload = await resp.json();
    // The lib decides list vs. empty vs. error — including staleness and
    // "every entry for this slug was malformed" — so this file only draws
    // the answer, never re-derives it.
    const result = resolveCoverage(payload, slug);
    if (result.status === 'error') {
      error.classList.remove('hidden');
      return;
    }
    if (result.status === 'empty') {
      // Confirmed no coverage — distinct from "could not check" above.
      empty.classList.remove('hidden');
      return;
    }
    list.replaceChildren(...(result.entries as Entry[]).map(item));
  } catch (err) {
    // A scraper outage must never mark up a dossier, and must never claim
    // "no coverage" when the truth is "could not check." Say nothing false,
    // break nothing.
    console.error('minister-news:', err);
    error.classList.remove('hidden');
  }
}

load();
