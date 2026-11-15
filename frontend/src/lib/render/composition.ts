import type { CompareMode, Frame } from '../../api/source';

export function composeFrames(a: Frame, b: Frame, mode: CompareMode, blinkToB = false): Float32Array {
  const count = Math.min(a.data.length, b.data.length);
  const output = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    if (mode === 'diff') output[i] = (b.data[i] - b.median) - (a.data[i] - a.median);
    else if (mode === 'sum') output[i] = ((a.data[i] - a.median) + (b.data[i] - b.median)) / 2;
    else output[i] = (blinkToB ? b : a).data[i];
  }
  return output;
}
