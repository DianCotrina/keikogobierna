import { formatDateEs } from '../../lib/format.mjs';

const DATA_URL = 'https://raw.githubusercontent.com/DianCotrina/keikogobierna/ultimitas-data/today.json';

interface Article {
  title: string;
  url: string;
  summary: string;
  author: string;
  published: string;
}

const LIMA = 'America/Lima';
const timeFmt = new Intl.DateTimeFormat('es-PE', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: LIMA });

function limaToday(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: LIMA }).format(new Date());
}

// Third-party text: build every node with textContent — never innerHTML.
function card(article: Article): HTMLElement {
  const el = document.createElement('article');
  el.className = 'ultimitas-card bg-white rounded-lg border border-tinta/10 shadow-card p-6 sm:p-7';

  const meta = document.createElement('p');
  meta.className = 'font-mono text-[0.65rem] uppercase tracking-[0.14em] text-tintafina';
  meta.textContent = `${timeFmt.format(new Date(article.published))} · El Comercio${article.author ? ` · ${article.author}` : ''}`;
  el.append(meta);

  const title = document.createElement('h2');
  title.className = 'font-sans font-bold text-lg mt-1.5 leading-snug';
  title.textContent = article.title;
  el.append(title);

  if (article.summary) {
    const summary = document.createElement('p');
    summary.className = 'mt-2 text-sm leading-[1.7] text-tintasuave';
    summary.textContent = article.summary;
    el.append(summary);
  }

  const linkWrap = document.createElement('p');
  linkWrap.className = 'mt-3';
  const link = document.createElement('a');
  link.href = article.url;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  link.className = 'nav-link font-sans text-sm font-medium';
  link.textContent = 'Leer en El Comercio →';
  linkWrap.append(link);
  el.append(linkWrap);

  return el;
}

async function load(): Promise<void> {
  const list = document.getElementById('ultimitas-list');
  const dateEl = document.getElementById('ultimitas-date');
  const errorEl = document.getElementById('ultimitas-error');
  if (!list || !dateEl || !errorEl) return;

  try {
    const resp = await fetch(DATA_URL, { cache: 'no-cache' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data: { date: string; articles: Article[] } = await resp.json();
    if (!data.date || !Array.isArray(data.articles) || data.articles.length === 0) {
      throw new Error('empty payload');
    }
    const suffix = data.date === limaToday() ? '' : ' · último día con noticias';
    dateEl.textContent = `Ultimitas del ${formatDateEs(data.date)}${suffix}`;
    list.replaceChildren(...data.articles.map(card));
  } catch (err) {
    console.error('ultimitas:', err);
    dateEl.textContent = 'Ultimitas';
    list.classList.add('hidden');
    errorEl.classList.remove('hidden');
  }
}

load();
