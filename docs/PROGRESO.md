# PROGRESO — SPACECORE

Bitácora compartida para que cualquier integrante (y su Claude Code) pueda continuar el trabajo
de otro. Claude Code la lee al empezar y la actualiza al terminar cada sesión.
Las entradas nuevas van ARRIBA en el historial. No borres entradas anteriores.

## Estado actual (actualizar en cada relevo)

| Campo | Valor |
|---|---|
| Última actualización | 2026-11-15 03:40 |
| Última persona que trabajó | David (con Claude) |
| Rama activa | docker (subida a GitHub; 3 commits encima de main con el de esta sesión) |
| Tarea en curso | T36 /spectrum terminado con datos reales. Despliegue (T61/T62/T63) en espera de las cuentas de Jesús. |
| Punto exacto donde quedó | Todo corre con `docker compose up -d --build`. Los 5 objetivos (6 detectores + espectro) están precalculados en backend/cache. La pestaña Espectro ya se ve y carga sola al cambiar de objetivo. |
| Siguiente paso concreto | 1) Revisar y hacer commit de los 5 arreglos de la interfaz de la prueba de las 04:45 (ver historial). 2) Decidir con el equipo: Redis en la nube (Upstash gratis o solo disco) y centrado/actualización de datos (ver "Pendientes por decidir"). 3) README (T74). 4) Desplegar (cuentas de Jesús). 5) PR de `docker` a main. |
| ¿El código actual funciona? | SÍ, CON DATOS REALES, en Docker (2026-11-15 03:30, computadora de David): 71 pruebas OK; /frames y /spectrum de los 5 objetivos responden en ~30 ms desde la caché. |

## Decididos por Jesús el 2026-11-15 (11:15)

- REDIS: sí va a producción (falta crear la cuenta y poner REDIS_URL en Cloud Run al desplegar).
- CENTRADO: fijo en 2026.0. Constante EPOCA_CENTRADO en frontend/src/config.ts y en
  backend/scripts/precalcular.py (deben ser iguales). Ya no depende del año en curso.
- MARGEN DEL RECORTE: se queda como está (recorte del mismo tamaño que el campo de visión).
- NOMBRE: la interfaz se llama SPACECORE (antes decía "Planet X").
- CACHÉ PRECALCULADA: la de David se copió a backend/cache de la computadora de Jesús y se
  validó con `python -m scripts.precalcular`: los 5 objetivos (6 detectores + espectro) salen
  en 0 s. No está en git; hay que tenerla en backend/cache al construir la imagen.
- Estado de ramas: PR #11 (rama docker) y PR #12 (captura) unidos a main; PR #10 cerrado sin
  unir por duplicado.
- Visto al probar: R Draconis en D6 se ve como un disco blanco enorme (estrella muy brillante,
  saturada). Conviene abrirla en otro detector para la demo.

## Pendientes por decidir con el equipo (David, 2026-11-15 04:00) — YA RESUELTOS, ver arriba

- REDIS EN PRODUCCIÓN: hoy Cloud Run usaría solo el disco (los 5 objetivos vienen en la
  imagen). Opción: Upstash gratis (256 MB, 500 mil comandos/mes); solo hay que poner
  REDIS_URL como variable secreta en Cloud Run. Sirve para que las búsquedas NUEVAS del
  jurado queden guardadas 7 días aunque Cloud Run apague el servidor.
- CENTRADO Y DATOS NUEVOS: con el centrado al 1 de enero, después del 1-ene-2027 Barnard,
  Eps Indi B y WISE 0855 dejan de salir de la caché (finalistas: finales de enero). Propuesta:
  centrado fijo en 2026.0 + revisar la lista de IRSA cada 24 h y recalcular en segundo plano
  si hay imágenes nuevas (cumple "fácil de actualizar con datos nuevos" del reto). Volver al
  centrado diario del equipo es peor: la caché caduca cada 2 a 4 semanas.

## Tareas terminadas (unidas a main)

- T11, T12, T13, T21: unidas a main (el último es el PR #8). Ya no queda ninguna rama abierta
  aparte de la de esta sesión.

- T03: estructura inicial en main, repo en GitHub, main protegida y los 5 compañeros con acceso
  (ya clonaron el repo, según confirmó Jesús el 2026-11-14).
- T60: Dockerfile del backend probado en local (PR #1, unido a main el 2026-11-14).
- T02: contrato de la API versión 1 en docs/api.md (PR #2, unido a main el 2026-11-14).
- T10: buscar_imagenes con el servicio SIA de IRSA (PR #3, unido a main el 2026-11-14).
- T40: interfaz del equipo en frontend/, TypeScript + Vite sin React (PR #4, unido a main el
  2026-11-14). Funciona en modo demostración; adelanta T41, T43, T44, T50, T51, T53, T54 y
  T55, que se dan por terminadas cuando funcionen con datos reales.

## Decisiones tomadas

- (2026-11-15 03:00, David) /spectrum (T36): un punto por imagen (cada píxel de SPHEREx ve otra
  longitud de onda). La tabla WCS-WAVE es IDÉNTICA en todos los recortes de un detector y
  versión de proceso (verificado con datos reales); solo cambia CRPIX1W/2W en la cabecera. Por
  eso se baja una vez por detector y de cada imagen solo un recorte de 0.035° (~80 KB). Se
  guardan las "estampillas" (IMAGE + VARIANCE) en la caché y la fotometría se calcula al vuelo:
  cambiar la apertura o el anillo no descarga nada. Máximo 40 imágenes por detector. Flujo en
  mJy (BUNIT MJy/sr × área del píxel). La apertura sigue el movimiento propio (pmra, pmdec,
  epoca). Fotometría de apertura simple, sin corrección por PSF.
- (2026-11-15 03:30, David) "Excluir píxeles marcados" queda APAGADO por defecto: en Barnard
  (D1–D4) y R Draconis (todo) el centro satura y con el filtro no se ve casi nada. Los puntos
  saturados se dibujan como círculos huecos (flujo por debajo del real).

- (2026-11-15 madrugada, David) DOCKER PARA TODO EL EQUIPO: `docker-compose.yml` en la raíz
  levanta Redis, backend (puerto 8000, con --reload) y frontend (5173) con un solo comando.
  Quien prefiera Windows sin Docker sigue igual: no se cambió ningún comando del equipo.
  Detalle de Windows: el contenedor no se entera cuando editas un archivo, así que Vite usa
  "polling" (DOCKER_POLLING=1, ver vite.config.ts) y uvicorn WATCHFILES_FORCE_POLLING.
- (2026-11-15 madrugada, David) CACHÉ EN REDIS + DISCO (T14, parcial): cache.py guarda en los
  dos y lee primero de Redis (7 días de vida por clave). Si REDIS_URL está vacía o Redis no
  responde, usa solo el disco sin error: así Cloud Run y Windows sin Docker funcionan igual.
  Las pruebas apagan Redis en tests/__init__.py para no contaminar la caché real con imágenes
  falsas. Librería nueva: redis==8.1.0.
- (2026-11-15 madrugada, David) CENTRADO AL 1 DE ENERO: la página (App.ts, `epocaDeCentrado`)
  y precalcular.py mueven los objetivos por su movimiento propio hasta el 1 de enero del año
  en curso, no hasta "hoy". Antes la posición cambiaba cada día y la caché precalculada dejaba
  de servir (incluida la evaluación de diciembre). Barnard se mueve < 11″ al año: no se nota
  en un campo de 6′. tests/test_precalcular.py fija las coordenadas que calcula la página.
- (2026-11-15 madrugada, David) LA CACHÉ VIAJA EN LA IMAGEN DE PRODUCCIÓN: `backend/Dockerfile`
  copia `cache/` (solo tiene sentido después de correr precalcular.py). Cloud Run arranca con
  los 5 objetivos listos aunque IRSA esté caído. Hay que volver a publicar si cambia la caché.
- (2026-11-14 noche) ALADIN SIN CDS NI ESAC: se probó desde la red del equipo (navegador del
  desktop app, con CORS) qué servidores responden:
  | Servicio | Resultado |
  |---|---|
  | IRSA HiPS (DSS2, 2MASS K, AllWISE W1, cubo SPHEREx DR1) | OK, ~0.1 s |
  | VizieR espejo CfA (vizier.cfa.harvard.edu): Gaia DR3, AllWISE, Sesame | OK con CORS, 1 a 8 s |
  | MAST/AWS y CSIRO (DSS2) | OK, 0.5 a 1.5 s |
  | CDS (vizier, simbad, hipscat, sesame .cds.unistra.fr) | Alcanzable pero SIN CORS o timeout |
  | ESAC (skies.esac.esa.int) | NO responde (timeout de 20 s) |
  | IRSA TAP (gaia_dr3_source, allwise) | Más de 25 s: no sirve para el navegador |
  Por eso: fondo por defecto = DSS2 de IRSA; Gaia DR3 y AllWISE se dibujan con
  `A.catalogFromURL` sobre el espejo CfA de VizieR (cono = media diagonal del campo, máximo
  3000 y 2000 fuentes); clic en una fuente = tabla de datos de Aladin. Se agregó el fondo
  SPHEREx DR1 (cubo de 102 capas) que sigue la λ elegida en el panel.

- (2026-11-14 noche) CO-ADD CON MEDIANA: cada época se arma reproyectando sus recortes a una
  malla común (norte arriba, este a la izquierda, 6.15"/px, centrada en ra/dec) y tomando la
  mediana píxel a píxel, después de restarle a cada recorte su fondo (su mediana). La mediana
  quita rayos cósmicos; restar el fondo hace falta porque cada imagen de un detector está en una
  λ un poco distinta. Es para VER, no es fotometría calibrada. Todavía no se usan FLAGS ni
  VARIANCE (eso queda para T15).
- (2026-11-14 noche) CACHÉ DE LA API: se guarda (1) la lista de imágenes de la zona, una sola
  consulta SIA para los 6 detectores, y (2) la "pila" de épocas ya sumadas (.bin con NumPy).
  NO se guardan los recortes crudos (en Cloud Run el disco ocupa memoria RAM). Si alguna
  descarga falla, el resultado se entrega pero no se guarda, para reintentar la próxima vez.
  La caché no caduca: si IRSA publica épocas nuevas, hay que borrar la carpeta cache/.
- (2026-11-14 noche) /resolve responde los 5 objetivos de prueba sin internet (tabla en
  app/servicio.py) y para los demás usa SkyCoord.from_name (Sesame del CDS).
- (2026-11-14 noche) La página, en modo API, ya no filtra las épocas por λ (cada época suma
  todo el detector). Cambio de una línea en frontend/src/App.ts (filterObservations).

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

- Fondo SPHEREx en Aladin: la capa se elige con `setSliceNumber(índice)` usando la tabla de λ
  del archivo properties del HiPS. No se pudo comprobar visualmente que el índice coincida
  exacto con la λ (Aladin calcula la capa de forma lineal): revisar con un objeto brillante.
- Gaia DR3 alrededor de Barnard's Star tarda ~8 s (1243 fuentes en 6'): es normal.

- (2026-11-14 noche) SIN PROBAR CON DATOS REALES: la sesión de Claude no tenía acceso a IRSA.
  Cosas a revisar con datos reales: que la estrella quede en el centro y con el norte arriba
  (comparar con Aladin), cuánto tarda /frames la primera vez y si alguna época sale vacía.
- La página permite un campo de visión de hasta 40' (0.67 grados), pero el backend acepta
  hasta FOV_MAX = 0.5 grados: entre 30' y 40' la página mostrará "El campo de visión máximo
  es 0.5 grados". Decidir si se sube FOV_MAX o se limita la página a 30'.
- La caché precalculada (T16) queda en la carpeta cache/ de quien corre el script. Cloud Run
  empieza cada instancia con el disco vacío: para la demo hay que llevar esa caché (T14:
  bucket, o copiarla dentro de la imagen de Docker). DECISIÓN DEL EQUIPO.
- Sin acceso de escritura de Claude al repo (la app de Claude no está instalada en
  JesusEscudero-S/spacecore): los cambios de esta sesión se entregaron como archivo para subirlos a mano.

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

### 2026-11-15 04:45 — David (Claude, prueba completa mientras David dormía) — rama: docker
- Prueba de punta a punta en la página real (Docker en la computadora de David):
  - Backend con caché, 5 objetivos: /epocas 4–9 ms, /frames 5–9 ms, /diff 5–11 ms,
    /spectrum 28–32 ms. Funciona SIN IRSA (a esa hora IRSA estaba caído: una zona sin caché
    responde 504 con mensaje claro a los 9.5 s).
  - Interfaz: clic en objetivo -> imágenes en 70–170 ms; cambiar D1–D6 instantáneo; Comparar
    (Alternar, Deslizar, Diferencia, Suma) OK; Reproducir OK; Espectro de los 5 objetivos en
    150–290 ms; "Excluir píxeles marcados" (Barnard 240 -> 79 puntos); apertura 24" OK.
  - Errores (RA inválida, fov grande, detector malo, épocas iguales, etc.): 400/404/422 con
    mensaje en español. /resolve de nombres nuevos usa internet (Betelgeuse 2.4 s).
- CAUSA del "No se pudo calcular el espectro" que vio David: un clic sobre la imagen elige ese
  punto exacto para el espectro (a 7" del objetivo ya no está en la caché), pero el panel
  mostraba el centro. Arreglos (SIN commit, para revisar): clic a < 15" del centro = el
  objetivo; el panel y el título dicen "punto elegido" si no lo es; nota "variabilidad
  simulada" solo en modo demo; encabezados de la tabla sin mayúsculas (decían "Λ (MM)" y
  "FLUJO (MJY)" = megajansky); un solo pedido de espectro al entrar a la pestaña.
- Para probar en el navegador integrado se usó un proxy temporal en vite.config.ts; ya se
  revirtió.

### 2026-11-15 03:40 — David (con Claude) — rama: docker
- T36 /spectrum: backend (app/ciencia/espectro.py, servicio.espectro, router con apertura,
  anillo, fondo y movimiento propio), contrato actualizado en docs/api.md, 11 pruebas nuevas
  (tests/test_espectro.py, 71 en total), modo mock con espectro falso.
- Frontend: la pestaña Espectro nunca se mostraba (nadie quitaba `hidden` de #viewSpec): lo
  arregla Espectro.ts. El cliente manda apertura/anillo/pm y usa fecha, época, error y
  píxeles saturados; el espectro se recalcula solo al cambiar de objetivo.
- precalcular.py: ahora también prepara el espectro, verifica que cada resultado SÍ quedó en
  la caché y reintenta hasta 3 veces (antes decía OK aunque IRSA hubiera fallado, y esos
  detectores tardaban ~20 s cada vez que se abría la página).
- Resultados reales: Barnard ~4–6 Jy (D1–D4 saturado), Eps Indi B 3–53 mJy, WISE 0855 en el
  nivel del ruido (esperado: es muy débil), RW Aur sube de 0.2 a 2 Jy hacia el infrarrojo,
  R Draconis 4–16 Jy y todo saturado.
- Pendiente: README (T74); despliegue (cuentas de Jesús); PR de `docker` a main.

### 2026-11-15 02:15 — David (con Claude) — rama: docker
- Contexto: trabajé en paralelo con Juan sin saberlo (misma lista de tareas). Mi versión del
  backend quedó en un `git stash` ("respaldo: version paralela de David") y NO se usa: la rama
  `docker` parte del main del equipo (9a9686a) y solo agrega lo que no existía.
- Hecho (commit 2696fd5): docker-compose.yml, frontend/Dockerfile y .dockerignore,
  vite.config.ts con polling, cache.py con Redis + disco, config.py (REDIS_URL,
  REDIS_TTL_HORAS), requirements.txt (redis), tests/__init__.py (apaga Redis en pruebas),
  tests/test_cache_redis.py, tests/test_precalcular.py, App.ts y precalcular.py centrados al
  1 de enero. 60 pruebas OK en Docker.
- Hecho (este commit): Dockerfile copia cache/ a la imagen; .dockerignore y .gitignore
  ajustados (cache/.gitkeep se sube); backend/.gcloudignore; infra/cloudrun.env.yaml;
  infra/despliegue.md con los pasos de Cloud Run y Vercel.
- Precalculado: 5 objetivos x 6 detectores (unos 20 min; IRSA dio muchos 503 pero todo quedó).
  Corrido 2 veces: la segunda, todo en (0 s).
- Cómo probar: `docker compose up -d --build`, luego
  `docker compose exec backend python -m unittest discover -v` (60 OK) y abrir
  http://localhost:5173 (sin parámetros): los 5 botones cargan en 1 a 2 s. Redis:
  `docker compose exec redis redis-cli --scan --pattern "spacecore:*"` lista claves.
- Pendiente: ejecutar infra/despliegue.md (requiere cuentas de Google Cloud y Vercel, las tiene
  Jesús); /spectrum (T36); README (T74). Si la página se publica desde un main SIN esta rama,
  centrará en "hoy" y no aprovechará la caché precalculada.


### 2026-11-15 00:20 — Juan (con Claude) — rama: api/T22-T34-mvp-backend
- Hecho: PRIMERA PRUEBA CON DATOS REALES, exitosa. La primera búsqueda de Barnard tardó 25 s
  (algunas descargas dieron "503 Service Unavailable" de IRSA y se reintentaron); la segunda,
  0 s desde la caché. Arreglos tras verlo en la página:
  - El centro de estrellas muy brillantes salía con un punto NEGRO (píxeles saturados que
    SPHEREx marca sin dato). `rellenar_huecos` (ciencia/alinear.py) los rellena con el máximo
    de sus vecinos, solo para el PNG.
  - Descargas: 4 a la vez en lugar de 8, para que IRSA responda menos "503".
  - La página decía "Sin cuadros para mostrar" mientras /frames calculaba (~40 s la primera
    vez). Ahora dice "Cargando imágenes de SPHEREx… (la primera vez ~1 min)".
  - Aladin: el fondo SPHEREx mostraba otra longitud de onda (Aladin reparte las capas del cubo
    por FRECUENCIA). `numeroParaAladin` corrige la cuenta; comprobado: D1->capa 8, D3->42, D6->94.
- Pendiente: /spectrum (T36) no existe todavía (la vista "Espectro" muestra "No existe esa
  dirección"). El fondo SPHEREx de Aladin se ve saturado (falta ajustar cortes de brillo).
- Cómo correrlo en Windows sin comandos: en la carpeta de Juan hay `iniciar-spacecore.bat`
  (página) e `iniciar-backend.bat` (backend; crea .venv, instala, prueba Barnard y enciende
  uvicorn). Abrir http://localhost:5173/?api=http://127.0.0.1:8000 con las dos ventanas abiertas.


### 2026-11-15 00:00 — Juan (con Claude, sesión en la nube) — rama: api/T22-T34-mvp-backend
- Hecho: T51 completa (Aladin con Gaia DR3 y AllWISE superpuestos, fondo SPHEREx DR1 y retícula
  en el centro) y prueba de qué servidores responden desde la red del equipo (tabla en
  "Decisiones tomadas"). Cliente de la API: mensajes claros si el backend está apagado, sin
  CORS o tarda más de 3 min, y chequeo de /health al arrancar.
- Archivos: frontend/src/components/visor/VistaAladin.ts (reescrito), index.html (fondos y
  switch de AllWISE), src/api/cliente.ts, src/App.ts, src/components/busqueda/PanelInfo.ts.
- Cómo probar: `npm run dev` en frontend, abrir http://localhost:5173, activar "Gaia DR3" y
  "AllWISE" en el panel derecho: aparecen círculos naranjas y verdes y el texto "Gaia DR3: N
  fuentes". Clic en un círculo -> tabla con sus datos. En "Fondo" elegir SPHEREx DR1 y mover
  el control de λ.


### 2026-11-14 23:45 — Juan (con Claude, sesión en la nube) — rama: api/T22-T34-mvp-backend
- Hecho:
  - T23 + T22: backend/app/ciencia/alinear.py (`malla_objetivo`, `alinear_recorte`,
    `sumar_epoca`). Reproyecta cada recorte con `reproject` y suma por mediana.
  - T32, T33, T34, T35, T37 y T31: backend/app/servicio.py (une todo), routers/imagenes.py
    (/resolve, /epocas, /frames, /diff), errores.py (formato {"error"}), mock.py (USAR_MOCK=1).
    irsa.py: `buscar_imagenes(..., detector=None)` trae los 6 detectores en una consulta.
    imagen.py: `a_png(..., asinh=False)` para la diferencia (gris = sin cambio).
  - T16: backend/scripts/precalcular.py (5 objetivos, corrige el movimiento propio igual que
    la página).
  - T52: la página carga los cuadros reales del backend (arreglo del filtro de λ en App.ts).
  - Pruebas nuevas: tests/test_alinear.py y tests/test_api.py (IRSA simulado). Total: 48.
- A medias (y dónde quedó): falta la prueba con datos reales (ver "Problemas conocidos").
  /spectrum (T36, Extra) no está hecho.
- Siguiente paso: probar con datos reales, unir el PR y publicar (T61, T62, T63).
- Decisiones: co-add con mediana, qué se guarda en caché y /resolve con respaldo (ver arriba).
- Problemas: sin red a IRSA desde la sesión; FOV de la página mayor que FOV_MAX; la caché
  precalculada no viaja sola a Cloud Run.
- Cómo probar (PowerShell, desde backend con .venv activado):
  - `python -m unittest discover -v` -> termina en "Ran 48 tests ... OK".
  - Datos reales: `python -m scripts.precalcular --objetivos barnard --detectores D2` -> debe
    imprimir "OK  Barnard's Star  D2 ... 3 épocas" (o más) y "Listo.". La primera vez tarda
    1 a 3 minutos.
  - Servidor: `uvicorn app.main:app --reload` y abrir
    http://127.0.0.1:8000/epocas?ra=269.4521&dec=4.6934&det=D2 (lista de épocas) y
    http://127.0.0.1:8000/frames?ra=269.4521&dec=4.6934&det=D2 (JSON con PNG).
  - Página: en frontend `npm run dev` y abrir http://localhost:5173/?api=http://127.0.0.1:8000
    -> Barnard's Star con la línea de tiempo de épocas abajo y el botón Play.
  - Sin IRSA: con `$env:USAR_MOCK="1"` antes de uvicorn, la página muestra 3 épocas falsas
    con una estrella que sube.


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
