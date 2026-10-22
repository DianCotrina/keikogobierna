import { limaToday, mandateClock, mandateCopy } from '../../lib/mandate.mjs';

function render(root: HTMLElement) {
  const clock = mandateClock(limaToday());
  const copy = mandateCopy(clock);

  root.dataset.phase = clock.phase;
  root.querySelector('[data-dc-day]')!.textContent = copy.day;
  root.querySelector('[data-dc-of]')!.textContent = copy.of;
  root.querySelector('[data-dc-note]')!.textContent = copy.note;
  root.querySelector('[data-dc-ruler]')!.setAttribute('aria-label', copy.label);

  root.querySelectorAll<HTMLElement>('.dc-tick').forEach((tick, i) => {
    const n = i + 1;
    tick.dataset.state = n < clock.elapsed ? 'past' : n === clock.elapsed ? 'today' : 'future';
  });
}

document.querySelectorAll<HTMLElement>('[data-day-counter]').forEach((root) => {
  render(root);
  // A page left open past Lima midnight should turn over to the next day.
  setInterval(() => render(root), 60_000);
});
