"""Pruebas del script de precálculo (no usan internet).

Lo más importante: que las coordenadas sean EXACTAMENTE las que pide la página. Los valores
esperados se obtuvieron el 2026-11-15 ejecutando propagarProperMotion() de
frontend/src/lib/coords.ts en el navegador con época 2026. Si esta prueba falla, la página y el
script ya no calculan igual y la caché precalculada no se aprovecharía.

Correr desde la carpeta backend:

    python -m unittest discover -v
"""

import unittest
from datetime import datetime, timezone

from scripts.precalcular import OBJETIVOS, epoca_de_centrado, propagar

# Resultado de la página (JavaScript) para la época 2026.0.
ESPERADO_2026 = {
    "barnard": (269.4463129282333, 4.767991833333333),
    "epsindib": (331.0962077419755, -56.80133),
    "wise0855": (133.7361291483328, -7.240144444444444),
    "rwaur": (76.95730000000003, 30.4015),
    "rdra": (248.178, 66.755),
}


class PruebasPrecalcular(unittest.TestCase):
    def test_mismas_coordenadas_que_la_pagina(self):
        for clave, esperado in ESPERADO_2026.items():
            with self.subTest(objetivo=clave):
                _nombre, ra0, dec0, pmra, pmdec = OBJETIVOS[clave]
                ra, dec = propagar(ra0, dec0, pmra, pmdec, 2026.0)
                self.assertAlmostEqual(ra, esperado[0], places=9)
                self.assertAlmostEqual(dec, esperado[1], places=9)

    def test_epoca_es_el_1_de_enero(self):
        self.assertEqual(epoca_de_centrado(datetime(2026, 11, 15, 6, tzinfo=timezone.utc)), 2026.0)
        self.assertEqual(epoca_de_centrado(datetime(2026, 12, 20, 23, tzinfo=timezone.utc)), 2026.0)
        self.assertEqual(epoca_de_centrado(datetime(2027, 1, 1, tzinfo=timezone.utc)), 2027.0)


if __name__ == "__main__":
    unittest.main()
