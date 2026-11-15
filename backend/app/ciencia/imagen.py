"""Convierte una imagen científica (matriz de números) en un PNG que se ve bien.

Una imagen de SPHEREx es una matriz de brillos en MJy/sr. Para mostrarla hay que decidir qué
brillo será negro y cuál blanco (vmin y vmax) y "estirar" los valores, porque las estrellas
brillantes son miles de veces más intensas que el fondo.

Para probar a mano (desde la carpeta backend, con el entorno .venv activado):

    python -m app.ciencia.imagen

Eso descarga un recorte real de Barnard's Star y guarda notebooks/salidas/barnard_D2.png
"""

import base64
import io

import numpy as np
from astropy.visualization import AsinhStretch, ManualInterval
from PIL import Image


def limites_brillo(
    imagenes: list[np.ndarray], percentil_bajo: float = 1.0, percentil_alto: float = 99.5
) -> tuple[float, float]:
    """Calcula vmin y vmax comunes para una lista de imágenes.

    Importante: todas las épocas de una búsqueda deben usar los MISMOS límites, para que al
    animarlas un cambio de brillo sea real y no un efecto de la escala.

    Usamos percentiles en vez del mínimo y el máximo para que unos pocos píxeles defectuosos
    (muy brillantes o muy oscuros) no arruinen el contraste.
    """
    validos = []
    for imagen in imagenes:
        datos = np.asarray(imagen, dtype=float)
        validos.append(datos[np.isfinite(datos)].ravel())
    valores = np.concatenate(validos) if validos else np.array([])
    if valores.size == 0:
        return 0.0, 1.0
    vmin, vmax = np.percentile(valores, [percentil_bajo, percentil_alto])
    if vmax <= vmin:
        vmax = vmin + 1.0
    return float(vmin), float(vmax)


def a_png(
    datos: np.ndarray,
    vmin: float,
    vmax: float,
    tamano: int | None = None,
    invertir: bool = False,
) -> bytes:
    """Convierte una imagen (matriz 2D) en los bytes de un PNG en escala de grises.

    Parámetros:
        datos: matriz 2D con el brillo de cada píxel. Puede traer NaN (píxeles sin dato).
        vmin, vmax: brillo que se pinta negro y brillo que se pinta blanco.
        tamano: si se da, la imagen se agranda o reduce a tamano x tamano píxeles. Con None
            (lo normal) se respeta la escala real: un píxel del PNG = un píxel de SPHEREx.
        invertir: True para fondo blanco y estrellas negras (como WiseView).
    """
    datos = np.asarray(datos, dtype=float)
    if datos.ndim != 2:
        raise ValueError(f"La imagen debe tener 2 dimensiones, tiene {datos.ndim}.")

    # Los píxeles sin dato (NaN o infinito) se pintan como el fondo.
    datos = np.where(np.isfinite(datos), datos, vmin)

    # Paso 1: llevar los brillos al rango 0..1 (vmin -> 0, vmax -> 1; lo que se sale se recorta).
    # Paso 2: estiramiento asinh, casi lineal para lo débil y comprimido para lo muy brillante.
    # (Usamos ManualInterval + AsinhStretch en vez de ImageNormalize porque esta última
    # necesita matplotlib, que no está en nuestras librerías.)
    intervalo = ManualInterval(vmin=vmin, vmax=vmax)
    estirar = AsinhStretch()
    escalado = np.asarray(estirar(intervalo(datos, clip=True)), dtype=float)  # valores 0..1

    grises = np.round(escalado * 255).astype(np.uint8)
    if invertir:
        grises = 255 - grises

    # En un FITS la fila 0 es la de ABAJO; en un PNG la fila 0 es la de ARRIBA. Volteamos
    # para que el norte quede arriba.
    grises = np.flipud(grises)

    imagen = Image.fromarray(grises, mode="L")
    if tamano is not None:
        # NEAREST conserva los píxeles nítidos (sin difuminar) al cambiar de tamaño.
        imagen = imagen.resize((tamano, tamano), resample=Image.NEAREST)

    salida = io.BytesIO()
    imagen.save(salida, format="PNG")
    return salida.getvalue()


def a_data_url(png: bytes) -> str:
    """Convierte los bytes de un PNG en un texto "data:image/png;base64,..." (formato del contrato)."""
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


if __name__ == "__main__":
    # Prueba manual: un recorte real de Barnard's Star convertido a PNG.
    from pathlib import Path

    import httpx
    from astropy.io import fits

    from app.datos.irsa import buscar_imagenes

    imagenes = buscar_imagenes(ra=269.4521, dec=4.6934, fov_grados=0.1, detector="D2")
    print(f"Imágenes disponibles: {len(imagenes)}. Descargando la primera...")
    respuesta = httpx.get(imagenes[0]["url_recorte"], timeout=120, follow_redirects=True)
    respuesta.raise_for_status()
    with fits.open(io.BytesIO(respuesta.content)) as hdul:
        datos = hdul["IMAGE"].data.astype(float)

    vmin, vmax = limites_brillo([datos])
    png = a_png(datos, vmin, vmax)

    carpeta = Path(__file__).resolve().parents[3] / "notebooks" / "salidas"
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / "barnard_D2.png"
    destino.write_bytes(png)
    print(f"Imagen de {datos.shape[1]} x {datos.shape[0]} píxeles, vmin={vmin:.3f}, vmax={vmax:.3f} MJy/sr")
    print(f"PNG guardado en {destino} ({len(png)} bytes)")
