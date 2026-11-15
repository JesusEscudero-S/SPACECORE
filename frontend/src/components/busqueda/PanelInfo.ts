import { posicionEspectro } from '../../lib/coords';
import { EXPLANATORY_SUPPLEMENT, PIX_ARCSEC } from '../../config';
import { setSwitch, verifyElements } from '../../lib/dom';
import { translate } from '../../lib/i18n';
import type { DisplaySettings, Store } from '../../state/store';
import type { ViewActions } from '../contracts';

export function mount(_root: ParentNode, store: Store, _actions: ViewActions): void {
  if (!verifyElements(['inStretch', 'segRender', 'swCommon', 'swCommon2', 'swSubBg', 'swSubBg2', 'swMarker', 'swMask', 'flagList', 'inspExplore', 'inspCompare', 'inspSpec', 'gaiaNotice'], 'inspector')) return;
  type DisplayToggle = Exclude<keyof DisplaySettings, 'stretch'>;
  const setDisplay = (patch: Partial<DisplaySettings>): void => {
    store.setState({ display: { ...store.getState().display, ...patch } });
  };
  const switches: [string, DisplayToggle][] = [
    ['swCommon', 'commonScale'], ['swCommon2', 'commonScale'],
    ['swSubBg', 'subtractBackground'], ['swSubBg2', 'subtractBackground'],
    ['swMarker', 'marker'], ['swMask', 'showMask'],
  ];
  switches.forEach(([id, key]) => document.getElementById(id)?.addEventListener('click', () => {
    const value = !store.getState().display[key];
    setDisplay({ [key]: value });
    switches.filter(([, linkedKey]) => linkedKey === key).forEach(([linkedId]) => setSwitch(linkedId, value));
  }));
  const stretch = document.getElementById('inStretch') as HTMLSelectElement | null;
  stretch?.addEventListener('change', () => {
    if (['linear', 'asinh', 'log'].includes(stretch.value)) setDisplay({ stretch: stretch.value as 'linear' | 'asinh' | 'log' });
  });
  document.getElementById('segRender')?.addEventListener('click', (event) => {
    const button = (event.target as HTMLElement).closest<HTMLButtonElement>('button[data-v]');
    if (button) setDisplay({ smooth: button.dataset.v === 'smooth' });
  });
  document.getElementById('swSpBg')?.addEventListener('click', () => {
    const next = !store.getState().spectrum.subtractBackground;
    store.setState({ spectrum: { ...store.getState().spectrum, subtractBackground: next } });
  });
  document.getElementById('swSpErr')?.addEventListener('click', () => {
    const next = !store.getState().spectrum.showError;
    store.setState({ spectrum: { ...store.getState().spectrum, showError: next } });
  });
  document.getElementById('swSpMask')?.addEventListener('click', () => {
    const next = !store.getState().spectrum.excludeMask;
    store.setState({ spectrum: { ...store.getState().spectrum, excludeMask: next } });
  });
  document.getElementById('inAp')?.addEventListener('change', (event) => {
    const aperture = Number((event.currentTarget as HTMLSelectElement).value);
    store.setState({ spectrum: { ...store.getState().spectrum, aperture } });
  });
  document.getElementById('inAnn')?.addEventListener('change', (event) => {
    const [annulusInner, annulusOuter] = (event.currentTarget as HTMLSelectElement).value.split('-').map(Number);
    store.setState({ spectrum: { ...store.getState().spectrum, annulusInner, annulusOuter } });
  });
  document.getElementById('btnRecalc')?.addEventListener('click', () => {
    window.dispatchEvent(new CustomEvent('spherex:compute-spectrum'));
  });
  const flagLink = document.getElementById('supLink') as HTMLAnchorElement | null;
  if (flagLink) flagLink.href = EXPLANATORY_SUPPLEMENT;

  function render(): void {
    const state = store.getState();
    for (const [id, key] of switches) setSwitch(id, state.display[key]);
    setSwitch('swSpBg', state.spectrum.subtractBackground);
    setSwitch('swSpErr', state.spectrum.showError);
    setSwitch('swSpMask', state.spectrum.excludeMask);
    if (stretch) stretch.value = state.display.stretch;
    document.querySelectorAll<HTMLButtonElement>('#segRender button[data-v]').forEach((button) => {
      button.setAttribute('aria-pressed', String((button.dataset.v === 'smooth') === state.display.smooth));
    });
    const explore = document.getElementById('inspExplore'); if (explore) explore.hidden = state.view !== 'explore';
    const compare = document.getElementById('inspCompare'); if (compare) compare.hidden = state.view !== 'compare';
    const spectrum = document.getElementById('inspSpec'); if (spectrum) spectrum.hidden = state.view !== 'spectrum';
    const flags = document.getElementById('flagList');
    if (flags) {
      flags.replaceChildren();
      const entries = Object.entries(state.frame?.flags ?? {}).filter(([key]) => !key.startsWith('__'));
      if (!entries.length) {
        const dt = document.createElement('dt'), dd = document.createElement('dd');
        dt.textContent = translate(state.lang, 'quality');
        dd.textContent = state.frame ? translate(state.lang, 'noFlags') : '—';
        flags.append(dt, dd);
      } else entries.forEach(([name, count]) => {
        const dt = document.createElement('dt'), dd = document.createElement('dd');
        dt.textContent = name; dd.textContent = count.toLocaleString(); flags.append(dt, dd);
      });
    }
    const title = document.getElementById('title');
    if (title) title.textContent = state.target?.name[state.lang] ?? `${state.center.ra.toFixed(4)}°, ${state.center.dec.toFixed(4)}°`;
    const subtitle = document.getElementById('subtitle');
    if (subtitle) subtitle.textContent = `${state.center.ra.toFixed(5)}° · ${state.center.dec >= 0 ? '+' : ''}${state.center.dec.toFixed(5)}° · ${state.fovArcmin.toFixed(1)}′`;
    const modeMessage = document.getElementById('statusDemo');
    if (modeMessage) modeMessage.textContent = state.api ? 'API · datos del backend' : translate(state.lang, 'demoBadge');
    const provenance = document.getElementById('statusColl'); if (provenance) provenance.textContent = state.collection;
    const note = document.getElementById('alignNote');
    if (note) note.textContent = state.api ? translate(state.lang, 'aligned') : translate(state.lang, 'alignedDemo');
    const banner = document.getElementById('banner');
    if (state.error && banner) {
      const text = document.getElementById('bannerText'); if (text) text.textContent = state.error;
      banner.className = 'banner err'; banner.hidden = false;
    }
    const centerNote = document.getElementById('centerNote');
    if (centerNote) centerNote.textContent = state.target && state.target.pmra !== 0 && !state.api
      ? (state.lang === 'es' ? 'Coordenadas y movimiento propio aproximados en la demo.' : 'Approximate coordinates and proper motion in demo mode.')
      : '';
    const scaleNote = document.getElementById('scaleNote');
    if (scaleNote) scaleNote.textContent = `N ↑ · E ← · ${state.api ? 'SPHEREx · ' : 'DEMO · '}${PIX_ARCSEC}″/px`;
    const specPosition = document.getElementById('specPos');
    if (specPosition) {
      // La posición donde de verdad se calcula el espectro (ver posicionEspectro en lib/coords.ts).
      const posicion = posicionEspectro(state.center, state.selectedSource);
      const elegido = posicion !== state.center;
      specPosition.textContent = `${posicion.ra.toFixed(5)}°, ${posicion.dec.toFixed(5)}°`
        + (elegido ? (state.lang === 'es' ? ' · punto elegido con clic (no es el objetivo)' : ' · clicked point (not the target)') : '');
    }
    const cutFov = document.getElementById('cutFov'); if (cutFov) cutFov.textContent = `${state.spectrum.aperture}″`;
  }
  store.subscribe((_state, changed) => {
    if (['display', 'spectrum', 'view', 'frame', 'target', 'center', 'selectedSource', 'fovArcmin', 'api', 'collection', 'lang', 'error'].some((key) => changed.has(key as keyof typeof _state))) render();
  });
  render();
}
