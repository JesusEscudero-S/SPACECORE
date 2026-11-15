"""Alinea las imágenes: las pone todas en la misma malla, con el norte arriba.

Los recortes de SPHEREx llegan girados (cada exposición con su propio ángulo) y un poco
descentrados. Para animarlos sin que las estrellas fijas "brinquen", proyectamos cada uno sobre
una malla común: centrada en el punto pedido, norte arriba, este a la izquierda y con el tamaño
de píxel de SPHEREx.

Un WCS (World Coordinate System) es la "receta" que dice a qué punto del cielo corresponde cada
píxel de una imagen.
"""

import warnings

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from reproject import reproject_interp

# Tamaño de píxel de SPHEREx en segundos de arco (verificado con IRSA el 2026-11-14).
ESCALA_ARCSEC = 6.15


def lado_en_pixeles(fov_grados: float, escala_arcsec: float = ESCALA_ARCSEC) -> int:
    """Cuántos píxeles mide de lado una imagen con ese campo de visión, a escala real."""
    return max(1, round(float(fov_grados) * 3600 / escala_arcsec))


def crear_wcs_destino(
    ra: float, dec: float, fov_grados: float, escala_arcsec: float = ESCALA_ARCSEC
) -> tuple[WCS, tuple[int, int]]:
    """Crea la malla común: centrada en (ra, dec), norte arriba y este a la izquierda.

    Devuelve (wcs_destino, forma), donde forma = (filas, columnas) de la imagen final.
    """
    lado = lado_en_pixeles(fov_grados, escala_arcsec)
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]  # proyección tangente (la habitual)
    wcs.wcs.cunit = ["deg", "deg"]
    wcs.wcs.crval = [float(ra), float(dec)]  # el punto del cielo que va en el centro
    wcs.wcs.crpix = [(lado + 1) / 2, (lado + 1) / 2]  # el píxel central (FITS cuenta desde 1)
    # Escala por píxel en grados. El signo negativo en RA hace que el este quede a la izquierda.
    wcs.wcs.cdelt = [-escala_arcsec / 3600, escala_arcsec / 3600]
    return wcs, (lado, lado)


def reproyectar(
    datos: np.ndarray, wcs_original: WCS, wcs_destino: WCS, forma: tuple[int, int]
) -> np.ndarray:
    """Proyecta una imagen sobre la malla destino. Lo que quede sin cubrir se llena con NaN."""
    resultado, cobertura = reproject_interp(
        (np.asarray(datos, dtype=float), wcs_original),
        wcs_destino,
        shape_out=forma,
        order="bilinear",
    )
    resultado[cobertura == 0] = np.nan
    return resultado


def alinear_recorte(hdul: fits.HDUList, wcs_destino: WCS, forma: tuple[int, int]) -> np.ndarray:
    """Toma un recorte de SPHEREx ya abierto y devuelve su imagen alineada a la malla destino.

    El header de IMAGE trae dos WCS: el espacial (el que usamos aquí) y uno alterno "W" para la
    longitud de onda. WCS(header) lee el espacial.
    """
    hdu = hdul["IMAGE"]
    with warnings.catch_warnings():
        # Astropy avisa de detalles del header que no nos afectan.
        warnings.simplefilter("ignore")
        wcs_original = WCS(hdu.header)
    return reproyectar(hdu.data, wcs_original, wcs_destino, forma)
