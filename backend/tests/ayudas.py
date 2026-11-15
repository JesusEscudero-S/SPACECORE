"""Funciones de apoyo para las pruebas: fabrican datos falsos parecidos a los de SPHEREx."""

import io

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

ESCALA_GRADOS = 6.15 / 3600


def wcs_girado(ra: float, dec: float, lado: int, giro_grados: float) -> WCS:
    """Un WCS centrado en (ra, dec) pero girado, como los recortes reales de SPHEREx."""
    angulo = np.radians(giro_grados)
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.cunit = ["deg", "deg"]
    wcs.wcs.crval = [ra, dec]
    wcs.wcs.crpix = [(lado + 1) / 2, (lado + 1) / 2]
    wcs.wcs.cdelt = [-ESCALA_GRADOS, ESCALA_GRADOS]
    wcs.wcs.pc = [[np.cos(angulo), -np.sin(angulo)], [np.sin(angulo), np.cos(angulo)]]
    return wcs


def imagen_con_estrella(wcs: WCS, lado: int, ra: float, dec: float, fondo: float = 1.0) -> np.ndarray:
    """Una imagen plana con una "estrella" (mancha gaussiana) en la posición (ra, dec) del cielo."""
    x, y = wcs.world_to_pixel_values(ra, dec)
    filas, columnas = np.mgrid[0:lado, 0:lado]
    estrella = 100.0 * np.exp(-((columnas - x) ** 2 + (filas - y) ** 2) / (2 * 1.5**2))
    return (fondo + estrella).astype(np.float32)


def recorte_falso(ra: float, dec: float, lado: int = 90, giro_grados: float = 180.0, fondo: float = 1.0) -> bytes:
    """Los bytes de un FITS parecido a un recorte de SPHEREx, con una estrella en (ra, dec)."""
    wcs = wcs_girado(ra, dec, lado, giro_grados)
    datos = imagen_con_estrella(wcs, lado, ra, dec, fondo)
    cabecera = wcs.to_header()
    hdul = fits.HDUList(
        [
            fits.PrimaryHDU(),
            fits.ImageHDU(datos, header=cabecera, name="IMAGE"),
            fits.ImageHDU(np.zeros((lado, lado), dtype=np.int32), header=cabecera, name="FLAGS"),
        ]
    )
    salida = io.BytesIO()
    hdul.writeto(salida)
    return salida.getvalue()
