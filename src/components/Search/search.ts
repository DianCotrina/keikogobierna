import { prepare, searchCorpus } from '../../lib/search.mjs';

// Behaviour for the buscador overlay. The matching itself lives in
// src/lib/search.mjs so the same code runs under `npm test`; this file is only
// plumbing: open/close, fetch once, debounce, render.
//
// Results are built with createElement + textContent, never innerHTML — the
// same rule Ultimitas follows. The content is our own plan data, but a
// highlighter is exactly the code someone later points at untrusted text.

interface CorpusItem {
  i: string;
  k: 'p' | 'c' | 'm';
  t: string;
  g?: string;
  x: string;
  q?: string;
}
interface Hit {
  item: CorpusItem;
  ranges: [number, number][];
}
interface Group {
  slug: string;
  name: string;
  count: number;
  items: Hit[];
}

const KIND_LABEL: Record<string, string> = {
  p: 'Propuesta',
  c: 'Primeros 100 días',
  m: 'Meta al 2031',
};

const trigger = document.getElementById('search-trigger') as HTMLButtonElement | null;
const overlay = document.getElementById('search-overlay');
const panel = document.getElementById('search-panel');
const input = document.getElementById('search-input') as HTMLInputElement | null;
const status = document.getElementById('search-status');
const results = document.getElementById('search-results');

if (trigger && overlay && panel && input && status && results) {
  let prepared: ReturnType<typeof prepare> | null = null;
  let loading: Promise<void> | null = null;
  let expanded = new Set<string>();
  let activeIndex = -1;
  let debounce: number | undefined;

  // Nothing here works without JavaScript, so the trigger only appears now.
  trigger.hidden = false;

  const rows = () => Array.from(results.querySelectorAll<HTMLAnchorElement>('.search-hit'));

  function setActive(next: number): void {
    const all = rows();
    if (all.length === 0) return;
    activeIndex = (next + all.length) % all.length;
    all.forEach((row, i) => row.setAttribute('data-active', String(i === activeIndex)));
    all[activeIndex].scrollIntoView({ block: 'nearest' });
  }

  /** The text with each matched range wrapped in <mark>. */
  function highlighted(text: string, ranges: [number, number][]): DocumentFragment {
    const fragment = document.createDocumentFragment();
    let cursor = 0;
    for (const [start, end] of ranges) {
      // A match can land inside a meta's indicator, which is searched but not
      // shown. Those offsets fall past the displayed text; drop them.
      if (start >= text.length) break;
      if (start > cursor) fragment.append(text.slice(cursor, start));
      const mark = document.createElement('mark');
      mark.textContent = text.slice(start, Math.min(end, text.length));
      fragment.append(mark);
      cursor = Math.min(end, text.length);
    }
    if (cursor < text.length) fragment.append(text.slice(cursor));
    return fragment;
  }

  function renderHit(group: Group, hit: Hit): HTMLAnchorElement {
    const link = document.createElement('a');
    link.className = 'search-hit';
    link.href = `/temas/${group.slug}/#${hit.item.i}`;

    const id = document.createElement('span');
    id.className = 'search-hit-id';
    id.textContent = hit.item.i.split('.')[1] ?? hit.item.i;

    const body = document.createElement('span');
    const text = document.createElement('span');
    text.className = 'search-hit-text';
    text.append(highlighted(hit.item.x, hit.ranges));
    const meta = document.createElement('span');
    meta.className = 'search-hit-meta';
    meta.textContent = hit.item.g
      ? `${KIND_LABEL[hit.item.k]} · ${hit.item.g}`
      : KIND_LABEL[hit.item.k];
    body.append(text, meta);

    link.append(id, body);
    return link;
  }

  function renderGroup(group: Group): HTMLElement {
    const section = document.createElement('section');
    section.className = 'search-group';

    const head = document.createElement('p');
    head.className = 'search-group-head';
    const name = document.createElement('span');
    name.textContent = group.name;
    const count = document.createElement('span');
    count.className = 'search-group-count';
    count.textContent = String(group.count);
    head.append(name, count);
    section.append(head);

    for (const hit of group.items) section.append(renderHit(group, hit));

    if (group.count > group.items.length) {
      const rest = group.count - group.items.length;
      const more = document.createElement('button');
      more.type = 'button';
      more.className = 'search-more';
      more.textContent = `… ${rest} ${rest === 1 ? 'más' : 'más'} en este tema`;
      more.addEventListener('click', () => {
        expanded.add(group.slug);
        run(input!.value);
      });
      section.append(more);
    }
    return section;
  }

  function renderEmpty(title: string, body: string): void {
    const box = document.createElement('div');
    box.className = 'search-empty';
    const heading = document.createElement('p');
    heading.className = 'search-empty-title';
    heading.textContent = title;
    const copy = document.createElement('p');
    copy.className = 'search-empty-body';
    copy.textContent = body;
    box.append(heading, copy);
    results!.replaceChildren(box);
  }

  function run(query: string): void {
    if (!prepared) return;
    // Expanded temas need every hit; the rest stay capped. One extra pass over
    // 764 records costs ~0.02 ms, so this is cheaper than tracking two results.
    const capped = searchCorpus(prepared, query);
    const full = expanded.size > 0
      ? searchCorpus(prepared, query, { limitPerGroup: Infinity })
      : capped;
    activeIndex = -1;

    if (capped.mode === 'idle') {
      status!.textContent = '';
      status!.removeAttribute('data-mode');
      results!.replaceChildren();
      return;
    }

    if (capped.total === 0) {
      status!.textContent = '';
      status!.removeAttribute('data-mode');
      renderEmpty(
        `Sin resultados para «${query.trim()}»`,
        'Revisa la ortografía o prueba con una palabra más general. La búsqueda cubre el texto del plan, no las noticias.',
      );
      return;
    }

    const temas = capped.groups.length === 1 ? 'tema' : 'temas';
    const items = capped.total === 1 ? 'resultado' : 'resultados';
    if (capped.mode === 'widened') {
      status!.dataset.mode = 'widened';
      status!.textContent = `Ningún resultado con todas las palabras. ${capped.total} ${items} con coincidencias parciales, en ${capped.groups.length} ${temas}.`;
    } else {
      status!.removeAttribute('data-mode');
      status!.textContent = `${capped.total} ${items} en ${capped.groups.length} ${temas}`;
    }

    results!.replaceChildren(...capped.groups.map((group: Group) => renderGroup(
      expanded.has(group.slug)
        ? full.groups.find((g: Group) => g.slug === group.slug) ?? group
        : group,
    )));
  }

  async function load(): Promise<void> {
    if (prepared) return;
    if (!loading) {
      loading = (async () => {
        const version = trigger!.dataset.version ?? '0';
        const response = await fetch(`/buscar.json?v=${encodeURIComponent(version)}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        prepared = prepare(await response.json());
      })();
    }
    try {
      await loading;
      run(input!.value);
    } catch {
      loading = null;
      renderEmpty(
        'No se pudo cargar el buscador',
        'Revisa tu conexión e inténtalo de nuevo. Mientras tanto, puedes navegar los temas desde el inicio.',
      );
    }
  }

  function open(): void {
    overlay!.hidden = false;
    trigger!.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
    input!.focus();
    input!.select();
    void load();
  }

  function close(): void {
    overlay!.hidden = true;
    trigger!.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
    trigger!.focus();
  }

  trigger.addEventListener('click', open);
  for (const dismiss of overlay.querySelectorAll('[data-search-close]')) {
    dismiss.addEventListener('click', close);
  }

  input.addEventListener('input', () => {
    expanded = new Set();
    window.clearTimeout(debounce);
    debounce = window.setTimeout(() => run(input.value), 120);
  });

  // "/" opens search the way it does on most documentation sites; Cmd/Ctrl+K
  // for the people who expect a command palette.
  document.addEventListener('keydown', (event) => {
    const target = event.target as HTMLElement | null;
    const typing = target !== null
      && (/^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName) || target.isContentEditable);
    const shortcut = event.key === '/' || ((event.metaKey || event.ctrlKey) && event.key === 'k');
    if (overlay.hidden && shortcut && !typing) {
      event.preventDefault();
      open();
    }
  });

  panel.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') { event.preventDefault(); close(); return; }
    if (event.key === 'ArrowDown') { event.preventDefault(); setActive(activeIndex + 1); return; }
    if (event.key === 'ArrowUp') { event.preventDefault(); setActive(activeIndex - 1); return; }
    if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      rows()[activeIndex]?.click();
      return;
    }
    if (event.key !== 'Tab') return;
    // The dialog is modal, so Tab must cycle inside it.
    const focusable = panel.querySelectorAll<HTMLElement>('a[href], button, input');
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
}
