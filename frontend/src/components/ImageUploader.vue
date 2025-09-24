<template>
  <div class="uploader">
    <div class="upload-area" @dragover.prevent="dragover = true" 
         @dragleave="dragover = false" @drop.prevent="handleDrop"
         :class="{ 'dragover': dragover, 'uploading': uploading }">
      <input type="file" ref="fileInput" @change="handleFileChange" accept="image/*" multiple hidden>
      
      <!-- Estado de carga -->
      <div v-if="uploading" class="upload-progress">
        <div class="spinner"></div>
        <p>Subiendo imágenes...</p>
      </div>
      
      <!-- Prompt de subida -->
      <div v-else-if="!displayUrl" class="upload-prompt" @click="triggerFileInput">
        <span class="icon">📁</span>
        <p>Arrastra imágenes aquí o haz clic para seleccionar</p>
        <p class="help-text">Puedes seleccionar múltiples archivos</p>
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
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAnnotationStore } from '../stores/annotationStore'

const store = useAnnotationStore()
const emit = defineEmits(['files-uploaded', 'image-clicked'])

const props = defineProps({
  currentImage: Object // Para mostrar la imagen actual seleccionada
})

const fileInput = ref(null)
const dragover = ref(false)
const files = ref([])
const previewUrl = ref(null)
const currentIndex = ref(0)
const uploading = ref(false)

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

const uploadFiles = async (fileList) => {
  uploading.value = true
  
  try {
    const uploadedImages = []
    
    for (const file of fileList) {
      // Solo procesar imágenes
      if (file.type.startsWith('image/')) {
        try {
          const uploadedImage = await store.uploadImage(file)
          uploadedImages.push(uploadedImage)
          
          // Para la primera imagen, mostrar preview
          if (uploadedImages.length === 1) {
            files.value = [file]
            loadPreview(file)
          }
        } catch (error) {
          console.error(`Error al subir ${file.name}:`, error)
          // Continuar con el siguiente archivo
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
</style>