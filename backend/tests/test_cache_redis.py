"""Pruebas de la capa de Redis de app/datos/cache.py.

Usan un Redis FALSO (un diccionario), así que no necesitan Redis ni internet. Comprueban que:
  - lo guardado va a Redis y al disco,
  - se lee primero de Redis,
  - si Redis falla, todo sigue funcionando con el disco, sin errores.

Correr desde la carpeta backend:

    python -m unittest discover -v
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.config import settings
from app.datos import cache


class RedisFalso:
    """Imita lo poco que usamos de un cliente de Redis: get y set."""

    def __init__(self, roto: bool = False):
        self.datos: dict[str, bytes] = {}
        self.caducidad: dict[str, int | None] = {}
        self.roto = roto

    def get(self, nombre):
        if self.roto:
            raise ConnectionError("Redis apagado")
        return self.datos.get(nombre)

    def set(self, nombre, valor, ex=None):
        if self.roto:
            raise ConnectionError("Redis apagado")
        self.datos[nombre] = valor
        self.caducidad[nombre] = ex


class PruebasCacheRedis(unittest.TestCase):
    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self._originales = (settings.cache_dir, settings.redis_url, settings.redis_ttl_horas)
        settings.cache_dir = self._temporal.name
        settings.redis_url = "redis://falso:6379/0"
        settings.redis_ttl_horas = 168
        cache._redis_pausado_hasta = 0.0

    def tearDown(self):
        settings.cache_dir, settings.redis_url, settings.redis_ttl_horas = self._originales
        cache._redis_pausado_hasta = 0.0
        self._temporal.cleanup()

    def _con_redis(self, falso):
        return mock.patch.object(cache, "_redis", return_value=falso)

    def test_guardar_escribe_en_redis_y_en_disco(self):
        falso = RedisFalso()
        clave = cache.crear_clave("frames", 1, 2, 0.1, "D2")
        with self._con_redis(falso):
            cache.set(clave, {"a": 1})
        self.assertIn(cache.PREFIJO_REDIS + f"{clave}.json", falso.datos)
        self.assertTrue((Path(settings.cache_dir) / f"{clave}.json").exists())

    def test_caduca_a_los_7_dias(self):
        falso = RedisFalso()
        clave = cache.crear_clave("frames", 1, 2, 0.1, "D2")
        with self._con_redis(falso):
            cache.set(clave, [1])
        self.assertEqual(falso.caducidad[cache.PREFIJO_REDIS + f"{clave}.json"], 168 * 3600)

    def test_lee_primero_de_redis(self):
        falso = RedisFalso()
        clave = cache.crear_clave("epocas", 1, 2, 0.1, "D2")
        falso.datos[cache.PREFIJO_REDIS + f"{clave}.json"] = b'{"de": "redis"}'
        with self._con_redis(falso):
            self.assertEqual(cache.get(clave), {"de": "redis"})

    def test_si_no_esta_en_redis_lo_trae_del_disco_y_lo_sube(self):
        clave = cache.crear_clave("epocas", 1, 2, 0.1, "D2")
        (Path(settings.cache_dir) / f"{clave}.json").write_text('{"de": "disco"}', encoding="utf-8")
        falso = RedisFalso()
        with self._con_redis(falso):
            self.assertEqual(cache.get(clave), {"de": "disco"})
        self.assertIn(cache.PREFIJO_REDIS + f"{clave}.json", falso.datos)

    def test_redis_roto_no_rompe_nada(self):
        clave = cache.crear_clave("frames", 3, 4, 0.1, "D2")
        with mock.patch.object(cache, "_redis", return_value=RedisFalso(roto=True)):
            cache.set(clave, {"ok": True})  # no debe lanzar error
            self.assertEqual(cache.get(clave), {"ok": True})  # sale del disco

    def test_redis_roto_se_pausa(self):
        cache._pausar_redis(ConnectionError("apagado"))
        self.assertIsNone(cache._redis())  # durante la pausa ni lo intenta

    def test_sin_redis_url_usa_solo_disco(self):
        settings.redis_url = ""
        self.assertIsNone(cache._redis())
        clave = cache.crear_clave("frames", 5, 6, 0.1, "D2")
        cache.set(clave, [42])
        self.assertEqual(cache.get(clave), [42])

    def test_bytes_por_redis(self):
        falso = RedisFalso()
        clave = cache.clave_de_texto("recorte", "https://ejemplo.test/b.fits")
        with self._con_redis(falso):
            cache.set_bytes(clave, b"\x00\x01FITS")
            (Path(settings.cache_dir) / f"{clave}.bin").unlink()  # borramos el disco a propósito
            self.assertEqual(cache.get_bytes(clave), b"\x00\x01FITS")  # sale de Redis


if __name__ == "__main__":
    unittest.main()
