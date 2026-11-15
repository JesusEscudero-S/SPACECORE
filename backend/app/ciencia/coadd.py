"""Suma (co-add) las imágenes de una misma época para reducir el ruido.

Varias exposiciones de la misma zona, tomadas con días de diferencia, se combinan en una sola
imagen más limpia. Las imágenes deben estar ya alineadas a la misma malla (ver alinear.py).

Usamos la MEDIANA píxel a píxel en lugar del promedio: si en una exposición un píxel salió mal
(un rayo cósmico, un píxel caliente), la mediana lo ignora sola.

Nota sobre las banderas (FLAGS): no las usamos para descartar píxeles. La bandera SOURCE
("píxel de una fuente conocida") viene encendida en casi toda la imagen, y las de saturación
se encienden justo sobre las estrellas brillantes que queremos ver.
"""

import warnings

import numpy as np


def coadd(imagenes: list[np.ndarray], restar_fondo: bool = True) -> np.ndarray:
    """Combina imágenes alineadas (todas del mismo tamaño) en una sola.

    Parámetros:
        imagenes: lista de matrices 2D del mismo tamaño. Pueden traer NaN.
        restar_fondo: si es True, a cada imagen se le resta primero su brillo de fondo (su
            mediana). El fondo cambia de una exposición a otra (luz zodiacal), y sin restarlo
            las imágenes no serían comparables.

    Devuelve una matriz 2D. Un píxel queda en NaN solo si ninguna imagen tenía dato ahí.
    """
    # Descartamos las imágenes que no tienen ni un solo dato válido.
    utiles = [np.asarray(i, dtype=float) for i in imagenes]
    utiles = [i for i in utiles if np.isfinite(i).any()]
    if not utiles:
        raise ValueError("No hay imágenes con datos para combinar.")

    pila = np.stack(utiles)  # forma: (n_imagenes, filas, columnas)
    pila[~np.isfinite(pila)] = np.nan

    if restar_fondo:
        fondos = np.nanmedian(pila, axis=(1, 2), keepdims=True)
        pila = pila - fondos

    with warnings.catch_warnings():
        # NumPy avisa cuando un píxel es NaN en todas las imágenes; ese caso es válido.
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return np.nanmedian(pila, axis=0)
