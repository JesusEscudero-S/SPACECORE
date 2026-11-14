// Cliente de la API: aquí irán las funciones resolve, getEpocas, getFrames, getDiff y
// getSpectrum. Se implementa en la tarea T42 (rol #1). El contrato está en docs/api.md.

// Dirección del backend. Se configura en el archivo frontend/.env (ver .env.example).
export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'
