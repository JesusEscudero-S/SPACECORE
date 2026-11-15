"""Pruebas de app/datos/epocas.py con datos falsos (no usan internet).

Para correrlas (desde la carpeta backend, con el entorno .venv activado):

    python -m unittest discover -v
"""

import unittest

from app.datos.epocas import agrupar_por_epoca, mjd_a_iso, separar_por_detector


def _imagen(mjd: float, detector: str = "D2") -> dict:
    return {"mjd": mjd, "fecha_obs": mjd_a_iso(mjd), "detector": detector, "url_recorte": f"u{mjd}"}


# Fechas reales (MJD) de Barnard's Star en el detector D2, resumidas: tres pasadas de SPHEREx.
BARNARD = [60908.982, 60911.491, 60914.276, 60917.674, 61114.032, 61116.68, 61121.228,
           61270.867, 61271.342, 61273.654]


class PruebasEpocas(unittest.TestCase):
    def test_tres_epocas_como_barnard(self):
        epocas = agrupar_por_epoca([_imagen(m) for m in BARNARD])
        self.assertEqual([e["id"] for e in epocas], ["E1", "E2", "E3"])
        self.assertEqual([e["n_imagenes"] for e in epocas], [4, 3, 3])
        self.assertEqual(sum(e["n_imagenes"] for e in epocas), len(BARNARD))

    def test_fechas_de_cada_epoca(self):
        epoca = agrupar_por_epoca([_imagen(60908.0), _imagen(60910.0)])[0]
        self.assertEqual(epoca["inicio"], "2025-08-21T00:00:00Z")
        self.assertEqual(epoca["fin"], "2025-08-23T00:00:00Z")
        self.assertEqual(epoca["fecha"], "2025-08-22T00:00:00Z")  # punto medio

    def test_ordena_aunque_lleguen_desordenadas(self):
        epocas = agrupar_por_epoca([_imagen(61114.0), _imagen(60908.0), _imagen(60909.0)])
        self.assertEqual([e["n_imagenes"] for e in epocas], [2, 1])
        mjds = [i["mjd"] for i in epocas[0]["imagenes"]]
        self.assertEqual(mjds, sorted(mjds))

    def test_el_hueco_decide_el_corte(self):
        imagenes = [_imagen(61000.0), _imagen(61030.0), _imagen(61060.5)]
        # 30 días exactos NO cortan; 30.5 sí.
        self.assertEqual([e["n_imagenes"] for e in agrupar_por_epoca(imagenes)], [2, 1])
        self.assertEqual(len(agrupar_por_epoca(imagenes, hueco_dias=10)), 3)
        self.assertEqual(len(agrupar_por_epoca(imagenes, hueco_dias=100)), 1)

    def test_lista_vacia_y_una_sola_imagen(self):
        self.assertEqual(agrupar_por_epoca([]), [])
        epocas = agrupar_por_epoca([_imagen(60908.0)])
        self.assertEqual(len(epocas), 1)
        self.assertEqual(epocas[0]["inicio"], epocas[0]["fin"])

    def test_separar_por_detector(self):
        imagenes = [_imagen(61000.0, "D2"), _imagen(61001.0, "D5"), _imagen(61002.0, "D2")]
        por_detector = separar_por_detector(imagenes)
        self.assertEqual(sorted(por_detector), ["D2", "D5"])
        self.assertEqual(len(por_detector["D2"]), 2)


if __name__ == "__main__":
    unittest.main()
