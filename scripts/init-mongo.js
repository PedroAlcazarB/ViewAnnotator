// Script de inicialización para MongoDB
// Este script se ejecuta automáticamente cuando se crea la base de datos

// Crear base de datos y colecciones
db = db.getSiblingDB('viewannotator');

// Crear índices para mejorar el rendimiento
db.images.createIndex({ "dataset_id": 1 });
db.images.createIndex({ "filename": 1 });
db.images.createIndex({ "upload_date": -1 });

db.annotations.createIndex({ "image_id": 1 });
db.annotations.createIndex({ "category_id": 1 });
db.annotations.createIndex({ "dataset_id": 1 });
db.annotations.createIndex({ "type": 1 });
db.annotations.createIndex({ "created_date": -1 });

db.categories.createIndex({ "dataset_id": 1 });
db.categories.createIndex({ "name": 1, "dataset_id": 1 }, { unique: true });

// Crear índice para datasets
// Índice único compuesto para permitir nombres repetidos por usuario
db.datasets.createIndex({ "name": 1, "user_id": 1 }, { unique: true });
db.datasets.createIndex({ "created_at": -1 });

print('Base de datos viewannotator inicializada correctamente');
print('Colecciones creadas: images, annotations, categories, datasets');
print('Índices creados para mejorar el rendimiento');