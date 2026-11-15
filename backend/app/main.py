"""Punto de entrada del backend: crea la app FastAPI, activa CORS e incluye los routers.

Para correrlo (desde la carpeta backend, con el entorno .venv activado):

    uvicorn app.main:app --reload

y abrir http://127.0.0.1:8000/docs
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.errores import ErrorApi
from app.routers import imagenes

registro = logging.getLogger(__name__)

app = FastAPI(
    title="SPACECORE API",
    description="API del proyecto SPACECORE (reto Planet X and SPHEREx, NASA Space Apps 2026).",
)

# CORS: permite que la página (frontend) llame a esta API desde otro dominio.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.lista_cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Endpoints del contrato: /resolve, /epocas, /frames, /diff y /spectrum.
app.include_router(imagenes.router)


# ---------------------------------------------------------------------------------------------
# Errores (T37): todos responden {"error": "mensaje en español"}, como pide docs/api.md.
# ---------------------------------------------------------------------------------------------
NOMBRES_PARAMETROS = {
    "ra": "RA",
    "dec": "Dec",
    "fov": "el campo de visión (fov)",
    "det": "el detector (det)",
    "name": "el nombre (name)",
    "a": "la época a",
    "b": "la época b",
    "apertura": "la apertura (arcsec)",
    "anillo_in": "el anillo interior (arcsec)",
    "anillo_out": "el anillo exterior (arcsec)",
    "fondo": "restar fondo (fondo)",
    "pmra": "el movimiento propio en RA (pmra)",
    "pmdec": "el movimiento propio en Dec (pmdec)",
    "epoca": "la época (año decimal)",
}


@app.exception_handler(ErrorApi)
def error_api(_: Request, error: ErrorApi) -> JSONResponse:
    return JSONResponse(status_code=error.codigo, content={"error": error.mensaje})


@app.exception_handler(RequestValidationError)
def error_parametros(_: Request, error: RequestValidationError) -> JSONResponse:
    """Parámetro que falta o con formato inválido -> 422 con un mensaje claro."""
    problemas = []
    for detalle in error.errors():
        parametro = str(detalle.get("loc", ["", "?"])[-1])
        nombre = NOMBRES_PARAMETROS.get(parametro, parametro)
        if detalle.get("type") == "missing":
            problemas.append(f"Falta {nombre}.")
        else:
            problemas.append(f"Valor inválido para {nombre}: {detalle.get('input')!r}.")
    return JSONResponse(status_code=422, content={"error": " ".join(problemas)})


@app.exception_handler(StarletteHTTPException)
def error_http(_: Request, error: StarletteHTTPException) -> JSONResponse:
    mensaje = "No existe esa dirección." if error.status_code == 404 else str(error.detail)
    return JSONResponse(status_code=error.status_code, content={"error": mensaje})


@app.exception_handler(Exception)
def error_inesperado(_: Request, error: Exception) -> JSONResponse:
    registro.exception("Error inesperado: %r", error)
    return JSONResponse(status_code=500, content={"error": "Error inesperado del servidor."})


@app.get("/health")
def health() -> dict[str, str]:
    """Sirve para comprobar que el servidor está vivo."""
    return {"status": "ok"}
