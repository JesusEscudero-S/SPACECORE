"""GET /frames: un PNG por época, listo para animar (ver docs/api.md).

La primera vez puede tardar medio minuto o más (descarga y procesa los recortes); después
sale de la caché al instante.
"""

from fastapi import APIRouter, Depends

from app import servicio
from app.routers.parametros import Busqueda, parametros_busqueda

router = APIRouter()


@router.get("/frames", summary="Imágenes por época de una zona")
def frames(busqueda: Busqueda = Depends(parametros_busqueda)) -> dict:
    return servicio.obtener_frames(busqueda.ra, busqueda.dec, busqueda.fov, busqueda.det)
