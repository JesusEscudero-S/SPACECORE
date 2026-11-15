"""Une las piezas de datos y de ciencia para responder a los endpoints.

Camino completo de una búsqueda:

    IRSA (qué imágenes hay)  ->  agrupar por época  ->  descargar recortes
        ->  alinear (norte arriba)  ->  sumar por época  ->  PNG

Todo lo que tarda se guarda en la caché, así la segunda búsqueda igual es inmediata.
"""

import asyncio
import logging
import threading
import time

import httpx
from pyvo.dal.exceptions import DALServiceError

from app.ciencia.alinear import ESCALA_ARCSEC, alinear_recorte, crear_wcs_destino
from app.ciencia.coadd import coadd
from app.ciencia.imagen import a_data_url, a_png, limites_brillo
from app.datos import cache, irsa
from app.datos.descargas import abrir_recorte, descargar_recortes
from app.datos.epocas import agrupar_por_epoca
from app.errores import ErrorApi

registro = logging.getLogger(__name__)

# Los recortes de IRSA vienen girados. Los pedimos 1.5 veces más grandes que el campo de
# visión para que, al enderezarlos, cubran todo el cuadro (hasta las esquinas).
MARGEN_RECORTE = 1.5

MENSAJE_IRSA = "El archivo de la NASA (IRSA) no respondió. Intenta de nuevo en un momento."
MENSAJE_SIN_DATOS = "SPHEREx todavía no tiene datos aquí."

# Candados: si llegan varias peticiones iguales a la vez, la primera hace el trabajo y las
# demás esperan y lo toman de la caché (así no le pedimos lo mismo a IRSA varias veces).
_candado_irsa = threading.Lock()
_candado_frames = threading.Lock()


def _observaciones(ra: float, dec: float) -> list[dict]:
    """Todas las observaciones (los 6 detectores) de un punto, desde la caché o desde IRSA."""
    clave = cache.crear_clave("observaciones", ra, dec)
    with _candado_irsa:
        guardadas = cache.get(clave)
        if guardadas is not None:
            return guardadas
        try:
            observaciones = irsa.buscar_observaciones(ra, dec)
        except (DALServiceError, OSError) as error:
            registro.error("IRSA falló al buscar observaciones: %r", error)
            raise ErrorApi(504, MENSAJE_IRSA) from error
        cache.set(clave, observaciones)
        return observaciones


def obtener_epocas(ra: float, dec: float, fov: float, det: str) -> list[dict]:
    """Las épocas de un punto para un detector (cada una con su lista de imágenes).

    Lanza ErrorApi 404 si SPHEREx no tiene imágenes de esa zona con ese detector.
    """
    observaciones = _observaciones(ra, dec)
    imagenes = irsa.imagenes_de_detector(observaciones, ra, dec, fov * MARGEN_RECORTE, det)
    if not imagenes:
        raise ErrorApi(404, MENSAJE_SIN_DATOS)
    return agrupar_por_epoca(imagenes)


def obtener_frames(ra: float, dec: float, fov: float, det: str) -> dict:
    """La respuesta completa de /frames: un PNG por época y los datos de la imagen."""
    clave = cache.crear_clave("frames", ra, dec, fov, det)
    with _candado_frames:
        guardado = cache.get(clave)
        if guardado is not None:
            return guardado

        inicio = time.time()
        epocas = obtener_epocas(ra, dec, fov, det)

        # 1) Descargar todos los recortes de todas las épocas de una sola vez.
        urls = [imagen["url_recorte"] for epoca in epocas for imagen in epoca["imagenes"]]
        try:
            recortes = asyncio.run(descargar_recortes(urls))
        except httpx.HTTPError as error:
            raise ErrorApi(504, MENSAJE_IRSA) from error
        recorte_de = dict(zip(urls, recortes))

        # 2) Por cada época: alinear sus imágenes a la misma malla y sumarlas.
        wcs_destino, forma = crear_wcs_destino(ra, dec, fov)
        sumadas = []  # lista de (época, imagen sumada)
        for epoca in epocas:
            alineadas = []
            for imagen in epoca["imagenes"]:
                datos = recorte_de.get(imagen["url_recorte"])
                if datos is None:
                    continue  # esa descarga falló: seguimos con las demás
                try:
                    with abrir_recorte(datos) as hdul:
                        alineadas.append(alinear_recorte(hdul, wcs_destino, forma))
                except Exception as error:  # un recorte dañado no debe tumbar toda la búsqueda
                    registro.warning("No se pudo procesar %s: %r", imagen["url_recorte"], error)
            try:
                sumadas.append((epoca, coadd(alineadas)))
            except ValueError:
                registro.warning("La época %s quedó sin imágenes útiles.", epoca["id"])

        if not sumadas:
            raise ErrorApi(504, MENSAJE_IRSA)

        # 3) Mismos límites de brillo para todas las épocas, y a PNG.
        vmin, vmax = limites_brillo([imagen for _, imagen in sumadas])
        respuesta = {
            "frames": [
                {
                    "epoca": epoca["id"],
                    "fecha": epoca["fecha"],
                    "png": a_data_url(a_png(imagen, vmin, vmax)),
                }
                for epoca, imagen in sumadas
            ],
            "meta": {
                "detector": det,
                "fov_grados": fov,
                "ra": ra,
                "dec": dec,
                "tamano_px": forma[0],
                "escala_arcsec_px": ESCALA_ARCSEC,
            },
        }
        cache.set(clave, respuesta)
        registro.info(
            "/frames ra=%s dec=%s fov=%s det=%s: %s épocas, %s recortes, %.1f s",
            ra, dec, fov, det, len(sumadas), len(urls), time.time() - inicio,
        )
        return respuesta
