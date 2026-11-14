# SPACECORE

Proyecto para el reto **"Planet X and SPHEREx"** del NASA Space Apps Challenge 2026.

Una herramienta web donde escribes coordenadas del cielo (RA/Dec) o el nombre de un objeto y ves
una secuencia de imágenes de la misión SPHEREx de esa zona en distintas fechas, como un pequeño
video, para detectar objetos que se mueven o que cambian de brillo.

> Estado: estructura inicial del proyecto. Todavía no hay funciones.

## Cómo correrlo (Windows PowerShell)

Necesitas Python 3.13 y Node.js instalados.

### Backend (servidor)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abre http://127.0.0.1:8000/health y debes ver `{"status":"ok"}`.
La documentación automática está en http://127.0.0.1:8000/docs.

Solo si vas a usar los notebooks: `pip install -r requirements-dev.txt` (agrega Jupyter).

### Frontend (página)

```powershell
cd frontend
npm install
npm run dev
```

Abre http://localhost:5173 y debes ver el título SPACECORE.

## Carpetas

| Carpeta | Qué contiene |
|---|---|
| `backend/` | API con FastAPI (Python) |
| `frontend/` | Página con React + Vite (TypeScript) |
| `docs/` | Contrato de la API (`api.md`), bitácora (`PROGRESO.md`) y plan de tareas (`plan/tareas.csv`) |
| `notebooks/` | Experimentos de ciencia |
| `infra/` | Archivos de despliegue |

## Cómo trabajamos

- Nadie hace commit directo a `main`. Cada tarea va en su rama (`<prefijo>/<ID>-<tema>`) y entra
  con un Pull Request.
- Las reglas completas del equipo están en `CLAUDE.md`.
