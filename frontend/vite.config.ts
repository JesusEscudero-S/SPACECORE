import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  // En Docker sobre Windows, el contenedor no se entera cuando editas un archivo: Vite seguiría
  // entregando la versión vieja. Con DOCKER_POLLING=1 (lo pone docker-compose.yml) Vite revisa
  // los archivos cada 300 ms. Fuera de Docker no se activa y todo funciona como siempre.
  const polling = loadEnv(mode, '.', '').DOCKER_POLLING === '1';
  return {
    server: {
      port: 5173,
      watch: polling ? { usePolling: true, interval: 300 } : undefined,
    },
  };
});
