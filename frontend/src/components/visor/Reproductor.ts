import { PIX_ARCSEC } from '../../config';
import { propagarProperMotion } from '../../lib/coords';
import { frameCanvas, differenceCanvas } from '../../lib/render/pixels';
import { composeFrames } from '../../lib/render/composition';
import { commonScale } from '../../lib/render/stretch';
import { verifyElements } from '../../lib/dom';
import type { Frame } from '../../api/source';
import type { Store } from '../../state/store';
import type { ViewActions } from '../contracts';

const D2R = Math.PI / 180;

export function mount(_root: ParentNode, store: Store, actions: ViewActions): void {
  if (!verifyElements(['skyCanvas', 'skyWrap', 'tZoomIn', 'tZoomOut', 'tCenter', 'tGrid', 'tFull', 'caption'], 'skyCanvas')) return;
  const canvas = document.getElementById('skyCanvas') as HTMLCanvasElement | null;
  const wrap = document.getElementById('skyWrap');
  if (!canvas || !wrap) {
    const message = '[skyCanvas] Falta #skyCanvas o #skyWrap; no se puede mostrar el cuadro.';
    console.error(message);
    const banner = document.getElementById('bannerText'); if (banner) banner.textContent = message;
    return;
  }
  const skyCanvas = canvas;
  const skyWrap = wrap;
  let isDragging = false;
  let dragStart = { x: 0, y: 0, center: { ra: 0, dec: 0 } };
  let blinkB = false;

  document.getElementById('tZoomIn')?.addEventListener('click', () => actions.changeFov(1 / 1.25));
  document.getElementById('tZoomOut')?.addEventListener('click', () => actions.changeFov(1.25));
  document.getElementById('tCenter')?.addEventListener('click', () => {
    const state = store.getState();
    if (state.target) actions.selectTarget(state.target);
    else actions.applyCoordinates(state.center, state.fovArcmin, state.fovInput);
  });
  document.getElementById('tGrid')?.addEventListener('click', () => {
    const next = !store.getState().display.grid;
    store.setState({ display: { ...store.getState().display, grid: next } });
    document.getElementById('tGrid')?.setAttribute('aria-pressed', String(next));
  });
  document.getElementById('tFull')?.addEventListener('click', () => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else if (skyWrap.requestFullscreen) void skyWrap.requestFullscreen();
  });

  skyCanvas.addEventListener('pointerdown', (event) => {
    if (event.button !== 0) return;
    const state = store.getState();
    isDragging = true;
    dragStart = { x: event.clientX, y: event.clientY, center: { ...state.center } };
    skyCanvas.setPointerCapture(event.pointerId);
  });
  skyCanvas.addEventListener('pointermove', (event) => {
    const point = screenPosition(event.clientX, event.clientY);
    const readout = document.getElementById('cursorReadout');
    if (point && readout) readout.textContent = `α ${point.ra.toFixed(4)}° · δ ${point.dec.toFixed(4)}°`;
  });
  skyCanvas.addEventListener('pointerup', (event) => {
    if (!isDragging) return;
    isDragging = false;
    const dx = event.clientX - dragStart.x, dy = event.clientY - dragStart.y;
    const rect = skyCanvas.getBoundingClientRect();
    if (Math.hypot(dx, dy) > 8) {
      const arcsecPerPixel = store.getState().fovArcmin * 60 / Math.min(rect.width, rect.height);
      const cosDec = Math.max(0.02, Math.cos(dragStart.center.dec * D2R));
      const center = {
        ra: (dragStart.center.ra + (dx * arcsecPerPixel / 3600) / cosDec + 360) % 360,
        dec: Math.max(-90, Math.min(90, dragStart.center.dec + dy * arcsecPerPixel / 3600)),
      };
      store.setState({ center, selectedSource: null });
      void actions.refresh();
    } else {
      const position = screenPosition(event.clientX, event.clientY);
      if (position) store.setState({ selectedSource: position });
    }
  });
  skyCanvas.addEventListener('pointercancel', () => { isDragging = false; });

  function screenPosition(clientX: number, clientY: number): { ra: number; dec: number } | null {
    const state = store.getState(), bounds = skyCanvas.getBoundingClientRect();
    const scale = Math.min(bounds.width / 100, bounds.height / 100);
    if (!scale) return null;
    const fovDegrees = state.fovArcmin / 60;
    const x = (clientX - bounds.left - bounds.width / 2) / scale;
    const y = (clientY - bounds.top - bounds.height / 2) / scale;
    return {
      ra: (state.center.ra - x * fovDegrees / 100 / Math.max(0.02, Math.cos(state.center.dec * D2R)) + 360) % 360,
      dec: Math.max(-90, Math.min(90, state.center.dec + y * fovDegrees / 100)),
    };
  }

  function activeFrame(): Frame | null {
    const state = store.getState();
    if (state.view !== 'compare' || !state.frameA || !state.frameB) return state.frame;
    if (state.mode === 'blink') return blinkB ? state.frameB : state.frameA;
    if (state.mode === 'diff') return { ...state.frameA, data: composeFrames(state.frameA, state.frameB, 'diff'), median: 0 };
    if (state.mode === 'sum') return { ...state.frameA, data: composeFrames(state.frameA, state.frameB, 'sum'), median: 0 };
    return state.frameA;
  }

  function render(): void {
    const state = store.getState(), bounds = skyWrap.getBoundingClientRect();
    const width = bounds.width, height = bounds.height, dpr = window.devicePixelRatio || 1;
    if (!width || !height) return;
    if (skyCanvas.width !== Math.round(width * dpr) || skyCanvas.height !== Math.round(height * dpr)) {
      skyCanvas.width = Math.round(width * dpr); skyCanvas.height = Math.round(height * dpr);
    }
    const context = skyCanvas.getContext('2d');
    if (!context) return;
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.fillStyle = '#050709'; context.fillRect(0, 0, width, height);
    const stateFrame = activeFrame();
    if (state.view === 'compare' && state.mode === 'slider' && state.frameA && state.frameB) {
      const scale = state.display.commonScale ? commonScale([state.frameA, state.frameB], state.display.subtractBackground) : undefined;
      const left = frameCanvas(state.frameA, state.display, scale), right = frameCanvas(state.frameB, state.display, scale);
      const imageWidth = Math.min(width, height) * 0.88, x = (width - imageWidth) / 2, y = (height - imageWidth) / 2;
      context.imageSmoothingEnabled = state.display.smooth;
      context.drawImage(left, x, y, imageWidth, imageWidth);
      context.save(); context.beginPath(); context.rect(x + imageWidth * state.slider, y, imageWidth * (1 - state.slider), imageWidth); context.clip();
      context.drawImage(right, x, y, imageWidth, imageWidth); context.restore();
    } else if (stateFrame) {
      const rendered = state.view === 'compare' && state.mode === 'diff' && state.frameA && state.frameB
        ? differenceCanvas(state.frameA, state.frameB, state.display)
        : frameCanvas(stateFrame, state.display, state.display.commonScale && state.frameA && state.frameB ? commonScale([state.frameA, state.frameB], state.display.subtractBackground) : undefined);
      const imageWidth = Math.min(width, height) * 0.88, x = (width - imageWidth) / 2, y = (height - imageWidth) / 2;
      context.imageSmoothingEnabled = state.display.smooth;
      context.drawImage(rendered, x, y, imageWidth, imageWidth);
    } else {
      context.fillStyle = '#b4bcc8'; context.font = '13px Inter, sans-serif'; context.textAlign = 'center';
      context.fillText(state.loading ? (state.lang === 'es' ? (state.api ? 'Cargando imágenes de SPHEREx… (la primera vez ~1 min)' : 'Cargando cuadros…') : (state.api ? 'Loading SPHEREx images… (first time ~1 min)' : 'Loading frames…')) : (state.lang === 'es' ? 'Sin cuadros para mostrar' : 'No frames available'), width / 2, height / 2);
    }
    if (state.display.grid) drawGrid(context, width, height);
    if (state.display.marker && state.target) drawExpected(context, state.target, state.center, state.fovArcmin, width, height, state.frame?.observation.mjd);
    drawCompass(context, width, height);
    drawScale(context, width, height, state.fovArcmin);
    const caption = document.getElementById('caption');
    if (caption) caption.textContent = state.view === 'compare'
      ? state.mode === 'diff' ? 'B − A · cian: más tenue · rojo: más brillante' : state.mode === 'sum' ? 'Promedio de las dos épocas seleccionadas' : state.mode === 'slider' ? 'Arrastra la línea para comparar épocas A y B.' : 'Alterna entre las épocas A y B.'
      : state.target?.note ? `${state.target.note[state.lang]}${state.api ? '' : state.lang === 'es' ? ' (variabilidad simulada en la demo)' : ' (variability simulated in the demo)'}` : (state.api ? 'Datos proporcionados por el backend.' : state.lang === 'es' ? 'Imagen y variabilidad simuladas; no son mediciones SPHEREx.' : 'Simulated image and variability; not SPHEREx measurements.');
    const selected = document.getElementById('popCoords');
    if (selected && state.selectedSource) selected.textContent = `${state.selectedSource.ra.toFixed(5)}°, ${state.selectedSource.dec.toFixed(5)}°`;
  }

  function drawGrid(context: CanvasRenderingContext2D, width: number, height: number): void {
    context.save(); context.strokeStyle = 'rgba(153,220,229,.23)'; context.lineWidth = 1;
    context.setLineDash([4, 5]);
    for (const fraction of [0.25, 0.5, 0.75]) {
      context.beginPath(); context.moveTo(width * fraction, height * 0.08); context.lineTo(width * fraction, height * 0.92); context.stroke();
      context.beginPath(); context.moveTo(width * 0.08, height * fraction); context.lineTo(width * 0.92, height * fraction); context.stroke();
    }
    context.restore();
  }
  function drawExpected(context: CanvasRenderingContext2D, target: NonNullable<ReturnType<Store['getState']>['target']>, center: { ra: number; dec: number }, fov: number, width: number, height: number, mjd?: number): void {
    const epoch = mjd ? 2000 + (mjd - 51544.5) / 365.25 : 2026.8;
    const expected = propagarProperMotion({ ra: target.ra, dec: target.dec, pmRA: target.pmra, pmDec: target.pmdec }, epoch);
    const cosDec = Math.max(0.02, Math.cos(center.dec * D2R));
    const x = width / 2 - ((expected.ra - center.ra + 540) % 360 - 180) * cosDec * 60 / fov * Math.min(width, height);
    const y = height / 2 - (expected.dec - center.dec) * 60 / fov * Math.min(width, height);
    context.save(); context.strokeStyle = '#99dce5'; context.lineWidth = 1.5; context.beginPath(); context.arc(x, y, 8, 0, Math.PI * 2); context.stroke();
    context.beginPath(); context.moveTo(x - 12, y); context.lineTo(x + 12, y); context.moveTo(x, y - 12); context.lineTo(x, y + 12); context.stroke(); context.restore();
  }
  function drawCompass(context: CanvasRenderingContext2D, width: number, height: number): void {
    context.save(); context.fillStyle = '#b4bcc8'; context.font = '11px JetBrains Mono, monospace';
    context.fillText('N ↑', width - 42, 23); context.fillText('E ←', width - 42, 39); context.restore();
  }
  function drawScale(context: CanvasRenderingContext2D, width: number, height: number, fov: number): void {
    const length = Math.min(width * 0.18, height * 0.18);
    context.save(); context.strokeStyle = '#dce7ef'; context.fillStyle = '#dce7ef'; context.lineWidth = 2;
    context.beginPath(); context.moveTo(18, height - 25); context.lineTo(18 + length, height - 25); context.stroke();
    context.font = '10px JetBrains Mono, monospace'; context.textAlign = 'left'; context.fillText(`${(fov * length / Math.min(width, height)).toFixed(1)}′`, 18, height - 31); context.restore();
  }

  const resizeObserver = new ResizeObserver(render);
  resizeObserver.observe(skyWrap);
  store.subscribe((_state, changed) => {
    if (changed.has('currentIndex') && store.getState().view === 'compare' && store.getState().mode === 'blink') blinkB = !blinkB;
    if (['frame', 'frameA', 'frameB', 'center', 'fovArcmin', 'view', 'mode', 'slider', 'display', 'target', 'currentIndex', 'loading', 'lang', 'selectedSource'].some((key) => changed.has(key as keyof typeof _state))) render();
  });
  render();
}
