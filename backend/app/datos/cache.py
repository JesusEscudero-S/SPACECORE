"""Caché: guarda resultados ya calculados para no pedirlos otra vez a IRSA.

REGLA: el resto del código solo debe usar las funciones de este archivo (crear_clave, get, set,
get_bytes, set_bytes). Así, si después cambiamos dónde se guarda, solo se cambia este archivo.

Uso típico:

    from app.datos import cache

    clave = cache.crear_clave("frames", ra, dec, fov, detector)
    datos = cache.get(clave)
    if datos is None:
        datos = calcular_algo_lento()
        cache.set(clave, datos)

Dónde se guarda (dos capas):

    1. Redis, si la variable de entorno REDIS_URL está definida y Redis responde. Es memoria:
       muy rápido. Con Docker (docker-compose.yml) siempre está encendido.
    2. Disco, en la carpeta CACHE_DIR (por defecto backend/cache/, ignorada por git). Siempre.

    - Al GUARDAR se escribe en las dos: si Redis se reinicia y pierde su memoria, el disco
      conserva todo.
    - Al LEER se busca primero en Redis; si no está, en disco (y se vuelve a subir a Redis).
    - Si Redis no está o falla, se usa solo el disco, SIN error. Así funciona igual en Windows
      sin Docker y en Cloud Run (que no tiene Redis).
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path

from app.config import settings

registro = logging.getLogger(__name__)


# ============================================================================ claves


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


def _validar(clave: str) -> None:
    # La clave se usa como nombre de archivo: solo aceptamos letras y números.
    if not clave or not clave.isalnum():
        raise ValueError(f"Clave de caché inválida: {clave!r}")


# ============================================================================ capa 1: Redis

# Prefijo de todas nuestras claves en Redis, para no mezclarlas con las de otros programas.
PREFIJO_REDIS = "spacecore:"

# Si Redis falla, no lo volvemos a intentar durante este tiempo (para no hacer lenta cada
# petición esperando a un Redis apagado).
PAUSA_TRAS_FALLO_S = 30

_cliente_redis = None  # la conexión, creada la primera vez que se necesita
_url_conectada = ""  # para qué REDIS_URL se creó (si cambia, se crea otra)
_redis_pausado_hasta = 0.0  # momento hasta el que no se intenta usar Redis


def _redis():
    """Devuelve la conexión a Redis, o None si no hay Redis configurado o está fallando."""
    global _cliente_redis, _url_conectada
    url = settings.redis_url
    if not url or time.monotonic() < _redis_pausado_hasta:
        return None
    if _cliente_redis is None or url != _url_conectada:
        try:
            import redis  # se importa aquí: sin Redis configurado, ni siquiera hace falta
        except ImportError:
            registro.warning("REDIS_URL está definida pero falta la librería redis: uso solo disco.")
            _pausar_redis()
            return None
        _cliente_redis = redis.Redis.from_url(
            url,
            socket_connect_timeout=0.5,  # si Redis no contesta rápido, mejor seguir con disco
            socket_timeout=2,
        )
        _url_conectada = url
        registro.info("Caché: usando Redis (%s) y disco (%s).", url, settings.cache_dir)
    return _cliente_redis


def _pausar_redis(error: Exception | None = None) -> None:
    global _redis_pausado_hasta
    if error is not None:
        registro.warning(
            "Redis no respondió (%r). Uso solo el disco durante %s s.", error, PAUSA_TRAS_FALLO_S
        )
    _redis_pausado_hasta = time.monotonic() + PAUSA_TRAS_FALLO_S


def _redis_leer(nombre: str) -> bytes | None:
    cliente = _redis()
    if cliente is None:
        return None
    try:
        return cliente.get(PREFIJO_REDIS + nombre)
    except Exception as error:  # cualquier falla de Redis: seguimos con el disco
        _pausar_redis(error)
        return None


def _redis_escribir(nombre: str, contenido: bytes) -> None:
    cliente = _redis()
    if cliente is None:
        return
    try:
        segundos = int(settings.redis_ttl_horas * 3600)
        # ex = cuántos segundos dura la clave. Con 0 o menos, no caduca.
        cliente.set(PREFIJO_REDIS + nombre, contenido, ex=segundos if segundos > 0 else None)
    except Exception as error:
        _pausar_redis(error)


# ============================================================================ capa 2: disco


def _ruta(nombre: str) -> Path:
    return Path(settings.cache_dir) / nombre


def _disco_leer(nombre: str) -> bytes | None:
    ruta = _ruta(nombre)
    if not ruta.exists():
        return None
    try:
        return ruta.read_bytes()
    except OSError:
        return None


def _disco_escribir(nombre: str, contenido: bytes) -> None:
    """Escribe el archivo de forma segura: primero a un temporal y luego lo renombra.

    Así nunca queda un archivo a medias si el programa se corta mientras escribe.
    """
    ruta = _ruta(nombre)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    temporal.write_bytes(contenido)
    os.replace(temporal, ruta)


# ============================================================================ las dos juntas


def _leer(nombre: str) -> bytes | None:
    contenido = _redis_leer(nombre)
    if contenido is not None:
        return contenido
    contenido = _disco_leer(nombre)
    if contenido is not None:
        _redis_escribir(nombre, contenido)  # la próxima vez saldrá de Redis
    return contenido


def _escribir(nombre: str, contenido: bytes) -> None:
    _disco_escribir(nombre, contenido)
    _redis_escribir(nombre, contenido)


# ============================================================================ uso público


def get(clave: str):
    """Devuelve los datos guardados con esa clave, o None si no hay nada."""
    _validar(clave)
    contenido = _leer(f"{clave}.json")
    if contenido is None:
        return None
    try:
        return json.loads(contenido.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        # Dato dañado: lo tratamos como si no existiera.
        return None


def set(clave: str, datos) -> None:  # noqa: A001 (el nombre "set" lo pide el diseño del proyecto)
    """Guarda datos (diccionarios, listas, textos, números) con esa clave.

    Los PNG se guardan como texto "data:image/png;base64,..." dentro de los datos.
    """
    _validar(clave)
    _escribir(f"{clave}.json", json.dumps(datos, ensure_ascii=False).encode("utf-8"))


def get_bytes(clave: str) -> bytes | None:
    """Como get, pero para datos binarios (por ejemplo, un recorte FITS)."""
    _validar(clave)
    return _leer(f"{clave}.bin")


def set_bytes(clave: str, datos: bytes) -> None:
    """Como set, pero para datos binarios."""
    _validar(clave)
    _escribir(f"{clave}.bin", bytes(datos))
