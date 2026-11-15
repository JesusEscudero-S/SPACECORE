import aladinPackage from '../../../node_modules/aladin-lite/package.json';
import { verifyElements } from '../../lib/dom';
import { translate } from '../../lib/i18n';
import type { SkyPosition } from '../../api/source';
import type { Store } from '../../state/store';
import type { ViewActions } from '../contracts';

// Servidores probados el 2026-11-14 desde la red del equipo (navegador, con CORS):
// - IRSA (irsa.ipac.caltech.edu): HiPS de DSS2, 2MASS, AllWISE W1 y el cubo de SPHEREx DR1 -> responden en ~0.1 s.
// - VizieR, espejo del CfA (vizier.cfa.harvard.edu): Gaia DR3 y AllWISE en VOTable con CORS -> ~1-2 s.
// - CDS (vizier/simbad/hipscat .cds.unistra.fr): responden, pero SIN CORS o con timeout desde el navegador.
// - ESAC (skies.esac.esa.int): no respondió (timeout de 20 s). Por eso ya no es el fondo por defecto.
const DEFAULT_SURVEY = 'https://irsa.ipac.caltech.edu/data/hips/CDS/DSS2/color';
const SPHEREX_HIPS = 'https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube';
const VIZIER = 'https://vizier.cfa.harvard.edu/viz-bin/votable';

// Longitud de onda (µm) de cada una de las 102 capas del cubo HiPS de SPHEREx, en orden.
// Copiada de data_cube_crval3_arr en .../spherex_allsky_cube/properties (IRSA, 2026-11-14).
const SPHEREX_LAMBDAS = [
  0.753, 0.771, 0.790, 0.809, 0.828, 0.848, 0.868, 0.889, 0.910, 0.932, 0.955, 0.978, 1.001, 1.025, 1.050, 1.075, 1.102,
  1.113, 1.139, 1.167, 1.195, 1.224, 1.254, 1.284, 1.315, 1.346, 1.378, 1.412, 1.446, 1.481, 1.517, 1.554, 1.592,
  1.631, 1.656, 1.695, 1.735, 1.775, 1.818, 1.861, 1.905, 1.949, 1.995, 2.041, 2.089, 2.139, 2.189, 2.240, 2.292,
  2.345, 2.399, 2.445, 2.506, 2.575, 2.646, 2.719, 2.794, 2.871, 2.951, 3.033, 3.118, 3.204, 3.293, 3.383, 3.476,
  3.570, 3.667, 3.768, 3.833, 3.867, 3.901, 3.935, 3.970, 4.005, 4.040, 4.076, 4.112, 4.148, 4.184, 4.220, 4.257,
  4.294, 4.331, 4.368, 4.405, 4.435, 4.467, 4.500, 4.533, 4.566, 4.600, 4.635, 4.669, 4.704, 4.739, 4.773, 4.808,
  4.843, 4.879, 4.915, 4.951, 4.988,
];
// Las capas 50 y 51 (canales dicroicos) están en blanco según el propio archivo properties.
const SPHEREX_BLANCAS = new Set([50, 51]);

interface CatalogoDef {
  key: 'gaia' | 'wise';
  nombre: string;
  tabla: string; // identificador en VizieR
  columnas: string;
  color: string;
  max: number;
  switchId: string;
  noticeId: string;
}

const CATALOGOS: readonly CatalogoDef[] = [
  {
    key: 'gaia', nombre: 'Gaia DR3', tabla: 'I/355/gaiadr3', color: '#f4b860', max: 3000,
    columnas: 'Source,RA_ICRS,DE_ICRS,Gmag,BP-RP,Plx,pmRA,pmDE,RUWE', switchId: 'swGaia', noticeId: 'gaiaNotice',
  },
  {
    key: 'wise', nombre: 'AllWISE', tabla: 'II/328/allwise', color: '#7fe0a5', max: 2000,
    columnas: 'AllWISE,RAJ2000,DEJ2000,W1mag,W2mag,W3mag,W4mag,pmRA,pmDE,ccf,qph', switchId: 'swWise', noticeId: 'wiseNotice',
  },
];

interface HiPSLayer { name: string; url: string; setSliceNumber?(slice: number): void }
interface CatalogLayer { getSources?(): unknown[] }
interface AladinViewer {
  gotoRaDec(ra: number, dec: number): void;
  setFoV(fovDegrees: number): void;
  setBaseImageLayer(layer: unknown): void;
  addCatalog(catalog: CatalogLayer): void;
  removeLayer(layer: CatalogLayer): void;
}
interface AladinLibrary {
  init: Promise<unknown>;
  aladin(selector: string, options: Record<string, unknown>): AladinViewer;
  imageHiPS(url: string, options: { name: string; url: string; successCallback?: () => void; errorCallback?: (error: unknown) => void }): HiPSLayer;
  catalogFromURL(url: string, options: Record<string, unknown>, onSuccess: (catalog: CatalogLayer) => void, onError: (error: unknown) => void): CatalogLayer;
}

/** Capa del cubo de SPHEREx más cercana a una longitud de onda (salta las capas en blanco). */
export function capaSpherex(lambdaUm: number): number {
  let mejor = 0;
  SPHEREX_LAMBDAS.forEach((valor, indice) => {
    if (SPHEREX_BLANCAS.has(indice)) return;
    if (Math.abs(valor - lambdaUm) < Math.abs(SPHEREX_LAMBDAS[mejor] - lambdaUm)) mejor = indice;
  });
  return mejor;
}

/** URL de VizieR (espejo CfA) para un cono alrededor del centro. */
export function urlVizier(def: CatalogoDef, centro: SkyPosition, radioArcsec: number): string {
  const params = new URLSearchParams({
    '-source': def.tabla,
    '-c': `${centro.ra.toFixed(6)} ${centro.dec >= 0 ? '+' : ''}${centro.dec.toFixed(6)}`,
    '-c.rs': String(Math.ceil(radioArcsec)),
    '-out.max': String(def.max),
    '-out': def.columnas,
  });
  return `${VIZIER}?${params}`;
}

export function mount(_root: ParentNode, store: Store, _actions: ViewActions): void {
  if (!verifyElements(['aladin', 'aladinMsg', 'aladinSurvey', 'aladinVersion', 'swGaia', 'gaiaNotice', 'swWise', 'wiseNotice'], 'aladinContext')) return;
  let viewer: AladinViewer | null = null;
  let library: AladinLibrary | null = null;
  let loading = false;
  let surveyRequest = 0;
  let capaFondo: HiPSLayer | null = null;
  let fondoEsSpherex = false;
  const activos: Record<CatalogoDef['key'], boolean> = { gaia: false, wise: false };
  const capasCatalogo: Partial<Record<CatalogoDef['key'], CatalogLayer>> = {};
  const pedidoCatalogo: Record<CatalogoDef['key'], number> = { gaia: 0, wise: 0 };
  let esperaRecarga = 0;
  const aladinRoot = document.getElementById('aladin');
  const surveySelect = document.getElementById('aladinSurvey') as HTMLSelectElement | null;
  const version = document.getElementById('aladinVersion');
  if (version) version.textContent = `v${aladinPackage.version}`;
  const es = (): boolean => store.getState().lang === 'es';

  function status(message: string, error = false): void {
    const node = document.getElementById('aladinMsg');
    if (!node) return;
    node.textContent = message;
    node.className = `hint${error ? ' sky-context-error' : ''}`;
    node.style.padding = '12px';
    node.hidden = false;
    if (error) console.error(`[aladinContext] ${message}`);
  }

  function aviso(def: CatalogoDef, texto: string): void {
    const node = document.getElementById(def.noticeId);
    if (node) node.textContent = texto;
  }

  function currentPosition(): SkyPosition { return store.getState().center; }

  async function start(): Promise<void> {
    if (!aladinRoot || loading || viewer || aladinRoot.clientWidth === 0) return;
    loading = true;
    status(es() ? 'Cargando Aladin Lite…' : 'Loading Aladin Lite…');
    try {
      const module = await import('aladin-lite');
      library = module.default as AladinLibrary;
      await library.init;
      const center = currentPosition();
      viewer = library.aladin('#aladin', {
        survey: surveySelect?.value || DEFAULT_SURVEY,
        target: `${center.ra} ${center.dec}`,
        fov: store.getState().fovArcmin / 60,
        cooFrame: 'ICRS', mode: 'dark', backgroundColor: 'rgb(8,18,28)',
        showZoomControl: false, showLayersControl: false, showGotoControl: false,
        showFullscreenControl: false, showSimbadPointerControl: false, showCooGridControl: false,
        // La retícula marca el centro de la búsqueda (la posición esperada del objetivo).
        showReticle: true, reticleColor: '#99dce5', reticleSize: 18,
        showFrame: false, showContextMenu: false, showStatusBar: false,
      });
      applySurvey(surveySelect?.value || DEFAULT_SURVEY);
      viewer.gotoRaDec(center.ra, center.dec);
      viewer.setFoV(store.getState().fovArcmin / 60);
      for (const def of CATALOGOS) if (activos[def.key]) cargarCatalogo(def);
    } catch (error) {
      console.warn('[aladinContext] No se pudo inicializar el visor.', error);
      status(es()
        ? 'No se pudo cargar Aladin Lite o el fondo del cielo. Verifica conexión y compatibilidad WebGL2; el reproductor sigue disponible.'
        : 'Aladin Lite or the sky background could not be loaded. Check connectivity and WebGL2; the player remains available.', true);
    } finally { loading = false; }
  }

  // Si el fondo es el cubo de SPHEREx, muestra la capa de la longitud de onda elegida en el panel.
  function sincronizarCapaSpherex(): void {
    if (!fondoEsSpherex || !capaFondo?.setSliceNumber) return;
    try { capaFondo.setSliceNumber(capaSpherex(store.getState().lambda)); } catch (error) { console.warn('[aladinContext] No se pudo cambiar la capa de SPHEREx.', error); }
  }

  function applySurvey(url: string): void {
    if (!library || !viewer) return;
    const request = ++surveyRequest;
    const name = surveySelect?.selectedOptions[0]?.textContent ?? 'HiPS';
    fondoEsSpherex = url === SPHEREX_HIPS;
    status(`${es() ? 'Cargando' : 'Loading'} ${name}…`);
    try {
      const layer = library.imageHiPS(url, {
        name, url,
        successCallback: () => {
          if (request !== surveyRequest) return;
          const node = document.getElementById('aladinMsg'); if (node) node.hidden = true;
          sincronizarCapaSpherex();
        },
        errorCallback: (error) => {
          if (request !== surveyRequest) return;
          console.warn('[aladinContext] Falló el HiPS seleccionado.', error);
          status(es() ? `No se pudo cargar ${name}. Prueba otro fondo en el selector.` : `Could not load ${name}. Try another background.`, true);
        },
      });
      capaFondo = layer;
      viewer.setBaseImageLayer(layer);
      window.setTimeout(() => {
        const node = document.getElementById('aladinMsg');
        if (request === surveyRequest && node && !node.hidden && node.textContent?.startsWith(es() ? 'Cargando' : 'Loading')) {
          status(es() ? `El fondo ${name} no respondió. Prueba otro.` : `${name} did not respond. Try another.`, true);
        }
      }, 20_000);
    } catch {
      status(es() ? `No se pudo cambiar al fondo ${name}.` : `Could not switch to ${name}.`, true);
    }
  }

  // Pide a VizieR (espejo del CfA) las fuentes del catálogo dentro del campo y las dibuja.
  // Al hacer clic en una fuente, Aladin muestra su tabla de datos (magnitudes, movimiento propio...).
  function cargarCatalogo(def: CatalogoDef): void {
    if (!library || !viewer) { aviso(def, es() ? 'Se cargará cuando Aladin esté listo.' : 'Will load once Aladin is ready.'); return; }
    const pedido = ++pedidoCatalogo[def.key];
    const anterior = capasCatalogo[def.key];
    if (anterior) { try { viewer.removeLayer(anterior); } catch { /* ya no estaba */ } delete capasCatalogo[def.key]; }
    if (!activos[def.key]) { aviso(def, ''); return; }

    // Radio = media diagonal del campo, para cubrir también las esquinas.
    const radioArcsec = (store.getState().fovArcmin * 60 / 2) * Math.SQRT2;
    aviso(def, es() ? `Consultando ${def.nombre} en VizieR…` : `Querying ${def.nombre} on VizieR…`);
    const url = urlVizier(def, currentPosition(), radioArcsec);
    const view = viewer;
    library.catalogFromURL(url, {
      name: def.nombre, color: def.color, sourceSize: 10, shape: 'circle', onClick: 'showTable', hoverColor: '#ffffff',
    }, (catalogo) => {
      if (pedido !== pedidoCatalogo[def.key] || !activos[def.key]) return;
      view.addCatalog(catalogo);
      capasCatalogo[def.key] = catalogo;
      const n = catalogo.getSources?.().length ?? 0;
      const tope = n >= def.max ? (es() ? ` (máximo ${def.max})` : ` (capped at ${def.max})`) : '';
      aviso(def, es()
        ? `${def.nombre}: ${n} fuentes${tope} · VizieR (CfA). Clic en una para ver sus datos.`
        : `${def.nombre}: ${n} sources${tope} · VizieR (CfA). Click one to see its data.`);
    }, (error) => {
      if (pedido !== pedidoCatalogo[def.key]) return;
      console.warn(`[aladinContext] Falló ${def.nombre}.`, error);
      aviso(def, es() ? `No se pudo consultar ${def.nombre} (VizieR CfA). Intenta de nuevo.` : `Could not query ${def.nombre} (VizieR CfA). Try again.`);
    });
  }

  for (const def of CATALOGOS) {
    const boton = document.getElementById(def.switchId) as HTMLButtonElement | null;
    if (!boton) continue;
    boton.disabled = false;
    boton.setAttribute('aria-checked', 'false');
    boton.addEventListener('click', () => {
      activos[def.key] = !activos[def.key];
      boton.setAttribute('aria-checked', String(activos[def.key]));
      if (def.key === 'gaia') store.setState({ gaiaEnabled: activos.gaia });
      cargarCatalogo(def);
    });
    aviso(def, '');
  }

  surveySelect?.addEventListener('change', () => applySurvey(surveySelect.value));
  const resize = new ResizeObserver(() => { if (aladinRoot?.clientWidth) void start(); });
  if (aladinRoot) resize.observe(aladinRoot);
  store.subscribe((_state, changed) => {
    if (changed.has('center') || changed.has('fovArcmin')) {
      const center = currentPosition();
      try { viewer?.gotoRaDec(center.ra, center.dec); viewer?.setFoV(store.getState().fovArcmin / 60); } catch (error) { console.warn('[aladinContext] No se pudo sincronizar centro/FOV.', error); }
      // Espera un momento antes de volver a consultar los catálogos (el FOV cambia en pasos rápidos).
      window.clearTimeout(esperaRecarga);
      esperaRecarga = window.setTimeout(() => { for (const def of CATALOGOS) if (activos[def.key]) cargarCatalogo(def); }, 600);
    }
    if (changed.has('lambda') || changed.has('detector')) sincronizarCapaSpherex();
    if (changed.has('view') && store.getState().view === 'explore') void start();
    if (changed.has('lang') && !viewer && !loading) status(translate(store.getState().lang, 'aladinLoading'));
  });

  // Aladin empieza antes del montaje de las demás vistas y no comparte su ruta de error.
  void start();
}
