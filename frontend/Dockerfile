# Imagen del frontend de SPACECORE (TypeScript + Vite, sin React).
# Solo para desarrollo local. Para publicar en Vercel no se usa este archivo.

FROM node:22-alpine

WORKDIR /app

# Primero solo la lista de paquetes: así Docker reutiliza la instalación si el código cambia.
COPY package*.json ./
RUN npm install

# Después el código.
COPY . .

EXPOSE 5173

# --host 0.0.0.0 es obligatorio: si no, Vite solo escucha dentro del contenedor y
# no se puede abrir http://localhost:5173 desde Windows.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
