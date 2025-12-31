# AppQueue - Guia de Despliegue en Produccion

## Configuracion de Dominios y Puertos

| Servicio | Dominio | Puerto |
|----------|---------|--------|
| Frontend | https://munoz.qxpert.ingenius.online | 6239 |
| Backend  | https://munoz.qxpertserver.ingenius.online | 6240 |
| Redis    | (interno) | - |

## Requisitos Previos

### En el Servidor
- Docker Engine 24.0+
- Docker Compose 2.20+
- Git
- 4GB RAM minimo
- Reverse proxy configurado (Nginx/Traefik) para SSL

### Base de Datos
- SQL Server 2019+
- Base de datos `AppQueueMunoz` creada
- Puerto 1433 accesible desde el contenedor

## Estructura de Archivos

```
AppQueue/
├── docker-compose.prod.yml    # Orquestacion de contenedores
├── .env                       # Variables de entorno (crear desde .env.production)
├── .env.production            # Plantilla de configuracion
├── DEPLOY.md                  # Esta guia
└── v1/
    ├── backend/
    │   ├── Dockerfile         # Imagen de produccion
    │   ├── Dockerfile.dev     # Imagen de desarrollo
    │   └── ...
    └── frontend/
        ├── Dockerfile         # Imagen de produccion
        ├── nginx.conf         # Configuracion de Nginx
        └── ...
```

## Pasos de Despliegue

### 1. Clonar el Repositorio

```bash
git clone <url-del-repositorio> AppQueue
cd AppQueue
```

### 2. Configurar Variables de Entorno

```bash
# Copiar plantilla
cp .env.production .env

# Editar con tus valores
nano .env
```

**Configurar en `.env`:**

```env
# Base de datos SQL Server
DATABASE_URL=mssql+pyodbc://usuario:password@host.docker.internal/AppQueueMunoz?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes

# Clave secreta (generar nueva)
SECRET_KEY=tu-clave-secreta-generada-con-openssl

# CORS
ALLOWED_ORIGINS=https://munoz.qxpert.ingenius.online
```

### 3. Construir las Imagenes

```bash
# Construir imagenes de produccion
docker-compose -f docker-compose.prod.yml build

# Si hay problemas de cache:
docker-compose -f docker-compose.prod.yml build --no-cache
```

### 4. Iniciar los Servicios

```bash
# Iniciar en background
docker-compose -f docker-compose.prod.yml up -d

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 5. Verificar el Despliegue

```bash
# Estado de los contenedores
docker-compose -f docker-compose.prod.yml ps

# Health checks
curl http://localhost:6239/health   # Frontend
curl http://localhost:6240/health   # Backend
```

## Configuracion del Reverse Proxy

Tu reverse proxy debe redirigir:

```
munoz.qxpert.ingenius.online (443) -> localhost:6239
munoz.qxpertserver.ingenius.online (443) -> localhost:6240
```

### Ejemplo Nginx (en el host)

```nginx
# Frontend
server {
    listen 443 ssl http2;
    server_name munoz.qxpert.ingenius.online;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:6239;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Backend
server {
    listen 443 ssl http2;
    server_name munoz.qxpertserver.ingenius.online;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:6240;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://127.0.0.1:6240;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

## Comandos Utiles

### Reiniciar Servicios

```bash
docker-compose -f docker-compose.prod.yml restart
docker-compose -f docker-compose.prod.yml restart backend
docker-compose -f docker-compose.prod.yml restart frontend
```

### Actualizar la Aplicacion

```bash
git pull origin main
docker-compose -f docker-compose.prod.yml up -d --build
```

### Ver Logs

```bash
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend
docker-compose -f docker-compose.prod.yml logs --tail=100
```

### Detener Servicios

```bash
docker-compose -f docker-compose.prod.yml down
```

## Troubleshooting

### Error: ODBC Driver not found

El Dockerfile usa la configuracion correcta para Debian 12 bookworm con el nuevo sistema de keyring de Microsoft. Si hay problemas:

```bash
# Entrar al contenedor
docker exec -it appqueue-backend bash

# Verificar driver instalado
odbcinst -q -d
# Debe mostrar: [ODBC Driver 18 for SQL Server]

# Probar conexion
python -c "import pyodbc; print(pyodbc.drivers())"
```

### Error: Connection refused a SQL Server

1. Verificar que SQL Server acepta conexiones remotas
2. Verificar firewall (puerto 1433)
3. Si SQL Server esta en el mismo host, usar `host.docker.internal` en DATABASE_URL

### Error: CORS

Verificar que `ALLOWED_ORIGINS` en `.env` incluye exactamente el dominio del frontend:
```
ALLOWED_ORIGINS=https://munoz.qxpert.ingenius.online
```

### Frontend no carga

```bash
# Ver logs de nginx
docker exec -it appqueue-frontend cat /var/log/nginx/error.log

# Verificar build de Angular
docker exec -it appqueue-frontend ls -la /usr/share/nginx/html
```

## Puertos Internos vs Externos

| Contenedor | Puerto Interno | Puerto Host |
|------------|---------------|-------------|
| frontend   | 80            | 6239        |
| backend    | 8000          | 6240        |
| redis      | 6379          | (no expuesto) |

## Contacto

Para soporte tecnico, contactar a Ingenius.
