"""T16: deja listos en la caché los 5 objetivos de prueba, para que la demo no dependa de IRSA.

Qué hace: para cada objetivo y cada detector llama a /epocas y /frames por dentro (sin servidor),
y después prepara el espectro (/spectrum, T36) del objetivo. Así queda todo guardado en la
carpeta de caché (CACHE_DIR, por defecto backend/cache/).

IMPORTANTE (movimiento propio): para Barnard's Star, Epsilon Indi B y WISE 0855 la página no
pide las coordenadas de catálogo, sino su posición al 1 DE ENERO DEL AÑO EN CURSO (las corrige
por el movimiento de la estrella; ver epocaDeCentrado en frontend/src/App.ts y
propagarProperMotion en frontend/src/lib/coords.ts). Este script hace exactamente la misma
cuenta, así que lo precalculado sirve todo el año (también para la evaluación de diciembre).
Solo hay que volver a correrlo a partir del 1 de enero.

Uso (desde la carpeta backend, con el entorno .venv activado):

    python -m scripts.precalcular                     # 5 objetivos, 6 detectores, fov 0.1
    python -m scripts.precalcular --detectores D2     # solo D2 (más rápido)
    python -m scripts.precalcular --objetivos barnard wise0855
    python -m scripts.precalcular --sin-espectro      # solo las imágenes
"""

import argparse
import logging
import math
import time
from datetime import datetime, timezone

from app import servicio
from app.errores import ErrorApi

DETECTORES = ["D1", "D2", "D3", "D4", "D5", "D6"]
INTENTOS = 3  # pasadas por detector si IRSA falla con alguna imagen

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


def epoca_de_centrado(fecha: datetime) -> float:
    """Igual que epocaDeCentrado() de frontend/src/App.ts: el 1 de enero del año en curso."""
    return float(math.floor(anio_decimal(fecha)))


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
    parser.add_argument("--sin-espectro", action="store_true", help="no preparar /spectrum")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    ahora = datetime.now(timezone.utc)
    fallos = 0
    for clave in args.objetivos:
        nombre, ra0, dec0, pmra, pmdec = OBJETIVOS[clave]
        # El mismo centro que pedirá la página durante todo el año (ver epoca_de_centrado).
        centros = [propagar(ra0, dec0, pmra, pmdec, epoca_de_centrado(ahora))]

        for ra, dec in centros:
            for det in args.detectores:
                # IRSA a veces responde 503 a una que otra imagen: entonces el resultado no se
                # guarda. Reintentamos hasta INTENTOS veces (cada pasada vuelve a bajar ese
                # detector, ~20 s; los detectores que ya quedaron guardados salen en 0 s).
                inicio = time.time()
                mensaje = ""
                for _ in range(INTENTOS):
                    try:
                        respuesta = servicio.frames(ra, dec, args.fov, det)
                        mensaje = f"{len(respuesta['frames'])} épocas"
                    except ErrorApi as error:
                        mensaje = f"({error.codigo}) {error.mensaje}"
                    if servicio.pila_en_cache(ra, dec, args.fov, det):
                        break
                if servicio.pila_en_cache(ra, dec, args.fov, det):
                    print(f"OK    {nombre:15s} {det}  ra={ra:.5f} dec={dec:.5f}  {mensaje}  ({time.time() - inicio:.0f} s)")
                else:
                    fallos += 1
                    print(f"FALLO {nombre:15s} {det}  no quedó en la caché (IRSA falló en algunas imágenes) {mensaje}")

            if args.sin_espectro:
                continue
            inicio = time.time()
            mensaje = ""
            for _ in range(INTENTOS):
                try:
                    meta, _, _ = servicio.estampillas(ra, dec)
                    mensaje = f"{len(meta)} imágenes"
                except ErrorApi as error:
                    mensaje = f"({error.codigo}) {error.mensaje}"
                if servicio.estampillas_en_cache(ra, dec):
                    break
            if servicio.estampillas_en_cache(ra, dec):
                print(f"OK    {nombre:15s} espectro  {mensaje}  ({time.time() - inicio:.0f} s)")
            else:
                fallos += 1
                print(f"FALLO {nombre:15s} espectro  no quedó en la caché (IRSA falló en algunas imágenes) {mensaje}")

    print("Listo." if fallos == 0 else f"Terminó con {fallos} fallos: vuelve a correrlo.")


if __name__ == "__main__":
    main()
