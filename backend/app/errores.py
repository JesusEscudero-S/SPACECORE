"""Errores de la API con el formato del contrato: {"error": "mensaje en español"}.

Para responder un error desde cualquier parte del backend:

    from app.errores import ErrorApi
    raise ErrorApi(404, "SPHEREx todavía no tiene datos aquí.")

Los "manejadores" de abajo se registran en main.py y convierten cada error en la respuesta JSON.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

registro = logging.getLogger(__name__)


class ErrorApi(Exception):
    """Un error que la página puede mostrar tal cual."""

    def __init__(self, estado: int, mensaje: str):
        super().__init__(mensaje)
        self.estado = estado
        self.mensaje = mensaje


def registrar_manejadores(app: FastAPI) -> None:
    """Hace que TODOS los errores salgan como {"error": "..."}."""

    @app.exception_handler(ErrorApi)
    async def _error_api(peticion: Request, error: ErrorApi) -> JSONResponse:
        return JSONResponse(status_code=error.estado, content={"error": error.mensaje})

    @app.exception_handler(RequestValidationError)
    async def _parametros_invalidos(peticion: Request, error: RequestValidationError) -> JSONResponse:
        # FastAPI detectó que falta un parámetro o tiene un valor inválido.
        nombres = sorted({str(detalle["loc"][-1]) for detalle in error.errors()})
        mensaje = "Parámetros inválidos o faltantes: " + ", ".join(nombres) + "."
        return JSONResponse(status_code=422, content={"error": mensaje})

    @app.exception_handler(Exception)
    async def _error_inesperado(peticion: Request, error: Exception) -> JSONResponse:
        registro.exception("Error inesperado en %s", peticion.url.path)
        return JSONResponse(status_code=500, content={"error": "Error inesperado del servidor."})
