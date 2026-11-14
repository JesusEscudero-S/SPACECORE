# PROGRESO — SPACECORE

Bitácora compartida para que cualquier integrante (y su Claude Code) pueda continuar el trabajo
de otro. Claude Code la lee al empezar y la actualiza al terminar cada sesión.
Las entradas nuevas van ARRIBA en el historial. No borres entradas anteriores.

## Estado actual (actualizar en cada relevo)

| Campo | Valor |
|---|---|
| Última actualización | 2026-11-14 14:30 |
| Última persona que trabajó | Jesús (rol #6) |
| Rama activa | main (solo para el primer commit; desde ahora, una rama por tarea) |
| Tarea en curso | T03 Repositorio listo |
| Punto exacto donde quedó | Estructura creada y probada en local, con el primer commit en main. Falta la parte de GitHub. |
| Siguiente paso concreto | Crear el repo vacío en GitHub, subir main, proteger main e invitar a los 5 compañeros. Luego T02 (aprobar el contrato). |
| ¿El código actual funciona? | Sí: el backend responde /health y el frontend abre con los 4 componentes vacíos. |

## Tareas terminadas (unidas a main)

- (ninguna todavía)

## Decisiones tomadas

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

- El servidor del CDS (aladin.cds.unistra.fr) tuvo fallas: usar Aladin Lite desde npm
  (`aladin-lite`), no desde la etiqueta <script> del CDS. El servicio que convierte nombres en
  coordenadas (Sesame del CDS) también puede fallar: tener las coordenadas de los 5 objetivos
  de prueba como respaldo.

## Historial de sesiones (la más reciente arriba)

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
