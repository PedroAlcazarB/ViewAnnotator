<template>
  <div class="image-gallery">
    <div class="gallery-header">
      <h3>Galería de Imágenes y Videos</h3>
      <div class="gallery-info">
        <span v-if="images.length > 0">{{ images.length }} imagen(es)</span>
        <span v-if="videos.length > 0"> • {{ videos.length }} video(s)</span>
        <span v-if="images.length === 0 && videos.length === 0">No hay contenido cargado</span>
      </div>
    </div>

    <!-- Uploader -->
    <ImageUploader 
      @files-uploaded="onFilesUploaded"
      @image-clicked="openAnnotationView"
      :currentImage="currentImage"
    />

    <!-- Grid de imágenes en miniatura -->
    <div v-if="images.length > 0" class="thumbnails-grid">
      <div 
        v-for="(image, index) in images" 
        :key="image._id"
        class="thumbnail-item"
        :class="{ 'active': currentImageIndex === index && !currentVideo }"
        @click="selectImage(index)"
      >
        <img 
          :src="`/api/images/${image._id}/data`" 
          :alt="image.filename" 
          class="thumbnail"
        >
        <div class="thumbnail-info">
          <span class="thumbnail-name">{{ truncateName(image.filename) }}</span>
          <span class="annotation-count">{{ getImageAnnotationCount(image._id) }} anotaciones</span>
        </div>
        <button 
          @click.stop="removeImage(index)" 
          class="remove-btn"
          title="Eliminar imagen"
        >
          ×
        </button>
      </div>
    </div>

    <!-- Grid de videos -->
    <div v-if="videos.length > 0" class="videos-section">
      <h4 class="section-title">Videos</h4>
      <div class="thumbnails-grid">
        <div 
          v-for="video in videos" 
          :key="video._id"
          class="thumbnail-item video-item"
          :class="{ 'active': currentVideo && currentVideo._id === video._id }"
          @click="selectVideo(video)"
        >
          <div class="video-thumbnail">
            <div class="video-icon">🎬</div>
            <div class="video-duration">{{ formatDuration(video.duration) }}</div>
          </div>
          <div class="thumbnail-info">
            <span class="thumbnail-name">{{ truncateName(video.filename) }}</span>
            <span class="annotation-count">{{ video.extracted_frames }} frames • {{ video.annotation_count || 0 }} anotaciones</span>
          </div>
          <button 
            @click.stop="removeVideo(video._id)" 
            class="remove-btn"
            title="Eliminar video"
          >
            ×
          </button>
        </div>
      </div>
    </div>

    <!-- Paginación -->
    <div v-if="totalPages > 1" class="pagination">
      <button 
        @click="goToPage(currentPage - 1)"
        :disabled="currentPage === 1"
        class="pagination-btn"
      >
        ← Anterior
      </button>
      
      <div class="page-numbers">
        <button
          v-for="page in visiblePages"
          :key="page"
          @click="goToPage(page)"
          :class="['page-btn', { active: page === currentPage }]"
        >
          {{ page }}
        </button>
      </div>
      
      <button 
        @click="goToPage(currentPage + 1)"
        :disabled="currentPage === totalPages"
        class="pagination-btn"
      >
        Siguiente →
      </button>
    </div>

    <!-- Información de página actual -->
    <div v-if="images.length > 0" class="page-info">
      <span>Página {{ currentPage }} de {{ totalPages }}</span>
      <span class="separator">•</span>
      <span>Mostrando {{ startIndex + 1 }}-{{ Math.min(endIndex, images.length) }} de {{ images.length }} imágenes</span>
    </div>

    <!-- Vista de anotación en modal/overlay -->
    <div v-if="showAnnotationView" class="annotation-overlay">
      <div class="annotation-header">
        <div class="annotation-title">
          <h3>Anotando: {{ currentVideo ? currentVideo.filename : currentImage?.filename }}</h3>
          <span v-if="!currentVideo" class="image-counter">Imagen {{ currentImageIndex + 1 }} de {{ images.length }}</span>
          <span v-else class="image-counter">Frame {{ currentFrameIndex + 1 }} de {{ videoFrames.length }}</span>
        </div>
        <div class="annotation-controls">
          <!-- Navegación entre imágenes o frames -->
          <div class="image-navigation">
            <button 
              @click="previousItem" 
              :disabled="(currentVideo && currentFrameIndex === 0) || (!currentVideo && currentImageIndex === 0)"
              class="nav-btn"
            >
              ← Anterior
            </button>
            <button 
              @click="nextItem" 
              :disabled="(currentVideo && currentFrameIndex === videoFrames.length - 1) || (!currentVideo && currentImageIndex === images.length - 1)"
              class="nav-btn"
            >
              Siguiente →
            </button>
          </div>
          
          <ExportCOCO />
          <button @click="closeAnnotationView" class="close-btn">Cerrar</button>
        </div>
      </div>
      <div class="annotation-content">
        <!-- Panel lateral izquierdo con herramientas -->
        <div class="annotation-sidebar">
          <AnnotationToolbar 
            @tool-changed="onToolChanged"
            @annotation-cleared="onAnnotationCleared"
            @undo-action="onUndoAction"
          />
        </div>
        
        <!-- Canvas principal -->
        <div class="annotation-canvas-container">
          <AnnotationCanvas 
            :imageUrl="currentFrame ? `http://localhost:5000/api/images/${currentFrame._id}/data` : (currentImage ? `http://localhost:5000/api/images/${currentImage._id}/data` : null)" 
            :imageId="currentFrame?._id || currentImage?._id"
            :activeTool="activeTool"
            :toolSettings="toolSettings"
          />
        </div>
      </div>
      
      <!-- Navegador de frames para videos -->
      <div v-if="currentVideo && videoFrames.length > 0" class="frames-navigator">
        <div class="frames-scroll">
          <div 
            v-for="(frame, index) in videoFrames" 
            :key="frame._id"
            class="frame-thumbnail"
            :class="{ 'active': currentFrameIndex === index }"
            @click="selectFrame(index)"
          >
            <img 
              :src="`http://localhost:5000/api/images/${frame._id}/data`" 
              :alt="`Frame ${frame.frame_number}`"
            >
            <div class="frame-info">
              <span class="frame-number">{{ frame.frame_number }}</span>
              <span class="frame-time">{{ formatTimestamp(frame.timestamp) }}</span>
              <span v-if="frame.annotation_count > 0" class="frame-annotations">{{ frame.annotation_count }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useAnnotationStore } from '../stores/annotationStore'
import ImageUploader from './ImageUploader.vue'
import AnnotationCanvas from './AnnotationsCanvas.vue'
import AnnotationToolbar from './AnnotationToolbar.vue'
import ExportCOCO from './ExportCOCO.vue'

const store = useAnnotationStore()

// Estado de la galería
const currentImageIndex = ref(0)
const showAnnotationView = ref(false)
const imagesPerPage = 6
const currentPage = ref(1)

// Estado de videos
const videos = ref([])
const currentVideo = ref(null)
const videoFrames = ref([])
const currentFrameIndex = ref(0)

// Estado de herramientas de anotación
const activeTool = ref('select')
const toolSettings = ref({})

// Computed properties usando el store
const images = computed(() => store.images)
const currentImage = computed(() => {
  if (currentVideo.value) return null
  return store.images[currentImageIndex.value] || null
})
const currentFrame = computed(() => {
  if (!currentVideo.value || videoFrames.value.length === 0) return null
  return videoFrames.value[currentFrameIndex.value] || null
})

const totalPages = computed(() => Math.ceil(store.images.length / imagesPerPage))

const startIndex = computed(() => (currentPage.value - 1) * imagesPerPage)
const endIndex = computed(() => startIndex.value + imagesPerPage)

const visiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  return pages
})

// Inicializar datos
onMounted(async () => {
  await store.initialize()
  await loadVideos()
})

// Funciones de manejo de archivos
async function onFilesUploaded(uploadedImages) {
  // Las imágenes ya están subidas al servidor por el ImageUploader
  // Solo necesitamos actualizar la selección si es necesario
  if (uploadedImages.length > 0 && store.images.length === uploadedImages.length) {
    // Si estas son las primeras imágenes, seleccionar la primera
    currentImageIndex.value = 0
  }
  // Recargar videos por si se subió alguno
  await loadVideos()
  // Recargar imágenes por si se procesó un video (se crean frames)
  await store.loadImages()
}

// Funciones para videos
async function loadVideos() {
  try {
    const token = localStorage.getItem('token')
    const dataset_id = store.currentDataset?._id
    
    const url = dataset_id 
      ? `http://localhost:5000/api/videos?dataset_id=${dataset_id}`
      : 'http://localhost:5000/api/videos'
    
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      videos.value = data.videos || []
    }
  } catch (error) {
    console.error('Error al cargar videos:', error)
  }
}

async function selectVideo(video) {
  currentVideo.value = video
  currentImageIndex.value = -1  // Desactivar selección de imagen
  
  // Cargar frames del video
  await loadVideoFrames(video._id)
  
  // Seleccionar el primer frame y abrir la vista de anotación
  if (videoFrames.value.length > 0) {
    currentFrameIndex.value = 0
    await store.setCurrentImage(videoFrames.value[0])
    showAnnotationView.value = true
  }
}

async function loadVideoFrames(videoId) {
  try {
    const token = localStorage.getItem('token')
    const response = await fetch(`http://localhost:5000/api/videos/${videoId}/frames`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      videoFrames.value = data.frames || []
    }
  } catch (error) {
    console.error('Error al cargar frames del video:', error)
  }
}

async function selectFrame(index) {
  currentFrameIndex.value = index
  if (videoFrames.value[index]) {
    await store.setCurrentImage(videoFrames.value[index])
  }
}

async function removeVideo(videoId) {
  if (confirm('¿Estás seguro de que quieres eliminar este video y todos sus frames?')) {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`http://localhost:5000/api/videos/${videoId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        await loadVideos()
        if (currentVideo.value && currentVideo.value._id === videoId) {
          currentVideo.value = null
          videoFrames.value = []
          closeAnnotationView()
        }
      } else {
        alert('Error al eliminar el video')
      }
    } catch (error) {
      console.error('Error al eliminar video:', error)
      alert('Error al eliminar el video')
    }
  }
}

async function selectImage(index) {
  currentImageIndex.value = index
  
  // Establecer imagen actual en el store
  if (store.images[index]) {
    await store.setCurrentImage(store.images[index])
  }
  
  // Ajustar página si es necesario
  const pageForImage = Math.floor(index / imagesPerPage) + 1
  if (pageForImage !== currentPage.value) {
    currentPage.value = pageForImage
  }
}

async function removeImage(index) {
  if (confirm('¿Estás seguro de que quieres eliminar esta imagen?')) {
    const image = store.images[index]
    
    try {
      // Eliminar imagen del servidor (esto también elimina las anotaciones)
      await store.deleteImage(image._id)
      
      // Ajustar índice actual si es necesario
      if (currentImageIndex.value >= store.images.length) {
        currentImageIndex.value = Math.max(0, store.images.length - 1)
      }
      
      // Ajustar página si es necesario
      if (store.images.length === 0) {
        currentPage.value = 1
      } else if (currentPage.value > totalPages.value) {
        currentPage.value = totalPages.value
      }
      
    } catch (error) {
      console.error('Error al eliminar imagen:', error)
      alert('Error al eliminar la imagen. Por favor, inténtalo de nuevo.')
    }
  }
}

// Funciones de navegación
function previousImage() {
  if (currentImageIndex.value > 0) {
    selectImage(currentImageIndex.value - 1)
  }
}

function nextImage() {
  if (currentImageIndex.value < store.images.length - 1) {
    selectImage(currentImageIndex.value + 1)
  }
}

function previousItem() {
  if (currentVideo.value) {
    if (currentFrameIndex.value > 0) {
      selectFrame(currentFrameIndex.value - 1)
    }
  } else {
    previousImage()
  }
}

function nextItem() {
  if (currentVideo.value) {
    if (currentFrameIndex.value < videoFrames.value.length - 1) {
      selectFrame(currentFrameIndex.value + 1)
    }
  } else {
    nextImage()
  }
}

// Funciones de paginación
function goToPage(page) {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
  }
}

// Funciones de vista de anotación
async function openAnnotationView() {
  if (currentImage.value) {
    await store.setCurrentImage(currentImage.value)
    showAnnotationView.value = true
  }
}

// Funciones de manejo de herramientas
function onToolChanged(event) {
  activeTool.value = event.tool
  toolSettings.value = event.settings
  store.setActiveTool(event.tool)
  store.updateToolSettings(event.tool, event.settings)
}

async function onAnnotationCleared() {
  // Limpiar anotaciones de la imagen actual
  if (currentImage.value) {
    try {
      await store.clearAnnotationsForImage(currentImage.value._id)
    } catch (error) {
      console.error('Error al limpiar anotaciones:', error)
    }
  }
}

function onUndoAction() {
  // Implementar lógica de undo - por ahora placeholder
  console.log('Undo action called')
}

function closeAnnotationView() {
  showAnnotationView.value = false
  // Limpiar estado del video si estaba viendo uno
  if (currentVideo.value) {
    currentVideo.value = null
    videoFrames.value = []
    currentFrameIndex.value = 0
  }
}

// Funciones auxiliares
function truncateName(name) {
  return name.length > 20 ? name.substring(0, 17) + '...' : name
}

function getImageAnnotationCount(imageId) {
  return store.getAnnotationsByImageId(imageId).length
}

function formatDuration(seconds) {
  if (!seconds) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function formatTimestamp(seconds) {
  if (!seconds) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// Watch para cargar anotaciones cuando cambie la imagen actual
watch(currentImageIndex, async (newIndex) => {
  if (store.images[newIndex] && showAnnotationView.value && !currentVideo.value) {
    try {
      await store.loadAnnotations(store.images[newIndex]._id)
    } catch (error) {
      console.error('Error al cargar anotaciones:', error)
    }
  }
})

// Watch para cargar anotaciones cuando cambie el frame del video
watch(currentFrameIndex, async (newIndex) => {
  if (currentVideo.value && videoFrames.value[newIndex] && showAnnotationView.value) {
    try {
      await store.loadAnnotations(videoFrames.value[newIndex]._id)
    } catch (error) {
      console.error('Error al cargar anotaciones del frame:', error)
    }
  }
})
</script>

<style scoped>
.image-gallery {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
}

.gallery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.gallery-header h3 {
  margin: 0;
  color: #2c3e50;
}

.gallery-info {
  color: #7f8c8d;
  font-size: 0.9rem;
}

.thumbnails-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
  margin: 1rem 0;
}

.thumbnail-item {
  position: relative;
  background: white;
  border: 2px solid transparent;
  border-radius: 8px;
  padding: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.thumbnail-item:hover {
  border-color: #3498db;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.thumbnail-item.active {
  border-color: #27ae60;
  background: #f8fff9;
}

.thumbnail {
  width: 100%;
  height: 120px;
  object-fit: cover;
  border-radius: 4px;
}

.thumbnail-info {
  margin-top: 0.5rem;
  text-align: center;
}

.thumbnail-name {
  display: block;
  font-weight: 500;
  color: #2c3e50;
  font-size: 0.9rem;
}

.annotation-count {
  display: block;
  color: #7f8c8d;
  font-size: 0.8rem;
  margin-top: 0.25rem;
}

.remove-btn {
  position: absolute;
  top: -5px;
  right: -5px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.remove-btn:hover {
  background: #c0392b;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
  margin: 1rem 0;
}

.pagination-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.pagination-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.pagination-btn:hover:not(:disabled) {
  background: #2980b9;
}

.page-numbers {
  display: flex;
  gap: 0.25rem;
}

.page-btn {
  background: white;
  color: #3498db;
  border: 1px solid #3498db;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  min-width: 40px;
}

.page-btn:hover {
  background: #3498db;
  color: white;
}

.page-btn.active {
  background: #3498db;
  color: white;
}

.page-info {
  text-align: center;
  color: #7f8c8d;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}

.separator {
  margin: 0 0.5rem;
}

/* Estilos del modal de anotación */
.annotation-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  z-index: 1000;
  display: flex;
  flex-direction: column;
}

.annotation-header {
  background: #2c3e50;
  color: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.annotation-title h3 {
  margin: 0;
  font-size: 1.2rem;
}

.image-counter {
  font-size: 0.9rem;
  color: #bdc3c7;
  margin-left: 1rem;
}

.annotation-controls {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.image-navigation {
  display: flex;
  gap: 0.5rem;
}

.nav-btn {
  background: #f39c12;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.nav-btn:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.nav-btn:hover:not(:disabled) {
  background: #e67e22;
}

.mini-category-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: white;
}

.mini-category-selector label {
  font-size: 0.9rem;
  font-weight: 500;
}

.category-select {
  padding: 0.25rem 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: white;
  font-size: 0.9rem;
}

.close-btn {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
}

.close-btn:hover {
  background: #c0392b;
}

.annotation-content {
  flex: 1;
  display: flex;
  gap: 1rem;
  padding: 1rem;
  overflow: hidden;
}

.annotation-sidebar {
  width: 300px;
  flex-shrink: 0;
  overflow-y: auto;
  max-height: 100%;
}

.annotation-canvas-container {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f8f9fa;
  border-radius: 8px;
  overflow: auto;
}

/* Estilos para videos */
.videos-section {
  margin-top: 2rem;
}

.section-title {
  font-size: 1.1rem;
  color: #2c3e50;
  margin-bottom: 1rem;
  padding-left: 0.5rem;
  border-left: 4px solid #3498db;
}

.video-item .video-thumbnail {
  position: relative;
  width: 100%;
  height: 150px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
}

.video-icon {
  font-size: 3rem;
  opacity: 0.9;
}

.video-duration {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

/* Navegador de frames */
.frames-navigator {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: #2c3e50;
  padding: 1rem;
  border-top: 2px solid #34495e;
  max-height: 180px;
}

.frames-scroll {
  display: flex;
  gap: 0.75rem;
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 0.5rem;
}

.frames-scroll::-webkit-scrollbar {
  height: 8px;
}

.frames-scroll::-webkit-scrollbar-track {
  background: #34495e;
  border-radius: 4px;
}

.frames-scroll::-webkit-scrollbar-thumb {
  background: #7f8c8d;
  border-radius: 4px;
}

.frames-scroll::-webkit-scrollbar-thumb:hover {
  background: #95a5a6;
}

.frame-thumbnail {
  flex-shrink: 0;
  width: 120px;
  cursor: pointer;
  border: 2px solid transparent;
  border-radius: 6px;
  overflow: hidden;
  transition: all 0.2s;
  background: #34495e;
}

.frame-thumbnail:hover {
  border-color: #3498db;
  transform: translateY(-2px);
}

.frame-thumbnail.active {
  border-color: #e67e22;
  box-shadow: 0 0 10px rgba(230, 126, 34, 0.5);
}

.frame-thumbnail img {
  width: 100%;
  height: 80px;
  object-fit: cover;
  display: block;
}

.frame-info {
  padding: 0.4rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  background: #34495e;
}

.frame-number {
  font-size: 0.75rem;
  color: #ecf0f1;
  font-weight: 600;
}

.frame-time {
  font-size: 0.7rem;
  color: #95a5a6;
}

.frame-annotations {
  font-size: 0.7rem;
  color: #e67e22;
  font-weight: 600;
}
</style>