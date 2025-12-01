# Herramientas de Desarrollo

Esta carpeta contiene archivos y scripts para el entorno de desarrollo con hot-reload.

## Contenido

- `docker-compose.dev.yml` - Configuración Docker Compose para desarrollo
- `start-development.sh` - Script para iniciar el entorno de desarrollo

## Uso

Para iniciar el entorno de desarrollo:

```bash
cd dev-tools
./start-development.sh
```

El entorno de desarrollo incluye:
- **Frontend**: Hot-reload en http://localhost:8080
- **Backend**: Hot-reload con Flask
- **Volúmenes montados**: Los cambios en el código se reflejan automáticamente
- **Puertos expuestos**: 
  - Frontend: 8080
  - Backend: 5000
  - MongoDB: 27017

## Detener el Entorno

Desde la raíz del proyecto:

```bash
./stop.sh dev
```

O detener todos los entornos:

```bash
./stop.sh all
```
