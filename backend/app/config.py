"""Configuración del backend, leída de variables de entorno (o del archivo .env).

Para usarla en cualquier archivo:

    from app.config import settings
    print(settings.fov_max)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Lee las variables del archivo backend/.env si existe (nunca se sube a git).
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Colección o versión de datos de SPHEREx en IRSA.
    # PENDIENTE: confirmar en la documentación de IRSA cuál está vigente (QR3 / DR1).
    # Variable de entorno: COLECCION_SPHEREX
    coleccion_spherex: str = ""

    # Campo de visión máximo permitido, en grados. Valor PROVISIONAL.
    # Variable de entorno: FOV_MAX
    fov_max: float = 0.5

    # Páginas web que pueden llamar a esta API, separadas por comas.
    # Variable de entorno: CORS_ORIGINS
    cors_origins: str = "http://localhost:5173"

    # Con USAR_MOCK=1 la API responde datos falsos (para que el frontend avance).
    # Variable de entorno: USAR_MOCK
    usar_mock: bool = False

    @property
    def lista_cors_origins(self) -> list[str]:
        """Convierte "a,b,c" en ["a", "b", "c"]."""
        return [origen.strip() for origen in self.cors_origins.split(",") if origen.strip()]


settings = Settings()
