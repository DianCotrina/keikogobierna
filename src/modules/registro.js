import { esc, stamp } from '../lib/dom.js';

export function renderRegistro(el, data) {
  el.innerHTML = data.actualizaciones.map((a) => `
    <li class="reveal flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-6 p-5 sm:p-6">
      <span class="font-mono text-xs text-tintafina shrink-0 sm:w-28">${esc(a.fecha_texto)}</span>
      <p class="flex-1 text-sm sm:text-base">${esc(a.texto)}</p>
      ${stamp(a.status)}
    </li>`).join('');
}
