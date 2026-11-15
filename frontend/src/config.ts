import type { DetectorId, DetectorRange } from './api/source';

// Colecciones vigentes de SPHEREx en IRSA (verificado el 2026-11-14 en el tutorial oficial):
// DR1 y QR3 reemplazan a QR2. El backend consulta las dos a la vez (COLECCION_SPHEREX).
export const COLLECTION = 'spherex_dr1';
export const API_BASE = new URLSearchParams(location.search).get('api') || import.meta.env.VITE_API_URL || null;
// Tamaño de píxel de SPHEREx: 6.15″ (columna s_pixel_scale del servicio SIA de IRSA, 2026-11-14).
export const PIX_ARCSEC = 6.15;
// Fecha FIJA (año decimal) en la que se centran los objetivos con movimiento propio.
// Debe ser IGUAL a EPOCA_CENTRADO de backend/scripts/precalcular.py (ver App.ts).
export const EPOCA_CENTRADO = 2026;
export const CHANNELS_PER_DETECTOR = 17;
export const COLLECTIONS = [COLLECTION, 'spherex_qr3'] as const;
export const EXPLANATORY_SUPPLEMENT = 'https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf';

// Bordes de detector tomados del prototipo. VERIFICAR contra el Explanatory Supplement.
export const DET: readonly DetectorRange[] = [
  { id: 'D1', min: 0.75, max: 1.09 },
  { id: 'D2', min: 1.09, max: 1.62 },
  { id: 'D3', min: 1.62, max: 2.41 },
  { id: 'D4', min: 2.41, max: 3.82 },
  { id: 'D5', min: 3.82, max: 4.42 },
  { id: 'D6', min: 4.42, max: 5.0 },
];

export function detector(id: DetectorId): DetectorRange {
  return DET.find((entry) => entry.id === id) ?? DET[1];
}

export function channelWidth(id: DetectorId): number {
  const range = detector(id);
  return (range.max - range.min) / CHANNELS_PER_DETECTOR;
}
