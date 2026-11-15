"""Pruebas de app/ciencia/imagen.py con datos falsos (no usan internet).

Para correrlas (desde la carpeta backend, con el entorno .venv activado):

    python -m unittest discover -v
"""

import io
import unittest

import numpy as np
from PIL import Image

from app.ciencia.imagen import a_data_url, a_png, limites_brillo


def _abrir(png: bytes) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(png)))


class PruebasImagen(unittest.TestCase):
    def test_png_respeta_el_tamano_real(self):
        datos = np.zeros((59, 53))  # 59 filas x 53 columnas
        pixeles = _abrir(a_png(datos, vmin=0, vmax=1))
        self.assertEqual(pixeles.shape, (59, 53))
        self.assertEqual(pixeles.dtype, np.uint8)

    def test_png_se_puede_redimensionar(self):
        pixeles = _abrir(a_png(np.zeros((59, 53)), vmin=0, vmax=1, tamano=256))
        self.assertEqual(pixeles.shape, (256, 256))

    def test_negro_blanco_y_valores_fuera_de_rango(self):
        datos = np.array([[0.0, 10.0], [-5.0, 99.0]])
        pixeles = _abrir(a_png(datos, vmin=0, vmax=10))
        # La imagen se voltea verticalmente: la fila 0 de los datos queda abajo.
        self.assertEqual(pixeles[1, 0], 0)      # vmin -> negro
        self.assertEqual(pixeles[1, 1], 255)    # vmax -> blanco
        self.assertEqual(pixeles[0, 0], 0)      # menor que vmin -> negro
        self.assertEqual(pixeles[0, 1], 255)    # mayor que vmax -> blanco

    def test_nan_se_pinta_como_fondo(self):
        datos = np.array([[np.nan, 10.0], [np.inf, 0.0]])
        pixeles = _abrir(a_png(datos, vmin=0, vmax=10))
        self.assertEqual(pixeles[1, 0], 0)
        self.assertEqual(pixeles[0, 0], 0)

    def test_invertir(self):
        datos = np.array([[0.0, 10.0]])
        pixeles = _abrir(a_png(datos, vmin=0, vmax=10, invertir=True))
        self.assertEqual(pixeles[0, 0], 255)
        self.assertEqual(pixeles[0, 1], 0)

    def test_el_norte_queda_arriba(self):
        datos = np.zeros((4, 4))
        datos[3, :] = 10.0  # la última fila del FITS es la de más al norte
        pixeles = _abrir(a_png(datos, vmin=0, vmax=10))
        self.assertTrue((pixeles[0, :] == 255).all())
        self.assertTrue((pixeles[3, :] == 0).all())

    def test_limites_comunes_ignoran_nan(self):
        a = np.array([[0.0, 1.0], [2.0, np.nan]])
        b = np.array([[3.0, 4.0], [5.0, 100.0]])
        vmin, vmax = limites_brillo([a, b], percentil_bajo=0, percentil_alto=100)
        self.assertEqual(vmin, 0.0)
        self.assertEqual(vmax, 100.0)

    def test_limites_con_imagen_plana_o_vacia(self):
        vmin, vmax = limites_brillo([np.full((3, 3), 7.0)])
        self.assertLess(vmin, vmax)
        self.assertEqual(limites_brillo([]), (0.0, 1.0))
        self.assertEqual(limites_brillo([np.full((2, 2), np.nan)]), (0.0, 1.0))

    def test_data_url(self):
        png = a_png(np.zeros((2, 2)), vmin=0, vmax=1)
        url = a_data_url(png)
        self.assertTrue(url.startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
