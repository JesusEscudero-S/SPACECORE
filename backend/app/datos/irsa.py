"""Consultas a IRSA (el archivo de la NASA/IPAC): qué imágenes de SPHEREx cubren un punto.

Usamos el servicio SIA (Simple Image Access) de IRSA, como en el tutorial oficial
"Introduction to SPHEREx Spectral Images":
https://caltech-ipac.github.io/irsa-tutorials/spherex-intro/

Nota: el otro camino oficial (consulta TAP sobre spherex.artifact y spherex.plane) devuelve lo
mismo, pero el 2026-11-14 tardaba más de 6 minutos y terminaba en error 502. SIA respondió en
unos 3 segundos. La única desventaja de SIA es que los datos nuevos tardan ~1 día en aparecer.

Para probar a mano (desde la carpeta backend, con el entorno .venv activado):

    python -m app.datos.irsa
"""

import logging
import time

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astroquery.ipac.irsa import Irsa
from pyvo.dal.exceptions import DALServiceError

from app.config import settings

registro = logging.getLogger(__name__)

DETECTORES = ("D1", "D2", "D3", "D4", "D5", "D6")

# Radio de búsqueda alrededor del punto. Con 1 segundo de arco (el valor del tutorial oficial)
# obtenemos las imágenes que contienen el punto.
RADIO_BUSQUEDA = 1 * u.arcsec

# IRSA a veces responde "502 Proxy Error" y al volver a preguntar funciona. Por eso reintentamos.
INTENTOS = 3
ESPERA_REINTENTO_S = 3


def _consultar_sia(centro: SkyCoord):
    """Pregunta al servicio SIA de IRSA, reintentando si el servidor falla."""
    for intento in range(1, INTENTOS + 1):
        try:
            return Irsa.query_sia(
                pos=(centro, RADIO_BUSQUEDA),
                collection=settings.lista_colecciones_spherex,
            )
        except (DALServiceError, OSError) as error:
            registro.warning("Consulta a IRSA: intento %s de %s falló: %r", intento, INTENTOS, error)
            if intento == INTENTOS:
                raise
            time.sleep(ESPERA_REINTENTO_S * intento)


def buscar_imagenes(ra: float, dec: float, fov_grados: float, detector: str) -> list[dict]:
    """Busca en IRSA las imágenes de SPHEREx que cubren el punto (ra, dec).

    Parámetros:
        ra, dec: coordenadas en grados decimales (ICRS).
        fov_grados: tamaño del recorte que se pedirá, en grados.
        detector: "D1" a "D6".

    Devuelve una lista ordenada de la imagen más antigua a la más reciente. Cada elemento es:
        {
            "url_recorte": dirección para descargar el recorte FITS de esa zona,
            "fecha_obs":   fecha de inicio de la exposición, texto ISO en UTC ("...Z"),
            "mjd":         la misma fecha como número (días, fecha juliana modificada),
            "detector":    el detector pedido,
            "coleccion":   colección de IRSA de donde viene ("spherex_dr1", "spherex_qr3"...),
        }

    Si SPHEREx no tiene imágenes de esa zona, devuelve una lista vacía.
    """
    observaciones = buscar_observaciones(ra, dec)
    return imagenes_de_detector(observaciones, ra, dec, fov_grados, detector)


def buscar_observaciones(ra: float, dec: float) -> list[dict]:
    """Pregunta a IRSA por TODAS las imágenes (los 6 detectores) que cubren el punto (ra, dec).

    Es la única función que habla con IRSA. Devuelve una lista ordenada por fecha; cada
    elemento es {"url_imagen", "mjd", "detector", "coleccion"}. Solo tiene textos y números,
    así que se puede guardar tal cual en la caché.
    """
    ra = float(ra)
    dec = float(dec)
    if not 0 <= ra < 360:
        raise ValueError(f"RA fuera de rango: {ra}. Debe estar entre 0 y 360 grados.")
    if not -90 <= dec <= 90:
        raise ValueError(f"Dec fuera de rango: {dec}. Debe estar entre -90 y 90 grados.")

    centro = SkyCoord(ra, dec, unit="deg", frame="icrs")
    tabla = _consultar_sia(centro)

    observaciones = []
    for fila in tabla:
        # energy_bandpassname viene como "SPHEREx-D2": nos quedamos con "D2".
        detector = str(fila["energy_bandpassname"]).replace("SPHEREx-", "")
        if detector not in DETECTORES:
            continue
        observaciones.append(
            {
                # access_url apunta a la imagen completa (2040 x 2040 píxeles).
                "url_imagen": str(fila["access_url"]),
                # t_min es el inicio de la exposición en días (fecha juliana modificada, MJD).
                "mjd": float(fila["t_min"]),
                "detector": detector,
                "coleccion": str(fila["obs_collection"]),
            }
        )
    observaciones.sort(key=lambda observacion: observacion["mjd"])
    return observaciones


def imagenes_de_detector(
    observaciones: list[dict], ra: float, dec: float, fov_grados: float, detector: str
) -> list[dict]:
    """De una lista de observaciones, arma las imágenes de UN detector con su URL de recorte.

    No habla con IRSA: solo filtra y arma direcciones.
    """
    ra = float(ra)
    dec = float(dec)
    fov_grados = float(fov_grados)
    if detector not in DETECTORES:
        raise ValueError(f"Detector inválido: {detector!r}. Debe ser uno de {DETECTORES}.")
    if fov_grados <= 0:
        raise ValueError(f"El campo de visión debe ser mayor que 0: {fov_grados}.")

    imagenes = []
    for observacion in observaciones:
        if observacion["detector"] != detector:
            continue
        fecha = Time(observacion["mjd"], format="mjd", scale="utc")
        imagenes.append(
            {
                # Al agregar ?center=...&size=... IRSA devuelve solo el recorte de esa zona.
                "url_recorte": f"{observacion['url_imagen']}?center={ra},{dec}d&size={fov_grados}",
                "fecha_obs": fecha.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "mjd": observacion["mjd"],
                "detector": detector,
                "coleccion": observacion["coleccion"],
            }
        )
    imagenes.sort(key=lambda imagen: imagen["mjd"])
    return imagenes


if __name__ == "__main__":
    # Prueba manual con Barnard's Star (coordenadas aproximadas).
    logging.basicConfig(level=logging.WARNING)
    inicio = time.time()
    resultado = buscar_imagenes(ra=269.4521, dec=4.6934, fov_grados=0.1, detector="D2")
    print(f"Imágenes encontradas: {len(resultado)} (en {time.time() - inicio:.1f} s)")
    if resultado:
        print("Primera:", resultado[0]["fecha_obs"], resultado[0]["coleccion"])
        print("        ", resultado[0]["url_recorte"])
        print("Última: ", resultado[-1]["fecha_obs"], resultado[-1]["coleccion"])
