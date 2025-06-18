<template>
  <div class="uploader">
    <div class="upload-area" @click="triggerFileInput" @dragover.prevent="dragover = true" 
         @dragleave="dragover = false" @drop.prevent="handleDrop"
         :class="{ 'dragover': dragover }">
      <input type="file" ref="fileInput" @change="handleFileChange" accept="image/*,video/*" multiple hidden>
      <div v-if="!previewUrl" class="upload-prompt">
        <span class="icon">📁</span>
        <p>Arrastra imágenes/videos aquí o haz clic para seleccionar</p>
      </div>
      <div v-else class="preview-container">
        <img v-if="isImage" :src="previewUrl" alt="Preview" class="preview-image">
        <video v-else controls class="preview-video">
          <source :src="previewUrl" :type="fileType">
        </video>
        <button @click.stop="clearFile" class="clear-btn">×</button>
      </div>
    </div>
    <div v-if="files.length > 0" class="file-list">
      <div v-for="(file, index) in files" :key="index" class="file-item" @click="selectFile(index)">
        {{ file.name }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const emit = defineEmits(['file-selected', 'files-uploaded'])

const fileInput = ref(null)
const dragover = ref(false)
const files = ref([])
const previewUrl = ref(null)
const currentIndex = ref(0)

const isImage = computed(() => {
  if (!files.value[currentIndex.value]) return true
  return files.value[currentIndex.value].type.startsWith('image/')
})

const fileType = computed(() => {
  return files.value[currentIndex.value]?.type || ''
})

const triggerFileInput = () => {
  fileInput.value.click()
}

const handleFileChange = (e) => {
  if (e.target.files.length > 0) {
    files.value = Array.from(e.target.files)
    loadPreview(0)
    emit('files-uploaded', files.value)
  }
}

const handleDrop = (e) => {
  dragover.value = false
  if (e.dataTransfer.files.length > 0) {
    files.value = Array.from(e.dataTransfer.files)
    loadPreview(0)
    emit('files-uploaded', files.value)
  }
}

const loadPreview = (index) => {
  if (files.value.length === 0) return
  
  currentIndex.value = index
  const file = files.value[index]
  const reader = new FileReader()
  
  reader.onload = (e) => {
    previewUrl.value = e.target.result
    emit('file-selected', { url: e.target.result, file })
  }
  
  if (file.type.startsWith('image/')) {
    reader.readAsDataURL(file)
  } else if (file.type.startsWith('video/')) {
    // Para videos, solo mostramos el primer frame como preview
    reader.readAsDataURL(file)
  }
}

const selectFile = (index) => {
  loadPreview(index)
}

const clearFile = () => {
  files.value = []
  previewUrl.value = null
}

defineExpose({
  nextFile: () => {
    if (currentIndex.value < files.value.length - 1) {
      loadPreview(currentIndex.value + 1)
    }
  },
  prevFile: () => {
    if (currentIndex.value > 0) {
      loadPreview(currentIndex.value - 1)
    }
  }
})
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

.preview-image, .preview-video {
  max-width: 100%;
  max-height: 400px;
  display: block;
  margin: 0 auto;
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

.file-list {
  margin-top: 1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.file-item {
  padding: 0.5rem;
  background: #f0f0f0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.file-item:hover {
  background: #e0e0e0;
}
</style>