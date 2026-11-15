"""T16: deja listos en la caché los 5 objetivos de prueba, para que la demo no dependa de IRSA.

Qué hace: para cada objetivo y cada detector llama a /epocas y /frames por dentro (sin servidor),
así quedan guardados en la carpeta de caché (CACHE_DIR, por defecto backend/cache/).

IMPORTANTE (movimiento propio): para Barnard's Star, Epsilon Indi B y WISE 0855 la página no
pide las coordenadas de catálogo, sino las de HOY (las corrige por el movimiento de la estrella,
ver propagarProperMotion en frontend/src/lib/coords.ts). Este script hace la misma cuenta para
hoy y los próximos días (--dias), para que la página encuentre justo esas búsquedas en la caché.
Conviene correrlo el mismo día de la demo o el anterior.

Uso (desde la carpeta backend, con el entorno .venv activado):

    python -m scripts.precalcular                     # 5 objetivos, 6 detectores, fov 0.1
    python -m scripts.precalcular --detectores D2     # solo D2 (más rápido)
    python -m scripts.precalcular --objetivos barnard wise0855
"""

import argparse
import logging
import math
import time
from datetime import datetime, timedelta, timezone

from app import servicio
from app.errores import ErrorApi

DETECTORES = ["D1", "D2", "D3", "D4", "D5", "D6"]

# Coordenadas J2000 (grados) y movimiento propio (milisegundos de arco por año), copiados de
# frontend/src/lib/objects.ts para que el cálculo sea idéntico al de la página.
OBJETIVOS = {
    "barnard": ("Barnard's Star", 269.4521, 4.6934, -798.6, 10328.1),
    "epsindib": ("Epsilon Indi B", 331.044, -56.783, 3960.0, -2538.0),
    "wise0855": ("WISE 0855", 133.7951, -7.2452, -8100.0, 700.0),
    "rwaur": ("RW Aurigae", 76.9573, 30.4015, 0.0, 0.0),
    "rdra": ("R Draconis", 248.178, 66.755, 0.0, 0.0),
}


def anio_decimal(fecha: datetime) -> float:
    """Igual que currentDecimalYear() de la página: 2026.87 = noviembre de 2026."""
    inicio = datetime(fecha.year, 1, 1, tzinfo=timezone.utc)
    fin = datetime(fecha.year + 1, 1, 1, tzinfo=timezone.utc)
    return fecha.year + (fecha - inicio) / (fin - inicio)


def propagar(ra: float, dec: float, pmra: float, pmdec: float, anio: float) -> tuple[float, float]:
    """Igual que propagarProperMotion() de la página (época de catálogo 2000)."""
    anios = anio - 2000
    nueva_dec = dec + pmdec * anios / 3_600_000
    nueva_ra = ra + pmra * anios / (3_600_000 * (math.cos(math.radians(dec)) or 1))
    return nueva_ra % 360, nueva_dec


def main() -> None:
    parser = argparse.ArgumentParser(description="Precalcula los 5 objetivos de prueba.")
    parser.add_argument("--objetivos", nargs="+", default=list(OBJETIVOS), choices=list(OBJETIVOS))
    parser.add_argument("--detectores", nargs="+", default=DETECTORES, choices=DETECTORES)
    parser.add_argument("--fov", type=float, default=0.1, help="grados (la página usa 0.1 = 6')")
    parser.add_argument("--dias", type=int, default=2, help="también los próximos N días")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    ahora = datetime.now(timezone.utc)
    fallos = 0
    for clave in args.objetivos:
        nombre, ra0, dec0, pmra, pmdec = OBJETIVOS[clave]
        # Centros distintos que pedirá la página entre hoy y dentro de --dias días.
        centros = []
        for dia in range(args.dias + 1):
            ra, dec = propagar(ra0, dec0, pmra, pmdec, anio_decimal(ahora + timedelta(days=dia)))
            if (round(ra, 4), round(dec, 4)) not in [(round(r, 4), round(d, 4)) for r, d in centros]:
                centros.append((ra, dec))

        for ra, dec in centros:
            for det in args.detectores:
                inicio = time.time()
                try:
                    respuesta = servicio.frames(ra, dec, args.fov, det)
                    print(
                        f"OK    {nombre:15s} {det}  ra={ra:.5f} dec={dec:.5f}  "
                        f"{len(respuesta['frames'])} épocas  ({time.time() - inicio:.0f} s)"
                    )
                except ErrorApi as error:
                    fallos += 1
                    print(f"FALLO {nombre:15s} {det}  ({error.codigo}) {error.mensaje}")

    print("Listo." if fallos == 0 else f"Terminó con {fallos} fallos: vuelve a correrlo.")


if __name__ == "__main__":
    main()
