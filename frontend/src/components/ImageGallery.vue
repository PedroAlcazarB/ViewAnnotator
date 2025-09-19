<template>
  <div class="image-gallery">
    <div class="gallery-header">
      <h3>Galería de Imágenes</h3>
      <div class="gallery-info">
        <span v-if="images.length > 0">{{ images.length }} imagen(es) cargada(s)</span>
        <span v-else>No hay imágenes cargadas</span>
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
        :key="image.id"
        class="thumbnail-item"
        :class="{ 'active': currentImageIndex === index }"
        @click="selectImage(index)"
      >
        <img :src="image.url" :alt="image.name" class="thumbnail">
        <div class="thumbnail-info">
          <span class="thumbnail-name">{{ truncateName(image.name) }}</span>
          <span class="annotation-count">{{ getImageAnnotationCount(image.id) }} anotaciones</span>
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
          <h3>Anotando: {{ currentImage?.name }}</h3>
          <span class="image-counter">Imagen {{ currentImageIndex + 1 }} de {{ images.length }}</span>
        </div>
        <div class="annotation-controls">
          <!-- Navegación entre imágenes -->
          <div class="image-navigation">
            <button 
              @click="previousImage" 
              :disabled="currentImageIndex === 0"
              class="nav-btn"
            >
              ← Anterior
            </button>
            <button 
              @click="nextImage" 
              :disabled="currentImageIndex === images.length - 1"
              class="nav-btn"
            >
              Siguiente →
            </button>
          </div>
          
          <!-- Mini gestor de categorías -->
          <div class="mini-category-selector">
            <label>Categoría activa:</label>
            <select v-model="store.selectedCategory" class="category-select">
              <option v-for="category in store.categories" :key="category.id" :value="category.id">
                {{ category.name }}
              </option>
            </select>
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
            @annotation-completed="onAnnotationCompleted"
          />
        </div>
        
        <!-- Canvas principal -->
        <div class="annotation-canvas-container">
          <AnnotationCanvas 
            :imageUrl="currentImage?.url" 
            :imageId="currentImage?.id"
            :activeTool="activeTool"
            :toolSettings="toolSettings"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAnnotationStore } from '../stores/annotationStore'
import ImageUploader from './ImageUploader.vue'
import AnnotationCanvas from './AnnotationsCanvas.vue'
import AnnotationToolbar from './AnnotationToolbar.vue'
import ExportCOCO from './ExportCOCO.vue'

const store = useAnnotationStore()

// Estado de la galería
const images = ref([])
const currentImageIndex = ref(0)
const showAnnotationView = ref(false)
const imagesPerPage = 6
const currentPage = ref(1)

// Estado de herramientas de anotación
const activeTool = ref('select')
const toolSettings = ref({})

// Computed properties
const currentImage = computed(() => images.value[currentImageIndex.value] || null)

const totalPages = computed(() => Math.ceil(images.value.length / imagesPerPage))

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

// Funciones de manejo de archivos
function onFilesUploaded(files) {
  files.forEach(file => {
    const reader = new FileReader()
    reader.onload = (e) => {
      addImage(e.target.result, file)
    }
    reader.readAsDataURL(file)
  })
}

function addImage(url, file) {
  const newImage = {
    id: Date.now() + Math.random(), // ID único
    url: url,
    name: file.name,
    file: file,
    dateAdded: new Date()
  }
  
  images.value.push(newImage)
  
  // Si es la primera imagen, seleccionarla automáticamente
  if (images.value.length === 1) {
    currentImageIndex.value = 0
  }
}

function selectImage(index) {
  currentImageIndex.value = index
  
  // Ajustar página si es necesario
  const pageForImage = Math.floor(index / imagesPerPage) + 1
  if (pageForImage !== currentPage.value) {
    currentPage.value = pageForImage
  }
}

function removeImage(index) {
  if (confirm('¿Estás seguro de que quieres eliminar esta imagen?')) {
    const imageId = images.value[index].id
    
    // Eliminar anotaciones asociadas a esta imagen
    store.removeAnnotationsByImageId(imageId)
    
    // Eliminar imagen
    images.value.splice(index, 1)
    
    // Ajustar índice actual si es necesario
    if (currentImageIndex.value >= images.value.length) {
      currentImageIndex.value = Math.max(0, images.value.length - 1)
    }
    
    // Ajustar página si es necesario
    if (images.value.length === 0) {
      currentPage.value = 1
    } else if (currentPage.value > totalPages.value) {
      currentPage.value = totalPages.value
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
  if (currentImageIndex.value < images.value.length - 1) {
    selectImage(currentImageIndex.value + 1)
  }
}

// Funciones de paginación
function goToPage(page) {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
  }
}

// Funciones de vista de anotación
function openAnnotationView() {
  if (currentImage.value) {
    store.setCurrentImage(currentImage.value)
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

function onAnnotationCleared() {
  // Limpiar anotaciones de la imagen actual
  if (currentImage.value) {
    store.clearAnnotationsForImage(currentImage.value.id)
  }
}

function onUndoAction() {
  // Implementar lógica de undo - por ahora placeholder
  console.log('Undo action called')
}

function onAnnotationCompleted() {
  // Completar anotación actual - por ahora placeholder
  console.log('Annotation completed')
}

function closeAnnotationView() {
  showAnnotationView.value = false
}

// Funciones auxiliares
function truncateName(name) {
  return name.length > 20 ? name.substring(0, 17) + '...' : name
}

function getImageAnnotationCount(imageId) {
  return store.getAnnotationsByImageId(imageId).length
}

// Watch para limpiar anotaciones cuando cambie la imagen actual
watch(currentImageIndex, () => {
  // Opcional: podrías mantener las anotaciones por imagen
  // store.clearAnnotations()
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
</style>