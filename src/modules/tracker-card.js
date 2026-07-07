import { esc, stamp } from '../lib/dom.js';

export function renderTrackerCard(el, data) {
  const { meta, summary, highlights } = data;
  const filled = Math.round(4 + (396 - 4) * (summary.overall_progress / 100));
  el.innerHTML = `
    <div class="bg-white/85 backdrop-blur rounded-lg shadow-lift border border-tinta/10 p-6 sm:p-7">
      <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-dashed border-tinta/20 pb-4">
        <p class="font-mono text-[0.65rem] sm:text-xs font-semibold uppercase tracking-[0.14em] text-tintasuave">Expediente · Avance general</p>
        <p class="font-mono text-[0.65rem] sm:text-xs text-tintafina whitespace-nowrap">${esc(meta.updated_text)}</p>
      </div>
      <div class="mt-5 flex flex-wrap items-end justify-between gap-x-4 gap-y-1">
        <p class="font-display text-5xl sm:text-6xl" style="letter-spacing:-0.03em">${esc(summary.overall_progress)}<span class="text-3xl">%</span></p>
        <p class="font-mono text-xs text-tintasuave mb-1.5">${esc(summary.total)} compromisos rastreados</p>
      </div>
      <div class="mt-3 h-4 relative" role="img" aria-label="Avance general: ${esc(summary.overall_progress)} por ciento">
        <svg class="absolute inset-0 w-full h-full" viewBox="0 0 400 16" fill="none" preserveAspectRatio="none" aria-hidden="true">
          <path d="M2 8 H 398" stroke="rgba(20,20,23,0.14)" stroke-width="10" stroke-linecap="round"/>
          <path d="M2 9 C 30 5, 60 12, ${filled} 7" stroke="#141417" stroke-width="9" stroke-linecap="round"/>
        </svg>
      </div>
      <div class="mt-6 grid grid-cols-4 gap-2 font-mono text-center">
        <div><p class="text-xl font-semibold text-verde">${esc(summary.statuses.fulfilled)}</p><p class="text-[0.6rem] uppercase tracking-wider text-tintafina mt-1">Cumplidos</p></div>
        <div><p class="text-xl font-semibold text-ambar">${esc(summary.statuses.in_progress)}</p><p class="text-[0.6rem] uppercase tracking-wider text-tintafina mt-1">En progreso</p></div>
        <div><p class="text-xl font-semibold text-plomo">${esc(summary.statuses.no_progress)}</p><p class="text-[0.6rem] uppercase tracking-wider text-tintafina mt-1">Sin avance</p></div>
        <div><p class="text-xl font-semibold text-rojo">${esc(summary.statuses.unfulfilled)}</p><p class="text-[0.6rem] uppercase tracking-wider text-tintafina mt-1">Incumplidos</p></div>
      </div>
      <ul class="mt-6 space-y-3 border-t border-dashed border-tinta/20 pt-5">
        ${highlights.map((h) => `
        <li class="flex items-start justify-between gap-3">
          <p class="text-sm leading-snug">${esc(h.text)}</p>
          ${stamp(h.status)}
        </li>`).join('')}
      </ul>
      <p class="mt-5 font-mono text-[0.6rem] text-tintafina leading-relaxed">Fuentes: ${meta.sources.map(esc).join(' · ')}</p>
    </div>`;
}
