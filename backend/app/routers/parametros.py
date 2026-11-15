"""Parámetros comunes de los endpoints de búsqueda: ra, dec, fov y det.

FastAPI revisa solo los tipos y los rangos (si algo no cumple, responde 422). Aquí además
revisamos que fov no pase del máximo configurado (eso es un 400, según el contrato).
"""

from dataclasses import dataclass

from fastapi import Query

from app.config import settings
from app.errores import ErrorApi

FOV_MINIMO = 0.01


@dataclass
class Busqueda:
    ra: float
    dec: float
    fov: float
    det: str


def parametros_busqueda(
    ra: float = Query(..., ge=0, lt=360, description="Ascensión recta en grados (ICRS).", examples=[269.4461]),
    dec: float = Query(..., ge=-90, le=90, description="Declinación en grados (ICRS).", examples=[4.7705]),
    fov: float = Query(0.1, ge=FOV_MINIMO, description="Campo de visión en grados.", examples=[0.1]),
    det: str = Query("D2", pattern="^D[1-6]$", description="Detector de SPHEREx: D1 a D6.", examples=["D2"]),
) -> Busqueda:
    if fov > settings.fov_max:
        raise ErrorApi(400, f"El campo de visión máximo es {settings.fov_max} grados.")
    return Busqueda(ra=ra, dec=dec, fov=fov, det=det)
