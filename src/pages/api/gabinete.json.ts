import type { APIRoute } from 'astro';
import { loadPortfolios, loadPeople, loadTenures } from '../../lib/cabinet.mjs';
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
    people: loadPeople(),
    tenures: loadTenures(),
  };

  return new Response(JSON.stringify(payload), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
