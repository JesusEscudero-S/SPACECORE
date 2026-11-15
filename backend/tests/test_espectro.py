"""Pruebas del espectro (T36) con datos sintéticos (no usan internet).

Para correrlas (desde la carpeta backend):

    python -m unittest tests.test_espectro -v
"""

import unittest
from unittest import mock

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from app import servicio
from app.ciencia import espectro
from app.errores import ErrorApi

ESCALA = 6.15 / 3600


def _cabecera_w(crpix1w: float, crpix2w: float) -> fits.Header:
    """Las llaves del WCS 'W' tal como vienen en un recorte real de SPHEREx (2026-11-15)."""
    cab = fits.Header()
    cab["WCSAXESW"] = 2
    cab["CNAME1W"], cab["CNAME2W"] = "Wavelength", "Bandwidth"
    cab["CRPIX1W"], cab["CRPIX2W"] = crpix1w, crpix2w
    cab["CDELT1W"], cab["CDELT2W"] = 1, 1
    cab["CUNIT1W"], cab["CUNIT2W"] = "um", "um"
    cab["CTYPE1W"], cab["CTYPE2W"] = "WAVE-TAB", "WAVE-TAB"
    cab["CRVAL1W"], cab["CRVAL2W"] = 1, 1
    cab["PV1_3W"], cab["PV2_3W"] = 1, 2
    cab["PS1_0W"], cab["PS2_0W"] = "WCS-WAVE", "WCS-WAVE"
    cab["PS1_1W"], cab["PS2_1W"] = "VALUES", "VALUES"
    cab["PS1_2W"], cab["PS2_2W"] = "X", "Y"
    return cab


def _tabla(pendiente: float = 1e-4) -> fits.BinTableHDU:
    """Tabla WCS-WAVE de 11x11 como la real; aquí lambda = 1 + pendiente * X y ancho = 0.03."""
    ejes = np.arange(1, 2042, 204, dtype=np.int32)  # 1, 205, ..., 2041
    valores = np.zeros((11, 11, 2), dtype=np.float32)
    valores[:, :, 0] = 1 + pendiente * ejes[np.newaxis, :]
    valores[:, :, 1] = 0.03
    columnas = [
        fits.Column(name="X", format="11J", dim="(11)", array=ejes[np.newaxis, :]),
        fits.Column(name="Y", format="11J", dim="(11)", array=ejes[np.newaxis, :]),
        fits.Column(name="VALUES", format="242E", dim="(2,11,11)", array=valores[np.newaxis]),
    ]
    return fits.BinTableHDU.from_columns(columnas, name="WCS-WAVE")


def _wcs_norte_arriba(n: int = 20) -> WCS:
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [269.45, 4.77]
    wcs.wcs.crpix = [(n + 1) / 2, (n + 1) / 2]
    wcs.wcs.cdelt = [-ESCALA, ESCALA]
    return wcs


def _estrella(n: int, x: float, y: float, total: float, fondo: float = 10.0) -> np.ndarray:
    filas, columnas = np.mgrid[:n, :n]
    sigma = 1.2
    gauss = np.exp(-((columnas - x) ** 2 + (filas - y) ** 2) / (2 * sigma**2))
    return fondo + total * gauss / gauss.sum()


class PruebasLongitudDeOnda(unittest.TestCase):
    def test_desplazamiento_por_crpix(self):
        # El mismo píxel del recorte con CRPIX1W corrido 100 cae 100 píxeles más allá en la tabla.
        tabla = _tabla()
        lam_a, ancho = espectro.longitud_de_onda(_cabecera_w(-1152.0, -1000.0), tabla, 8.0, 8.0)
        lam_b, _ = espectro.longitud_de_onda(_cabecera_w(-1252.0, -1000.0), tabla, 8.0, 8.0)
        self.assertAlmostEqual(lam_b - lam_a, 100 * 1e-4, places=5)
        self.assertAlmostEqual(ancho, 0.03, places=5)
        # Píxel del detector ~1161: lambda ~ 1.116 (tolerancia de unos pocos píxeles).
        self.assertAlmostEqual(lam_a, 1 + 1e-4 * 1161, delta=5e-4)

    def test_tabla_ida_y_vuelta_por_la_cache(self):
        tabla = espectro.bytes_a_tabla(espectro.tabla_a_bytes(_tabla()))
        lam, _ = espectro.longitud_de_onda(_cabecera_w(-1152.0, -1000.0), tabla, 8.0, 8.0)
        self.assertAlmostEqual(lam, 1 + 1e-4 * 1161, delta=5e-4)


class PruebasGeometria(unittest.TestCase):
    def test_jacobiano_norte_arriba_este_izquierda(self):
        wcs = _wcs_norte_arriba()
        x, y, jac = espectro.posicion_y_jacobiano(wcs, 269.45, 4.77)
        self.assertAlmostEqual(x, 9.5, places=3)
        self.assertAlmostEqual(y, 9.5, places=3)
        self.assertAlmostEqual(jac[0][0], -1 / 6.15, places=3)  # este -> x baja
        self.assertAlmostEqual(jac[1][1], 1 / 6.15, places=3)   # norte -> y sube
        self.assertAlmostEqual(jac[0][1], 0, places=3)
        self.assertAlmostEqual(jac[1][0], 0, places=3)

    def test_area_del_pixel(self):
        self.assertAlmostEqual(espectro.area_pixel_sr(_wcs_norte_arriba()) / (6.15 / 206264.806) ** 2, 1, places=4)


class PruebasFotometria(unittest.TestCase):
    def test_apertura_chica_pierde_la_luz_esperada(self):
        # Con radio 3 px entra 1 - exp(-r^2 / 2 sigma^2) = 95.6 % de la luz (sin corrección de PSF).
        imagen = _estrella(20, 9.3, 10.1, total=500.0)
        suma, _, _, _ = espectro.fotometria(imagen, np.ones((20, 20)), 9.3, 10.1, 3, 5, 8)
        self.assertAlmostEqual(suma, 500.0 * (1 - np.exp(-9 / (2 * 1.2**2))), delta=5.0)

    def test_recupera_el_flujo_y_resta_el_fondo(self):
        # Apertura de 4.5 px: encierra el 99.9 % de la luz de esta estrella (sigma 1.2 px).
        imagen = _estrella(20, 9.3, 10.1, total=500.0)
        suma, error, n_malos, n_ap = espectro.fotometria(imagen, np.ones((20, 20)), 9.3, 10.1, 4.5, 6, 9)
        self.assertAlmostEqual(suma, 500.0, delta=5.0)
        self.assertEqual(n_malos, 0)
        self.assertAlmostEqual(error, np.sqrt(n_ap), places=6)

    def test_sin_restar_fondo_suma_tambien_el_fondo(self):
        imagen = _estrella(20, 9.3, 10.1, total=500.0)
        suma, _, _, n_ap = espectro.fotometria(imagen, np.ones((20, 20)), 9.3, 10.1, 4.5, 6, 9, restar_fondo=False)
        self.assertAlmostEqual(suma, 500.0 + 10.0 * n_ap, delta=5.0)

    def test_centro_saturado_cuenta_pixeles_malos(self):
        imagen = _estrella(20, 10, 10, total=500.0)
        imagen[10, 10] = np.nan
        suma, _, n_malos, _ = espectro.fotometria(imagen, np.ones((20, 20)), 10, 10, 3, 5, 8)
        self.assertEqual(n_malos, 1)
        self.assertLess(suma, 500.0)  # el valor real queda subestimado

    def test_apertura_fuera_del_recorte(self):
        _, _, _, n_ap = espectro.fotometria(np.zeros((20, 20)), np.ones((20, 20)), 80, 80, 3, 5, 8)
        self.assertEqual(n_ap, 0)


class PruebasServicioEspectro(unittest.TestCase):
    def _meta(self, mjd: float, x: float = 9.5) -> dict:
        return {
            "x": x, "y": 9.5, "jac": [[-1 / 6.15, 0.0], [0.0, 1 / 6.15]], "lambda_um": 1.2,
            "ancho_um": 0.03, "area_sr": (6.15 / 206264.806) ** 2, "mjd": mjd,
            "fecha": "2025-08-21T00:00:00Z", "detector": "D2", "url": "u",
        }

    def test_radios_invalidos(self):
        with self.assertRaises(ErrorApi) as error:
            servicio.espectro(269.45, 4.77, apertura=40, anillo_in=30, anillo_out=50)
        self.assertEqual(error.exception.codigo, 400)

    def test_movimiento_propio_mueve_la_apertura(self):
        # La estrella está 12 arcsec al norte del centro (2 px): con pm de 12"/año y la imagen
        # tomada un año después de la época de ra/dec, la apertura la encuentra completa.
        mjd = 51544.5 + 365.25 * 26  # año 2026.0
        imagen = _estrella(24, 9.5, 9.5 + 12 / 6.15, total=1000.0, fondo=0.0)
        datos = ([self._meta(mjd)], imagen[np.newaxis], np.ones((1, 24, 24)))
        with mock.patch.object(servicio, "estampillas", return_value=datos), \
             mock.patch.object(servicio, "_ids_de_epoca", return_value={"u": "E1"}):
            quieto = servicio.espectro(269.45, 4.77, apertura=6, anillo_in=30, anillo_out=50)
            movido = servicio.espectro(269.45, 4.77, apertura=6, anillo_in=30, anillo_out=50,
                                       pmra=0, pmdec=12000, epoca=2025.0)
        self.assertGreater(movido["puntos"][0]["flujo"], 3 * quieto["puntos"][0]["flujo"])
        self.assertEqual(movido["puntos"][0]["epoca"], "E1")
        self.assertEqual(movido["unidad_flujo"], "mJy")


if __name__ == "__main__":
    unittest.main()
