const MONTH_NAMES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
];

// Spelled out rather than derived from Intl on purpose: the build must render
// the same month names whatever ICU data the host node happens to ship.
const MONTH_ABBR = [
  'ene', 'feb', 'mar', 'abr', 'may', 'jun',
  'jul', 'ago', 'set', 'oct', 'nov', 'dic',
];

export function formatDateEs(iso) {
  const [year, month, day] = iso.split('-').map(Number);
  return `${day} de ${MONTH_NAMES[month - 1]} de ${year}`;
}

/** Compact form for dense rows: "28 jul 2026". */
export function formatDateEsShort(iso) {
  const [year, month, day] = iso.split('-').map(Number);
  return `${day} ${MONTH_ABBR[month - 1]} ${year}`;
}

/** "1 día" / "2 días" — Spanish agreement, in one place. */
export function plural(n, one, many) {
  return `${n} ${n === 1 ? one : many}`;
}
