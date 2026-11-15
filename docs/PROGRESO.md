# PROGRESO — SPACECORE

Bitácora compartida para que cualquier integrante (y su Claude Code) pueda continuar el trabajo
de otro. Claude Code la lee al empezar y la actualiza al terminar cada sesión.
Las entradas nuevas van ARRIBA en el historial. No borres entradas anteriores.

## Estado actual (actualizar en cada relevo)

| Campo | Valor |
|---|---|
| Última actualización | 2026-11-14 21:00 |
| Última persona que trabajó | Jesús |
| Rama activa | datos/T13-cache (hay 4 ramas con PR: T21, T11, T12 y T13; no chocan entre sí) |
| Tarea en curso | Bloque T21 + T11 + T12 + T13 terminado; falta unir sus PR |
| Punto exacto donde quedó | Ya existen las piezas sueltas del backend: buscar imágenes (irsa.py), descargarlas (descargas.py), agruparlas por época (epocas.py), convertirlas a PNG (ciencia/imagen.py) y guardarlas (cache.py). Falta unirlas en los endpoints. |
| Siguiente paso concreto | Unir los 4 PR. Después T23 (reproyectar para dejar el norte arriba) y T22 (sumar las imágenes de cada época), y luego los endpoints T32, T33 y T34. |
| ¿El código actual funciona? | Sí: `python -m unittest discover -v` desde backend pasa (29 pruebas con las 4 ramas unidas). El frontend funciona en modo demostración. |

## Tareas terminadas (unidas a main)

- T03: estructura inicial en main, repo en GitHub, main protegida y los 5 compañeros con acceso
  (ya clonaron el repo, según confirmó Jesús el 2026-11-14).
- T60: Dockerfile del backend probado en local (PR #1, unido a main el 2026-11-14).
- T02: contrato de la API versión 1 en docs/api.md (PR #2, unido a main el 2026-11-14).
- T10: buscar_imagenes con el servicio SIA de IRSA (PR #3, unido a main el 2026-11-14).
- T40: interfaz del equipo en frontend/, TypeScript + Vite sin React (PR #4, unido a main el
  2026-11-14). Funciona en modo demostración; adelanta T41, T43, T44, T50, T51, T53, T54 y
  T55, que se dan por terminadas cuando funcionen con datos reales.

## Decisiones tomadas

- FRONTEND SIN REACT (2026-11-14): se adoptó la interfaz que preparó el equipo (TypeScript +
  Vite, archivos .ts). Su `frontend/src/api/cliente.ts` habla el contrato de docs/api.md y sin
  backend funciona en modo demostración con datos simulados. La carpeta `interfaz-propuesta/`
  de la raíz es la copia original que entregó el equipo: no está en git y es redundante.
- Contrato versión 1.1: `/frames` y `/diff` mandan el PNG a ESCALA REAL (un píxel del PNG = un
  píxel de SPHEREx, 6.15 arcsec), no a 256 px fijos. Se agregó `meta.escala_arcsec_px`.
- La interfaz calcula la diferencia y la suma en el navegador a partir de los PNG, así que
  `/diff` (T24 y T35) pierde prioridad.
- Los recortes se descargan SIN la tabla EPSF (se corta la descarga antes): 124 KB en vez de
  3.9 MB. Para el espectro (T25) hay que pedir el archivo completo (`completo=True`).
- `a_png` usa `ManualInterval` + `AsinhStretch` de Astropy, no `ImageNormalize`, porque esta
  última exige matplotlib, que no está en la lista de librerías.
- Pruebas del backend con `unittest` (incluido en Python), en backend/tests/. No se agregó
  pytest.

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
- Colección de datos de SPHEREx: RESUELTO el 2026-11-14. Se usan las colecciones SIA
  `spherex_dr1` y `spherex_qr3` (valor por defecto de COLECCION_SPHEREX en config.py), tomadas
  del tutorial oficial "Introduction to SPHEREx Spectral Images". Existen también
  `spherex_dr1_deep` y `spherex_qr3_deep` (campos profundos), que no usamos.
- T10 busca las imágenes con SIA (`Irsa.query_sia`) y no con TAP: TAP tardó más de 6 minutos y
  terminó en error 502 tres veces; SIA respondió en 1 a 3 segundos con los mismos datos. La
  desventaja de SIA (datos nuevos con ~1 día de retraso) no nos afecta.
- Verificado con datos reales el 2026-11-14: tamaño de píxel de SPHEREx = 6.15 arcsec (columna
  `s_pixel_scale` de SIA); la imagen viene en MJy/sr (BUNIT); las extensiones del recorte son
  IMAGE, FLAGS, VARIANCE, ZODI, EPSF y WCS-WAVE (la de PSF se llama EPSF, no PSF).
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

- IRSA ESTUVO MUY INESTABLE el 2026-11-14 por la noche: el servicio SIA respondió "502 Proxy
  Error" en la mayoría de los intentos, a ratos en todos. `buscar_imagenes` reintenta 3 veces.
  Para la demo es indispensable precalcular los 5 objetivos y servirlos desde la caché (T16).
- El recorte de IRSA no queda centrado exacto en el punto pedido (en la prueba, a ~13 arcsec) y
  viene girado (WCS TAN-SIP). Hasta que exista T23 las imágenes no tienen el norte arriba.
- La interfaz, en modo API, hace 6 llamadas a `/epocas` (una por detector) al buscar. Como SIA
  devuelve los 6 detectores en una sola consulta, conviene guardar esa consulta en la caché.

- Cada recorte de SPHEREx pesa ~3.9 MB aunque la imagen sea pequeña (53 x 59 píxeles para
  fov = 0.1), porque trae la tabla EPSF completa. Barnard's Star tiene 62 imágenes en D2: son
  unos 240 MB por búsqueda. Hay que tenerlo en cuenta en T11 (descargas) y T13 (caché), y
  averiguar si IRSA permite pedir solo algunas extensiones.
- La consulta TAP a IRSA (spherex.artifact + spherex.plane con CONTAINS) falló el 2026-11-14
  con "502 Proxy Error" tras 400 segundos, tres veces seguidas. Por eso T10 usa SIA.

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

### 2026-11-14 21:00 — Jesús — ramas: ciencia/T21-png, datos/T11-descargas, datos/T12-epocas, datos/T13-cache
- Hecho: PR #3 (T10) y PR #4 (T40, interfaz del equipo) unidos a main. Después, cuatro tareas,
  cada una en su rama con su PR:
  - T21: backend/app/ciencia/imagen.py (`limites_brillo`, `a_png`, `a_data_url`) y contrato
    1.1 a escala real. PNG real de muestra en notebooks/salidas/barnard_D2.png.
  - T11: backend/app/datos/descargas.py (`descargar_recortes`, `cortar_antes_de_tabla`,
    `abrir_recorte`) y reintentos en `buscar_imagenes`.
  - T12: backend/app/datos/epocas.py (`agrupar_por_epoca`, `separar_por_detector`).
  - T13: backend/app/datos/cache.py (`crear_clave`, `get`, `set`, `get_bytes`, `set_bytes`) y
    la variable CACHE_DIR.
- A medias (y dónde quedó): los 4 PR están abiertos. T20 (notebook) no se hizo como notebook:
  la exploración del recorte se hizo con scripts y quedó anotada en CLAUDE.md.
- Siguiente paso: T23 y T22, luego los endpoints T32, T33 y T34, y conectar la interfaz (T52).
- Decisiones: ver "Decisiones tomadas" (sin React, contrato 1.1, recortes sin EPSF, unittest).
- Problemas: IRSA con errores 502 muy frecuentes (ver "Problemas conocidos").
- Cómo probar: desde backend, `python -m unittest discover -v` (termina en OK);
  `python -m app.ciencia.imagen` genera el PNG de muestra; `python -m app.datos.descargas`
  descarga los recortes de Barnard's Star y mide el tiempo. Desde frontend, `npm run dev`.

### 2026-11-14 20:05 — Jesús — rama: datos/T10-buscar-imagenes
- Hecho: PR #2 (T02) unido a main y su rama borrada. T10: `buscar_imagenes(ra, dec,
  fov_grados, detector)` en backend/app/datos/irsa.py, con el servicio SIA de IRSA. Devuelve
  una lista ordenada por fecha con url_recorte, fecha_obs, mjd, detector y coleccion.
  config.py: COLECCION_SPHEREX ahora vale por defecto "spherex_dr1,spherex_qr3".
- Resultados reales (detector D2, fov 0.1): Barnard's Star 62 imágenes, WISE 0855 48,
  Epsilon Indi B 93, RW Aurigae 55, R Draconis 89. Cada consulta tardó entre 1 y 1.5 s.
  Barnard's Star tiene tres grupos de fechas: agosto de 2025, marzo de 2026 y agosto-septiembre
  de 2026. Un recorte descargado dio HTTP 200, 3.9 MB, FITS válido.
- A medias (y dónde quedó): falta unir el PR de T10.
- Siguiente paso: T20 y T21 (recorte a PNG), luego T11 (descargas en paralelo).
- Decisiones: SIA en lugar de TAP, y colecciones DR1 + QR3 (ver "Decisiones tomadas").
  Jesús autorizó borrar siempre las ramas ya unidas a main.
- Problemas: TAP de IRSA con error 502; cada recorte pesa ~3.9 MB (ver "Problemas conocidos").
- Cómo probar: `cd backend`, `.venv\Scripts\Activate.ps1`, `python -m app.datos.irsa`. Debe
  imprimir "Imágenes encontradas: 62" (o más, si SPHEREx publicó datos nuevos) y una URL.

### 2026-11-14 19:10 — Jesús — rama: api/T02-contrato
- Hecho: PR #1 (T60) unido a main y ramas infra/T60-docker e infra/T03-cierre borradas. T03 se
  da por terminada. Cambio de reparto: Jesús y Claude hacen todo el código. T02: contrato
  versión 1 escrito en docs/api.md (parámetros, ejemplos, errores y tipos TypeScript).
- A medias (y dónde quedó): Jesús aprobó el contrato versión 1; falta unir el PR. Los compañeros
  están preparando un diseño de interfaz; cuando llegue hay que revisar si el contrato le alcanza.
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
