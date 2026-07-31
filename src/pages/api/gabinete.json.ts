import type { APIRoute } from 'astro';
import { loadPortfolios, loadMinisters, loadTenures, loadAnnouncements } from '../../lib/cabinet.mjs';
import pkg from '../../../package.json';

// Static datos-abiertos endpoint: rendered once at build into dist/api/gabinete.json.
export const GET: APIRoute = () => {
  const payload = {
    meta: {
      version: pkg.version,
      generated: new Date().toISOString(),
      source: 'https://github.com/DianCotrina/keikogobierna',
      license: 'Nombramientos: El Peruano (norma citada en cada tenure). Registro judicial: fuentes públicas enlazadas en cada entrada.',
      notice: 'Las etapas procesales no son sentencias. Toda persona es inocente mientras no se declare judicialmente su responsabilidad.',
    },
    portfolios: loadPortfolios(),
    ministers: loadMinisters(),
    tenures: loadTenures(),
    // Provisional: announced in public, not yet appointed by norma. Superseded
    // by a tenure on the same portfolio the moment one exists.
    announcements: loadAnnouncements(),
  };

  return new Response(JSON.stringify(payload), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
