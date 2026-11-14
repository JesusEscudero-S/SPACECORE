# Contrato de la API — SPACECORE

> **Estado: PROPUESTA.** Falta aprobarlo entre frontend y backend (tarea T02).
> Una vez aprobado, este archivo es la fuente de verdad y solo se cambia avisando a todo el equipo.

## Reglas generales

- Todos los endpoints son `GET` y responden JSON.
- Coordenadas (`ra`, `dec`) en **grados decimales ICRS**.
- `fov` (campo de visión) en **grados**.
- `det` (detector) es uno de `D1`, `D2`, `D3`, `D4`, `D5`, `D6`.
- Los errores siempre tienen este formato, con el código HTTP adecuado:

```json
{"error": "mensaje en español"}
```

- Con la variable de entorno `USAR_MOCK=1` el backend responde datos falsos con este mismo
  formato, para que el frontend avance sin esperar.

## Endpoints

| Endpoint | Parámetros | Respuesta |
|---|---|---|
| `GET /health` | - | `{"status": "ok"}` |
| `GET /resolve` | `name` | `{"name": "Barnard's Star", "ra": <grados>, "dec": <grados>}` |
| `GET /epocas` | `ra`, `dec`, `fov`, `det` | `{"epocas": [{"id": "E1", "inicio": "<fecha>", "fin": "<fecha>", "n_imagenes": <n>}]}` |
| `GET /frames` | `ra`, `dec`, `fov`, `det` | `{"frames": [{"epoca": "E1", "fecha": "<fecha>", "png": "data:image/png;base64,..."}], "meta": {"detector": "D2", "fov_grados": <n>}}` |
| `GET /diff` | `ra`, `dec`, `fov`, `det`, `a`, `b` | `{"png": "data:image/png;base64,...", "epoca_a": "E1", "epoca_b": "E3"}` |
| `GET /spectrum` | `ra`, `dec` | `{"puntos": [{"lambda_um": <n>, "flujo": <n>}]}` |

## Pendiente de definir en T02

- Tipo y rango exacto de cada parámetro (por ejemplo, valor máximo de `fov`).
- Formato exacto de las fechas.
- Un ejemplo completo de respuesta por endpoint.
- Códigos HTTP de error de cada endpoint.
