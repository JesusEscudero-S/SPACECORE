"""Pruebas de app/datos/cache.py en una carpeta temporal (no usan internet).

Para correrlas (desde la carpeta backend, con el entorno .venv activado):

    python -m unittest discover -v
"""

import tempfile
import unittest
from pathlib import Path

from app.config import settings
from app.datos import cache


class PruebasCache(unittest.TestCase):
    def setUp(self):
        # Cada prueba usa su propia carpeta temporal en vez de la carpeta cache/ real.
        self._temporal = tempfile.TemporaryDirectory()
        self._carpeta_original = settings.cache_dir
        self._coleccion_original = settings.coleccion_spherex
        settings.cache_dir = self._temporal.name

    def tearDown(self):
        settings.cache_dir = self._carpeta_original
        settings.coleccion_spherex = self._coleccion_original
        self._temporal.cleanup()

    def test_guardar_y_leer(self):
        clave = cache.crear_clave("frames", 269.4521, 4.6934, 0.1, "D2")
        self.assertIsNone(cache.get(clave))
        datos = {"frames": [{"epoca": "E1", "png": "data:image/png;base64,AAAA"}], "ñ": "épocas"}
        cache.set(clave, datos)
        self.assertEqual(cache.get(clave), datos)

    def test_sobrescribir(self):
        clave = cache.crear_clave("epocas", 10, 20, 0.1, "D2")
        cache.set(clave, [1, 2])
        cache.set(clave, [3])
        self.assertEqual(cache.get(clave), [3])

    def test_bytes(self):
        clave = cache.clave_de_texto("recorte", "https://ejemplo.test/a.fits?center=1,2d")
        self.assertIsNone(cache.get_bytes(clave))
        cache.set_bytes(clave, b"SIMPLE  =" + bytes(range(256)))
        self.assertEqual(cache.get_bytes(clave), b"SIMPLE  =" + bytes(range(256)))

    def test_misma_busqueda_misma_clave(self):
        a = cache.crear_clave("frames", 269.45210, 4.69340, 0.1, "D2")
        b = cache.crear_clave("frames", 269.452101, 4.693399, 0.1, "D2")  # casi idéntica
        self.assertEqual(a, b)

    def test_busquedas_distintas_claves_distintas(self):
        base = cache.crear_clave("frames", 269.4521, 4.6934, 0.1, "D2")
        self.assertNotEqual(base, cache.crear_clave("frames", 269.4531, 4.6934, 0.1, "D2"))
        self.assertNotEqual(base, cache.crear_clave("frames", 269.4521, 4.6934, 0.2, "D2"))
        self.assertNotEqual(base, cache.crear_clave("frames", 269.4521, 4.6934, 0.1, "D3"))
        self.assertNotEqual(base, cache.crear_clave("epocas", 269.4521, 4.6934, 0.1, "D2"))

    def test_la_coleccion_forma_parte_de_la_clave(self):
        antes = cache.crear_clave("frames", 1, 2, 0.1, "D2")
        settings.coleccion_spherex = "otra_coleccion"
        self.assertNotEqual(antes, cache.crear_clave("frames", 1, 2, 0.1, "D2"))

    def test_archivo_danado_cuenta_como_vacio(self):
        clave = cache.crear_clave("frames", 1, 2, 0.1, "D2")
        (Path(settings.cache_dir) / f"{clave}.json").write_text("{esto no es json", encoding="utf-8")
        self.assertIsNone(cache.get(clave))

    def test_clave_invalida(self):
        with self.assertRaises(ValueError):
            cache.get("../secreto")
        with self.assertRaises(ValueError):
            cache.set("", {})


if __name__ == "__main__":
    unittest.main()
