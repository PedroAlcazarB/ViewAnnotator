# ViewAnnotator

Una aplicación web moderna y completa para anotación de imágenes y videos, con soporte para múltiples formatos de exportación y herramientas de inteligencia artificial integradas.

![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)
![Python](https://img.shields.io/badge/python-3.10-blue.svg)
![Vue](https://img.shields.io/badge/vue-3.x-green.svg)

## Características

- **Anotación de Imágenes**: Interfaz intuitiva para crear bounding boxes con precisión
- **Soporte para Videos**: Extracción automática de frames con configuración de FPS
- **Múltiples Formatos**: Importación y exportación en COCO, YOLO y Pascal VOC
- **Gestión de Datasets**: Organización estructurada de proyectos de anotación
- **Gestión de Categorías**: Administración de categorías con colores personalizados
- **Herramientas de IA**: Integración con modelos YOLO para anotación automática
- **Sistema de Autenticación**: Control de acceso mediante usuarios y sesiones seguras
- **Arquitectura Dockerizada**: Despliegue simplificado mediante Docker Compose
- **Base de Datos MongoDB**: Almacenamiento robusto y escalable

## Prerequisitos

Antes de comenzar, asegúrate de tener instalado:

- **Docker** (20.10+)
- **Docker Compose** (2.0+)
- **Git**

### Permisos de Docker

Si al ejecutar los scripts obtienes un error de permisos de Docker, tienes dos opciones:

**Opción 1: Añadir tu usuario al grupo docker (recomendado para uso frecuente)**
```bash
sudo usermod -aG docker $USER
newgrp docker  # O reinicia sesión para aplicar cambios
```

**Opción 2: Ejecutar con sudo (para uso puntual)**
```bash
sudo ./start-production.sh
```

> **Nota**: Si añades tu usuario al grupo docker, no necesitarás usar `sudo` para los comandos de Docker. Sin embargo, esto otorga privilegios equivalentes a root para Docker. Elige la opción que mejor se adapte a tus necesidades de seguridad y frecuencia de uso.

## Instalación

Sigue estos pasos para clonar el repositorio y configurar el entorno:

```bash
# Clona el repositorio
git clone https://github.com/PedroAlcazarB/ViewAnnotator.git

# Accede a la raíz del proyecto
cd ViewAnnotator

# Verifica que tienes Docker y Docker Compose instalados
docker --version
docker compose version
```

## Inicio Rápido

Una vez clonado el repositorio, inicia la aplicación con el comando:

```bash
./start-production.sh
```

El script de inicio automático realiza las siguientes operaciones:
- Verificación de Docker y Docker Compose en el sistema
- Generación o validación de una `SECRET_KEY` segura en el archivo `.env`
- Creación de directorios persistentes (`backend/datasets`, `mongodb/data`, etc.)
- Construcción y arranque de los servicios mediante `docker-compose.prod.yml`
- Presentación del estado de los contenedores y acceso a logs

Una vez finalizado el proceso, la aplicación estará disponible en **http://localhost:5050**.

> **Nota de Seguridad**: Solo el puerto del frontend (5050 por defecto) está expuesto. El backend y MongoDB se comunican internamente a través de la red Docker para mayor seguridad.

> **Configuración de Puerto**: Puedes cambiar el puerto de acceso editando la variable `FRONTEND_PORT` en el archivo `.env`.

## Detener la Aplicación

Para detener todos los servicios:

```bash
./stop.sh
```

## Estructura del Proyecto

```
ViewAnnotator/
├── backend/                    # Backend Flask
│   ├── app.py                 # Aplicación principal
│   ├── requirements.txt       # Dependencias Python
│   ├── Dockerfile            # Imagen Docker del backend
│   ├── datasets/             # Imágenes y datasets
│   └── ai_models/            # Modelos de IA
├── frontend/                  # Frontend Vue.js
│   ├── src/                  # Código fuente
│   ├── Dockerfile           # Imagen Docker del frontend
│   └── nginx.conf          # Configuración Nginx
├── mongodb/                  # Datos de MongoDB
│   ├── data/                # Datos persistentes
│   └── logs/               # Logs de MongoDB
├── scripts/                 # Scripts de utilidad
├── dev-tools/              # Herramientas de desarrollo
├── .env                    # Variables de entorno (generado)
├── .env.example           # Plantilla de variables
├── docker-compose.prod.yml    # Docker Compose
├── start-production.sh        # Script de inicio
└── stop.sh                    # Script para detener
```

## API Endpoints

### Autenticación
- `POST /api/auth/register` - Registro de usuario
- `POST /api/auth/login` - Inicio de sesión
- `GET /api/auth/verify` - Verificar token

### Imágenes
- `GET /api/images` - Listar imágenes
- `POST /api/images` - Subir imagen
- `GET /api/images/<id>` - Obtener imagen
- `DELETE /api/images/<id>` - Eliminar imagen

### Anotaciones
- `GET /api/annotations` - Listar anotaciones
- `POST /api/annotations` - Crear anotación
- `PUT /api/annotations/<id>` - Actualizar anotación
- `DELETE /api/annotations/<id>` - Eliminar anotación
- `POST /api/annotations/import` - Importar anotaciones
- `GET /api/annotations/export/<dataset_id>` - Exportar anotaciones

### Categorías
- `GET /api/categories` - Listar categorías
- `POST /api/categories` - Crear categoría
- `PUT /api/categories/<id>` - Actualizar categoría
- `DELETE /api/categories/<id>` - Eliminar categoría

### Datasets
- `GET /api/datasets` - Listar datasets
- `POST /api/datasets` - Crear dataset
- `DELETE /api/datasets/<id>` - Eliminar dataset
- `POST /api/datasets/import` - Importar dataset ZIP

### Videos
- `POST /api/videos` - Subir video
- `POST /api/videos/process` - Procesar video con FPS
- `GET /api/videos/<id>/frames` - Obtener frames del video

### IA (Herramientas de Anotación Automática)
- `POST /api/ai/load-model` - Cargar modelo YOLO
- `POST /api/ai/predict` - Realizar predicción
- `GET /api/ai/model-status` - Estado del modelo

## Formatos Soportados

### Importación/Exportación
- **COCO JSON** - Compatible con COCO dataset format
- **YOLO** - Formato YOLO (txt + classes)
- **Pascal VOC** - Formato XML de Pascal VOC

### Imágenes
- JPG, JPEG, PNG, BMP, TIFF, WebP, GIF

### Videos
- MP4, AVI, MOV, MKV, FLV, WMV, WebM, M4V

## Seguridad

- SECRET_KEY generada automáticamente de forma segura
- Tokens JWT para autenticación de usuarios
- Contraseñas hasheadas mediante bcrypt
- Variables de entorno para configuración sensible
- Headers de seguridad implementados en Nginx

## Comandos Útiles

### Ver logs en tiempo real
```bash
docker-compose logs -f
```

### Ver logs de un servicio específico
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Reconstruir servicios tras cambios
```bash
docker-compose build
docker-compose up -d
```

### Ver estado de los contenedores
```bash
docker-compose ps
```

## Desarrollo

> **Nota**: Los archivos de desarrollo se encuentran en la carpeta `dev-tools/`.
Para trabajar en modo desarrollo con hot-reload:

```bash
# Usar el entorno de desarrollo
cd dev-tools
./start-development.sh
```

El entorno de desarrollo estará disponible en **http://localhost:8080** con recarga automática de cambios.

> **Nota**: En desarrollo, el frontend usa el puerto 8080 mientras que en producción usa el puerto configurado en `FRONTEND_PORT` (5050 por defecto).

## Características Técnicas

### Backend
- **Framework**: Flask 3.x
- **Base de Datos**: MongoDB 6.0
- **Autenticación**: JWT (JSON Web Tokens)
- **Inteligencia Artificial**: YOLOv8 (Ultralytics)
- **Procesamiento de Imágenes**: Pillow, OpenCV
- **Procesamiento de Videos**: OpenCV

### Frontend
- **Framework**: Vue 3
- **Gestión de Estado**: Pinia
- **Canvas y Anotación**: Konva.js
- **Herramienta de Construcción**: Vite
- **Servidor Web**: Nginx (producción)
