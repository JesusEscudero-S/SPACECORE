# PROGRESO — SPACECORE

Bitácora compartida para que cualquier integrante (y su Claude Code) pueda continuar el trabajo
de otro. Claude Code la lee al empezar y la actualiza al terminar cada sesión.
Las entradas nuevas van ARRIBA en el historial. No borres entradas anteriores.

## Estado actual (actualizar en cada relevo)

| Campo | Valor |
|---|---|
| Última actualización | 2026-11-14 19:10 |
| Última persona que trabajó | Jesús |
| Rama activa | api/T02-contrato |
| Tarea en curso | T02 Contrato de la API: versión 1 escrita en docs/api.md, falta que Jesús la apruebe y unir el PR |
| Punto exacto donde quedó | docs/api.md tiene todos los endpoints con parámetros, ejemplos y errores. Falta revisarlo contra el diseño de interfaz que están preparando los compañeros. |
| Siguiente paso concreto | Aprobar el contrato y unir el PR. Después T10 (consulta a IRSA) y T20/T21 (abrir un recorte y convertirlo a PNG). |
| ¿El código actual funciona? | Sí: backend (/health) y frontend en local, y el backend dentro de Docker. T02 solo cambia documentos. |

## Tareas terminadas (unidas a main)

- T03: estructura inicial en main, repo en GitHub, main protegida y los 5 compañeros con acceso
  (ya clonaron el repo, según confirmó Jesús el 2026-11-14).
- T60: Dockerfile del backend probado en local (PR #1, unido a main el 2026-11-14).

## Decisiones tomadas

- NUEVO REPARTO (2026-11-14): Jesús, con Claude Code, desarrolla TODO el código del proyecto
  (las tareas de los roles #1 a #6). El resto del equipo prepara el pitch (T65 y T75). La regla
  de "no tocar carpetas de otro rol" ya no aplica para Jesús.
- El orden de trabajo es en línea recta hacia el MVP: datos reales (T10, T20, T21, T11, T12,
  T13), API (T30, T32, T33, T22, T23, T34), página (T40, T41, T42, T50, T43, T52) y publicar
  (T61, T62, T63). T31 (mock) queda fuera por ahora: servía para trabajar en paralelo.
- Contrato de la API versión 1 en docs/api.md. Respecto a la propuesta de CLAUDE.md agrega
  `meta.ra`, `meta.dec` y `meta.tamano_px` en /frames y `unidad_flujo` en /spectrum.
- Nombre del proyecto y del repositorio: SPACECORE / spacecore.
- Caché definitiva: PENDIENTE de decidir (bucket u otra opción). Por ahora, caché en disco.
- Colección de datos de SPHEREx: PENDIENTE de confirmar en la documentación de IRSA
  (los tutoriales recomiendan QR3 y DR1 sobre QR2). En config.py queda vacía por ahora.
- FOV_MAX = 0.5 grados es un valor PROVISIONAL (nadie lo ha definido todavía); se cambia con
  la variable de entorno FOV_MAX.
- Jupyter va en backend/requirements-dev.txt, separado de requirements.txt, para que la imagen
  de Docker no pese de más. Solo lo instala quien use los notebooks.
- Las versiones de backend/requirements.txt están fijas (==) con las que se probaron el
  2026-11-14 en Python 3.13.
- docs/api.md está marcado como PROPUESTA hasta que se apruebe en T02.
- .claude/launch.json permite a Claude Code (app de escritorio) arrancar el backend y el
  frontend para probarlos. No afecta al proyecto.

## Problemas conocidos

- La conexión a PyPI falló dos veces por tiempo de espera al instalar las librerías de Python
  (red intermitente). Si `pip install` falla con "No matching distribution found", repetir con:
  `pip install --default-timeout 120 --retries 10 -r requirements.txt`.
- T20 pide matplotlib y T25 sugiere photutils, pero no están en la lista de tecnologías de
  CLAUDE.md ni en requirements.txt. El equipo debe decidir si se agregan.
- La imagen de Docker pesa 875 MB; 532 MB son las librerías de requirements.txt (scipy, dask,
  zarr y botocore llegan como dependencias de reproject y s3fs). Para bajarla habría que quitar
  librerías (por ejemplo s3fs, que es opcional): decisión del equipo.
- En la computadora de Jesús el puerto 8080 lo ocupa un servicio de Windows (AgentService), así
  que ahí `docker run -p 8080:8080` falla con "ports are not available". Usar otro puerto del
  lado de la computadora: `docker run -p 8081:8080 planetx-api` y abrir
  http://localhost:8081/health.
- En la computadora de Jesús, Docker Desktop 4.89 no arranca ("An unexpected error occurred",
  en el log: "rename ...sailor-ingest.sock ... The file cannot be accessed by the system").
  Windows deja bloqueados los archivos socket que crea Docker. Primero probar reiniciar Windows.
  Si sigue: cerrar Docker Desktop, renombrar las carpetas `%LOCALAPPDATA%\Docker\run` y
  `%LOCALAPPDATA%\docker-secrets-engine` (las dos a la vez) y volver a abrirlo.
- Docker Hub estuvo muy lento el 2026-11-14 (falló con "TLS handshake timeout"). Si
  `docker build` falla al bajar la base, correr antes `docker pull python:3.13-slim`.

- El servidor del CDS (aladin.cds.unistra.fr) tuvo fallas: usar Aladin Lite desde npm
  (`aladin-lite`), no desde la etiqueta <script> del CDS. El servicio que convierte nombres en
  coordenadas (Sesame del CDS) también puede fallar: tener las coordenadas de los 5 objetivos
  de prueba como respaldo.

## Historial de sesiones (la más reciente arriba)

### 2026-11-14 19:10 — Jesús — rama: api/T02-contrato
- Hecho: PR #1 (T60) unido a main y ramas infra/T60-docker e infra/T03-cierre borradas. T03 se
  da por terminada. Cambio de reparto: Jesús y Claude hacen todo el código. T02: contrato
  versión 1 escrito en docs/api.md (parámetros, ejemplos, errores y tipos TypeScript).
- A medias (y dónde quedó): T02 espera la aprobación de Jesús y el PR. Los compañeros están
  preparando un diseño de interfaz; cuando llegue hay que revisar si el contrato le alcanza.
- Siguiente paso: unir el PR de T02 y empezar T10.
- Decisiones: ver "Decisiones tomadas" (nuevo reparto, orden de trabajo y campos agregados al
  contrato).
- Problemas: la red siguió intermitente (un `git pull` falló por no poder conectar a GitHub).
- Cómo probar: T02 solo cambia documentos; abrir docs/api.md y leerlo.

### 2026-11-14 15:50 — Jesús — rama: infra/T60-docker
- Hecho: T60. `docker build -t planetx-api backend` termina bien (unos 5 min con buena red) y
  el contenedor responde `{"status":"ok"}` en /health y abre /docs. Se comprobó el puerto 8080
  interno (con `-p 8081:8080`) y que respeta la variable PORT (con `-e PORT=9090`), como la
  usará Cloud Run. Al Dockerfile se le agregó `--default-timeout=120 --retries 10` en pip para
  que no falle con red lenta.
- A medias (y dónde quedó): la rama está subida pero falta unirla a main con un PR. No se probó
  en el puerto 8080 de la computadora porque ahí está ocupado (ver "Problemas conocidos").
- Siguiente paso: unir el PR de esta rama; después T61 (deploy a Cloud Run).
- Decisiones: esta rama incluye el commit de bitácora de infra/T03-cierre para que no choquen
  al unirse. Con unir este PR basta; la rama infra/T03-cierre ya no necesita PR propio.
- Problemas: Docker Desktop no arrancaba, Docker Hub lento y puerto 8080 ocupado (los tres
  están en "Problemas conocidos" con su solución). La imagen pesa 875 MB.
- Cómo probar: con Docker Desktop abierto, `docker build -t planetx-api backend`, luego
  `docker run -p 8080:8080 planetx-api` y abrir http://localhost:8080/health.

### 2026-11-14 15:00 — Jesús — rama: infra/T03-cierre
- Hecho: parte de GitHub de T03. Repo público https://github.com/JesusEscudero-S/spacecore,
  main subida, regla de protección activa en main (requiere Pull Request, no se puede borrar
  ni forzar push) y 5 compañeros invitados.
- A medias (y dónde quedó): al momento de revisar, 1 compañero aceptó la invitación y 4 siguen
  pendientes. No hay ningún PR todavía, así que falta comprobar el criterio de T03 ("todos
  clonaron y pueden crear ramas y PRs").
- Siguiente paso: cada compañero acepta la invitación, clona, crea una rama con el prefijo de
  su rol y abre un PR de prueba. Después T02.
- Decisiones: la protección de main pide Pull Request pero 0 aprobaciones, para que el
  integrador (#6) pueda unir sin quedarse bloqueado.
- Problemas: ninguno nuevo.
- Cómo probar: `git clone https://github.com/JesusEscudero-S/spacecore.git` y seguir el README.

### 2026-11-14 14:30 — Jesús — rama: main
- Hecho: T03 (parte local). Git inicializado con la rama main. Esqueleto del backend (FastAPI con
  CORS y /health, config.py, carpetas routers/datos/ciencia/scripts, Dockerfile, .dockerignore,
  .env.example). Proyecto Vite react-ts en frontend/ con componentes vacíos Buscador, PanelInfo,
  Reproductor y VistaAladin, y src/api/cliente.ts. docs/api.md, .gitignore, plantilla de PR y
  README. PROGRESO.md y tareas.csv se movieron a docs/ y docs/plan/.
- A medias (y dónde quedó): la parte de GitHub de T03 (crear el repo, subir main, proteger main,
  invitar al equipo y que cada quien clone y abra un PR de prueba).
- Siguiente paso: terminar la parte de GitHub; después T02 (contrato) y cada rol con sus tareas.
- Decisiones: ver la sección "Decisiones tomadas".
- Problemas: PyPI con red intermitente (ver "Problemas conocidos"). El Dockerfile está escrito
  pero NO se construyó la imagen todavía (eso es T60).
- Aviso a otros roles: esto adelanta parte de T30 (rol #3: main.py, config.py y /health ya
  existen), T40 (rol #1: los 4 componentes vacíos ya existen; falta el layout) y T60 (rol #6:
  Dockerfile y .dockerignore ya existen; falta probarlos).
- Cómo probar:
  - Backend: `cd backend`, `python -m venv .venv`, `.venv\Scripts\Activate.ps1`,
    `pip install -r requirements.txt`, `uvicorn app.main:app --reload` y abrir
    http://127.0.0.1:8000/health (debe verse `{"status":"ok"}`).
  - Frontend: `cd frontend`, `npm install`, `npm run dev` y abrir http://localhost:5173
    (debe verse el título SPACECORE y los 4 componentes "pendiente").

<!--
Plantilla para cada entrada:

### AAAA-MM-DD HH:MM — (nombre) — rama: (rama)
- Hecho:
- A medias (y dónde quedó):
- Siguiente paso:
- Decisiones:
- Problemas:
- Cómo probar:
-->
