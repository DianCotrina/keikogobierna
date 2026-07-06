export function esc(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

export const STATUSES = {
  fulfilled:   { label: 'Cumplida',    color: 'verde' },
  in_progress: { label: 'En progreso', color: 'ambar' },
  no_progress: { label: 'Sin avance',  color: 'plomo' },
  unfulfilled: { label: 'Incumplida',  color: 'rojo' },
};

export function stamp(status) {
  const { label, color } = STATUSES[status] ?? { label: String(status), color: 'plomo' };
  return `<span class="stamp text-${color} shrink-0">${esc(label)}</span>`;
}
