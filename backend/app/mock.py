"""Datos FALSOS para probar la API sin IRSA (T31). Se activan con USAR_MOCK=1.

Tienen el mismo formato que los reales (docs/api.md): 3 épocas separadas ~6 meses y, en cada
imagen, unas estrellas fijas más una que se mueve hacia el norte (como Barnard's Star).
NO son datos científicos: solo sirven para que la página se pueda probar.
"""

import numpy as np

from app.ciencia.alinear import tamano_malla
from app.datos.epocas import agrupar_por_epoca

# MJD aproximados de agosto 2025, marzo 2026 y agosto 2026 (como las épocas reales de Barnard).
_MJD_EPOCAS = (60900.0, 61110.0, 61270.0)


def epocas(det: str) -> list[dict]:
    imagenes = []
    for mjd in _MJD_EPOCAS:
        for k in range(4):  # 4 imágenes por época, tomadas en días seguidos
            imagenes.append({"mjd": mjd + k, "fecha_obs": "", "detector": det, "url_recorte": ""})
    return agrupar_por_epoca(imagenes)


def pila(lista: list[dict], fov: float) -> np.ndarray:
    n = tamano_malla(fov)
    y, x = np.mgrid[0:n, 0:n]
    generador = np.random.default_rng(42)
    fijas = generador.uniform(0, n, size=(8, 2))
    imagenes = []
    for numero, _ in enumerate(lista):
        imagen = generador.normal(0, 0.05, size=(n, n))
        for fx, fy in fijas:
            imagen += 2 * np.exp(-((x - fx) ** 2 + (y - fy) ** 2) / (2 * 1.2**2))
        # La estrella que se mueve: 2 píxeles hacia el norte (arriba) por época.
        cx, cy = n / 2, n / 2 + 2 * numero
        imagen += 5 * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * 1.2**2))
        imagenes.append(imagen)
    return np.stack(imagenes)
