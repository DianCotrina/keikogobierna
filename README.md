# keikogobierna

**Seguimiento ciudadano e independiente del plan de gobierno 2026–2031.**

**Sitio en vivo:** https://www.keikogobierna.com

## Qué es

El plan de gobierno «Perú con Orden» inscrito ante el JNE contiene promesas concretas.
Este sitio las convirtió en **764 compromisos rastreables** — 632 propuestas, 67 acciones
de los primeros 100 días y 65 metas al 2031 — y registra qué pasa con cada uno:
**cumplida, en progreso, sin avance o incumplida**, siempre con evidencia pública enlazada.

Lo prometido es deuda. Este es el registro de la deuda.

## Cómo funciona

Tres capas, cada una con su propio ritmo:

1. **El plan (inmutable).** Extraído una sola vez del PDF oficial a JSON
   (`src/data/plan/`). Cada compromiso conserva su texto tal como figura en el documento
   y un ID que nunca cambia.
2. **Los rastreadores (diarios, deterministas).** Leen El Peruano (cada norma publicada
   se compara contra los 764 compromisos), El Comercio (alimenta la página
   [Las ultimitas](https://www.keikogobierna.com/ultimitas/)) y la prensa peruana vía
   Google News. **Sin inteligencia artificial**: solo coincidencias de texto que
   cualquiera puede rehacer. Las coincidencias se archivan como issues para revisión.
3. **La certificación (humana, siempre).** Ninguna máquina asigna un estado. Una persona
   revisa cada coincidencia, la contrasta con fuentes oficiales (MEF, INEI, Congreso)
   y recién ahí certifica — mediante un pull request público, con fecha y fuente.

El sitio es estático (Astro): cada cambio de estado se publica reconstruyendo la página,
y el historial completo queda en git.

## Datos abiertos

Todo el plan y su seguimiento son consumibles como JSON, regenerados en cada publicación:

- https://www.keikogobierna.com/api/plan.json — el plan completo (pilares, temas, compromisos, metas)
- https://www.keikogobierna.com/api/tracking.json — estados y evidencia

Úsalos citando la fuente. El código, los datos y el historial de este repositorio son
públicos: el camino queda abierto a quien quiera auditarlo.

## Desarrollo

```bash
npm install        # dependencias
npm run dev        # servidor local en http://localhost:3000
npm run build      # build estático a dist/
npm test           # tests de la capa de datos
npm run validate   # valida el árbol del plan + tracking.json
```

Los rastreadores viven en `tools/scrapers/` (Python, sin dependencias externas) y corren
como GitHub Actions programadas. La arquitectura completa está documentada en
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Fuentes

El detalle de cada fuente — el documento original, las fuentes automáticas y las de
contraste — está en https://www.keikogobierna.com/fuentes/
