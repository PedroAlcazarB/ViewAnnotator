// Script de inicialización para MongoDB
// Este script se ejecuta automáticamente cuando se crea la base de datos

// Crear base de datos y colecciones
db = db.getSiblingDB('visilab_annotator');

// Crear índices para mejorar el rendimiento
db.images.createIndex({ "project_id": 1 });
db.images.createIndex({ "filename": 1 });
db.images.createIndex({ "upload_date": -1 });

db.annotations.createIndex({ "image_id": 1 });
db.annotations.createIndex({ "category": 1 });
db.annotations.createIndex({ "type": 1 });
db.annotations.createIndex({ "created_date": -1 });

db.categories.createIndex({ "project_id": 1 });
db.categories.createIndex({ "name": 1, "project_id": 1 }, { unique: true });

// Insertar categorías por defecto
db.categories.insertMany([
    {
        name: "persona",
        color: "#ff0000",
        project_id: "default",
        created_date: new Date()
    },
    {
        name: "vehiculo",
        color: "#00ff00", 
        project_id: "default",
        created_date: new Date()
    },
    {
        name: "objeto",
        color: "#0000ff",
        project_id: "default", 
        created_date: new Date()
    }
]);

print('Base de datos visilab_annotator inicializada correctamente');
print('Colecciones creadas: images, annotations, categories');
print('Índices creados para mejorar el rendimiento');
print('Categorías por defecto insertadas');