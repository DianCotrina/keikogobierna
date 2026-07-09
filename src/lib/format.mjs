const MONTH_NAMES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
];

export function formatDateEs(iso) {
  const [year, month, day] = iso.split('-').map(Number);
  return `${day} de ${MONTH_NAMES[month - 1]} de ${year}`;
}
