export type DetectorId = 'D1' | 'D2' | 'D3' | 'D4' | 'D5' | 'D6';
export type ViewName = 'explore' | 'compare' | 'spectrum';
export type CompareMode = 'blink' | 'slider' | 'diff' | 'sum';
export type Lang = 'es' | 'en';

export interface DetectorRange { id: DetectorId; min: number; max: number }
export interface SkyPosition { ra: number; dec: number }
export interface Target extends SkyPosition {
  key: string;
  name: Record<Lang, string>;
  short: string;
  pmra: number;
  pmdec: number;
  aliases: string[];
  detector?: DetectorId;
  sed?: { lambda: number; flux: number; temperature: number };
  variability?: { kind: 'mira' | 'tts'; period?: number; amplitude?: number };
  note?: Record<Lang, string>;
}
export interface Observation {
  id: string;
  date: string;
  mjd: number;
  detector: DetectorId;
  lambda_um: number;
  flags: Record<string, number>;
  target?: Target;
}
export interface Frame {
  nx: number;
  ny: number;
  data: Float32Array;
  mask: Uint8Array;
  flags: Record<string, number>;
  median: number;
  center: SkyPosition;
  observation: Observation;
}
export interface SpectrumPoint {
  obs_id: string;
  date: string;
  mjd: number;
  detector: DetectorId;
  lambda_um: number;
  flux_mjy: number;
  err_mjy: number;
  nbad: number;
}
export interface PhotometryOptions {
  ap: number;
  annIn: number;
  annOut: number;
  subBg: boolean;
  exclMask: boolean;
}
export interface FrameSource {
  readonly isDemo: boolean;
  resolve(query: string): Promise<Target | null>;
  epocas(center: SkyPosition, fovArcmin: number, collection: string, target: Target | null): Promise<Observation[]>;
  frame(observation: Observation, center: SkyPosition, nx: number, ny: number, collection: string): Promise<Frame>;
  spectrum(center: SkyPosition, collection: string, options: PhotometryOptions, target: Target | null): Promise<SpectrumPoint[]>;
}
