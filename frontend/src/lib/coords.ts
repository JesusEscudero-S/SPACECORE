const RA_RANGE_MESSAGE = 'La ascensión recta debe estar entre 0 y 360° (o entre 0 y 24 h).';
const DEC_RANGE_MESSAGE = 'La declinación debe estar entre −90° y +90°.';

function normalizeText(value: unknown): string {
  return String(value ?? '').trim().replace(/[−–]/gu, '-').replace(/[＋]/gu, '+');
}

function parseDecimal(value: unknown, fieldName: string): number {
  const normalized = normalizeText(value);
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:\s*(?:°|deg))?$/iu.test(normalized)) {
    throw new TypeError(`${fieldName} no tiene un formato válido.`);
  }
  const numeric = normalized.replace(/\s*(?:°|deg)$/iu, '');
  const result = Number(numeric);
  if (!Number.isFinite(result)) throw new TypeError(`${fieldName} no tiene un formato válido.`);
  return result;
}

function parseSexagesimal(value: unknown, fieldName: string): number {
  const normalized = normalizeText(value)
    .replace(/[hH°ºdD:：mM'′’sS"″]/gu, ' ')
    .trim();
  const match = normalized.match(/^([+-]?)\s*(\d+(?:\.\d+)?)(?:\s+(\d+(?:\.\d+)?))?(?:\s+(\d+(?:\.\d+)?))?$/u);
  if (!match) throw new TypeError(`${fieldName} no tiene un formato válido.`);

  const first = Number(match[2]);
  const minutes = match[3] === undefined ? 0 : Number(match[3]);
  const seconds = match[4] === undefined ? 0 : Number(match[4]);
  if (minutes >= 60 || seconds >= 60) {
    throw new RangeError('Los minutos y segundos deben ser menores que 60.');
  }
  const magnitude = first + minutes / 60 + seconds / 3600;
  return match[1] === '-' ? -magnitude : magnitude;
}

/** Detecta horas sexagesimales por el formato; un número simple se interpreta como grados. */
export type RAUnit = 'auto' | 'deg' | 'degrees' | 'h' | 'hours';

export function detectRAUnit(value: unknown, requestedUnit: RAUnit = 'auto'): 'h' | 'deg' {
  if (requestedUnit === 'h' || requestedUnit === 'hours') return 'h';
  if (requestedUnit === 'deg' || requestedUnit === 'degrees') return 'deg';
  return /[\s:：hHmMsS]/u.test(String(value ?? '').trim()) ? 'h' : 'deg';
}

/** Convierte RA a grados. `unit` acepta auto, deg o h. */
export function parseRA(value: unknown, unit: RAUnit = 'auto'): number {
  const text = normalizeText(value);
  if (!text) throw new TypeError('Escribe una ascensión recta.');
  const resolvedUnit = detectRAUnit(text, unit);
  if (text.startsWith('-')) throw new RangeError(RA_RANGE_MESSAGE);

  const hasSexagesimalParts = /[\s:：hHmMsS]/u.test(text);
  let parsed;
  if (!hasSexagesimalParts && resolvedUnit === 'deg') {
    parsed = parseDecimal(text, 'La ascensión recta');
  } else {
    parsed = parseSexagesimal(text, 'La ascensión recta');
  }

  const degrees = resolvedUnit === 'h' ? parsed * 15 : parsed;
  if (degrees < 0 || degrees > 360) throw new RangeError(RA_RANGE_MESSAGE);
  return degrees === 360 ? 0 : degrees;
}

/** Convierte una declinación decimal o sexagesimal a grados con signo. */
export function parseDec(value: unknown): number {
  const text = normalizeText(value);
  if (!text) throw new TypeError('Escribe una declinación.');
  const looksDecimal = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:\s*(?:°|deg))?$/iu.test(text);
  const degrees = looksDecimal ? parseDecimal(text, 'La declinación') : parseSexagesimal(text, 'La declinación');
  if (degrees < -90 || degrees > 90) throw new RangeError(DEC_RANGE_MESSAGE);
  return degrees;
}

/** Formatea grados de RA como horas, minutos y segundos. */
export function formatRA(raDegrees: number, precision = 2): string {
  if (!Number.isFinite(raDegrees)) throw new TypeError('La ascensión recta debe ser un número finito.');
  const circleSeconds = 24 * 60 * 60;
  const factor = 10 ** precision;
  let total = ((((raDegrees % 360) + 360) % 360) / 15) * 3600;
  total = Math.round(total * factor) / factor;
  if (total >= circleSeconds) total = 0;
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total - hours * 3600) / 60);
  const seconds = total - hours * 3600 - minutes * 60;
  return `${String(hours).padStart(2, '0')}h${String(minutes).padStart(2, '0')}m${seconds.toFixed(precision).padStart(precision ? 5 + precision - 2 : 2, '0')}s`;
}

/** Formatea grados de Dec como grados, minutos y segundos con signo explícito. */
export function formatDec(decDegrees: number, precision = 1): string {
  if (!Number.isFinite(decDegrees)) throw new TypeError('La declinación debe ser un número finito.');
  const sign = decDegrees < 0 || Object.is(decDegrees, -0) ? '−' : '+';
  const factor = 10 ** precision;
  let total = Math.round(Math.abs(decDegrees) * 3600 * factor) / factor;
  const maxSeconds = 90 * 3600;
  if (total > maxSeconds) total = maxSeconds;
  const degrees = Math.floor(total / 3600);
  const minutes = Math.floor((total - degrees * 3600) / 60);
  const seconds = total - degrees * 3600 - minutes * 60;
  const secWidth = precision ? 3 + precision : 2;
  return `${sign}${String(degrees).padStart(2, '0')}°${String(minutes).padStart(2, '0')}′${seconds.toFixed(precision).padStart(secWidth, '0')}″`;
}

/**
 * Propaga linealmente una posición desde una época de referencia.
 * pmRA debe ser μRA·cos(Dec), en mas/año, como lo entrega SIMBAD.
 */
export function propagarProperMotion(position: { ra: number; dec: number; pmRA: number; pmDec: number; epoch?: number }, targetEpoch: number): { ra: number; dec: number; deltaYears: number } {
  const { ra, dec, pmRA, pmDec, epoch = 2000 } = position ?? {};
  if (![ra, dec, pmRA, pmDec, epoch, targetEpoch].every(Number.isFinite)) {
    throw new TypeError('La posición, el movimiento propio y las épocas deben ser números finitos.');
  }
  if (dec < -90 || dec > 90) throw new RangeError(DEC_RANGE_MESSAGE);
  const deltaYears = targetEpoch - epoch;
  const cosDec = Math.cos((dec * Math.PI) / 180);
  if (Math.abs(cosDec) < 1e-12 && pmRA !== 0) {
    throw new RangeError('No se puede aproximar el movimiento en RA en el polo celeste.');
  }
  const nextDec = dec + (pmDec * deltaYears) / 3_600_000;
  const nextRA = ra + (pmRA * deltaYears) / (3_600_000 * (cosDec || 1));
  return {
    ra: ((nextRA % 360) + 360) % 360,
    dec: Math.max(-90, Math.min(90, nextDec)),
    deltaYears,
  };
}

export function currentDecimalYear(date = new Date()): number {
  const start = Date.UTC(date.getUTCFullYear(), 0, 1);
  const end = Date.UTC(date.getUTCFullYear() + 1, 0, 1);
  return date.getUTCFullYear() + (date.getTime() - start) / (end - start);
}



/** Separación aproximada entre dos posiciones, en segundos de arco (válida para distancias cortas). */
export function separacionArcsec(a: { ra: number; dec: number }, b: { ra: number; dec: number }): number {
  const cosDec = Math.cos((((a.dec + b.dec) / 2) * Math.PI) / 180);
  let dRa = a.ra - b.ra;
  if (dRa > 180) dRa -= 360;
  if (dRa < -180) dRa += 360;
  return Math.hypot(dRa * cosDec, a.dec - b.dec) * 3600;
}

/** Radio (arcsec) dentro del cual un clic en la imagen cuenta como "el objetivo del centro". */
export const RADIO_OBJETIVO_ARCSEC = 15;

/**
 * Dónde se calcula el espectro: el punto elegido con clic, salvo que el clic caiga a menos de
 * RADIO_OBJETIVO_ARCSEC del centro (casi siempre es un clic sobre la misma estrella objetivo).
 * Así un clic sobre la estrella no pide una posición nueva que no está en la caché.
 */
export function posicionEspectro(center: { ra: number; dec: number }, selected: { ra: number; dec: number } | null): { ra: number; dec: number } {
  if (!selected || separacionArcsec(center, selected) < RADIO_OBJETIVO_ARCSEC) return center;
  return selected;
}
