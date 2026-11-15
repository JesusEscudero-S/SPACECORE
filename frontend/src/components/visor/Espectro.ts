import type { SpectrumPoint } from '../../api/source';
import { PIX_ARCSEC } from '../../config';
import { translate } from '../../lib/i18n';
import type { Store } from '../../state/store';
import type { ViewActions } from '../contracts';
import { verifyElements } from '../../lib/dom';

interface PlotlyApi {
  newPlot(target: HTMLElement, data: Record<string, unknown>[], layout: Record<string, unknown>, config?: Record<string, unknown>): Promise<unknown>;
  react(target: HTMLElement, data: Record<string, unknown>[], layout: Record<string, unknown>, config?: Record<string, unknown>): Promise<unknown>;
  purge(target: HTMLElement): void;
}
interface PlotClickEvent { points?: { pointNumber?: number }[] }
interface PlotElement extends HTMLElement { on?: (event: string, handler: (event: PlotClickEvent) => void) => void }

export function mount(_root: ParentNode, store: Store, actions: ViewActions): void {
  if (!verifyElements(['specCanvas', 'specRows', 'specSub', 'specMeta', 'swColorEpoch', 'swYlog', 'btnRecalc'], 'spectrum')) return;
  let plotly: PlotlyApi | null = null;
  let loadPromise: Promise<PlotlyApi> | null = null;
  let renderedOnce = false;
  let lastPointSignature = '';

  const loadPlotly = (): Promise<PlotlyApi> => {
    if (!loadPromise) loadPromise = import('plotly.js-basic-dist-min').then((module) => module.default as unknown as PlotlyApi);
    return loadPromise;
  };
  const chartBox = document.getElementById('specCanvas') as PlotElement | null;
  const compute = (): void => { void actions.computeSpectrum(); };
  document.getElementById('btnRecalc')?.addEventListener('click', compute);
  window.addEventListener('spherex:compute-spectrum', compute);

  async function draw(points: SpectrumPoint[]): Promise<void> {
    if (!chartBox) return;
    plotly = await loadPlotly();
    const valid = points.filter((point) => Number.isFinite(point.flux_mjy) && Number.isFinite(point.lambda_um));
    const minMjd = Math.min(...valid.map((point) => point.mjd), 0), maxMjd = Math.max(...valid.map((point) => point.mjd), 0);
    const colors = valid.map((point) => {
      const fraction = maxMjd > minMjd ? (point.mjd - minMjd) / (maxMjd - minMjd) : 0;
      return store.getState().spectrum.colorEpoch
        ? `rgb(${Math.round(153 + 73 * fraction)},${Math.round(220 - 36 * fraction)},${Math.round(229 - 122 * fraction)})`
        : '#99dce5';
    });
    const state = store.getState();
    // Círculo hueco = había píxeles sin dato en la apertura (centro saturado): el flujo real es mayor.
    const saturado = state.lang === 'es' ? '<br>centro saturado: flujo por debajo del real' : '<br>saturated core: flux underestimated';
    const trace: Record<string, unknown> = {
      type: 'scatter', mode: 'markers', name: translate(state.lang, 'legFlux'),
      x: valid.map((point) => point.lambda_um), y: valid.map((point) => point.flux_mjy),
      text: valid.map((point) => (point.nbad > 0 ? saturado : '')),
      marker: {
        color: colors, size: 7, line: { color: colors, width: 1.5 },
        symbol: valid.map((point) => (point.nbad > 0 ? 'circle-open' : 'circle')),
      },
      error_y: state.spectrum.showError ? { type: 'data', array: valid.map((point) => point.err_mjy), visible: true, color: '#99dce5', thickness: 1 } : { visible: false },
      customdata: valid.map((point) => point.obs_id),
      hovertemplate: '%{x:.3f} µm<br>%{y:.3g} mJy%{text}<extra></extra>',
    };
    const shapes = [1.09, 1.62, 2.41, 3.82, 4.42].map((x) => ({ type: 'line', x0: x, x1: x, y0: 0, y1: 1, yref: 'paper', line: { color: '#39424f', dash: 'dot', width: 1 } }));
    const layout: Record<string, unknown> = {
      autosize: true, paper_bgcolor: '#0c0f14', plot_bgcolor: '#0c0f14',
      font: { family: 'Inter, sans-serif', color: '#b4bcc8', size: 11 },
      margin: { l: 64, r: 20, t: 30, b: 58 }, showlegend: false, shapes,
      xaxis: { title: { text: translate(state.lang, 'xlab') }, range: [0.75, 5], gridcolor: '#202832', zerolinecolor: '#39424f' },
      yaxis: { title: { text: translate(state.lang, 'unit') }, type: state.spectrum.logarithmic ? 'log' : 'linear', gridcolor: '#202832', zerolinecolor: '#39424f' },
    };
    const config = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d'] };
    if (renderedOnce) await plotly.react(chartBox, [trace], layout, config);
    else {
      await plotly.newPlot(chartBox, [trace], layout, config);
      renderedOnce = true;
      chartBox.on?.('plotly_click', (event) => {
        const index = event.points?.[0]?.pointNumber;
        if (index === undefined) return;
        const selected = valid[index];
        const observation = store.getState().observations.find((entry) => entry.id === selected?.obs_id);
        if (observation) void actions.chooseObservation(observation);
      });
    }
  }

  function renderTable(points: SpectrumPoint[]): void {
    const body = document.getElementById('specRows');
    if (!body) return;
    body.replaceChildren();
    const sorted = [...points].sort((a, b) => a.mjd - b.mjd);
    for (const point of sorted) {
      const row = document.createElement('tr');
      for (const text of [point.date, point.lambda_um.toFixed(3), point.detector, `${point.flux_mjy.toPrecision(3)} ± ${point.err_mjy.toPrecision(2)} mJy`]) {
        const cell = document.createElement('td'); cell.textContent = text; row.append(cell);
      }
      row.addEventListener('click', () => {
        const observation = store.getState().observations.find((entry) => entry.id === point.obs_id);
        if (observation) void actions.chooseObservation(observation);
      });
      body.append(row);
    }
  }

  // Muestra la sección del espectro y oculta el visor de imágenes (y al revés). Antes nadie
  // quitaba el atributo hidden de #viewSpec, así que la pestaña "Espectro" nunca se veía.
  function mostrarVista(): void {
    const enEspectro = store.getState().view === 'spectrum';
    const cielo = document.getElementById('viewSky');
    const espectro = document.getElementById('viewSpec');
    const cambio = cielo !== null && cielo.hidden !== enEspectro;
    if (cielo) cielo.hidden = enEspectro;
    if (espectro) espectro.hidden = !enEspectro;
    // Al volver a mostrar el visor, que recalcule su tamaño (estuvo oculto con ancho 0).
    if (cambio && !enEspectro) window.dispatchEvent(new Event('resize'));
  }

  function render(): void {
    const state = store.getState();
    mostrarVista();
    const colorSwitch = document.getElementById('swColorEpoch');
    const logSwitch = document.getElementById('swYlog');
    colorSwitch?.setAttribute('aria-checked', String(state.spectrum.colorEpoch));
    logSwitch?.setAttribute('aria-checked', String(state.spectrum.logarithmic));
    const subtitle = document.getElementById('specSub');
    if (subtitle) {
      subtitle.textContent = `${state.target?.name[state.lang] ?? 'Fuente'} · ${state.spectrum.points.length} puntos${state.api ? '' : state.lang === 'es' ? ' (simulados)' : ' (simulated)'}`;
      // Estrellas muy brillantes (R Draconis) saturan en TODAS las imágenes: con el filtro activo no queda ninguno.
      if (state.api && state.spectrum.excludeMask && !state.spectrum.points.length) {
        subtitle.textContent += state.lang === 'es'
          ? ' · todos tienen el centro saturado: desactiva "Excluir píxeles marcados" para verlos'
          : ' · all have a saturated core: turn off "Exclude flagged pixels" to see them';
      }
    }
    const metadata = document.getElementById('specMeta');
    if (metadata) {
      metadata.replaceChildren();
      const items = [
        [translate(state.lang, 'metaSrc'), state.api ? 'API' : state.lang === 'es' ? 'Simulado (demo)' : 'Simulated (demo)'],
        [translate(state.lang, 'metaColl'), state.collection], [translate(state.lang, 'metaPix'), `${PIX_ARCSEC}″/px`],
        [translate(state.lang, 'metaAp'), `${state.spectrum.aperture}″ · ${state.spectrum.annulusInner}–${state.spectrum.annulusOuter}″`],
      ];
      items.forEach(([name, value]) => { const dt = document.createElement('dt'), dd = document.createElement('dd'); dt.textContent = name; dd.textContent = value; metadata.append(dt, dd); });
    }
    const signature = `${state.spectrum.points.length}:${state.spectrum.points[0]?.obs_id ?? ''}:${state.spectrum.points.at(-1)?.obs_id ?? ''}`;
    if (signature !== lastPointSignature) { renderTable(state.spectrum.points); lastPointSignature = signature; }
    if (state.view === 'spectrum') {
      const canvasLabel = document.getElementById('specCanvas');
      if (canvasLabel) canvasLabel.setAttribute('aria-label', translate(state.lang, 'specTitle'));
      void draw(state.spectrum.points).catch((error: unknown) => {
        console.error('[spectrum] No se pudo cargar Plotly o dibujar el espectro.', error);
        const sub = document.getElementById('specSub');
        if (sub) sub.textContent = state.lang === 'es' ? 'No se pudo cargar el espectro.' : 'The spectrum could not be loaded.';
      });
    }
  }

  document.getElementById('swColorEpoch')?.addEventListener('click', () => {
    store.setState({ spectrum: { ...store.getState().spectrum, colorEpoch: !store.getState().spectrum.colorEpoch } });
  });
  document.getElementById('swYlog')?.addEventListener('click', () => {
    store.setState({ spectrum: { ...store.getState().spectrum, logarithmic: !store.getState().spectrum.logarithmic } });
  });
  store.subscribe((_state, changed) => {
    if (changed.has('view')) mostrarVista();
    if (changed.has('view') && store.getState().view === 'spectrum') {
      if (!store.getState().spectrum.points.length) void actions.computeSpectrum();
      render();
    } else if (['spectrum', 'lang', 'collection', 'target'].some((key) => changed.has(key as keyof typeof _state))) render();
  });
  render();
}
