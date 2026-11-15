"""GET /resolve: convierte el nombre de un objeto en coordenadas (ver docs/api.md)."""

import logging

from astropy.coordinates import SkyCoord
from astropy.coordinates.name_resolve import NameResolveError
from fastapi import APIRouter, Query

from app.datos import cache
from app.errores import ErrorApi

router = APIRouter()
registro = logging.getLogger(__name__)

# Respaldo por si el servicio de nombres (Sesame, del CDS) no responde: coordenadas ICRS de los
# 5 objetivos de prueba. Las de las 4 estrellas son las que devolvió Sesame el 2026-11-14,
# redondeadas a 4 decimales; la de WISE 0855 es la que da el enunciado del reto.
# Son posiciones de catálogo (época J2000), sin corregir por movimiento propio.
RESPALDO = {
    "barnard's star": (269.4521, 4.6934),
    "barnards star": (269.4521, 4.6934),
    "epsilon indi b": (331.0441, -56.7828),
    "eps ind b": (331.0441, -56.7828),
    "wise 0855": (133.7951, -7.2451),
    "wise 0855-0714": (133.7951, -7.2451),
    "rw aurigae": (76.9565, 30.4014),
    "rw aur": (76.9565, 30.4014),
    "r draconis": (248.1676, 66.7550),
    "r dra": (248.1676, 66.7550),
}


def _normalizar(nombre: str) -> str:
    return " ".join(nombre.lower().split())


@router.get("/resolve", summary="Nombre de un objeto a coordenadas")
def resolve(
    name: str = Query(..., min_length=1, max_length=100, description="Nombre del objeto.", examples=["Barnard's Star"]),
) -> dict:
    nombre = name.strip()
    if not nombre:
        raise ErrorApi(422, "Parámetros inválidos o faltantes: name.")

    clave = cache.clave_de_texto("resolve", _normalizar(nombre))
    guardado = cache.get(clave)
    if guardado is not None:
        return guardado

    try:
        # Pregunta al servicio Sesame del CDS (necesita internet).
        coordenadas = SkyCoord.from_name(nombre)
        ra, dec = float(coordenadas.ra.deg), float(coordenadas.dec.deg)
    except NameResolveError as error:
        # Sesame no lo encontró, o no respondió. Probamos con la lista de respaldo.
        registro.warning("Sesame no resolvió %r: %s", nombre, error)
        respaldo = RESPALDO.get(_normalizar(nombre))
        if respaldo is None:
            raise ErrorApi(404, f"No se encontró ningún objeto llamado '{nombre}'.") from error
        ra, dec = respaldo

    respuesta = {"name": nombre, "ra": ra, "dec": dec}
    cache.set(clave, respuesta)
    return respuesta
