# Contrato de la API — SPACECORE

> **Versión 1 (2026-11-14).** Este archivo es la fuente de verdad de cómo se hablan la página
> (frontend) y el servidor (backend). Si un cambio de código necesita modificarlo, primero se
> cambia aquí y se avisa al equipo.
>
> Pendiente: revisarlo contra el diseño de interfaz del equipo cuando esté disponible.

## Reglas generales

- Todos los endpoints son `GET` y responden JSON en UTF-8.
- Dirección base en local: `http://127.0.0.1:8000`. En producción: la URL de Cloud Run
  (pendiente, tarea T61).
- Con la variable de entorno `USAR_MOCK=1` el backend responde datos falsos con este mismo
  formato.

### Parámetros comunes

| Parámetro | Tipo | Unidad | Valores permitidos | Por defecto |
|---|---|---|---|---|
| `ra` | número decimal | grados (ICRS) | de 0 a menos de 360 | obligatorio |
| `dec` | número decimal | grados (ICRS) | de -90 a 90 | obligatorio |
| `fov` | número decimal | grados | de 0.01 a `FOV_MAX` (hoy 0.5, provisional) | 0.1 |
| `det` | texto | - | `D1`, `D2`, `D3`, `D4`, `D5`, `D6` | `D2` |

- `fov` (campo de visión) es el lado del cuadrado de cielo que se muestra.
- `det` es el detector de SPHEREx; cada uno ve un rango distinto del infrarrojo.

### Fechas

Todas las fechas van en formato ISO 8601, en hora UTC y terminadas en `Z`.
Ejemplo: `"2025-06-14T03:21:07Z"`.

### Épocas

Una época es un grupo de imágenes de la misma zona tomadas en fechas cercanas (SPHEREx vuelve
a pasar por cada zona más o menos cada 6 meses). Se identifican como `E1`, `E2`, `E3`...,
ordenadas de la más antigua a la más reciente. El identificador vale para una misma
combinación de `ra`, `dec`, `fov` y `det`.

### Errores

Cualquier error responde con este formato y el código HTTP que corresponda. El mensaje está
en español y la página puede mostrarlo tal cual.

```json
{"error": "mensaje en español"}
```

| Código | Cuándo |
|---|---|
| 400 | El valor es válido como dato pero no está permitido (por ejemplo, `fov` mayor al máximo, o `a` igual a `b` en `/diff`). |
| 404 | No se encontró lo pedido: el nombre no existe, SPHEREx no tiene imágenes de esa zona, o la época no existe. |
| 422 | Falta un parámetro obligatorio o tiene un formato inválido (por ejemplo, `ra=hola` o `det=D9`). |
| 504 | El archivo de la NASA (IRSA) tardó demasiado o no respondió. |
| 500 | Error inesperado del servidor. |

---

## GET /health

Sirve para comprobar que el servidor está vivo. No recibe parámetros.

```json
{"status": "ok"}
```

---

## GET /resolve

Convierte el nombre de un objeto en coordenadas.

| Parámetro | Tipo | Descripción |
|---|---|---|
| `name` | texto, obligatorio | Nombre del objeto, por ejemplo `Barnard's Star`. |

Ejemplo: `GET /resolve?name=Barnard's Star`

```json
{
  "name": "Barnard's Star",
  "ra": 269.4521,
  "dec": 4.6934
}
```

- `name`: el mismo texto que se envió.
- `ra`, `dec`: en grados decimales ICRS. Los valores del ejemplo son aproximados.

Errores: 404 si el nombre no se encuentra; 422 si falta `name`; 504 si el servicio de nombres
no responde.

---

## GET /epocas

Dice en qué épocas hay imágenes de esa zona.

Parámetros: `ra`, `dec`, `fov`, `det` (ver "Parámetros comunes").

Ejemplo: `GET /epocas?ra=269.4521&dec=4.6934&fov=0.1&det=D2`

```json
{
  "epocas": [
    {
      "id": "E1",
      "inicio": "2025-06-14T03:21:07Z",
      "fin": "2025-06-16T18:40:52Z",
      "n_imagenes": 12
    },
    {
      "id": "E2",
      "inicio": "2025-12-10T09:05:33Z",
      "fin": "2025-12-12T22:17:01Z",
      "n_imagenes": 9
    }
  ]
}
```

- `inicio`, `fin`: fecha de la primera y de la última imagen de la época.
- `n_imagenes`: cuántas imágenes se combinan en esa época.
- Las fechas y cantidades del ejemplo son inventadas, solo muestran el formato.
- Campo opcional futuro (tarea T15): `calidad`, un indicador de píxeles con defectos.

Errores: 400 si `fov` supera el máximo; 404 si no hay imágenes en esa zona; 422 por parámetros
inválidos; 504 si IRSA no responde.

---

## GET /frames

Entrega una imagen PNG por época, lista para animar.

Parámetros: `ra`, `dec`, `fov`, `det` (ver "Parámetros comunes").

Ejemplo: `GET /frames?ra=269.4521&dec=4.6934&fov=0.1&det=D2`

```json
{
  "frames": [
    {
      "epoca": "E1",
      "fecha": "2025-06-15T11:00:59Z",
      "png": "data:image/png;base64,iVBORw0KGgo..."
    },
    {
      "epoca": "E2",
      "fecha": "2025-12-11T15:41:17Z",
      "png": "data:image/png;base64,iVBORw0KGgo..."
    }
  ],
  "meta": {
    "detector": "D2",
    "fov_grados": 0.1,
    "ra": 269.4521,
    "dec": 4.6934,
    "tamano_px": 256
  }
}
```

- `frames`: ordenados de la época más antigua a la más reciente.
- `fecha`: punto medio entre el inicio y el fin de la época.
- `png`: imagen como "data URL", lista para usarse en `<img src="...">` o en un canvas.
- Todas las imágenes de una respuesta tienen el mismo tamaño, la misma zona de cielo y la misma
  escala de brillo, para que se puedan comparar al animarlas.
- Orientación: norte arriba y este a la izquierda. El centro de la imagen es (`ra`, `dec`).
- `meta.tamano_px`: ancho y alto del PNG en píxeles (es cuadrado).
- `meta.ra`, `meta.dec` y `meta.tamano_px` se agregaron en esta versión respecto a la propuesta
  inicial: la página los necesita para convertir un clic en coordenadas (tarea T55).

Esta consulta puede tardar alrededor de 1 minuto la primera vez (después queda en caché).

Errores: 400 si `fov` supera el máximo; 404 si no hay imágenes en esa zona; 422 por parámetros
inválidos; 504 si IRSA no responde.

---

## GET /diff

Entrega la imagen de diferencia entre dos épocas: lo que cambió resalta.

| Parámetro | Tipo | Descripción |
|---|---|---|
| `ra`, `dec`, `fov`, `det` | - | Ver "Parámetros comunes". |
| `a` | texto, obligatorio | Identificador de la primera época, por ejemplo `E1`. |
| `b` | texto, obligatorio | Identificador de la segunda época, por ejemplo `E3`. |

Ejemplo: `GET /diff?ra=269.4521&dec=4.6934&fov=0.1&det=D2&a=E1&b=E3`

```json
{
  "png": "data:image/png;base64,iVBORw0KGgo...",
  "epoca_a": "E1",
  "epoca_b": "E3"
}
```

- La imagen es la época `b` menos la época `a`.
- Gris significa sin cambio. Un objeto que se movió aparece como un par claro/oscuro.
- Mismo tamaño y orientación que las imágenes de `/frames`.

Errores: 400 si `a` y `b` son la misma época o `fov` supera el máximo; 404 si alguna época no
existe; 422 por parámetros inválidos; 504 si IRSA no responde.

---

## GET /spectrum

Entrega el espectro de un punto: cuánto brilla en cada longitud de onda del infrarrojo.

| Parámetro | Tipo | Descripción |
|---|---|---|
| `ra`, `dec` | - | Ver "Parámetros comunes". |

Ejemplo: `GET /spectrum?ra=269.4521&dec=4.6934`

```json
{
  "puntos": [
    {"lambda_um": 0.82, "flujo": 15.3},
    {"lambda_um": 1.47, "flujo": 22.8},
    {"lambda_um": 4.21, "flujo": 9.6}
  ],
  "unidad_flujo": "<unidad que indica el archivo de SPHEREx>"
}
```

- `lambda_um`: longitud de onda en micras (entre 0.75 y 5).
- `puntos`: ordenados de menor a mayor longitud de onda.
- `unidad_flujo`: texto con la unidad del flujo. El backend lo copia del propio archivo de
  SPHEREx, así no queda escrito a mano en el código. Se agregó en esta versión respecto a la
  propuesta inicial.
- Los valores del ejemplo son inventados, solo muestran el formato.

Errores: 404 si no hay imágenes en ese punto; 422 por parámetros inválidos; 504 si IRSA no
responde.

---

## Tipos TypeScript (para el frontend)

Estos tipos describen las mismas respuestas de arriba. Se copian a `frontend/src/api/` en la
tarea T42.

```ts
export type Detector = 'D1' | 'D2' | 'D3' | 'D4' | 'D5' | 'D6'

export interface ErrorApi {
  error: string
}

export interface RespuestaResolve {
  name: string
  ra: number
  dec: number
}

export interface Epoca {
  id: string
  inicio: string
  fin: string
  n_imagenes: number
}

export interface RespuestaEpocas {
  epocas: Epoca[]
}

export interface Frame {
  epoca: string
  fecha: string
  png: string
}

export interface MetaFrames {
  detector: Detector
  fov_grados: number
  ra: number
  dec: number
  tamano_px: number
}

export interface RespuestaFrames {
  frames: Frame[]
  meta: MetaFrames
}

export interface RespuestaDiff {
  png: string
  epoca_a: string
  epoca_b: string
}

export interface PuntoEspectro {
  lambda_um: number
  flujo: number
}

export interface RespuestaSpectrum {
  puntos: PuntoEspectro[]
  unidad_flujo: string
}
```

## Valores provisionales

Estos valores se eligieron para poder avanzar y se pueden cambiar sin romper el formato:

- `FOV_MAX` = 0.5 grados y `fov` mínimo = 0.01 grados.
- `fov` por defecto = 0.1 grados.
- `det` por defecto = `D2`.
- `tamano_px` = 256.
