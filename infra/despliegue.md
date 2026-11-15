# Cómo publicar SPACECORE (T61, T62 y T63)

Backend en **Google Cloud Run** y página en **Vercel**, como decidió el equipo. Comandos para
Windows PowerShell, desde la carpeta raíz del proyecto (`SPACECORE`).

Tiempo estimado la primera vez: 30 a 45 minutos. Las veces siguientes: 5 minutos.

## Antes de empezar (una sola vez)

1. **Google Cloud**: un proyecto con facturación activada (pide tarjeta, pero Cloud Run tiene
   capa gratuita de sobra para el hackathon). Apunta el **ID del proyecto** (no el nombre).
2. **gcloud CLI** instalado: https://cloud.google.com/sdk/docs/install (reinicia la terminal
   después de instalarlo).
3. **Cuenta de Vercel** (gratis) conectada a GitHub: https://vercel.com/signup
4. **La rama con los cambios de Docker unida a `main`** (o publicar desde esa rama). Si la
   página se publica desde un `main` sin esos cambios, centrará los objetivos en la posición de
   "hoy" y no encontrará nada en la caché precalculada: la demo cargaría lento.

## Paso 0: precalcular los 5 objetivos (en tu computadora, con Docker)

La imagen de producción lleva la caché **adentro** (ver `backend/Dockerfile`). Lo que no esté
calculado en este momento, no estará en la nube.

```powershell
docker compose up -d
docker compose exec backend python -m scripts.precalcular
```

Debe terminar con `Listo.` y, si lo corres otra vez, todas las líneas en `(0 s)`.
Comprueba que la carpeta `backend\cache` tenga archivos `.bin` (son las imágenes ya sumadas).

## Paso 1: backend en Cloud Run

```powershell
gcloud auth login
gcloud config set project ID-DEL-PROYECTO
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

gcloud run deploy spacecore-api `
  --source backend `
  --region us-east4 `
  --allow-unauthenticated `
  --memory 1Gi --cpu 1 --cpu-boost `
  --timeout 300 `
  --max-instances 10 `
  --env-vars-file infra/cloudrun.env.yaml
```

- Si pregunta si crea un repositorio de Artifact Registry, responde **Y**.
- Tarda de 5 a 10 minutos: sube la carpeta `backend`, construye la imagen y la publica.
- Al final imprime `Service URL: https://spacecore-api-XXXX.us-east4.run.app`. **Guárdala.**

Comprobar (sustituye la URL por la tuya):

```powershell
curl https://spacecore-api-XXXX.us-east4.run.app/health
curl "https://spacecore-api-XXXX.us-east4.run.app/epocas?ra=269.4463&dec=4.7680&fov=0.1&det=D2"
```

La primera debe responder `{"status":"ok"}` y la segunda las 3 épocas de Barnard's Star en
menos de 2 segundos (sale de la caché que viaja en la imagen).

## Paso 2: página en Vercel

Más fácil desde la web:

1. https://vercel.com/new → **Import** el repositorio `SPACECORE`.
2. **Root Directory**: `frontend` (botón *Edit*). Framework: detecta **Vite** solo.
3. **Environment Variables**: agrega `VITE_API_URL` = la URL de Cloud Run del paso 1
   (sin barra al final). **Si se te olvida, la página se publica en MODO DEMOSTRACIÓN con datos
   falsos** y abajo a la izquierda dirá "MODO DEMOSTRACIÓN".
4. Si la rama con los cambios de Docker aún no está en `main`, en *Settings → Git →
   Production Branch* pon esa rama.
5. **Deploy**. En 1 o 2 minutos da una dirección `https://spacecore-XXXX.vercel.app`.

## Paso 3: permitir que la página hable con el backend (CORS)

Sin esto, la página carga pero toda búsqueda falla con "Failed to fetch".

1. Abre `infra/cloudrun.env.yaml` y pon la dirección de Vercel (sin barra al final):
   ```yaml
   CORS_ORIGINS: "https://spacecore-XXXX.vercel.app,http://localhost:5173"
   ```
2. Aplica el cambio (no reconstruye la imagen, tarda 1 minuto):
   ```powershell
   gcloud run services update spacecore-api --region us-east4 --env-vars-file infra/cloudrun.env.yaml
   ```

## Paso 4: probar la página publicada (T63 y T73)

Abre la dirección de Vercel y revisa:

- [ ] Abajo a la izquierda dice **"API · datos del backend"** (no "MODO DEMOSTRACIÓN").
- [ ] Los 5 botones de objetivos cargan en 1 o 2 segundos y la línea de tiempo muestra 3 o más
      épocas.
- [ ] En la Estrella de Barnard, al dar **Reproducir**, la estrella del centro se mueve entre
      épocas y las demás quedan fijas.
- [ ] Cambiar de detector (D1 a D6) también carga rápido.
- [ ] Una búsqueda nueva (por ejemplo `Vega`) tarda hasta 1 minuto la primera vez y después
      queda rápida. Si IRSA está caído, muestra un mensaje en español y no se traba.

## Cuándo volver a publicar

| Qué cambió | Qué hacer |
|---|---|
| Código del backend o la caché precalculada | Repetir el **paso 1** (el mismo comando `gcloud run deploy`) |
| Código de la página | Nada: Vercel vuelve a publicar solo con cada `git push` a la rama de producción |
| La dirección de Vercel | Repetir el **paso 3** |

## Si algo falla

- **"Failed to fetch" en la página**: casi siempre es CORS. La dirección en `CORS_ORIGINS` tiene
  que ser idéntica a la de la barra del navegador (con `https://`, sin barra al final).
- **La primera petición tarda 10 segundos**: es el arranque en frío de Cloud Run. Para que no
  pase durante la evaluación, se puede dejar una instancia siempre encendida (cuesta unos
  centavos por hora): `gcloud run services update spacecore-api --region us-east4 --min-instances 1`.
  Al terminar, volver a `--min-instances 0`.
- **Error 504 en una búsqueda nueva**: IRSA (NASA) no respondió. Reintentar en un minuto. Los 5
  objetivos de prueba no dependen de IRSA porque van en la caché.
- **`gcloud` dice que falta un permiso o facturación**: revisa que el proyecto tenga facturación
  activa y que tu cuenta sea propietaria o editora del proyecto.
- **Ver los registros del backend en la nube**:
  ```powershell
  gcloud run services logs read spacecore-api --region us-east4 --limit 50
  ```

## Lo que NO hace esta configuración

- Redis no existe en Cloud Run: el backend usa solo la caché en disco que viaja en la imagen (y
  lo que calcule en caliente vive en memoria mientras la instancia siga viva). Es suficiente
  para la demo.
- La caché no se actualiza sola cuando SPHEREx publica datos nuevos: hay que volver a correr el
  paso 0 y el paso 1.
