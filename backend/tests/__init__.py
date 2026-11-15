# Las pruebas NUNCA usan el Redis de verdad. Varias generan imágenes FALSAS con coordenadas
# reales (por ejemplo, Barnard's Star); si llegaran al Redis que usa la página, ésta podría
# mostrarlas como si fueran de la NASA. Este archivo corre antes que cualquier prueba, así que
# basta con apagar Redis aquí (con Docker, REDIS_URL viene encendida desde docker-compose.yml).
import os

os.environ["REDIS_URL"] = ""
