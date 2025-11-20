from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId
import os
import json
from datetime import datetime, timedelta
import base64
from PIL import Image
import io
import zipfile
import jwt
from functools import wraps
import cv2
import numpy as np

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY no encontrada...")

if SECRET_KEY == 'dev-secret-key-change-in-production':
    raise ValueError("¡PELIGRO! Está usando la SECRET_KEY de desarrollo...")
app.config['SECRET_KEY'] = SECRET_KEY

# Permitir archivos grandes (videos, ZIPs, imágenes) - 2GB máximo
app.config['MAX_CONTENT_LENGTH'] = 2000 * 1024 * 1024  # 2GB

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

# ==================== AUTENTICACIÓN Y AUTORIZACIÓN ====================

def token_required(f):
    """Decorador para proteger rutas que requieren autenticación"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Obtener token del header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Token mal formado'}), 401
        
        if not token:
            return jsonify({'error': 'Token no proporcionado'}), 401
        
        try:
            # Decodificar token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
            
            # Verificar que el usuario existe
            db = get_db()
            user = db.users.find_one({'_id': ObjectId(current_user_id)})
            if not user:
                return jsonify({'error': 'Usuario no encontrado'}), 401
            
            # Pasar el user_id a la función
            return f(current_user_id, *args, **kwargs)
        
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401
        except Exception as e:
            return jsonify({'error': f'Error de autenticación: {str(e)}'}), 401
    
    return decorated

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Registrar un nuevo usuario"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Username y password son requeridos'}), 400
        
        username = data['username'].strip()
        password = data['password']
        full_name = data.get('full_name', '').strip()
        
        # Validar longitud
        if len(username) < 3:
            return jsonify({'error': 'El username debe tener al menos 3 caracteres'}), 400
        if len(password) < 6:
            return jsonify({'error': 'El password debe tener al menos 6 caracteres'}), 400
        
        db = get_db()
        
        # Verificar si el usuario ya existe
        if db.users.find_one({'username': username}):
            return jsonify({'error': 'El usuario ya existe'}), 409
        
        # Hash del password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Crear usuario
        user_doc = {
            'username': username,
            'password': hashed_password,
            'full_name': full_name,
            'created_at': datetime.utcnow(),
            'is_admin': False
        }
        
        result = db.users.insert_one(user_doc)
        user_id = str(result.inserted_id)
        
        # Generar token
        token = jwt.encode({
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'message': 'Usuario registrado exitosamente',
            'token': token,
            'user': {
                'id': user_id,
                'username': username,
                'full_name': full_name
            }
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Error al registrar usuario: {str(e)}'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Iniciar sesión"""
    try:
        data = request.get_json()
        
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Username y password son requeridos'}), 400
        
        username = data['username'].strip()
        password = data['password']
        
        db = get_db()
        user = db.users.find_one({'username': username})
        
        if not user:
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        # Verificar password
        if not bcrypt.check_password_hash(user['password'], password):
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        # Generar token
        token = jwt.encode({
            'user_id': str(user['_id']),
            'exp': datetime.utcnow() + timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'message': 'Login exitoso',
            'token': token,
            'user': {
                'id': str(user['_id']),
                'username': user['username'],
                'full_name': user.get('full_name', '')
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al iniciar sesión: {str(e)}'}), 500

@app.route('/api/auth/verify', methods=['GET'])
@token_required
def verify_token(current_user_id):
    """Verificar si un token es válido y obtener información del usuario"""
    try:
        db = get_db()
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        
        if not user:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        return jsonify({
            'valid': True,
            'user': {
                'id': str(user['_id']),
                'username': user['username'],
                'full_name': user.get('full_name', '')
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error al verificar token: {str(e)}'}), 500

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

def is_video_file(filename):
    """Verificar si un archivo es un video basado en su extensión"""
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
    file_ext = os.path.splitext(filename)[1].lower()
    return file_ext in video_extensions

def extract_video_frames(video_path, output_folder, fps=1):
    """
    Extraer frames de un video a una tasa específica
    
    Args:
        video_path: Ruta del archivo de video
        output_folder: Carpeta donde guardar los frames
        fps: Frames por segundo a extraer (por defecto 1 frame/segundo)
    
    Returns:
        Lista de información de frames extraídos
    """
    frames_info = []
    
    try:
        # Crear carpeta de salida
        os.makedirs(output_folder, exist_ok=True)
        
        # Abrir video
        video = cv2.VideoCapture(video_path)
        if not video.isOpened():
            raise Exception("No se pudo abrir el video")
        
        # Obtener propiedades del video
        video_fps = video.get(cv2.CAP_PROP_FPS)
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / video_fps if video_fps > 0 else 0
        width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Calcular intervalo de frames a extraer
        frame_interval = int(video_fps / fps) if fps > 0 else int(video_fps)
        
        print(f"Video FPS: {video_fps}, Extrayendo cada {frame_interval} frames")
        
        frame_count = 0
        extracted_count = 0
        
        while True:
            ret, frame = video.read()
            if not ret:
                break
            
            # Extraer frame según el intervalo
            if frame_count % frame_interval == 0:
                # Generar nombre de archivo para el frame
                timestamp = frame_count / video_fps if video_fps > 0 else 0
                frame_filename = f"frame_{extracted_count:06d}_t{timestamp:.2f}s.jpg"
                frame_path = os.path.join(output_folder, frame_filename)
                
                # Guardar frame como imagen
                cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                # Convertir frame a base64 para MongoDB
                _, buffer = cv2.imencode('.jpg', frame)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                frames_info.append({
                    'frame_number': extracted_count,
                    'timestamp': timestamp,
                    'filename': frame_filename,
                    'file_path': frame_path,
                    'width': width,
                    'height': height,
                    'data': frame_base64
                })
                
                extracted_count += 1
            
            frame_count += 1
        
        video.release()
        
        print(f"Extraídos {extracted_count} frames de {total_frames} totales")
        
        return frames_info
        
    except Exception as e:
        print(f"Error extrayendo frames del video: {str(e)}")
        return []

def find_videos_in_directory(directory_path, max_depth=3):
    """
    Buscar recursivamente todos los videos en un directorio
    
    Args:
        directory_path: Ruta del directorio a buscar
        max_depth: Profundidad máxima de búsqueda
    
    Returns:
        Lista de información de videos encontrados
    """
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
    found_videos = []
    
    for root, dirs, files in os.walk(directory_path):
        depth = root[len(directory_path):].count(os.sep)
        if depth >= max_depth:
            dirs.clear()
            continue
            
        for filename in files:
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in video_extensions:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, directory_path)
                
                found_videos.append({
                    'file_path': file_path,
                    'filename': filename,
                    'relative_path': relative_path
                })
    
    return found_videos

# Carpeta donde se guardarán las imágenes (backup)
IMAGE_FOLDER = os.path.join(os.getcwd(), 'datasets')
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# ==================== ENDPOINTS PARA IMÁGENES ====================

@app.route('/api/images', methods=['POST'])
@token_required
def upload_image(current_user_id):
    """Subir una nueva imagen o video y procesarlo según corresponda"""
    if 'image' not in request.files:
        return jsonify({'error': 'No se encontró ningún archivo'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400

    try:
        db = get_db()
        dataset_id = request.form.get('dataset_id')
        
        # Verificar si es un video
        if is_video_file(file.filename):
            # Redirigir al procesamiento de video
            return process_video_upload(file, current_user_id, dataset_id, db)
        
        # Si hay dataset_id, verificar que pertenece al usuario y obtener el nombre del dataset
        dataset_folder_path = IMAGE_FOLDER  # Por defecto en la carpeta principal
        if dataset_id:
            dataset = db.datasets.find_one({'_id': ObjectId(dataset_id), 'user_id': current_user_id})
            if dataset:
                dataset_folder_path = os.path.join(IMAGE_FOLDER, str(dataset['_id']))
                os.makedirs(dataset_folder_path, exist_ok=True)
            else:
                return jsonify({'error': 'Dataset no encontrado o no autorizado'}), 403
        
        # Leer la imagen como bytes
        image_data = file.read()
        
        # Guardar también una copia física (backup) en la carpeta correcta
        save_path = os.path.join(dataset_folder_path, file.filename)
        with open(save_path, 'wb') as f:
            f.write(image_data)
        
        # Obtener información de la imagen
        pil_image = Image.open(io.BytesIO(image_data))
        width, height = pil_image.size
        
        # Convertir imagen a base64 para MongoDB
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Guardar ruta relativa para facilitar la organización
        relative_path = os.path.relpath(save_path, IMAGE_FOLDER) if dataset_id else file.filename
        
        # Crear documento de imagen
        image_doc = {
            'filename': file.filename,
            'original_name': file.filename,
            'file_path': relative_path,  # Ruta relativa desde IMAGE_FOLDER
            'data': image_base64,
            'content_type': file.content_type,
            'size': len(image_data),
            'width': width,
            'height': height,
            'upload_date': datetime.utcnow(),
            'dataset_id': dataset_id,
            'project_id': request.form.get('project_id', 'default'),  # Mantener para compatibilidad
            'user_id': current_user_id,  # Asociar imagen al usuario
            'type': 'image'
        }
        
        # Insertar en MongoDB
        result = db.images.insert_one(image_doc)
        image_doc['_id'] = str(result.inserted_id)
        
        return jsonify({
            'message': 'Imagen subida correctamente',
            'image': serialize_doc(image_doc)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al subir archivo: {str(e)}'}), 500

def process_video_upload(video_file, current_user_id, dataset_id, db):
    """Función auxiliar para guardar el video sin procesarlo inmediatamente"""
    try:
        # Si hay dataset_id, verificar que pertenece al usuario
        dataset_folder_path = IMAGE_FOLDER
        if dataset_id:
            dataset = db.datasets.find_one({'_id': ObjectId(dataset_id), 'user_id': current_user_id})
            if dataset:
                dataset_folder_path = os.path.join(IMAGE_FOLDER, str(dataset['_id']))
                os.makedirs(dataset_folder_path, exist_ok=True)
            else:
                return jsonify({'error': 'Dataset no encontrado o no autorizado'}), 403
        
        # Guardar video
        video_filename = video_file.filename
        video_path = os.path.join(dataset_folder_path, video_filename)
        video_file.save(video_path)
        
        # Obtener información del video
        video_capture = cv2.VideoCapture(video_path)
        video_fps = video_capture.get(cv2.CAP_PROP_FPS)
        total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / video_fps if video_fps > 0 else 0
        width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        video_capture.release()
        
        # Obtener tamaño del archivo
        video_size = os.path.getsize(video_path)
        
        # Crear documento de video en MongoDB (sin procesar aún)
        video_doc = {
            'filename': video_filename,
            'original_name': video_filename,
            'file_path': os.path.relpath(video_path, IMAGE_FOLDER),
            'size': video_size,
            'width': width,
            'height': height,
            'fps': video_fps,
            'duration': duration,
            'total_frames': total_frames,
            'upload_date': datetime.utcnow(),
            'dataset_id': dataset_id,
            'user_id': current_user_id,
            'type': 'video',
            'processed': False
        }
        
        result = db.videos.insert_one(video_doc)
        video_id = str(result.inserted_id)
        video_doc['_id'] = video_id
        
        return jsonify({
            'message': 'Video subido correctamente',
            'video': serialize_doc(video_doc),
            'requires_processing': True
        })
        
    except Exception as e:
        print(f"Error al procesar video: {str(e)}")
        return jsonify({'error': f'Error al procesar video: {str(e)}'}), 500

@app.route('/api/images', methods=['GET'])
@token_required
def get_images(current_user_id):
    """Obtener lista de todas las imágenes y videos del usuario"""
    try:
        db = get_db()
        dataset_id = request.args.get('dataset_id')
        project_id = request.args.get('project_id', 'default')
        include_videos = request.args.get('include_videos', 'true').lower() == 'true'
        
        # Construir filtro - siempre filtrar por usuario
        query_filter = {'user_id': current_user_id}
        if dataset_id:
            query_filter['dataset_id'] = dataset_id
        else:
            query_filter['project_id'] = project_id

        # Obtener imágenes (excluir frames de video)
        image_filter = query_filter.copy()
        image_filter['$or'] = [
            {'type': 'image'},
            {'type': {'$exists': False}}  # Compatibilidad con imágenes antiguas
        ]
        # Excluir explícitamente frames de video
        image_filter['video_id'] = {'$exists': False}
        
        images = list(db.images.find(
            image_filter,
            {'data': 0}  # Excluir datos binarios para listar
        ))
        
        # Agregar contador de anotaciones para cada imagen
        for image in images:
            image_id = str(image['_id'])
            annotation_count = db.annotations.count_documents({'image_id': image_id, 'user_id': current_user_id})
            image['annotation_count'] = annotation_count
        
        result = {
            'images': [serialize_doc(img) for img in images]
        }
        
        # Incluir videos si se solicita
        if include_videos:
            video_filter = query_filter.copy()
            videos = list(db.videos.find(video_filter))
            
            for video in videos:
                video_id = str(video['_id'])
                # Contar anotaciones en todos los frames del video
                annotation_count = db.annotations.count_documents({
                    'video_id': video_id,
                    'user_id': current_user_id
                })
                video['annotation_count'] = annotation_count
            
            result['videos'] = [serialize_doc(video) for video in videos]
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener imágenes: {str(e)}'}), 500

@app.route('/api/images/<image_id>', methods=['GET'])
@token_required
def get_image(current_user_id, image_id):
    """Obtener una imagen específica"""
    try:
        db = get_db()
        
        if not ObjectId.is_valid(image_id):
            return jsonify({'error': 'ID de imagen inválido'}), 400
            
        image_doc = db.images.find_one({'_id': ObjectId(image_id), 'user_id': current_user_id})
        
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
            
        # Obtener la imagen sin verificar usuario (las imágenes son públicas para visualización)
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
@token_required
def delete_image(current_user_id, image_id):
    """Eliminar una imagen y sus anotaciones"""
    try:
        db = get_db()
        
        if not ObjectId.is_valid(image_id):
            return jsonify({'error': 'ID de imagen inválido'}), 400
        
        # Obtener información de la imagen antes de eliminarla y verificar propiedad
        image_doc = db.images.find_one({'_id': ObjectId(image_id), 'user_id': current_user_id})
        if not image_doc:
            return jsonify({'error': 'Imagen no encontrada o no autorizada'}), 403
            
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

# ==================== FUNCIONES AUXILIARES PARA ANOTACIONES ====================

def check_annotation_duplicate(db, image_id, category_id, category_name, bbox, tolerance=5):
    """
    Verificar si ya existe una anotación similar en la misma imagen
    
    Args:
        db: Conexión a la base de datos
        image_id: ID de la imagen
        category_id: ID de la categoría
        category_name: Nombre de la categoría  
        bbox: Bounding box [x, y, width, height]
        tolerance: Tolerancia en píxeles para considerar coordenadas similares
    
    Returns:
        dict: {'is_duplicate': bool, 'existing_annotation': dict or None}
    """
    try:
        if not bbox or len(bbox) < 4:
            return {'is_duplicate': False, 'existing_annotation': None}
        
        x, y, width, height = bbox
        
        # Buscar anotaciones existentes en la misma imagen con la misma categoría
        query = {
            'image_id': image_id,
            '$or': [
                {'category_id': category_id},
                {'category': category_name}
            ]
        }
        
        existing_annotations = db.annotations.find(query)
        
        for annotation in existing_annotations:
            existing_bbox = annotation.get('bbox')
            if not existing_bbox or len(existing_bbox) < 4:
                continue
                
            ex_x, ex_y, ex_width, ex_height = existing_bbox
            
            # Verificar si las coordenadas están dentro de la tolerancia
            x_match = abs(x - ex_x) <= tolerance
            y_match = abs(y - ex_y) <= tolerance
            width_match = abs(width - ex_width) <= tolerance
            height_match = abs(height - ex_height) <= tolerance
            
            # Si todas las coordenadas coinciden dentro de la tolerancia, es un duplicado
            if x_match and y_match and width_match and height_match:
                return {
                    'is_duplicate': True, 
                    'existing_annotation': serialize_doc(annotation)
                }
        
        return {'is_duplicate': False, 'existing_annotation': None}
        
    except Exception as e:
        print(f"Error al verificar duplicados: {e}")
        return {'is_duplicate': False, 'existing_annotation': None}

def calculate_bbox_overlap(bbox1, bbox2):
    """
    Calcular el IoU (Intersection over Union) entre dos bounding boxes
    
    Args:
        bbox1, bbox2: [x, y, width, height]
    
    Returns:
        float: Valor IoU entre 0 y 1
    """
    try:
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Convertir a coordenadas (x1, y1, x2, y2)
        box1 = [x1, y1, x1 + w1, y1 + h1]
        box2 = [x2, y2, x2 + w2, y2 + h2]
        
        # Calcular intersección
        x_left = max(box1[0], box2[0])
        y_top = max(box1[1], box2[1])
        x_right = min(box1[2], box2[2])
        y_bottom = min(box1[3], box2[3])
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
            
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        
        # Calcular áreas de las cajas
        box1_area = w1 * h1
        box2_area = w2 * h2
        
        # Calcular unión
        union_area = box1_area + box2_area - intersection_area
        
        if union_area == 0:
            return 0.0
            
        return intersection_area / union_area
        
    except Exception as e:
        print(f"Error al calcular IoU: {e}")
        return 0.0

def check_annotation_duplicate_advanced(db, image_id, category_id, category_name, bbox, iou_threshold=0.9):
    """
    Verificar duplicados usando IoU (Intersection over Union) más preciso
    
    Args:
        db: Conexión a la base de datos
        image_id: ID de la imagen (string o ObjectId)
        category_id: ID de la categoría
        category_name: Nombre de la categoría  
        bbox: Bounding box [x, y, width, height]
        iou_threshold: Umbral IoU para considerar duplicado (0.90 = 90% de solapamiento)
    
    Returns:
        dict: {'is_duplicate': bool, 'existing_annotation': dict or None, 'iou': float}
    """
    try:
        if not bbox or len(bbox) < 4:
            return {'is_duplicate': False, 'existing_annotation': None, 'iou': 0.0}
        
        # Normalizar image_id: buscar tanto por string como por ObjectId
        image_id_query = {'$or': []}
        if isinstance(image_id, str):
            image_id_query['$or'].append({'image_id': image_id})
            try:
                image_id_query['$or'].append({'image_id': ObjectId(image_id)})
            except:
                pass
        else:
            image_id_query['$or'].append({'image_id': image_id})
            image_id_query['$or'].append({'image_id': str(image_id)})
        
        # Normalizar category_id: buscar tanto por string como por ObjectId
        category_query = {'$or': []}
        if category_name:
            category_query['$or'].append({'category': category_name})
        if category_id:
            if isinstance(category_id, str):
                category_query['$or'].append({'category_id': category_id})
                try:
                    category_query['$or'].append({'category_id': ObjectId(category_id)})
                except:
                    pass
            else:
                category_query['$or'].append({'category_id': category_id})
                category_query['$or'].append({'category_id': str(category_id)})
        
        # Buscar anotaciones existentes en la misma imagen con la misma categoría
        query = {
            '$and': [
                image_id_query,
                category_query
            ]
        }
        
        existing_annotations = list(db.annotations.find(query))
        
        for annotation in existing_annotations:
            # Primero verificar contra original_bbox si existe (para detectar duplicados de IA escalados)
            original_bbox = annotation.get('original_bbox')
            if original_bbox and len(original_bbox) >= 4:
                iou_original = calculate_bbox_overlap(bbox, original_bbox)
                if iou_original >= iou_threshold:
                    return {
                        'is_duplicate': True, 
                        'existing_annotation': serialize_doc(annotation),
                        'iou': iou_original
                    }
            
            # Luego verificar contra bbox actual
            existing_bbox = annotation.get('bbox')
            if existing_bbox and len(existing_bbox) >= 4:
                iou = calculate_bbox_overlap(bbox, existing_bbox)
                if iou >= iou_threshold:
                    return {
                        'is_duplicate': True, 
                        'existing_annotation': serialize_doc(annotation),
                        'iou': iou
                    }
        
        return {'is_duplicate': False, 'existing_annotation': None, 'iou': 0.0}
        
    except Exception as e:
        import traceback
        print(f"Error al verificar duplicados avanzados: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return {'is_duplicate': False, 'existing_annotation': None, 'iou': 0.0}

# ==================== ENDPOINTS PARA VIDEOS ====================

@app.route('/api/videos/process', methods=['POST'])
@token_required
def process_video_with_fps(current_user_id):
    """Procesar un video ya subido con un FPS personalizado"""
    try:
        data = request.get_json()
        
        if not data or 'video_id' not in data:
            return jsonify({'error': 'video_id es requerido'}), 400
        
        video_id = data['video_id']
        fps = float(data.get('fps', 1))
        
        if not ObjectId.is_valid(video_id):
            return jsonify({'error': 'ID de video inválido'}), 400
        
        db = get_db()
        video_doc = db.videos.find_one({'_id': ObjectId(video_id), 'user_id': current_user_id})
        
        if not video_doc:
            return jsonify({'error': 'Video no encontrado o no autorizado'}), 403
        
        video_path = os.path.join(IMAGE_FOLDER, video_doc['file_path'])
        
        if not os.path.exists(video_path):
            return jsonify({'error': 'Archivo de video no encontrado'}), 404
        
        # Crear carpeta para frames
        video_name_no_ext = os.path.splitext(video_doc['filename'])[0]
        dataset_folder = os.path.dirname(video_path)
        frames_folder = os.path.join(dataset_folder, f"{video_name_no_ext}_frames")
        os.makedirs(frames_folder, exist_ok=True)
        
        # Extraer frames
        frames_info = extract_video_frames(video_path, frames_folder, fps=fps)
        
        if not frames_info:
            return jsonify({'error': 'No se pudieron extraer frames del video'}), 500
        
        # Actualizar documento de video
        db.videos.update_one(
            {'_id': ObjectId(video_id)},
            {'$set': {
                'frames_folder': os.path.relpath(frames_folder, IMAGE_FOLDER),
                'extracted_frames': len(frames_info),
                'frames_count': len(frames_info),
                'extraction_fps': fps,
                'processed': True,
                'processed_date': datetime.utcnow()
            }}
        )
        
        # Guardar frames en la colección de imágenes marcados como frames de video
        frame_ids = []
        for frame_info in frames_info:
            frame_doc = {
                'filename': frame_info['filename'],
                'original_name': frame_info['filename'],
                'file_path': os.path.relpath(frame_info['file_path'], IMAGE_FOLDER),
                'data': frame_info['data'],
                'content_type': 'image/jpeg',
                'size': len(base64.b64decode(frame_info['data'])),
                'width': frame_info['width'],
                'height': frame_info['height'],
                'upload_date': datetime.utcnow(),
                'dataset_id': video_doc.get('dataset_id'),
                'user_id': current_user_id,
                'type': 'video_frame',
                'video_id': video_id,
                'frame_number': frame_info['frame_number'],
                'timestamp': frame_info['timestamp']
            }
            
            result = db.images.insert_one(frame_doc)
            frame_ids.append(str(result.inserted_id))
        
        return jsonify({
            'message': f'Video procesado correctamente. Se extrajeron {len(frames_info)} frames.',
            'video_id': video_id,
            'frames_count': len(frames_info),
            'frame_ids': frame_ids
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al procesar video: {str(e)}'}), 500

@app.route('/api/videos', methods=['POST'])
@token_required
def upload_video(current_user_id):
    """Subir un nuevo video y extraer frames para anotación"""
    if 'video' not in request.files:
        return jsonify({'error': 'No se encontró ningún video'}), 400

    video_file = request.files['video']
    if video_file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400

    try:
        db = get_db()
        dataset_id = request.form.get('dataset_id')
        
        # Verificar que es un video
        if not is_video_file(video_file.filename):
            return jsonify({'error': 'El archivo no es un video válido'}), 400
        
        # Si hay dataset_id, verificar que pertenece al usuario
        dataset_folder_path = IMAGE_FOLDER
        if dataset_id:
            dataset = db.datasets.find_one({'_id': ObjectId(dataset_id), 'user_id': current_user_id})
            if dataset:
                dataset_folder_path = os.path.join(IMAGE_FOLDER, str(dataset['_id']))
                os.makedirs(dataset_folder_path, exist_ok=True)
            else:
                return jsonify({'error': 'Dataset no encontrado o no autorizado'}), 403
        
        # Guardar video original
        video_filename = video_file.filename
        video_path = os.path.join(dataset_folder_path, video_filename)
        video_file.save(video_path)
        
        # Crear carpeta para frames del video
        video_name_no_ext = os.path.splitext(video_filename)[0]
        frames_folder = os.path.join(dataset_folder_path, f"{video_name_no_ext}_frames")
        os.makedirs(frames_folder, exist_ok=True)
        
        # Extraer frames (1 fps por defecto)
        fps = float(request.form.get('fps', 1))
        frames_info = extract_video_frames(video_path, frames_folder, fps=fps)
        
        if not frames_info:
            return jsonify({'error': 'No se pudieron extraer frames del video'}), 500
        
        # Obtener información del video
        video_capture = cv2.VideoCapture(video_path)
        video_fps = video_capture.get(cv2.CAP_PROP_FPS)
        total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / video_fps if video_fps > 0 else 0
        width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        video_capture.release()
        
        # Obtener tamaño del archivo
        video_size = os.path.getsize(video_path)
        
        # Crear documento de video en MongoDB
        video_doc = {
            'filename': video_filename,
            'original_name': video_filename,
            'file_path': os.path.relpath(video_path, IMAGE_FOLDER),
            'frames_folder': os.path.relpath(frames_folder, IMAGE_FOLDER),
            'size': video_size,
            'width': width,
            'height': height,
            'fps': video_fps,
            'duration': duration,
            'total_frames': total_frames,
            'extracted_frames': len(frames_info),
            'frames_count': len(frames_info),  # Agregar frames_count para compatibilidad con frontend
            'upload_date': datetime.utcnow(),
            'dataset_id': dataset_id,
            'user_id': current_user_id,
            'type': 'video'
        }
        
        result = db.videos.insert_one(video_doc)
        video_id = str(result.inserted_id)
        video_doc['_id'] = video_id
        
        # Guardar frames en la colección de imágenes con referencia al video
        frame_ids = []
        for frame_info in frames_info:
            frame_doc = {
                'filename': frame_info['filename'],
                'original_name': frame_info['filename'],
                'file_path': os.path.relpath(frame_info['file_path'], IMAGE_FOLDER),
                'data': frame_info['data'],
                'content_type': 'image/jpeg',
                'size': len(base64.b64decode(frame_info['data'])),
                'width': frame_info['width'],
                'height': frame_info['height'],
                'upload_date': datetime.utcnow(),
                'dataset_id': dataset_id,
                'user_id': current_user_id,
                'video_id': video_id,  # Referencia al video
                'frame_number': frame_info['frame_number'],
                'timestamp': frame_info['timestamp'],
                'type': 'video_frame'
            }
            
            frame_result = db.images.insert_one(frame_doc)
            frame_ids.append(str(frame_result.inserted_id))
        
        return jsonify({
            'message': 'Video subido y procesado correctamente',
            'video': serialize_doc(video_doc),
            'frames_count': len(frame_ids),
            'frame_ids': frame_ids
        })
        
    except Exception as e:
        print(f"Error al subir video: {str(e)}")
        return jsonify({'error': f'Error al subir video: {str(e)}'}), 500

@app.route('/api/videos', methods=['GET'])
@token_required
def get_videos(current_user_id):
    """Obtener lista de todos los videos del usuario"""
    try:
        db = get_db()
        dataset_id = request.args.get('dataset_id')
        
        query_filter = {'user_id': current_user_id}
        if dataset_id:
            query_filter['dataset_id'] = dataset_id
        
        videos = list(db.videos.find(query_filter))
        
        # Agregar contador de anotaciones para cada video
        for video in videos:
            video_id = str(video['_id'])
            # Contar anotaciones en todos los frames del video
            annotation_count = db.annotations.count_documents({
                'video_id': video_id,
                'user_id': current_user_id
            })
            video['annotation_count'] = annotation_count
        
        return jsonify({
            'videos': [serialize_doc(video) for video in videos]
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener videos: {str(e)}'}), 500

@app.route('/api/videos/<video_id>', methods=['GET'])
@token_required
def get_video(current_user_id, video_id):
    """Obtener información de un video específico"""
    try:
        db = get_db()
        
        if not ObjectId.is_valid(video_id):
            return jsonify({'error': 'ID de video inválido'}), 400
        
        video_doc = db.videos.find_one({'_id': ObjectId(video_id), 'user_id': current_user_id})
        
        if not video_doc:
            return jsonify({'error': 'Video no encontrado'}), 404
        
        return jsonify({
            'video': serialize_doc(video_doc)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener video: {str(e)}'}), 500

@app.route('/api/videos/<video_id>/frames', methods=['GET'])
@token_required
def get_video_frames(current_user_id, video_id):
    """Obtener todos los frames de un video"""
    try:
        db = get_db()
        
        if not ObjectId.is_valid(video_id):
            return jsonify({'error': 'ID de video inválido'}), 400
        
        # Verificar que el video existe y pertenece al usuario
        video_doc = db.videos.find_one({'_id': ObjectId(video_id), 'user_id': current_user_id})
        if not video_doc:
            return jsonify({'error': 'Video no encontrado'}), 404
        
        # Obtener frames del video (sin los datos base64 para listar)
        limit = request.args.get('limit', type=int)
        frames_cursor = db.images.find(
            {'video_id': video_id, 'user_id': current_user_id},
            {'data': 0}
        ).sort('frame_number', 1)

        if limit:
            frames_cursor = frames_cursor.limit(max(limit, 0))

        frames = list(frames_cursor)
        
        # Agregar contador de anotaciones para cada frame
        for frame in frames:
            frame_id = str(frame['_id'])
            annotation_count = db.annotations.count_documents({
                'image_id': frame_id,
                'user_id': current_user_id
            })
            frame['annotation_count'] = annotation_count
        
        return jsonify({
            'frames': [serialize_doc(frame) for frame in frames]
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener frames: {str(e)}'}), 500

@app.route('/api/videos/<video_id>', methods=['DELETE'])
@token_required
def delete_video(current_user_id, video_id):
    """Eliminar un video, sus frames y anotaciones"""
    try:
        db = get_db()
        
        if not ObjectId.is_valid(video_id):
            return jsonify({'error': 'ID de video inválido'}), 400
        
        # Obtener información del video
        video_doc = db.videos.find_one({'_id': ObjectId(video_id), 'user_id': current_user_id})
        if not video_doc:
            return jsonify({'error': 'Video no encontrado o no autorizado'}), 403
        
        # Eliminar archivo de video
        if 'file_path' in video_doc:
            video_path = os.path.join(IMAGE_FOLDER, video_doc['file_path'])
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
            except Exception as e:
                print(f"Error al eliminar archivo de video: {str(e)}")
        
        # Eliminar carpeta de frames
        if 'frames_folder' in video_doc:
            frames_folder = os.path.join(IMAGE_FOLDER, video_doc['frames_folder'])
            try:
                if os.path.exists(frames_folder):
                    import shutil
                    shutil.rmtree(frames_folder)
            except Exception as e:
                print(f"Error al eliminar carpeta de frames: {str(e)}")
        
        # Eliminar frames de la colección de imágenes
        frames_result = db.images.delete_many({'video_id': video_id, 'user_id': current_user_id})
        
        # Eliminar anotaciones de los frames
        annotations_result = db.annotations.delete_many({'video_id': video_id, 'user_id': current_user_id})
        
        # Eliminar documento del video
        db.videos.delete_one({'_id': ObjectId(video_id)})
        
        return jsonify({
            'message': 'Video eliminado correctamente',
            'deleted_frames': frames_result.deleted_count,
            'deleted_annotations': annotations_result.deleted_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al eliminar video: {str(e)}'}), 500

# ==================== ENDPOINTS PARA ANOTACIONES ====================

@app.route('/api/annotations', methods=['POST'])
@token_required
def create_annotation(current_user_id):
    """Crear una nueva anotación"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No se proporcionaron datos'}), 400
            
        if 'image_id' not in data:
            return jsonify({'error': 'image_id es requerido'}), 400
        
        db = get_db()
        
        # Obtener información de la imagen para verificar el dataset y usuario
        image_doc = db.images.find_one({'_id': ObjectId(data['image_id']), 'user_id': current_user_id})
        if not image_doc:
            return jsonify({'error': 'Imagen no encontrada o no autorizada'}), 404
        
        dataset_id = image_doc.get('dataset_id')
        if not dataset_id:
            return jsonify({'error': 'La imagen debe pertenecer a un dataset'}), 400
        
        # Verificar que existan categorías en el dataset antes de permitir anotaciones
        categories_count = db.categories.count_documents({'dataset_id': dataset_id, 'user_id': current_user_id})
        if categories_count == 0:
            return jsonify({
                'error': 'No se pueden crear anotaciones sin categorías. Primero debe crear al menos una categoría para este dataset.',
                'code': 'NO_CATEGORIES_AVAILABLE'
            }), 400
        
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
            'source': data.get('source', 'manual'),  # manual, ai_prediction, imported
            'confidence': data.get('confidence'),  # Solo para predicciones de IA
            'model_name': data.get('model_name'),  # Solo para predicciones de IA
            'created_date': datetime.utcnow(),
            'modified_date': datetime.utcnow(),
            'user_id': current_user_id,  # Asociar anotación al usuario
            'video_id': image_doc.get('video_id')  # Asociar con video si el frame pertenece a uno
        }
        
        # Verificar duplicados antes de crear la anotación
        check_duplicates = data.get('check_duplicates', True)  # Por defecto verificar duplicados
        
        if check_duplicates and bbox:
            duplicate_result = check_annotation_duplicate_advanced(
                db, 
                data['image_id'], 
                data.get('category_id'), 
                data.get('category', 'default'), 
                bbox,
                iou_threshold=0.90  # 90% de solapamiento
            )
            
            if duplicate_result['is_duplicate']:
                return jsonify({
                    'message': 'Anotación duplicada detectada',
                    'is_duplicate': True,
                    'existing_annotation': duplicate_result['existing_annotation'],
                    'iou': duplicate_result['iou'],
                    'action': 'skipped'
                }), 200
        
        # Insertar en MongoDB
        result = db.annotations.insert_one(annotation_doc)
        annotation_doc['_id'] = str(result.inserted_id)
        
        return jsonify({
            'message': 'Anotación creada correctamente',
            'annotation': serialize_doc(annotation_doc),
            'is_duplicate': False
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al crear anotación: {str(e)}'}), 500

@app.route('/api/annotations', methods=['GET'])
@token_required
def get_annotations(current_user_id):
    """Obtener anotaciones de una imagen específica, todas las anotaciones o anotaciones de un dataset"""
    try:
        image_id = request.args.get('image_id')
        dataset_id = request.args.get('dataset_id')
        
        db = get_db()
        
        if image_id:
            # Obtener anotaciones de una imagen específica del usuario
            annotations = list(db.annotations.find({'image_id': image_id, 'user_id': current_user_id}))
        elif dataset_id:
            # Obtener todas las anotaciones de un dataset específico del usuario
            # Primero obtener todas las imágenes del dataset del usuario
            images = list(db.images.find({'dataset_id': dataset_id, 'user_id': current_user_id}))
            image_ids = [str(img['_id']) for img in images]
            
            # Luego obtener anotaciones de esas imágenes del usuario
            annotations = list(db.annotations.find({'image_id': {'$in': image_ids}, 'user_id': current_user_id}))
        else:
            # Obtener todas las anotaciones del usuario
            annotations = list(db.annotations.find({'user_id': current_user_id}))
        
        return jsonify({
            'annotations': [serialize_doc(ann) for ann in annotations]
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener anotaciones: {str(e)}'}), 500

@app.route('/api/annotations/<annotation_id>', methods=['PUT'])
@token_required
def update_annotation(current_user_id, annotation_id):
    """Actualizar una anotación existente"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No se proporcionaron datos'}), 400
            
        if not ObjectId.is_valid(annotation_id):
            return jsonify({'error': 'ID de anotación inválido'}), 400
        
        db = get_db()
        
        # Verificar que la anotación pertenece a una imagen del usuario
        annotation = db.annotations.find_one({'_id': ObjectId(annotation_id)})
        if not annotation:
            return jsonify({'error': 'Anotación no encontrada'}), 404
        
        # Verificar propiedad a través de la imagen
        image = db.images.find_one({'_id': ObjectId(annotation['image_id']), 'user_id': current_user_id})
        if not image:
            return jsonify({'error': 'No autorizado para actualizar esta anotación'}), 403
        
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
@token_required
def delete_annotation(current_user_id, annotation_id):
    """Eliminar una anotación"""
    try:
        if not ObjectId.is_valid(annotation_id):
            return jsonify({'error': 'ID de anotación inválido'}), 400
        
        db = get_db()
        
        # Verificar que la anotación pertenece a una imagen del usuario
        annotation = db.annotations.find_one({'_id': ObjectId(annotation_id)})
        if not annotation:
            return jsonify({'error': 'Anotación no encontrada'}), 404
        
        # Verificar propiedad a través de la imagen
        image = db.images.find_one({'_id': ObjectId(annotation['image_id']), 'user_id': current_user_id})
        if not image:
            return jsonify({'error': 'No autorizado para eliminar esta anotación'}), 403
        
        # Eliminar la anotación
        result = db.annotations.delete_one({'_id': ObjectId(annotation_id)})
        
        if result.deleted_count == 0:
            return jsonify({'error': 'Error al eliminar anotación'}), 500
            
        return jsonify({'message': 'Anotación eliminada correctamente'})
        
    except Exception as e:
        return jsonify({'error': f'Error al eliminar anotación: {str(e)}'}), 500

@app.route('/api/annotations/bulk', methods=['DELETE'])
@token_required
def delete_annotations_bulk(current_user_id):
    """Eliminar múltiples anotaciones por image_id"""
    try:
        data = request.get_json()
        
        if not data or 'image_id' not in data:
            return jsonify({'error': 'image_id es requerido'}), 400
        
        db = get_db()
        
        # Verificar que la imagen pertenece al usuario
        image = db.images.find_one({'_id': ObjectId(data['image_id']), 'user_id': current_user_id})
        if not image:
            return jsonify({'error': 'No autorizado para eliminar anotaciones de esta imagen'}), 403
        
        # Eliminar anotaciones de la imagen
        result = db.annotations.delete_many({'image_id': data['image_id']})
        
        return jsonify({
            'message': f'{result.deleted_count} anotaciones eliminadas correctamente',
            'deleted_count': result.deleted_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al eliminar anotaciones: {str(e)}'}), 500

# ==================== ENDPOINTS PARA CATEGORÍAS ====================

@app.route('/api/categories', methods=['GET'])
@token_required
def get_categories(current_user_id):
    """Obtener todas las categorías de un dataset específico o de todos los datasets del usuario"""
    try:
        db = get_db()
        dataset_id = request.args.get('dataset_id')
        
        # Si se proporciona dataset_id, filtrar por ese dataset y usuario
        # Si no, devolver todas las categorías del usuario (vista global)
        if dataset_id:
            categories = list(db.categories.find({'dataset_id': dataset_id, 'user_id': current_user_id}))
        else:
            categories = list(db.categories.find({'user_id': current_user_id}))
        
        # Contar anotaciones por categoría y estandarizar formato
        for category in categories:
            category_id = str(category['_id'])
            # Buscar anotaciones que coincidan con category_id O category
            annotation_count = db.annotations.count_documents({
                'user_id': current_user_id,
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
@token_required
def create_category(current_user_id):
    """Crear una nueva categoría asociada a un dataset específico"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({'error': 'name es requerido'}), 400
        
        if 'dataset_id' not in data or not data['dataset_id']:
            return jsonify({'error': 'dataset_id es requerido. Debes especificar a qué dataset pertenece esta categoría.'}), 400
        
        db = get_db()
        
        # Verificar que el dataset existe y pertenece al usuario
        dataset = db.datasets.find_one({'_id': ObjectId(data['dataset_id']), 'user_id': current_user_id})
        if not dataset:
            return jsonify({'error': 'El dataset especificado no existe o no tienes acceso'}), 404
        
        # Crear documento de categoría
        category_doc = {
            'name': data['name'],
            'color': data.get('color', '#00ff00'),
            'dataset_id': data['dataset_id'],
            'created_date': datetime.utcnow(),
            'user_id': current_user_id  # Asociar categoría al usuario
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
@token_required
def get_category(current_user_id, category_id):
    """Obtener una categoría por ID"""
    try:
        db = get_db()
        
        # Verificar que la categoría pertenece al usuario
        category = db.categories.find_one({'_id': ObjectId(category_id), 'user_id': current_user_id})
        
        if not category:
            return jsonify({'error': 'Categoría no encontrada o no autorizada'}), 403
        
        return jsonify({
            'category': serialize_doc(category)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener categoría: {str(e)}'}), 500

@app.route('/api/categories/<category_id>', methods=['PUT'])
@token_required
def update_category(current_user_id, category_id):
    """Actualizar una categoría existente"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400
        
        db = get_db()
        
        # Verificar que la categoría pertenece al usuario
        existing_category = db.categories.find_one({'_id': ObjectId(category_id), 'user_id': current_user_id})
        if not existing_category:
            return jsonify({'error': 'Categoría no encontrada o no autorizada'}), 403
        
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
            {'_id': ObjectId(category_id), 'user_id': current_user_id},
            {'$set': update_fields}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'Error al actualizar categoría'}), 500
        
        # Obtener categoría actualizada
        updated_category = db.categories.find_one({'_id': ObjectId(category_id), 'user_id': current_user_id})
        
        return jsonify({
            'message': 'Categoría actualizada correctamente',
            'category': serialize_doc(updated_category)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al actualizar categoría: {str(e)}'}), 500

@app.route('/api/categories/<category_id>', methods=['DELETE'])
@token_required
def delete_category(current_user_id, category_id):
    """Eliminar una categoría y opcionalmente sus anotaciones asociadas"""
    try:
        db = get_db()
        
        # Verificar que la categoría pertenece al usuario
        category = db.categories.find_one({'_id': ObjectId(category_id), 'user_id': current_user_id})
        if not category:
            return jsonify({'error': 'Categoría no encontrada o no autorizada'}), 403
        
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
        
        # Eliminar registros de visibilidad asociados a esta categoría
        visibility_result = db.category_visibility.delete_many({'category_id': category_id})
        print(f"Eliminados {visibility_result.deleted_count} registros de visibilidad de la categoría {category_id}")
        
        # Eliminar categoría
        result = db.categories.delete_one({'_id': ObjectId(category_id), 'user_id': current_user_id})
        
        if result.deleted_count == 0:
            return jsonify({'error': 'Error al eliminar categoría'}), 500
        
        return jsonify({
            'message': 'Categoría eliminada correctamente',
            'deleted_annotations': annotation_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al eliminar categoría: {str(e)}'}), 500

@app.route('/api/categories/<category_id>/toggle-visibility', methods=['PATCH'])
@token_required
def toggle_category_visibility(current_user_id, category_id):
    """Toggle visibilidad de una categoría para un dataset específico"""
    try:
        db = get_db()
        dataset_id = request.args.get('dataset_id')
        
        if not dataset_id:
            return jsonify({'error': 'dataset_id es requerido'}), 400
        
        # Verificar que la categoría pertenece al usuario
        category = db.categories.find_one({'_id': ObjectId(category_id), 'user_id': current_user_id})
        if not category:
            return jsonify({'error': 'Categoría no encontrada o no autorizada'}), 403
        
        # Verificar que el dataset pertenece al usuario
        dataset = db.datasets.find_one({'_id': ObjectId(dataset_id), 'user_id': current_user_id})
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado o no autorizado'}), 403
        
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
@token_required
def get_categories_visibility(current_user_id, dataset_id):
    """Obtener visibilidad de categorías para un dataset"""
    try:
        db = get_db()
        
        # Verificar que el dataset pertenece al usuario
        dataset = db.datasets.find_one({'_id': ObjectId(dataset_id), 'user_id': current_user_id})
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado o no autorizado'}), 403
        
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
@token_required
def get_categories_data(current_user_id):
    """Obtener estadísticas de categorías con conteo de anotaciones"""
    try:
        db = get_db()
        dataset_id = request.args.get('dataset_id')
        
        # Si no se proporciona dataset_id, devolver error
        if not dataset_id:
            return jsonify({'error': 'dataset_id es requerido'}), 400
        
        # Verificar que el dataset pertenece al usuario
        dataset = db.datasets.find_one({'_id': ObjectId(dataset_id), 'user_id': current_user_id})
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado o no autorizado'}), 403
        
        # Obtener todas las categorías del dataset del usuario
        categories = list(db.categories.find({'dataset_id': dataset_id, 'user_id': current_user_id}))
        
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

@app.route('/api/categories/check/<dataset_id>', methods=['GET'])
@token_required
def check_categories_availability(current_user_id, dataset_id):
    """Verificar si un dataset tiene categorías disponibles"""
    try:
        db = get_db()
        
        # Verificar que el dataset pertenece al usuario
        dataset = db.datasets.find_one({'_id': ObjectId(dataset_id), 'user_id': current_user_id})
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado o no autorizado'}), 403
        
        # Contar categorías en el dataset del usuario
        categories_count = db.categories.count_documents({'dataset_id': dataset_id, 'user_id': current_user_id})
        
        # Obtener lista de categorías si existen
        categories = []
        if categories_count > 0:
            categories_list = list(db.categories.find({'dataset_id': dataset_id, 'user_id': current_user_id}))
            categories = [serialize_doc(cat) for cat in categories_list]
        
        return jsonify({
            'has_categories': categories_count > 0,
            'total_categories': categories_count,
            'categories': categories,
            'can_annotate': categories_count > 0
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al verificar categorías: {str(e)}'}), 500

# ==================== ENDPOINTS PARA DATASETS ====================

@app.route('/api/datasets', methods=['GET'])
@token_required
def get_datasets(current_user_id):
    """Obtener lista de todos los datasets del usuario"""
    try:
        db = get_db()
        # Filtrar solo datasets del usuario actual
        datasets = list(db.datasets.find({'user_id': current_user_id}, {'images': 0}))  # Excluir lista de imágenes para listar
        
        # Contar archivos (imágenes + videos) para cada dataset
        for dataset in datasets:
            dataset_id = str(dataset['_id'])
            # Imágenes que no son frames de video
            n_images = db.images.count_documents({'dataset_id': dataset_id, 'user_id': current_user_id, 'video_id': {'$exists': False}})
            # Videos
            n_videos = db.videos.count_documents({'dataset_id': dataset_id, 'user_id': current_user_id})
            dataset['file_count'] = n_images + n_videos
        
        return jsonify({
            'datasets': [serialize_doc(ds) for ds in datasets]
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al obtener datasets: {str(e)}'}), 500

@app.route('/api/datasets', methods=['POST'])
@token_required
def create_dataset(current_user_id):
    """Crear un nuevo dataset"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({'error': 'name es requerido'}), 400
        
        db = get_db()
        
        # Permitir que diferentes usuarios tengan datasets con el mismo nombre
        # Solo verificar duplicados para el mismo usuario
        existing = db.datasets.find_one({'name': data['name'], 'user_id': current_user_id})
        if existing:
            return jsonify({'error': 'Ya existe un dataset con ese nombre para tu usuario'}), 400
        
        # Obtener el nombre del usuario
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        nombre_usuario = user.get('full_name') or user.get('username') or 'usuario'

        # Crear documento de dataset
        dataset_doc = {
            'name': data['name'],
            'description': data.get('description', ''),
            'folder_path': f"/datasets/{data['name']}",
            'categories': data.get('categories', []),
            'created_date': datetime.utcnow(),
            'created_by': nombre_usuario,
            'image_count': 0,
            'user_id': current_user_id  # Asociar dataset al usuario
        }
        
        # Insertar en MongoDB
        result = db.datasets.insert_one(dataset_doc)
        dataset_doc['_id'] = str(result.inserted_id)
        
        # Crear directorio físico usando el ID del dataset
        dataset_folder = os.path.join(IMAGE_FOLDER, str(result.inserted_id))
        os.makedirs(dataset_folder, exist_ok=True)
        
        return jsonify({
            'message': 'Dataset creado correctamente',
            'dataset': serialize_doc(dataset_doc)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al crear dataset: {str(e)}'}), 500

@app.route('/api/datasets/<dataset_id>', methods=['GET'])
@token_required
def get_dataset(current_user_id, dataset_id):
    """Obtener un dataset específico con sus imágenes"""
    try:
        db = get_db()
        
        if not ObjectId.is_valid(dataset_id):
            return jsonify({'error': 'ID de dataset inválido'}), 400
            
        dataset = db.datasets.find_one({'_id': ObjectId(dataset_id), 'user_id': current_user_id})
        
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado'}), 404
        
        # Obtener imágenes del dataset del usuario
        images = list(db.images.find(
            {'dataset_id': dataset_id, 'user_id': current_user_id},
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
@token_required
def delete_dataset(current_user_id, dataset_id):
    """Eliminar un dataset y todas sus imágenes/anotaciones"""
    try:
        db = get_db()
        
        if not ObjectId.is_valid(dataset_id):
            return jsonify({'error': 'ID de dataset inválido'}), 400
        
        # Verificar que existe y pertenece al usuario
        dataset = db.datasets.find_one({'_id': ObjectId(dataset_id), 'user_id': current_user_id})
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
        
        # Eliminar registros de visibilidad del dataset antes de eliminar las categorías
        visibility_result = db.category_visibility.delete_many({'dataset_id': dataset_id})
        print(f"Eliminados {visibility_result.deleted_count} registros de visibilidad del dataset {dataset_id}")
        
        # Eliminar todas las categorías asociadas al dataset
        categories_result = db.categories.delete_many({'dataset_id': dataset_id})
        
        # Eliminar todas las imágenes del dataset de la base de datos
        images_result = db.images.delete_many({'dataset_id': dataset_id})
        
        # Eliminar carpeta física completa del dataset usando el ID
        dataset_folder = os.path.join(IMAGE_FOLDER, str(dataset_id))
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
            'deleted_categories': categories_result.deleted_count,
            'deleted_folder': deleted_folder,
            'dataset_name': dataset_name
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al eliminar dataset: {str(e)}'}), 500

@app.route('/api/datasets/import', methods=['POST'])
@token_required
def import_dataset_zip(current_user_id):
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
        
        # Verificar que no existe un dataset con el mismo nombre para este usuario
        existing = db.datasets.find_one({'name': dataset_name, 'user_id': current_user_id})
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
            'image_count': 0,
            'user_id': current_user_id  # Asociar dataset al usuario
        }
        
        result = db.datasets.insert_one(dataset_doc)
        dataset_id = str(result.inserted_id)
        
        # Crear directorio usando el ID del dataset
        dataset_folder = os.path.join(IMAGE_FOLDER, dataset_id)
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
                        'dataset_id': dataset_id,
                        'user_id': current_user_id  # Asociar imagen al usuario
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
@token_required
def import_images_to_dataset(current_user_id):
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
        
        # Verificar que el dataset existe y pertenece al usuario
        dataset = db.datasets.find_one({'_id': ObjectId(dataset_id), 'user_id': current_user_id})
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado'}), 404
        
        # Usar el ID del dataset para la carpeta
        dataset_folder = os.path.join(IMAGE_FOLDER, str(dataset_id))
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
                        'dataset_id': dataset_id,
                        'user_id': current_user_id  # Asociar imagen al usuario
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
@token_required
def reprocess_images_from_folder(current_user_id, dataset_id):
    """Reprocesar imágenes que están en carpeta pero no en base de datos"""
    try:
        db = get_db()
        
        # Verificar que el dataset existe y pertenece al usuario
        dataset = db.datasets.find_one({
            '_id': ObjectId(dataset_id),
        })
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado o no autorizado'}), 403
        
        # Usar el ID del dataset para la carpeta
        dataset_folder = os.path.join(IMAGE_FOLDER, str(dataset_id))
        
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
                        'dataset_id': dataset_id,
                        'user_id': ObjectId(current_user_id)
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
@token_required
def import_annotations(current_user_id):
    """Importar anotaciones desde diferentes formatos: COCO, YOLO, PascalVOC"""
    try:
        db = get_db()
        
        # Obtener el formato de las anotaciones
        annotation_format = request.form.get('format', 'coco')
        dataset_id = request.form.get('dataset_id')
        
        # Verificar que el dataset pertenece al usuario
        if dataset_id:
            dataset = db.datasets.find_one({'_id': ObjectId(dataset_id), 'user_id': current_user_id})
            if not dataset:
                return jsonify({'error': 'Dataset no encontrado o no autorizado'}), 403
        
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
            stats = process_coco_format(db, annotations_file, images_file, dataset_id, current_user_id)
        elif annotation_format == 'yolo':
            # Procesar formato YOLO (ZIP con .txt)
            stats = process_yolo_format(db, annotations_file, images_file, dataset_id, current_user_id)
        elif annotation_format == 'pascal':
            # Procesar formato PascalVOC (ZIP con .xml)
            stats = process_pascal_format(db, annotations_file, images_file, dataset_id, current_user_id)
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


def process_coco_format(db, annotations_file, images_file, dataset_id, user_id):
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
                    'annotation_count': 0,
                    'user_id': user_id  # Asociar categoría al usuario
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
            'modified_date': datetime.utcnow(),
            'user_id': user_id  # Asociar anotación al usuario
        }

        # Polígonos (segmentación)
        if 'segmentation' in ann and ann['segmentation']:
            seg = ann['segmentation'][0] if isinstance(ann['segmentation'], list) else []
            if seg and isinstance(seg, list) and len(seg) >= 6:  # Al menos 3 puntos (6 valores)
                points = [[seg[i], seg[i+1]] for i in range(0, len(seg), 2)]
                annotation_doc['points'] = points
                annotation_doc['type'] = 'polygon'
                annotation_doc['closed'] = True

        # Verificar duplicados antes de crear la anotación
        duplicate_result = check_annotation_duplicate_advanced(
            db, 
            image_id, 
            category_id, 
            category_doc.get('name', 'default') if category_doc else 'default', 
            bbox,
            iou_threshold=0.9  # Umbral más estricto para importaciones
        )
        
        if duplicate_result['is_duplicate']:
            print(f"⚠️ Anotación duplicada omitida (IoU: {duplicate_result['iou']:.3f})")
            continue  # Saltar esta anotación
        
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

def process_yolo_format(db, annotations_file, images_file, dataset_id, user_id):
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
            
            # Crear o encontrar categorías en el dataset actual
            for idx, class_name in enumerate(classes):
                existing = db.categories.find_one({
                    'name': class_name,
                    'dataset_id': dataset_id
                })
                
                if existing:
                    category_map[idx] = str(existing['_id'])
                else:
                    new_cat = {
                        'name': class_name,
                        'color': f"#{hash(class_name) & 0xFFFFFF:06x}",
                        'dataset_id': dataset_id,
                        'created_date': datetime.utcnow(),
                        'user_id': user_id  # Asociar categoría al usuario
                    }
                    result = db.categories.insert_one(new_cat)
                    category_map[idx] = str(result.inserted_id)
                    stats['categories'] += 1
        
        # Procesar archivos .txt de anotaciones
        # Buscar carpeta labels/ o usar la raíz
        labels_dir = os.path.join(temp_dir, 'labels')
        if not os.path.exists(labels_dir):
            labels_dir = temp_dir
        
        # Listar archivos de anotaciones
        if os.path.isdir(labels_dir):
            annotation_files = [f for f in os.listdir(labels_dir) 
                              if f.endswith('.txt') and f != 'classes.txt']
        else:
            annotation_files = []
        
        for filename in annotation_files:
            # Buscar imagen correspondiente en el dataset actual
            image_name = filename.replace('.txt', '')
            # Intentar con diferentes extensiones
            existing_img = None
            for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
                img_filename = image_name + ext
                # Buscar en el dataset especificado
                existing_img = db.images.find_one({
                    'filename': img_filename,
                    'dataset_id': dataset_id
                })
                if existing_img:
                    break
            
            if not existing_img:
                stats['errors'].append(f"Imagen no encontrada en el dataset para: {filename}")
                continue
            
            image_id = str(existing_img['_id'])
            image_width = existing_img['width']
            image_height = existing_img['height']
            stats['images'] += 1
            
            # Leer anotaciones YOLO
            with open(os.path.join(labels_dir, filename), 'r') as f:
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
                        'dataset_id': dataset_id,
                        'user_id': user_id  # Asociar anotación al usuario
                    }
                    
                    # Verificar duplicados antes de crear la anotación
                    category_id = category_map.get(class_id)
                    if category_id:
                        category_doc = db.categories.find_one({'_id': ObjectId(category_id)})
                        category_name = category_doc.get('name', 'default') if category_doc else 'default'
                        
                        duplicate_result = check_annotation_duplicate_advanced(
                            db, 
                            image_id, 
                            category_id, 
                            category_name, 
                            bbox,
                            iou_threshold=0.9  # Umbral más estricto para importaciones
                        )
                        
                        if duplicate_result['is_duplicate']:
                            print(f"⚠️ Anotación YOLO duplicada omitida (IoU: {duplicate_result['iou']:.3f})")
                            continue  # Saltar esta anotación
                    
                    db.annotations.insert_one(annotation_doc)
                    stats['annotations'] += 1
    
    return stats

def process_pascal_format(db, annotations_file, images_file, dataset_id, user_id):
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
        
        # Buscar archivos .xml recursivamente en todas las subcarpetas
        xml_files = []
        for root_dir, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.xml'):
                    xml_files.append(os.path.join(root_dir, file))
        
        print(f"Archivos XML encontrados: {len(xml_files)}")
        for xml_file in xml_files:
            print(f"  - {xml_file}")
        
        # Procesar archivos .xml
        for xml_path in xml_files:
            filename = os.path.basename(xml_path)
            
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                
                # Obtener nombre de la imagen
                image_filename = root.find('filename').text if root.find('filename') is not None else filename.replace('.xml', '.jpg')
                print(f"Buscando imagen: {image_filename} en dataset: {dataset_id}")
                
                # Buscar imagen en el dataset actual
                existing_img = db.images.find_one({
                    'filename': image_filename,
                    'dataset_id': dataset_id
                })
                if not existing_img:
                    stats['errors'].append(f"Imagen no encontrada en el dataset para: {image_filename}")
                    continue
                
                image_id = str(existing_img['_id'])
                stats['images'] += 1
                print(f"  ✓ Imagen encontrada: {image_filename}")
                
                # Procesar cada objeto anotado
                for obj in root.findall('object'):
                    name = obj.find('name').text
                    
                    # Crear o encontrar categoría en el dataset actual
                    if name not in category_map:
                        existing_cat = db.categories.find_one({
                            'name': name,
                            'dataset_id': dataset_id
                        })
                        
                        if existing_cat:
                            category_map[name] = str(existing_cat['_id'])
                        else:
                            new_cat = {
                                'name': name,
                                'color': f"#{hash(name) & 0xFFFFFF:06x}",
                                'dataset_id': dataset_id,
                                'created_date': datetime.utcnow(),
                                'user_id': user_id  # Asociar categoría al usuario
                            }
                            result = db.categories.insert_one(new_cat)
                            category_map[name] = str(result.inserted_id)
                            stats['categories'] += 1
                            print(f"Categoría creada: {name}")
                    
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
                        'dataset_id': dataset_id,
                        'user_id': user_id  # Asociar anotación al usuario
                    }
                    
                    # Verificar duplicados antes de crear la anotación
                    duplicate_result = check_annotation_duplicate_advanced(
                        db, 
                        image_id, 
                        category_map[name], 
                        name, 
                        bbox,
                        iou_threshold=0.8  # Umbral más estricto para importaciones
                    )
                    
                    if duplicate_result['is_duplicate']:
                        print(f"⚠️ Anotación Pascal duplicada omitida (IoU: {duplicate_result['iou']:.3f})")
                        continue  # Saltar esta anotación
                    
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

# ==================== FUNCIONES AUXILIARES PARA DIVISIÓN DE DATASET ====================

def split_dataset_random(images, train_pct, val_pct, test_pct):
    """
    Divide una lista de imágenes aleatoriamente en train/val/test
    según los porcentajes dados.
    """
    import random
    
    # 1. Barajar la lista de imágenes aleatoriamente
    random.shuffle(images)
    
    # 2. Calcular los puntos de corte
    total_images = len(images)
    train_count = int(total_images * (train_pct / 100))
    val_count = int(total_images * (val_pct / 100))
    
    # 3. Cortar la lista en tres partes
    train_images = images[0:train_count]
    val_images = images[train_count : train_count + val_count]
    test_images = images[train_count + val_count:] # El resto va a test
    
    print(f"División aleatoria: {len(train_images)} train, {len(val_images)} val, {len(test_images)} test")
    
    return train_images, val_images, test_images

def export_coco_format_with_split(dataset, train_images, val_images, test_images, 
                                   annotations, categories, include_images, db):
    """Exportar en formato COCO con división train/val/test"""
    from flask import Response
    import tempfile
    
    # Crear archivo ZIP
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Exportar cada conjunto
            for split_name, split_images in [('train', train_images), 
                                              ('val', val_images), 
                                              ('test', test_images)]:
                if not split_images:
                    continue
                
                # Filtrar anotaciones para este conjunto
                split_image_ids = [str(img['_id']) for img in split_images]
                split_annotations = [ann for ann in annotations 
                                    if ann['image_id'] in split_image_ids]
                
                # Crear estructura COCO para este conjunto
                coco_data = create_coco_structure(dataset, split_images, 
                                                 split_annotations, categories)
                
                # Guardar JSON
                zf.writestr(f'{split_name}/annotations.json', 
                           json.dumps(coco_data, indent=2))
                
                # Si incluye imágenes, agregarlas
                if include_images:
                    for img in split_images:
                        img_doc = db.images.find_one({'_id': ObjectId(img['_id'])})
                        if img_doc and 'data' in img_doc:
                            image_data = img_doc['data']
                            zf.writestr(f"{split_name}/images/{img['filename']}", 
                                       image_data)
        
        with open(temp_zip.name, 'rb') as f:
            zip_data = f.read()
        
        os.unlink(temp_zip.name)
        
        return Response(
            zip_data,
            mimetype='application/zip',
            headers={'Content-Disposition': f'attachment; filename={dataset["name"]}_coco_split.zip'}
        )
    except Exception as e:
        if os.path.exists(temp_zip.name):
            os.unlink(temp_zip.name)
        raise e

def create_coco_structure(dataset, images, annotations, categories):
    """Crea la estructura COCO JSON con soporte para videos"""
    coco_data = {
        'info': {
            'description': dataset.get('name', 'Dataset'),
            'date_created': datetime.utcnow().isoformat(),
            'version': '1.0',
            'supports_video': True
        },
        'videos': [],
        'images': [],
        'annotations': [],
        'categories': []
    }
    
    # Obtener videos del dataset
    db = get_db()
    dataset_id = str(dataset.get('_id'))
    user_id = dataset.get('user_id')
    
    # Obtener todos los video_ids únicos de las imágenes
    video_ids = set()
    for img in images:
        if 'video_id' in img and img['video_id']:
            video_ids.add(img['video_id'])
    
    # Mapear videos
    video_map = {}
    if video_ids:
        videos = list(db.videos.find({
            '_id': {'$in': [ObjectId(vid) if ObjectId.is_valid(vid) else vid for vid in video_ids]},
            'user_id': user_id
        }))
        
        for idx, video in enumerate(videos, start=1):
            video_id = idx
            video_map[str(video['_id'])] = video_id
            coco_data['videos'].append({
                'id': video_id,
                'file_name': video['filename'],
                'width': video.get('width', 0),
                'height': video.get('height', 0),
                'fps': video.get('fps', 0),
                'duration': video.get('duration', 0),
                'total_frames': video.get('total_frames', 0),
                'extracted_frames': video.get('extracted_frames', 0)
            })
    
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
        
        image_entry = {
            'id': img_id,
            'file_name': img['filename'],
            'width': img.get('width', 0),
            'height': img.get('height', 0),
            'date_captured': img.get('created_at', datetime.utcnow()).isoformat()
        }
        
        # Si la imagen es un frame de video, añadir información adicional
        if 'video_id' in img and img['video_id']:
            video_db_id = img['video_id']
            if video_db_id in video_map:
                image_entry['video_id'] = video_map[video_db_id]
                image_entry['frame_number'] = img.get('frame_number', 0)
                image_entry['timestamp'] = img.get('timestamp', 0)
        
        coco_data['images'].append(image_entry)
    
    # Mapear anotaciones
    for idx, ann in enumerate(annotations, start=1):
        image_id = image_map.get(ann['image_id'])
        category_id = category_map.get(ann['category_id'])
        
        if not image_id or not category_id:
            continue
        
        bbox = ann.get('bbox', [0, 0, 0, 0])
        
        # Si la anotación tiene puntos, es un polígono
        if 'points' in ann and ann['points'] and len(ann['points']) > 0:
            points = ann['points']
            segmentation = []
            for point in points:
                if len(point) >= 2:
                    segmentation.extend([point[0], point[1]])
            
            if segmentation and len(segmentation) >= 6:
                x_coords = [segmentation[i] for i in range(0, len(segmentation), 2)]
                y_coords = [segmentation[i] for i in range(1, len(segmentation), 2)]
                
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                
                bbox = [x_min, y_min, x_max - x_min, y_max - y_min]
                
                area = 0
                n = len(x_coords)
                for i in range(n):
                    j = (i + 1) % n
                    area += x_coords[i] * y_coords[j]
                    area -= x_coords[j] * y_coords[i]
                area = abs(area) / 2.0
            else:
                area = bbox[2] * bbox[3] if len(bbox) >= 4 else 0
                
            ann_data = {
                'id': idx,
                'image_id': image_id,
                'category_id': category_id,
                'bbox': bbox,
                'area': area,
                'segmentation': [segmentation],
                'iscrowd': 0
            }
        else:
            area = bbox[2] * bbox[3] if len(bbox) >= 4 else 0
            
            ann_data = {
                'id': idx,
                'image_id': image_id,
                'category_id': category_id,
                'bbox': bbox,
                'area': area,
                'iscrowd': 0
            }
            
            if 'segmentation' in ann and ann['segmentation']:
                ann_data['segmentation'] = ann['segmentation']
        
        coco_data['annotations'].append(ann_data)
    
    return coco_data

def export_yolo_format_with_split(dataset, train_images, val_images, test_images,
                                   annotations, categories, include_images, db):
    """Exportar en formato YOLO con división train/val/test"""
    from flask import Response
    import tempfile
    
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Crear archivo de clases
            classes_content = '\n'.join([cat['name'] for cat in categories])
            zf.writestr('classes.txt', classes_content)
            
            # Mapeo de categorías a índices
            category_map = {str(cat['_id']): idx for idx, cat in enumerate(categories)}
            
            # Exportar cada conjunto
            for split_name, split_images in [('train', train_images), 
                                              ('val', val_images), 
                                              ('test', test_images)]:
                if not split_images:
                    continue
                
                for img in split_images:
                    img_id = str(img['_id'])
                    img_annotations = [ann for ann in annotations if ann['image_id'] == img_id]
                    
                    # Crear archivo YOLO para esta imagen
                    yolo_lines = []
                    for ann in img_annotations:
                        cat_idx = category_map.get(ann['category_id'])
                        if cat_idx is None:
                            continue
                        
                        bbox = ann.get('bbox', [0, 0, 0, 0])
                        if len(bbox) < 4:
                            continue
                        
                        # Convertir bbox COCO [x, y, width, height] a YOLO [center_x, center_y, width, height] normalizado
                        img_width = img.get('width', 1)
                        img_height = img.get('height', 1)
                        
                        center_x = (bbox[0] + bbox[2] / 2) / img_width
                        center_y = (bbox[1] + bbox[3] / 2) / img_height
                        width = bbox[2] / img_width
                        height = bbox[3] / img_height
                        
                        yolo_lines.append(f"{cat_idx} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f}")
                    
                    # Guardar archivo de anotaciones
                    txt_filename = os.path.splitext(img['filename'])[0] + '.txt'
                    zf.writestr(f'{split_name}/labels/{txt_filename}', '\n'.join(yolo_lines))
                    
                    # Si incluye imágenes, agregarlas
                    if include_images:
                        img_doc = db.images.find_one({'_id': ObjectId(img['_id'])})
                        if img_doc and 'data' in img_doc:
                            image_data = img_doc['data']
                            zf.writestr(f"{split_name}/images/{img['filename']}", image_data)
        
        with open(temp_zip.name, 'rb') as f:
            zip_data = f.read()
        
        os.unlink(temp_zip.name)
        
        return Response(
            zip_data,
            mimetype='application/zip',
            headers={'Content-Disposition': f'attachment; filename={dataset["name"]}_yolo_split.zip'}
        )
    except Exception as e:
        if os.path.exists(temp_zip.name):
            os.unlink(temp_zip.name)
        raise e

def export_pascal_format_with_split(dataset, train_images, val_images, test_images,
                                     annotations, categories, include_images, db):
    """Exportar en formato Pascal VOC con división train/val/test"""
    from flask import Response
    import tempfile
    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom import minidom
    
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Mapeo de categorías
            category_map = {str(cat['_id']): cat['name'] for cat in categories}
            
            # Exportar cada conjunto
            for split_name, split_images in [('train', train_images), 
                                              ('val', val_images), 
                                              ('test', test_images)]:
                if not split_images:
                    continue
                
                for img in split_images:
                    img_id = str(img['_id'])
                    img_annotations = [ann for ann in annotations if ann['image_id'] == img_id]
                    
                    # Crear XML Pascal VOC
                    annotation = Element('annotation')
                    
                    folder = SubElement(annotation, 'folder')
                    folder.text = split_name
                    
                    filename = SubElement(annotation, 'filename')
                    filename.text = img['filename']
                    
                    size = SubElement(annotation, 'size')
                    width = SubElement(size, 'width')
                    width.text = str(img.get('width', 0))
                    height = SubElement(size, 'height')
                    height.text = str(img.get('height', 0))
                    depth = SubElement(size, 'depth')
                    depth.text = '3'
                    
                    for ann in img_annotations:
                        cat_name = category_map.get(ann['category_id'], 'unknown')
                        bbox = ann.get('bbox', [0, 0, 0, 0])
                        
                        obj = SubElement(annotation, 'object')
                        name = SubElement(obj, 'name')
                        name.text = cat_name
                        
                        bndbox = SubElement(obj, 'bndbox')
                        xmin = SubElement(bndbox, 'xmin')
                        xmin.text = str(int(bbox[0]))
                        ymin = SubElement(bndbox, 'ymin')
                        ymin.text = str(int(bbox[1]))
                        xmax = SubElement(bndbox, 'xmax')
                        xmax.text = str(int(bbox[0] + bbox[2]))
                        ymax = SubElement(bndbox, 'ymax')
                        ymax.text = str(int(bbox[1] + bbox[3]))
                    
                    # Convertir a string XML formateado
                    xml_str = minidom.parseString(tostring(annotation)).toprettyxml(indent='  ')
                    
                    # Guardar XML
                    xml_filename = os.path.splitext(img['filename'])[0] + '.xml'
                    zf.writestr(f'{split_name}/annotations/{xml_filename}', xml_str)
                    
                    # Si incluye imágenes, agregarlas
                    if include_images:
                        img_doc = db.images.find_one({'_id': ObjectId(img['_id'])})
                        if img_doc and 'data' in img_doc:
                            image_data = img_doc['data']
                            zf.writestr(f"{split_name}/images/{img['filename']}", image_data)
        
        with open(temp_zip.name, 'rb') as f:
            zip_data = f.read()
        
        os.unlink(temp_zip.name)
        
        return Response(
            zip_data,
            mimetype='application/zip',
            headers={'Content-Disposition': f'attachment; filename={dataset["name"]}_pascal_split.zip'}
        )
    except Exception as e:
        if os.path.exists(temp_zip.name):
            os.unlink(temp_zip.name)
        raise e

# ==================== ENDPOINTS PARA EXPORTAR ANOTACIONES ====================

@app.route('/api/annotations/export/<dataset_id>', methods=['GET'])
@token_required
def export_annotations(current_user_id, dataset_id):
    """Exportar anotaciones en diferentes formatos (COCO, YOLO, PascalVOC)"""
    try:
        db = get_db()
        
        # Verificar que el dataset pertenece al usuario
        dataset = db.datasets.find_one({
            '_id': ObjectId(dataset_id),
            'user_id': current_user_id
        })
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado o no autorizado'}), 403
        
        # Obtener parámetros
        export_format = request.args.get('format', 'coco')  # coco, yolo, pascal
        include_images = request.args.get('include_images', 'false').lower() == 'true'
        only_annotated = request.args.get('only_annotated', 'true').lower() == 'true'
        enable_split = request.args.get('enable_split', 'false').lower() == 'true'
        train_percentage = float(request.args.get('train_percentage', 80))
        val_percentage = float(request.args.get('val_percentage', 10))
        test_percentage = float(request.args.get('test_percentage', 10))
        
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
        
        # Si está habilitada la división, dividir las imágenes
        if enable_split:
            train_images, val_images, test_images = split_dataset_random(
                images, train_percentage, val_percentage, test_percentage
            )
            print(f"División: {len(train_images)} train, {len(val_images)} val, {len(test_images)} test")
            
            if export_format == 'coco':
                return export_coco_format_with_split(
                    dataset, train_images, val_images, test_images, 
                    annotations, categories, include_images, db
                )
            elif export_format == 'yolo':
                return export_yolo_format_with_split(
                    dataset, train_images, val_images, test_images,
                    annotations, categories, include_images, db
                )
            elif export_format == 'pascal':
                return export_pascal_format_with_split(
                    dataset, train_images, val_images, test_images,
                    annotations, categories, include_images, db
                )
        else:
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
@token_required
def get_export_statistics(current_user_id, dataset_id):
    """Obtener estadísticas de exportación sin realizar la exportación"""
    try:
        db = get_db()
        
        # Verificar que el dataset pertenece al usuario
        dataset = db.datasets.find_one({
            '_id': ObjectId(dataset_id),
            'user_id': current_user_id
        })
        if not dataset:
            return jsonify({'error': 'Dataset no encontrado o no autorizado'}), 403
        
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
    """Exportar en formato COCO JSON con soporte para videos"""
    from flask import Response
    import tempfile
    
    # Crear estructura COCO extendida con videos
    coco_data = {
        'info': {
            'description': dataset.get('name', 'Dataset'),
            'date_created': datetime.utcnow().isoformat(),
            'version': '1.0',
            'supports_video': True
        },
        'videos': [],
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
    
    # Obtener videos del dataset
    db = get_db()
    dataset_id = str(dataset.get('_id'))
    user_id = dataset.get('user_id')
    videos = list(db.videos.find({'dataset_id': dataset_id, 'user_id': user_id}))
    
    # Mapear videos
    video_map = {}
    for idx, video in enumerate(videos, start=1):
        video_id = idx
        video_map[str(video['_id'])] = video_id
        coco_data['videos'].append({
            'id': video_id,
            'file_name': video['filename'],
            'width': video.get('width', 0),
            'height': video.get('height', 0),
            'fps': video.get('fps', 0),
            'duration': video.get('duration', 0),
            'total_frames': video.get('total_frames', 0),
            'extracted_frames': video.get('extracted_frames', 0)
        })
    
    # Mapear imágenes (incluyendo frames de video)
    image_map = {}
    for idx, img in enumerate(images, start=1):
        img_id = idx
        image_map[str(img['_id'])] = img_id
        
        image_entry = {
            'id': img_id,
            'file_name': img['filename'],
            'width': img.get('width', 0),
            'height': img.get('height', 0),
            'date_captured': img.get('created_at', datetime.utcnow()).isoformat()
        }
        
        # Si la imagen es un frame de video, añadir información adicional
        if 'video_id' in img and img['video_id']:
            video_db_id = img['video_id']
            if video_db_id in video_map:
                image_entry['video_id'] = video_map[video_db_id]
                image_entry['frame_number'] = img.get('frame_number', 0)
                image_entry['timestamp'] = img.get('timestamp', 0)
        
        coco_data['images'].append(image_entry)
    
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

# ==================== RUTAS PARA HERRAMIENTAS DE IA ====================

import yaml
import shutil

# Variable global para almacenar el modelo cargado
loaded_model = None
loaded_model_id = None
model_name = None
model_categories = []

# Directorio permanente para modelos guardados
MODELS_DIR = os.path.join(os.getcwd(), 'ai_models')
os.makedirs(MODELS_DIR, exist_ok=True)

# Archivo de configuración para modelos precargados
PRELOADED_MODELS_CONFIG = os.path.join(MODELS_DIR, 'preloaded_models.json')

def ensure_preloaded_models():
    """
    Asegura que los modelos precargados estén registrados en la base de datos.
    Lee el archivo preloaded_models.json y registra los modelos si existen.
    """
    if not os.path.exists(PRELOADED_MODELS_CONFIG):
        return
    
    try:
        with open(PRELOADED_MODELS_CONFIG, 'r', encoding='utf-8') as f:
            preloaded_config = json.load(f)
    except Exception as e:
        print(f"Error al leer preloaded_models.json: {e}")
        return
    
    if not isinstance(preloaded_config, list):
        print("El archivo preloaded_models.json debe contener una lista de modelos")
        return
    
    db = get_db()
    
    for model_config in preloaded_config:
        try:
            name = model_config.get('name')
            file_name = model_config.get('model_file')
            
            if not name or not file_name:
                continue
            
            # Construir ruta completa del archivo
            if os.path.isabs(file_name):
                model_path = file_name
            else:
                model_path = os.path.join(MODELS_DIR, file_name)
            
            # Verificar que el archivo exista
            if not os.path.exists(model_path):
                print(f"Modelo precargado no encontrado: {model_path}")
                continue
            
            # Verificar si ya existe en la base de datos
            existing_model = db.ai_models.find_one({'file_path': model_path})
            
            # Procesar archivo YAML si existe
            yaml_path = model_config.get('yaml_file')
            if yaml_path:
                if not os.path.isabs(yaml_path):
                    yaml_path = os.path.join(MODELS_DIR, yaml_path)
                if not os.path.exists(yaml_path):
                    yaml_path = None
            
            # Obtener categorías
            categories = model_config.get('categories', [])
            if not categories and yaml_path:
                try:
                    with open(yaml_path, 'r', encoding='utf-8') as yf:
                        yaml_data = yaml.safe_load(yf)
                        if 'names' in yaml_data:
                            if isinstance(yaml_data['names'], dict):
                                categories = list(yaml_data['names'].values())
                            else:
                                categories = yaml_data['names']
                except Exception as e:
                    print(f"Error leyendo YAML para {name}: {e}")
            
            if existing_model:
                # Actualizar modelo existente para marcarlo como precargado
                db.ai_models.update_one(
                    {'_id': existing_model['_id']},
                    {'$set': {
                        'is_preloaded': True,
                        'name': name,
                        'description': model_config.get('description', existing_model.get('description', '')),
                        'categories': categories or existing_model.get('categories', [])
                    }}
                )
            else:
                # Crear nuevo modelo
                import uuid
                model_uuid = model_config.get('uuid', str(uuid.uuid4()))
                
                model_doc = {
                    'name': name,
                    'description': model_config.get('description', name),
                    'file_path': model_path,
                    'yaml_path': yaml_path,
                    'categories': categories,
                    'uuid': model_uuid,
                    'created_at': model_config.get('created_at', datetime.now().isoformat()),
                    'file_size': os.path.getsize(model_path),
                    'original_filename': os.path.basename(model_path),
                    'is_preloaded': True
                }
                
                db.ai_models.insert_one(model_doc)
                print(f"Modelo precargado registrado: {name}")
        
        except Exception as e:
            print(f"Error procesando modelo precargado {model_config}: {e}")

# Inicializar modelos precargados al importar el módulo
try:
    ensure_preloaded_models()
    print("Modelos precargados inicializados")
except Exception as e:
    print(f"Error al inicializar modelos precargados: {e}")

def _generate_color_not_in_set(used_colors_set):
    """
    Genera un color único que NO está en el set proporcionado.
    
    Args:
        used_colors_set: Un set de colores (en mayúsculas) que ya están en uso.
    
    Returns:
        String con el color en formato hexadecimal.
    """
    # Lista extendida de colores predefinidos
    predefined_colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', 
        '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9', '#F8B500', '#FF69B4',
        '#32CD32', '#FF4500', '#8A2BE2', '#00CED1', '#FFD700', '#DC143C',
        '#00FF7F', '#FF1493', '#1E90FF', '#FF8C00', '#9370DB', '#00FA9A',
        '#FF6347', '#40E0D0', '#DA70D6', '#00BFFF', '#FFA500', '#BA55D3',
        '#7FFF00', '#FF69B4', '#6495ED', '#FF7F50', '#9932CC', '#00FFFF'
    ]
    
    # 1. Buscar un color disponible de la lista predefinida
    for color in predefined_colors:
        if color.upper() not in used_colors_set:
            return color # Devuelve el color
    
    # 2. Si todos están en uso, generar uno aleatorio único
    import random
    import colorsys
    
    max_attempts = 100
    for _ in range(max_attempts):
        hue = random.random()
        saturation = 0.7 + random.random() * 0.3 # Entre 0.7 y 1.0
        value = 0.8 + random.random() * 0.2      # Entre 0.8 y 1.0
        
        rgb = colorsys.hsv_to_rgb(hue, saturation, value)
        hex_color = '#%02X%02X%02X' % (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
        
        if hex_color.upper() not in used_colors_set:
            return hex_color
    
    # 3. Como último recurso, usar un color base con timestamp
    import time
    timestamp = int(time.time()) % 1000000
    fallback_color = f'#{timestamp:06X}'
    
    # Asegurarse de que incluso el fallback sea único
    while fallback_color.upper() in used_colors_set:
        timestamp += 1
        fallback_color = f'#{(timestamp % 1000000):06X}'
        
    return fallback_color

def ensure_model_categories_exist(dataset_id, model_categories, user_id=None):
    """
    Asegurar que las categorías del modelo existan en la base de datos.
    Si no existen, las crea automáticamente con colores únicos.
    (Versión corregida para evitar colores duplicados en la misma ejecución)
    
    Args:
        dataset_id: ID del dataset
        model_categories: Lista de nombres de categorías del modelo
        
    Returns:
        Lista de categorías creadas
    """
    db = get_db()
    created_categories = []
    
    # 1. Obtener TODAS las categorías existentes y sus colores de UNA SOLA VEZ
    existing_categories_list = list(db.categories.find({'dataset_id': dataset_id}))

    # Si recibimos categorías sin user_id (legacy) y conocemos el usuario, actualizarlas
    if user_id:
        for cat in existing_categories_list:
            if not cat.get('user_id'):
                db.categories.update_one({'_id': cat['_id']}, {'$set': {'user_id': user_id}})
                cat['user_id'] = user_id
    
    # 2. Crear un mapa de nombres para búsquedas rápidas en memoria
    existing_names_map = {cat['name']: cat for cat in existing_categories_list}
    
    # 3. Crear un set de colores ya en uso (normalizados a mayúsculas)
    used_colors = set()
    for cat in existing_categories_list:
        if 'color' in cat and cat['color']:
            used_colors.add(cat['color'].upper())
    
    print(f"Colores ya en uso para dataset {dataset_id}: {used_colors}")

    # 4. Iterar sobre las categorías del modelo
    for category_name in model_categories:
        
        # 5. Verificar si ya existe usando el mapa en memoria
        if category_name not in existing_names_map:
            
            # 6. Generar un color único usando el set actualizado
            # (Usamos la NUEVA función auxiliar)
            color = _generate_color_not_in_set(used_colors)
            
            # 7. AÑADIR el nuevo color al set INMEDIATAMENTE
            # Esto es clave para que la siguiente iteración no lo repita
            used_colors.add(color.upper())
            
            print(f"Generando nueva categoría '{category_name}' con color {color}")
            
            # Crear nueva categoría
            category_doc = {
                'name': category_name,
                'color': color,
                'dataset_id': dataset_id,
                'created_date': datetime.utcnow(),
                'creator': 'ai_model' # Marcar que fue creada por un modelo de IA
            }

            if user_id:
                category_doc['user_id'] = user_id
            
            result = db.categories.insert_one(category_doc)
            category_doc['_id'] = str(result.inserted_id)
            category_doc['id'] = category_doc['_id']
            created_categories.append(category_doc)
            
            # 8. Añadir la categoría recién creada al mapa
            # para evitar que se cree de nuevo si el nombre está duplicado
            # en la lista `model_categories`
            existing_names_map[category_name] = category_doc
    
    return created_categories

def get_category_mapping(dataset_id, model_categories):
    """
    Obtener el mapeo entre índices de categorías del modelo y IDs de categorías en la base de datos.
    
    Args:
        dataset_id: ID del dataset
        model_categories: Lista de nombres de categorías del modelo
        
    Returns:
        Dict con mapeo {índice_modelo: categoria_id_db}
    """
    db = get_db()
    mapping = {}
    
    for idx, category_name in enumerate(model_categories):
        category = db.categories.find_one({
            'name': category_name,
            'dataset_id': dataset_id
        })
        
        if category:
            mapping[idx] = str(category['_id'])
    
    return mapping

@app.route('/api/ai/saved-models', methods=['GET'])
@token_required
def get_saved_models(current_user_id):
    """Obtener lista de modelos guardados, separados por tipo"""
    try:
        db = get_db()
        # Obtener modelos del usuario actual o modelos precargados (compartidos)
        models = list(db.ai_models.find({
            '$or': [
                {'user_id': current_user_id},
                {'is_preloaded': True}
            ]
        }))
        
        preloaded_models = []
        custom_models = []
        
        for model in models:
            model['_id'] = str(model['_id'])
            model['id'] = model['_id']
            model['is_preloaded'] = model.get('is_preloaded', False)
            model['can_delete'] = not model['is_preloaded']
            
            if model['is_preloaded']:
                preloaded_models.append(model)
            else:
                custom_models.append(model)
        
        return jsonify({
            'success': True,
            'models': models,
            'preloaded': preloaded_models,
            'custom': custom_models
        })
    except Exception as e:
        return jsonify({'error': f'Error al obtener modelos: {str(e)}'}), 500

@app.route('/api/ai/load-saved-model', methods=['POST'])
@token_required
def load_saved_model(current_user_id):
    """Cargar un modelo previamente guardado y crear sus categorías en el dataset"""
    global loaded_model, loaded_model_id, model_name, model_categories
    
    try:
        data = request.get_json()
        model_id = data.get('model_id')
        dataset_id = data.get('dataset_id')  # Dataset ID para crear categorías
        
        if not model_id:
            return jsonify({'error': 'ID de modelo requerido'}), 400
        
        # Importar YOLO solo cuando sea necesario
        from ultralytics import YOLO
        
        db = get_db()
        
        # Verificar que el modelo pertenece al usuario o es precargado
        model_doc = db.ai_models.find_one({
            '_id': ObjectId(model_id),
            '$or': [
                {'user_id': current_user_id},
                {'is_preloaded': True}
            ]
        })
        
        if not model_doc:
            return jsonify({'error': 'Modelo no encontrado o no autorizado'}), 403
        
        # Cargar el modelo desde el archivo guardado
        model_path = model_doc['file_path']
        if not os.path.exists(model_path):
            return jsonify({'error': 'Archivo de modelo no encontrado'}), 404
        
        loaded_model = YOLO(model_path)
        model_name = model_doc['name']
        model_categories = model_doc['categories']
        loaded_model_id = str(model_doc['_id'])
        
        # Crear categorías del modelo en el dataset si se proporciona dataset_id
        created_categories = []
        if dataset_id:
            created_categories = ensure_model_categories_exist(dataset_id, model_categories, current_user_id)
        
        return jsonify({
            'success': True,
            'message': f'Modelo "{model_name}" cargado exitosamente',
            'categories': model_categories,
            'created_categories': [serialize_doc(cat) for cat in created_categories],
            'model_info': {
                'id': str(model_doc['_id']),
                'name': model_doc['name'],
                'description': model_doc.get('description', ''),
                'created_at': model_doc.get('created_at', ''),
                'is_preloaded': model_doc.get('is_preloaded', False)
            }
        })
        
    except Exception as e:
        print(f"Error al cargar modelo guardado: {e}")
        return jsonify({'error': f'Error al cargar modelo: {str(e)}'}), 500

@app.route('/api/ai/load-model', methods=['POST'])
@token_required
def load_ai_model(current_user_id):
    """Cargar un modelo YOLO para inferencia y guardarlo en la base de datos"""
    global loaded_model, loaded_model_id, model_name, model_categories
    
    try:
        # Importar YOLO solo cuando sea necesario
        from ultralytics import YOLO
        
        # Verificar que se envió un archivo de modelo
        if 'model_file' not in request.files:
            return jsonify({'error': 'No se encontró archivo de modelo'}), 400
        
        model_file = request.files['model_file']
        if model_file.filename == '':
            return jsonify({'error': 'No se seleccionó archivo de modelo'}), 400
        
        # Obtener información del formulario
        submitted_name = request.form.get('model_name', 'Modelo sin nombre')
        description = request.form.get('description', f'Modelo {submitted_name}')
        dataset_id = request.form.get('dataset_id')  # Dataset ID opcional para crear categorías
        
        # Crear directorio permanente para este modelo
        import uuid
        model_uuid = str(uuid.uuid4())
        model_dir = os.path.join(MODELS_DIR, model_uuid)
        os.makedirs(model_dir, exist_ok=True)
        
        # Guardar archivo del modelo permanentemente
        model_filename = f"{submitted_name.replace(' ', '_')}.pt"
        permanent_model_path = os.path.join(model_dir, model_filename)
        model_file.save(permanent_model_path)
        
        # Cargar el modelo YOLO para obtener información
        loaded_model = YOLO(permanent_model_path)
        model_name = submitted_name
        
        # Intentar cargar categorías desde archivo YAML si se proporciona
        yaml_path = None
        model_categories = []
        
        if 'yaml_file' in request.files and request.files['yaml_file'].filename != '':
            yaml_file = request.files['yaml_file']
            yaml_path = os.path.join(model_dir, 'config.yaml')
            yaml_file.save(yaml_path)
            
            try:
                with open(yaml_path, 'r') as f:
                    yaml_data = yaml.safe_load(f)
                    if 'names' in yaml_data:
                        model_categories = list(yaml_data['names'].values()) if isinstance(yaml_data['names'], dict) else yaml_data['names']
                    else:
                        model_categories = []
            except Exception as e:
                print(f"Error al leer archivo YAML: {e}")
                model_categories = []
        
        # Si aún no hay categorías, intentar obtenerlas del modelo
        if not model_categories:
            try:
                # Algunos modelos YOLO tienen información de clases
                if hasattr(loaded_model, 'names'):
                    model_categories = list(loaded_model.names.values())
                else:
                    # Intentar determinar el número de clases del modelo
                    num_classes = getattr(loaded_model.model, 'nc', None) if hasattr(loaded_model, 'model') else None
                    if num_classes:
                        model_categories = [f'Clase_{i}' for i in range(num_classes)]
                    else:
                        # Si no se puede determinar, usar una clase genérica
                        model_categories = ['Objeto_detectado']
            except Exception as e:
                print(f"Error al obtener categorías del modelo: {e}")
                # Fallback genérico sin asumir tipo de modelo
                model_categories = ['Objeto_detectado']
        
        # Guardar información del modelo en la base de datos
        db = get_db()
        model_doc = {
            'name': submitted_name,
            'description': description,
            'file_path': permanent_model_path,
            'yaml_path': yaml_path,
            'categories': model_categories,
            'uuid': model_uuid,
            'created_at': datetime.now().isoformat(),
            'file_size': os.path.getsize(permanent_model_path),
            'original_filename': model_file.filename,
            'is_preloaded': False,
            'user_id': current_user_id  # Asociar modelo al usuario
        }
        
        result = db.ai_models.insert_one(model_doc)
        model_doc['_id'] = str(result.inserted_id)
        loaded_model_id = str(result.inserted_id)
        
        # Crear categorías del modelo en el dataset si se proporciona dataset_id
        created_categories = []
        if dataset_id:
            created_categories = ensure_model_categories_exist(dataset_id, model_categories, current_user_id)
        
        return jsonify({
            'success': True,
            'message': f'Modelo "{model_name}" cargado y guardado exitosamente',
            'categories': model_categories,
            'created_categories': [serialize_doc(cat) for cat in created_categories],
            'model_info': {
                'id': str(result.inserted_id),
                'name': submitted_name,
                'description': description,
                'uuid': model_uuid
            }
        })
        
    except Exception as e:
        print(f"Error al cargar modelo: {e}")
        # Limpiar archivos si hubo error
        try:
            if 'model_dir' in locals() and os.path.exists(model_dir):
                shutil.rmtree(model_dir)
        except:
            pass
        
        loaded_model = None
        model_name = None
        model_categories = []
        return jsonify({'error': f'Error al cargar el modelo: {str(e)}'}), 500

@app.route('/api/ai/unload-model', methods=['POST'])
@token_required
def unload_ai_model(current_user_id):
    """Descargar el modelo actual"""
    global loaded_model, loaded_model_id, model_name, model_categories
    
    try:
        loaded_model = None
        loaded_model_id = None
        model_name = None
        model_categories = []
        
        # Limpiar archivos temporales
        temp_dir = '/tmp/ai_models'
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
        
        return jsonify({'success': True, 'message': 'Modelo descargado exitosamente'})
        
    except Exception as e:
        return jsonify({'error': f'Error al descargar modelo: {str(e)}'}), 500

@app.route('/api/ai/models/<model_id>', methods=['DELETE'])
@token_required
def delete_ai_model(current_user_id, model_id):
    """Eliminar un modelo personalizado (no precargado)"""
    global loaded_model, loaded_model_id, model_name, model_categories
    
    try:
        if not ObjectId.is_valid(model_id):
            return jsonify({'error': 'ID de modelo inválido'}), 400
        
        db = get_db()
        
        # Verificar que el modelo pertenece al usuario y no es precargado
        model_doc = db.ai_models.find_one({
            '_id': ObjectId(model_id),
            'user_id': current_user_id
        })
        
        if not model_doc:
            return jsonify({'error': 'Modelo no encontrado o no autorizado'}), 403
        
        # No permitir eliminar modelos precargados
        if model_doc.get('is_preloaded', False):
            return jsonify({'error': 'No se pueden eliminar modelos precargados'}), 403
        
        # Eliminar modelo de la base de datos
        result = db.ai_models.delete_one({'_id': ObjectId(model_id), 'user_id': current_user_id})
        
        if result.deleted_count == 0:
            return jsonify({'error': 'No se pudo eliminar el modelo'}), 500
        
        # Eliminar archivos físicos si existen
        try:
            # Intentar eliminar por UUID (carpeta completa)
            if model_doc.get('uuid'):
                model_folder = os.path.join(MODELS_DIR, model_doc['uuid'])
                if os.path.exists(model_folder):
                    shutil.rmtree(model_folder)
                    print(f"Carpeta del modelo eliminada: {model_folder}")
            else:
                # Fallback: eliminar archivo individual
                model_path = model_doc.get('file_path')
                if model_path and os.path.exists(model_path):
                    os.remove(model_path)
                    print(f"Archivo de modelo eliminado: {model_path}")
        except Exception as file_error:
            print(f"Error al eliminar archivos del modelo {model_id}: {file_error}")
            # No fallar la operación si solo hay error al eliminar archivos
        
        # Si el modelo eliminado es el que está cargado, descargarlo
        if loaded_model_id == str(model_doc['_id']):
            loaded_model = None
            loaded_model_id = None
            model_name = None
            model_categories = []
        
        return jsonify({
            'success': True,
            'message': f'Modelo "{model_doc["name"]}" eliminado exitosamente'
        })
        
    except Exception as e:
        print(f"Error al eliminar modelo: {e}")
        return jsonify({'error': f'Error al eliminar modelo: {str(e)}'}), 500

@app.route('/api/ai/predict', methods=['POST'])
@token_required
def predict_image(current_user_id):
    """Realizar predicción en una imagen usando el modelo cargado"""
    global loaded_model, model_categories
    
    try:
        if loaded_model is None:
            return jsonify({'error': 'No hay modelo cargado'}), 400
        
        data = request.get_json()
        image_id = data.get('image_id')
        confidence = data.get('confidence', 0.5)
        
        if not image_id:
            return jsonify({'error': 'ID de imagen requerido'}), 400
        
        # Obtener imagen de la base de datos y verificar propiedad
        db = get_db()
        image_doc = db.images.find_one({'_id': ObjectId(image_id), 'user_id': current_user_id})
        
        if not image_doc:
            return jsonify({'error': 'Imagen no encontrada o no autorizada'}), 403
        
        # Verificar que la imagen tenga dataset_id
        dataset_id = image_doc.get('dataset_id')
        if not dataset_id:
            return jsonify({'error': 'La imagen debe pertenecer a un dataset para realizar predicciones'}), 400
        
        # Crear automáticamente las categorías del modelo si no existen
        created_categories = ensure_model_categories_exist(dataset_id, model_categories, current_user_id)
        
        # Obtener el mapeo de categorías del modelo a IDs de base de datos
        category_mapping = get_category_mapping(dataset_id, model_categories)
        
        # Crear imagen PIL desde los datos
        image_data = None
        if 'data' in image_doc:
            # Los datos pueden estar en formato base64 o como bytes
            data = image_doc['data']
            if isinstance(data, str):
                # Si es string, podría ser base64
                try:
                    image_data = base64.b64decode(data)
                except:
                    return jsonify({'error': 'Formato de imagen inválido en base de datos'}), 400
            else:
                # Si ya son bytes
                image_data = data
        else:
            # Si la imagen está en el sistema de archivos
            image_path = os.path.join('/app/images', image_doc.get('path', ''))
            if not os.path.exists(image_path):
                return jsonify({'error': 'Archivo de imagen no encontrado'}), 404
            
            with open(image_path, 'rb') as f:
                image_data = f.read()
        
        if image_data is None:
            return jsonify({'error': 'No se pudieron obtener los datos de la imagen'}), 400
        
        # Convertir a imagen PIL
        try:
            image = Image.open(io.BytesIO(image_data))
            # Asegurar que la imagen esté en modo RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')
        except Exception as e:
            return jsonify({'error': f'Error al procesar la imagen: {str(e)}'}), 400
        
        # Realizar predicción
        try:
            print(f"Realizando predicción con confianza: {confidence}")
            results = loaded_model(image, conf=confidence)
            print(f"Predicción completada, {len(results)} resultados obtenidos")
        except Exception as e:
            print(f"Error durante la predicción: {e}")
            return jsonify({'error': f'Error durante la predicción: {str(e)}'}), 500
        
        # Procesar resultados y guardar como anotaciones
        detections = []
        created_annotations = []
        
        if len(results) > 0:
            result = results[0]  # Tomar el primer resultado
            print(f"Procesando resultado: {type(result)}")
            
            if result.boxes is not None:
                boxes = result.boxes
                print(f"Encontradas {len(boxes)} cajas")
                
                for i in range(len(boxes)):
                    try:
                        # Obtener coordenadas del bounding box (xyxy format)
                        box = boxes.xyxy[i].cpu().numpy()
                        conf = boxes.conf[i].cpu().numpy()
                        cls = int(boxes.cls[i].cpu().numpy())
                        
                        # Convertir a formato [x, y, width, height]
                        x1, y1, x2, y2 = box
                        bbox = [float(x1), float(y1), float(x2 - x1), float(y2 - y1)]
                        
                        # Obtener el ID de categoría correspondiente
                        category_id = category_mapping.get(cls)
                        category_name = model_categories[cls] if cls < len(model_categories) else f'Clase {cls}'
                        
                        if not category_id:
                            print(f"No se encontró categoría para clase {cls}, saltando detección")
                            continue
                        
                        detection = {
                            'bbox': bbox,
                            'confidence': float(conf),
                            'class': cls,
                            'category_id': category_id,
                            'category_name': category_name
                        }
                        
                        # Crear anotación en la base de datos
                        annotation_doc = {
                            'image_id': image_id,
                            'type': 'bbox',
                            'category': category_name,
                            'category_id': category_id,
                            'bbox': bbox,
                            'original_bbox': bbox,  # Guardar bbox original para detectar duplicados después de escalado
                            'area': bbox[2] * bbox[3],  # width * height
                            'stroke': '#00ff00',  # Color por defecto para predicciones
                            'strokeWidth': 2,
                            'fill': 'rgba(0,255,0,0.2)',
                            'confidence': float(conf),
                            'source': 'ai_prediction',  # Marcar como predicción de IA
                            'model_name': model_name,
                            'created_date': datetime.utcnow(),
                            'modified_date': datetime.utcnow(),
                            'user_id': current_user_id  # Asociar anotación al usuario
                        }
                        
                        # Verificar duplicados antes de crear la anotación
                        duplicate_result = check_annotation_duplicate_advanced(
                            db, 
                            image_id, 
                            category_id, 
                            category_name, 
                            bbox,
                            iou_threshold=0.90  # 90% de solapamiento
                        )
                        
                        if duplicate_result['is_duplicate']:
                            print(f"Detección {i}: duplicado detectado (IoU: {duplicate_result['iou']:.3f}), saltando...")
                            # Agregar a detecciones pero marcar como duplicado
                            detection['is_duplicate'] = True
                            detection['existing_annotation_id'] = duplicate_result['existing_annotation']['_id']
                            detections.append(detection)
                            continue
                        
                        # Insertar anotación en MongoDB
                        annotation_result = db.annotations.insert_one(annotation_doc)
                        annotation_doc['_id'] = str(annotation_result.inserted_id)
                        created_annotations.append(serialize_doc(annotation_doc))
                        
                        print(f"Detección {i}: clase={cls} ({category_name}), confianza={conf:.3f}, bbox={bbox}, anotación creada con ID={annotation_doc['_id']}")
                        detection['is_duplicate'] = False
                        detections.append(detection)
                        
                    except Exception as e:
                        print(f"Error procesando detección {i}: {e}")
                        continue
            else:
                print("No se encontraron boxes en el resultado")
        
        # Estadísticas de duplicados
        duplicates_count = len([d for d in detections if d.get('is_duplicate', False)])
        created_count = len(created_annotations)
        total_detections = len(detections)
        
        return jsonify({
            'success': True,
            'detections': detections,
            'annotations': created_annotations,
            'model_name': model_name,
            'categories': model_categories,
            'created_categories': [serialize_doc(cat) for cat in created_categories],
            'total_detections': total_detections,
            'total_annotations_created': created_count,
            'duplicates_skipped': duplicates_count,
            'message': f'Predicción completada. Se crearon {created_count} anotaciones nuevas de {total_detections} detecciones. {duplicates_count} duplicados omitidos.'
        })
        
    except Exception as e:
        print(f"Error en predicción: {e}")
        return jsonify({'error': f'Error en la predicción: {str(e)}'}), 500

@app.route('/api/ai/model-status', methods=['GET'])
@token_required
def get_model_status(current_user_id):
    """Obtener estado actual del modelo"""
    global loaded_model, model_name, model_categories
    
    return jsonify({
        'is_loaded': loaded_model is not None,
        'model_name': model_name,
        'categories': model_categories
    })

@app.route('/api/ai/test-image', methods=['POST'])
@token_required
def test_image_processing(current_user_id):
    """Endpoint para probar el procesamiento de imágenes sin predicción"""
    try:
        data = request.get_json()
        image_id = data.get('image_id')
        
        if not image_id:
            return jsonify({'error': 'ID de imagen requerido'}), 400
        
        # Obtener imagen de la base de datos y verificar propiedad
        db = get_db()
        image_doc = db.images.find_one({'_id': ObjectId(image_id), 'user_id': current_user_id})
        
        if not image_doc:
            return jsonify({'error': 'Imagen no encontrada o no autorizada'}), 403
        
        # Información de debug sobre la imagen
        info = {
            'has_data_field': 'data' in image_doc,
            'has_path_field': 'path' in image_doc,
            'filename': image_doc.get('filename', 'Unknown'),
            'data_type': str(type(image_doc.get('data', None))),
        }
        
        if 'data' in image_doc:
            data_field = image_doc['data']
            if isinstance(data_field, str):
                info['data_length'] = len(data_field)
                info['data_sample'] = data_field[:50] + '...' if len(data_field) > 50 else data_field
            else:
                info['data_length'] = len(data_field) if hasattr(data_field, '__len__') else 'Unknown'
        
        return jsonify({
            'success': True,
            'image_info': info
        })
        
    except Exception as e:
        return jsonify({'error': f'Error al procesar imagen: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

