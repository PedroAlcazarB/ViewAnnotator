from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId
import os
import json
from datetime import datetime
import base64
from PIL import Image
import io
import zipfile

app = Flask(__name__)
CORS(app)

# Configuración de MongoDB
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://mongo:27017/')
DB_NAME = 'visilab_annotator'

def get_db():
    """Obtener conexión a la base de datos MongoDB"""
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]

def serialize_doc(doc):
    """Convertir ObjectId a string para JSON serialization"""
    if doc and '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc

# Carpeta donde se guardarán las imágenes (backup)
IMAGE_FOLDER = os.path.join(os.getcwd(), 'images')
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# ==================== ENDPOINTS PARA IMÁGENES ====================

@app.route('/api/images', methods=['POST'])
def upload_image():
    """Subir una nueva imagen y guardarla en MongoDB"""
    if 'image' not in request.files:
        return jsonify({'error': 'No se encontró ninguna imagen'}), 400

    image = request.files['image']
    if image.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400

    try:
        db = get_db()
        dataset_id = request.form.get('dataset_id')
        
        # Si hay dataset_id, obtener el nombre del dataset para crear la ruta correcta
        dataset_folder_path = IMAGE_FOLDER  # Por defecto en la carpeta principal
        if dataset_id:
            dataset = db.datasets.find_one({'_id': ObjectId(dataset_id)})
            if dataset:
                dataset_folder_path = os.path.join(IMAGE_FOLDER, dataset['name'])
                os.makedirs(dataset_folder_path, exist_ok=True)
        
        # Leer la imagen como bytes
        image_data = image.read()
        
        # Guardar también una copia física (backup) en la carpeta correcta
        save_path = os.path.join(dataset_folder_path, image.filename)
        with open(save_path, 'wb') as f:
            f.write(image_data)
        
        # Obtener información de la imagen
        pil_image = Image.open(io.BytesIO(image_data))
        width, height = pil_image.size
        
        # Convertir imagen a base64 para MongoDB
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Guardar ruta relativa para facilitar la organización
        relative_path = os.path.relpath(save_path, IMAGE_FOLDER) if dataset_id else image.filename
        
        # Crear documento de imagen
        image_doc = {
            'filename': image.filename,
            'original_name': image.filename,
            'file_path': relative_path,  # Ruta relativa desde IMAGE_FOLDER
            'data': image_base64,
            'content_type': image.content_type,
            'size': len(image_data),
            'width': width,
            'height': height,
            'upload_date': datetime.utcnow(),
            'dataset_id': dataset_id,
            'project_id': request.form.get('project_id', 'default')  # Mantener para compatibilidad
        }
        
        # Insertar en MongoDB
        result = db.images.insert_one(image_doc)
        image_doc['_id'] = str(result.inserted_id)
        
        return jsonify({
            'message': 'Imagen subida correctamente',
            'image': serialize_doc(image_doc)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al subir imagen: {str(e)}'}), 500

@app.route('/api/images', methods=['GET'])
def get_images():
    """Obtener lista de todas las imágenes"""
    try:
        db = get_db()
        dataset_id = request.args.get('dataset_id')
        project_id = request.args.get('project_id', 'default')
        
        # Construir filtro
        query_filter = {}
        if dataset_id:
            query_filter['dataset_id'] = dataset_id
        else:
            query_filter['project_id'] = project_id
        
        images = list(db.images.find(
            query_filter,
            {'data': 0}  # Excluir datos binarios para listar
        ))
        
        return jsonify({
            'images': [serialize_doc(img) for img in images]
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener imágenes: {str(e)}'}), 500

@app.route('/api/images/<image_id>', methods=['GET'])
def get_image(image_id):
    """Obtener una imagen específica"""
    try:
        db = get_db()
        
        if not ObjectId.is_valid(image_id):
            return jsonify({'error': 'ID de imagen inválido'}), 400
            
        image_doc = db.images.find_one({'_id': ObjectId(image_id)})
        
        if not image_doc:
            return jsonify({'error': 'Imagen no encontrada'}), 404
            
        return jsonify({
            'image': serialize_doc(image_doc)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener imagen: {str(e)}'}), 500

@app.route('/api/images/<image_id>/data', methods=['GET'])
def get_image_data(image_id):
    """Servir los datos binarios de una imagen"""
    try:
        db = get_db()
        
        if not ObjectId.is_valid(image_id):
            return jsonify({'error': 'ID de imagen inválido'}), 400
            
        image_doc = db.images.find_one({'_id': ObjectId(image_id)})
        
        if not image_doc:
            return jsonify({'error': 'Imagen no encontrada'}), 404
            
        # Decodificar base64 y servir imagen
        image_data = base64.b64decode(image_doc['data'])
        
        from flask import Response
        return Response(
            image_data,
            mimetype=image_doc.get('content_type', 'image/jpeg'),
            headers={'Content-Disposition': f'inline; filename={image_doc["filename"]}'}
        )
        
    except Exception as e:
        return jsonify({'error': f'Error al servir imagen: {str(e)}'}), 500

@app.route('/api/images/<image_id>', methods=['DELETE'])
def delete_image(image_id):
    """Eliminar una imagen y sus anotaciones"""
    try:
        db = get_db()
        
        if not ObjectId.is_valid(image_id):
            return jsonify({'error': 'ID de imagen inválido'}), 400
        
        # Obtener información de la imagen antes de eliminarla
        image_doc = db.images.find_one({'_id': ObjectId(image_id)})
        if not image_doc:
            return jsonify({'error': 'Imagen no encontrada'}), 404
            
        # Eliminar imagen de MongoDB
        result = db.images.delete_one({'_id': ObjectId(image_id)})
        
        if result.deleted_count == 0:
            return jsonify({'error': 'Error al eliminar imagen de la base de datos'}), 500
        
        # Eliminar archivo físico si existe
        file_path = None
        if 'file_path' in image_doc:
            file_path = os.path.join(IMAGE_FOLDER, image_doc['file_path'])
        elif 'filename' in image_doc:
            # Fallback para imágenes antigas sin file_path
            file_path = os.path.join(IMAGE_FOLDER, image_doc['filename'])
            
        if file_path:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Archivo físico eliminado: {file_path}")
                else:
                    print(f"Archivo físico no encontrado: {file_path}")
            except Exception as file_error:
                print(f"Error al eliminar archivo físico {file_path}: {str(file_error)}")
                # No fallar la operación completa si solo falla la eliminación del archivo
            
        # Eliminar anotaciones asociadas
        annotations_result = db.annotations.delete_many({'image_id': image_id})
        print(f"Eliminadas {annotations_result.deleted_count} anotaciones asociadas")
        
        return jsonify({
            'message': 'Imagen eliminada correctamente',
            'deleted_annotations': annotations_result.deleted_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al eliminar imagen: {str(e)}'}), 500

# Ruta para servir imágenes desde la carpeta "images" (backward compatibility)
@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

# ==================== ENDPOINTS PARA ANOTACIONES ====================

@app.route('/api/annotations', methods=['POST'])
def create_annotation():
    """Crear una nueva anotación"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No se proporcionaron datos'}), 400
            
        if 'image_id' not in data:
            return jsonify({'error': 'image_id es requerido'}), 400
        
        db = get_db()
        
        # Crear documento de anotación
        annotation_doc = {
            'image_id': data['image_id'],
            'type': data.get('type', 'bbox'),
            'category': data.get('category', 'default'),
            'category_id': data.get('category_id'),
            'bbox': data.get('bbox'),
            'points': data.get('points'),
            'stroke': data.get('stroke', '#00ff00'),
            'strokeWidth': data.get('strokeWidth', 2),
            'fill': data.get('fill', 'rgba(0,255,0,0.2)'),
            'closed': data.get('closed', False),
            'center': data.get('center'),
            'created_date': datetime.utcnow(),
            'modified_date': datetime.utcnow()
        }
        
        # Insertar en MongoDB
        result = db.annotations.insert_one(annotation_doc)
        annotation_doc['_id'] = str(result.inserted_id)
        
        return jsonify({
            'message': 'Anotación creada correctamente',
            'annotation': serialize_doc(annotation_doc)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al crear anotación: {str(e)}'}), 500

@app.route('/api/annotations', methods=['GET'])
def get_annotations():
    """Obtener anotaciones de una imagen específica"""
    try:
        image_id = request.args.get('image_id')
        
        if not image_id:
            return jsonify({'error': 'image_id es requerido'}), 400
        
        db = get_db()
        annotations = list(db.annotations.find({'image_id': image_id}))
        
        return jsonify({
            'annotations': [serialize_doc(ann) for ann in annotations]
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener anotaciones: {str(e)}'}), 500

@app.route('/api/annotations/<annotation_id>', methods=['PUT'])
def update_annotation(annotation_id):
    """Actualizar una anotación existente"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No se proporcionaron datos'}), 400
            
        if not ObjectId.is_valid(annotation_id):
            return jsonify({'error': 'ID de anotación inválido'}), 400
        
        db = get_db()
        
        # Actualizar campos modificables
        update_data = {
            'modified_date': datetime.utcnow()
        }
        
        # Campos que se pueden actualizar
        updateable_fields = ['type', 'category', 'category_id', 'bbox', 'points', 
                           'stroke', 'strokeWidth', 'fill', 'closed', 'center']
        
        for field in updateable_fields:
            if field in data:
                update_data[field] = data[field]
        
        result = db.annotations.update_one(
            {'_id': ObjectId(annotation_id)},
            {'$set': update_data}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'Anotación no encontrada'}), 404
            
        # Obtener anotación actualizada
        updated_annotation = db.annotations.find_one({'_id': ObjectId(annotation_id)})
        
        return jsonify({
            'message': 'Anotación actualizada correctamente',
            'annotation': serialize_doc(updated_annotation)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al actualizar anotación: {str(e)}'}), 500

@app.route('/api/annotations/<annotation_id>', methods=['DELETE'])
def delete_annotation(annotation_id):
    """Eliminar una anotación"""
    try:
        if not ObjectId.is_valid(annotation_id):
            return jsonify({'error': 'ID de anotación inválido'}), 400
        
        db = get_db()
        result = db.annotations.delete_one({'_id': ObjectId(annotation_id)})
        
        if result.deleted_count == 0:
            return jsonify({'error': 'Anotación no encontrada'}), 404
            
        return jsonify({'message': 'Anotación eliminada correctamente'})
        
    except Exception as e:
        return jsonify({'error': f'Error al eliminar anotación: {str(e)}'}), 500

@app.route('/api/annotations/bulk', methods=['DELETE'])
def delete_annotations_bulk():
    """Eliminar múltiples anotaciones por image_id"""
    try:
        data = request.get_json()
        
        if not data or 'image_id' not in data:
            return jsonify({'error': 'image_id es requerido'}), 400
        
        db = get_db()
        result = db.annotations.delete_many({'image_id': data['image_id']})
        
        return jsonify({
            'message': f'{result.deleted_count} anotaciones eliminadas correctamente',
            'deleted_count': result.deleted_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al eliminar anotaciones: {str(e)}'}), 500

# ==================== ENDPOINTS PARA CATEGORÍAS ====================

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Obtener todas las categorías"""
    try:
        db = get_db()
        project_id = request.args.get('project_id', 'default')
        
        categories = list(db.categories.find({'project_id': project_id}))
        
        return jsonify({
            'categories': [serialize_doc(cat) for cat in categories]
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener categorías: {str(e)}'}), 500

@app.route('/api/categories', methods=['POST'])
def create_category():
    """Crear una nueva categoría"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({'error': 'name es requerido'}), 400
        
        db = get_db()
        
        # Crear documento de categoría
        category_doc = {
            'name': data['name'],
            'color': data.get('color', '#00ff00'),
            'project_id': data.get('project_id', 'default'),
            'created_date': datetime.utcnow()
        }
        
        # Insertar en MongoDB
        result = db.categories.insert_one(category_doc)
        category_doc['_id'] = str(result.inserted_id)
        
        return jsonify({
            'message': 'Categoría creada correctamente',
            'category': serialize_doc(category_doc)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al crear categoría: {str(e)}'}), 500

# ==================== ENDPOINTS PARA DATASETS ====================

@app.route('/api/datasets', methods=['GET'])
def get_datasets():
    """Obtener lista de todos los datasets"""
    try:
        db = get_db()
        datasets = list(db.datasets.find({}, {'images': 0}))  # Excluir lista de imágenes para listar
        
        # Contar imágenes para cada dataset
        for dataset in datasets:
            dataset_id = str(dataset['_id'])
            image_count = db.images.count_documents({'dataset_id': dataset_id})
            dataset['image_count'] = image_count
        
        return jsonify({
            'datasets': [serialize_doc(ds) for ds in datasets]
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener datasets: {str(e)}'}), 500

@app.route('/api/datasets', methods=['POST'])
def create_dataset():
    """Crear un nuevo dataset"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({'error': 'name es requerido'}), 400
        
        db = get_db()
        
        # Verificar que no existe un dataset con el mismo nombre
        existing = db.datasets.find_one({'name': data['name']})
        if existing:
            return jsonify({'error': 'Ya existe un dataset con ese nombre'}), 400
        
        # Crear documento de dataset
        dataset_doc = {
            'name': data['name'],
            'description': data.get('description', ''),
            'folder_path': f"/images/{data['name']}",
            'categories': data.get('categories', []),
            'created_date': datetime.utcnow(),
            'created_by': data.get('created_by', 'usuario'),
            'image_count': 0
        }
        
        # Insertar en MongoDB
        result = db.datasets.insert_one(dataset_doc)
        dataset_doc['_id'] = str(result.inserted_id)
        
        # Crear directorio físico
        dataset_folder = os.path.join(IMAGE_FOLDER, data['name'])
        os.makedirs(dataset_folder, exist_ok=True)
        
        return jsonify({
            'message': 'Dataset creado correctamente',
            'dataset': serialize_doc(dataset_doc)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al crear dataset: {str(e)}'}), 500

@app.route('/api/datasets/<dataset_id>', methods=['GET'])
def get_dataset(dataset_id):
    """Obtener un dataset específico con sus imágenes"""
    try:
        db = get_db()
        
        if not ObjectId.is_valid(dataset_id):
            return jsonify({'error': 'ID de dataset inválido'}), 400
            
        dataset = db.datasets.find_one({'_id': ObjectId(dataset_id)})
        
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado'}), 404
        
        # Obtener imágenes del dataset
        images = list(db.images.find(
            {'dataset_id': dataset_id},
            {'data': 0}  # Excluir datos binarios para listar
        ))
        
        dataset['images'] = [serialize_doc(img) for img in images]
        dataset['image_count'] = len(images)
        
        return jsonify({
            'dataset': serialize_doc(dataset)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener dataset: {str(e)}'}), 500

@app.route('/api/datasets/<dataset_id>', methods=['DELETE'])
def delete_dataset(dataset_id):
    """Eliminar un dataset y todas sus imágenes/anotaciones"""
    try:
        db = get_db()
        
        if not ObjectId.is_valid(dataset_id):
            return jsonify({'error': 'ID de dataset inválido'}), 400
        
        # Verificar que existe
        dataset = db.datasets.find_one({'_id': ObjectId(dataset_id)})
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado'}), 404
        
        dataset_name = dataset.get('name')
        deleted_files = 0
        deleted_folder = False
        
        # Obtener todas las imágenes del dataset para eliminar anotaciones
        images = list(db.images.find({'dataset_id': dataset_id}))
        
        # Eliminar anotaciones de todas las imágenes
        for img in images:
            db.annotations.delete_many({'image_id': str(img['_id'])})
        
        # Eliminar todas las imágenes del dataset de la base de datos
        images_result = db.images.delete_many({'dataset_id': dataset_id})
        
        # Eliminar carpeta física completa del dataset
        if dataset_name:
            dataset_folder = os.path.join(IMAGE_FOLDER, dataset_name)
            try:
                if os.path.exists(dataset_folder):
                    import shutil
                    shutil.rmtree(dataset_folder)
                    deleted_folder = True
                    print(f"Carpeta del dataset eliminada: {dataset_folder}")
                else:
                    print(f"Carpeta del dataset no encontrada: {dataset_folder}")
            except Exception as folder_error:
                print(f"Error al eliminar carpeta del dataset {dataset_folder}: {str(folder_error)}")
                # No fallar la operación completa si solo falla la eliminación de la carpeta
        
        # Eliminar el dataset de la base de datos
        dataset_result = db.datasets.delete_one({'_id': ObjectId(dataset_id)})
        
        return jsonify({
            'message': 'Dataset eliminado correctamente',
            'deleted_images': images_result.deleted_count,
            'deleted_folder': deleted_folder,
            'dataset_name': dataset_name
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al eliminar dataset: {str(e)}'}), 500

@app.route('/api/datasets/import', methods=['POST'])
def import_dataset_zip():
    """Importar un dataset desde un archivo ZIP"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se encontró ningún archivo'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        
        if not file.filename.lower().endswith('.zip'):
            return jsonify({'error': 'Solo se permiten archivos ZIP'}), 400

        dataset_name = request.form.get('name') or file.filename.replace('.zip', '')
        
        db = get_db()
        
        # Verificar que no existe un dataset con el mismo nombre
        existing = db.datasets.find_one({'name': dataset_name})
        if existing:
            return jsonify({'error': 'Ya existe un dataset con ese nombre'}), 400
        
        # Crear dataset
        dataset_doc = {
            'name': dataset_name,
            'description': f'Importado desde {file.filename}',
            'folder_path': f"/datasets/{dataset_name}",
            'categories': [],
            'created_date': datetime.utcnow(),
            'created_by': 'usuario',
            'image_count': 0
        }
        
        result = db.datasets.insert_one(dataset_doc)
        dataset_id = str(result.inserted_id)
        
        # Crear directorio
        dataset_folder = os.path.join(IMAGE_FOLDER, dataset_name)
        os.makedirs(dataset_folder, exist_ok=True)
        
        # Descomprimir ZIP
        import zipfile
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, file.filename)
            file.save(zip_path)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(dataset_folder)
        
        # Procesar imágenes encontradas
        image_count = 0
        supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        
        for root, dirs, files in os.walk(dataset_folder):
            for filename in files:
                if any(filename.lower().endswith(ext) for ext in supported_formats):
                    file_path = os.path.join(root, filename)
                    
                    try:
                        # Leer y procesar imagen
                        with open(file_path, 'rb') as img_file:
                            image_data = img_file.read()
                        
                        pil_image = Image.open(io.BytesIO(image_data))
                        width, height = pil_image.size
                        
                        # Convertir a base64 para MongoDB
                        image_base64 = base64.b64encode(image_data).decode('utf-8')
                        
                        # Calcular ruta relativa desde IMAGE_FOLDER
                        relative_path = os.path.relpath(file_path, IMAGE_FOLDER)
                        
                        # Crear documento de imagen
                        image_doc = {
                            'filename': filename,
                            'original_name': filename,
                            'file_path': relative_path,  # Ruta relativa desde IMAGE_FOLDER
                            'data': image_base64,
                            'content_type': f'image/{filename.split(".")[-1].lower()}',
                            'size': len(image_data),
                            'width': width,
                            'height': height,
                            'upload_date': datetime.utcnow(),
                            'dataset_id': dataset_id
                        }
                        
                        db.images.insert_one(image_doc)
                        image_count += 1
                        
                    except Exception as e:
                        print(f"Error procesando imagen {filename}: {e}")
                        continue
        
        # Actualizar contador de imágenes
        db.datasets.update_one(
            {'_id': ObjectId(dataset_id)},
            {'$set': {'image_count': image_count}}
        )
        
        return jsonify({
            'message': f'Dataset importado correctamente con {image_count} imágenes',
            'dataset_id': dataset_id,
            'image_count': image_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al importar dataset: {str(e)}'}), 500

@app.route('/api/datasets/import-images', methods=['POST'])
def import_images_to_dataset():
    """Importar imágenes desde un archivo ZIP a un dataset existente"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se encontró ningún archivo'}), 400

        file = request.files['file']
        dataset_id = request.form.get('dataset_id')
        
        if file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        
        if not file.filename.lower().endswith('.zip'):
            return jsonify({'error': 'Solo se permiten archivos ZIP'}), 400
            
        if not dataset_id:
            return jsonify({'error': 'Se requiere dataset_id'}), 400

        db = get_db()
        
        # Verificar que el dataset existe
        dataset = db.datasets.find_one({'_id': ObjectId(dataset_id)})
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado'}), 404
        
        dataset_name = dataset['name']
        dataset_folder = os.path.join(IMAGE_FOLDER, dataset_name)
        os.makedirs(dataset_folder, exist_ok=True)
        
        # Guardar y extraer ZIP
        zip_path = os.path.join(dataset_folder, file.filename)
        file.save(zip_path)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dataset_folder)
        
        # Eliminar el archivo ZIP después de extraer
        os.remove(zip_path)
        
        # Procesar imágenes encontradas
        image_count = 0
        processed_images = []
        supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        
        for root, dirs, files in os.walk(dataset_folder):
            for filename in files:
                if any(filename.lower().endswith(ext) for ext in supported_formats):
                    file_path = os.path.join(root, filename)
                    
                    try:
                        # Leer y procesar imagen
                        with open(file_path, 'rb') as img_file:
                            image_data = img_file.read()
                        
                        pil_image = Image.open(io.BytesIO(image_data))
                        width, height = pil_image.size
                        
                        # Convertir a base64 para MongoDB
                        image_base64 = base64.b64encode(image_data).decode('utf-8')
                        
                        # Calcular ruta relativa desde IMAGE_FOLDER
                        relative_path = os.path.relpath(file_path, IMAGE_FOLDER)
                        
                        # Crear documento de imagen
                        image_doc = {
                            'filename': filename,
                            'original_name': filename,
                            'file_path': relative_path,
                            'data': image_base64,
                            'content_type': f'image/{filename.split(".")[-1].lower()}',
                            'size': len(image_data),
                            'width': width,
                            'height': height,
                            'upload_date': datetime.utcnow(),
                            'dataset_id': dataset_id
                        }
                        
                        result = db.images.insert_one(image_doc)
                        image_doc['_id'] = str(result.inserted_id)
                        processed_images.append(serialize_doc(image_doc))
                        image_count += 1
                        
                    except Exception as e:
                        print(f"Error procesando imagen {filename}: {e}")
                        continue
        
        # Actualizar contador de imágenes del dataset
        current_count = db.images.count_documents({'dataset_id': dataset_id})
        db.datasets.update_one(
            {'_id': ObjectId(dataset_id)},
            {'$set': {'image_count': current_count}}
        )
        
        return jsonify({
            'message': f'Se procesaron {image_count} imágenes desde el ZIP',
            'image_count': image_count,
            'images': processed_images
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al importar imágenes: {str(e)}'}), 500

# ==================== HEALTH CHECK ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar el estado de la aplicación y la conexión a MongoDB"""
    try:
        db = get_db()
        # Intenta hacer una operación simple para verificar la conexión
        client = MongoClient(MONGO_URI)
        client.admin.command('ping')
        return jsonify({
            'status': 'healthy',
            'mongodb': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'mongodb': 'disconnected',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
