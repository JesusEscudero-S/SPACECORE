"""Pruebas de app/datos/descargas.py con un servidor falso (no usan internet).

Para correrlas (desde la carpeta backend, con el entorno .venv activado):

    python -m unittest discover -v
"""

import asyncio
import io
import unittest

import httpx
import numpy as np
from astropy.io import fits
from astropy.table import Table

from app.datos.descargas import abrir_recorte, cortar_antes_de_tabla, descargar_recortes


def _fits_falso() -> bytes:
    """Un FITS parecido a un recorte: 2 imágenes y luego una tabla (como EPSF)."""
    hdul = fits.HDUList(
        [
            fits.PrimaryHDU(),
            fits.ImageHDU(np.ones((5, 6), dtype=np.float32), name="IMAGE"),
            fits.ImageHDU(np.zeros((5, 6), dtype=np.int32), name="FLAGS"),
            fits.BinTableHDU(Table({"x": np.arange(1000.0)}), name="EPSF"),
        ]
    )
    salida = io.BytesIO()
    hdul.writeto(salida)
    return salida.getvalue()


class PruebasCorte(unittest.TestCase):
    def test_quita_la_tabla_y_conserva_las_imagenes(self):
        completo = _fits_falso()
        recortado = cortar_antes_de_tabla(completo)
        self.assertLess(len(recortado), len(completo))
        self.assertEqual(len(recortado) % 2880, 0)
        with abrir_recorte(recortado) as hdul:
            self.assertEqual([hdu.name for hdu in hdul], ["PRIMARY", "IMAGE", "FLAGS"])
            self.assertEqual(hdul["IMAGE"].data.shape, (5, 6))

    def test_sin_tabla_no_cambia_nada(self):
        hdul = fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(np.ones((2, 2)), name="IMAGE")])
        salida = io.BytesIO()
        hdul.writeto(salida)
        self.assertEqual(cortar_antes_de_tabla(salida.getvalue()), salida.getvalue())


class PruebasDescarga(unittest.TestCase):
    def _descargar(self, manejador, urls, **opciones):
        async def correr():
            transporte = httpx.MockTransport(manejador)
            async with httpx.AsyncClient(transport=transporte) as cliente:
                return await descargar_recortes(
                    urls, cliente=cliente, espera_reintento=0, **opciones
                )

        return asyncio.run(correr())

    def test_mismo_orden_y_none_si_falla(self):
        contenido = _fits_falso()

        def manejador(peticion: httpx.Request) -> httpx.Response:
            if "malo" in str(peticion.url):
                return httpx.Response(500)
            return httpx.Response(200, content=contenido)

        urls = ["https://ejemplo.test/a", "https://ejemplo.test/malo", "https://ejemplo.test/c"]
        resultados = self._descargar(manejador, urls)
        self.assertEqual(len(resultados), 3)
        self.assertIsNotNone(resultados[0])
        self.assertIsNone(resultados[1])
        self.assertIsNotNone(resultados[2])
        with abrir_recorte(resultados[0]) as hdul:
            self.assertEqual([hdu.name for hdu in hdul], ["PRIMARY", "IMAGE", "FLAGS"])

    def test_completo_trae_tambien_la_tabla(self):
        contenido = _fits_falso()
        resultados = self._descargar(
            lambda peticion: httpx.Response(200, content=contenido),
            ["https://ejemplo.test/a"],
            completo=True,
        )
        self.assertEqual(resultados[0], contenido)

    def test_reintenta_hasta_que_funciona(self):
        contenido = _fits_falso()
        llamadas = {"n": 0}

        def manejador(peticion: httpx.Request) -> httpx.Response:
            llamadas["n"] += 1
            if llamadas["n"] < 3:
                return httpx.Response(502)
            return httpx.Response(200, content=contenido)

        resultados = self._descargar(manejador, ["https://ejemplo.test/a"])
        self.assertEqual(llamadas["n"], 3)
        self.assertIsNotNone(resultados[0])

    def test_lista_vacia(self):
        self.assertEqual(self._descargar(lambda p: httpx.Response(200), []), [])


if __name__ == "__main__":
    unittest.main()
