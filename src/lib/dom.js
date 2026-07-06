export function esc(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

export const ESTADOS = {
  cumplida:    { label: 'Cumplida',    color: 'verde' },
  en_progreso: { label: 'En progreso', color: 'ambar' },
  sin_avance:  { label: 'Sin avance',  color: 'plomo' },
  incumplida:  { label: 'Incumplida',  color: 'rojo' },
};

export function stamp(estado) {
  const { label, color } = ESTADOS[estado] ?? { label: String(estado), color: 'plomo' };
  return `<span class="stamp text-${color} shrink-0">${esc(label)}</span>`;
}
