"""Descarga muchos recortes de SPHEREx al mismo tiempo, con reintentos.

Truco importante: un recorte completo pesa ~3.9 MB aunque la imagen sea pequeña, porque al
final trae una tabla enorme (EPSF) que no usamos para las imágenes. Por defecto cortamos la
descarga justo antes de esa tabla: quedan ~125 KB con las extensiones IMAGE, FLAGS, VARIANCE
y ZODI. Con completo=True se baja todo (hace falta para el espectro: WCS-WAVE va después).

Para probar a mano (desde la carpeta backend, con el entorno .venv activado):

    python -m app.datos.descargas
"""

import asyncio
import io
import logging

import httpx
from astropy.io import fits

registro = logging.getLogger(__name__)

# Así empieza la cabecera de una tabla binaria en un archivo FITS. En los recortes de SPHEREx
# la primera tabla es EPSF; todo lo anterior son las imágenes que sí necesitamos.
MARCA_TABLA = b"XTENSION= 'BINTABLE'"
BLOQUE_FITS = 2880  # un FITS está hecho de bloques de 2880 bytes

TIEMPO_LIMITE_S = 120
INTENTOS = 3


def cortar_antes_de_tabla(datos: bytes) -> bytes:
    """Devuelve el FITS sin las tablas del final (deja solo las extensiones de imagen).

    Si no encuentra ninguna tabla, devuelve los datos tal cual.
    """
    posicion = datos.find(MARCA_TABLA)
    # La cabecera de cada extensión empieza siempre al inicio de un bloque.
    while posicion > 0 and posicion % BLOQUE_FITS != 0:
        posicion = datos.find(MARCA_TABLA, posicion + 1)
    if posicion <= 0:
        return bytes(datos)
    return bytes(datos[:posicion])


async def _descargar_uno(
    cliente: httpx.AsyncClient,
    semaforo: asyncio.Semaphore,
    url: str,
    completo: bool,
    espera_reintento: float,
) -> bytes | None:
    """Descarga un recorte. Devuelve None si falla después de varios intentos."""
    async with semaforo:  # limita cuántas descargas corren a la vez
        for intento in range(1, INTENTOS + 1):
            try:
                datos = bytearray()
                async with cliente.stream("GET", url) as respuesta:
                    respuesta.raise_for_status()
                    async for trozo in respuesta.aiter_bytes():
                        datos.extend(trozo)
                        if not completo and MARCA_TABLA in datos:
                            # Ya llegó la parte de las imágenes: dejamos de descargar.
                            break
                return bytes(datos) if completo else cortar_antes_de_tabla(bytes(datos))
            except httpx.HTTPError as error:
                registro.warning(
                    "Intento %s de %s falló para %s: %r", intento, INTENTOS, url, error
                )
                if intento < INTENTOS:
                    # Espera creciente: 1x, 2x... para no saturar a IRSA.
                    await asyncio.sleep(espera_reintento * intento)
        registro.error("No se pudo descargar %s", url)
        return None


async def descargar_recortes(
    urls: list[str],
    max_concurrentes: int = 8,
    completo: bool = False,
    espera_reintento: float = 2.0,
    cliente: httpx.AsyncClient | None = None,
) -> list[bytes | None]:
    """Descarga los recortes de la lista de URLs, varios a la vez.

    Devuelve una lista del MISMO tamaño y en el MISMO orden que `urls`. Si un recorte falla,
    en su lugar queda None (se registra el error y se sigue con los demás).

    Parámetros:
        urls: direcciones de recorte (las que devuelve buscar_imagenes).
        max_concurrentes: cuántas descargas simultáneas se permiten.
        completo: False = solo las extensiones de imagen (rápido); True = archivo entero.
        espera_reintento: segundos de espera base entre reintentos.
        cliente: solo para pruebas; normalmente se deja en None.
    """
    semaforo = asyncio.Semaphore(max_concurrentes)
    cliente_propio = cliente is None
    if cliente is None:
        cliente = httpx.AsyncClient(timeout=TIEMPO_LIMITE_S, follow_redirects=True)
    try:
        tareas = [
            _descargar_uno(cliente, semaforo, url, completo, espera_reintento) for url in urls
        ]
        return list(await asyncio.gather(*tareas))
    finally:
        if cliente_propio:
            await cliente.aclose()


def abrir_recorte(datos: bytes) -> fits.HDUList:
    """Abre los bytes de un recorte como un FITS de Astropy.

    Uso:
        with abrir_recorte(datos) as hdul:
            imagen = hdul["IMAGE"].data
    """
    return fits.open(io.BytesIO(datos))


if __name__ == "__main__":
    # Prueba manual: descarga todos los recortes de Barnard's Star (detector D2) y mide el tiempo.
    import time

    from app.datos.irsa import buscar_imagenes

    logging.basicConfig(level=logging.WARNING)
    imagenes = buscar_imagenes(ra=269.4521, dec=4.6934, fov_grados=0.1, detector="D2")
    lista_urls = [imagen["url_recorte"] for imagen in imagenes]
    print(f"Descargando {len(lista_urls)} recortes...")

    inicio = time.time()
    resultados = asyncio.run(descargar_recortes(lista_urls))
    segundos = time.time() - inicio

    buenos = [r for r in resultados if r is not None]
    total_mb = sum(len(r) for r in buenos) / 1024 / 1024
    print(f"Descargados: {len(buenos)} de {len(lista_urls)} en {segundos:.1f} s ({total_mb:.1f} MB)")
    if buenos:
        with abrir_recorte(buenos[0]) as hdul:
            print("Extensiones del primero:", [hdu.name for hdu in hdul])
            print("Tamaño de IMAGE:", hdul["IMAGE"].data.shape)
