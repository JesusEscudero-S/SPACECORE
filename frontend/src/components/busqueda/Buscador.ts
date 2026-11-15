import { COLLECTIONS, DET, detector } from '../../config';
import { parseDec, parseRA } from '../../lib/coords';
import { applyI18n, translate } from '../../lib/i18n';
import { TARGETS, targetName } from '../../lib/objects';
import { showMessage, verifyElements } from '../../lib/dom';
import type { Store } from '../../state/store';
import type { ViewActions } from '../contracts';

export function mount(_root: ParentNode, store: Store, actions: ViewActions): void {
  if (!verifyElements(['searchForm', 'searchInput', 'queryForm', 'inRA', 'inDec', 'inFov', 'detBtns', 'inLam', 'inTol', 'inColl', 'chips', 'nav'], 'sidebar')) return;
  const searchForm = document.getElementById('searchForm');
  if (searchForm) searchForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const value = (document.getElementById('searchInput') as HTMLInputElement | null)?.value.trim();
    if (value) void actions.search(value);
  }); else showMessage('[UI] Falta #searchForm; la búsqueda no está disponible.', 'error');

  const queryForm = document.getElementById('queryForm');
  if (queryForm) queryForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const state = store.getState();
    const raInput = document.getElementById('inRA') as HTMLInputElement | null;
    const decInput = document.getElementById('inDec') as HTMLInputElement | null;
    const fovInput = document.getElementById('inFov') as HTMLInputElement | null;
    if (!raInput || !decInput || !fovInput) return showMessage('[UI] Falta un campo de coordenadas o FOV.', 'error');
    try {
      const ra = parseRA(raInput.value, 'auto');
      const dec = parseDec(decInput.value);
      const input = fovInput.value.trim();
      const fov = Number(input.replace(',', '.'));
      if (!Number.isFinite(fov) || fov < 1.5 || fov > 40) throw new RangeError('El campo de visión debe estar entre 1.5 y 40 arcmin.');
      actions.applyCoordinates({ ra, dec }, fov, input);
    } catch (error) { showMessage(error instanceof Error ? error.message : String(error), 'warn'); }
  }); else showMessage('[UI] Falta #queryForm; la consulta por coordenadas no está disponible.', 'error');

  const detectors = document.getElementById('detBtns');
  if (detectors) DET.forEach((entry) => {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'btn sm'; button.dataset.det = entry.id;
    button.textContent = entry.id; button.title = `${entry.min}–${entry.max} µm`;
    button.addEventListener('click', () => store.setState({ detector: entry.id, lambda: (entry.min + entry.max) / 2 }));
    detectors.append(button);
  });
  else showMessage('[UI] Falta #detBtns; no se pueden seleccionar detectores.', 'error');

  const tolerance = document.getElementById('inTol') as HTMLSelectElement | null;
  if (tolerance) {
    [['0.5', '± 0.5 canal'], ['1', '± 1 canal'], ['2', '± 2 canales'], ['inf', 'Cualquiera']].forEach(([value, label]) => {
      const option = document.createElement('option'); option.value = value; option.textContent = label; tolerance.append(option);
    });
    tolerance.addEventListener('change', () => {
      const value = tolerance.value;
      if (['0.5', '1', '2', 'inf'].includes(value)) store.setState({ tolerance: value as '0.5' | '1' | '2' | 'inf' });
    });
  }

  const collection = document.getElementById('inColl') as HTMLSelectElement | null;
  if (collection) {
    COLLECTIONS.forEach((name) => { const option = document.createElement('option'); option.value = name; option.textContent = name; collection.append(option); });
    collection.addEventListener('change', () => { store.setState({ collection: collection.value }); void actions.refresh(); });
  }

  const chips = document.getElementById('chips');
  if (chips) {
    TARGETS.forEach((target) => {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'chip'; button.textContent = targetName(target, store.getState().lang);
      button.setAttribute('aria-pressed', 'false'); button.addEventListener('click', () => actions.selectTarget(target));
      chips.append(button);
    });
  }

  const lambda = document.getElementById('inLam') as HTMLInputElement | null;
  lambda?.addEventListener('input', () => {
    const range = detector(store.getState().detector);
    const fraction = Number(lambda.value) / 1000;
    store.setState({ lambda: range.min + fraction * (range.max - range.min) });
  });
  document.getElementById('inFov')?.addEventListener('input', (event) => {
    store.setState({ fovInput: (event.currentTarget as HTMLInputElement).value });
  });
  document.getElementById('fovMinus')?.addEventListener('click', () => actions.changeFov(1 / 1.25));
  document.getElementById('fovPlus')?.addEventListener('click', () => actions.changeFov(1.25));
  document.getElementById('btnRefresh')?.addEventListener('click', () => { void actions.refresh(); });
  document.getElementById('btnLang')?.addEventListener('click', () => {
    const next = store.getState().lang === 'es' ? 'en' : 'es';
    store.setState({ lang: next }); applyI18n(next);
    render(next);
  });
  document.getElementById('nav')?.addEventListener('click', (event) => {
    const button = (event.target as HTMLElement).closest<HTMLButtonElement>('button[data-view]');
    if (button && ['explore', 'compare', 'spectrum'].includes(button.dataset.view ?? '')) actions.setView(button.dataset.view as 'explore' | 'compare' | 'spectrum');
  });
  document.getElementById('btnRail')?.addEventListener('click', () => document.getElementById('leftRail')?.classList.toggle('collapsed'));
  document.getElementById('btnInsp')?.addEventListener('click', () => document.getElementById('inspector')?.classList.toggle('collapsed'));

  function render(lang: 'es' | 'en'): void {
    const state = store.getState();
    const ra = document.getElementById('inRA') as HTMLInputElement | null;
    const dec = document.getElementById('inDec') as HTMLInputElement | null;
    const fov = document.getElementById('inFov') as HTMLInputElement | null;
    if (ra && document.activeElement !== ra) ra.value = state.center.ra.toFixed(5);
    if (dec && document.activeElement !== dec) dec.value = state.center.dec.toFixed(5);
    if (fov && document.activeElement !== fov) fov.value = state.fovInput;
    const lambdaSlider = document.getElementById('inLam') as HTMLInputElement | null;
    if (lambdaSlider) {
      const range = detector(state.detector);
      lambdaSlider.value = String(Math.round(1000 * (state.lambda - range.min) / (range.max - range.min)));
    }
    const lamLabel = document.getElementById('lamVal'); if (lamLabel) lamLabel.textContent = `${state.lambda.toFixed(2)} µm`;
    const detLabel = document.getElementById('detHint'); if (detLabel) detLabel.textContent = `${state.lambda.toFixed(2)} µm`;
    const fovLabel = document.getElementById('fovHint'); if (fovLabel) fovLabel.textContent = `${(state.fovArcmin / 60).toFixed(3)}°`;
    if (tolerance) {
      tolerance.value = state.tolerance;
      const labels = lang === 'es' ? ['± 0.5 canal', '± 1 canal', '± 2 canales', 'Cualquiera'] : ['± 0.5 channel', '± 1 channel', '± 2 channels', 'Any'];
      [...tolerance.options].forEach((option, index) => { option.textContent = labels[index] ?? option.textContent; });
    }
    if (collection) collection.value = state.collection;
    detectors?.querySelectorAll<HTMLButtonElement>('button[data-det]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.det === state.detector)));
    chips?.querySelectorAll<HTMLButtonElement>('.chip').forEach((button, index) => {
      button.textContent = targetName(TARGETS[index], lang);
      button.setAttribute('aria-pressed', String(TARGETS[index].key === state.target?.key));
    });
    document.querySelectorAll<HTMLButtonElement>('#nav button[data-view]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.view === state.view)));
  }

  store.subscribe((_state, changed) => {
    if (['center', 'fovArcmin', 'fovInput', 'detector', 'tolerance', 'lambda', 'collection', 'lang', 'target', 'view'].some((key) => changed.has(key as keyof typeof _state))) render(store.getState().lang);
  });
  render(store.getState().lang);
}
