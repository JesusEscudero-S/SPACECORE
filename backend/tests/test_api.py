"""Pruebas de los endpoints con IRSA simulado (no usan internet).

Se reemplazan las dos funciones que hablan con IRSA (buscar observaciones y descargar recortes)
por versiones falsas, y se prueba toda la cadena hasta el JSON de respuesta.

Para correrlas (desde la carpeta backend, con el entorno .venv activado):

    python -m unittest discover -v
"""

import base64
import io
import tempfile
import unittest
from unittest import mock

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.coordinates.name_resolve import NameResolveError
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.main import app
from tests.ayudas import recorte_falso

RA, DEC = 269.4461, 4.7705
BUSQUEDA = {"ra": RA, "dec": DEC, "fov": 0.1, "det": "D2"}

# Dos pasadas de SPHEREx (agosto 2025 y marzo 2026) en D2, y una imagen suelta en D5.
OBSERVACIONES = [
    {"url_imagen": "https://irsa.test/a.fits", "mjd": 60908.98, "detector": "D2", "coleccion": "spherex_dr1"},
    {"url_imagen": "https://irsa.test/b.fits", "mjd": 60911.49, "detector": "D2", "coleccion": "spherex_dr1"},
    {"url_imagen": "https://irsa.test/c.fits", "mjd": 61114.03, "detector": "D2", "coleccion": "spherex_dr1"},
    {"url_imagen": "https://irsa.test/d.fits", "mjd": 61116.68, "detector": "D2", "coleccion": "spherex_qr3"},
    {"url_imagen": "https://irsa.test/e.fits", "mjd": 61116.70, "detector": "D5", "coleccion": "spherex_qr3"},
]


class PruebasApi(unittest.TestCase):
    def setUp(self):
        # Caché en una carpeta temporal, para no tocar la real ni mezclar pruebas.
        self._temporal = tempfile.TemporaryDirectory()
        self._carpeta_original = settings.cache_dir
        settings.cache_dir = self._temporal.name
        self.cliente = TestClient(app)

        self.descargas = 0

        async def descargar_falso(urls, **opciones):
            self.descargas += 1
            return [recorte_falso(RA, DEC, giro_grados=181, fondo=1.0 + i) for i, _ in enumerate(urls)]

        self._parches = [
            mock.patch("app.datos.irsa.buscar_observaciones", return_value=OBSERVACIONES),
            mock.patch("app.servicio.descargar_recortes", side_effect=descargar_falso),
        ]
        self.buscar = self._parches[0].start()
        self._parches[1].start()

    def tearDown(self):
        for parche in self._parches:
            parche.stop()
        settings.cache_dir = self._carpeta_original
        self._temporal.cleanup()

    # ---------- /health ----------
    def test_health(self):
        respuesta = self.cliente.get("/health")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"status": "ok"})

    # ---------- /epocas ----------
    def test_epocas_formato_del_contrato(self):
        respuesta = self.cliente.get("/epocas", params=BUSQUEDA)
        self.assertEqual(respuesta.status_code, 200)
        epocas = respuesta.json()["epocas"]
        self.assertEqual([e["id"] for e in epocas], ["E1", "E2"])
        self.assertEqual([e["n_imagenes"] for e in epocas], [2, 2])
        self.assertEqual(sorted(epocas[0]), ["fin", "id", "inicio", "n_imagenes"])  # sin URLs internas
        self.assertTrue(epocas[0]["inicio"].endswith("Z"))

    def test_epocas_usa_la_cache_para_los_demas_detectores(self):
        self.cliente.get("/epocas", params=BUSQUEDA)
        self.cliente.get("/epocas", params={**BUSQUEDA, "det": "D5"})
        self.assertEqual(self.buscar.call_count, 1)  # IRSA se consultó una sola vez

    def test_epocas_sin_datos_da_404(self):
        respuesta = self.cliente.get("/epocas", params={**BUSQUEDA, "det": "D1"})
        self.assertEqual(respuesta.status_code, 404)
        self.assertIn("error", respuesta.json())

    def test_parametros_invalidos_dan_422_con_formato_del_contrato(self):
        casos = [
            {**BUSQUEDA, "ra": 400},
            {**BUSQUEDA, "dec": -91},
            {**BUSQUEDA, "det": "D9"},
            {**BUSQUEDA, "ra": "hola"},
            {"dec": DEC},  # falta ra
        ]
        for parametros in casos:
            respuesta = self.cliente.get("/epocas", params=parametros)
            self.assertEqual(respuesta.status_code, 422, parametros)
            self.assertEqual(list(respuesta.json()), ["error"], parametros)

    def test_fov_mayor_al_maximo_da_400(self):
        respuesta = self.cliente.get("/epocas", params={**BUSQUEDA, "fov": settings.fov_max + 0.1})
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("error", respuesta.json())

    def test_irsa_caido_da_504(self):
        self.buscar.side_effect = OSError("502 Proxy Error")
        respuesta = self.cliente.get("/epocas", params=BUSQUEDA)
        self.assertEqual(respuesta.status_code, 504)
        self.assertIn("IRSA", respuesta.json()["error"])

    # ---------- /frames ----------
    def test_frames_formato_del_contrato(self):
        respuesta = self.cliente.get("/frames", params=BUSQUEDA)
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.json()
        self.assertEqual([f["epoca"] for f in cuerpo["frames"]], ["E1", "E2"])
        self.assertEqual(
            cuerpo["meta"],
            {"detector": "D2", "fov_grados": 0.1, "ra": RA, "dec": DEC, "tamano_px": 59, "escala_arcsec_px": 6.15},
        )
        for frame in cuerpo["frames"]:
            self.assertTrue(frame["png"].startswith("data:image/png;base64,"))
            self.assertTrue(frame["fecha"].endswith("Z"))

    def test_frames_png_a_escala_real_con_la_estrella_al_centro(self):
        cuerpo = self.cliente.get("/frames", params=BUSQUEDA).json()
        png = base64.b64decode(cuerpo["frames"][0]["png"].split(",", 1)[1])
        pixeles = np.array(Image.open(io.BytesIO(png)))
        self.assertEqual(pixeles.shape, (59, 59))
        # La estrella satura varios píxeles en blanco: tomamos el centro de esa mancha.
        filas, columnas = np.nonzero(pixeles == pixeles.max())
        self.assertLessEqual(abs(filas.mean() - 29), 1)
        self.assertLessEqual(abs(columnas.mean() - 29), 1)

    def test_frames_la_segunda_vez_sale_de_la_cache(self):
        primera = self.cliente.get("/frames", params=BUSQUEDA).json()
        segunda = self.cliente.get("/frames", params=BUSQUEDA).json()
        self.assertEqual(primera, segunda)
        self.assertEqual(self.descargas, 1)

    def test_frames_sin_datos_da_404(self):
        respuesta = self.cliente.get("/frames", params={**BUSQUEDA, "det": "D1"})
        self.assertEqual(respuesta.status_code, 404)

    # ---------- /resolve ----------
    def test_resolve_con_sesame(self):
        coordenadas = SkyCoord(10.5, -20.25, unit="deg")
        with mock.patch("app.routers.resolve.SkyCoord.from_name", return_value=coordenadas):
            respuesta = self.cliente.get("/resolve", params={"name": "Objeto X"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["name"], "Objeto X")
        self.assertAlmostEqual(respuesta.json()["ra"], 10.5)
        self.assertAlmostEqual(respuesta.json()["dec"], -20.25)

    def test_resolve_usa_el_respaldo_si_sesame_falla(self):
        with mock.patch("app.routers.resolve.SkyCoord.from_name", side_effect=NameResolveError("caído")):
            respuesta = self.cliente.get("/resolve", params={"name": "  barnard's   STAR "})
        self.assertEqual(respuesta.status_code, 200)
        self.assertAlmostEqual(respuesta.json()["ra"], 269.4521)

    def test_resolve_nombre_desconocido_da_404(self):
        with mock.patch("app.routers.resolve.SkyCoord.from_name", side_effect=NameResolveError("no")):
            respuesta = self.cliente.get("/resolve", params={"name": "objeto inventado 123"})
        self.assertEqual(respuesta.status_code, 404)
        self.assertIn("error", respuesta.json())

    def test_resolve_sin_nombre_da_422(self):
        respuesta = self.cliente.get("/resolve")
        self.assertEqual(respuesta.status_code, 422)
        self.assertEqual(list(respuesta.json()), ["error"])


if __name__ == "__main__":
    unittest.main()
