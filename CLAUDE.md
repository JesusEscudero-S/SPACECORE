# CLAUDE.md — SPACECORE (reto "Planet X and SPHEREx", NASA Space Apps Challenge 2026)

Este archivo le da a Claude Code el contexto del proyecto SPACECORE. Léelo completo al inicio de cada sesión,
y después lee docs/PROGRESO.md (ver "Continuidad entre sesiones y personas").

## Sobre el equipo (importante)

- Somos 6 estudiantes y es nuestro PRIMER hackathon. Somos principiantes.
- Explica en español, en palabras simples, qué vas a hacer y por qué ANTES de escribir código.
- Después de cada cambio, di cómo probarlo (comando exacto y qué se debe ver).
- Prefiere soluciones simples y legibles a soluciones "elegantes".
- Si algo de la tarea no está claro o hay que tomar una decisión importante, PREGUNTA antes de hacerlo.
- Tenemos 2 días (08:00 a 18:00). Prioridad: que el MVP funcione publicado al final del Día 1.

## Qué estamos construyendo

Reto: "Planet X and SPHEREx". Una herramienta web pública donde el usuario escribe coordenadas
del cielo (RA/Dec) o el nombre de un objeto, y ve una secuencia de imágenes de la misión SPHEREx
de esa zona tomadas en distintas fechas, como un pequeño video (efecto "blink"), para detectar
objetos que se mueven (enanas marrones, estrellas cercanas, asteroides) o que cambian de brillo.

- SPHEREx (NASA) mapea todo el cielo cada ~6 meses desde mayo de 2025, en 102 bandas del
  infrarrojo cercano (0.75 a 5 micras), con 6 detectores (D1 a D6).
- Referencia de lo que buscamos: WiseView (http://byw.tools/wiseview), hecho para la misión WISE.
- Objetivos de prueba (TODO debe funcionar con estos 5):
  - Barnard's Star (se mueve rápido)
  - Epsilon Indi B (par de enanas marrones junto a una estrella)
  - WISE 0855 (enana marrón que se mueve rápido; RA 08h55m10.831s, Dec -07d14m42.53s)
  - RW Aurigae (estrella variable)
  - R Draconis (estrella variable)
- Extras que valora el reto: sumar imágenes por detector para mejorar la señal, sumar o restar
  épocas, elegir campo de visión, superponer Gaia y WISE, coordenadas en la URL, mostrar banderas
  de calidad y generar espectros al vuelo.

## Arquitectura

```
[Navegador: React + Vite (Vercel)]
        |  HTTP GET (JSON)
        v
[API: FastAPI en Docker (Google Cloud Run, us-east4)]  <- sin estado, sin base de datos
        |-- IRSA (NASA/IPAC): consulta TAP/SIA + servicio de recortes (cutouts)
        |-- (opcional) bucket público de SPHEREx en AWS S3: s3://nasa-irsa-spherex
        |-- Caché: en disco al inicio; la definitiva está POR DECIDIR (bucket u otra)
[Aladin Lite en el navegador: mapa del cielo + Gaia DR3 + WISE, servidos por el CDS]
```

- No usamos base de datos: IRSA es la fuente de datos. Solo guardamos resultados ya calculados.
- La caché debe usarse a través de una interfaz simple `get(clave)` / `set(clave, datos)` en
  `backend/app/datos/cache.py`, para poder cambiar la implementación sin tocar el resto del código.

## Tecnologías (decididas por el equipo; no agregues otras sin preguntar)

- Frontend: TypeScript, React, Vite, Node.js + npm, HTML5 Canvas, estado en la URL
  (URLSearchParams), Aladin Lite v3 (`aladin-lite`), Plotly.js (`plotly.js-dist-min`).
- Backend: Python 3.13, FastAPI + Uvicorn, Astropy, Astroquery, PyVO, NumPy, Pillow, reproject,
  httpx + asyncio, fsspec/s3fs, Jupyter para experimentar.
- Infraestructura: Docker, Google Cloud Run, Vercel. GitHub para el código.
- Sistema operativo del equipo: Windows (PowerShell). Da los comandos para PowerShell.

## Estructura del repositorio

```
spacecore/
├── CLAUDE.md
├── README.md
├── docs/
│   ├── PROGRESO.md             # bitácora de relevo entre sesiones y personas
│   ├── api.md                  # contrato de la API (fuente de verdad)
│   └── plan/                   # plan de trabajo: tareas.csv y guías del equipo
├── backend/
│   ├── app/
│   │   ├── main.py             # crea la app FastAPI, CORS, incluye routers
│   │   ├── config.py           # variables de entorno (pydantic-settings)
│   │   ├── routers/            # endpoints (/resolve, /epocas, /frames, /diff, /spectrum, mock)
│   │   ├── datos/              # IRSA, descargas, épocas, caché
│   │   └── ciencia/            # escala de brillo, co-add, alineación, diferencia, espectro
│   ├── scripts/                # precalcular.py, etc.
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .dockerignore
│   └── .env.example            # nunca subir .env real
├── frontend/                   # proyecto Vite (react-ts)
│   └── src/
│       ├── App.tsx
│       ├── api/                # cliente.ts: llamadas a la API
│       └── components/
│           ├── busqueda/       # Buscador, botones de objetivos, panel de info (rol #1)
│           └── visor/          # Reproductor (canvas), VistaAladin, Espectro (rol #2)
├── notebooks/                  # experimentos de ciencia
└── infra/                      # archivos de despliegue y configuración
```

## Roles y carpetas (no modifiques carpetas de otro rol sin que te lo pida)

> **Cambio de reparto (2026-11-14):** Jesús, con Claude Code, desarrolla todo el código del
> proyecto (las tareas de los roles #1 a #6). El resto del equipo prepara el pitch (T65 y T75).
> Si trabajas con Jesús, puedes modificar cualquier carpeta. La tabla de abajo se conserva como
> referencia de qué carpeta corresponde a cada parte del proyecto y de los prefijos de ramas.

| Rol | Qué hace | Carpetas | Prefijo de ramas |
|---|---|---|---|
| #1 Frontend - interfaz | Layout, buscador, URL, cliente de la API | frontend/src/components/busqueda, frontend/src/api, App.tsx | front-ui/ |
| #2 Frontend - visualización | Reproductor, Aladin, espectro | frontend/src/components/visor | front-viz/ |
| #3 Backend - API | Contrato, FastAPI, endpoints, mocks, errores | backend/app/main.py, config.py, routers/ | api/ |
| #4 Backend - datos | IRSA, descargas, épocas, caché, precálculo | backend/app/datos, backend/scripts | datos/ |
| #5 Ciencia | Imagen a PNG, co-add, alineación, diferencia, espectro | backend/app/ciencia, notebooks | ciencia/ |
| #6 Infra + presentación | Repo, Docker, Cloud Run, Vercel, unir PRs | backend/Dockerfile, infra, docs | infra/ |

## Continuidad entre sesiones y personas (MUY IMPORTANTE)

Varias personas del equipo usan Claude Code (cada una con su propia cuenta) y se pueden relevar
cuando a alguien se le acaban los límites de uso. Tú no recuerdas sesiones anteriores, así que
la memoria compartida del proyecto es el archivo `docs/PROGRESO.md` y el historial de git.

Al EMPEZAR cada sesión:
1. Lee CLAUDE.md y docs/PROGRESO.md.
2. Ejecuta `git status`, `git branch` y `git log --oneline -10` para ver en qué estado quedó todo.
3. Resume en 3-5 líneas: qué está hecho, qué quedó a medias y cuál es el siguiente paso.
   Pregunta si seguimos con eso o con otra tarea.

DURANTE la sesión:
- Haz commits pequeños y frecuentes (cada avance que funcione), para que nada se pierda si la
  sesión se corta de repente por límites de uso.

Al TERMINAR la sesión, o cuando yo diga "prepara el relevo":
1. Actualiza docs/PROGRESO.md (no lo borres: agrega una entrada nueva arriba del historial y
   actualiza la tabla de estado) con: fecha y hora, quién trabajó, rama, tareas hechas, tareas a
   medias con el punto exacto donde quedaron, siguiente paso concreto, decisiones tomadas,
   problemas conocidos y comandos para probar.
2. Haz commit de todo lo que funcione, incluido PROGRESO.md, con el mensaje
   "relevo: <resumen corto>". Si algo quedó a medias y no funciona, haz commit igual en la rama
   de la tarea con el prefijo "WIP:" y anótalo en PROGRESO.md.
3. Haz `git push` de la rama para que el compañero que sigue pueda bajarla.
4. Dime el nombre de la rama y el texto exacto que mi compañero debe darle a su Claude Code
   para continuar.

Nunca dejes trabajo importante sin commit ni sin push: lo que no está en GitHub, el siguiente
compañero no lo puede ver.

## Plan de trabajo

- Todas las tareas están en `docs/plan/tareas.csv` (ID, tarea, rol, día, horario, prioridad,
  depende de, criterio de "lista", descripción detallada).
- Cuando te pidan "haz la tarea T34", lee esa fila completa (en especial "Descripción detallada"
  y "Está lista cuando...") y revisa que sus dependencias existan antes de empezar.
- Prioridades: MVP > Importante > Extra. No empieces un Extra si el MVP no funciona.

## Contrato de la API (propuesta; la versión vigente está en docs/api.md)

Coordenadas en grados decimales ICRS. `fov` en grados. `det` = D1..D6. Errores siempre como
`{"error": "mensaje en español"}` con el código HTTP adecuado.

| Endpoint | Parámetros | Respuesta |
|---|---|---|
| GET /health | - | `{"status": "ok"}` |
| GET /resolve | name | `{"name": "Barnard's Star", "ra": <grados>, "dec": <grados>}` |
| GET /epocas | ra, dec, fov, det | `{"epocas": [{"id": "E1", "inicio": "<fecha>", "fin": "<fecha>", "n_imagenes": <n>}]}` |
| GET /frames | ra, dec, fov, det | `{"frames": [{"epoca": "E1", "fecha": "<fecha>", "png": "data:image/png;base64,..."}], "meta": {"detector": "D2", "fov_grados": <n>}}` |
| GET /diff | ra, dec, fov, det, a, b | `{"png": "data:image/png;base64,...", "epoca_a": "E1", "epoca_b": "E3"}` |
| GET /spectrum | ra, dec | `{"puntos": [{"lambda_um": <n>, "flujo": <n>}]}` |

- Con `USAR_MOCK=1` el backend responde datos falsos con este mismo formato (para que el
  frontend avance sin esperar).
- Si un cambio requiere modificar el contrato, DETENTE y avísame: hay que acordarlo con el equipo.

## Datos de SPHEREx (notas técnicas)

- Fuente: NASA/IPAC Infrared Science Archive (IRSA). Tutoriales oficiales:
  https://caltech-ipac.github.io/irsa-tutorials/spherex/ (en especial "Spectral Image Cutouts").
- Consulta recomendada (del tutorial oficial): `astroquery.ipac.irsa.Irsa.query_tap` sobre las
  tablas `spherex.artifact` y `spherex.plane` (unidas por `planeid`), filtrando con
  `1 = CONTAINS(POINT('ICRS', ra, dec), p.poly)` y `p.energy_bandpassname = 'SPHEREx-D2'`,
  ordenando por `p.time_bounds_lower`. URL del recorte:
  `'https://irsa.ipac.caltech.edu/' || a.uri || '?center={ra},{dec}d&size={fov}'`.
  La consulta puede tardar ~20 s.
- TAP da los datos en cuanto se ingestan (semanal); SIA tiene ~1 día de retraso.
- Versiones de datos: los tutoriales indican que QR3 y DR1 reemplazan a QR2. La colección o
  versión debe ir en `config.py` (variable de entorno), nunca escrita en el código.
- Cada recorte es un FITS multi-extensión: IMAGE, FLAGS, VARIANCE, ZODI, PSF y WCS-WAVE.
  El header de IMAGE trae el WCS espacial y un WCS alterno 'W' para la longitud de onda.
- Existe un HiPS de todo el cielo de SPHEREx (102 capas) que Aladin Lite puede mostrar:
  https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube
- Verificado con datos reales el 2026-11-14: (1) usamos el servicio SIA
  (`Irsa.query_sia` con las colecciones `spherex_dr1` y `spherex_qr3`) porque la consulta TAP
  de arriba tardaba más de 6 minutos y daba error 502, mientras SIA responde en 1 a 3 s; (2) el
  píxel mide 6.15 arcsec; (3) la imagen viene en MJy/sr; (4) la extensión de PSF se llama EPSF;
  (5) cada recorte pesa ~3.9 MB por la tabla EPSF.
- VERIFICA contra la documentación oficial antes de fijar en código: tamaño de píxel de SPHEREx
  (~6.2 arcsec), nombre de la colección vigente, tabla de Gaia DR3 en VizieR (I/355/gaiadr3) y
  la API de Aladin Lite. Si no puedes verificar algo, dilo.

## Reglas de trabajo con Git

- Nunca hagas commit directo a `main`. Cada tarea en su rama: `<prefijo>/<ID>-<tema>`
  (ejemplo: `front-ui/T41-buscador`).
- Commits pequeños que empiecen con el ID: `T41: validar RA y Dec`.
- No hagas `git push --force`, ni borres ramas, ni reescribas historia sin preguntar.
- Antes de terminar: el código corre, no hay errores obvios, y explicas cómo probarlo.

## Lo que NUNCA debes hacer

- Subir secretos (contraseñas, tokens, URLs privadas). Van en `.env` (ignorado por git).
- Subir archivos `.fits`, la carpeta `cache/`, `node_modules/` o `.venv/`.
- Agregar librerías, servicios o bases de datos que no estén en la lista sin preguntar.
- Cambiar archivos de otro rol "de paso" para arreglar algo: avísame y lo coordinamos.
- Inventar datos científicos o resultados: si algo no se puede verificar, dilo.

## Comandos útiles (Windows PowerShell)

```powershell
# Backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload          # http://127.0.0.1:8000/docs

# Frontend
cd frontend
npm install
npm run dev                            # http://localhost:5173

# Docker (con Docker Desktop abierto)
docker build -t planetx-api backend
docker run -p 8080:8080 planetx-api    # http://localhost:8080/health
```
