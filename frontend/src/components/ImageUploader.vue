<template>
  <div class="uploader">
    <div class="upload-area" @dragover.prevent="dragover = true" 
         @dragleave="dragover = false" @drop.prevent="handleDrop"
         :class="{ 'dragover': dragover }">
      <input type="file" ref="fileInput" @change="handleFileChange" accept="image/*,video/*" multiple hidden>
      <div v-if="!displayUrl" class="upload-prompt" @click="triggerFileInput">
        <span class="icon">📁</span>
        <p>Arrastra imágenes/videos aquí o haz clic para seleccionar</p>
        <p class="help-text">Puedes seleccionar múltiples archivos</p>
      </div>
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
        <button @click.stop="triggerFileInput" class="change-file-btn">
          {{ props.currentImage ? '+ Añadir más' : 'Cambiar imagen' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const emit = defineEmits(['files-uploaded', 'image-clicked'])

const props = defineProps({
  currentImage: Object // Para mostrar la imagen actual seleccionada
})

const fileInput = ref(null)
const dragover = ref(false)
const files = ref([])
const previewUrl = ref(null)
const currentIndex = ref(0)

// Si hay una imagen actual (desde la galería), mostrarla
const displayUrl = computed(() => {
  return props.currentImage?.url || previewUrl.value
})

const isImage = computed(() => {
  if (props.currentImage) return true
  if (!files.value[currentIndex.value]) return true
  return files.value[currentIndex.value].type.startsWith('image/')
})

const fileType = computed(() => {
  if (props.currentImage) return 'image/*'
  return files.value[currentIndex.value]?.type || ''
})

// Watch para actualizar la preview cuando cambie la imagen actual
watch(() => props.currentImage, (newImage) => {
  if (newImage) {
    previewUrl.value = newImage.url
  }
})

const triggerFileInput = () => {
  fileInput.value.click()
}

const handleImageClick = () => {
  emit('image-clicked')
}

const handleFileChange = (e) => {
  if (e.target.files.length > 0) {
    files.value = Array.from(e.target.files)
    // Solo emitir files-uploaded para múltiples archivos
    emit('files-uploaded', files.value)
    // No llamar loadPreview aquí para evitar duplicados
  }
}

const handleDrop = (e) => {
  dragover.value = false
  if (e.dataTransfer.files.length > 0) {
    files.value = Array.from(e.dataTransfer.files)
    // Solo emitir files-uploaded para múltiples archivos
    emit('files-uploaded', files.value)
    // No llamar loadPreview aquí para evitar duplicados
  }
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

.change-file-btn:hover {
  background: #369e6f;
}
</style>