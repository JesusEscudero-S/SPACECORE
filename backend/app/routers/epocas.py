"""GET /epocas: en qué épocas hay imágenes de una zona (ver docs/api.md)."""

from fastapi import APIRouter, Depends

from app import servicio
from app.routers.parametros import Busqueda, parametros_busqueda

router = APIRouter()


@router.get("/epocas", summary="Épocas con imágenes de una zona")
def epocas(busqueda: Busqueda = Depends(parametros_busqueda)) -> dict:
    lista = servicio.obtener_epocas(busqueda.ra, busqueda.dec, busqueda.fov, busqueda.det)
    # Respondemos solo lo que dice el contrato (sin las URLs internas de IRSA).
    return {
        "epocas": [
            {
                "id": epoca["id"],
                "inicio": epoca["inicio"],
                "fin": epoca["fin"],
                "n_imagenes": epoca["n_imagenes"],
            }
            for epoca in lista
        ]
    }
