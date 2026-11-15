import type { Frame } from '../../api/source';
import type { DisplaySettings } from '../../state/store';
import { commonScale, stretchValue, type StretchScale } from './stretch';

export function frameCanvas(frame: Frame, settings: DisplaySettings, scale?: StretchScale): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = frame.nx; canvas.height = frame.ny;
  const context = canvas.getContext('2d');
  if (!context) return canvas;
  const image = context.createImageData(frame.nx, frame.ny);
  const shared = scale ?? commonScale([frame], settings.subtractBackground);
  for (let i = 0; i < frame.data.length; i++) {
    const index = i * 4;
    const source = frame.data[i] - (settings.subtractBackground ? frame.median : 0);
    const value = Math.round(Math.max(0, Math.min(1, stretchValue(source, shared, settings.stretch))) * 255);
    if (settings.showMask && frame.mask[i]) {
      image.data[index] = 236; image.data[index + 1] = 139; image.data[index + 2] = 81;
    } else image.data[index] = image.data[index + 1] = image.data[index + 2] = value;
    image.data[index + 3] = 255;
  }
  context.putImageData(image, 0, 0);
  return canvas;
}

export function differenceCanvas(a: Frame, b: Frame, settings: DisplaySettings, scale?: StretchScale): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = a.nx; canvas.height = a.ny;
  const context = canvas.getContext('2d');
  if (!context) return canvas;
  const image = context.createImageData(a.nx, a.ny);
  const shared = scale ?? commonScale([a, b], settings.subtractBackground);
  for (let i = 0; i < a.data.length; i++) {
    const delta = (b.data[i] - (settings.subtractBackground ? b.median : 0)) - (a.data[i] - (settings.subtractBackground ? a.median : 0));
    const strength = Math.max(-1, Math.min(1, Math.asinh(delta / (shared.sigma * 3)) / Math.asinh(shared.high / 3)));
    const amount = Math.abs(strength), base = [63, 69, 78], tint = strength < 0 ? [111, 195, 209] : [224, 134, 111];
    const index = i * 4;
    image.data[index] = base[0] + (tint[0] - base[0]) * amount;
    image.data[index + 1] = base[1] + (tint[1] - base[1]) * amount;
    image.data[index + 2] = base[2] + (tint[2] - base[2]) * amount;
    image.data[index + 3] = 255;
  }
  context.putImageData(image, 0, 0);
  return canvas;
}
