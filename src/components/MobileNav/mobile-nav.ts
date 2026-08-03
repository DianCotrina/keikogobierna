const trigger = document.getElementById('menu-trigger') as HTMLButtonElement | null;
const panel = document.getElementById('menu-panel');
const backdrop = document.getElementById('menu-backdrop');

if (trigger && panel && backdrop) {
  // Nothing here works without JavaScript, so the trigger only appears now.
  trigger.hidden = false;

  // The lock goes on <html>, not <body>: locking the body turns it into a
  // non-scrolling container, which collapses the scroll offset and drops the
  // sticky header out of the viewport — menu and all.
  function open(): void {
    panel!.hidden = false;
    backdrop!.hidden = false;
    trigger!.setAttribute('aria-expanded', 'true');
    trigger!.setAttribute('aria-label', 'Cerrar el menú');
    document.documentElement.style.overflow = 'hidden';
    panel!.querySelector<HTMLAnchorElement>('.menu-row')?.focus();
  }

  // Links close the menu on their way out; restoring focus to the trigger
  // there would scroll the header back into view and undo the jump.
  function close(restoreFocus = true): void {
    panel!.hidden = true;
    backdrop!.hidden = true;
    trigger!.setAttribute('aria-expanded', 'false');
    trigger!.setAttribute('aria-label', 'Abrir el menú');
    document.documentElement.style.overflow = '';
    if (restoreFocus) trigger!.focus();
  }

  trigger.addEventListener('click', () => {
    if (panel.hidden) open(); else close();
  });

  backdrop.addEventListener('click', () => close());

  for (const link of panel.querySelectorAll('[data-menu-close]')) {
    link.addEventListener('click', () => close(false));
  }

  // Listening on the document, not the panel: while the sheet is open the
  // trigger is part of the loop, and focus can sit on either.
  document.addEventListener('keydown', (event) => {
    if (panel.hidden) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }

    if (event.key !== 'Tab') return;
    // The sheet is modal, so Tab must cycle inside it.
    const focusable: HTMLElement[] = [trigger, ...panel.querySelectorAll<HTMLElement>('a[href]')];
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

  // The desktop nav takes over at md, so a rotation to landscape must not
  // leave the sheet open over it.
  window.matchMedia('(min-width: 768px)').addEventListener('change', (event) => {
    if (event.matches && !panel.hidden) close(false);
  });
}
