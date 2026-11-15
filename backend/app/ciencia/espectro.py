"""Espectro de un punto con imágenes de SPHEREx (T36): longitud de onda + fotometría.

Cómo funciona SPHEREx: cada píxel del detector ve una longitud de onda distinta (un filtro
que cambia de color a lo largo del detector). Por eso cada imagen que cubre una estrella mide
su brillo en UNA longitud de onda; juntando cientos de imágenes sale el espectro.

Longitud de onda de un píxel: el recorte trae un WCS alterno 'W' en la cabecera de IMAGE y una
tabla (extensión WCS-WAVE) con la longitud de onda en una malla de 11x11 puntos del detector.
Verificado con datos reales (2026-11-15, Barnard's Star): la tabla es IDÉNTICA en todos los
recortes de un mismo detector y versión de proceso; lo único que cambia de un recorte a otro es
CRPIX1W/CRPIX2W en la cabecera de IMAGE. Por eso la tabla se baja una sola vez por detector
(la tabla va al final del archivo, después de ~3.8 MB de PSF) y de cada imagen basta el
recorte corto (~80 KB). Es el mismo cálculo del tutorial oficial de IRSA "spherex-cutouts":
    WCS(cabecera, fobj=hdul, key="W"); wcs.sip = None; wcs.pixel_to_world(x, y)

Fotometría: suma de los píxeles dentro de un círculo (apertura) menos el fondo (mediana de un
anillo alrededor). IMAGE viene en MJy/sr; multiplicando por el área del píxel (sr) queda en
MJy, y por 1e9 en mJy. Es fotometría de apertura simple, sin corrección por la PSF: sirve
para ver la forma del espectro, no es una medición calibrada al 1 %.
"""

import io
import logging
import warnings
from contextlib import contextmanager

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning

# MJy -> mJy
MJY_A_MILIJY = 1e9


@contextmanager
def _sin_avisos():
    """Astropy avisa mucho al leer el WCS alterno 'W' (detalles de formato sin efecto)."""
    # Además del aviso, astropy escribe un INFO largo ("Inconsistent SIP distortion...") por
    # cada imagen: las cabeceras traen coeficientes SIP y CTYPE sin "-SIP". No afecta el
    # resultado (al WCS de longitud de onda se le quita el SIP, como en el tutorial de IRSA).
    registro_astropy = logging.getLogger("astropy")
    nivel = registro_astropy.level
    registro_astropy.setLevel(logging.WARNING)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FITSFixedWarning)
            warnings.simplefilter("ignore", UserWarning)
            yield
    finally:
        registro_astropy.setLevel(nivel)


def tabla_a_bytes(tabla: fits.BinTableHDU) -> bytes:
    """Guarda la extensión WCS-WAVE como un FITS pequeño (para la caché)."""
    salida = io.BytesIO()
    fits.HDUList([fits.PrimaryHDU(), fits.BinTableHDU(data=tabla.data, header=tabla.header)]).writeto(salida)
    return salida.getvalue()


def bytes_a_tabla(datos: bytes) -> fits.BinTableHDU:
    with fits.open(io.BytesIO(datos)) as hdul:
        tabla = hdul[1]
        return fits.BinTableHDU(data=tabla.data.copy(), header=tabla.header.copy(), name="WCS-WAVE")


def longitud_de_onda(cabecera: fits.Header, tabla: fits.BinTableHDU, x: float, y: float) -> tuple[float, float]:
    """Longitud de onda central y ancho de banda (micras) en el píxel (x, y) del recorte.

    x, y empiezan en 0 (como en NumPy). `cabecera` es la de IMAGE de ESE recorte y `tabla` la
    extensión WCS-WAVE de cualquier recorte del mismo detector.
    """
    hdul = fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(header=cabecera, name="IMAGE"), tabla])
    with _sin_avisos():
        espectral = WCS(cabecera, fobj=hdul, key="W")
        espectral.sip = None
        lam, ancho = espectral.pixel_to_world(x, y)
    return float(u.Quantity(lam).to_value(u.um)), float(u.Quantity(ancho).to_value(u.um))


def wcs_espacial(cabecera: fits.Header) -> WCS:
    with _sin_avisos():
        return WCS(cabecera, naxis=2)


def posicion_y_jacobiano(wcs: WCS, ra: float, dec: float) -> tuple[float, float, list[list[float]]]:
    """Píxel (x, y) del punto y cuántos píxeles se mueve por cada arcsec al este y al norte.

    Devuelve (x, y, jac) con jac = [[dx/dEste, dx/dNorte], [dy/dEste, dy/dNorte]] (px/arcsec).
    Sirve para mover la apertura según el movimiento propio sin guardar toda la cabecera.
    """
    paso = 5.0  # arcsec
    cos_dec = np.cos(np.radians(dec)) or 1.0
    puntos = SkyCoord(
        [ra, ra + paso / 3600 / cos_dec, ra],
        [dec, dec, dec + paso / 3600],
        unit="deg",
    )
    xs, ys = wcs.world_to_pixel(puntos)
    jac = [
        [float((xs[1] - xs[0]) / paso), float((xs[2] - xs[0]) / paso)],
        [float((ys[1] - ys[0]) / paso), float((ys[2] - ys[0]) / paso)],
    ]
    return float(xs[0]), float(ys[0]), jac


def area_pixel_sr(wcs: WCS) -> float:
    """Área de un píxel en estereorradianes (en el centro del recorte).

    Los recortes de SPHEREx traen CUNIT = 'deg'; si un WCS no trae unidades, se asumen grados.
    """
    area = u.Quantity(wcs.proj_plane_pixel_area())
    if area.unit == u.dimensionless_unscaled:
        area = area.value * u.deg**2
    return float(area.to_value(u.sr))


def fotometria(
    imagen: np.ndarray,
    varianza: np.ndarray,
    x: float,
    y: float,
    r_apertura: float,
    r_anillo_in: float,
    r_anillo_out: float,
    restar_fondo: bool = True,
) -> tuple[float, float, int, int]:
    """Fotometría de apertura. Radios en píxeles; x, y empiezan en 0.

    Devuelve (suma, error, n_malos, n_apertura), suma y error en las unidades de la imagen
    por píxel (MJy/sr · px). n_malos = píxeles sin dato (NaN) dentro de la apertura: en
    estrellas muy brillantes el centro satura y SPHEREx lo deja en NaN, así que la suma queda
    por DEBAJO del valor real. n_apertura = 0 si la apertura cae fuera del recorte.
    """
    imagen = np.asarray(imagen, dtype=float)
    varianza = np.asarray(varianza, dtype=float)
    filas, columnas = np.mgrid[: imagen.shape[0], : imagen.shape[1]]
    radio = np.hypot(columnas - x, filas - y)
    en_apertura = radio <= r_apertura
    n_apertura = int(en_apertura.sum())
    if n_apertura == 0:
        return float("nan"), float("nan"), 0, 0

    valores = imagen[en_apertura]
    validos = np.isfinite(valores)
    n_malos = int((~validos).sum())

    fondo = 0.0
    if restar_fondo:
        anillo = imagen[(radio >= r_anillo_in) & (radio <= r_anillo_out)]
        anillo = anillo[np.isfinite(anillo)]
        if anillo.size:
            fondo = float(np.median(anillo))

    suma = float(np.sum(valores[validos] - fondo)) if validos.any() else float("nan")
    var = varianza[en_apertura][validos]
    var = var[np.isfinite(var) & (var >= 0)]
    error = float(np.sqrt(var.sum())) if var.size else float("nan")
    return suma, error, n_malos, n_apertura
