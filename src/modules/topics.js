import { esc } from '../lib/dom.js';

export function renderTopics(el, data) {
  el.innerHTML = data.topics.map((topic) => `
    <a href="#" class="card-hover reveal block bg-white rounded-lg border border-tinta/10 shadow-card p-6" data-topic="${esc(topic.id)}">
      <div class="flex items-baseline justify-between">
        <h3 class="font-sans font-bold text-lg">${esc(topic.name)}</h3>
        <span class="font-mono text-xs text-tintafina">${esc(topic.commitments)} comp.</span>
      </div>
      <div class="mt-4 h-1.5 rounded-full bg-tinta/10 overflow-hidden"><div class="h-full rounded-full bg-tinta" style="width:${esc(topic.progress)}%"></div></div>
      <p class="mt-3 font-mono text-xs text-tintasuave">${esc(topic.progress)} % de avance</p>
    </a>`).join('');
}
