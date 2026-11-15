import type { Lang } from '../api/source';
import { $ } from './dom';

type Message = string | ((...args: (string | number)[]) => string);

const I18N: Record<Lang, Record<string, Message>> = {
  es: {
    searchPh: 'Objeto o coordenadas (ej. WISE 0855, 269.45 4.69)', searchAria: 'Buscar objeto o coordenadas',
    navExplore: 'Explorar', navCompare: 'Comparar', navSpectrum: 'Espectro', railQuery: 'Consulta', railPanel: 'Panel',
    export: 'Exportar', share: 'Compartir', expPng: 'Imagen actual', expCsv: 'Espectro (CSV)', shareLink: 'Copiar enlace', shareEmbed: 'Código para insertar',
    query: 'Consulta', ra: 'Ascensión recta', dec: 'Declinación', fov: 'Campo de visión (arcmin)', zoomIn: 'Acercar', zoomOut: 'Alejar', search: 'Buscar',
    detectors: 'Detectores', lamRef: 'λ de referencia', lamHelp: 'Solo se animan cuadros con λ parecida: así un cambio de brillo no se debe a otro color.',
    tol: 'Tolerancia de λ', chan: 'canal', channels: '17 canales por detector · 102 en toda la misión',
    data: 'Colección de datos', refresh: 'Actualizar búsqueda', collHelp: 'IRSA publica nuevos datos cada semana.', dismiss: 'Cerrar',
    mBlink: 'Alternar', mSlider: 'Deslizar', mDiff: 'Diferencia', mSum: 'Suma', examples: 'Objetivos de ejemplo:', viewSpec: 'Ver espectro',
    recenter: 'Recentrar', grid: 'Malla de coordenadas', fullscreen: 'Pantalla completa',
    specTitle: 'Espectro de la fuente', colorEpoch: 'Colorear por época', ylog: 'Eje Y logarítmico', legFlux: 'Flujo', legErr: 'Incertidumbre 1σ', older: 'antigua', newer: 'reciente', legGap: 'Sin cobertura (no es flujo cero)',
    specNote: 'Cada punto sale de una exposición distinta. Si los puntos de un mismo canal se separan por época, la fuente varía. Clic en un punto para ver su cuadro.',
    tDate: 'Fecha', tPoints: 'Puntos', tDets: 'Detectores', tFrames: 'Cuadros',
    context: 'Contexto en el cielo', aladinLoading: 'Cargando Aladin Lite…', baseLayer: 'Fondo', gaiaCat: 'catálogo', display: 'Visualización', stretch: 'Estiramiento', linear: 'lineal',
    render: 'Píxeles', rPixel: 'Reales', rSmooth: 'Suave', commonScale: 'Escala común', subBg: 'Restar fondo', expected: 'Posición esperada', maskPx: 'Píxeles enmascarados',
    quality: 'Calidad del cuadro', supLink: 'Significado de las banderas (documentación IRSA) ↗', prep: 'Preparación', epochs: 'Épocas comparadas', legend: 'Leyenda de la diferencia', neg: 'Más tenue en B', zero: 'Sin cambio', pos: 'Más brillante en B',
    diffHelp: 'B − A. Una estrella que se movió deja un par: tenue donde estaba (A), brillante donde está (B).',
    cutout: 'Recorte de apertura', cutLegend: 'Círculo: apertura · discontinuo: anillo de fondo', extraction: 'Extracción', aperture: 'Apertura', annulus: 'Anillo de fondo',
    subBgSpec: 'Restar fondo', showErr: 'Mostrar incertidumbre', exclBad: 'Excluir píxeles marcados', recalc: 'Recalcular', meta: 'Metadatos',
    prev: 'Anterior', next: 'Siguiente', docs: 'Documentación SPHEREx · IRSA', close: 'Cerrar',
    play: 'Reproducir', pause: 'Pausar', anyL: 'Cualquiera',
    demoBadge: 'MODO DEMOSTRACIÓN · datos simulados, no son imágenes reales de SPHEREx',
    loading: 'Cargando cuadros', loadingN: (a, b) => `Cargando cuadros ${a}/${b}…`, noCov: 'Sin cobertura SPHEREx para estas coordenadas en la colección elegida. Prueba otra colección o amplía el campo.',
    oneFrame: 'Solo hay un cuadro con esta λ: sube la tolerancia o cambia de detector para poder comparar.', errLoad: m => `No se pudo cargar: ${m}`,
    invalid: 'Consulta inválida: RA debe estar entre 0° y 360° y Dec entre −90° y +90°.', notFound: n => `No se encontró «${n}». Prueba con coordenadas.`,
    centerPropagated: d => `Centrado en la posición del objeto en ${d} (J2000 + movimiento propio).`, centerManual: 'Centro fijo en las coordenadas indicadas.',
    approxPx: 'px', frameOf: (i, n) => `${i} / ${n}`, noFrames: 'Sin cuadros',
    capExplore: 'Los cuadros se repiten en bucle. Lo que se mueve respecto a las estrellas fijas es un candidato a objeto cercano; lo que cambia de brillo, una variable.',
    capBlink: 'Se alternan A y B. Fíjate en lo que «salta» entre una imagen y la otra.', capSlider: 'Arrastra la línea: a la izquierda la época A, a la derecha la B.',
    capDiff: 'Resta B − A. Un objeto que se movió deja un par: cian (donde estaba) y rojo (donde está).', capSum: n => `Promedio de ${n} cuadros: más señal-ruido para ver objetos tenues, pero lo que se mueve se vuelve una mancha.`,
    lamOk: 'λ comparable', lamBad: 'λ distinta',
    lamWarn: (a, b) => `A está a ${a} µm y B a ${b} µm. Un cambio de brillo puede deberse al color, no a variabilidad real.`, lamGood: 'Las dos épocas miden casi la misma λ: la comparación es justa.',
    lamExplain: 'λ distinta', aligned: 'La alineación celeste (WCS) la hace el servidor antes de enviar los cuadros.', alignedDemo: 'En la demo todos los cuadros ya comparten la malla celeste.',
    date: 'Fecha', det: 'Detector', wl: 'λ', pointsN: n => `${n} puntos`, selSource: 'Fuente seleccionada', expectedLbl: 'Posición esperada',
    posTxt: (r, d) => `Posición: ${r}°, ${d}°`, specSubTxt: (n, p) => `${n} · ${p} puntos`, noSpec: 'Sin puntos', unit: 'Flujo (mJy)', xlab: 'Longitud de onda (µm)',
    metaSrc: 'Origen', metaColl: 'Colección', metaPix: 'Escala', metaAp: 'Apertura', copy: 'Copiar', copied: 'Copiado ✓', linkTitle: 'Enlace compartible', linkHelp: 'Conserva coordenadas, campo, detector, λ, vista y modo.',
    embedTitle: 'Código para insertar', embedHelp: 'Pega este iframe en cualquier página.', pngDone: 'Imagen descargada.', csvDone: 'CSV descargado.', noFlags: 'Sin banderas', maskedPx: 'Píxeles marcados',
    flagsDemo: 'Banderas simuladas en la demo.', aladinFail: 'No se pudo cargar Aladin Lite (¿sin conexión?). El resto funciona.', cursor: (r, d) => `α ${r}° · δ ${d}°`,
    ariaSky: (t, f) => `Imagen del cielo, ${t}. ${f}`, scale1: '1 arcmin', timeLbl: 'Línea de tiempo de observaciones', noTarget: 'Posición sin objeto asociado', lamUm: l => `${l} µm`,
    fovLess: 'Reducir campo (acercar)', fovMore: 'Ampliar campo (alejar)', maskedPx2: 'Píxeles marcados', srcPos: 'Posición seleccionada', tooltipSel: 'Fuente', hintPos: 'Clic en el cielo para elegir una fuente y ver su espectro.'
  },
  en: {
    searchPh: 'Object or coordinates (e.g. WISE 0855, 269.45 4.69)', searchAria: 'Search object or coordinates',
    navExplore: 'Explore', navCompare: 'Compare', navSpectrum: 'Spectrum', railQuery: 'Query', railPanel: 'Panel',
    export: 'Export', share: 'Share', expPng: 'Current image', expCsv: 'Spectrum (CSV)', shareLink: 'Copy link', shareEmbed: 'Embed code',
    query: 'Query', ra: 'Right ascension', dec: 'Declination', fov: 'Field of view (arcmin)', zoomIn: 'Zoom in', zoomOut: 'Zoom out', search: 'Search',
    detectors: 'Detectors', lamRef: 'Reference λ', lamHelp: 'Only frames with similar λ are animated, so a brightness change is not just a different colour.',
    tol: 'λ tolerance', chan: 'channel', channels: '17 channels per detector · 102 across the mission',
    data: 'Data collection', refresh: 'Refresh search', collHelp: 'IRSA publishes new data every week.', dismiss: 'Dismiss',
    mBlink: 'Blink', mSlider: 'Slide', mDiff: 'Difference', mSum: 'Sum', examples: 'Example targets:', viewSpec: 'View spectrum',
    recenter: 'Recenter', grid: 'Coordinate grid', fullscreen: 'Fullscreen',
    specTitle: 'Source spectrum', colorEpoch: 'Colour by epoch', ylog: 'Log Y axis', legFlux: 'Flux', legErr: '1σ uncertainty', older: 'older', newer: 'newer', legGap: 'No coverage (not zero flux)',
    specNote: 'Each point comes from a different exposure. If points of the same channel separate by epoch, the source varies. Click a point to see its frame.',
    tDate: 'Date', tPoints: 'Points', tDets: 'Detectors', tFrames: 'Frames',
    context: 'Sky context', aladinLoading: 'Loading Aladin Lite…', baseLayer: 'Background', gaiaCat: 'catalogue', display: 'Display', stretch: 'Stretch', linear: 'linear',
    render: 'Pixels', rPixel: 'Real', rSmooth: 'Smooth', commonScale: 'Common scale', subBg: 'Subtract background', expected: 'Expected position', maskPx: 'Masked pixels',
    quality: 'Frame quality', supLink: 'What the flags mean (IRSA docs) ↗', prep: 'Preparation', epochs: 'Compared epochs', legend: 'Difference legend', neg: 'Fainter in B', zero: 'No change', pos: 'Brighter in B',
    diffHelp: 'B − A. A star that moved leaves a pair: faint where it was (A), bright where it is (B).',
    cutout: 'Aperture cutout', cutLegend: 'Circle: aperture · dashed: background annulus', extraction: 'Extraction', aperture: 'Aperture', annulus: 'Background annulus',
    subBgSpec: 'Subtract background', showErr: 'Show uncertainty', exclBad: 'Exclude flagged pixels', recalc: 'Recompute', meta: 'Metadata',
    prev: 'Previous', next: 'Next', docs: 'SPHEREx documentation · IRSA', close: 'Close',
    play: 'Play', pause: 'Pause', anyL: 'Any',
    demoBadge: 'DEMO MODE · simulated data, not real SPHEREx images',
    loading: 'Loading frames', loadingN: (a, b) => `Loading frames ${a}/${b}…`, noCov: 'No SPHEREx coverage at these coordinates in the chosen collection. Try another collection or widen the field.',
    oneFrame: 'Only one frame at this λ: raise the tolerance or change detector to compare.', errLoad: m => `Could not load: ${m}`,
    invalid: 'Invalid query: RA must be 0°–360° and Dec −90° to +90°.', notFound: n => `“${n}” not found. Try coordinates.`,
    centerPropagated: d => `Centred on the object's position on ${d} (J2000 + proper motion).`, centerManual: 'Centre fixed on the given coordinates.',
    approxPx: 'px', frameOf: (i, n) => `${i} / ${n}`, noFrames: 'No frames',
    capExplore: 'Frames loop automatically. Anything that moves against the fixed stars is a nearby-object candidate; anything that changes brightness is a variable.',
    capBlink: 'A and B alternate. Look for whatever “jumps” between the two images.', capSlider: 'Drag the line: epoch A on the left, epoch B on the right.',
    capDiff: 'B − A subtraction. A moving object leaves a pair: cyan (where it was) and red (where it is).', capSum: n => `Average of ${n} frames: better signal-to-noise for faint objects, but movers smear out.`,
    lamOk: 'comparable λ', lamBad: 'different λ',
    lamWarn: (a, b) => `A is at ${a} µm and B at ${b} µm. A brightness change may come from colour, not real variability.`, lamGood: 'Both epochs measure nearly the same λ: the comparison is fair.',
    lamExplain: 'different λ', aligned: 'Sky alignment (WCS) is done by the server before frames are sent.', alignedDemo: 'In the demo all frames already share the sky grid.',
    date: 'Date', det: 'Detector', wl: 'λ', pointsN: n => `${n} points`, selSource: 'Selected source', expectedLbl: 'Expected position',
    posTxt: (r, d) => `Position: ${r}°, ${d}°`, specSubTxt: (n, p) => `${n} · ${p} points`, noSpec: 'No points', unit: 'Flux (mJy)', xlab: 'Wavelength (µm)',
    metaSrc: 'Source', metaColl: 'Collection', metaPix: 'Scale', metaAp: 'Aperture', copy: 'Copy', copied: 'Copied ✓', linkTitle: 'Shareable link', linkHelp: 'Keeps coordinates, field, detector, λ, view and mode.',
    embedTitle: 'Embed code', embedHelp: 'Paste this iframe into any page.', pngDone: 'Image downloaded.', csvDone: 'CSV downloaded.', noFlags: 'No flags', maskedPx: 'Flagged pixels',
    flagsDemo: 'Flags are simulated in the demo.', aladinFail: 'Could not load Aladin Lite (offline?). Everything else works.', cursor: (r, d) => `α ${r}° · δ ${d}°`,
    ariaSky: (t, f) => `Sky image, ${t}. ${f}`, scale1: '1 arcmin', timeLbl: 'Observation timeline', noTarget: 'Position with no associated object', lamUm: l => `${l} µm`,
    fovLess: 'Narrow field (zoom in)', fovMore: 'Widen field (zoom out)', maskedPx2: 'Flagged pixels', srcPos: 'Selected position', tooltipSel: 'Source', hintPos: 'Click the sky to pick a source and see its spectrum.'
  }
};
export function translate(lang: Lang, key: string, ...args: (string | number)[]): string {
  const message = I18N[lang][key];
  return typeof message === 'function' ? message(...args) : message ?? key;
}

export function applyI18n(lang: Lang, root: ParentNode = document): void {
  document.documentElement.lang = lang;
  root.querySelectorAll<HTMLElement>('[data-i18n]').forEach((node) => {
    const key = node.dataset.i18n;
    if (key) node.textContent = translate(lang, key);
  });
  root.querySelectorAll<HTMLInputElement>('[data-i18n-ph]').forEach((node) => {
    const key = node.dataset.i18nPh;
    if (key) node.placeholder = translate(lang, key);
  });
  root.querySelectorAll<HTMLElement>('[data-i18n-aria]').forEach((node) => {
    const key = node.dataset.i18nAria;
    if (key) node.setAttribute('aria-label', translate(lang, key));
  });
  root.querySelectorAll<HTMLElement>('[data-i18n-title]').forEach((node) => {
    const key = node.dataset.i18nTitle;
    if (key) node.title = translate(lang, key);
  });
  const langButton = $('btnLang');
  if (langButton) langButton.textContent = lang === 'es' ? 'EN' : 'ES';
}
