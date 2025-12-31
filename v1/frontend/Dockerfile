# ===========================================
# AppQueue Frontend - Production Dockerfile
# Multi-stage build: Build + Nginx
# ===========================================

# Stage 1: Build Angular app
FROM node:20-alpine AS builder

WORKDIR /app

# Instalar dependencias primero (mejor cache)
COPY package*.json ./
RUN npm ci --legacy-peer-deps

# Copiar codigo fuente
COPY . .

# Build de produccion
RUN npm run build -- --configuration=production

# ===========================================
# Stage 2: Nginx para servir la app
# ===========================================
FROM nginx:alpine

# Zona horaria
ENV TZ=America/Lima
RUN apk add --no-cache tzdata \
    && cp /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

# Eliminar configuracion por defecto de nginx
RUN rm -rf /usr/share/nginx/html/*
RUN rm /etc/nginx/conf.d/default.conf

# Copiar configuracion personalizada de nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar app compilada desde el builder
COPY --from=builder /app/dist/health-system/browser /usr/share/nginx/html

# Exponer puerto 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1

# Comando por defecto
CMD ["nginx", "-g", "daemon off;"]
