# Imagen del backend de SPACECORE (FastAPI + Uvicorn).
# Construir:  docker build -t planetx-api backend
# Correr:     docker run -p 8080:8080 planetx-api     -> http://localhost:8080/health

FROM python:3.13-slim

WORKDIR /app

# Primero solo las dependencias: así Docker las reutiliza si el código cambia.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Después el código.
COPY app ./app
COPY scripts ./scripts

# Cloud Run indica el puerto con la variable PORT. En local usamos 8080.
ENV PORT=8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
