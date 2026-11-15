"""Pruebas de app/ciencia/alinear.py con datos falsos (no usan internet).

Para correrlas (desde la carpeta backend, con el entorno .venv activado):

    python -m unittest discover -v
"""

import unittest

import numpy as np

from app.ciencia.alinear import alinear_recorte, crear_wcs_destino, lado_en_pixeles, reproyectar
from app.datos.descargas import abrir_recorte
from tests.ayudas import imagen_con_estrella, recorte_falso, wcs_girado

RA, DEC = 269.4461, 4.7705


class PruebasAlinear(unittest.TestCase):
    def test_lado_en_pixeles(self):
        self.assertEqual(lado_en_pixeles(0.1), 59)   # 360 arcsec / 6.15
        self.assertEqual(lado_en_pixeles(0.5), 293)
        self.assertEqual(lado_en_pixeles(0.0001), 1)  # nunca menos de 1

    def test_malla_centrada_norte_arriba_este_izquierda(self):
        wcs, forma = crear_wcs_destino(RA, DEC, 0.1)
        self.assertEqual(forma, (59, 59))
        centro = (forma[0] - 1) / 2
        ra_c, dec_c = wcs.pixel_to_world_values(centro, centro)
        self.assertAlmostEqual(float(ra_c), RA, places=6)
        self.assertAlmostEqual(float(dec_c), DEC, places=6)
        # Una fila más arriba en el FITS = más al norte (mayor Dec).
        self.assertGreater(float(wcs.pixel_to_world_values(centro, centro + 1)[1]), DEC)
        # Una columna más a la derecha = más al oeste (menor RA): el este queda a la izquierda.
        self.assertLess(float(wcs.pixel_to_world_values(centro + 1, centro)[0]), RA)

    def test_la_estrella_cae_en_el_centro_sin_importar_el_giro(self):
        wcs_destino, forma = crear_wcs_destino(RA, DEC, 0.1)
        centro = (forma[0] - 1) // 2
        for giro in (0, 37, 90, 181):
            wcs_original = wcs_girado(RA, DEC, 90, giro)
            imagen = imagen_con_estrella(wcs_original, 90, RA, DEC)
            alineada = reproyectar(imagen, wcs_original, wcs_destino, forma)
            fila, columna = np.unravel_index(np.nanargmax(alineada), alineada.shape)
            self.assertLessEqual(abs(fila - centro), 1, f"giro {giro}")
            self.assertLessEqual(abs(columna - centro), 1, f"giro {giro}")

    def test_una_estrella_desplazada_al_norte_sube(self):
        wcs_destino, forma = crear_wcs_destino(RA, DEC, 0.1)
        wcs_original = wcs_girado(RA, DEC, 90, 180)
        dec_norte = DEC + 10 * 6.15 / 3600  # 10 píxeles al norte
        imagen = imagen_con_estrella(wcs_original, 90, RA, dec_norte)
        alineada = reproyectar(imagen, wcs_original, wcs_destino, forma)
        fila, columna = np.unravel_index(np.nanargmax(alineada), alineada.shape)
        self.assertEqual(fila, 29 + 10)   # en el FITS, norte = filas mayores
        self.assertEqual(columna, 29)

    def test_lo_no_cubierto_queda_en_nan(self):
        wcs_destino, forma = crear_wcs_destino(RA, DEC, 0.1)
        wcs_original = wcs_girado(RA, DEC, 20, 0)  # imagen pequeña: no cubre todo
        alineada = reproyectar(np.ones((20, 20)), wcs_original, wcs_destino, forma)
        self.assertTrue(np.isnan(alineada[0, 0]))
        self.assertTrue(np.isfinite(alineada[29, 29]))

    def test_alinear_un_recorte_completo(self):
        wcs_destino, forma = crear_wcs_destino(RA, DEC, 0.1)
        with abrir_recorte(recorte_falso(RA, DEC, giro_grados=181)) as hdul:
            alineada = alinear_recorte(hdul, wcs_destino, forma)
        self.assertEqual(alineada.shape, (59, 59))
        self.assertFalse(np.isnan(alineada).any())  # con margen, cubre todo el cuadro
        fila, columna = np.unravel_index(np.nanargmax(alineada), alineada.shape)
        self.assertLessEqual(abs(fila - 29), 1)
        self.assertLessEqual(abs(columna - 29), 1)


if __name__ == "__main__":
    unittest.main()
