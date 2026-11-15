import type { Frame } from '../../api/source';

export interface StretchScale { center: number; sigma: number; high: number }
export type StretchKind = 'linear' | 'asinh' | 'log';

function quantile(sorted: number[], fraction: number): number {
  if (!sorted.length) return 1;
  return sorted[Math.max(0, Math.min(sorted.length - 1, Math.round(fraction * (sorted.length - 1))))];
}

export function commonScale(frames: Frame[], subtractBackground: boolean): StretchScale {
  const sample: number[] = [];
  for (const frame of frames) {
    const step = Math.max(1, Math.floor(frame.data.length / 12_000));
    for (let i = 0; i < frame.data.length; i += step) {
      if (!frame.mask[i] && Number.isFinite(frame.data[i])) sample.push(frame.data[i] - (subtractBackground ? frame.median : 0));
    }
  }
  sample.sort((a, b) => a - b);
  const center = quantile(sample, 0.5);
  const deviations = sample.map((value) => Math.abs(value - center)).sort((a, b) => a - b);
  const sigma = Math.max(quantile(deviations, 0.5) * 1.4826, 1e-6);
  return { center: subtractBackground ? 0 : center, sigma, high: Math.max(8, Math.min(250, quantile(sample, 0.9995) / sigma)) };
}

export function stretchValue(value: number, scale: StretchScale, kind: StretchKind): number {
  const normalized = (value - scale.center) / scale.sigma;
  if (kind === 'linear') return (normalized + 2) / Math.max(17, scale.high * 0.1 + 2);
  if (kind === 'log') return Math.log1p(Math.max(0, normalized + 2)) / Math.log1p(scale.high + 2);
  const lower = Math.asinh(-2 / 3), upper = Math.asinh(scale.high / 3);
  return (Math.asinh(normalized / 3) - lower) / (upper - lower);
}
