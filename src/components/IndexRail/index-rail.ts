function initIndexRail() {
  const rail = document.getElementById('index-rail');
  const chip = document.getElementById('index-rail-chip');
  const dialog = document.getElementById('index-rail-dialog') as HTMLDialogElement | null;
  const sentinel = document.getElementById('indice');
  if (!rail || !chip || !dialog || !sentinel) return;

  // Active once the inline índice has been scrolled past (its bottom is above
  // the viewport); inactive at page top or while the índice is still visible.
  const visibility = new IntersectionObserver(([entry]) => {
    const active = !entry.isIntersecting && entry.boundingClientRect.bottom < 0;
    rail.classList.toggle('is-active', active);
    chip.classList.toggle('is-active', active);
    if (!active && dialog.open) dialog.close();
  });
  visibility.observe(sentinel);

  // Scrollspy: a section is "current" while it intersects the top ~35% of the
  // viewport; when several do, the one furthest down the document wins. A
  // current child also highlights its parent. Rows exist twice (rail + dialog),
  // hence data-target lookups instead of ids.
  const links = Array.from(document.querySelectorAll<HTMLAnchorElement>('.rail-link[data-target]'));
  const ids = [...new Set(links.map((link) => link.dataset.target!))];

  const parentByTarget = new Map<string, string>();
  rail.querySelectorAll(':scope .rail-tree > li').forEach((li) => {
    const parent = li.querySelector<HTMLElement>(':scope > .rail-link');
    if (!parent?.dataset.target) return;
    li.querySelectorAll<HTMLElement>('.rail-children .rail-link').forEach((child) => {
      if (child.dataset.target) parentByTarget.set(child.dataset.target, parent.dataset.target!);
    });
  });

  let currentId: string | null = null;
  function setCurrent(id: string | null) {
    if (id === currentId) return;
    currentId = id;
    const parentId = id ? parentByTarget.get(id) : undefined;
    links.forEach((link) => {
      const target = link.dataset.target;
      link.classList.toggle('is-current', target === id || (parentId !== undefined && target === parentId));
    });
  }

  const intersecting = new Set<string>();
  const spy = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      const id = (entry.target as HTMLElement).id;
      if (entry.isIntersecting) intersecting.add(id);
      else intersecting.delete(id);
    }
    const current = ids.filter((id) => intersecting.has(id)).at(-1) ?? currentId;
    setCurrent(current);
  }, { rootMargin: '0% 0px -65% 0px' });
  ids.forEach((id) => {
    const el = document.getElementById(id);
    if (el) spy.observe(el);
  });

  // Chip + dialog (same interaction pattern as the Donate dialogs).
  chip.addEventListener('click', () => {
    dialog.showModal();
    chip.setAttribute('aria-expanded', 'true');
  });
  dialog.addEventListener('close', () => chip.setAttribute('aria-expanded', 'false'));
  dialog.querySelector('[data-close]')?.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', () => dialog.close());
  });
}

initIndexRail();
