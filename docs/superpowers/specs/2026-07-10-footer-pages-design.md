# Footer redesign + Fuentes + Privacidad pages

**Date:** 2026-07-10
**Status:** Approved by Diego (design conversation, 2026-07-10)

## Problem

The footer's «Fuentes» and «Contacto» links are dead (`href="#"`), Metodología duplicates a main-nav destination, and there's no rights line, no contact channel, and no legal page.

## Design

### Footer (Base.astro — all pages)

Three-block layout replacing the current two-block row:

- **Brand block** (left): wordmark (unchanged) → disclaimer (unchanged) → LinkedIn link: inline `in` SVG logo + no visible text, `href="https://www.linkedin.com/in/diancotrina/"`, `target="_blank" rel="noopener noreferrer"`, `aria-label="Perfil de LinkedIn de Diego Cotrina"`, hover/focus-visible states → rights line «© 2026 keikogobierna · Todos los derechos reservados.» (mono, tintafina, same size as disclaimer) → existing version link.
- **Fuentes column**: mono uppercase heading «Fuentes» → link «Plan y fuentes oficiales» to `/fuentes/`.
- **Contacto column**: mono uppercase heading «Contacto» → visible mailto `dian.cs183@gmail.com` (`href="mailto:dian.cs183@gmail.com"`) → link «Privacidad» to `/privacidad/`.
- **Metodología link removed** from the footer.

(Exact grouping may flex to two columns — Fuentes | Contacto — with Privacidad under Contacto, per the approved sketch.)

### /fuentes/ page (`src/pages/fuentes.astro`)

Masthead pattern of the other pages (eyebrow + display h1 + serif intro). Case-file list of sources, each: name, what it verifies, official link (external, `noopener`):

1. **Plan de Gobierno «Perú con Orden» 2026–2031** (Fuerza Popular) — the JNE-registered document all 632 proposals/65 metas come from. Links: JNE Plataforma Electoral (https://plataformaelectoral.jne.gob.pe) and the archived working copy in the repo (https://github.com/DianCotrina/keikogobierna/blob/main/docs/Plan-de-Gobierno-Reforzado_V2.pdf).
2. **El Peruano — Normas Legales** (https://busquedas.elperuano.pe) — decretos, leyes y normas que certifican cumplimientos.
3. **MEF — Consulta Amigable** (https://apps5.mineco.gob.pe/transparencia/Navegador/default.aspx) — ejecución presupuestal.
4. **INEI** (https://www.inei.gob.pe) — estadísticas oficiales para indicadores de metas.
5. **Congreso de la República** (https://www.congreso.gob.pe) — proyectos de ley y actas.

Closing line tying to methodology: states cambian solo con estas fuentes, enlazadas en cada certificación.

### /privacidad/ page (`src/pages/privacidad.astro`)

Same masthead pattern. Short, truthful sections:

- **Sin cookies ni rastreadores**: static site, no cookies, no analytics, no tracking of any kind.
- **Alertas por correo**: the alert form, when active, collects only the email address, used solely to send state-change alerts; never shared; removable on request.
- **Contacto**: dian.cs183@gmail.com for questions about data or this policy.
- Last-updated line (10 de julio de 2026).

Both pages: title/description in Spanish, linked only from the footer, `activeNav` unset.

## Out of scope

- Social links beyond LinkedIn; analytics; making the alert form functional.

## Verification

- `npm run build` (28 pages: 26 + 2 new).
- Screenshots: footer desktop + 390px (iframe trick), /fuentes/ and /privacidad/ full pages.
- 21 tests unaffected.
