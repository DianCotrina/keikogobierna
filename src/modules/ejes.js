import { esc } from '../lib/dom.js';

export function renderEjes(el, data) {
  el.innerHTML = data.ejes.map((eje) => `
    <a href="#" class="card-hover reveal block bg-white rounded-lg border border-tinta/10 shadow-card p-6" data-eje="${esc(eje.id)}">
      <div class="flex items-baseline justify-between">
        <h3 class="font-sans font-bold text-lg">${esc(eje.nombre)}</h3>
        <span class="font-mono text-xs text-tintafina">${esc(eje.compromisos)} comp.</span>
      </div>
      <div class="mt-4 h-1.5 rounded-full bg-tinta/10 overflow-hidden"><div class="h-full rounded-full bg-tinta" style="width:${esc(eje.avance)}%"></div></div>
      <p class="mt-3 font-mono text-xs text-tintasuave">${esc(eje.avance)} % de avance</p>
    </a>`).join('');
}
