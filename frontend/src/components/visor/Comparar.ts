import type { CompareMode } from '../../api/source';
import type { Store } from '../../state/store';
import { verifyElements } from '../../lib/dom';
import type { ViewActions } from '../contracts';

export function mount(_root: ParentNode, store: Store, _actions: ViewActions): void {
  if (!verifyElements(['cmpModes', 'cmpBar', 'selA', 'selB', 'skyWrap', 'sliderLine', 'sliderHandle'], 'compare')) return;
  const modes = document.getElementById('cmpModes');
  modes?.addEventListener('click', (event) => {
    const button = (event.target as HTMLElement).closest<HTMLButtonElement>('button[data-mode]');
    const mode = button?.dataset.mode;
    if (mode && ['blink', 'slider', 'diff', 'sum'].includes(mode)) store.setState({ mode: mode as CompareMode });
  });

  const selectA = document.getElementById('selA') as HTMLSelectElement | null;
  const selectB = document.getElementById('selB') as HTMLSelectElement | null;
  selectA?.addEventListener('change', () => store.setState({ epochA: selectA.value }));
  selectB?.addEventListener('change', () => store.setState({ epochB: selectB.value }));

  const wrap = document.getElementById('skyWrap');
  const slider = document.getElementById('sliderLine');
  let dragging = false;
  const setSlider = (event: PointerEvent): void => {
    if (!wrap || !dragging) return;
    const bounds = wrap.getBoundingClientRect();
    const value = Math.max(0.02, Math.min(0.98, (event.clientX - bounds.left) / bounds.width));
    store.setState({ slider: value });
  };
  document.getElementById('sliderHandle')?.addEventListener('pointerdown', (event) => {
    dragging = true;
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    setSlider(event);
  });
  document.getElementById('sliderHandle')?.addEventListener('pointermove', setSlider);
  document.getElementById('sliderHandle')?.addEventListener('pointerup', () => { dragging = false; });
  document.getElementById('sliderHandle')?.addEventListener('lostpointercapture', () => { dragging = false; });

  const update = (): void => {
    const state = store.getState();
    const bar = document.getElementById('cmpBar');
    if (bar) bar.hidden = state.view !== 'compare';
    if (modes) modes.hidden = state.view !== 'compare';
    document.querySelectorAll<HTMLButtonElement>('#cmpModes button[data-mode]').forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.mode === state.mode));
    });
    if (slider) {
      slider.hidden = state.view !== 'compare' || state.mode !== 'slider';
      slider.style.left = `${state.slider * 100}%`;
    }
    const observations = state.observations;
    for (const [select, selected] of [[selectA, state.epochA], [selectB, state.epochB]] as const) {
      if (!select) continue;
      const current = selected || observations.at(-1)?.id || '';
      if (select.options.length !== observations.length) {
        select.replaceChildren(...observations.map((observation) => {
          const option = document.createElement('option'); option.value = observation.id;
          option.textContent = `${observation.date} · ${observation.detector} · ${observation.lambda_um.toFixed(2)} µm`;
          return option;
        }));
      }
      if ([...select.options].some((option) => option.value === current)) select.value = current;
    }
  };
  store.subscribe((_state, changed) => {
    if (['view', 'mode', 'slider', 'observations', 'epochA', 'epochB', 'detector', 'lambda', 'tolerance'].some((key) => changed.has(key as keyof typeof _state))) update();
  });
  update();
}
