import { PIX_ARCSEC } from '../../config';
import type { Frame, PhotometryOptions } from '../../api/source';

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  if (!sorted.length) return 0;
  const middle = sorted.length >> 1;
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

/** Aperture sum with an annular background estimate, mask handling and 1σ noise. */
export function aperturePhotometry(
  frame: Frame,
  options: PhotometryOptions,
  noisePerPixel = 0.12,
  psfSigmaPixels = 0.95,
): { flux: number; error: number; badPixels: number } {
  const pixelSolidAngle = (PIX_ARCSEC / 206265) ** 2;
  const pixelFluxScale = pixelSolidAngle * 1e9;
  const centerX = (frame.nx - 1) / 2, centerY = (frame.ny - 1) / 2;
  const aperture = options.ap / PIX_ARCSEC;
  const inner = options.annIn / PIX_ARCSEC;
  const outer = options.annOut / PIX_ARCSEC;
  const ring: number[] = [], apertureValues: number[] = [];
  let badPixels = 0;
  for (let y = 0; y < frame.ny; y++) for (let x = 0; x < frame.nx; x++) {
    const radius = Math.hypot(x - centerX, y - centerY);
    const index = y * frame.nx + x;
    const flagged = frame.mask[index] === 1;
    if (radius <= aperture) {
      if (flagged) badPixels++;
      if (!(flagged && options.exclMask)) apertureValues.push(frame.data[index]);
    } else if (radius >= inner && radius <= outer && !(flagged && options.exclMask)) ring.push(frame.data[index]);
  }
  const background = options.subBg ? median(ring) : 0;
  const encircledEnergy = Math.max(0.05, 1 - Math.exp(-(aperture ** 2) / (2 * psfSigmaPixels ** 2)));
  const sum = apertureValues.reduce((total, value) => total + value - background, 0);
  const error = noisePerPixel * Math.sqrt(apertureValues.length * (1 + apertureValues.length / Math.max(1, ring.length))) * pixelFluxScale / encircledEnergy;
  return { flux: sum * pixelFluxScale / encircledEnergy, error, badPixels };
}
