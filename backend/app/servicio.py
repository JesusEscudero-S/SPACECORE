"""Une todas las piezas del backend para responder a los endpoints.

El camino de una búsqueda es:

    buscar_imagenes (IRSA, T10)  ->  agrupar_por_epoca (T12)  ->  descargar_recortes (T11)
    ->  alinear a la malla común (T23)  ->  sumar cada época (T22)  ->  PNG (T21)

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
            400, f"El campo de visión máximo es {settings.fov_max} grados; pediste {fov}."
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

