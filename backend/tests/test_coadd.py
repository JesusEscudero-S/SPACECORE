"""Pruebas de app/ciencia/coadd.py con datos falsos (no usan internet).

Para correrlas (desde la carpeta backend, con el entorno .venv activado):

    python -m unittest discover -v
"""

import unittest

import numpy as np

from app.ciencia.coadd import coadd


class PruebasCoadd(unittest.TestCase):
    def test_la_mediana_ignora_un_pixel_anomalo(self):
        buenas = [np.full((4, 4), 5.0) for _ in range(4)]
        mala = np.full((4, 4), 5.0)
        mala[1, 2] = 9999.0  # un rayo cósmico en una sola exposición
        resultado = coadd(buenas + [mala], restar_fondo=False)
        self.assertTrue(np.allclose(resultado, 5.0))

    def test_restar_fondo_hace_comparables_las_imagenes(self):
        estrella = np.zeros((5, 5))
        estrella[2, 2] = 10.0
        # La misma escena con tres niveles de fondo distintos.
        imagenes = [estrella + fondo for fondo in (1.0, 50.0, 300.0)]
        resultado = coadd(imagenes)
        self.assertAlmostEqual(float(resultado[2, 2]), 10.0)
        self.assertAlmostEqual(float(resultado[0, 0]), 0.0)

    def test_nan_en_una_imagen_no_estropea_el_pixel(self):
        a = np.full((3, 3), 2.0)
        b = np.full((3, 3), 2.0)
        b[0, 0] = np.nan
        resultado = coadd([a, b], restar_fondo=False)
        self.assertEqual(float(resultado[0, 0]), 2.0)

    def test_pixel_sin_dato_en_ninguna_imagen_queda_nan(self):
        a = np.full((3, 3), 2.0)
        a[1, 1] = np.nan
        resultado = coadd([a, a.copy()], restar_fondo=False)
        self.assertTrue(np.isnan(resultado[1, 1]))
        self.assertEqual(float(resultado[0, 0]), 2.0)

    def test_una_sola_imagen(self):
        imagen = np.arange(9.0).reshape(3, 3)
        self.assertTrue(np.allclose(coadd([imagen], restar_fondo=False), imagen))

    def test_descarta_imagenes_vacias_y_falla_si_no_queda_ninguna(self):
        vacia = np.full((3, 3), np.nan)
        buena = np.full((3, 3), 4.0)
        self.assertTrue(np.allclose(coadd([vacia, buena], restar_fondo=False), 4.0))
        with self.assertRaises(ValueError):
            coadd([vacia])
        with self.assertRaises(ValueError):
            coadd([])


if __name__ == "__main__":
    unittest.main()
