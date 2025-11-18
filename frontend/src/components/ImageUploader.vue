<template>
  <div class="uploader">
    <div class="upload-area" @dragover.prevent="dragover = true" 
         @dragleave="dragover = false" @drop.prevent="handleDrop"
         :class="{ 'dragover': dragover, 'uploading': uploading }">
      <input type="file" ref="fileInput" @change="handleFileChange" accept="image/*,video/*,.zip" multiple hidden>
      
      <!-- Estado de carga -->
      <div v-if="uploading" class="upload-progress">
        <div class="spinner"></div>
        <p v-if="!isProcessingServer">{{ uploadMessage }}</p>
        <p v-else style="color:#3498db;font-weight:500;">Procesando en el servidor...</p>
        <div v-if="uploadTotal > 0" class="progress-bar-wrapper">
          <div class="progress-bar">
            <div class="progress-bar-fill" :style="{ width: uploadPercent + '%' }"></div>
          </div>
          <div class="progress-bar-label">{{ uploadPercent }}%</div>
        </div>
      </div>
      
      <!-- Prompt de subida -->
      <div v-else-if="!displayUrl" class="upload-prompt" @click="triggerFileInput">
        <span class="icon">📁</span>
        <p>Arrastra archivos aquí o haz clic para seleccionar</p>
        <p class="help-text">Admite imágenes, vídeos o ZIP con contenido</p>
      </div>
      
      <!-- Preview de imagen -->
      <div v-else class="preview-container">
        <div class="image-wrapper">
          <img v-if="isImage" :src="displayUrl" alt="Preview" class="preview-image clickable-image" 
               @click="handleImageClick" title="Haz clic para anotar">
          <div class="click-overlay">
            <span class="click-text">🖱️ Clic para anotar</span>
          </div>
        </div>
        <video v-if="!isImage" controls class="preview-video">
          <source :src="displayUrl" :type="fileType">
        </video>
        <button v-if="!props.currentImage" @click.stop="clearFile" class="clear-btn">×</button>
        <button @click.stop="triggerFileInput" class="change-file-btn" :disabled="uploading">
          {{ props.currentImage ? '+ Añadir más' : 'Cambiar imagen' }}
        </button>
      </div>
    </div>
    
    <!-- Mostrar errores del store -->
    <div v-if="store.error" class="error-message">
      {{ store.error }}
      <button @click="store.clearError()" class="close-error">×</button>
    </div>

    <!-- Modal para configurar extracción de frames de video -->
    <div v-if="showVideoModal" class="modal-overlay" @click="closeVideoModal">
      <div class="modal-video" @click.stop>
        <div class="modal-header">
          <h2>Video Detectado</h2>
          <button @click="closeVideoModal" class="close-btn">&times;</button>
        </div>
        
        <div class="modal-body">
          <p class="video-info">
            <strong>{{ pendingVideo?.filename }}</strong>
          </p>
          <p class="video-details">
            Duración: {{ formatDuration(pendingVideo?.duration || 0) }} | 
            Resolución: {{ pendingVideo?.width }}x{{ pendingVideo?.height }}
          </p>
          
          <div class="form-section">
            <label>¿Cada cuántos segundos quieres extraer un frame?</label>
            <div class="fps-options">
              <button 
                v-for="option in fpsOptions" 
                :key="option.value"
                @click="selectedFps = option.value"
                :class="['fps-option', { selected: selectedFps === option.value }]"
              >
                <span class="option-label">{{ option.label }}</span>
                <span class="option-desc">{{ option.description }}</span>
              </button>
            </div>
          </div>

          <div class="info-box">
            <p>
              <strong>Frames estimados:</strong> 
              {{ estimatedFrames }}
            </p>
          </div>
        </div>
        
        <div class="modal-footer">
          <button @click="closeVideoModal" class="btn-cancel">
            Cancelar
          </button>
          <button @click="processVideo" class="btn-extract">
            Extraer Frames
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAnnotationStore } from '../stores/annotationStore'

const store = useAnnotationStore()
const emit = defineEmits(['files-uploaded', 'image-clicked'])

const props = defineProps({
  currentImage: Object, // Para mostrar la imagen actual seleccionada
  datasetId: String // ID del dataset al que subir las imágenes
})

const fileInput = ref(null)
const dragover = ref(false)
const files = ref([])
const previewUrl = ref(null)
const currentIndex = ref(0)
const uploading = ref(false)
const uploadMessage = ref('Subiendo imágenes...')
const uploadProgress = ref(0)
const uploadTotal = ref(0)
const uploadPercent = computed(() => {
  if (!uploadTotal.value) return 0
  return Math.round((uploadProgress.value / uploadTotal.value) * 100)
})

const isProcessingServer = computed(() => {
  return uploadPercent.value === 100 && uploading.value
})

// Estado del modal de video
const showVideoModal = ref(false)
const pendingVideo = ref(null)
const selectedFps = ref(1)
const fpsOptions = [
  { value: 2, label: '0.5s', description: 'Muy detallado' },
  { value: 1, label: '1s', description: 'Detallado' },
  { value: 0.5, label: '2s', description: 'Normal' },
  { value: 0.2, label: '5s', description: 'Espaciado' },
  { value: 0.1, label: '10s', description: 'Muy espaciado' }
]

const estimatedFrames = computed(() => {
  if (!pendingVideo.value) return 0
  // Usar el total de frames y FPS real del video, igual que el backend
  const videoFps = pendingVideo.value.fps
  const totalFrames = pendingVideo.value.total_frames
  const extractFps = selectedFps.value
  if (!videoFps || !totalFrames || !extractFps) return 0
  const frameInterval = Math.floor(videoFps / extractFps)
  if (frameInterval < 1) return totalFrames // Si el FPS de extracción es mayor que el del video, extrae todos los frames
  return Math.floor(totalFrames / frameInterval) + 1
})

// Si hay una imagen actual (desde la galería), mostrarla
const displayUrl = computed(() => {
  if (props.currentImage?.data) {
    return `data:${props.currentImage.content_type};base64,${props.currentImage.data}`
  }
  if (props.currentImage?._id) {
    return `http://localhost:5000/api/images/${props.currentImage._id}/data`
  }
  return previewUrl.value
})

const isImage = computed(() => {
  if (props.currentImage) return true
  if (!files.value[currentIndex.value]) return true
  return files.value[currentIndex.value].type.startsWith('image/')
})

const fileType = computed(() => {
  if (props.currentImage) return props.currentImage.content_type || 'image/*'
  return files.value[currentIndex.value]?.type || ''
})

// Watch para actualizar la preview cuando cambie la imagen actual
watch(() => props.currentImage, (newImage) => {
  if (newImage) {
    // La preview se maneja a través del computed displayUrl
    previewUrl.value = null
  }
})

const triggerFileInput = () => {
  fileInput.value.click()
}

const handleImageClick = () => {
  emit('image-clicked')
}

const handleFileChange = async (e) => {
  if (e.target.files.length > 0) {
    const fileList = Array.from(e.target.files)
    await uploadFiles(fileList)
  }
}

const handleDrop = async (e) => {
  dragover.value = false
  if (e.dataTransfer.files.length > 0) {
    const fileList = Array.from(e.dataTransfer.files)
    await uploadFiles(fileList)
  }
}

// Subida de ZIP y videos con barra de progreso
const uploadFileWithProgress = async (file, url, fieldName, datasetId, uploadedArr) => {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const formData = new FormData()
    formData.append(fieldName, file)
    formData.append('dataset_id', datasetId)
    xhr.open('POST', url, true)
    
    // Obtener token de localStorage
    const token = localStorage.getItem('auth_token')
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    }
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        uploadProgress.value = event.loaded
        uploadTotal.value = event.total
      }
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText)
          if (Array.isArray(data.images)) {
            uploadedArr.push(...data.images)
            resolve(data.images)
          } else if (data.requires_processing) {
            resolve(data)
          } else {
            uploadedArr.push(data)
            resolve(data)
          }
        } catch (err) {
          reject(err)
        }
      } else {
        reject(new Error('Error al subir el archivo'))
      }
    }
    xhr.onerror = () => {
      reject(new Error('Error de red al subir el archivo'))
    }
    xhr.send(formData)
  })
}

const uploadFiles = async (fileList) => {
  uploading.value = true
  uploadMessage.value = 'Procesando archivos...'
  uploadProgress.value = 0
  uploadTotal.value = 0
  try {
    const uploadedImages = []
    for (const file of fileList) {
      if (file.type === 'application/zip' || file.name.toLowerCase().endsWith('.zip')) {
        uploadMessage.value = `Descomprimiendo y procesando ${file.name}...`
        await uploadFileWithProgress(file, 'http://localhost:5000/api/datasets/import-images', 'file', props.datasetId, uploadedImages)
      } else if (file.type.startsWith('video/')) {
        uploadMessage.value = `Subiendo video ${file.name}...`
        const result = await uploadFileWithProgress(file, 'http://localhost:5000/api/images', 'image', props.datasetId, uploadedImages)
        
        if (result && result.video && result.requires_processing) {
          uploading.value = false
          pendingVideo.value = result.video
          showVideoModal.value = true
          return
        }
      } else if (file.type.startsWith('image/')) {
        uploadMessage.value = `Subiendo ${file.name}...`
        await uploadFileWithProgress(file, 'http://localhost:5000/api/images', 'image', props.datasetId, uploadedImages)
        if (uploadedImages.length === 1) {
          files.value = [file]
          loadPreview(file)
        }
      }
    }
    if (uploadedImages.length > 0) {
      emit('files-uploaded', uploadedImages)
    }
  } catch (error) {
    console.error('Error en la subida:', error)
  } finally {
    uploading.value = false
    uploadMessage.value = 'Subiendo imágenes...'
    uploadProgress.value = 0
    uploadTotal.value = 0
  }
}

const loadPreview = (file) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    previewUrl.value = e.target.result
  }
  reader.readAsDataURL(file)
}

const clearFile = () => {
  files.value = []
  previewUrl.value = null
}

const closeVideoModal = async () => {
  // Si hay un video pendiente, eliminarlo del backend
  if (pendingVideo.value?._id) {
    try {
      const token = localStorage.getItem('auth_token')
      await fetch(`http://localhost:5000/api/videos/${pendingVideo.value._id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
    } catch (error) {
      console.error('Error al eliminar el video:', error)
    }
  }
  
  showVideoModal.value = false
  pendingVideo.value = null
  selectedFps.value = 1
}

const formatDuration = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const processVideo = async () => {
  if (!pendingVideo.value) return
  
  try {
    showVideoModal.value = false
    uploading.value = true
    uploadMessage.value = `Extrayendo frames del video (${estimatedFrames.value} frames estimados)...`
    
    const token = localStorage.getItem('auth_token')
    const response = await fetch('http://localhost:5000/api/videos/process', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        video_id: pendingVideo.value._id,
        fps: selectedFps.value
      })
    })
    
    if (!response.ok) {
      throw new Error('Error al procesar el video')
    }
    
    const data = await response.json()
    
    uploadMessage.value = `Video procesado: ${data.frames_count} frames extraídos.`
    
    emit('files-uploaded', [data])
    
    setTimeout(() => {
      uploading.value = false
      pendingVideo.value = null
      selectedFps.value = 1
    }, 2000)
    
  } catch (error) {
    console.error('Error procesando video:', error)
    alert('Error al procesar el video')
    uploading.value = false
  }
}
</script>

<style scoped>
.uploader {
  margin: 1rem;
}

.upload-area {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  position: relative;
}

.upload-area.dragover {
  border-color: #42b983;
  background-color: rgba(66, 185, 131, 0.1);
}

.upload-prompt .icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.preview-container {
  position: relative;
  max-width: 100%;
  max-height: 400px;
}

.image-wrapper {
  position: relative;
  display: inline-block;
}

.click-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 500;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

.image-wrapper:hover .click-overlay {
  opacity: 1;
}

.preview-image, .preview-video {
  max-width: 100%;
  max-height: 400px;
  display: block;
  margin: 0 auto;
}

.clickable-image {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  border-radius: 4px;
}

.clickable-image:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.clear-btn {
  position: absolute;
  top: -10px;
  right: -10px;
  background: #ff4444;
  color: white;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  font-size: 14px;
  cursor: pointer;
}

.change-file-btn {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.2s;
}

.change-file-btn:hover:not(:disabled) {
  background: #369e6f;
}

.change-file-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

/* Estilos para estado de carga */
.upload-area.uploading {
  border-color: #42b983;
  background-color: rgba(66, 185, 131, 0.05);
}

.upload-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #42b983;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.upload-progress p {
  margin: 0;
  color: #42b983;
  font-weight: 500;
}

.progress-bar-wrapper {
  width: 100%;
  max-width: 320px;
  margin-top: 0.5rem;
}
.progress-bar {
  width: 100%;
  height: 16px;
  background: #eee;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #42b983 0%, #3498db 100%);
  transition: width 0.2s;
}
.progress-bar-label {
  text-align: right;
  font-size: 0.95rem;
  color: #42b983;
  font-weight: 600;
  margin-top: 2px;
}

/* Estilos para mensajes de error */
.error-message {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 4px;
  color: #c33;
  font-size: 0.9rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.close-error {
  background: none;
  border: none;
  color: #c33;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-error:hover {
  background: rgba(204, 51, 51, 0.1);
  border-radius: 50%;
}

/* Modal de video - diseño simple */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.modal-video {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 600px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h2 {
  margin: 0;
  color: #2c3e50;
  font-size: 1.25rem;
  font-weight: 600;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 1.75rem;
  cursor: pointer;
  color: #6c757d;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: color 0.2s;
}

.close-btn:hover {
  color: #2c3e50;
}

.modal-body {
  padding: 1.5rem;
}

.video-info {
  font-size: 1rem;
  margin-bottom: 0.5rem;
  color: #2c3e50;
}

.video-details {
  color: #6c757d;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e5e7eb;
}

.form-section {
  margin-bottom: 1.5rem;
}

.form-section label {
  display: block;
  margin-bottom: 1rem;
  font-weight: 600;
  color: #2c3e50;
  font-size: 0.95rem;
}

.fps-options {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.fps-option {
  background: white;
  border: 2px solid #dee2e6;
  border-radius: 6px;
  padding: 0.875rem 1rem;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.fps-option:hover {
  border-color: #adb5bd;
  background: #f8f9fa;
}

.fps-option.selected {
  border-color: #007bff;
  background: #e7f3ff;
}

.option-label {
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
}

.option-desc {
  font-size: 0.85rem;
  color: #6c757d;
}

.info-box {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  padding: 0.875rem;
}

.info-box p {
  margin: 0;
  color: #495057;
  font-size: 0.9rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid #e5e7eb;
  background: #f8f9fa;
}

.btn-cancel,
.btn-extract {
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: #e9ecef;
  color: #495057;
}

.btn-cancel:hover {
  background: #dee2e6;
}

.btn-extract {
  background: #007bff;
  color: white;
}

.btn-extract:hover {
  background: #0056b3;
}
</style>