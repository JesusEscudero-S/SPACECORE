import aladinPackage from '../../../node_modules/aladin-lite/package.json';
import { verifyElements } from '../../lib/dom';
import { translate } from '../../lib/i18n';
import type { SkyPosition } from '../../api/source';
import type { Store } from '../../state/store';
import type { ViewActions } from '../contracts';

const DEFAULT_SURVEY = 'https://skies.esac.esa.int/DSSColor';
interface HiPSLayer { name: string; url: string }
interface AladinViewer {
  gotoRaDec(ra: number, dec: number): void;
  setFoV(fovDegrees: number): void;
  setBaseImageLayer(layer: unknown): void;
}
interface AladinLibrary {
  init: Promise<unknown>;
  aladin(selector: string, options: Record<string, unknown>): AladinViewer;
  imageHiPS(url: string, options: { name: string; url: string; successCallback?: () => void; errorCallback?: (error: unknown) => void }): HiPSLayer;
}

export function mount(_root: ParentNode, store: Store, _actions: ViewActions): void {
  if (!verifyElements(['aladin', 'aladinMsg', 'aladinSurvey', 'aladinVersion', 'swGaia', 'gaiaNotice'], 'aladinContext')) return;
  let viewer: AladinViewer | null = null;
  let library: AladinLibrary | null = null;
  let loading = false;
  let surveyRequest = 0;
  const aladinRoot = document.getElementById('aladin');
  const surveySelect = document.getElementById('aladinSurvey') as HTMLSelectElement | null;
  const version = document.getElementById('aladinVersion');
  if (version) version.textContent = `v${aladinPackage.version}`;

  function status(message: string, error = false): void {
    const node = document.getElementById('aladinMsg');
    if (!node) return;
    node.textContent = message;
    node.className = `hint${error ? ' sky-context-error' : ''}`;
    node.style.padding = '12px';
    node.hidden = false;
    if (error) console.error(`[aladinContext] ${message}`);
  }

  function currentPosition(): SkyPosition { return store.getState().center; }

  async function start(): Promise<void> {
    if (!aladinRoot || loading || viewer || aladinRoot.clientWidth === 0) return;
    loading = true;
    status(store.getState().lang === 'es' ? 'Cargando el fondo DSS2 desde ESAC…' : 'Loading the DSS2 background from ESAC…');
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
        showReticle: false, showFrame: false, showContextMenu: false, showStatusBar: false,
      });
      applySurvey(surveySelect?.value || DEFAULT_SURVEY);
      viewer.gotoRaDec(center.ra, center.dec);
      viewer.setFoV(store.getState().fovArcmin / 60);
    } catch (error) {
      console.warn('[aladinContext] No se pudo inicializar el visor.', error);
      const lang = store.getState().lang;
      status(lang === 'es'
        ? 'No se pudo cargar Aladin Lite o el fondo del cielo. Verifica conexión y compatibilidad WebGL2; el reproductor de demostración sigue disponible.'
        : 'Aladin Lite or the sky background could not be loaded. Check connectivity and WebGL2; the demo player remains available.', true);
    } finally { loading = false; }
  }

  function applySurvey(url: string): void {
    if (!library || !viewer) return;
    const request = ++surveyRequest;
    const name = surveySelect?.selectedOptions[0]?.textContent ?? 'HiPS';
    status(`${store.getState().lang === 'es' ? 'Cargando' : 'Loading'} ${name}…`);
    try {
      const layer = library.imageHiPS(url, {
        name, url,
        successCallback: () => { if (request === surveyRequest) { const node = document.getElementById('aladinMsg'); if (node) node.hidden = true; } },
        errorCallback: (error) => {
          if (request !== surveyRequest) return;
          console.warn('[aladinContext] Falló el HiPS seleccionado.', error);
          status(store.getState().lang === 'es' ? `No se pudo cargar ${name}. Prueba otro espejo en el selector.` : `Could not load ${name}. Try another mirror from the selector.`, true);
        },
      });
      viewer.setBaseImageLayer(layer);
      window.setTimeout(() => {
        const node = document.getElementById('aladinMsg');
        if (request === surveyRequest && node && !node.hidden && node.textContent?.startsWith(store.getState().lang === 'es' ? 'Cargando' : 'Loading')) {
          status(store.getState().lang === 'es' ? `El fondo ${name} no respondió. Prueba otro espejo.` : `${name} did not respond. Try another mirror.`, true);
        }
      }, 20_000);
    } catch (error) {
      status(store.getState().lang === 'es' ? `No se pudo cambiar al fondo ${name}.` : `Could not switch to ${name}.`, true);
    }
  }

  surveySelect?.addEventListener('change', () => applySurvey(surveySelect.value));
  const resize = new ResizeObserver(() => { if (aladinRoot?.clientWidth) void start(); });
  if (aladinRoot) resize.observe(aladinRoot);
  store.subscribe((_state, changed) => {
    if (changed.has('center') || changed.has('fovArcmin')) {
      const center = currentPosition();
      try { viewer?.gotoRaDec(center.ra, center.dec); viewer?.setFoV(store.getState().fovArcmin / 60); } catch (error) { console.warn('[aladinContext] No se pudo sincronizar centro/FOV.', error); }
    }
    if (changed.has('view') && store.getState().view === 'explore') void start();
    if (changed.has('lang') && !viewer && !loading) status(translate(store.getState().lang, 'aladinLoading'));
  });

  // Aladin empieza antes del montaje de las demás vistas y no comparte su ruta de error.
  void start();
}
