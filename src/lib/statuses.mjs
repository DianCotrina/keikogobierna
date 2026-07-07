export const STATUSES = {
  fulfilled: { label: 'Cumplida', color: 'verde' },
  in_progress: { label: 'En progreso', color: 'ambar' },
  no_progress: { label: 'Sin avance', color: 'plomo' },
  unfulfilled: { label: 'Incumplida', color: 'rojo' },
};

export function statusMeta(status) {
  return STATUSES[status] ?? { label: String(status), color: 'plomo' };
}
