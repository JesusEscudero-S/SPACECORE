"""Pruebas de app/ciencia/alinear.py con imágenes sintéticas (no usan internet).

Para correrlas (desde la carpeta backend):

    python -m unittest discover -v
"""

import unittest

import numpy as np
from astropy.wcs import WCS

from app.ciencia.alinear import (
    alinear,
    malla_objetivo,
    restar_fondo,
    sumar_epoca,
    tamano_malla,
)


def _wcs_girado(ra: float, dec: float, n: int, angulo_grados: float) -> WCS:
    """Un WCS como el de un recorte de SPHEREx: girado y con el centro un poco corrido."""
    escala = 6.15 / 3600
    angulo = np.radians(angulo_grados)
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [ra, dec]
    wcs.wcs.crpix = [n / 2 + 3.3, n / 2 - 2.1]  # el punto pedido no queda en el centro
    wcs.wcs.cd = escala * np.array(
        [[-np.cos(angulo), np.sin(angulo)], [np.sin(angulo), np.cos(angulo)]]
    )
    return wcs


def _estrella(wcs: WCS, forma: tuple[int, int], ra: float, dec: float) -> np.ndarray:
    """Imagen con fondo 10 y una estrella gaussiana en (ra, dec)."""
    x0, y0 = wcs.world_to_pixel_values(ra, dec)
    y, x = np.mgrid[0 : forma[0], 0 : forma[1]]
    return 10 + 100 * np.exp(-((x - x0) ** 2 + (y - y0) ** 2) / (2 * 1.5**2))


class PruebasMalla(unittest.TestCase):
    def test_tamano_del_contrato(self):
        # docs/api.md: para fov = 0.1 grados son 59 píxeles.
        self.assertEqual(tamano_malla(0.1), 59)

    def test_norte_arriba_y_este_a_la_izquierda(self):
        wcs, forma = malla_objetivo(269.45, 4.69, 0.1)
        self.assertEqual(forma, (59, 59))
        centro = wcs.pixel_to_world_values(29, 29)
        self.assertAlmostEqual(float(centro[0]), 269.45, places=6)
        self.assertAlmostEqual(float(centro[1]), 4.69, places=6)
        # Subir una fila (y + 1) aumenta la Dec: el norte está arriba.
        _, dec_arriba = wcs.pixel_to_world_values(29, 30)
        self.assertGreater(float(dec_arriba), 4.69)
        # Ir a la derecha (x + 1) disminuye la RA: el este está a la izquierda.
        ra_derecha, _ = wcs.pixel_to_world_values(30, 29)
        self.assertLess(float(ra_derecha), 269.45)


class PruebasAlinear(unittest.TestCase):
    def test_la_estrella_queda_en_su_lugar_aunque_el_recorte_venga_girado(self):
        ra, dec = 269.45, 4.69
        # La estrella está 30 arcsec al norte del centro.
        dec_estrella = dec + 30 / 3600
        wcs_recorte = _wcs_girado(ra, dec, 80, angulo_grados=37)
        recorte = _estrella(wcs_recorte, (80, 80), ra, dec_estrella)

        wcs_malla, forma = malla_objetivo(ra, dec, 0.1)
        alineada = alinear(recorte, wcs_recorte, wcs_malla, forma)

        fila, columna = np.unravel_index(np.nanargmax(alineada), forma)
        x_esperado, y_esperado = wcs_malla.world_to_pixel_values(ra, dec_estrella)
        self.assertLessEqual(abs(columna - x_esperado), 1)
        self.assertLessEqual(abs(fila - y_esperado), 1)

    def test_zona_sin_cubrir_queda_nan(self):
        wcs_recorte = _wcs_girado(10.0, 0.0, 20, angulo_grados=0)
        wcs_malla, forma = malla_objetivo(10.0, 0.0, 0.1)  # malla más grande que el recorte
        alineada = alinear(np.ones((20, 20)), wcs_recorte, wcs_malla, forma)
        self.assertTrue(np.isnan(alineada[0, 0]))
        self.assertTrue(np.isfinite(alineada[29, 29]))


class PruebasSumar(unittest.TestCase):
    def test_resta_el_fondo(self):
        imagen = np.full((5, 5), 7.0)
        imagen[2, 2] = 100.0
        sin_fondo = restar_fondo(imagen)
        self.assertEqual(sin_fondo[0, 0], 0.0)
        self.assertEqual(sin_fondo[2, 2], 93.0)

    def test_mediana_quita_un_rayo_cosmico(self):
        base = np.zeros((4, 4))
        con_rayo = base.copy()
        con_rayo[1, 1] = 1000.0
        resultado = sumar_epoca([base, base.copy(), con_rayo])
        self.assertEqual(resultado[1, 1], 0.0)

    def test_ignora_los_nan(self):
        a = np.full((3, 3), 5.0)
        b = np.full((3, 3), 5.0)
        b[0, 0] = np.nan
        resultado = sumar_epoca([a, b])
        self.assertTrue(np.all(np.isfinite(resultado)))

    def test_sin_imagenes_da_error(self):
        with self.assertRaises(ValueError):
            sumar_epoca([])


if __name__ == "__main__":
    unittest.main()
