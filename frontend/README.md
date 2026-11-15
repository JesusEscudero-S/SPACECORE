# SPACECORE · frontend (TypeScript + Vite, SIN React)

Interfaz completa: buscador, reproductor de épocas (blink), comparar (deslizar/diferencia/suma),
espectro, Aladin Lite y estado en la URL. Si alguien prefiere React, puede adaptar `src/components/`.

Requisito: Node.js 20 o superior.

```powershell
npm install
npm run dev          # http://localhost:5173  -> MODO DEMO (datos simulados, sin backend)
npm run typecheck    # revisa tipos
npm run build        # genera dist/ (Vercel)
```

## Conectar con el backend
1. Copia `.env.example` a `.env` y pon `VITE_API_URL=http://127.0.0.1:8000`
   (o abre `http://localhost:5173/?api=http://127.0.0.1:8000` sin tocar nada).
2. El backend debe permitir CORS desde `http://localhost:5173`.
3. Con `USAR_MOCK=1` en el backend se puede probar el flujo completo.

`src/api/cliente.ts` implementa `docs/api.md` (propuesta T02): `/resolve?name`, `/epocas`, `/frames`,
`/spectrum`. Si el contrato cambia, solo hay que editar ese archivo.

## Estructura (respeta CLAUDE.md, con TypeScript plano en vez de .tsx)
| Repo (React)                        | Aquí                                              |
|-------------------------------------|---------------------------------------------------|
| `main.tsx`, `App.tsx`               | `src/main.ts`, `src/App.ts` (arranque y lógica)   |
| `api/cliente.ts`                    | `src/api/cliente.ts` (+ `demoSource.ts`, `source.ts`) |
| `components/busqueda/Buscador`      | `components/busqueda/Buscador.ts`                 |
| `components/busqueda/PanelInfo`     | `components/busqueda/PanelInfo.ts`                |
| `components/visor/Reproductor`      | `components/visor/Reproductor.ts` (+ `BarraTiempo`, `Comparar`) |
| `components/visor/VistaAladin`      | `components/visor/VistaAladin.ts`                 |
| `components/visor/Espectro`         | `components/visor/Espectro.ts`                    |
Extras que no tienen equivalente en el repo: `src/lib/` (coordenadas, objetos, render), `src/state/`
(estado y URL), `src/styles/`, `src/config.ts`. El HTML está en `index.html` (ids fijos; no cambiarlos).

## Qué funciona con el contrato de api.md y qué no
- Probado con datos reales el 2026-11-15 (Barnard's Star, detector D2): se ven las 3 épocas y,
  en Comparar > Diferencia, el par cian/rojo del movimiento de la estrella.
- Con el backend, el filtro "λ de referencia / tolerancia" no aplica: cada cuadro es una época
  que ya combina todo el detector. El filtro sigue activo en modo demostración.
- Funciona: buscar por nombre o coordenadas, blink por época y detector, deslizar A/B, diferencia
  B−A y suma, Aladin, URL compartible, espectro (lambda vs flujo).
- La diferencia y la suma se calculan en el navegador con los PNG, o sea con brillo ya escalado
  (no MJy/sr calibrado). `/diff` existe en api.md pero la interfaz no lo usa.
- No disponible con PNG: banderas de calidad, píxeles enmascarados, barras de error y fotometría de
  apertura (api.md no los trae). Esos controles quedan sin efecto en modo API.
- Escala: la interfaz asume 6.15″/píxel (valor verificado con IRSA, en `src/config.ts`). Conviene
  que `/frames` devuelva PNG con ese tamaño (nx = fov·3600/6.15) para que la barra de escala y la
  marca de posición esperada sean correctas.
- `/frames` debe devolver `epoca` con el mismo `id` que `/epocas`.
- Sin movimiento propio en `/resolve`: los 5 objetivos de prueba usan el de `src/lib/objects.ts`.
