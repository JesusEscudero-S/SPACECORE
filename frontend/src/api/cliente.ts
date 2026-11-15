// Cliente de la API de SPACECORE. Implementa el contrato de docs/api.md (propuesta T02):
//   GET /resolve?name   GET /epocas?ra&dec&fov&det   GET /frames?ra&dec&fov&det   GET /spectrum?ra&dec
// Si el contrato cambia, este es el ÚNICO archivo que hay que tocar.
import { DET, EPOCA_CENTRADO, detector } from '../config';
import { propagarProperMotion } from '../lib/coords';
import type { DetectorId, Frame, FrameSource, Observation, PhotometryOptions, SkyPosition, SpectrumPoint, Target } from './source';

interface RespuestaResolve { name: string; ra: number; dec: number }
interface Epoca { id: string; inicio: string; fin?: string; n_imagenes?: number }
interface FrameApi { epoca: string; fecha: string; png: string }
interface RespuestaFrames { frames: FrameApi[] }
interface PuntoEspectro {
  lambda_um: number; flujo: number; error?: number | null; fecha?: string; mjd?: number;
  detector?: DetectorId; epoca?: string; n_malos?: number;
}

const TIEMPO_LIMITE_MS = 180_000;

class ErrorApi extends Error {
  constructor(mensaje: string, readonly estado: number) { super(mensaje); }
}

function mjdDe(fecha: string): number {
  const ms = Date.parse(fecha);
  return Number.isFinite(ms) ? ms / 86400000 + 40587 : 0;
}

function detectorDeLambda(lambda: number): DetectorId {
  return (DET.find((d) => lambda >= d.min && lambda <= d.max) ?? DET[1]).id;
}

async function pngAFrame(png: string, observation: Observation, center: SkyPosition): Promise<Frame> {
  const bitmap = await createImageBitmap(await (await fetch(png)).blob());
  const nx = bitmap.width, ny = bitmap.height;
  const canvas = document.createElement('canvas');
  canvas.width = nx; canvas.height = ny;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  if (!ctx) throw new Error('El navegador no pudo leer la imagen PNG.');
  ctx.drawImage(bitmap, 0, 0);
  bitmap.close();
  const rgba = ctx.getImageData(0, 0, nx, ny).data;
  const data = new Float32Array(nx * ny);
  for (let i = 0; i < data.length; i++) data[i] = 0.299 * rgba[4 * i] + 0.587 * rgba[4 * i + 1] + 0.114 * rgba[4 * i + 2];
  const ordenado = Float32Array.from(data).sort();
  return { nx, ny, data, mask: new Uint8Array(nx * ny), flags: {}, median: ordenado[ordenado.length >> 1] ?? 0, center, observation };
}

export class ClienteApi implements FrameSource {
  readonly isDemo = false;
  private readonly base: string;
  private fovGrados = 0.1;
  private readonly cacheFrames = new Map<string, Promise<Map<string, string>>>();

  constructor(base: string) { this.base = base.replace(/\/$/u, ''); }

  /** ¿Responde el backend? Llama a /health con un límite de 25 s.
   *  (Cloud Run apaga el servidor si nadie lo usa y tarda unos segundos en volver a arrancar:
   *  con un límite corto, el primer visitante veía un error aunque todo estuviera bien.) */
  async salud(): Promise<boolean> {
    try {
      const respuesta = await fetch(`${this.base}/health`, { signal: AbortSignal.timeout(25000) });
      return respuesta.ok;
    } catch { return false; }
  }

  private async pedir<T>(ruta: string, params: Record<string, string | number>): Promise<T> {
    const consulta = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]));
    // /frames puede tardar ~1 min la primera vez (descarga y suma las imágenes de IRSA).
    const limite = new AbortController();
    const reloj = setTimeout(() => limite.abort(), TIEMPO_LIMITE_MS);
    let respuesta: Response;
    try {
      respuesta = await fetch(`${this.base}${ruta}?${consulta}`, { signal: limite.signal });
    } catch (error) {
      // fetch solo falla así cuando NO hubo respuesta: servidor apagado, URL mal escrita o CORS.
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new ErrorApi(`El backend tardó más de ${TIEMPO_LIMITE_MS / 1000} s en ${ruta}. Vuelve a intentar: la segunda vez sale de la caché.`, 504);
      }
      throw new ErrorApi(`No se pudo conectar con el backend (${this.base}). Revisa que uvicorn esté corriendo y que CORS_ORIGINS incluya ${location.origin}.`, 0);
    } finally {
      clearTimeout(reloj);
    }
    if (!respuesta.ok) {
      let mensaje = `HTTP ${respuesta.status} en ${ruta}`;
      try { const cuerpo = await respuesta.json() as { error?: string }; if (cuerpo.error) mensaje = cuerpo.error; } catch { /* sin JSON */ }
      throw new ErrorApi(mensaje, respuesta.status);
    }
    return await respuesta.json() as T;
  }

  async resolve(query: string): Promise<Target | null> {
    try {
      const d = await this.pedir<RespuestaResolve>('/resolve', { name: query });
      if (!Number.isFinite(d.ra) || !Number.isFinite(d.dec)) return null;
      const nombre = d.name || query;
      // api.md aún no incluye movimiento propio: queda en 0 para objetos que no estén en la lista local.
      return { key: nombre, name: { es: nombre, en: nombre }, short: nombre, ra: d.ra, dec: d.dec, pmra: 0, pmdec: 0, aliases: [query, nombre] };
    } catch (error) {
      if (error instanceof ErrorApi && error.estado === 404) return null;
      throw error;
    }
  }

  // Una consulta liviana por detector (sin imágenes). Cada época se vuelve una "observación".
  async epocas(center: SkyPosition, fovArcmin: number, _coleccion: string, _objetivo: Target | null): Promise<Observation[]> {
    this.fovGrados = fovArcmin / 60;
    const ids = DET.map((d) => d.id);
    const resultados = await Promise.allSettled(ids.map((det) =>
      this.pedir<{ epocas: Epoca[] }>('/epocas', { ra: center.ra, dec: center.dec, fov: this.fovGrados, det })));
    const observaciones: Observation[] = [];
    let primerError: unknown = null;
    resultados.forEach((res, i) => {
      if (res.status === 'rejected') { primerError ??= res.reason; return; }
      const rango = detector(ids[i]);
      for (const e of res.value.epocas ?? []) {
        observaciones.push({
          id: `${ids[i]}:${e.id}`, date: e.inicio.slice(0, 10), mjd: mjdDe(e.inicio), detector: ids[i],
          lambda_um: (rango.min + rango.max) / 2, flags: {}, // api.md no trae λ por imagen: se usa el centro del detector
        });
      }
    });
    if (!observaciones.length && primerError) throw primerError instanceof Error ? primerError : new Error(String(primerError));
    return observaciones.sort((a, b) => a.mjd - b.mjd);
  }

  // /frames devuelve todas las épocas de un detector en una sola respuesta: se pide una vez y se guarda.
  private framesDe(det: DetectorId, center: SkyPosition): Promise<Map<string, string>> {
    const clave = `${det}|${center.ra.toFixed(6)}|${center.dec.toFixed(6)}|${this.fovGrados.toFixed(5)}`;
    let pendiente = this.cacheFrames.get(clave);
    if (!pendiente) {
      pendiente = this.pedir<RespuestaFrames>('/frames', { ra: center.ra, dec: center.dec, fov: this.fovGrados, det })
        .then((r) => new Map((r.frames ?? []).map((f) => [f.epoca, f.png] as const)));
      pendiente.catch(() => this.cacheFrames.delete(clave));
      this.cacheFrames.set(clave, pendiente);
    }
    return pendiente;
  }

  async frame(observation: Observation, center: SkyPosition, _nx: number, _ny: number, _coleccion: string): Promise<Frame> {
    const idEpoca = observation.id.slice(observation.id.indexOf(':') + 1);
    const png = (await this.framesDe(observation.detector, center)).get(idEpoca);
    if (!png) throw new Error(`El backend no devolvió imagen para la época ${idEpoca}.`);
    return await pngAFrame(png, observation, center);
  }

  // Un punto por imagen de SPHEREx. La apertura y el anillo de la interfaz se envían en arcsec.
  // Si el centro es el objetivo, se manda su movimiento propio: el backend mueve la apertura a
  // donde estaba la estrella en la fecha de cada imagen (el centro está en EPOCA_CENTRADO, ver App.ts).
  async spectrum(center: SkyPosition, _coleccion: string, opciones: PhotometryOptions, objetivo: Target | null): Promise<SpectrumPoint[]> {
    const params: Record<string, string | number> = {
      ra: center.ra, dec: center.dec, apertura: opciones.ap, anillo_in: opciones.annIn, anillo_out: opciones.annOut,
      fondo: String(opciones.subBg),
    };
    if (objetivo && (objetivo.pmra || objetivo.pmdec)) {
      const epoca = EPOCA_CENTRADO;
      const p = propagarProperMotion({ ra: objetivo.ra, dec: objetivo.dec, pmRA: objetivo.pmra, pmDec: objetivo.pmdec }, epoca);
      const distanciaArcsec = Math.hypot((p.ra - center.ra) * Math.cos((center.dec * Math.PI) / 180), p.dec - center.dec) * 3600;
      if (distanciaArcsec < 10) Object.assign(params, { pmra: objetivo.pmra, pmdec: objetivo.pmdec, epoca });
    }
    const d = await this.pedir<{ puntos: PuntoEspectro[] }>('/spectrum', params);
    return (d.puntos ?? [])
      // "Excluir píxeles marcados": quita los puntos con píxeles sin dato (centro saturado) en la apertura.
      .filter((p) => !(opciones.exclMask && (p.n_malos ?? 0) > 0))
      .map((p, i) => {
        const det = p.detector ?? detectorDeLambda(p.lambda_um);
        return {
          obs_id: p.epoca ? `${det}:${p.epoca}` : `S${i + 1}`, date: (p.fecha ?? '').slice(0, 10), mjd: p.mjd ?? 0,
          detector: det, lambda_um: p.lambda_um, flux_mjy: p.flujo, err_mjy: p.error ?? 0, nbad: p.n_malos ?? 0,
        };
      });
  }
}
