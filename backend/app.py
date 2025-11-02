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

# ==================== FUNCIONES AUXILIARES PARA PROCESAMIENTO DE IMÁGENES ====================

def find_images_in_directory(directory_path, max_depth=3):
    """
    Buscar recursivamente todas las imágenes en un directorio y sus subcarpetas
    
    Args:
        directory_path: Ruta del directorio a buscar
        max_depth: Profundidad máxima de búsqueda (evita bucles infinitos)
    
    Returns:
        Lista de tuplas (file_path, filename, relative_path)
    """
    supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.gif'}
    found_images = []
    
    for root, dirs, files in os.walk(directory_path):
        # Calcular profundidad actual
        depth = root[len(directory_path):].count(os.sep)
        if depth >= max_depth:
            dirs.clear()  # No buscar más profundo
            continue
            
        for filename in files:
            # Verificar extensión
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in supported_formats:
                file_path = os.path.join(root, filename)
                
                # Validar que es una imagen real
                try:
                    with Image.open(file_path) as img:
                        # Verificar que no es un archivo corrupto
                        img.verify()
                        
                    # Calcular ruta relativa desde el directorio base
                    relative_path = os.path.relpath(file_path, directory_path)
                    found_images.append({
                        'file_path': file_path,
                        'filename': filename,
                        'relative_path': relative_path
                    })
                    
                except Exception as e:
                    print(f"Archivo no válido ignorado: {filename} - {str(e)}")
                    continue
    
    return found_images

def extract_and_find_images(zip_file_path, extract_path):
    """
    Extraer ZIP y buscar imágenes automáticamente gestionando subcarpetas
    
    Args:
        zip_file_path: Ruta del archivo ZIP
        extract_path: Directorio donde extraer las imágenes finales
    
    Returns:
        Lista de imágenes encontradas y procesadas
    """
    import shutil
    
    try:
        # Crear directorio temporal para extracción
        temp_extract_dir = os.path.join(extract_path, 'temp_extract')
        os.makedirs(temp_extract_dir, exist_ok=True)
        
        # Extraer ZIP
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)
        
        # Buscar imágenes recursivamente
        found_images = find_images_in_directory(temp_extract_dir)
        
        print(f"Encontradas {len(found_images)} imágenes en el ZIP")
        
        # Mover imágenes al directorio final y organizar
        final_images = []
        for image_info in found_images:
            file_path = image_info['file_path']
            filename = image_info['filename']
            relative_path = image_info['relative_path']
            
            try:
                # Crear nombre único si hay duplicados
                final_filename = filename
                counter = 1
                while os.path.exists(os.path.join(extract_path, final_filename)):
                    name, ext = os.path.splitext(filename)
                    final_filename = f"{name}_{counter}{ext}"
                    counter += 1
                
                # Mover imagen al directorio final
                final_path = os.path.join(extract_path, final_filename)
                shutil.move(file_path, final_path)
                
                final_images.append({
                    'file_path': final_path,
                    'filename': final_filename,
                    'original_path': relative_path
                })
                
            except Exception as e:
                print(f"Error moviendo imagen {filename}: {str(e)}")
                continue
        
        # Limpiar directorio temporal
        try:
            shutil.rmtree(temp_extract_dir)
        except Exception as e:
            print(f"Error limpiando directorio temporal: {str(e)}")
        
        return final_images
        
    except Exception as e:
        print(f"Error extrayendo ZIP: {str(e)}")
        return []

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
        
        # Agregar contador de anotaciones para cada imagen
        for image in images:
            image_id = str(image['_id'])
            annotation_count = db.annotations.count_documents({'image_id': image_id})
            image['annotation_count'] = annotation_count
        
        return jsonify({
            'images': [serialize_doc(img) for img in images]
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener imágenes: {str(e)}'}), 500@app.route('/api/images/<image_id>', methods=['GET'])
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
        
        # Calcular área si hay bbox
        bbox = data.get('bbox')
        area = 0
        if bbox and len(bbox) >= 4:
            # bbox format: [x, y, width, height]
            area = bbox[2] * bbox[3]
        
        # Crear documento de anotación
        annotation_doc = {
            'image_id': data['image_id'],
            'type': data.get('type', 'bbox'),
            'category': data.get('category', 'default'),
            'category_id': data.get('category_id'),
            'bbox': bbox,
            'area': area,
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
    """Obtener anotaciones de una imagen específica, todas las anotaciones o anotaciones de un dataset"""
    try:
        image_id = request.args.get('image_id')
        dataset_id = request.args.get('dataset_id')
        
        db = get_db()
        
        if image_id:
            # Obtener anotaciones de una imagen específica
            annotations = list(db.annotations.find({'image_id': image_id}))
        elif dataset_id:
            # Obtener todas las anotaciones de un dataset específico
            # Primero obtener todas las imágenes del dataset
            images = list(db.images.find({'dataset_id': dataset_id}))
            image_ids = [str(img['_id']) for img in images]
            
            # Luego obtener anotaciones de esas imágenes
            annotations = list(db.annotations.find({'image_id': {'$in': image_ids}}))
        else:
            # Obtener todas las anotaciones
            annotations = list(db.annotations.find())
        
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
        
        # Recalcular área si se actualiza el bbox
        if 'bbox' in data:
            bbox = data['bbox']
            if bbox and len(bbox) >= 4:
                update_data['area'] = bbox[2] * bbox[3]
            else:
                update_data['area'] = 0
        
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
    """Obtener todas las categorías de un dataset específico o de todos los datasets"""
    try:
        db = get_db()
        dataset_id = request.args.get('dataset_id')
        
        # Si se proporciona dataset_id, filtrar por ese dataset
        # Si no, devolver todas las categorías (vista global)
        if dataset_id:
            categories = list(db.categories.find({'dataset_id': dataset_id}))
        else:
            categories = list(db.categories.find())
        
        # Contar anotaciones por categoría y estandarizar formato
        for category in categories:
            category_id = str(category['_id'])
            # Buscar anotaciones que coincidan con category_id O category
            annotation_count = db.annotations.count_documents({
                '$or': [
                    {'category_id': category_id},
                    {'category': category_id}
                ]
            })
            category['numberAnnotations'] = annotation_count
            category['creator'] = category.get('creator', 'system')
            # Estandarizar ID para consistencia con el frontend
            category['id'] = category_id
        
        return jsonify({
            'categories': [serialize_doc(cat) for cat in categories]
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener categorías: {str(e)}'}), 500

@app.route('/api/categories', methods=['POST'])
def create_category():
    """Crear una nueva categoría asociada a un dataset específico"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({'error': 'name es requerido'}), 400
        
        if 'dataset_id' not in data or not data['dataset_id']:
            return jsonify({'error': 'dataset_id es requerido. Debes especificar a qué dataset pertenece esta categoría.'}), 400
        
        db = get_db()
        
        # Verificar que el dataset existe
        dataset = db.datasets.find_one({'_id': ObjectId(data['dataset_id'])})
        if not dataset:
            return jsonify({'error': 'El dataset especificado no existe'}), 404
        
        # Crear documento de categoría
        category_doc = {
            'name': data['name'],
            'color': data.get('color', '#00ff00'),
            'dataset_id': data['dataset_id'],
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

@app.route('/api/categories/<category_id>', methods=['GET'])
def get_category(category_id):
    """Obtener una categoría por ID"""
    try:
        db = get_db()
        category = db.categories.find_one({'_id': ObjectId(category_id)})
        
        if not category:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        
        return jsonify({
            'category': serialize_doc(category)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener categoría: {str(e)}'}), 500

@app.route('/api/categories/<category_id>', methods=['PUT'])
def update_category(category_id):
    """Actualizar una categoría existente"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400
        
        db = get_db()
        
        # Preparar campos actualizables
        update_fields = {}
        if 'name' in data:
            update_fields['name'] = data['name']
        if 'color' in data:
            update_fields['color'] = data['color']
        
        if not update_fields:
            return jsonify({'error': 'No hay campos para actualizar'}), 400
        
        update_fields['updated_date'] = datetime.utcnow()
        
        # Actualizar en MongoDB
        result = db.categories.update_one(
            {'_id': ObjectId(category_id)},
            {'$set': update_fields}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        
        # Obtener categoría actualizada
        updated_category = db.categories.find_one({'_id': ObjectId(category_id)})
        
        return jsonify({
            'message': 'Categoría actualizada correctamente',
            'category': serialize_doc(updated_category)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al actualizar categoría: {str(e)}'}), 500

@app.route('/api/categories/<category_id>', methods=['DELETE'])
def delete_category(category_id):
    """Eliminar una categoría y opcionalmente sus anotaciones asociadas"""
    try:
        db = get_db()
        dataset_id = request.args.get('dataset_id')  # Parámetro opcional para contexto de dataset
        force = request.args.get('force', 'false').lower() == 'true'  # Forzar eliminación
        
        if dataset_id:
            # Contexto de dataset: solo considerar anotaciones de ese dataset
            # Primero obtener todas las imágenes del dataset
            images = list(db.images.find({'dataset_id': dataset_id}))
            image_ids = [str(img['_id']) for img in images]
            
            # Buscar anotaciones de esta categoría en las imágenes del dataset
            annotations_query = {
                '$and': [
                    {'image_id': {'$in': image_ids}},
                    {'$or': [
                        {'category_id': category_id},
                        {'category': category_id}
                    ]}
                ]
            }
            
            context_message = f"en el dataset"
        else:
            # Contexto global: considerar todas las anotaciones
            annotations_query = {
                '$or': [
                    {'category_id': category_id},
                    {'category': category_id}
                ]
            }
            
            context_message = f"en el sistema"
        
        # Contar anotaciones que serían afectadas
        annotation_count = db.annotations.count_documents(annotations_query)
        
        # Si hay anotaciones y no se fuerza, informar al usuario
        if annotation_count > 0 and not force:
            return jsonify({
                'error': f'La categoría tiene {annotation_count} anotaciones asociadas {context_message}.',
                'annotation_count': annotation_count,
                'requires_force': True
            }), 400
        
        # Si se fuerza o no hay anotaciones, proceder con la eliminación
        if annotation_count > 0:
            # Eliminar anotaciones asociadas primero
            delete_result = db.annotations.delete_many(annotations_query)
            print(f"Eliminadas {delete_result.deleted_count} anotaciones de la categoría {category_id}")
        
        # Eliminar categoría
        result = db.categories.delete_one({'_id': ObjectId(category_id)})
        
        if result.deleted_count == 0:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        
        return jsonify({
            'message': 'Categoría eliminada correctamente',
            'deleted_annotations': annotation_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al eliminar categoría: {str(e)}'}), 500

@app.route('/api/categories/<category_id>/toggle-visibility', methods=['PATCH'])
def toggle_category_visibility(category_id):
    """Toggle visibilidad de una categoría para un dataset específico"""
    try:
        db = get_db()
        dataset_id = request.args.get('dataset_id')
        
        if not dataset_id:
            return jsonify({'error': 'dataset_id es requerido'}), 400
        
        # Buscar o crear registro de visibilidad
        visibility_doc = db.category_visibility.find_one({
            'category_id': category_id,
            'dataset_id': dataset_id
        })
        
        if visibility_doc:
            # Toggle visibilidad existente
            new_hidden = not visibility_doc.get('hidden', False)
            db.category_visibility.update_one(
                {'_id': visibility_doc['_id']},
                {'$set': {'hidden': new_hidden}}
            )
        else:
            # Crear nuevo registro (por defecto visible, así que lo ocultamos)
            new_hidden = True
            db.category_visibility.insert_one({
                'category_id': category_id,
                'dataset_id': dataset_id,
                'hidden': new_hidden
            })
        
        return jsonify({
            'message': 'Visibilidad actualizada',
            'hidden': new_hidden
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al toggle visibilidad: {str(e)}'}), 500

@app.route('/api/categories/visibility/<dataset_id>', methods=['GET'])
def get_categories_visibility(dataset_id):
    """Obtener visibilidad de categorías para un dataset"""
    try:
        db = get_db()
        
        visibility_records = list(db.category_visibility.find({'dataset_id': dataset_id}))
        
        # Convertir a diccionario para fácil acceso
        visibility_map = {}
        for record in visibility_records:
            visibility_map[record['category_id']] = record.get('hidden', False)
        
        return jsonify({
            'visibility': visibility_map
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener visibilidad: {str(e)}'}), 500

@app.route('/api/categories/data', methods=['GET'])
def get_categories_data():
    """Obtener estadísticas de categorías con conteo de anotaciones"""
    try:
        db = get_db()
        dataset_id = request.args.get('dataset_id')
        
        # Si no se proporciona dataset_id, devolver error
        if not dataset_id:
            return jsonify({'error': 'dataset_id es requerido'}), 400
        
        # Obtener todas las categorías del dataset
        categories = list(db.categories.find({'dataset_id': dataset_id}))
        
        # Contar anotaciones por categoría y estandarizar formato
        for category in categories:
            category_id = str(category['_id'])
            # Buscar anotaciones que coincidan con category_id O category
            annotation_count = db.annotations.count_documents({
                '$or': [
                    {'category_id': category_id},
                    {'category': category_id}
                ]
            })
            category['numberAnnotations'] = annotation_count
            category['creator'] = category.get('creator', 'system')
            # Estandarizar ID para consistencia con el frontend
            category['id'] = category_id
        
        return jsonify({
            'categories': [serialize_doc(cat) for cat in categories]
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener datos de categorías: {str(e)}'}), 500

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
        
        # Descomprimir y procesar ZIP
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, file.filename)
            file.save(zip_path)
            
            # Usar la nueva función para extraer y encontrar imágenes
            found_images = extract_and_find_images(zip_path, dataset_folder)
        
        total_images = len(found_images)
        print(f"Total de imágenes encontradas: {total_images}")
        
        # Procesar imágenes por lotes para evitar problemas de memoria y timeout
        batch_size = 50  # Procesar de 50 en 50
        image_count = 0
        processed_images = []
        failed_images = []
        
        for i in range(0, total_images, batch_size):
            batch = found_images[i:i + batch_size]
            batch_number = (i // batch_size) + 1
            total_batches = (total_images + batch_size - 1) // batch_size
            
            print(f"Procesando lote {batch_number}/{total_batches} ({len(batch)} imágenes)")
            
            # Preparar documentos del lote
            batch_docs = []
            
            for image_info in batch:
                file_path = image_info['file_path']
                filename = image_info['filename']
                original_path = image_info['original_path']
                
                try:
                    # Leer y procesar imagen
                    with open(file_path, 'rb') as img_file:
                        image_data = img_file.read()
                    
                    # Verificar tamaño de imagen (limitar a 10MB)
                    if len(image_data) > 10 * 1024 * 1024:  # 10MB
                        print(f"Imagen {filename} demasiado grande ({len(image_data)} bytes), omitiendo")
                        failed_images.append({'filename': filename, 'reason': 'Tamaño excesivo'})
                        continue
                    
                    # Reabrir para obtener dimensiones (verify() cierra la imagen)
                    pil_image = Image.open(file_path)
                    width, height = pil_image.size
                    pil_image.close()
                    
                    # Convertir a base64 para MongoDB
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                    
                    # Calcular ruta relativa desde IMAGE_FOLDER
                    relative_path = os.path.relpath(file_path, IMAGE_FOLDER)
                    
                    # Crear documento de imagen con información adicional
                    image_doc = {
                        'filename': filename,
                        'original_name': filename,
                        'file_path': relative_path,
                        'original_zip_path': original_path,  # Ruta original dentro del ZIP
                        'data': image_base64,
                        'content_type': f'image/{filename.split(".")[-1].lower()}',
                        'size': len(image_data),
                        'width': width,
                        'height': height,
                        'upload_date': datetime.utcnow(),
                        'dataset_id': dataset_id
                    }
                    
                    batch_docs.append(image_doc)
                    
                except Exception as e:
                    print(f"Error procesando imagen {filename}: {e}")
                    failed_images.append({'filename': filename, 'reason': str(e)})
                    continue
            
            # Insertar lote completo en MongoDB
            if batch_docs:
                try:
                    result = db.images.insert_many(batch_docs)
                    image_count += len(result.inserted_ids)
                    print(f"Lote {batch_number} insertado: {len(result.inserted_ids)} imágenes")
                except Exception as e:
                    print(f"Error insertando lote {batch_number}: {e}")
                    # Intentar insertar una por una como fallback
                    for doc in batch_docs:
                        try:
                            db.images.insert_one(doc)
                            image_count += 1
                        except Exception as single_error:
                            print(f"Error insertando imagen individual {doc['filename']}: {single_error}")
                            failed_images.append({'filename': doc['filename'], 'reason': str(single_error)})
            
            # Limpiar memoria del lote
            del batch_docs
            
            print(f"Progreso: {image_count}/{total_images} imágenes procesadas")
        
        print(f"Procesamiento completado: {image_count} imágenes exitosas, {len(failed_images)} fallos")
        
        # Actualizar contador de imágenes
        db.datasets.update_one(
            {'_id': ObjectId(dataset_id)},
            {'$set': {'image_count': image_count}}
        )
        
        # Preparar respuesta con estadísticas detalladas
        response_data = {
            'message': f'Dataset importado: {image_count} de {total_images} imágenes procesadas',
            'dataset_id': dataset_id,
            'total_found': total_images,
            'successfully_imported': image_count,
            'failed_imports': len(failed_images),
            'success_rate': round((image_count / total_images * 100), 2) if total_images > 0 else 0
        }
        
        # Incluir información de fallos si los hay (máximo 10 para no sobrecargar)
        if failed_images:
            response_data['sample_failures'] = failed_images[:10]
            if len(failed_images) > 10:
                response_data['additional_failures'] = len(failed_images) - 10
        
        return jsonify(response_data)
        
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
        
        # Usar directorio temporal para el ZIP (fuera del volumen monitoreado)
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, file.filename)
            file.save(zip_path)
            
            # Extraer y buscar imágenes usando la nueva función
            found_images = extract_and_find_images(zip_path, dataset_folder)
        
        total_images = len(found_images)
        print(f"Total de imágenes encontradas para importar: {total_images}")
        
        # Procesar imágenes por lotes para evitar problemas de memoria y timeout
        batch_size = 50  # Procesar de 50 en 50
        image_count = 0
        processed_images = []
        failed_images = []
        
        for i in range(0, total_images, batch_size):
            batch = found_images[i:i + batch_size]
            batch_number = (i // batch_size) + 1
            total_batches = (total_images + batch_size - 1) // batch_size
            
            print(f"Procesando lote {batch_number}/{total_batches} ({len(batch)} imágenes)")
            
            # Preparar documentos del lote
            batch_docs = []
            
            for image_info in batch:
                file_path = image_info['file_path']
                filename = image_info['filename']
                original_path = image_info['original_path']
                
                try:
                    # Leer y procesar imagen
                    with open(file_path, 'rb') as img_file:
                        image_data = img_file.read()
                    
                    # Verificar tamaño de imagen (limitar a 10MB)
                    if len(image_data) > 10 * 1024 * 1024:  # 10MB
                        print(f"Imagen {filename} demasiado grande ({len(image_data)} bytes), omitiendo")
                        failed_images.append({'filename': filename, 'reason': 'Tamaño excesivo'})
                        continue
                    
                    # Reabrir para obtener dimensiones (verify() cierra la imagen)
                    pil_image = Image.open(file_path)
                    width, height = pil_image.size
                    pil_image.close()
                    
                    # Convertir a base64 para MongoDB
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                    
                    # Calcular ruta relativa desde IMAGE_FOLDER
                    relative_path = os.path.relpath(file_path, IMAGE_FOLDER)
                    
                    # Crear documento de imagen con información adicional
                    image_doc = {
                        'filename': filename,
                        'original_name': filename,
                        'file_path': relative_path,
                        'original_zip_path': original_path,  # Ruta original dentro del ZIP
                        'data': image_base64,
                        'content_type': f'image/{filename.split(".")[-1].lower()}',
                        'size': len(image_data),
                        'width': width,
                        'height': height,
                        'upload_date': datetime.utcnow(),
                        'dataset_id': dataset_id
                    }
                    
                    batch_docs.append(image_doc)
                    
                except Exception as e:
                    print(f"Error procesando imagen {filename}: {e}")
                    failed_images.append({'filename': filename, 'reason': str(e)})
                    continue
            
            # Insertar lote completo en MongoDB
            if batch_docs:
                try:
                    result = db.images.insert_many(batch_docs)
                    image_count += len(result.inserted_ids)
                    print(f"Lote {batch_number} insertado: {len(result.inserted_ids)} imágenes")
                    
                    # Agregar IDs a processed_images para compatibilidad
                    for i, doc in enumerate(batch_docs):
                        doc['_id'] = str(result.inserted_ids[i])
                        processed_images.append(serialize_doc(doc))
                        
                except Exception as e:
                    print(f"Error insertando lote {batch_number}: {e}")
                    # Intentar insertar una por una como fallback
                    for doc in batch_docs:
                        try:
                            result = db.images.insert_one(doc)
                            doc['_id'] = str(result.inserted_id)
                            processed_images.append(serialize_doc(doc))
                            image_count += 1
                        except Exception as single_error:
                            print(f"Error insertando imagen individual {doc['filename']}: {single_error}")
                            failed_images.append({'filename': doc['filename'], 'reason': str(single_error)})
            
            # Limpiar memoria del lote
            del batch_docs
            
            print(f"Progreso: {image_count}/{total_images} imágenes procesadas")
        
        print(f"Procesamiento completado: {image_count} imágenes exitosas, {len(failed_images)} fallos")
        
        # Actualizar contador de imágenes del dataset
        current_count = db.images.count_documents({'dataset_id': dataset_id})
        db.datasets.update_one(
            {'_id': ObjectId(dataset_id)},
            {'$set': {'image_count': current_count}}
        )
        
        # Preparar respuesta con estadísticas detalladas
        response_data = {
            'message': f'Imágenes importadas: {image_count} de {total_images} procesadas exitosamente',
            'total_found': total_images,
            'successfully_imported': image_count,
            'failed_imports': len(failed_images),
            'success_rate': round((image_count / total_images * 100), 2) if total_images > 0 else 0,
            'images': processed_images[:10]  # Solo primeras 10 para no sobrecargar la respuesta
        }
        
        # Incluir información de fallos si los hay (máximo 10 para no sobrecargar)
        if failed_images:
            response_data['sample_failures'] = failed_images[:10]
            if len(failed_images) > 10:
                response_data['additional_failures'] = len(failed_images) - 10
        
        if len(processed_images) > 10:
            response_data['additional_images'] = len(processed_images) - 10
            
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': f'Error al importar imágenes: {str(e)}'}), 500

@app.route('/api/datasets/<dataset_id>/reprocess-images', methods=['POST'])
def reprocess_images_from_folder(dataset_id):
    """Reprocesar imágenes que están en carpeta pero no en base de datos"""
    try:
        db = get_db()
        
        # Verificar que el dataset existe
        dataset = db.datasets.find_one({'_id': ObjectId(dataset_id)})
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado'}), 404
        
        dataset_name = dataset['name']
        dataset_folder = os.path.join(IMAGE_FOLDER, dataset_name)
        
        if not os.path.exists(dataset_folder):
            return jsonify({'error': 'Carpeta del dataset no encontrada'}), 404
        
        # Buscar imágenes en la carpeta que no estén en la base de datos
        found_images = find_images_in_directory(dataset_folder)
        
        # Filtrar solo las que NO están en la base de datos
        existing_files = set()
        existing_images = db.images.find({'dataset_id': dataset_id}, {'filename': 1})
        for img in existing_images:
            existing_files.add(img['filename'])
        
        new_images = []
        for img_info in found_images:
            if img_info['filename'] not in existing_files:
                new_images.append(img_info)
        
        total_images = len(new_images)
        print(f"Encontradas {total_images} imágenes nuevas para procesar")
        
        if total_images == 0:
            return jsonify({
                'message': 'No se encontraron imágenes nuevas para procesar',
                'total_found': 0,
                'successfully_imported': 0
            })
        
        # Procesar imágenes por lotes
        batch_size = 50
        image_count = 0
        failed_images = []
        
        for i in range(0, total_images, batch_size):
            batch = new_images[i:i + batch_size]
            batch_number = (i // batch_size) + 1
            total_batches = (total_images + batch_size - 1) // batch_size
            
            print(f"Reprocesando lote {batch_number}/{total_batches} ({len(batch)} imágenes)")
            
            batch_docs = []
            
            for image_info in batch:
                file_path = image_info['file_path']
                filename = image_info['filename']
                
                try:
                    # Leer y procesar imagen
                    with open(file_path, 'rb') as img_file:
                        image_data = img_file.read()
                    
                    # Verificar tamaño de imagen (limitar a 10MB)
                    if len(image_data) > 10 * 1024 * 1024:  # 10MB
                        print(f"Imagen {filename} demasiado grande ({len(image_data)} bytes), omitiendo")
                        failed_images.append({'filename': filename, 'reason': 'Tamaño excesivo'})
                        continue
                    
                    # Obtener dimensiones
                    pil_image = Image.open(file_path)
                    width, height = pil_image.size
                    pil_image.close()
                    
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
                    
                    batch_docs.append(image_doc)
                    
                except Exception as e:
                    print(f"Error procesando imagen {filename}: {e}")
                    failed_images.append({'filename': filename, 'reason': str(e)})
                    continue
            
            # Insertar lote completo en MongoDB
            if batch_docs:
                try:
                    result = db.images.insert_many(batch_docs)
                    image_count += len(result.inserted_ids)
                    print(f"Lote {batch_number} insertado: {len(result.inserted_ids)} imágenes")
                except Exception as e:
                    print(f"Error insertando lote {batch_number}: {e}")
                    # Intentar insertar una por una como fallback
                    for doc in batch_docs:
                        try:
                            db.images.insert_one(doc)
                            image_count += 1
                        except Exception as single_error:
                            print(f"Error insertando imagen individual {doc['filename']}: {single_error}")
                            failed_images.append({'filename': doc['filename'], 'reason': str(single_error)})
            
            del batch_docs
            print(f"Progreso: {image_count}/{total_images} imágenes reprocesadas")
        
        # Actualizar contador de imágenes del dataset
        current_count = db.images.count_documents({'dataset_id': dataset_id})
        db.datasets.update_one(
            {'_id': ObjectId(dataset_id)},
            {'$set': {'image_count': current_count}}
        )
        
        return jsonify({
            'message': f'Reprocesamiento completado: {image_count} de {total_images} imágenes añadidas',
            'total_found': total_images,
            'successfully_imported': image_count,
            'failed_imports': len(failed_images),
            'success_rate': round((image_count / total_images * 100), 2) if total_images > 0 else 0,
            'sample_failures': failed_images[:10] if failed_images else []
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al reprocesar imágenes: {str(e)}'}), 500

# ==================== IMPORTAR ANOTACIONES ====================

@app.route('/api/annotations/import', methods=['POST'])
def import_annotations():
    """Importar anotaciones desde diferentes formatos: COCO, YOLO, PascalVOC"""
    try:
        db = get_db()
        
        # Obtener el formato de las anotaciones
        annotation_format = request.form.get('format', 'coco')
        dataset_id = request.form.get('dataset_id')
        
        if 'annotations' not in request.files:
            return jsonify({'error': 'No se encontró archivo de anotaciones'}), 400
        
        annotations_file = request.files['annotations']
        images_file = request.files.get('images')  # Opcional
        
        # Estadísticas de importación
        stats = {
            'images': 0,
            'annotations': 0,
            'categories': 0,
            'errors': []
        }
        
        if annotation_format == 'coco':
            # Procesar formato COCO (JSON)
            stats = process_coco_format(db, annotations_file, images_file, dataset_id)
        elif annotation_format == 'yolo':
            # Procesar formato YOLO (ZIP con .txt)
            stats = process_yolo_format(db, annotations_file, images_file, dataset_id)
        elif annotation_format == 'pascal':
            # Procesar formato PascalVOC (ZIP con .xml)
            stats = process_pascal_format(db, annotations_file, images_file, dataset_id)
        else:
            return jsonify({'error': f'Formato no soportado: {annotation_format}'}), 400
        
        return jsonify({
            'message': f'Anotaciones importadas exitosamente desde formato {annotation_format.upper()}',
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al importar anotaciones: {str(e)}'}), 500

def merge_coco_json_files(json_files_data):
    """
    Combina múltiples archivos JSON de formato COCO en uno solo.
    Soporta: instances_*.json, captions_*.json, person_keypoints_*.json
    
    Args:
        json_files_data: Lista de diccionarios con datos COCO
    
    Returns:
        Diccionario COCO combinado con images, annotations y categories unificadas
    """
    merged = {
        'images': [],
        'annotations': [],
        'categories': []
    }
    
    image_ids_seen = set()
    category_ids_seen = {}  # {original_id: new_id}
    annotation_id_counter = 1
    
    for coco_data in json_files_data:
        # Combinar imágenes (evitar duplicados por image_id y file_name)
        if 'images' in coco_data:
            for img in coco_data['images']:
                img_identifier = (img['id'], img.get('file_name', ''))
                if img_identifier not in image_ids_seen:
                    image_ids_seen.add(img_identifier)
                    merged['images'].append(img)
        
        # Combinar categorías (evitar duplicados por nombre)
        if 'categories' in coco_data:
            for cat in coco_data['categories']:
                # Buscar si ya existe una categoría con el mismo nombre
                existing_cat = next(
                    (c for c in merged['categories'] if c['name'] == cat['name']), 
                    None
                )
                
                if existing_cat:
                    # Mapear el ID antiguo al ID existente
                    category_ids_seen[cat['id']] = existing_cat['id']
                else:
                    # Agregar nueva categoría
                    merged['categories'].append(cat)
                    category_ids_seen[cat['id']] = cat['id']
        
        # Combinar anotaciones
        if 'annotations' in coco_data:
            for ann in coco_data['annotations']:
                # Crear copia para no modificar original
                new_ann = ann.copy()
                
                # Asignar nuevo ID de anotación
                new_ann['id'] = annotation_id_counter
                annotation_id_counter += 1
                
                # Actualizar category_id si fue remapeado
                if ann['category_id'] in category_ids_seen:
                    new_ann['category_id'] = category_ids_seen[ann['category_id']]
                
                merged['annotations'].append(new_ann)
    
    # Agregar metadata
    merged['info'] = {
        'description': 'Merged COCO dataset',
        'date_created': datetime.utcnow().isoformat(),
        'merged_files': len(json_files_data)
    }
    
    return merged


def process_coco_format(db, annotations_file, images_file, dataset_id):
    """Procesar archivo COCO JSON o ZIP con múltiples JSONs, con búsqueda por nombre de imagen dentro del dataset"""
    import json
    import zipfile
    import tempfile
    import random
    from bson import ObjectId
    from datetime import datetime
    import os

    def generate_random_color():
        """Generar un color aleatorio en formato hex"""
        return f"#{random.randint(0, 0xFFFFFF):06x}"

    coco_data = None

    # Intentar cargar JSON o ZIP
    try:
        annotations_file.seek(0)
        coco_data = json.load(annotations_file)
    except json.JSONDecodeError:
        annotations_file.seek(0)
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(annotations_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                json_files = []
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith('.json'):
                            with open(os.path.join(root, file), 'r') as f:
                                try:
                                    json_files.append(json.load(f))
                                except Exception:
                                    continue
                if len(json_files) == 1:
                    coco_data = json_files[0]
                elif len(json_files) > 1:
                    coco_data = merge_coco_json_files(json_files)
                else:
                    raise ValueError("No se encontraron archivos JSON válidos")
        except zipfile.BadZipFile:
            raise ValueError("El archivo no es un JSON válido ni un ZIP válido")

    if not coco_data:
        raise ValueError("Archivo COCO inválido")

    stats = {'images': 0, 'annotations': 0, 'categories': 0, 'errors': []}

    # ================================
    # CREAR / MAPEAR CATEGORÍAS
    # ================================
    category_map = {}
    if 'categories' in coco_data:
        for cat in coco_data['categories']:
            cat_name = cat['name']
            color = cat.get('color', generate_random_color())
            if not color.startswith('#') or len(color) != 7:
                color = generate_random_color()

            # Buscar por nombre en las categorías del dataset actual
            existing = db.categories.find_one({'name': cat_name, 'dataset_id': dataset_id})
            if existing:
                category_map[cat['id']] = str(existing['_id'])
                print(f"✅ Categoría existente: {cat_name}")
            else:
                # Crear nueva categoría en el dataset actual
                new_cat = {
                    'name': cat_name,
                    'color': color,
                    'dataset_id': dataset_id,
                    'created_date': datetime.utcnow(),
                    'annotation_count': 0
                }
                result = db.categories.insert_one(new_cat)
                category_map[cat['id']] = str(result.inserted_id)
                stats['categories'] += 1
                print(f"🆕 Categoría creada: {cat_name} ({color})")

    # =====================================
    # MAPEAR IMÁGENES POR NOMBRE DENTRO DEL DATASET
    # =====================================
    image_map = {}
    if 'images' in coco_data:
        for img in coco_data['images']:
            filename = img['file_name']
            existing_img = db.images.find_one({
                'filename': filename,
                'dataset_id': dataset_id  # <-- Solo dentro del dataset actual
            })

            if existing_img:
                image_map[img['id']] = str(existing_img['_id'])
                stats['images'] += 1
                print(f"🖼️ Imagen encontrada en dataset: {filename}")
            else:
                stats['errors'].append(f"No se encontró la imagen {filename} en el dataset actual")
                print(f"⚠️ Imagen no encontrada en dataset: {filename}")

    # =====================================
    # IMPORTAR ANOTACIONES
    # =====================================
    category_annotation_count = {}

    for ann in coco_data.get('annotations', []):
        image_id = image_map.get(ann['image_id'])
        category_id = category_map.get(ann['category_id'])
        if not image_id or not category_id:
            continue

        bbox = ann.get('bbox', [0, 0, 0, 0])
        area = ann.get('area', 0) or (bbox[2] * bbox[3] if len(bbox) >= 4 else 0)

        # Obtener color de la categoría para el stroke
        category_color = '#00ff00'  # Color por defecto
        try:
            category_doc = db.categories.find_one({'_id': ObjectId(category_id)})
            if category_doc and 'color' in category_doc:
                category_color = category_doc['color']
        except Exception:
            pass

        annotation_doc = {
            'image_id': image_id,
            'category_id': category_id,
            'bbox': bbox,
            'area': area,
            'type': 'bbox',
            'stroke': category_color,
            'strokeWidth': 2,
            'fill': 'rgba(0,255,0,0.2)',
            'closed': False,
            'created_date': datetime.utcnow(),
            'modified_date': datetime.utcnow()
        }

        # Polígonos (segmentación)
        if 'segmentation' in ann and ann['segmentation']:
            seg = ann['segmentation'][0] if isinstance(ann['segmentation'], list) else []
            if seg and isinstance(seg, list) and len(seg) >= 6:  # Al menos 3 puntos (6 valores)
                points = [[seg[i], seg[i+1]] for i in range(0, len(seg), 2)]
                annotation_doc['points'] = points
                annotation_doc['type'] = 'polygon'
                annotation_doc['closed'] = True

        db.annotations.insert_one(annotation_doc)
        stats['annotations'] += 1
        category_annotation_count[category_id] = category_annotation_count.get(category_id, 0) + 1

    # =====================================
    # ACTUALIZAR CONTADOR DE CATEGORÍAS
    # =====================================
    for category_id, count in category_annotation_count.items():
        total = db.annotations.count_documents({'category_id': category_id})
        db.categories.update_one(
            {'_id': ObjectId(category_id)},
            {'$set': {'annotation_count': total}}
        )
        print(f"📊 Categoría {category_id}: {total} anotaciones totales")

    return stats

def process_yolo_format(db, annotations_file, images_file, dataset_id):
    """Procesar formato YOLO (ZIP con archivos .txt)"""
    import zipfile
    import tempfile
    
    stats = {'images': 0, 'annotations': 0, 'categories': 0, 'errors': []}
    
    # Extraer ZIP a directorio temporal
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(annotations_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Buscar archivo classes.txt
        classes_file = os.path.join(temp_dir, 'classes.txt')
        classes = []
        category_map = {}
        
        if os.path.exists(classes_file):
            with open(classes_file, 'r') as f:
                classes = [line.strip() for line in f.readlines()]
            
            # Crear o encontrar categorías
            for idx, class_name in enumerate(classes):
                existing = db.categories.find_one({
                    'name': class_name,
                    'project_id': dataset_id or 'default'
                })
                
                if existing:
                    category_map[idx] = str(existing['_id'])
                else:
                    new_cat = {
                        'name': class_name,
                        'color': f"#{hash(class_name) & 0xFFFFFF:06x}",
                        'project_id': dataset_id or 'default',
                        'created_date': datetime.utcnow()
                    }
                    result = db.categories.insert_one(new_cat)
                    category_map[idx] = str(result.inserted_id)
                    stats['categories'] += 1
        
        # Procesar archivos .txt de anotaciones
        for filename in os.listdir(temp_dir):
            if not filename.endswith('.txt') or filename == 'classes.txt':
                continue
            
            # Buscar imagen correspondiente
            image_name = filename.replace('.txt', '')
            # Intentar con diferentes extensiones
            for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
                img_filename = image_name + ext
                existing_img = db.images.find_one({'filename': img_filename})
                if existing_img:
                    break
            
            if not existing_img:
                stats['errors'].append(f"Imagen no encontrada para: {filename}")
                continue
            
            image_id = str(existing_img['_id'])
            image_width = existing_img['width']
            image_height = existing_img['height']
            stats['images'] += 1
            
            # Leer anotaciones YOLO
            with open(os.path.join(temp_dir, filename), 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue
                    
                    class_id = int(parts[0])
                    center_x = float(parts[1])
                    center_y = float(parts[2])
                    width = float(parts[3])
                    height = float(parts[4])
                    
                    # Convertir coordenadas normalizadas a absolutas
                    abs_center_x = center_x * image_width
                    abs_center_y = center_y * image_height
                    abs_width = width * image_width
                    abs_height = height * image_height
                    
                    # Calcular bbox [x, y, width, height]
                    bbox = [
                        abs_center_x - abs_width / 2,
                        abs_center_y - abs_height / 2,
                        abs_width,
                        abs_height
                    ]
                    
                    annotation_doc = {
                        'image_id': image_id,
                        'category_id': category_map.get(class_id),
                        'bbox': bbox,
                        'type': 'bbox',
                        'area': abs_width * abs_height,
                        'created_date': datetime.utcnow(),
                        'dataset_id': dataset_id
                    }
                    
                    db.annotations.insert_one(annotation_doc)
                    stats['annotations'] += 1
    
    return stats

def process_pascal_format(db, annotations_file, images_file, dataset_id):
    """Procesar formato PascalVOC (ZIP con archivos .xml)"""
    import zipfile
    import tempfile
    import xml.etree.ElementTree as ET
    
    stats = {'images': 0, 'annotations': 0, 'categories': 0, 'errors': []}
    category_map = {}
    
    # Extraer ZIP a directorio temporal
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(annotations_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Procesar archivos .xml
        for filename in os.listdir(temp_dir):
            if not filename.endswith('.xml'):
                continue
            
            try:
                tree = ET.parse(os.path.join(temp_dir, filename))
                root = tree.getroot()
                
                # Obtener nombre de la imagen
                image_filename = root.find('filename').text if root.find('filename') is not None else filename.replace('.xml', '.jpg')
                
                # Buscar imagen en la base de datos
                existing_img = db.images.find_one({'filename': image_filename})
                if not existing_img:
                    stats['errors'].append(f"Imagen no encontrada: {image_filename}")
                    continue
                
                image_id = str(existing_img['_id'])
                stats['images'] += 1
                
                # Procesar cada objeto anotado
                for obj in root.findall('object'):
                    name = obj.find('name').text
                    
                    # Crear o encontrar categoría
                    if name not in category_map:
                        existing_cat = db.categories.find_one({
                            'name': name,
                            'project_id': dataset_id or 'default'
                        })
                        
                        if existing_cat:
                            category_map[name] = str(existing_cat['_id'])
                        else:
                            new_cat = {
                                'name': name,
                                'color': f"#{hash(name) & 0xFFFFFF:06x}",
                                'project_id': dataset_id or 'default',
                                'created_date': datetime.utcnow()
                            }
                            result = db.categories.insert_one(new_cat)
                            category_map[name] = str(result.inserted_id)
                            stats['categories'] += 1
                    
                    # Obtener coordenadas del bounding box
                    bbox_elem = obj.find('bndbox')
                    xmin = float(bbox_elem.find('xmin').text)
                    ymin = float(bbox_elem.find('ymin').text)
                    xmax = float(bbox_elem.find('xmax').text)
                    ymax = float(bbox_elem.find('ymax').text)
                    
                    # Convertir a formato [x, y, width, height]
                    bbox = [xmin, ymin, xmax - xmin, ymax - ymin]
                    
                    annotation_doc = {
                        'image_id': image_id,
                        'category_id': category_map[name],
                        'bbox': bbox,
                        'type': 'bbox',
                        'area': (xmax - xmin) * (ymax - ymin),
                        'created_date': datetime.utcnow(),
                        'dataset_id': dataset_id
                    }
                    
                    db.annotations.insert_one(annotation_doc)
                    stats['annotations'] += 1
                    
            except Exception as e:
                stats['errors'].append(f"Error procesando {filename}: {str(e)}")
    
    return stats

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

# ==================== ENDPOINTS PARA EXPORTAR ANOTACIONES ====================

@app.route('/api/annotations/export/<dataset_id>', methods=['GET'])
def export_annotations(dataset_id):
    """Exportar anotaciones en diferentes formatos (COCO, YOLO, PascalVOC)"""
    try:
        db = get_db()
        
        # Obtener parámetros
        export_format = request.args.get('format', 'coco')  # coco, yolo, pascal
        include_images = request.args.get('include_images', 'false').lower() == 'true'
        only_annotated = request.args.get('only_annotated', 'true').lower() == 'true'
        
        # Obtener dataset
        dataset = db.datasets.find_one({'_id': ObjectId(dataset_id)})
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado'}), 404
        
        # Obtener imágenes
        image_query = {'dataset_id': dataset_id}
        images = list(db.images.find(image_query))
        
        # Si only_annotated está activado, filtrar solo las que tienen anotaciones
        if only_annotated:
            image_ids = [str(img['_id']) for img in images]
            annotated_image_ids = db.annotations.distinct('image_id', {'image_id': {'$in': image_ids}})
            images = [img for img in images if str(img['_id']) in annotated_image_ids]
        
        # Obtener todas las anotaciones del dataset
        image_ids = [str(img['_id']) for img in images]
        annotations = list(db.annotations.find({'image_id': {'$in': image_ids}}))
        
        # Obtener categorías del dataset
        categories = list(db.categories.find({'dataset_id': dataset_id}))
        
        print(f"Exportando: {len(images)} imágenes, {len(annotations)} anotaciones, {len(categories)} categorías")
        
        if export_format == 'coco':
            return export_coco_format(dataset, images, annotations, categories, include_images)
        elif export_format == 'yolo':
            return export_yolo_format(dataset, images, annotations, categories, include_images, db)
        elif export_format == 'pascal':
            return export_pascal_format(dataset, images, annotations, categories, include_images, db)
        else:
            return jsonify({'error': f'Formato no soportado: {export_format}'}), 400
            
    except InvalidId:
        return jsonify({'error': 'ID de dataset inválido'}), 400
    except Exception as e:
        print(f"Error al exportar anotaciones: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/annotations/export-stats/<dataset_id>', methods=['GET'])
def get_export_statistics(dataset_id):
    """Obtener estadísticas de exportación sin realizar la exportación"""
    try:
        db = get_db()
        
        # Obtener parámetros (los mismos que el endpoint de exportación)
        only_annotated = request.args.get('only_annotated', 'true').lower() == 'true'
        
        # Obtener dataset
        dataset = db.datasets.find_one({'_id': ObjectId(dataset_id)})
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado'}), 404
        
        # Obtener imágenes
        image_query = {'dataset_id': dataset_id}
        all_images = list(db.images.find(image_query))
        
        # Filtrar imágenes según parámetros
        if only_annotated:
            image_ids = [str(img['_id']) for img in all_images]
            annotated_image_ids = db.annotations.distinct('image_id', {'image_id': {'$in': image_ids}})
            filtered_images = [img for img in all_images if str(img['_id']) in annotated_image_ids]
        else:
            filtered_images = all_images
        
        # Obtener anotaciones de las imágenes filtradas
        filtered_image_ids = [str(img['_id']) for img in filtered_images]
        annotations_count = db.annotations.count_documents({'image_id': {'$in': filtered_image_ids}})
        
        # Obtener categorías del dataset
        categories = list(db.categories.find({'dataset_id': dataset_id}))
        
        return jsonify({
            'images': len(filtered_images),
            'annotations': annotations_count,
            'categories': len(categories),
            'total_images_in_dataset': len(all_images)
        })
        
    except InvalidId:
        return jsonify({'error': 'ID de dataset inválido'}), 400
    except Exception as e:
        print(f"Error al obtener estadísticas de exportación: {e}")
        return jsonify({'error': str(e)}), 500

def export_coco_format(dataset, images, annotations, categories, include_images):
    """Exportar en formato COCO JSON"""
    from flask import Response
    import tempfile
    
    # Crear estructura COCO
    coco_data = {
        'info': {
            'description': dataset.get('name', 'Dataset'),
            'date_created': datetime.utcnow().isoformat(),
            'version': '1.0'
        },
        'images': [],
        'annotations': [],
        'categories': []
    }
    
    # Mapear categorías
    category_map = {}
    for idx, cat in enumerate(categories, start=1):
        cat_id = idx
        category_map[str(cat['_id'])] = cat_id
        coco_data['categories'].append({
            'id': cat_id,
            'name': cat['name'],
            'supercategory': 'object',
            'color': cat.get('color', '#FF0000')
        })
    
    # Mapear imágenes
    image_map = {}
    for idx, img in enumerate(images, start=1):
        img_id = idx
        image_map[str(img['_id'])] = img_id
        coco_data['images'].append({
            'id': img_id,
            'file_name': img['filename'],
            'width': img.get('width', 0),
            'height': img.get('height', 0),
            'date_captured': img.get('created_at', datetime.utcnow()).isoformat()
        })
    
    # Mapear anotaciones
    for idx, ann in enumerate(annotations, start=1):
        image_id = image_map.get(ann['image_id'])
        category_id = category_map.get(ann['category_id'])
        
        if not image_id or not category_id:
            continue
        
        bbox = ann.get('bbox', [0, 0, 0, 0])
        
        # Si la anotación tiene puntos, es un polígono
        if 'points' in ann and ann['points'] and len(ann['points']) > 0:
            # Convertir puntos a formato de segmentación COCO
            points = ann['points']
            # Aplanar los puntos: [[x1, y1], [x2, y2], ...] -> [x1, y1, x2, y2, ...]
            segmentation = []
            for point in points:
                if len(point) >= 2:
                    segmentation.extend([point[0], point[1]])
            
            # Calcular bbox desde los puntos del polígono
            if segmentation and len(segmentation) >= 6:  # Al menos 3 puntos
                x_coords = [segmentation[i] for i in range(0, len(segmentation), 2)]
                y_coords = [segmentation[i] for i in range(1, len(segmentation), 2)]
                
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                
                # Formato COCO bbox: [x, y, width, height]
                bbox = [x_min, y_min, x_max - x_min, y_max - y_min]
                
                # Calcular área del polígono usando fórmula shoelace
                area = 0
                n = len(x_coords)
                for i in range(n):
                    j = (i + 1) % n
                    area += x_coords[i] * y_coords[j]
                    area -= x_coords[j] * y_coords[i]
                area = abs(area) / 2.0
            else:
                # Si no hay suficientes puntos, usar área del bbox
                area = bbox[2] * bbox[3] if len(bbox) >= 4 else 0
                
            ann_data = {
                'id': idx,
                'image_id': image_id,
                'category_id': category_id,
                'bbox': bbox,
                'area': area,
                'segmentation': [segmentation],  # COCO usa lista de listas
                'iscrowd': 0
            }
        else:
            # Es un rectángulo/bbox
            area = bbox[2] * bbox[3] if len(bbox) >= 4 else 0
            
            ann_data = {
                'id': idx,
                'image_id': image_id,
                'category_id': category_id,
                'bbox': bbox,
                'area': area,
                'iscrowd': 0
            }
            
            # Agregar segmentación si existe (para compatibilidad con datos importados)
            if 'segmentation' in ann and ann['segmentation']:
                ann_data['segmentation'] = ann['segmentation']
        
        coco_data['annotations'].append(ann_data)
    
    # Si no se incluyen imágenes, solo devolver JSON
    if not include_images:
        json_str = json.dumps(coco_data, indent=2)
        return Response(
            json_str,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={dataset["name"]}_coco.json'}
        )
    
    # Si se incluyen imágenes, crear ZIP
    db = get_db()
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Agregar JSON de anotaciones
            zf.writestr('annotations.json', json.dumps(coco_data, indent=2))
            
            # Agregar imágenes
            for img in images:
                img_doc = db.images.find_one({'_id': ObjectId(img['_id'])})
                if img_doc and 'data' in img_doc:
                    image_data = img_doc['data']
                    zf.writestr(f"images/{img['filename']}", image_data)
        
        with open(temp_zip.name, 'rb') as f:
            zip_data = f.read()
        
        os.unlink(temp_zip.name)
        
        return Response(
            zip_data,
            mimetype='application/zip',
            headers={'Content-Disposition': f'attachment; filename={dataset["name"]}_coco.zip'}
        )
    except Exception as e:
        if os.path.exists(temp_zip.name):
            os.unlink(temp_zip.name)
        raise e

def export_yolo_format(dataset, images, annotations, categories, include_images, db):
    """Exportar en formato YOLO"""
    from flask import Response
    import tempfile
    
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Crear mapeo de categorías
            category_map = {}
            category_names = []
            for idx, cat in enumerate(categories):
                category_map[str(cat['_id'])] = idx
                category_names.append(cat['name'])
            
            # Escribir archivo classes.txt
            zf.writestr('classes.txt', '\n'.join(category_names))
            
            # Procesar cada imagen
            for img in images:
                img_id = str(img['_id'])
                img_width = img.get('width', 1)
                img_height = img.get('height', 1)
                
                # Obtener anotaciones de esta imagen
                img_annotations = [ann for ann in annotations if ann['image_id'] == img_id]
                
                if not img_annotations and not include_images:
                    continue
                
                # Crear archivo de anotaciones YOLO
                yolo_lines = []
                for ann in img_annotations:
                    category_id = category_map.get(ann['category_id'])
                    if category_id is None:
                        continue
                    
                    bbox = ann.get('bbox', [0, 0, 0, 0])
                    x, y, w, h = bbox
                    
                    # Convertir a formato YOLO (normalizado)
                    x_center = (x + w / 2) / img_width
                    y_center = (y + h / 2) / img_height
                    width_norm = w / img_width
                    height_norm = h / img_height
                    
                    yolo_lines.append(f"{category_id} {x_center:.6f} {y_center:.6f} {width_norm:.6f} {height_norm:.6f}")
                
                # Escribir archivo de anotaciones
                txt_filename = os.path.splitext(img['filename'])[0] + '.txt'
                zf.writestr(f"labels/{txt_filename}", '\n'.join(yolo_lines))
                
                # Incluir imagen si se solicita
                if include_images:
                    img_doc = db.images.find_one({'_id': ObjectId(img_id)})
                    if img_doc and 'data' in img_doc:
                        zf.writestr(f"images/{img['filename']}", img_doc['data'])
        
        with open(temp_zip.name, 'rb') as f:
            zip_data = f.read()
        
        os.unlink(temp_zip.name)
        
        return Response(
            zip_data,
            mimetype='application/zip',
            headers={'Content-Disposition': f'attachment; filename={dataset["name"]}_yolo.zip'}
        )
    except Exception as e:
        if os.path.exists(temp_zip.name):
            os.unlink(temp_zip.name)
        raise e

def export_pascal_format(dataset, images, annotations, categories, include_images, db):
    """Exportar en formato PascalVOC XML"""
    from flask import Response
    import tempfile
    import xml.etree.ElementTree as ET
    
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Crear mapeo de categorías
            category_names = {str(cat['_id']): cat['name'] for cat in categories}
            
            # Procesar cada imagen
            for img in images:
                img_id = str(img['_id'])
                
                # Obtener anotaciones de esta imagen
                img_annotations = [ann for ann in annotations if ann['image_id'] == img_id]
                
                if not img_annotations and not include_images:
                    continue
                
                # Crear XML
                annotation = ET.Element('annotation')
                
                # Información de la imagen
                ET.SubElement(annotation, 'folder').text = dataset.get('name', 'dataset')
                ET.SubElement(annotation, 'filename').text = img['filename']
                
                size = ET.SubElement(annotation, 'size')
                ET.SubElement(size, 'width').text = str(img.get('width', 0))
                ET.SubElement(size, 'height').text = str(img.get('height', 0))
                ET.SubElement(size, 'depth').text = '3'
                
                # Agregar objetos
                for ann in img_annotations:
                    obj = ET.SubElement(annotation, 'object')
                    
                    category_name = category_names.get(ann['category_id'], 'unknown')
                    ET.SubElement(obj, 'name').text = category_name
                    ET.SubElement(obj, 'pose').text = 'Unspecified'
                    ET.SubElement(obj, 'truncated').text = '0'
                    ET.SubElement(obj, 'difficult').text = '0'
                    
                    bbox = ann.get('bbox', [0, 0, 0, 0])
                    x, y, w, h = bbox
                    
                    bndbox = ET.SubElement(obj, 'bndbox')
                    ET.SubElement(bndbox, 'xmin').text = str(int(x))
                    ET.SubElement(bndbox, 'ymin').text = str(int(y))
                    ET.SubElement(bndbox, 'xmax').text = str(int(x + w))
                    ET.SubElement(bndbox, 'ymax').text = str(int(y + h))
                
                # Convertir a string XML
                xml_str = ET.tostring(annotation, encoding='unicode')
                
                # Escribir archivo XML
                xml_filename = os.path.splitext(img['filename'])[0] + '.xml'
                zf.writestr(f"annotations/{xml_filename}", xml_str)
                
                # Incluir imagen si se solicita
                if include_images:
                    img_doc = db.images.find_one({'_id': ObjectId(img_id)})
                    if img_doc and 'data' in img_doc:
                        zf.writestr(f"images/{img['filename']}", img_doc['data'])
        
        with open(temp_zip.name, 'rb') as f:
            zip_data = f.read()
        
        os.unlink(temp_zip.name)
        
        return Response(
            zip_data,
            mimetype='application/zip',
            headers={'Content-Disposition': f'attachment; filename={dataset["name"]}_pascalvoc.zip'}
        )
    except Exception as e:
        if os.path.exists(temp_zip.name):
            os.unlink(temp_zip.name)
        raise e

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

