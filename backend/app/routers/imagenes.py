"""Endpoints del contrato (docs/api.md): /resolve, /epocas, /frames, /diff y /spectrum.

Aquí solo se leen y validan los parámetros; el trabajo lo hace app/servicio.py.
FastAPI corre estas funciones (definidas con `def`, no `async def`) en hilos aparte, así una
búsqueda lenta no bloquea a las demás.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app import servicio

router = APIRouter()

# Parámetros comunes (ver "Parámetros comunes" en docs/api.md). Si un valor no cumple estas
# reglas, FastAPI responde 422 y main.py lo convierte en {"error": "..."}.
Ra = Annotated[float, Query(ge=0, lt=360, description="Ascensión recta en grados (ICRS)")]
Dec = Annotated[float, Query(ge=-90, le=90, description="Declinación en grados (ICRS)")]
Fov = Annotated[float, Query(ge=0.01, description="Campo de visión en grados")]
Det = Annotated[
    Literal["D1", "D2", "D3", "D4", "D5", "D6"], Query(description="Detector de SPHEREx")
]


@router.get("/resolve")
def resolve(name: Annotated[str, Query(min_length=1, description="Nombre del objeto")]):
    """Convierte el nombre de un objeto en coordenadas."""
    return servicio.resolver(name)


@router.get("/epocas")
def epocas(ra: Ra, dec: Dec, fov: Fov = 0.1, det: Det = "D2"):
    """Dice en qué épocas hay imágenes de esa zona."""
    return {"epocas": servicio.resumen_epocas(servicio.epocas(ra, dec, fov, det))}


@router.get("/frames")
def frames(ra: Ra, dec: Dec, fov: Fov = 0.1, det: Det = "D2"):
    """Entrega una imagen PNG por época, lista para animar."""
    return servicio.frames(ra, dec, fov, det)


@router.get("/diff")
def diff(
    ra: Ra,
    dec: Dec,
    a: Annotated[str, Query(description="Primera época, por ejemplo E1")],
    b: Annotated[str, Query(description="Segunda época, por ejemplo E3")],
    fov: Fov = 0.1,
    det: Det = "D2",
):
    """Entrega la imagen de diferencia (época b menos época a)."""
    return servicio.diferencia(ra, dec, fov, det, a, b)


@router.get("/spectrum")
def spectrum(
    ra: Ra,
    dec: Dec,
    apertura: Annotated[float, Query(gt=0, le=60, description="Radio de la apertura en arcsec")] = 18.0,
    anillo_in: Annotated[float, Query(gt=0, le=60, description="Radio interior del anillo de fondo (arcsec)")] = 30.0,
    anillo_out: Annotated[float, Query(gt=0, le=60, description="Radio exterior del anillo de fondo (arcsec)")] = 50.0,
    fondo: Annotated[bool, Query(description="Restar el fondo del anillo")] = True,
    pmra: Annotated[float, Query(description="Movimiento propio en RA·cos(Dec), mas/año")] = 0.0,
    pmdec: Annotated[float, Query(description="Movimiento propio en Dec, mas/año")] = 0.0,
    epoca: Annotated[float | None, Query(ge=2000, le=2100, description="Año decimal de ra/dec (para el movimiento propio)")] = None,
):
    """Entrega el espectro del punto: brillo contra longitud de onda, un punto por imagen."""
    return servicio.espectro(ra, dec, apertura, anillo_in, anillo_out, fondo, pmra, pmdec, epoca)
