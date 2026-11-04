// An open trail stays open while the visitor is inside its card and collapses
// once they click or tab somewhere else. It deliberately ignores the mouse
// merely drifting off the card, which happens constantly while reading, and
// window blur, so following a norm to El Peruano doesn't close it.

const SELECTOR = 'details[data-evidence-trail]';
const CLOSE_FALLBACK_MS = 240;

const trails = () => [...document.querySelectorAll<HTMLDetailsElement>(SELECTOR)];
const cardOf = (trail: HTMLDetailsElement) => trail.closest('[data-evidence-card]') ?? trail;
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Collapsing shortens the page, so whatever the visitor just reached below the
// trail would jump upward. Safari has no scroll anchoring, so hold it in place.
function collapse(trail: HTMLDetailsElement, reached?: Element | null) {
  const below = reached && trail.compareDocumentPosition(reached) & Node.DOCUMENT_POSITION_FOLLOWING;
  const before = below ? reached.getBoundingClientRect().top : 0;
  trail.open = false;
  if (below) {
    window.scrollBy({ top: reached.getBoundingClientRect().top - before, behavior: 'instant' });
  }
}

function close(trail: HTMLDetailsElement, reached?: Element | null) {
  if (!trail.open || 'closing' in trail.dataset) return;
  if (reducedMotion()) {
    collapse(trail, reached);
    return;
  }
  trail.dataset.closing = '';
  const finish = () => {
    // Reopened mid-animation: the flag is gone, so leave it open.
    if (!('closing' in trail.dataset)) return;
    delete trail.dataset.closing;
    collapse(trail, reached);
  };
  trail.querySelector('[data-et-body]')?.addEventListener('animationend', finish, { once: true });
  window.setTimeout(finish, CLOSE_FALLBACK_MS);
}

function closeOthers(target: Element) {
  for (const trail of trails()) {
    if (trail.open && !cardOf(trail).contains(target)) close(trail, target);
  }
}

document.addEventListener('click', (event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;

  const summary = target.closest('summary');
  const trail = summary?.closest<HTMLDetailsElement>(SELECTOR);
  if (trail) {
    if ('closing' in trail.dataset) {
      event.preventDefault();
      delete trail.dataset.closing;
    } else if (trail.open) {
      // The browser would drop the content at once; run the exit first.
      event.preventDefault();
      close(trail);
    }
  }
  closeOthers(target);
});

document.addEventListener('focusin', (event) => {
  if (event.target instanceof Element) closeOthers(event.target);
});

document.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape') return;
  const focused = document.activeElement;
  const trail = trails().find((item) => item.open && focused && cardOf(item).contains(focused));
  if (!trail) return;
  close(trail);
  trail.querySelector('summary')?.focus();
});

// A link to a specific commitment should land on it with its trail showing.
function openFromHash() {
  if (!location.hash) return;
  const card = document.getElementById(decodeURIComponent(location.hash.slice(1)));
  const trail = card?.querySelector<HTMLDetailsElement>(SELECTOR);
  if (trail) trail.open = true;
}

openFromHash();
window.addEventListener('hashchange', openFromHash);
