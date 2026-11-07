import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import satori from 'satori';
import { Resvg } from '@resvg/resvg-js';
import { formatDateEs, formatDateEsShort, plural } from './format.mjs';
import { truncate } from './infographic.mjs';

// Paper and ink, always light: an image travels without the viewer's theme.
const C = {
  papel: '#F5F3EE',
  hoja: '#FFFFFF',
  tinta: '#141417',
  suave: '#46464D',
  fina: '#6E6E76',
  rojo: '#C8102E',
  verde: '#1F7A4D',
  ambar: '#A35E00',
  track: '#E2DFD8',
};

export const FORMATS = {
  vertical: { width: 1080, height: 1350 },
  enlace: { width: 1200, height: 630 },
};

// Fonts come from the @fontsource packages. Read from the project root: the
// build runs there, and a path relative to this module breaks once bundled.
const font = (pkg, file) => readFileSync(join(process.cwd(), 'node_modules', '@fontsource', pkg, 'files', file));
let fonts;
const loadFonts = () =>
  (fonts ??= [
    { name: 'Archivo Black', data: font('archivo-black', 'archivo-black-latin-400-normal.woff'), weight: 400 },
    { name: 'Archivo', data: font('archivo', 'archivo-latin-500-normal.woff'), weight: 500 },
    { name: 'Archivo', data: font('archivo', 'archivo-latin-700-normal.woff'), weight: 700 },
    { name: 'Source Serif', data: font('source-serif-4', 'source-serif-4-latin-400-normal.woff'), weight: 400 },
    { name: 'Source Serif', data: font('source-serif-4', 'source-serif-4-latin-600-normal.woff'), weight: 600 },
    { name: 'Plex Mono', data: font('ibm-plex-mono', 'ibm-plex-mono-latin-400-normal.woff'), weight: 400 },
    { name: 'Plex Mono', data: font('ibm-plex-mono', 'ibm-plex-mono-latin-600-normal.woff'), weight: 600 },
  ]);

// Satori takes React-shaped objects; every box with several children is a flex box.
const h = (type, style, ...children) => ({
  type,
  // Satori rejects an undefined style value, so optional ones are dropped here.
  props: { style: Object.fromEntries(Object.entries({ display: 'flex', ...style }).filter(([, v]) => v !== undefined)), children: children.flat(Infinity).filter((c) => c !== null && c !== false) },
});
const text = (value, style) => h('div', style, String(value));

const logo = (size) =>
  h('div', { fontFamily: 'Archivo Black', fontSize: size, letterSpacing: '-0.02em' },
    text('keiko', { color: C.tinta }), text('gobierna', { color: C.rojo }));

// Part-to-whole on a track: the unfilled track is "sin avance", so only two
// status colours appear, separated by surface gaps and named by direct labels
// (green/amber sit in the colour-blind floor band; the labels carry identity).
function statusBar({ total, fulfilled, inProgress }, width, height) {
  const px = (n) => (n === 0 ? 0 : Math.max(Math.round((n / total) * width), 10));
  const segments = [
    fulfilled > 0 && h('div', { width: px(fulfilled), height, background: C.verde, borderRadius: 4 }),
    inProgress > 0 && h('div', { width: px(inProgress), height, background: C.ambar, borderRadius: 4, marginLeft: fulfilled > 0 ? 3 : 0 }),
  ];
  return h('div', { width, height, background: C.track, borderRadius: 6, overflow: 'hidden' }, segments);
}

function legend({ total, fulfilled, inProgress }, size) {
  const swatch = (color, border) => h('div', { width: size * 0.7, height: size * 0.7, background: color, border, borderRadius: 3, marginRight: 10 });
  const item = (swatchEl, label) => h('div', { alignItems: 'center', marginRight: 34 }, swatchEl, text(label, {}));
  return h('div', { fontFamily: 'Plex Mono', fontSize: size, color: C.suave, flexWrap: 'wrap' },
    item(swatch(C.verde), plural(fulfilled, 'cumplido', 'cumplidos')),
    item(swatch(C.ambar), `${inProgress} en progreso`),
    item(swatch(C.track, `2px solid ${C.fina}`), `${total - fulfilled - inProgress} sin avance`));
}

const DEFINITION = 'Iniciado: en progreso o cumplido, según una norma publicada en El Peruano. Sin avance: todavía no hay una norma que lo acredite, no que no se haya hecho nada.';

function footer(path, size) {
  return h('div', { flexDirection: 'column', borderTop: `2px dashed ${C.track}`, paddingTop: 26 },
    text(DEFINITION, { fontFamily: 'Source Serif', fontSize: size, lineHeight: 1.45, color: C.suave }),
    text(`keikogobierna.com${path === '/' ? '' : path}`, { marginTop: 16, fontFamily: 'Plex Mono', fontWeight: 600, fontSize: size, color: C.tinta }),
    text('Fuentes: plan inscrito ante el JNE y normas de El Peruano', { marginTop: 6, fontFamily: 'Plex Mono', fontSize: size - 3, color: C.fina }));
}

const frame = ({ width, height }, padding, ...children) =>
  h('div', { width, height, flexDirection: 'column', background: C.papel, fontFamily: 'Archivo' },
    h('div', { width, height: 14, background: C.rojo }),
    h('div', { flex: 1, flexDirection: 'column', padding }, children));

const header = (asOf, logoSize, dateSize) =>
  h('div', { justifyContent: 'space-between', alignItems: 'center' },
    logo(logoSize),
    text(`Datos al ${formatDateEs(asOf)}`, { fontFamily: 'Plex Mono', fontSize: dateSize, color: C.fina }));

function headline(d, size, labelSize, gap) {
  return h('div', { flexDirection: 'column' },
    text(`${d.started} de ${d.total}`, { fontFamily: 'Archivo Black', fontSize: size, lineHeight: 0.95, letterSpacing: '-0.03em', color: C.tinta }),
    text(d.started === 1 ? 'compromiso iniciado' : 'compromisos iniciados', { marginTop: gap, fontFamily: 'Source Serif', fontSize: labelSize, color: C.suave }));
}

// Lines a text takes at a given size across a width (average glyph ≈ 0.5em
// for the serif). Used to fit whole items instead of clipping one in half.
const lines = (value, size, width) => Math.ceil((value.length * size * 0.5) / width);
const ITEM_CHARS = 130;
const itemHeight = (item) => 26 + lines(truncate(item.text, ITEM_CHARS), 31, 860) * 42 + 38;

// Room left for the list once the fixed blocks are laid out (px).
function listRoom(titleLines) {
  const fixed = 14 + 64 + 52 + 56 + 32 + titleLines * 98 + 36 + 106 + 42 + 28 + 30 + 18 + 30 + 14 + 30 + 34 + 40 + 205 + 60;
  return FORMATS.vertical.height - fixed;
}

function fitting(items, titleLines) {
  let room = listRoom(titleLines);
  const shown = [];
  for (const item of items) {
    room -= itemHeight(item);
    if (room < (shown.length + 1 < items.length ? 40 : 0)) break;
    shown.push(item);
  }
  return shown;
}

function itemRow(item) {
  const mark = item.status === 'fulfilled' ? C.verde : C.ambar;
  return h('div', { marginTop: 26, flexShrink: 0 },
    h('div', { width: 16, height: 16, borderRadius: 8, background: mark, marginTop: 14, marginRight: 22, flexShrink: 0 }),
    h('div', { flexDirection: 'column', flex: 1 },
      text(truncate(item.text, ITEM_CHARS), { fontFamily: 'Source Serif', fontSize: 31, lineHeight: 1.35, color: C.tinta }),
      text(
        [item.status === 'fulfilled' ? 'Cumplido' : 'En progreso', item.norma, item.date && formatDateEsShort(item.date)].filter(Boolean).join(' · '),
        { marginTop: 8, fontFamily: 'Plex Mono', fontSize: 23, color: C.suave },
      )));
}

function topicVertical(d, asOf) {
  const longTitle = d.name.length > 22;
  const titleLines = lines(d.name, longTitle ? 72 : 96, 936 / 1.08);
  const shown = fitting(d.items, titleLines);
  return frame(FORMATS.vertical, '64px 72px 60px',
    header(asOf, 42, 24),
    text(`PLAN DE GOBIERNO DE KEIKO FUJIMORI · TEMA ${d.section}`, { marginTop: 56, fontFamily: 'Plex Mono', fontSize: 24, letterSpacing: '0.14em', color: C.suave }),
    text(d.name, { marginTop: 14, fontFamily: 'Archivo Black', fontSize: longTitle ? 72 : 96, lineHeight: 1.02, letterSpacing: '-0.03em', color: C.tinta }),
    h('div', { marginTop: 36 }, headline(d, 112, 36, 6)),
    h('div', { marginTop: 28 }, statusBar(d, 936, 30)),
    h('div', { marginTop: 18 }, legend(d, 24)),
    text(`Metas al 2031: ${d.goals.fulfilled} de ${d.goals.total} cumplidas`, { marginTop: 14, fontFamily: 'Plex Mono', fontSize: 24, color: C.suave }),
    h('div', { flex: 1, flexDirection: 'column', marginTop: 34, overflow: 'hidden' },
      d.items.length === 0
        ? text('Ningún compromiso de este tema tiene todavía una norma que acredite avance.', { fontFamily: 'Source Serif', fontSize: 34, lineHeight: 1.4, color: C.tinta })
        : [
            text(d.items.length === 1 ? 'El compromiso iniciado' : 'Los compromisos iniciados', { flexShrink: 0, fontFamily: 'Archivo', fontWeight: 700, fontSize: 30, color: C.tinta }),
            shown.map(itemRow),
            d.items.length > shown.length && text(`y ${d.items.length - shown.length} más en la web`, { marginTop: 20, fontFamily: 'Plex Mono', fontSize: 23, color: C.suave }),
          ]),
    footer(d.path, 23));
}

function planVertical(d, asOf) {
  const shown = d.topics.slice(0, 4);
  return frame(FORMATS.vertical, '64px 72px 60px',
    header(asOf, 42, 24),
    text('SEGUIMIENTO CIUDADANO E INDEPENDIENTE', { marginTop: 56, fontFamily: 'Plex Mono', fontSize: 24, letterSpacing: '0.14em', color: C.suave }),
    text('Plan de gobierno de Keiko Fujimori', { marginTop: 14, fontFamily: 'Archivo Black', fontSize: 72, lineHeight: 1.04, letterSpacing: '-0.03em', color: C.tinta }),
    h('div', { marginTop: 36 }, headline(d, 112, 36, 6)),
    h('div', { marginTop: 28 }, statusBar(d, 936, 30)),
    h('div', { marginTop: 18 }, legend(d, 24)),
    text(`Primeros 100 días: ${d.hundred.inProgress} de ${d.hundred.total} acciones en progreso, ${d.hundred.fulfilled} cumplidas`, { marginTop: 14, fontFamily: 'Plex Mono', fontSize: 24, color: C.suave }),
    h('div', { flex: 1, flexDirection: 'column', marginTop: 34, overflow: 'hidden' },
      text('Temas con compromisos iniciados', { flexShrink: 0, fontFamily: 'Archivo', fontWeight: 700, fontSize: 30, color: C.tinta }),
      shown.map((topic) =>
        h('div', { marginTop: 12, flexShrink: 0, justifyContent: 'space-between', borderBottom: `1px solid ${C.track}`, paddingBottom: 10 },
          text(topic.name, { fontFamily: 'Source Serif', fontSize: 32, color: C.tinta }),
          text(`${topic.started} de ${topic.total}`, { fontFamily: 'Plex Mono', fontWeight: 600, fontSize: 28, color: C.tinta }))),
      d.topics.length > shown.length && text(`y ${plural(d.topics.length - shown.length, 'tema', 'temas')} más en la web`, { marginTop: 16, fontFamily: 'Plex Mono', fontSize: 23, color: C.suave })),
    footer(d.path, 23));
}

function landscape(d, asOf) {
  const title = d.kind === 'plan' ? 'Plan de gobierno de Keiko Fujimori' : d.name;
  return frame(FORMATS.enlace, '40px 60px 40px',
    header(asOf, 34, 20),
    text(d.kind === 'plan' ? 'SEGUIMIENTO CIUDADANO E INDEPENDIENTE' : `PLAN DE GOBIERNO DE KEIKO FUJIMORI · TEMA ${d.section}`, { marginTop: 34, fontFamily: 'Plex Mono', fontSize: 20, letterSpacing: '0.14em', color: C.suave }),
    text(title, { marginTop: 10, fontFamily: 'Archivo Black', fontSize: title.length > 24 ? 56 : 72, lineHeight: 1.04, letterSpacing: '-0.03em', color: C.tinta }),
    h('div', { marginTop: 'auto', alignItems: 'flex-end' },
      text(`${d.started} de ${d.total}`, { fontFamily: 'Archivo Black', fontSize: 104, lineHeight: 0.9, letterSpacing: '-0.03em', color: C.tinta }),
      text(d.started === 1 ? 'compromiso iniciado' : 'compromisos iniciados', { marginLeft: 22, marginBottom: 6, fontFamily: 'Source Serif', fontSize: 36, color: C.suave })),
    h('div', { marginTop: 24 }, statusBar(d, 1080, 26)),
    h('div', { marginTop: 14, justifyContent: 'space-between', alignItems: 'center' },
      legend(d, 20),
      text('keikogobierna.com', { fontFamily: 'Plex Mono', fontWeight: 600, fontSize: 20, color: C.tinta })));
}

export async function renderInfographic(data, format, asOf) {
  const tree = format === 'enlace' ? landscape(data, asOf) : data.kind === 'plan' ? planVertical(data, asOf) : topicVertical(data, asOf);
  const svg = await satori(tree, { ...FORMATS[format], fonts: loadFonts() });
  return new Resvg(svg, { fitTo: { mode: 'original' } }).render().asPng();
}
