"""Une todas las piezas del backend para responder a los endpoints.

El camino de una búsqueda es:

    buscar_imagenes (IRSA, T10)  ->  agrupar_por_epoca (T12)  ->  descargar_recortes (T11)
    ->  alinear a la malla común (T23)  ->  sumar cada época (T22)  ->  PNG (T21)

y el del espectro (T36), al final de este archivo:

    buscar_imagenes  ->  recorte corto de cada imagen ("estampilla")  ->  longitud de onda
    (tabla WCS-WAVE, una por detector)  ->  fotometría de apertura en cada estampilla

Todo lo lento se guarda en la caché (T13):
- La lista de imágenes de la zona (consulta SIA): una sola consulta sirve para los 6
  detectores, así que las 6 llamadas a /epocas que hace la página solo consultan IRSA una vez.
- Las imágenes ya sumadas de cada época ("pila"): con ellas se sacan /frames y /diff sin
  volver a descargar nada.

Con USAR_MOCK=1 no se consulta IRSA: se usan datos falsos de app/mock.py.
"""

import asyncio
import io
import logging
import re
import threading

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.coordinates.name_resolve import NameResolveError
from pyvo.dal.exceptions import DALServiceError

from app import mock
from app.ciencia.alinear import (
    ESCALA_ARCSEC_PX,
    alinear_recorte,
    malla_objetivo,
    rellenar_huecos,
    sumar_epoca,
)
from app.ciencia import espectro as ciencia_espectro
from app.ciencia.imagen import a_data_url, a_png, limites_brillo
from app.config import settings
from app.datos import cache
from app.datos.descargas import abrir_recorte, descargar_recortes
from app.datos.epocas import agrupar_por_epoca
from app.datos.irsa import buscar_imagenes
from app.errores import ErrorApi

registro = logging.getLogger(__name__)

MENSAJE_IRSA_CAIDO = (
    "El archivo de la NASA (IRSA) no respondió. Suele ser temporal: intenta de nuevo en un minuto."
)

# ---------------------------------------------------------------------------------------------
# Candados: si llegan dos peticiones iguales a la vez (la página pide /epocas de los 6
# detectores al mismo tiempo), la segunda espera a la primera y luego usa la caché, en lugar
# de repetir la misma consulta lenta a IRSA.
# ---------------------------------------------------------------------------------------------
_candados: dict[str, threading.Lock] = {}
_candado_general = threading.Lock()


def _candado(clave: str) -> threading.Lock:
    with _candado_general:
        return _candados.setdefault(clave, threading.Lock())


# ---------------------------------------------------------------------------------------------
# Validaciones comunes
# ---------------------------------------------------------------------------------------------
def validar_fov(fov: float) -> None:
    """El contrato pide 400 si el campo de visión supera el máximo."""
    if fov > settings.fov_max:
        raise ErrorApi(
            400, f"El campo de visión máximo es {settings.fov_max:g} grados; pediste {fov:.3g}."
        )


# ---------------------------------------------------------------------------------------------
# /resolve
# ---------------------------------------------------------------------------------------------
# Respaldo para los 5 objetivos de prueba, por si el servicio de nombres del CDS (Sesame) falla.
# Coordenadas J2000 (las mismas de frontend/src/lib/objects.ts). WISE 0855: las de CLAUDE.md.
OBJETIVOS_PRUEBA = {
    "barnards star": ("Barnard's Star", 269.4521, 4.6934),
    "estrella de barnard": ("Barnard's Star", 269.4521, 4.6934),
    "gj 699": ("Barnard's Star", 269.4521, 4.6934),
    "epsilon indi b": ("Epsilon Indi B", 331.044, -56.783),
    "eps indi b": ("Epsilon Indi B", 331.044, -56.783),
    "wise 0855": ("WISE 0855", 133.7951, -7.2452),
    "wise 0855-0714": ("WISE 0855", 133.7951, -7.2452),
    "wise j085510.83-071442.5": ("WISE 0855", 133.7951, -7.2452),
    "rw aurigae": ("RW Aurigae", 76.9573, 30.4015),
    "rw aur": ("RW Aurigae", 76.9573, 30.4015),
    "r draconis": ("R Draconis", 248.178, 66.755),
    "r dra": ("R Draconis", 248.178, 66.755),
}


def _normalizar_nombre(nombre: str) -> str:
    """'Barnard's  Star' -> 'barnards star' (minúsculas, sin apóstrofos ni espacios dobles)."""
    texto = nombre.lower().replace("'", "").replace("’", "")
    return " ".join(texto.split())


def resolver(nombre: str) -> dict:
    """Convierte un nombre de objeto en coordenadas (grados ICRS)."""
    nombre = nombre.strip()
    if not nombre:
        raise ErrorApi(422, "Escribe el nombre de un objeto.")

    conocido = OBJETIVOS_PRUEBA.get(_normalizar_nombre(nombre))
    if conocido is not None:
        return {"name": nombre, "ra": conocido[1], "dec": conocido[2]}

    clave = cache.clave_de_texto("resolve", _normalizar_nombre(nombre))
    guardado = cache.get(clave)
    if guardado is not None:
        return {"name": nombre, "ra": guardado["ra"], "dec": guardado["dec"]}

    try:
        coordenada = SkyCoord.from_name(nombre)
    except NameResolveError as error:
        if "All Sesame queries failed" in str(error):
            raise ErrorApi(504, "El servicio de nombres (CDS Sesame) no respondió.") from error
        raise ErrorApi(404, f"No encontré el objeto {nombre!r}. Prueba con RA y Dec.") from error

    resultado = {"ra": round(float(coordenada.ra.deg), 6), "dec": round(float(coordenada.dec.deg), 6)}
    cache.set(clave, resultado)
    return {"name": nombre, **resultado}


# ---------------------------------------------------------------------------------------------
# /epocas
# ---------------------------------------------------------------------------------------------
def imagenes_de_zona(ra: float, dec: float, fov: float) -> list[dict]:
    """Lista de imágenes de SPHEREx (de los 6 detectores) que cubren el punto. Usa la caché."""
    clave = cache.crear_clave("sia", ra, dec, fov)
    with _candado(clave):
        imagenes = cache.get(clave)
        if imagenes is None:
            try:
                imagenes = buscar_imagenes(ra, dec, fov, detector=None)
            except (DALServiceError, OSError) as error:
                registro.error("IRSA no respondió: %r", error)
                raise ErrorApi(504, MENSAJE_IRSA_CAIDO) from error
            cache.set(clave, imagenes)
    return imagenes


def epocas(ra: float, dec: float, fov: float, det: str) -> list[dict]:
    """Épocas de un detector, con sus imágenes (ver agrupar_por_epoca)."""
    validar_fov(fov)
    if settings.usar_mock:
        return mock.epocas(det)
    imagenes = [i for i in imagenes_de_zona(ra, dec, fov) if i["detector"] == det]
    if not imagenes:
        raise ErrorApi(404, f"SPHEREx todavía no tiene imágenes de esa zona con el detector {det}.")
    return agrupar_por_epoca(imagenes)


def resumen_epocas(lista: list[dict]) -> list[dict]:
    """Deja solo los campos del contrato (quita la lista interna de imágenes)."""
    return [
        {"id": e["id"], "inicio": e["inicio"], "fin": e["fin"], "n_imagenes": e["n_imagenes"]}
        for e in lista
    ]


# ---------------------------------------------------------------------------------------------
# Pila de épocas (la base de /frames y /diff)
# ---------------------------------------------------------------------------------------------
def _pila_a_bytes(pila: np.ndarray) -> bytes:
    salida = io.BytesIO()
    np.save(salida, pila.astype(np.float32), allow_pickle=False)
    return salida.getvalue()


def _bytes_a_pila(datos: bytes) -> np.ndarray:
    return np.load(io.BytesIO(datos), allow_pickle=False).astype(float)


def _calcular_pila(ra: float, dec: float, fov: float, lista: list[dict]) -> tuple[np.ndarray, list[int], bool]:
    """Descarga, alinea y suma cada época.

    Devuelve (pila, usadas, completo): pila tiene una imagen por época (NaN si no se pudo
    usar ninguna), usadas dice cuántas imágenes entraron en cada época y completo es False si
    alguna descarga falló (en ese caso no se guarda en la caché, para reintentar después).
    """
    wcs_malla, forma = malla_objetivo(ra, dec, fov)

    urls = [imagen["url_recorte"] for e in lista for imagen in e["imagenes"]]
    # 4 descargas a la vez: con 8, IRSA respondía "503 Service Unavailable" seguido (2026-11-14).
    recortes = asyncio.run(descargar_recortes(urls, max_concurrentes=4))
    completo = all(r is not None for r in recortes)

    pila = []
    usadas = []
    posicion = 0
    for e in lista:
        alineadas = []
        for _ in e["imagenes"]:
            datos = recortes[posicion]
            posicion += 1
            if datos is None:
                continue
            try:
                with abrir_recorte(datos) as hdul:
                    alineadas.append(alinear_recorte(hdul, wcs_malla, forma))
            except Exception as error:  # un archivo dañado no debe tumbar toda la búsqueda
                registro.warning("No se pudo usar un recorte de %s: %r", e["id"], error)
                completo = False
        usadas.append(len(alineadas))
        pila.append(sumar_epoca(alineadas) if alineadas else np.full(forma, np.nan))
    return np.stack(pila), usadas, completo


def pila_en_cache(ra: float, dec: float, fov: float, det: str) -> bool:
    """¿Quedaron guardadas las imágenes de este detector? (lo usa scripts/precalcular.py).

    Si IRSA falla con alguna imagen, la pila NO se guarda (para no congelar un resultado
    incompleto) y la página la vuelve a calcular en cada visita: tarda ~20 s por detector.
    """
    clave = cache.crear_clave("pila", ra, dec, fov, det)
    return cache.get(clave) is not None and cache.get_bytes(clave) is not None


def pila_de_epocas(ra: float, dec: float, fov: float, det: str) -> tuple[list[dict], np.ndarray]:
    """Devuelve (épocas, pila). Solo incluye las épocas que tienen al menos una imagen usable."""
    lista = epocas(ra, dec, fov, det)
    if settings.usar_mock:
        return lista, mock.pila(lista, fov)

    clave = cache.crear_clave("pila", ra, dec, fov, det)
    with _candado(clave):
        info = cache.get(clave)
        datos = cache.get_bytes(clave)
        if info is not None and datos is not None:
            usadas = info["usadas"]
            pila = _bytes_a_pila(datos)
        else:
            pila, usadas, completo = _calcular_pila(ra, dec, fov, lista)
            if completo:
                cache.set_bytes(clave, _pila_a_bytes(pila))
                cache.set(clave, {"usadas": usadas})

    utiles = [i for i, n in enumerate(usadas) if n > 0]
    if not utiles:
        raise ErrorApi(504, "No se pudo descargar ninguna imagen de IRSA. " + MENSAJE_IRSA_CAIDO)
    return [lista[i] for i in utiles], pila[utiles]


def _meta(ra: float, dec: float, fov: float, det: str, tamano: int) -> dict:
    return {
        "detector": det,
        "fov_grados": fov,
        "ra": ra,
        "dec": dec,
        "tamano_px": tamano,
        "escala_arcsec_px": ESCALA_ARCSEC_PX,
    }


# ---------------------------------------------------------------------------------------------
# /frames y /diff
# ---------------------------------------------------------------------------------------------
def frames(ra: float, dec: float, fov: float, det: str) -> dict:
    """Un PNG por época, todos con la misma escala de brillo (contrato: GET /frames)."""
    lista, pila = pila_de_epocas(ra, dec, fov, det)
    vmin, vmax = limites_brillo(list(pila))
    cuadros = [
        {
            "epoca": e["id"],
            "fecha": e["fecha"],
            "png": a_data_url(a_png(rellenar_huecos(imagen), vmin, vmax)),
        }
        for e, imagen in zip(lista, pila)
    ]
    return {"frames": cuadros, "meta": _meta(ra, dec, fov, det, pila.shape[-1])}


def diferencia(ra: float, dec: float, fov: float, det: str, a: str, b: str) -> dict:
    """Época b menos época a (contrato: GET /diff). Gris = sin cambio."""
    if a == b:
        raise ErrorApi(400, "Elige dos épocas distintas para comparar.")
    lista, pila = pila_de_epocas(ra, dec, fov, det)
    ids = [e["id"] for e in lista]
    for epoca in (a, b):
        if epoca not in ids:
            raise ErrorApi(404, f"La época {epoca} no existe. Hay: {', '.join(ids)}.")
    resta = pila[ids.index(b)] - pila[ids.index(a)]
    validos = np.abs(resta[np.isfinite(resta)])
    limite = float(np.percentile(validos, 99.5)) if validos.size else 1.0
    limite = limite if limite > 0 else 1.0
    png = a_png(resta, -limite, limite, asinh=False)
    return {"png": a_data_url(png), "epoca_a": a, "epoca_b": b}



# ---------------------------------------------------------------------------------------------
# /spectrum (T36). Ver app/ciencia/espectro.py para la explicación científica.
# ---------------------------------------------------------------------------------------------
# Recorte de cada imagen para el espectro: 0.035 grados = 126 arcsec (~20 x 20 píxeles), así
# cabe un anillo de fondo de hasta 60 arcsec de radio. Pesa ~80 KB por imagen.
TAM_ESPECTRO_GRADOS = 0.035
RADIO_MAX_ARCSEC = 60.0
# Un punto popular tiene 300-500 imágenes (6 detectores). Tomamos como máximo 40 por detector,
# repartidas en el tiempo: el espectro sigue denso (240 puntos) y la primera vez tarda menos.
MAX_IMAGENES_POR_DETECTOR = 40
# Si se cambia cómo se calculan las estampillas, subir este número invalida la caché vieja.
VERSION_ESTAMPILLAS = 1
# Tamaño fijo de las estampillas guardadas (los recortes en el borde del detector salen más
# chicos; se rellenan con NaN abajo y a la derecha, sin mover los índices de los píxeles).
LADO_ESTAMPILLA = 24
# La lista de imágenes de IRSA se guarda en la caché con el fov en la clave. Usamos el mismo
# valor que pide la página (0.1), así el espectro reusa la consulta que ya hizo /epocas.
FOV_ZONA = 0.1


def _url_base(url: str) -> str:
    return url.split("?", 1)[0]


def _url_recorte(url: str, ra: float, dec: float, tam: float) -> str:
    return f"{_url_base(url)}?center={ra},{dec}d&size={tam}"


def _version_proceso(url: str) -> str:
    """'.../l2b-v27-2026-229/2/...' -> 'l2b-v27'. La tabla WCS-WAVE depende de esto y del detector."""
    encontrado = re.search(r"/(l2b-v\d+)-", url)
    return encontrado.group(1) if encontrado else "desconocida"


def _repartir(lista: list, maximo: int) -> list:
    """Hasta `maximo` elementos repartidos parejo a lo largo de la lista (que viene por fecha)."""
    if len(lista) <= maximo:
        return list(lista)
    indices = np.linspace(0, len(lista) - 1, maximo).round().astype(int)
    return [lista[i] for i in sorted(set(indices))]


def _tabla_onda(det: str, version: str, url: str, ra: float, dec: float):
    """Tabla WCS-WAVE del detector (se baja una vez: es el final de un recorte completo)."""
    clave = cache.clave_de_texto("wcs-wave", f"{det}|{version}")
    with _candado(clave):
        datos = cache.get_bytes(clave)
        if datos is None:
            completo = asyncio.run(
                descargar_recortes([_url_recorte(url, ra, dec, 0.01)], max_concurrentes=1, completo=True)
            )[0]
            if completo is None:
                return None
            with abrir_recorte(completo) as hdul:
                datos = ciencia_espectro.tabla_a_bytes(hdul["WCS-WAVE"])
            cache.set_bytes(clave, datos)
    return ciencia_espectro.bytes_a_tabla(datos)


def _a_lado_fijo(datos: np.ndarray) -> np.ndarray:
    salida = np.full((LADO_ESTAMPILLA, LADO_ESTAMPILLA), np.nan, dtype=np.float32)
    alto = min(LADO_ESTAMPILLA, datos.shape[0])
    ancho = min(LADO_ESTAMPILLA, datos.shape[1])
    salida[:alto, :ancho] = datos[:alto, :ancho]
    return salida


def _calcular_estampillas(ra: float, dec: float, imagenes: list[dict]) -> tuple[list[dict], np.ndarray, np.ndarray, bool]:
    """Baja el recorte corto de cada imagen y anota posición, longitud de onda y área del píxel."""
    urls = [_url_recorte(i["url_recorte"], ra, dec, TAM_ESPECTRO_GRADOS) for i in imagenes]
    recortes = asyncio.run(descargar_recortes(urls, max_concurrentes=4))
    completo = all(r is not None for r in recortes)

    tablas: dict[tuple[str, str], object] = {}
    meta, imgs, varianzas = [], [], []
    for imagen, datos in zip(imagenes, recortes):
        if datos is None:
            continue
        clave_tabla = (imagen["detector"], _version_proceso(imagen["url_recorte"]))
        if clave_tabla not in tablas:
            tablas[clave_tabla] = _tabla_onda(*clave_tabla, imagen["url_recorte"], ra, dec)
        tabla = tablas[clave_tabla]
        if tabla is None:
            completo = False
            continue
        try:
            with abrir_recorte(datos) as hdul:
                cabecera = hdul["IMAGE"].header
                unidad = str(cabecera.get("BUNIT", "")).replace(" ", "").lower()
                if unidad != "mjy/sr":
                    registro.warning("Unidad inesperada %r en %s; se omite.", unidad, imagen["url_recorte"])
                    continue
                wcs = ciencia_espectro.wcs_espacial(cabecera)
                x, y, jac = ciencia_espectro.posicion_y_jacobiano(wcs, ra, dec)
                lam, ancho = ciencia_espectro.longitud_de_onda(cabecera, tabla, x, y)
                meta.append({
                    "x": x, "y": y, "jac": jac, "lambda_um": lam, "ancho_um": ancho,
                    "area_sr": ciencia_espectro.area_pixel_sr(wcs),
                    "mjd": imagen["mjd"], "fecha": imagen["fecha_obs"], "detector": imagen["detector"],
                    "url": _url_base(imagen["url_recorte"]),
                })
                imgs.append(_a_lado_fijo(np.asarray(hdul["IMAGE"].data, dtype=np.float32)))
                varianzas.append(_a_lado_fijo(np.asarray(hdul["VARIANCE"].data, dtype=np.float32)))
        except Exception as error:  # un archivo dañado no debe tumbar todo el espectro
            registro.warning("No se pudo usar un recorte para el espectro: %r", error)
            completo = False
    vacio = np.empty((0, LADO_ESTAMPILLA, LADO_ESTAMPILLA), dtype=np.float32)
    return (
        meta,
        np.stack(imgs) if imgs else vacio,
        np.stack(varianzas) if varianzas else vacio,
        completo,
    )


def _clave_estampillas(ra: float, dec: float) -> str:
    tipo = f"espectro-v{VERSION_ESTAMPILLAS}-max{MAX_IMAGENES_POR_DETECTOR}"
    return cache.crear_clave(tipo, ra, dec, TAM_ESPECTRO_GRADOS)


def estampillas_en_cache(ra: float, dec: float) -> bool:
    """¿Ya quedó guardado el espectro de este punto? (lo usa scripts/precalcular.py)."""
    return cache.get_bytes(_clave_estampillas(ra, dec)) is not None


def estampillas(ra: float, dec: float) -> tuple[list[dict], np.ndarray, np.ndarray]:
    """Estampillas del punto (de la caché si ya se calcularon)."""
    imagenes = imagenes_de_zona(ra, dec, FOV_ZONA)
    if not imagenes:
        raise ErrorApi(404, "SPHEREx todavía no tiene imágenes de esa zona.")
    por_detector: dict[str, list[dict]] = {}
    for imagen in imagenes:
        por_detector.setdefault(imagen["detector"], []).append(imagen)
    elegidas = [i for det in sorted(por_detector) for i in _repartir(por_detector[det], MAX_IMAGENES_POR_DETECTOR)]

    clave = _clave_estampillas(ra, dec)
    with _candado(clave):
        meta = cache.get(clave)
        datos = cache.get_bytes(clave)
        if meta is not None and datos is not None:
            with np.load(io.BytesIO(datos), allow_pickle=False) as npz:
                return meta, npz["imagenes"].astype(float), npz["varianzas"].astype(float)
        meta, imgs, varianzas, completo = _calcular_estampillas(ra, dec, elegidas)
        if completo and meta:
            salida = io.BytesIO()
            np.savez_compressed(salida, imagenes=imgs, varianzas=varianzas)
            cache.set_bytes(clave, salida.getvalue())
            cache.set(clave, meta)
    if not meta:
        raise ErrorApi(504, "No se pudo descargar ninguna imagen de IRSA. " + MENSAJE_IRSA_CAIDO)
    return meta, imgs.astype(float), varianzas.astype(float)


def _ids_de_epoca(ra: float, dec: float) -> dict[str, str]:
    """URL base de cada imagen -> época ("E1"...), igual que en /epocas de su detector."""
    imagenes = imagenes_de_zona(ra, dec, FOV_ZONA)
    por_detector: dict[str, list[dict]] = {}
    for imagen in imagenes:
        por_detector.setdefault(imagen["detector"], []).append(imagen)
    ids = {}
    for lista in por_detector.values():
        for epoca in agrupar_por_epoca(lista):
            for imagen in epoca["imagenes"]:
                ids[_url_base(imagen["url_recorte"])] = epoca["id"]
    return ids


def _anio_decimal(mjd: float) -> float:
    """MJD -> año decimal, igual que demoSource.ts (2000 + (mjd - 51544.5) / 365.25)."""
    return 2000.0 + (mjd - 51544.5) / 365.25


def espectro(
    ra: float,
    dec: float,
    apertura: float = 18.0,
    anillo_in: float = 30.0,
    anillo_out: float = 50.0,
    restar_fondo: bool = True,
    pmra: float = 0.0,
    pmdec: float = 0.0,
    epoca: float | None = None,
) -> dict:
    """Espectro del punto (contrato: GET /spectrum). Radios en arcsec; pm en mas/año.

    Si se da `epoca` (año decimal de ra/dec) y movimiento propio, la apertura se coloca donde
    estaba la estrella en la fecha de cada imagen (Barnard's Star se mueve 10 arcsec por año).
    """
    if not 0 < apertura < anillo_in < anillo_out <= RADIO_MAX_ARCSEC:
        raise ErrorApi(
            400,
            f"Se necesita 0 < apertura < anillo interior < anillo exterior <= {RADIO_MAX_ARCSEC:g} arcsec.",
        )
    if settings.usar_mock:
        return mock.espectro()

    meta, imgs, varianzas = estampillas(ra, dec)
    ids = _ids_de_epoca(ra, dec)
    puntos = []
    for info, imagen, varianza in zip(meta, imgs, varianzas):
        x, y = info["x"], info["y"]
        if epoca is not None and (pmra or pmdec):
            anios = _anio_decimal(info["mjd"]) - epoca
            este, norte = pmra * anios / 1000, pmdec * anios / 1000  # arcsec
            (dxe, dxn), (dye, dyn) = info["jac"]
            x, y = x + dxe * este + dxn * norte, y + dye * este + dyn * norte
        suma, error, n_malos, n_apertura = ciencia_espectro.fotometria(
            imagen, varianza, x, y,
            apertura / ESCALA_ARCSEC_PX, anillo_in / ESCALA_ARCSEC_PX, anillo_out / ESCALA_ARCSEC_PX,
            restar_fondo,
        )
        if n_apertura == 0 or not np.isfinite(suma):
            continue
        factor = info["area_sr"] * ciencia_espectro.MJY_A_MILIJY
        puntos.append({
            "lambda_um": round(info["lambda_um"], 4),
            "ancho_um": round(info["ancho_um"], 4),
            "flujo": float(suma * factor),
            "error": float(error * factor) if np.isfinite(error) else None,
            "fecha": info["fecha"],
            "mjd": info["mjd"],
            "detector": info["detector"],
            "epoca": ids.get(info["url"], ""),
            "n_malos": n_malos,
        })
    if not puntos:
        raise ErrorApi(404, "No se pudo medir el brillo en ese punto (queda fuera de los recortes).")
    puntos.sort(key=lambda p: p["lambda_um"])
    return {
        "puntos": puntos,
        "unidad_flujo": "mJy",
        "meta": {
            "ra": ra, "dec": dec, "apertura_arcsec": apertura, "anillo_arcsec": [anillo_in, anillo_out],
            "restar_fondo": restar_fondo, "n_imagenes": len(meta),
        },
    }
