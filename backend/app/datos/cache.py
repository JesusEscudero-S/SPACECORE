"""Caché: guarda resultados ya calculados para no pedirlos otra vez a IRSA.

REGLA: el resto del código solo debe usar las funciones de este archivo (crear_clave, get, set,
get_bytes, set_bytes). Así, si después cambiamos el disco por un bucket en la nube, solo se
cambia este archivo.

Uso típico:

    from app.datos import cache

    clave = cache.crear_clave("frames", ra, dec, fov, detector)
    datos = cache.get(clave)
    if datos is None:
        datos = calcular_algo_lento()
        cache.set(clave, datos)

Esta versión guarda archivos en la carpeta cache/ (ignorada por git). La carpeta se puede
cambiar con la variable de entorno CACHE_DIR.
"""

import hashlib
import json
import os
from pathlib import Path

from app.config import settings


def crear_clave(tipo: str, ra: float, dec: float, fov: float = 0.0, detector: str = "") -> str:
    """Crea la clave (un texto único) de una búsqueda.

    Dos búsquedas iguales dan la misma clave. RA y Dec se redondean a 4 decimales (unos 0.4
    segundos de arco), así dos búsquedas casi idénticas comparten resultado. La colección de
    datos forma parte de la clave: si cambia la colección, no se reutilizan resultados viejos.

    `tipo` distingue qué se guarda: "epocas", "frames", "diff", "spectrum", "resolve"...
    """
    texto = "|".join(
        [
            settings.coleccion_spherex,
            f"{round(float(ra), 4):.4f}",
            f"{round(float(dec), 4):.4f}",
            f"{float(fov):.4f}",
            detector,
            tipo,
        ]
    )
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:32]


def clave_de_texto(tipo: str, texto: str) -> str:
    """Crea una clave a partir de un texto cualquiera (por ejemplo, una URL o un nombre)."""
    completo = f"{settings.coleccion_spherex}|{tipo}|{texto}"
    return hashlib.sha256(completo.encode("utf-8")).hexdigest()[:32]


def _ruta(clave: str, extension: str) -> Path:
    # La clave se usa como nombre de archivo: solo aceptamos letras y números.
    if not clave or not clave.isalnum():
        raise ValueError(f"Clave de caché inválida: {clave!r}")
    return Path(settings.cache_dir) / f"{clave}.{extension}"


def _escribir(ruta: Path, contenido: bytes) -> None:
    """Escribe el archivo de forma segura: primero a un temporal y luego lo renombra.

    Así nunca queda un archivo a medias si el programa se corta mientras escribe.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    temporal.write_bytes(contenido)
    os.replace(temporal, ruta)


def get(clave: str):
    """Devuelve los datos guardados con esa clave, o None si no hay nada."""
    ruta = _ruta(clave, "json")
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # Archivo dañado: lo tratamos como si no existiera.
        return None


def set(clave: str, datos) -> None:  # noqa: A001 (el nombre "set" lo pide el diseño del proyecto)
    """Guarda datos (diccionarios, listas, textos, números) con esa clave.

    Los PNG se guardan como texto "data:image/png;base64,..." dentro de los datos.
    """
    _escribir(_ruta(clave, "json"), json.dumps(datos, ensure_ascii=False).encode("utf-8"))


def get_bytes(clave: str) -> bytes | None:
    """Como get, pero para datos binarios (por ejemplo, un recorte FITS)."""
    ruta = _ruta(clave, "bin")
    if not ruta.exists():
        return None
    try:
        return ruta.read_bytes()
    except OSError:
        return None


def set_bytes(clave: str, datos: bytes) -> None:
    """Como set, pero para datos binarios."""
    _escribir(_ruta(clave, "bin"), datos)
