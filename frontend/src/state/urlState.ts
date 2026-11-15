import type { CompareMode, Lang, ViewName } from '../api/source';
import type { AppState } from './store';
import { COLLECTION } from '../config';

export interface UrlState {
  api: string | null; lang: Lang; view: ViewName; collection: string; fovArcmin: number;
  detector: AppState['detector']; tolerance: AppState['tolerance']; mode: CompareMode;
  epochA: string; epochB: string; lambda: number; playing: boolean; embed: boolean;
  query: string; ra: number | null; dec: number | null;
}

const allowed = <T extends string>(value: string | null, choices: readonly T[], fallback: T): T =>
  choices.includes(value as T) ? value as T : fallback;

export function readUrlState(search = location.search): UrlState {
  const p = new URLSearchParams(search);
  const fov = Number(p.get('fov'));
  const lambda = Number(p.get('lam'));
  const raValue = p.get('ra');
  const decValue = p.get('dec');
  const ra = raValue === null ? Number.NaN : Number(raValue);
  const dec = decValue === null ? Number.NaN : Number(decValue);
  return {
    api: p.get('api'),
    lang: allowed(p.get('lang'), ['es', 'en'] as const, (navigator.language.startsWith('en') ? 'en' : 'es')),
    view: allowed(p.get('view'), ['explore', 'compare', 'spectrum'] as const, 'explore'),
    collection: p.get('collection') || COLLECTION,
    fovArcmin: Number.isFinite(fov) && fov > 0 ? Math.min(40, Math.max(1.5, fov)) : 6,
    detector: allowed(p.get('det'), ['D1', 'D2', 'D3', 'D4', 'D5', 'D6'] as const, 'D2'),
    tolerance: allowed(p.get('tol'), ['0.5', '1', '2', 'inf'] as const, '1'),
    mode: allowed(p.get('mode'), ['blink', 'slider', 'diff', 'sum'] as const, 'slider'),
    epochA: p.get('a') ?? '', epochB: p.get('b') ?? '',
    lambda: Number.isFinite(lambda) && lambda > 0 ? lambda : 0,
    playing: p.get('play') === '1', embed: p.get('embed') === '1',
    query: p.get('q') ?? '',
    ra: Number.isFinite(ra) && ra >= 0 && ra <= 360 ? ra : null,
    dec: Number.isFinite(dec) && dec >= -90 && dec <= 90 ? dec : null,
  };
}

export function writeUrlState(state: Readonly<AppState>, replace = true): URLSearchParams {
  const params = new URLSearchParams();
  if (state.api) params.set('api', state.api);
  params.set('lang', state.lang); params.set('view', state.view); params.set('collection', state.collection);
  params.set('fov', state.fovArcmin.toString()); params.set('det', state.detector); params.set('tol', state.tolerance);
  params.set('mode', state.mode); params.set('a', state.epochA); params.set('b', state.epochB);
  params.set('lam', state.lambda.toString()); params.set('play', state.playing ? '1' : '0');
  params.set('embed', state.embed ? '1' : '0'); if (state.query) params.set('q', state.query);
  params.set('ra', state.center.ra.toString()); params.set('dec', state.center.dec.toString());
  if (replace) {
    try { history.replaceState(null, '', `${location.pathname}?${params}`); }
    catch (error) { console.warn('[urlState] No se pudo actualizar el historial (iframe sandboxed).', error); }
  }
  return params;
}
