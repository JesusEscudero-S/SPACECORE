import type { CompareMode, Frame, Lang, Observation, SkyPosition, SpectrumPoint, Target, ViewName } from '../api/source';

export interface DisplaySettings {
  stretch: 'linear' | 'asinh' | 'log';
  smooth: boolean;
  commonScale: boolean;
  subtractBackground: boolean;
  grid: boolean;
  marker: boolean;
  showMask: boolean;
}
export interface SpectrumSettings {
  aperture: number;
  annulusInner: number;
  annulusOuter: number;
  subtractBackground: boolean;
  showError: boolean;
  excludeMask: boolean;
  colorEpoch: boolean;
  logarithmic: boolean;
  points: SpectrumPoint[];
}
export interface AppState {
  api: string | null;
  lang: Lang;
  view: ViewName;
  collection: string;
  fovArcmin: number;
  fovInput: string;
  detector: 'D1' | 'D2' | 'D3' | 'D4' | 'D5' | 'D6';
  tolerance: '0.5' | '1' | '2' | 'inf';
  mode: CompareMode;
  epochA: string;
  epochB: string;
  lambda: number;
  playing: boolean;
  speed: number;
  embed: boolean;
  query: string;
  center: SkyPosition;
  target: Target | null;
  observations: Observation[];
  currentIndex: number;
  frame: Frame | null;
  frameA: Frame | null;
  frameB: Frame | null;
  slider: number;
  loading: boolean;
  error: string;
  display: DisplaySettings;
  spectrum: SpectrumSettings;
  selectedSource: SkyPosition | null;
  gaiaEnabled: boolean;
}

export type StatePatch = Partial<AppState>;
export type StateListener = (state: Readonly<AppState>, changed: ReadonlySet<keyof AppState>) => void;

export interface Store {
  getState(): Readonly<AppState>;
  setState(patch: StatePatch): void;
  subscribe(listener: StateListener): () => void;
}

export function createStore(initial: AppState): Store {
  let state = initial;
  const listeners = new Set<StateListener>();
  return {
    getState: () => state,
    setState(patch) {
      const changed = new Set(Object.keys(patch) as (keyof AppState)[]);
      if (!changed.size) return;
      state = { ...state, ...patch };
      listeners.forEach((listener) => listener(state, changed));
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}
