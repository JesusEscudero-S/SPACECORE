import type { Store } from '../../state/store';
import type { ViewActions } from '../contracts';
import { verifyElements } from '../../lib/dom';

export function mount(_root: ParentNode, store: Store, actions: ViewActions): void {
  if (!verifyElements(['bPlay', 'bPrev', 'bNext', 'inSpeed', 'timeline', 'counter', 'frameChip'], 'dock')) return;
  document.getElementById('bPlay')?.addEventListener('click', actions.togglePlayback);
  document.getElementById('bPrev')?.addEventListener('click', () => actions.step(-1));
  document.getElementById('bNext')?.addEventListener('click', () => actions.step(1));
  const speed = document.getElementById('inSpeed') as HTMLSelectElement | null;
  speed?.addEventListener('change', () => {
    const value = Number(speed.value);
    if ([0.5, 1, 2, 4].includes(value)) store.setState({ speed: value });
  });

  let timer: number | undefined;
  const tick = (): void => actions.step(1);
  function update(): void {
    const state = store.getState();
    const play = document.getElementById('bPlay');
    if (play) play.textContent = state.playing ? (state.lang === 'es' ? 'Pausar' : 'Pause') : (state.lang === 'es' ? 'Reproducir' : 'Play');
    if (speed) speed.value = String(state.speed);
    const timeline = document.getElementById('timeline');
    if (timeline) {
      timeline.replaceChildren();
      if (state.observations.length) {
        const axis = document.createElement('div'); axis.className = 'axis'; timeline.append(axis);
        state.observations.forEach((observation, index) => {
          const button = document.createElement('button'); button.type = 'button'; button.className = 'tick';
          button.style.left = `${state.observations.length === 1 ? 50 : 4 + index * 92 / (state.observations.length - 1)}%`;
          button.title = `${observation.date} · ${observation.lambda_um.toFixed(2)} µm`;
          button.setAttribute('aria-current', String(observation.id === state.observations[state.currentIndex]?.id));
          button.addEventListener('click', () => { void actions.chooseObservation(observation); });
          timeline.append(button);
          if (index === 0 || index === state.observations.length - 1) {
            const label = document.createElement('span'); label.className = 'tl-lab'; label.style.left = button.style.left;
            label.textContent = observation.date.slice(0, 4); timeline.append(label);
          }
        });
      }
    }
    const current = state.observations[state.currentIndex];
    const counter = document.getElementById('counter');
    if (counter) counter.textContent = current ? `${state.currentIndex + 1} / ${state.observations.length}` : (state.lang === 'es' ? 'Sin cuadros' : 'No frames');
    const chip = document.getElementById('frameChip');
    if (chip) chip.textContent = current ? `${current.date} · ${current.detector} · ${current.lambda_um.toFixed(2)} µm` : '';
    if (state.playing && timer === undefined) timer = window.setInterval(tick, (state.view === 'compare' ? 700 : 1100) / state.speed);
    if ((!state.playing || !state.observations.length) && timer !== undefined) { window.clearInterval(timer); timer = undefined; }
    if (state.playing && timer !== undefined) {
      window.clearInterval(timer);
      timer = window.setInterval(tick, (state.view === 'compare' ? 700 : 1100) / state.speed);
    }
  }
  store.subscribe((_state, changed) => {
    if (['observations', 'currentIndex', 'playing', 'speed', 'view', 'lang', 'frame'].some((key) => changed.has(key as keyof typeof _state))) update();
  });
  update();
}
