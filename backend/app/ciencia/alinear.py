"""Alinea los recortes de SPHEREx en una misma malla (T23) y suma los de cada época (T22).

Por qué hace falta:
- Cada recorte de IRSA viene GIRADO (su WCS es TAN-SIP con el detector inclinado) y no queda
  centrado exacto en el punto pedido. Si animamos los recortes tal cual, las estrellas
  "bailan" de un cuadro a otro aunque no se muevan.
- Solución (T23): definimos UNA malla común (la "malla objetivo"): centrada en (ra, dec), con
  el norte arriba, el este a la izquierda y píxeles de 6.15 arcsec. Cada recorte se reproyecta
  a esa malla con la librería `reproject`. Así todas las épocas quedan encimadas igual.
- Después (T22) juntamos las imágenes de una misma época en una sola, más limpia. Usamos la
  MEDIANA píxel a píxel: quita rayos cósmicos y píxeles malos que salen en una sola imagen.

Nota científica: dentro de una época, cada imagen de un detector se tomó en una longitud de
onda un poco distinta (SPHEREx usa un filtro que cambia de color a lo largo del detector).
Por eso, antes de combinar, a cada imagen le restamos su fondo (la mediana de sus píxeles).
El resultado sirve para VER y comparar épocas; no es una fotometría calibrada.

Para probar (desde la carpeta backend):

    python -m unittest tests.test_alinear -v
"""

import warnings

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning
from reproject import reproject_interp

# Tamaño de píxel de SPHEREx: 6.15 segundos de arco (columna s_pixel_scale del servicio SIA de
# IRSA, verificado con datos reales el 2026-11-14). Es también la escala de los PNG (contrato 1.1).
ESCALA_ARCSEC_PX = 6.15


def tamano_malla(fov_grados: float, escala_arcsec: float = ESCALA_ARCSEC_PX) -> int:
    """Ancho (y alto) en píxeles de la malla: fov en arcsec dividido entre la escala.

    Ejemplo: fov = 0.1 grados = 360 arcsec; 360 / 6.15 = 58.5 -> 59 píxeles.
    """
    return max(1, int(round(float(fov_grados) * 3600 / escala_arcsec)))


def malla_objetivo(
    ra: float, dec: float, fov_grados: float, escala_arcsec: float = ESCALA_ARCSEC_PX
) -> tuple[WCS, tuple[int, int]]:
    """Crea la malla común: un WCS con el norte arriba y el este a la izquierda.

    Devuelve (wcs, forma), donde forma = (alto, ancho) en píxeles, como en NumPy.
    """
    n = tamano_malla(fov_grados, escala_arcsec)
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [float(ra), float(dec)]
    # El píxel de referencia es el centro de la imagen (en FITS los píxeles se cuentan desde 1).
    wcs.wcs.crpix = [(n + 1) / 2, (n + 1) / 2]
    escala_grados = escala_arcsec / 3600
    # CDELT1 negativo = el este queda a la izquierda (la RA crece hacia la izquierda).
    # CDELT2 positivo = el norte queda arriba (en FITS la fila 0 es la de abajo).
    wcs.wcs.cdelt = [-escala_grados, escala_grados]
    wcs.wcs.cunit = ["deg", "deg"]
    return wcs, (n, n)


def wcs_de_cabecera(cabecera: fits.Header) -> WCS:
    """Lee el WCS espacial de la cabecera de IMAGE (incluye la distorsión SIP).

    La cabecera trae además un WCS alterno 'W' (longitud de onda); aquí usamos el principal.
    """
    with warnings.catch_warnings():
        # Astropy avisa de detalles menores del formato; no afectan el resultado.
        warnings.simplefilter("ignore", FITSFixedWarning)
        return WCS(cabecera, naxis=2)


def alinear(
    datos: np.ndarray, wcs_origen: WCS, wcs_destino: WCS, forma: tuple[int, int]
) -> np.ndarray:
    """Reproyecta una imagen a la malla objetivo.

    Los píxeles de la malla que el recorte no cubre quedan como NaN (sin dato).
    """
    datos = np.asarray(datos, dtype=float)
    resultado = reproject_interp(
        (datos, wcs_origen), wcs_destino, shape_out=forma, return_footprint=False
    )
    return np.asarray(resultado, dtype=float)


def alinear_recorte(hdul: fits.HDUList, wcs_destino: WCS, forma: tuple[int, int]) -> np.ndarray:
    """Toma un recorte de SPHEREx ya abierto y devuelve su IMAGE alineada a la malla."""
    imagen = hdul["IMAGE"]
    return alinear(imagen.data, wcs_de_cabecera(imagen.header), wcs_destino, forma)


def restar_fondo(datos: np.ndarray) -> np.ndarray:
    """Resta el fondo de la imagen (la mediana de los píxeles con dato)."""
    datos = np.asarray(datos, dtype=float)
    validos = datos[np.isfinite(datos)]
    if validos.size == 0:
        return datos
    return datos - float(np.median(validos))


def sumar_epoca(alineadas: list[np.ndarray]) -> np.ndarray:
    """Combina las imágenes alineadas de UNA época en una sola (co-add, T22).

    A cada imagen se le resta su fondo y luego se toma la mediana píxel a píxel, ignorando los
    NaN. Si en un píxel ninguna imagen tiene dato, queda NaN.
    """
    if not alineadas:
        raise ValueError("No hay imágenes para combinar.")
    pila = np.stack([restar_fondo(imagen) for imagen in alineadas])
    with warnings.catch_warnings():
        # nanmedian avisa "All-NaN slice" en píxeles sin ningún dato: es lo esperado.
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmedian(pila, axis=0)
