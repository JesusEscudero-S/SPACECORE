"""Punto de entrada del backend: crea la app FastAPI, activa CORS e incluye los routers.

Para correrlo (desde la carpeta backend, con el entorno .venv activado):

    uvicorn app.main:app --reload

y abrir http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

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

# Aquí se incluirán los routers de backend/app/routers/ cuando existan. Ejemplo:
#   from app.routers import resolve
#   app.include_router(resolve.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Sirve para comprobar que el servidor está vivo."""
    return {"status": "ok"}
