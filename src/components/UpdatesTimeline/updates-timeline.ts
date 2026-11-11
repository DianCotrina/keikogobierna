// Updates timeline behaviour. State lives in data attributes so the CSS is the
// only place that decides what an open or pinned row looks like.
//
//   hover (mouse/pen)  opens the row, never closes others; leaving the list
//                      closes every row except the pinned one
//   click / tap        pins the row (one at a time); again to release
//   focus              opens the focused row only; arrows, Home and End move
//   Escape             closes everything and releases the pin

const LEAVE_GRACE_MS = 120;
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function init(root: HTMLElement) {
  const list = root.querySelector<HTMLOListElement>('[data-list]');
  const stage = root.querySelector<HTMLElement>('[data-stage]');
  const viewport = root.querySelector<HTMLElement>('[data-viewport]');
  const rail = root.querySelector<HTMLElement>('[data-rail]');
  const railHi = root.querySelector<HTMLElement>('[data-rail-hi]');
  const footState = root.querySelector<HTMLElement>('[data-foot-state]');
  const announce = root.querySelector<HTMLElement>('[data-announce]');
  if (!list || !stage || !viewport || !rail || !railHi) return;

  const rows = [...list.querySelectorAll<HTMLLIElement>('[data-entry]')];
  const triggers = rows.map((row) => row.querySelector<HTMLButtonElement>('[data-trigger]')!);
  const visible = Math.max(1, Number(root.dataset.visible) || 9);

  let pinned: HTMLLIElement | null = null;
  // The row the rail highlights: the last one opened.
  let active: HTMLLIElement | null = null;
  let leaveTimer = 0;
  let frame = 0;

  const isOpen = (row: HTMLLIElement) => row.dataset.open === 'true';

  function setOpen(row: HTMLLIElement, open: boolean) {
    if (isOpen(row) === open) return;
    row.dataset.open = String(open);
    row.querySelector('[data-trigger]')?.setAttribute('aria-expanded', String(open));
  }

  function setActive(row: HTMLLIElement | null) {
    active = row;
    schedule();
  }

  function open(row: HTMLLIElement, { only = false } = {}) {
    if (only) rows.forEach((other) => other !== row && other !== pinned && setOpen(other, false));
    setOpen(row, true);
    setActive(row);
  }

  function closeAll() {
    rows.forEach((row) => row !== pinned && setOpen(row, false));
    setActive(pinned);
  }

  function pin(row: HTMLLIElement | null) {
    if (pinned) {
      pinned.dataset.pinned = 'false';
      pinned.querySelector('[data-trigger]')?.setAttribute('aria-pressed', 'false');
    }
    pinned = row;
    if (row) {
      row.dataset.pinned = 'true';
      row.querySelector('[data-trigger]')?.setAttribute('aria-pressed', 'true');
      open(row, { only: true });
    } else {
      closeAll();
    }
    const title = row?.querySelector('.tl-title')?.textContent?.trim();
    if (footState) footState.textContent = row ? 'Fila fijada · vuelve a hacer clic para soltarla' : 'Ninguna fila fijada';
    if (announce) announce.textContent = row ? `Fijada: ${title}` : 'Ninguna fila fijada.';
  }

  // Geometry is read once the DOM settles; rows open instantly, so there is no
  // in-between state to chase.
  function measure() {
    frame = 0;
    const origin = stage!.getBoundingClientRect().top;
    const nodes = rows.map((row) => row.querySelector('[data-node]')!.getBoundingClientRect());
    const first = nodes[0];
    const last = nodes.at(-1);
    if (first && last) {
      const start = first.top + first.height / 2 - origin;
      rail!.style.transform = `translateY(${start}px)`;
      rail!.style.height = `${last.top + last.height / 2 - first.top - first.height / 2}px`;
    }
    if (active) {
      const box = active.getBoundingClientRect();
      railHi!.style.setProperty('--tone', active.style.getPropertyValue('--tone'));
      railHi!.style.transform = `translateY(${box.top - origin}px) scaleY(${box.height})`;
      railHi!.style.opacity = '1';
    } else {
      railHi!.style.opacity = '0';
    }
  }

  function schedule() {
    if (!frame) frame = requestAnimationFrame(measure);
  }

  // Half of the next row's header stays in view, so the list reads as scrollable.
  function fitViewport() {
    const peek = rows[visible];
    if (!peek) {
      viewport!.style.maxHeight = '';
      return;
    }
    const header = peek.querySelector('[data-trigger]')!.getBoundingClientRect();
    viewport!.style.maxHeight = `${peek.getBoundingClientRect().top - stage!.getBoundingClientRect().top + header.height / 2}px`;
  }

  list.addEventListener('pointermove', (event) => {
    if (event.pointerType === 'touch') return;
    clearTimeout(leaveTimer);
    const row = (event.target as Element).closest<HTMLLIElement>('[data-entry]');
    if (row && row !== active && !pinned) open(row);
  });
  list.addEventListener('pointerenter', () => clearTimeout(leaveTimer));
  list.addEventListener('pointerleave', (event) => {
    if (event.pointerType === 'touch') return;
    clearTimeout(leaveTimer);
    leaveTimer = window.setTimeout(() => {
      if (!list.querySelector(':focus-visible')) closeAll();
    }, reducedMotion() ? 0 : LEAVE_GRACE_MS);
  });

  triggers.forEach((trigger, index) => {
    const row = rows[index];
    trigger.addEventListener('click', () => {
      clearTimeout(leaveTimer);
      pin(pinned === row ? null : row);
    });
    trigger.addEventListener('focus', () => {
      if (trigger.matches(':focus-visible') && !pinned) open(row, { only: true });
    });
    trigger.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        pin(null);
        closeAll();
        return;
      }
      const target =
        event.key === 'ArrowDown' ? (index + 1) % triggers.length
        : event.key === 'ArrowUp' ? (index - 1 + triggers.length) % triggers.length
        : event.key === 'Home' ? 0
        : event.key === 'End' ? triggers.length - 1
        : -1;
      if (target < 0) return;
      event.preventDefault();
      triggers[target].focus();
    });
  });

  list.addEventListener('focusout', (event) => {
    if (!list.contains(event.relatedTarget as Node | null) && !pinned) closeAll();
  });

  const observer = new ResizeObserver(() => {
    fitViewport();
    schedule();
  });
  observer.observe(stage);
  document.fonts?.ready.then(() => {
    fitViewport();
    schedule();
  });
  fitViewport();
  measure();
}

document.querySelectorAll<HTMLElement>('[data-timeline]').forEach(init);
