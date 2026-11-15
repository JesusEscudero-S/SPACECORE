import type { Observation, SkyPosition, Target, ViewName } from '../api/source';

export interface ViewActions {
  search(query: string): Promise<void>;
  selectTarget(target: Target): void;
  applyCoordinates(position: SkyPosition, fovArcmin: number, originalFov: string): void;
  changeFov(deltaFactor: number): void;
  refresh(): Promise<void>;
  setView(view: ViewName): void;
  chooseObservation(observation: Observation): Promise<void>;
  step(delta: number): void;
  togglePlayback(): void;
  computeSpectrum(): Promise<void>;
  share(kind: 'link' | 'embed'): void;
  export(kind: 'png' | 'csv'): void;
}
