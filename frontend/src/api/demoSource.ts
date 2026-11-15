import { DET, PIX_ARCSEC, channelWidth } from '../config';
import { propagarProperMotion } from '../lib/coords';
import { localResolve } from '../lib/objects';
import { aperturePhotometry } from '../lib/render/photometry';
import type { Frame, FrameSource, Observation, PhotometryOptions, SkyPosition, SpectrumPoint, Target } from './source';

const D2R = Math.PI / 180;
const C2 = 14388;
const PIXEL_SR = (PIX_ARCSEC / 206265) ** 2;
const MJY_SR_TO_MJY = PIXEL_SR * 1e9;
const PSF_SIGMA = 0.95;
const NOISE = 0.12;
const DATES = ['2025-06-08', '2025-08-20', '2025-12-05', '2026-02-12', '2026-05-30', '2026-08-14', '2026-10-30'];

function mjdOf(date: string): number { return Date.UTC(+date.slice(0, 4), +date.slice(5, 7) - 1, +date.slice(8, 10)) / 86400000 + 40587; }
function dateOfMjd(mjd: number): string { return new Date((mjd - 40587) * 86400000).toISOString().slice(0, 10); }
function hash32(text: string): number {
  let hash = 2166136261 >>> 0;
  for (let i = 0; i < text.length; i++) { hash ^= text.charCodeAt(i); hash = Math.imul(hash, 16777619); }
  return hash >>> 0;
}
function random(seed: number): () => number {
  let value = seed >>> 0;
  return () => {
    value = (value + 0x6d2b79f5) >>> 0;
    let t = value;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function gaussian(rng: () => number): number {
  let u = 0;
  while (u === 0) u = rng();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rng());
}
function median(values: number[]): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = sorted.length >> 1;
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}
function planckRatio(lambda: number, reference: number, temperature: number): number {
  const a = C2 / (reference * temperature);
  const b = C2 / (lambda * temperature);
  const ratio = (reference / lambda) ** 3 * (Math.expm1(a) / Math.expm1(b));
  return Number.isFinite(ratio) ? ratio : 0;
}
function targetFlux(target: Target, lambda: number, mjd: number): number {
  const sed = target.sed ?? { lambda: 2.2, flux: 100, temperature: 3000 };
  let variability = 1;
  if (target.variability?.kind === 'mira') {
    const period = target.variability.period ?? 245;
    const amplitude = target.variability.amplitude ?? 0.7;
    variability = 10 ** (-0.4 * amplitude * Math.sin(2 * Math.PI * (mjd - 51544) / period));
  } else if (target.variability?.kind === 'tts') {
    variability = 10 ** (-0.4 * (0.25 * Math.sin(2 * Math.PI * mjd / 37) + 0.2 * Math.sin(2 * Math.PI * mjd / 91 + 1)));
  }
  return sed.flux * planckRatio(lambda, sed.lambda, sed.temperature) * variability;
}
function pixelOf(center: SkyPosition, position: SkyPosition, nx: number, ny: number): { x: number; y: number } {
  const cosDec = Math.max(0.02, Math.cos(center.dec * D2R));
  return {
    x: (nx - 1) / 2 - ((position.ra - center.ra + 540) % 360 - 180) * cosDec * 3600 / PIX_ARCSEC,
    y: (ny - 1) / 2 - (position.dec - center.dec) * 3600 / PIX_ARCSEC,
  };
}
function addGaussian(data: Float32Array, nx: number, ny: number, x: number, y: number, amplitude: number): void {
  const radius = 4;
  for (let dy = -radius; dy <= radius; dy++) for (let dx = -radius; dx <= radius; dx++) {
    const px = Math.round(x) + dx, py = Math.round(y) + dy;
    if (px < 0 || px >= nx || py < 0 || py >= ny) continue;
    data[py * nx + px] += amplitude * Math.exp(-((px - x) ** 2 + (py - y) ** 2) / (2 * PSF_SIGMA ** 2));
  }
}
function finishFrame(data: Float32Array, mask: Uint8Array, nx: number, ny: number, observation: Observation, center: SkyPosition): Frame {
  const samples = Array.from(data).filter(Number.isFinite);
  const masked = mask.reduce((sum, value) => sum + value, 0);
  return { nx, ny, data, mask, flags: { ...observation.flags, __masked: masked }, median: median(samples), center, observation };
}

export class DemoSource implements FrameSource {
  readonly isDemo = true;

  async resolve(query: string): Promise<Target | null> {
    const local = localResolve(query);
    if (local) return local;
    try {
      const url = `https://vizier.cfa.harvard.edu/viz-bin/Sesame?${encodeURIComponent(query)}`;
      const response = await fetch(url);
      if (!response.ok) return null;
      const body = await response.text();
      const coordinates = body.match(/%J\s+([\d.]+)\s+([+-]?[\d.]+)/);
      if (!coordinates) return null;
      const motion = body.match(/%P\s+([+-]?[\d.]+)\s+([+-]?[\d.]+)/);
      return {
        key: query, name: { es: query, en: query }, short: query, ra: Number(coordinates[1]), dec: Number(coordinates[2]),
        pmra: Number(motion?.[1] ?? 0), pmdec: Number(motion?.[2] ?? 0), aliases: [query],
      };
    } catch (error) {
      console.warn('[demoSource] No se pudo resolver por Sesame; queda disponible la resolución local.', error);
      return null;
    }
  }

  async epocas(_center: SkyPosition, _fovArcmin: number, _collection: string, target: Target | null): Promise<Observation[]> {
    const observations: Observation[] = [];
    for (const date of DATES) {
      const epochMjd = mjdOf(date);
      for (const [detectorIndex, detector] of DET.entries()) {
        for (const channel of [5, 9, 13]) {
          const jitter = (random(hash32(`${date}${detector.id}${channel}`))() - 0.5) * 0.7;
          const mjd = epochMjd + detectorIndex * 1.3 + channel * 0.11;
          observations.push({
            id: `${date}_${detector.id}_c${channel}`, date: dateOfMjd(mjd), mjd, detector: detector.id,
            lambda_um: detector.min + (channel + 0.5 + jitter) * channelWidth(detector.id), flags: {}, target: target ?? undefined,
          });
        }
      }
    }
    return observations.sort((a, b) => a.mjd - b.mjd);
  }

  async frame(observation: Observation, center: SkyPosition, nx: number, ny: number, _collection: string): Promise<Frame> {
    const rng = random(hash32(`${observation.id}|${nx}x${ny}`));
    const data = new Float32Array(nx * ny);
    const mask = new Uint8Array(nx * ny);
    const base = 4 * (1 + 1.5 * Math.exp(-(observation.lambda_um - 0.75) / 0.6));
    const gradientX = (rng() - 0.5) * 0.01, gradientY = (rng() - 0.5) * 0.01;
    for (let y = 0; y < ny; y++) for (let x = 0; x < nx; x++) {
      data[y * nx + x] = base + gradientX * (x - nx / 2) + gradientY * (y - ny / 2) + NOISE * gaussian(rng);
    }

    // Campo determinista para que las estrellas de fondo permanezcan fijas entre épocas.
    const stars = random(hash32(`${center.ra.toFixed(3)}:${center.dec.toFixed(3)}`));
    for (let i = 0; i < 42; i++) {
      const x = stars() * nx, y = stars() * ny;
      const amplitude = 0.4 + stars() * 2.5;
      addGaussian(data, nx, ny, x, y, amplitude);
    }
    const target = observation.target;
    if (target) {
      const position = propagarProperMotion({ ra: target.ra, dec: target.dec, pmRA: target.pmra, pmDec: target.pmdec }, 2000 + (observation.mjd - 51544.5) / 365.25);
      const pixel = pixelOf(center, position, nx, ny);
      const flux = targetFlux(target, observation.lambda_um, observation.mjd) / MJY_SR_TO_MJY / (2 * Math.PI * PSF_SIGMA ** 2);
      addGaussian(data, nx, ny, pixel.x, pixel.y, Math.min(flux, 500));
    }
    for (let i = 0, count = Math.round(nx * ny * 0.0015); i < count; i++) {
      const pixel = Math.floor(rng() * nx * ny);
      data[pixel] += 20 + rng() * 40;
      mask[pixel] = 1;
    }
    return finishFrame(data, mask, nx, ny, observation, center);
  }

  async spectrum(center: SkyPosition, _collection: string, options: PhotometryOptions, target: Target | null): Promise<SpectrumPoint[]> {
    const observations = await this.epocas(center, 6, _collection, target);
    return Promise.all(observations.map(async (observation) => {
      const frame = await this.frame(observation, center, 41, 41, _collection);
      const result = aperturePhotometry(frame, options, NOISE, PSF_SIGMA);
      return {
        obs_id: observation.id, date: observation.date, mjd: observation.mjd, detector: observation.detector,
        lambda_um: observation.lambda_um, flux_mjy: result.flux, err_mjy: result.error, nbad: result.badPixels,
      };
    }));
  }
}

