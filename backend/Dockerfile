# Imagen del backend de SPACECORE (FastAPI + Uvicorn).
# Construir:  docker build -t planetx-api backend
# Correr:     docker run -p 8080:8080 planetx-api     -> http://localhost:8080/health

FROM python:3.13-slim

WORKDIR /app

# Primero solo las dependencias: así Docker las reutiliza si el código cambia.
COPY requirements.txt .
# --default-timeout y --retries: para que no falle si la red está lenta.
RUN pip install --no-cache-dir --default-timeout=120 --retries 10 -r requirements.txt

# Después el código.
COPY app ./app
COPY scripts ./scripts

# La caché precalculada (T16) viaja DENTRO de la imagen: así la página publicada carga los 5
# objetivos al instante aunque IRSA esté caído. Antes de construir la imagen de producción hay
# que correr `python -m scripts.precalcular` (ver infra/despliegue.md). Si la carpeta solo trae
# .gitkeep, la imagen arranca con la caché vacía y funciona igual, solo que más lento.
COPY cache ./cache

# Cloud Run indica el puerto con la variable PORT. En local usamos 8080.
ENV PORT=8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
