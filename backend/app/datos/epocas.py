"""Agrupa las imágenes de SPHEREx en épocas.

SPHEREx vuelve a pasar por cada zona del cielo más o menos cada 6 meses. Por eso las imágenes
de un punto llegan en grupos de pocos días, separados por meses. Cada grupo es una "época".

Para probar (desde la carpeta backend, con el entorno .venv activado):

    python -m unittest discover -v
"""

from astropy.time import Time

# Si entre dos imágenes consecutivas pasan más días que esto, empieza una época nueva.
HUECO_DIAS = 30.0


def mjd_a_iso(mjd: float) -> str:
    """Convierte una fecha MJD (días) al texto ISO en UTC del contrato: "2025-08-21T23:33:58Z"."""
    return Time(float(mjd), format="mjd", scale="utc").strftime("%Y-%m-%dT%H:%M:%SZ")


def agrupar_por_epoca(imagenes: list[dict], hueco_dias: float = HUECO_DIAS) -> list[dict]:
    """Agrupa una lista de imágenes en épocas según su fecha.

    Parámetros:
        imagenes: lista como la que devuelve buscar_imagenes (cada una con "mjd" y "fecha_obs").
            Deben ser de UN solo detector (ver separar_por_detector).
        hueco_dias: separación mínima, en días, para considerar que empieza otra época.

    Devuelve una lista ordenada de la época más antigua a la más reciente. Cada época es:
        {
            "id":         "E1", "E2"... (E1 es la más antigua),
            "inicio":     fecha de la primera imagen (texto ISO en UTC),
            "fin":        fecha de la última imagen,
            "fecha":      punto medio entre inicio y fin (la fecha que se muestra en el cuadro),
            "n_imagenes": cuántas imágenes tiene,
            "imagenes":   las imágenes de esa época, ordenadas por fecha,
        }
    """
    ordenadas = sorted(imagenes, key=lambda imagen: imagen["mjd"])

    # Paso 1: partir la lista en grupos cada vez que hay un hueco grande.
    grupos: list[list[dict]] = []
    for imagen in ordenadas:
        if grupos and imagen["mjd"] - grupos[-1][-1]["mjd"] <= hueco_dias:
            grupos[-1].append(imagen)
        else:
            grupos.append([imagen])

    # Paso 2: describir cada grupo.
    epocas = []
    for numero, grupo in enumerate(grupos, start=1):
        mjd_inicio = grupo[0]["mjd"]
        mjd_fin = grupo[-1]["mjd"]
        epocas.append(
            {
                "id": f"E{numero}",
                "inicio": mjd_a_iso(mjd_inicio),
                "fin": mjd_a_iso(mjd_fin),
                "fecha": mjd_a_iso((mjd_inicio + mjd_fin) / 2),
                "n_imagenes": len(grupo),
                "imagenes": grupo,
            }
        )
    return epocas


def separar_por_detector(imagenes: list[dict]) -> dict[str, list[dict]]:
    """Reparte una lista con imágenes de varios detectores en un diccionario {"D1": [...], ...}."""
    por_detector: dict[str, list[dict]] = {}
    for imagen in imagenes:
        por_detector.setdefault(imagen["detector"], []).append(imagen)
    return por_detector
