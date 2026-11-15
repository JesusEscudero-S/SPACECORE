"""Configuración del backend, leída de variables de entorno (o del archivo .env).

Para usarla en cualquier archivo:

    from app.config import settings
    print(settings.fov_max)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Lee las variables del archivo backend/.env si existe (nunca se sube a git).
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Colecciones de datos de SPHEREx en IRSA (servicio SIA), separadas por comas.
    # Verificado el 2026-11-14 en el tutorial oficial de IRSA: DR1 y QR3 son las vigentes y
    # reemplazan a QR2. También existen spherex_dr1_deep y spherex_qr3_deep (campos profundos).
    # Variable de entorno: COLECCION_SPHEREX
    coleccion_spherex: str = "spherex_dr1,spherex_qr3"

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
    def lista_colecciones_spherex(self) -> list[str]:
        """Convierte "a,b" en ["a", "b"]."""
        return [c.strip() for c in self.coleccion_spherex.split(",") if c.strip()]

    @property
    def lista_cors_origins(self) -> list[str]:
        """Convierte "a,b,c" en ["a", "b", "c"]."""
        return [origen.strip() for origen in self.cors_origins.split(",") if origen.strip()]


settings = Settings()
