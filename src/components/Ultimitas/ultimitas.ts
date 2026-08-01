import { formatDateEs } from '../../lib/format.mjs';
import { safeHttpUrl } from '../../lib/safe-url.mjs';

const DATA_URL = 'https://raw.githubusercontent.com/DianCotrina/keikogobierna/ultimitas-data/today.json';
// Records written before the source field existed are all El Comercio.
const DEFAULT_SOURCE = 'El Comercio';

interface Article {
  title: string;
  url: string;
  summary: string;
  author: string;
  published: string;
  source?: string;
}

const LIMA = 'America/Lima';
const timeFmt = new Intl.DateTimeFormat('es-PE', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: LIMA });

function limaToday(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: LIMA }).format(new Date());
}

// Third-party text: build every node with textContent — never innerHTML.
function card(article: Article): HTMLElement {
  const source = article.source ?? DEFAULT_SOURCE;
  const el = document.createElement('article');
  el.className = 'ultimitas-card bg-white rounded-lg border border-tinta/10 shadow-card p-6 sm:p-7';
  el.dataset.source = source;

  const head = document.createElement('div');
  head.className = 'flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5';
  const meta = document.createElement('p');
  meta.className = 'font-mono text-[0.65rem] uppercase tracking-[0.14em] text-tintafina';
  meta.textContent = `${timeFmt.format(new Date(article.published))}${article.author ? ` · ${article.author}` : ''}`;
  const chip = document.createElement('span');
  chip.className = 'ultimitas-source';
  chip.textContent = source;
  head.append(meta, chip);
  el.append(head);

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

  const safeUrl = safeHttpUrl(article.url);
  if (safeUrl) {
    const linkWrap = document.createElement('p');
    linkWrap.className = 'mt-3';
    const link = document.createElement('a');
    link.href = safeUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.className = 'nav-link font-sans text-sm font-medium';
    link.textContent = `Leer en ${source} →`;
    linkWrap.append(link);
    el.append(linkWrap);
  }

  return el;
}

function applyFilter(list: HTMLElement, emptyEl: HTMLElement, filter: string): void {
  let visible = 0;
  for (const el of list.querySelectorAll<HTMLElement>('.ultimitas-card')) {
    const show = filter === 'all' || el.dataset.source === filter;
    el.hidden = !show;
    if (show) visible += 1;
  }
  emptyEl.textContent = `Sin titulares de ${filter} este día.`;
  emptyEl.classList.toggle('hidden', filter === 'all' || visible > 0);
}

function renderFilters(bar: HTMLElement, list: HTMLElement, emptyEl: HTMLElement, sources: string[]): void {
  // Chips come from the data, not a hardcoded outlet list; skip on single-source days.
  if (sources.length < 2) return;
  const options = ['all', ...sources];
  for (const option of options) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'ultimitas-filter';
    btn.textContent = option === 'all' ? 'Todas' : option;
    btn.setAttribute('aria-pressed', String(option === 'all'));
    btn.addEventListener('click', () => {
      for (const other of bar.querySelectorAll('button')) other.setAttribute('aria-pressed', 'false');
      btn.setAttribute('aria-pressed', 'true');
      applyFilter(list, emptyEl, option);
    });
    bar.append(btn);
  }
  bar.hidden = false;
}

async function load(): Promise<void> {
  const list = document.getElementById('ultimitas-list');
  const dateEl = document.getElementById('ultimitas-date');
  const errorEl = document.getElementById('ultimitas-error');
  const filtersEl = document.getElementById('ultimitas-filters');
  const filterEmptyEl = document.getElementById('ultimitas-filter-empty');
  if (!list || !dateEl || !errorEl || !filtersEl || !filterEmptyEl) return;

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
    const sources = [...new Set(data.articles.map((a) => a.source ?? DEFAULT_SOURCE))];
    renderFilters(filtersEl, list, filterEmptyEl, sources);
  } catch (err) {
    console.error('ultimitas:', err);
    dateEl.textContent = 'Ultimitas';
    list.classList.add('hidden');
    errorEl.classList.remove('hidden');
  }
}

load();
