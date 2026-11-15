import { API_BASE, COLLECTION, DET, channelWidth, detector } from './config';
import { ClienteApi } from './api/cliente';
import { DemoSource } from './api/demoSource';
import type { FrameSource, Observation, SkyPosition, Target, ViewName } from './api/source';
import { currentDecimalYear, posicionEspectro, propagarProperMotion } from './lib/coords';
import { download, showMessage, verifyElements } from './lib/dom';
import { applyI18n } from './lib/i18n';
import { localResolve, TARGETS } from './lib/objects';
import type { AppState, Store } from './state/store';
import { createStore } from './state/store';
import { readUrlState, writeUrlState } from './state/urlState';
import { mount as mountVistaAladin } from './components/visor/VistaAladin';
import { mount as mountComparar } from './components/visor/Comparar';
import type { ViewActions } from './components/contracts';
import { mount as mountBarraTiempo } from './components/visor/BarraTiempo';
import { mount as mountPanelInfo } from './components/busqueda/PanelInfo';
import { mount as mountCompartir } from './components/busqueda/Compartir';
import { mount as mountBuscador } from './components/busqueda/Buscador';
import { mount as mountReproductor } from './components/visor/Reproductor';
import { mount as mountEspectro } from './components/visor/Espectro';

// Los objetivos se centran en su posición al 1 de enero del año en curso, no en la de "hoy":
// así las coordenadas no cambian cada día y lo precalculado en la caché del backend sirve todo
// el año. Barnard, la más rápida, se mueve menos de 11″ en un año: en un campo de 6′ no se nota.
// backend/scripts/precalcular.py usa EXACTAMENTE esta misma regla: si cambias una, cambia la otra.
function epocaDeCentrado(): number { return Math.floor(currentDecimalYear()); }

const route = readUrlState();
const queryTarget = TARGETS.find((target) => target.key === route.query) ?? localResolve(route.query);
const defaultTarget: Target = queryTarget ?? TARGETS[0];
const initialTarget = route.ra !== null && route.dec !== null ? queryTarget : defaultTarget;
const defaultCenter = route.ra !== null && route.dec !== null
  ? { ra: route.ra, dec: route.dec }
  : propagarProperMotion({ ra: defaultTarget.ra, dec: defaultTarget.dec, pmRA: defaultTarget.pmra, pmDec: defaultTarget.pmdec }, epocaDeCentrado());
const selectedDetector = detector(route.detector);
const requestedLambda = route.lambda >= selectedDetector.min && route.lambda <= selectedDetector.max
  ? route.lambda : selectedDetector.min + (9.5 / 17) * (selectedDetector.max - selectedDetector.min);

const initialState: AppState = {
  api: route.api ?? API_BASE, lang: route.lang, view: route.view, collection: route.collection || COLLECTION,
  fovArcmin: route.fovArcmin, fovInput: String(route.fovArcmin), detector: route.detector,
  tolerance: route.tolerance, mode: route.mode, epochA: route.epochA, epochB: route.epochB,
  lambda: requestedLambda, playing: route.playing, speed: 1, embed: route.embed,
  query: route.query || (route.ra === null ? defaultTarget.key : ''),
  center: defaultCenter, target: initialTarget, observations: [], currentIndex: 0, frame: null,
  frameA: null, frameB: null, slider: 0.5, loading: true, error: '',
  display: { stretch: 'asinh', smooth: true, commonScale: true, subtractBackground: true, grid: true, marker: true, showMask: false },
  spectrum: { aperture: 18, annulusInner: 30, annulusOuter: 50, subtractBackground: true, showError: true, excludeMask: false, colorEpoch: true, logarithmic: true, points: [] },
  selectedSource: null, gaiaEnabled: false,
};

const store = createStore(initialState);
const source: FrameSource = initialState.api ? new ClienteApi(initialState.api) : new DemoSource();
let allObservations: Observation[] = [];
let loadSequence = 0;
const frameCache = new Map<string, ReturnType<FrameSource['frame']>>();

const actions: ViewActions = {
  async search(query) {
    const value = query.trim();
    if (!value) return;
    const pair = value.match(/^\s*([+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+))\s*[,;\s]\s*([+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+))\s*$/u);
    if (pair) {
      const ra = Number(pair[1].replace(',', '.')), dec = Number(pair[2].replace(',', '.'));
      if (ra >= 0 && ra <= 360 && dec >= -90 && dec <= 90) this.applyCoordinates({ ra, dec }, store.getState().fovArcmin, store.getState().fovInput);
      else store.setState({ error: store.getState().lang === 'es' ? 'Coordenadas fuera de rango.' : 'Coordinates out of range.' });
      return;
    }
    store.setState({ loading: true, error: '' });
    try {
      const target = TARGETS.find((entry) => entry.key === value) ?? localResolve(value) ?? await source.resolve(value);
      if (!target) {
        store.setState({ loading: false, error: store.getState().lang === 'es' ? `No se encontró «${value}». Prueba con coordenadas.` : `“${value}” was not found. Try coordinates.` });
        return;
      }
      this.selectTarget(target);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      store.setState({ loading: false, error: store.getState().lang === 'es' ? `No se pudo resolver el objeto: ${message}` : `Could not resolve the object: ${message}` });
    }
  },
  selectTarget(target) {
    const center = propagarProperMotion({ ra: target.ra, dec: target.dec, pmRA: target.pmra, pmDec: target.pmdec }, epocaDeCentrado());
    const state = store.getState();
    const targetDetector = target.detector ?? state.detector;
    const range = detector(targetDetector);
    store.setState({
      target, center, query: target.key, detector: targetDetector,
      lambda: target.detector ? (range.min + range.max) / 2 : Math.max(range.min, Math.min(range.max, state.lambda)),
      selectedSource: null, error: '',
    });
    const input = document.getElementById('searchInput') as HTMLInputElement | null;
    if (input) input.value = target.name[state.lang];
    void this.refresh();
  },
  applyCoordinates(position, fovArcmin, originalFov) {
    store.setState({
      center: position, target: null, query: '', selectedSource: position,
      fovArcmin: Math.min(40, Math.max(1.5, fovArcmin)), fovInput: originalFov, error: '',
    });
    void this.refresh();
  },
  changeFov(deltaFactor) {
    const next = Math.min(40, Math.max(1.5, store.getState().fovArcmin * deltaFactor));
    store.setState({ fovArcmin: next, fovInput: next.toFixed(1) });
    void this.refresh();
  },
  async refresh() {
    const state = store.getState();
    const sequence = ++loadSequence;
    store.setState({ loading: true, error: '', frame: null, frameA: null, frameB: null });
    try {
      allObservations = await source.epocas(state.center, state.fovArcmin, state.collection, state.target);
      if (sequence !== loadSequence) return;
      const observations = filterObservations(allObservations, store.getState());
      if (!observations.length) {
        store.setState({ observations: [], currentIndex: 0, loading: false, error: store.getState().lang === 'es'
          ? 'Sin cuadros con este detector y λ. Prueba otra tolerancia o detector.'
          : 'No frames match this detector and wavelength. Try another tolerance or detector.' });
        return;
      }
      const current = store.getState();
      const epochA = observations.some((entry) => entry.id === current.epochA) ? current.epochA : observations[0].id;
      const epochB = observations.some((entry) => entry.id === current.epochB) ? current.epochB : observations.at(-1)!.id;
      // loading sigue en true hasta que llegue el primer cuadro (con backend, /frames puede tardar ~1 min).
      store.setState({ observations, epochA, epochB, currentIndex: 0, loading: true, error: '' });
      await loadFrame(observations[0], sequence);
      if (store.getState().view === 'compare') await loadCompareFrames(sequence);
    } catch (error) {
      if (sequence !== loadSequence) return;
      const message = error instanceof Error ? error.message : String(error);
      store.setState({ observations: [], frame: null, loading: false, error: store.getState().lang === 'es' ? `No se pudieron cargar las épocas: ${message}` : `Could not load epochs: ${message}` });
    }
  },
  setView(view) {
    store.setState({ view });
    if (view === 'compare') void loadCompareFrames(loadSequence);
    if (view === 'spectrum' && !store.getState().spectrum.points.length) void this.computeSpectrum();
  },
  async chooseObservation(observation) {
    const index = store.getState().observations.findIndex((entry) => entry.id === observation.id);
    if (index >= 0) store.setState({ currentIndex: index });
    store.setState({ playing: false });
    await loadFrame(observation, loadSequence);
  },
  step(delta) {
    const state = store.getState();
    if (!state.observations.length) return;
    const index = (state.currentIndex + delta + state.observations.length) % state.observations.length;
    store.setState({ currentIndex: index });
    void loadFrame(state.observations[index], loadSequence);
  },
  togglePlayback() { store.setState({ playing: !store.getState().playing }); },
  async computeSpectrum() {
    const state = store.getState();
    const pedido = spectrumOptionsKey(state);
    store.setState({ error: '' });
    try {
      const points = await source.spectrum(posicionEspectro(state.center, state.selectedSource), state.collection, {
        ap: state.spectrum.aperture, annIn: state.spectrum.annulusInner, annOut: state.spectrum.annulusOuter,
        subBg: state.spectrum.subtractBackground, exclMask: state.spectrum.excludeMask,
      }, state.target);
      // Si mientras tanto cambió el objetivo o las opciones, esta respuesta ya es vieja.
      if (spectrumOptionsKey(store.getState()) !== pedido) return;
      store.setState({ spectrum: { ...store.getState().spectrum, points } });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      store.setState({ error: store.getState().lang === 'es' ? `No se pudo calcular el espectro: ${message}` : `Could not calculate spectrum: ${message}` });
    }
  },
  share(kind) { window.dispatchEvent(new CustomEvent('spherex:share', { detail: kind })); },
  export(kind) {
    if (kind === 'csv') {
      const rows = [['obs_id', 'date', 'mjd', 'detector', 'lambda_um', 'flux_mjy', 'err_mjy', 'nbad'], ...store.getState().spectrum.points.map((point) => [point.obs_id, point.date, String(point.mjd), point.detector, String(point.lambda_um), String(point.flux_mjy), String(point.err_mjy), String(point.nbad)])];
      download('spherex-spectrum.csv', new Blob([rows.map((row) => row.join(',')).join('\n')], { type: 'text/csv;charset=utf-8' }));
      showMessage(store.getState().lang === 'es' ? 'CSV descargado.' : 'CSV downloaded.');
      return;
    }
    const canvas = document.getElementById('skyCanvas') as HTMLCanvasElement | null;
    if (!canvas) return showMessage('[modal] Falta #skyCanvas; no se pudo exportar el PNG.', 'error');
    canvas.toBlob((blob) => {
      if (blob) download('spherex-frame.png', blob);
      else showMessage(store.getState().lang === 'es' ? 'No se pudo crear el PNG.' : 'Could not create PNG.', 'error');
    });
  },
};

function filterObservations(observations: Observation[], state: Readonly<AppState>): Observation[] {
  // Con backend, cada época es la suma de TODO el detector (no hay λ por imagen): el filtro de λ no aplica.
  const width = state.tolerance === 'inf' || !source.isDemo ? Infinity : Number(state.tolerance) * channelWidth(state.detector);
  return observations.filter((observation) => observation.detector === state.detector && Math.abs(observation.lambda_um - state.lambda) <= width)
    .sort((a, b) => a.mjd - b.mjd);
}

async function loadFrame(observation: Observation, sequence: number): Promise<void> {
  const state = store.getState();
  const key = `${state.collection}:${observation.id}:${state.center.ra.toFixed(6)}:${state.center.dec.toFixed(6)}:160`;
  try {
    let pending = frameCache.get(key);
    if (!pending) { pending = source.frame(observation, state.center, 160, 160, state.collection); frameCache.set(key, pending); }
    const frame = await pending;
    if (sequence !== loadSequence) return;
    store.setState({ frame, loading: false });
  } catch (error) {
    if (sequence !== loadSequence) return;
    const message = error instanceof Error ? error.message : String(error);
    store.setState({ loading: false, error: store.getState().lang === 'es' ? `No se pudo cargar el cuadro: ${message}` : `Could not load frame: ${message}` });
  }
}

async function loadCompareFrames(sequence: number): Promise<void> {
  const state = store.getState();
  const first = state.observations.find((observation) => observation.id === state.epochA);
  const second = state.observations.find((observation) => observation.id === state.epochB);
  if (!first || !second) return;
  try {
    const [frameA, frameB] = await Promise.all([
      source.frame(first, state.center, 160, 160, state.collection),
      source.frame(second, state.center, 160, 160, state.collection),
    ]);
    if (sequence !== loadSequence) return;
    store.setState({ frameA, frameB });
  } catch (error) {
    if (sequence !== loadSequence) return;
    const message = error instanceof Error ? error.message : String(error);
    store.setState({ error: `No se pudieron cargar los cuadros A/B: ${message}` });
  }
}

function spectrumOptionsKey(state: Readonly<AppState>): string {
  return [state.spectrum.aperture, state.spectrum.annulusInner, state.spectrum.annulusOuter, state.spectrum.subtractBackground, state.spectrum.excludeMask, state.selectedSource?.ra, state.selectedSource?.dec, state.center.ra, state.center.dec, state.collection, state.target?.key].join(':');
}

function subscribeToState(): void {
  const urlKeys = ['api', 'lang', 'view', 'collection', 'fovArcmin', 'detector', 'tolerance', 'mode', 'epochA', 'epochB', 'lambda', 'playing', 'embed', 'query', 'center'];
  let lastSpectrumOptions = spectrumOptionsKey(store.getState());
  store.subscribe((state, changed) => {
    if (urlKeys.some((key) => changed.has(key as keyof AppState))) writeUrlState(state);
    if (changed.has('lang')) applyI18n(state.lang);
    if (changed.has('detector') || changed.has('tolerance') || changed.has('lambda')) {
      const observations = filterObservations(allObservations, state);
      const epochA = observations.some((entry) => entry.id === state.epochA) ? state.epochA : observations[0]?.id ?? '';
      const epochB = observations.some((entry) => entry.id === state.epochB) ? state.epochB : observations.at(-1)?.id ?? '';
      store.setState({ observations, epochA, epochB, currentIndex: 0, frame: null, frameA: null, frameB: null });
      if (observations[0]) void loadFrame(observations[0], loadSequence);
      if (state.view === 'compare') void loadCompareFrames(loadSequence);
    } else if (changed.has('epochA') || changed.has('epochB')) {
      if (state.view === 'compare') void loadCompareFrames(loadSequence);
    } else if (changed.has('view') && state.view === 'compare') void loadCompareFrames(loadSequence);
    if (changed.has('collection') || changed.has('center') || changed.has('fovArcmin')) frameCache.clear();
    // El espectro depende del objetivo, del centro y de las opciones de extracción. Si algo de
    // eso cambia: en la pestaña Espectro se recalcula al momento; fuera de ella se borran los
    // puntos viejos para que se recalcule al entrar (antes había que presionar "Recalcular").
    const currentOptions = spectrumOptionsKey(state);
    if (currentOptions !== lastSpectrumOptions) {
      lastSpectrumOptions = currentOptions;
      if (state.view === 'spectrum') void actions.computeSpectrum();
      else if (state.spectrum.points.length) store.setState({ spectrum: { ...state.spectrum, points: [] } });
    }
  });
}

async function boot(): Promise<void> {
  if (initialState.embed) document.body.classList.add('embed');
  applyI18n(initialState.lang);
  verifyElements([
    'app', 'searchForm', 'searchInput', 'nav', 'queryForm', 'inRA', 'inDec', 'inFov', 'detBtns', 'inLam', 'inTol', 'inColl',
    'skyWrap', 'skyCanvas', 'viewSky', 'viewSpec', 'cmpModes', 'cmpBar', 'selA', 'selB', 'sliderLine', 'sliderHandle',
    'timeline', 'bPrev', 'bPlay', 'bNext', 'inSpeed', 'aladin', 'aladinSurvey', 'gaiaNotice', 'specCanvas', 'specRows',
    'inStretch', 'swCommon', 'swSubBg', 'swMarker', 'swMask', 'modalTitle', 'modalBody', 'backdrop',
  ], 'boot');
  // El contexto de Aladin arranca primero; su carga asíncrona no depende de las otras vistas.
  mountVistaAladin(document, store, actions);
  mountBuscador(document, store, actions);
  mountComparar(document, store, actions);
  mountReproductor(document, store, actions);
  mountBarraTiempo(document, store, actions);
  mountPanelInfo(document, store, actions);
  mountEspectro(document, store, actions);
  mountCompartir(document, store, actions);
  subscribeToState();
  if (route.query && !queryTarget) {
    try {
      const target = await source.resolve(route.query);
      if (target) actions.selectTarget(target);
      else if (route.ra === null) store.setState({ error: store.getState().lang === 'es' ? `No se pudo resolver «${route.query}».` : `Could not resolve “${route.query}”.` });
    } catch (error) { store.setState({ error: error instanceof Error ? error.message : String(error) }); }
  }
  if (source instanceof ClienteApi && !(await source.salud())) {
    store.setState({ error: store.getState().lang === 'es'
      ? `El backend (${initialState.api}) no responde a /health. Revisa que uvicorn esté corriendo.`
      : `The backend (${initialState.api}) does not answer /health. Check that uvicorn is running.` });
  }
  await actions.refresh();
  if (initialState.view === 'spectrum') await actions.computeSpectrum();
}

void boot().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error('[boot] Error de inicio:', error);
  store.setState({ loading: false, error: `No se pudo iniciar la aplicación: ${message}` });
  showMessage(`No se pudo iniciar la aplicación: ${message}`, 'error');
});
