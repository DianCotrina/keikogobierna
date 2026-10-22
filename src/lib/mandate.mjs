// The government's clock. Days are counted in Lima time, with inauguration
// day as day 1, so the counter reads the same everywhere in Peru regardless
// of the visitor's own timezone or when the site was last built.

import { formatDateEs, plural } from './format.mjs';

export const INAUGURATION = '2026-07-28';
export const DEADLINE_DAYS = 100;

const DAY_MS = 86_400_000;

// en-CA formats as YYYY-MM-DD, which is exactly the ISO date we want.
const limaFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'America/Lima',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

export function limaToday(now = new Date()) {
  return limaFormatter.format(now);
}

function isoToUtcMs(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return Date.UTC(y, m - 1, d);
}

export function addDays(iso, n) {
  return new Date(isoToUtcMs(iso) + n * DAY_MS).toISOString().slice(0, 10);
}

// Day 1 is inauguration day; anything before it is 0 or negative.
export function governmentDay(todayIso) {
  return Math.round((isoToUtcMs(todayIso) - isoToUtcMs(INAUGURATION)) / DAY_MS) + 1;
}

// The last day inside the 100-day window.
export const DEADLINE = addDays(INAUGURATION, DEADLINE_DAYS - 1);

export function mandateClock(todayIso) {
  const day = governmentDay(todayIso);
  let phase;
  if (day < 1) phase = 'before';
  else if (day < DEADLINE_DAYS) phase = 'running';
  else if (day === DEADLINE_DAYS) phase = 'deadline';
  else phase = 'over';

  // Days of the window that have elapsed, today included, clamped to the ruler.
  const elapsed = Math.min(Math.max(day, 0), DEADLINE_DAYS);
  return {
    day,
    phase,
    elapsed,
    remaining: DEADLINE_DAYS - elapsed,
    overdue: Math.max(day - DEADLINE_DAYS, 0),
  };
}

// Visitor-facing copy for the counter. Shared by the build-time render and the
// browser refresh so both always say the same thing for the same day.
export function mandateCopy(clock) {
  const deadline = formatDateEs(DEADLINE);
  switch (clock.phase) {
    case 'before':
      return {
        day: '0',
        of: `de ${DEADLINE_DAYS}`,
        note: `El gobierno asume el ${formatDateEs(INAUGURATION)}.`,
        label: `El plazo de ${DEADLINE_DAYS} días aún no empieza.`,
      };
    case 'deadline':
      return {
        day: String(clock.day),
        of: `de ${DEADLINE_DAYS}`,
        note: `Hoy, ${deadline}, vence el plazo de los ${DEADLINE_DAYS} días.`,
        label: `Día ${clock.day} de ${DEADLINE_DAYS}: hoy vence el plazo.`,
      };
    case 'over':
      return {
        day: String(clock.day),
        of: 'de gobierno',
        note: `El plazo de los ${DEADLINE_DAYS} días venció el ${deadline}, hace ${plural(clock.overdue, 'día', 'días')}.`,
        label: `Día ${clock.day} de gobierno: el plazo de ${DEADLINE_DAYS} días venció hace ${plural(clock.overdue, 'día', 'días')}.`,
      };
    default:
      return {
        day: String(clock.day),
        of: `de ${DEADLINE_DAYS}`,
        note: `${clock.remaining === 1 ? 'Falta' : 'Faltan'} ${plural(clock.remaining, 'día', 'días')} para que venza el plazo, el ${deadline}.`,
        label: `Día ${clock.day} de ${DEADLINE_DAYS}: ${clock.remaining === 1 ? 'falta' : 'faltan'} ${plural(clock.remaining, 'día', 'días')}.`,
      };
  }
}
