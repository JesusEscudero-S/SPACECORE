"""Pruebas de los endpoints (/resolve, /epocas, /frames, /diff) SIN internet.

IRSA se reemplaza por funciones falsas que devuelven recortes sintéticos: girados y con una
estrella que se mueve hacia el norte, como pasaría con Barnard's Star.

Para correrlas (desde la carpeta backend):

    python -m unittest discover -v
"""

import base64
import io
import shutil
import tempfile
import unittest
from unittest import mock

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from fastapi.testclient import TestClient
from PIL import Image
from pyvo.dal.exceptions import DALServiceError

from app import servicio
from app.config import settings
from app.main import app

RA, DEC = 269.4521, 4.6934
MJD_EPOCAS = (60900.0, 61110.0, 61270.0)


def _recorte_falso(numero_epoca: int) -> bytes:
    """Un recorte FITS girado 30 grados, con una estrella que sube 12 arcsec por época."""
    n = 64
    escala = 6.15 / 3600
    angulo = np.radians(30)
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [RA, DEC]
    wcs.wcs.crpix = [n / 2 + 2, n / 2 - 1]
    wcs.wcs.cd = escala * np.array(
        [[-np.cos(angulo), np.sin(angulo)], [np.sin(angulo), np.cos(angulo)]]
    )
    x0, y0 = wcs.world_to_pixel_values(RA, DEC + 12 * numero_epoca / 3600)
    y, x = np.mgrid[0:n, 0:n]
    datos = 1 + 50 * np.exp(-((x - x0) ** 2 + (y - y0) ** 2) / (2 * 1.3**2))
    hdul = fits.HDUList(
        [
            fits.PrimaryHDU(),
            fits.ImageHDU(datos.astype(np.float32), header=wcs.to_header(), name="IMAGE"),
            fits.ImageHDU(np.zeros((n, n), dtype=np.int32), name="FLAGS"),
        ]
    )
    salida = io.BytesIO()
    hdul.writeto(salida)
    return salida.getvalue()


def _buscar_falso(ra, dec, fov, detector=None):
    imagenes = []
    for numero, mjd in enumerate(MJD_EPOCAS):
        for k in range(3):
            for det in ("D2", "D6"):
                imagenes.append(
                    {
                        "url_recorte": f"falso://{numero}/{k}/{det}",
                        "fecha_obs": "",
                        "mjd": mjd + k,
                        "detector": det,
                        "coleccion": "spherex_dr1",
                    }
                )
    return imagenes


async def _descargar_falso(urls):
    return [_recorte_falso(int(url.split("/")[2])) for url in urls]


def _png(data_url: str) -> np.ndarray:
    self_prefijo = "data:image/png;base64,"
    assert data_url.startswith(self_prefijo)
    return np.array(Image.open(io.BytesIO(base64.b64decode(data_url[len(self_prefijo):]))))


class PruebasApi(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        self.cambios = [
            mock.patch.object(settings, "cache_dir", self.carpeta),
            mock.patch.object(settings, "usar_mock", False),
            mock.patch.object(servicio, "buscar_imagenes", side_effect=_buscar_falso),
            mock.patch.object(servicio, "descargar_recortes", side_effect=_descargar_falso),
        ]
        for cambio in self.cambios:
            cambio.start()
        self.buscar = servicio.buscar_imagenes
        self.cliente = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        for cambio in self.cambios:
            cambio.stop()
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def test_health(self):
        self.assertEqual(self.cliente.get("/health").json(), {"status": "ok"})

    def test_epocas(self):
        r = self.cliente.get("/epocas", params={"ra": RA, "dec": DEC, "fov": 0.1, "det": "D2"})
        self.assertEqual(r.status_code, 200)
        epocas = r.json()["epocas"]
        self.assertEqual([e["id"] for e in epocas], ["E1", "E2", "E3"])
        self.assertEqual(epocas[0]["n_imagenes"], 3)
        self.assertEqual(set(epocas[0]), {"id", "inicio", "fin", "n_imagenes"})
        self.assertTrue(epocas[0]["inicio"].endswith("Z"))

    def test_seis_detectores_una_sola_consulta_a_irsa(self):
        for det in ("D2", "D6"):
            self.cliente.get("/epocas", params={"ra": RA, "dec": DEC, "det": det})
        self.assertEqual(self.buscar.call_count, 1)

    def test_frames_formato_y_movimiento(self):
        r = self.cliente.get("/frames", params={"ra": RA, "dec": DEC, "fov": 0.1, "det": "D2"})
        self.assertEqual(r.status_code, 200)
        cuerpo = r.json()
        self.assertEqual(cuerpo["meta"]["tamano_px"], 59)
        self.assertEqual(cuerpo["meta"]["escala_arcsec_px"], 6.15)
        self.assertEqual([f["epoca"] for f in cuerpo["frames"]], ["E1", "E2", "E3"])

        filas = []
        for cuadro in cuerpo["frames"]:
            imagen = _png(cuadro["png"])
            self.assertEqual(imagen.shape, (59, 59))
            fila, columna = np.unravel_index(np.argmax(imagen), imagen.shape)
            filas.append(fila)
            self.assertLessEqual(abs(columna - 29), 1)  # la estrella no se mueve en RA
        # En el PNG la fila 0 es la de arriba: si la estrella va al norte, la fila disminuye.
        self.assertGreater(filas[0], filas[1])
        self.assertGreater(filas[1], filas[2])

    def test_diff(self):
        params = {"ra": RA, "dec": DEC, "det": "D2", "a": "E1", "b": "E3"}
        r = self.cliente.get("/diff", params=params)
        self.assertEqual(r.status_code, 200)
        imagen = _png(r.json()["png"])
        self.assertAlmostEqual(float(np.median(imagen)), 128, delta=3)  # fondo gris = sin cambio

    def test_diff_errores(self):
        base = {"ra": RA, "dec": DEC, "det": "D2"}
        self.assertEqual(self.cliente.get("/diff", params={**base, "a": "E1", "b": "E1"}).status_code, 400)
        r = self.cliente.get("/diff", params={**base, "a": "E1", "b": "E9"})
        self.assertEqual(r.status_code, 404)
        self.assertIn("error", r.json())

    def test_errores_de_parametros(self):
        r = self.cliente.get("/frames", params={"ra": "hola", "dec": DEC})
        self.assertEqual(r.status_code, 422)
        self.assertIn("RA", r.json()["error"])
        self.assertEqual(self.cliente.get("/frames", params={"ra": RA, "dec": DEC, "det": "D9"}).status_code, 422)
        self.assertEqual(self.cliente.get("/frames", params={"dec": DEC}).status_code, 422)
        r = self.cliente.get("/frames", params={"ra": RA, "dec": DEC, "fov": 5})
        self.assertEqual(r.status_code, 400)
        self.assertIn("máximo", r.json()["error"])

    def test_zona_sin_datos_da_404(self):
        self.buscar.side_effect = lambda *a, **k: []
        r = self.cliente.get("/epocas", params={"ra": 10, "dec": 10})
        self.assertEqual(r.status_code, 404)

    def test_irsa_caido_da_504(self):
        self.buscar.side_effect = DALServiceError("502 Proxy Error")
        r = self.cliente.get("/epocas", params={"ra": 10, "dec": 10})
        self.assertEqual(r.status_code, 504)
        self.assertIn("IRSA", r.json()["error"])

    def test_resolve_objetivo_de_prueba_sin_internet(self):
        r = self.cliente.get("/resolve", params={"name": "Barnard's Star"})
        self.assertEqual(r.json(), {"name": "Barnard's Star", "ra": 269.4521, "dec": 4.6934})

    def test_mock(self):
        with mock.patch.object(settings, "usar_mock", True):
            r = self.cliente.get("/frames", params={"ra": RA, "dec": DEC})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["frames"]), 3)
        self.assertEqual(self.buscar.call_count, 0)


if __name__ == "__main__":
    unittest.main()
