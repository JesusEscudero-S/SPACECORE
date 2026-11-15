import type { Lang, Target } from '../api/source';

// Las coordenadas y parámetros fotométricos vienen del prototipo; los parámetros SED
// y la variabilidad solo generan datos de demostración y no son mediciones SPHEREx.
export const TARGETS: readonly Target[] = [
  {
    key: 'barnard', name: { es: 'Estrella de Barnard', en: "Barnard's Star" }, short: 'Barnard',
    ra: 269.4521, dec: 4.6934, pmra: -798.6, pmdec: 10328.1,
    aliases: ['barnard', 'barnards star', 'barnard s star', 'estrella de barnard', 'gj 699', 'v2500 oph'],
    sed: { lambda: 2.2, flux: 10500, temperature: 3200 },
  },
  {
    key: 'epsindib', name: { es: 'Epsilon Indi B', en: 'Epsilon Indi B' }, short: 'ε Indi B',
    ra: 331.044, dec: -56.783, pmra: 3960, pmdec: -2538,
    aliases: ['epsilon indi b', 'eps indi b', 'eps ind b', 'epsilon indi', 'epsilon indi ba', 'eps indi'],
    sed: { lambda: 2.2, flux: 22, temperature: 1250 },
    note: {
      es: 'Par de enanas marrones (no se resuelve en SPHEREx). ε Indi A, mucho más brillante, queda a ~6.7′.',
      en: 'Brown dwarf pair (unresolved by SPHEREx). The much brighter ε Indi A lies ~6.7′ away.',
    },
  },
  {
    key: 'wise0855', name: { es: 'WISE 0855', en: 'WISE 0855' }, short: 'WISE 0855',
    ra: 133.7951, dec: -7.2452, pmra: -8100, pmdec: 700,
    aliases: ['wise 0855', 'wise0855', 'wise j0855', 'wise 0855-0714', 'wise j085510.83-071442.5'],
    detector: 'D6', sed: { lambda: 4.6, flux: 0.47, temperature: 285 },
    note: {
      es: 'Parámetros físicos ilustrativos (~285 K), no medidos. Prueba D6 y modo Suma.',
      en: 'Illustrative physical parameters (~285 K), not measured. Try D6 and Sum mode.',
    },
  },
  {
    key: 'rwaur', name: { es: 'RW Aurigae', en: 'RW Aurigae' }, short: 'RW Aur',
    ra: 76.9573, dec: 30.4015, pmra: 0, pmdec: 0,
    aliases: ['rw aur', 'rw aurigae', 'rw auriga'], sed: { lambda: 2.2, flux: 1830, temperature: 4000 },
    variability: { kind: 'tts' },
    note: { es: 'Estrella joven variable (tipo T Tauri): su brillo cambia de forma irregular.', en: 'Young variable star (T Tauri type): its brightness changes irregularly.' },
  },
  {
    key: 'rdra', name: { es: 'R Draconis', en: 'R Draconis' }, short: 'R Dra',
    ra: 248.178, dec: 66.755, pmra: 0, pmdec: 0,
    aliases: ['r dra', 'r draconis', 'r draconis mira'], sed: { lambda: 2.2, flux: 150000, temperature: 2800 },
    variability: { kind: 'mira', period: 245, amplitude: 0.7 },
    note: { es: 'Variable tipo Mira: su brillo cambia mucho en unos 8 meses.', en: 'Mira-type variable: its brightness changes strongly over about 8 months.' },
  },
];

export function targetName(target: Target, lang: Lang): string { return target.name[lang] || target.short; }

function normalize(value: string): string {
  return value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/gu, '').replace(/[^a-z0-9+\-. ]/gu, ' ').replace(/\s+/gu, ' ').trim();
}

export function localResolve(query: string): Target | null {
  const normalized = normalize(query).replace(/'/gu, '');
  return TARGETS.find((target) => target.aliases.some((alias) =>
    normalized === normalize(alias).replace(/'/gu, '') || normalized === normalize(target.name.es) || normalized === normalize(target.name.en))) ?? null;
}
