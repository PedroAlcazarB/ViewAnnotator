<template>
  <div class="dataset-view">
    <!-- Header del dataset -->
    <div class="dataset-header">
      <div class="header-left">
        <button @click="goBack" class="back-btn" title="Volver al inicio">
          <i class="fas fa-arrow-left"></i>
          <span class="back-text">Volver</span>
        </button>
        <div class="dataset-info">
          <h1>{{ dataset.name }}</h1>
          <p>Total de {{ images.length }} imágenes mostradas en 1 página.</p>
        </div>
      </div>
      
      <div class="header-actions">
        <button @click="showExportModal = true" class="btn btn-warning">
          <i class="fas fa-file-export"></i> Exportar Anotaciones
        </button>
        <button @click="showImportModal = true" class="btn btn-info">
          <i class="fas fa-file-import"></i> Importar Anotaciones
        </button>
        <button @click="showUploadModal = true" class="btn btn-success">
          <i class="fas fa-upload"></i> Subir Imágenes
        </button>
      </div>
    </div>

    <!-- Barra lateral de acciones -->
    <div class="content-wrapper">
      <div class="sidebar">
        <div class="action-btn active">
          <i class="fas fa-images"></i>
          Imágenes
        </div>
        
        <div class="stats">
          <div class="stat-item">
            <strong>Imágenes:</strong> {{ images.length }}
          </div>
          <div class="stat-item">
            <strong>Annotations:</strong> {{ totalAnnotations }}
          </div>
          <div class="stat-item">
            <strong>Con anotaciones:</strong> {{ imagesWithAnnotationsCount }}
          </div>
          <div class="stat-item">
            <strong>Sin anotaciones:</strong> {{ imagesWithoutAnnotationsCount }}
          </div>
        </div>
      </div>

      <!-- Galería de imágenes -->
      <div class="main-content">
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
          <p>Cargando imágenes...</p>
        </div>
        
        <div v-else-if="images.length === 0" class="no-images">
          <i class="fas fa-images"></i>
          <p>No se encontraron imágenes en el dataset</p>
          <button @click="showUploadModal = true" class="btn btn-primary">
            Subir Imágenes
          </button>
        </div>
        
        <div v-else>
          <!-- Barra de filtros -->
          <div class="filter-bar">
            <label for="image-filter">Filtrar:</label>
            <select id="image-filter" v-model="filterStatus" class="filter-select">
              <option value="all">Todas las imágenes</option>
              <option value="with-annotations">Con anotaciones</option>
              <option value="no-annotations">Sin anotaciones</option>
            </select>
            <span v-if="filterStatus !== 'all'" class="filter-results">
              {{ filteredImages.length }} resultado(s)
            </span>
          </div>

          <!-- Mensaje cuando no hay resultados del filtro -->
          <div v-if="filteredImages.length === 0" class="no-images">
            <i class="fas fa-filter"></i>
            <p>No hay imágenes que coincidan con el filtro seleccionado</p>
            <button @click="filterStatus = 'all'" class="btn btn-secondary">
              Limpiar filtro
            </button>
          </div>

          <!-- Grid de imágenes filtradas -->
          <div v-else class="image-grid">
            <div 
              v-for="image in filteredImages" 
              :key="image._id" 
              class="image-card"
              @click="openAnnotator(image)"
            >
              <img 
                :src="`http://localhost:5000/api/images/${image._id}/data`" 
                :alt="image.filename"
                @error="handleImageError"
              />
              <div class="image-info">
                <p class="filename">{{ image.filename }}</p>
                <p class="annotations-count">
                  {{ getAnnotationCount(image) }} annotations
                </p>
              </div>
              <div class="image-actions">
                <button @click.stop="deleteImage(image)" class="btn-icon delete">
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de subida de imágenes -->
    <div v-if="showUploadModal" class="modal-overlay" @click="showUploadModal = false">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>Subir Imágenes a {{ dataset.name }}</h2>
          <button @click="showUploadModal = false" class="close-btn">&times;</button>
        </div>
        
        <div class="modal-body">
          <ImageUploader 
            :dataset-id="dataset._id"
            @files-uploaded="handleImagesUploaded"
          />
        </div>
      </div>
    </div>

    <!-- Modal de importación de anotaciones -->
    <ImportAnnotations 
      :show="showImportModal"
      :dataset-id="dataset._id"
      @close="showImportModal = false"
      @import-complete="handleImportComplete"
    />

    <!-- Modal de exportación de anotaciones -->
    <ExportAnnotations 
      :show="showExportModal"
      :dataset-id="dataset._id"
      @close="showExportModal = false"
    />

    <!-- Modal del anotador -->
    <div v-if="selectedImage" class="annotator-modal">
      <div class="annotator-header">
        <button @click="closeAnnotator" class="back-btn" title="Volver al dataset">
          <i class="fas fa-arrow-left"></i>
          <span class="back-text">Volver al Dataset</span>
        </button>
        <h2>{{ selectedImage.filename }}</h2>
      </div>
      
      <div class="annotator-content">
        <!-- Panel lateral izquierdo -->
        <div class="annotator-sidebar">

          <AnnotationToolbar 
            @annotation-cleared="handleAnnotationsUpdated"
            @undo-action="handleAnnotationsUpdated"
            @annotation-completed="handleAnnotationCompleted"
          />
          <CategoryManager />
        </div>
        
        <!-- Canvas principal -->
        <div class="annotator-canvas">
          <AnnotationsCanvas 
            ref="annotationsCanvas"
            :image-url="`http://localhost:5000/api/images/${selectedImage._id}/data`"
            :image-id="selectedImage._id"
            :active-tool="store.activeTool"
            :tool-settings="store.toolSettings"
            @annotation-saved="handleAnnotationSaved"
          />
        </div>
        
        <!-- Panel lateral derecho - Herramientas de IA -->
        <div class="annotator-ai-sidebar">
          <AITools 
            :current-image="selectedImage"
            :dataset-id="dataset._id"
            @model-loaded="handleModelLoaded"
            @model-unloaded="handleModelUnloaded"
            @annotations-updated="handleAnnotationsUpdated"
            @navigate-to-image="handleNavigateToImage"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import ImageUploader from '../components/ImageUploader.vue'
import ImportAnnotations from '../components/ImportAnnotations.vue'
import ExportAnnotations from '../components/ExportAnnotations.vue'
import AnnotationsCanvas from '../components/AnnotationsCanvas.vue'
import AnnotationToolbar from '../components/AnnotationToolbar.vue'
import CategoryManager from '../components/CategoryManager.vue'
import AITools from '../components/AITools.vue'
import { useAnnotationStore } from '../stores/annotationStore'

export default {
  name: 'DatasetView',
  components: {
    ImageUploader,
    ImportAnnotations,
    ExportAnnotations,
    AnnotationsCanvas,
    AnnotationToolbar,
    CategoryManager,
    AITools
  },
  props: {
    dataset: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const store = useAnnotationStore()
    return { store }
  },
  data() {
    return {
      loading: false,
      showUploadModal: false,
      showImportModal: false,
      showExportModal: false,
      selectedImage: null,
      filterStatus: 'all'
    }
  },
  computed: {
    images() {
      return this.store.images
    },
    annotations() {
      return this.store.annotations
    },
    totalAnnotations() {
      // Sumar todos los contadores de anotaciones de las imágenes
      return this.images.reduce((total, image) => {
        return total + (image.annotation_count || 0)
      }, 0)
    },
    filteredImages() {
      if (this.filterStatus === 'with-annotations') {
        return this.images.filter(image => this.getAnnotationCount(image) > 0)
      }
      if (this.filterStatus === 'no-annotations') {
        return this.images.filter(image => this.getAnnotationCount(image) === 0)
      }
      return this.images
    },
    imagesWithAnnotationsCount() {
      return this.images.filter(image => this.getAnnotationCount(image) > 0).length
    },
    imagesWithoutAnnotationsCount() {
      return this.images.filter(image => this.getAnnotationCount(image) === 0).length
    }
  },
  mounted() {
    // Establecer contexto del dataset y cargar datos
    this.store.setCurrentDataset(this.dataset)
    this.loadDatasetData()
  },
  beforeUnmount() {
    // Limpiar contexto al salir
    this.store.clearDatasetContext()
  },
  methods: {
    async loadDatasetData() {
      try {
        this.loading = true
        await this.store.initialize(this.dataset._id)
      } catch (error) {
        console.error('Error loading dataset data:', error)
      } finally {
        this.loading = false
      }
    },
    
    getAnnotationCount(image) {
      // Si la imagen tiene annotation_count del backend, usarlo
      if (image.annotation_count !== undefined) {
        return image.annotation_count
      }
      // Fallback al store si las anotaciones están cargadas
      return this.store.getAnnotationsByImageId(image._id).length
    },
    
    async deleteImage(image) {
      if (!confirm(`¿Estás seguro de que quieres eliminar "${image.filename}"?`)) {
        return
      }
      
      try {
        await this.store.deleteImage(image._id)
      } catch (error) {
        console.error('Error deleting image:', error)
        alert('Error deleting image')
      }
    },
    
    async handleImagesUploaded(uploadedImages) {
      this.showUploadModal = false
      console.log(`Uploaded ${uploadedImages.length} images successfully`)
      
      // Recargar imágenes para actualizar la galería
      try {
        await this.store.loadImages(this.dataset._id)
      } catch (error) {
        console.error('Error reloading images after upload:', error)
      }
    },
    
    async handleImportComplete(result) {
      this.showImportModal = false
      console.log('Import completed:', result)
      
      // Recargar imágenes y anotaciones para actualizar la vista
      try {
        await this.store.loadImages(this.dataset._id)
        // También podríamos mostrar un mensaje de éxito
        alert(`✅ Importación completada: ${result.stats.annotations} anotaciones importadas`)
      } catch (error) {
        console.error('Error reloading data after import:', error)
      }
    },
    
    handleImageError(event) {
      console.error('Error loading image:', event.target.src)
      event.target.style.display = 'none'
    },
    
    async openAnnotator(image) {
      this.selectedImage = image
      // Establecer la imagen actual en el store (ya carga automáticamente las anotaciones)
      await this.store.setCurrentImage(image)
    },
    
    closeAnnotator() {
      this.selectedImage = null
      // Las anotaciones se manejan automáticamente por el store
    },
    
    handleAnnotationsUpdated() {
      this.handleAnnotationSaved()
    },

    async handleAnnotationCompleted(event) {
      const imageId = event?.imageId || this.selectedImage?._id || this.selectedImage?.id
      if (!imageId) return
      this.store.markImageAsCompleted(imageId)
      this.handleAnnotationSaved()

      if (this.selectedImage) {
        this.selectedImage.completed = true
      }
      const inList = this.images.find(img => (img._id || img.id) === imageId)
      if (inList) {
        inList.completed = true
      }

      const nextImage = this.store.getNextIncompleteImage(imageId)
      if (nextImage) {
        await this.openAnnotator(nextImage)
        this.handleAnnotationSaved()
      } else {
        alert('Imagen marcada como completada. No quedan más imágenes pendientes.')
        this.closeAnnotator()
      }
    },

    handleAnnotationSaved() {
      // Actualizar el contador de anotaciones en la imagen actual
      if (this.selectedImage) {
        const currentId = this.selectedImage._id || this.selectedImage.id
        const updatedCount = this.store.getAnnotationsByImageId(currentId).length
        this.selectedImage.annotation_count = updatedCount
        
        // Buscar la imagen en la lista de images y actualizar su contador también
        const imageInList = this.images.find(img => (img._id || img.id) === currentId)
        if (imageInList) {
          imageInList.annotation_count = updatedCount
        }
      }
    },
    
    goBack() {
      this.$emit('go-back')
    },
    
    // Métodos para herramientas de IA
    handleModelLoaded(modelInfo) {
      console.log('Model loaded:', modelInfo)
      // Aquí puedes agregar lógica adicional cuando se carga un modelo
    },
    
    handleModelUnloaded() {
      console.log('Model unloaded')
      // Limpiar cualquier visualización de predicciones
      if (this.$refs.annotationsCanvas) {
        this.$refs.annotationsCanvas.clearPredictions()
      }
    },
    
    handleAnnotationsUpdated(updateData) {
      console.log('Annotations updated from AI prediction:', updateData)
      
      // Refrescar las anotaciones en el store para la imagen actual
      if (this.selectedImage) {
        this.store.loadAnnotations(this.selectedImage._id)
      }
      
      // Si se crearon categorías nuevas, refrescar las categorías
      if (updateData.created_categories && updateData.created_categories.length > 0) {
        this.store.loadCategories(this.dataset._id)
      }
      
      // Mostrar mensaje de éxito si está disponible
      if (updateData.message) {
        console.log(updateData.message)
        // Opcional: mostrar una notificación toast aquí
      }
    },
    
    async handleNavigateToImage(image) {
      // Cambiar a la nueva imagen
      await this.openAnnotator(image)
      
      // Limpiar predicciones si la predicción automática está deshabilitada
      // (el componente AITools se encargará de esto a través de su watcher)
    }
  }
}
</script>

<style scoped>
.dataset-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.dataset-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0;
}

.back-btn {
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(108, 117, 125, 0.3);
  cursor: pointer;
  font-size: 0.9rem;
  color: #495057;
  padding: 0.65rem 1rem;
  border-radius: 8px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-right: 1rem;
  font-weight: 500;
}

.back-btn .fas {
  font-size: 0.85rem;
}

.back-text {
  font-size: 0.9rem;
  letter-spacing: 0.02em;
}

.back-btn:hover {
  background: rgba(52, 152, 219, 0.1);
  border-color: rgba(52, 152, 219, 0.4);
  color: #3498db;
  transform: translateX(-2px);
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.15);
}

.back-btn:active {
  transform: translateX(-1px);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.dataset-info h1 {
  margin: 0;
  color: #333;
  font-size: 1.8rem;
}

.dataset-info p {
  margin: 5px 0 0 0;
  color: #6c757d;
  font-size: 0.9rem;
}

.header-actions .btn {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-success {
  background-color: #28a745;
  color: white;
}

.btn-info {
  background-color: #17a2b8;
  color: white;
  margin-right: 10px;
}

.btn-info:hover {
  background-color: #138496;
}

.btn-warning {
  background-color: #ff9800;
  color: white;
  margin-right: 10px;
}

.btn-warning:hover {
  background-color: #f57c00;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.btn-secondary:hover {
  background-color: #5a6268;
}

.content-wrapper {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 250px;
  background: #343a40;
  color: white;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.action-btn.active {
  background-color: #28a745;
}

.stats {
  margin-top: 20px;
}

.stat-item {
  padding: 8px 0;
  border-bottom: 1px solid #495057;
  font-size: 0.9rem;
}

.main-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f1f3f5;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 20px;
  color: #495057;
}

.filter-bar label {
  font-weight: 600;
  font-size: 0.9rem;
}

.filter-select {
  flex: 0 0 230px;
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 6px;
  background: white;
  color: #495057;
  font-size: 0.9rem;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.filter-select:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.15);
}

.filter-results {
  margin-left: auto;
  font-size: 0.85rem;
  color: #6c757d;
  font-weight: 500;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.no-images {
  text-align: center;
  padding: 60px 20px;
  color: #6c757d;
}

.no-images i {
  font-size: 4rem;
  margin-bottom: 20px;
  color: #dee2e6;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}

.image-card {
  background: white;
  border-radius: 8px;
  border: 1px solid #dee2e6;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.image-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  transform: translateY(-2px);
}

.image-card img {
  width: 100%;
  height: 150px;
  object-fit: cover;
}

.image-info {
  padding: 12px;
}

.filename {
  font-weight: 500;
  margin: 0 0 5px 0;
  font-size: 0.9rem;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.annotations-count {
  margin: 0;
  color: #6c757d;
  font-size: 0.8rem;
}

.image-actions {
  position: absolute;
  top: 8px;
  right: 8px;
}

.btn-icon {
  background: rgba(0,0,0,0.5);
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.btn-icon.delete {
  color: #dc3545;
}

.btn-icon:hover {
  background: rgba(0,0,0,0.7);
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 10px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h2 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
}

.modal-body {
  padding: 20px;
}

/* Annotator Modal */
.annotator-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: white;
  z-index: 2000;
  display: flex;
  flex-direction: column;
}

.annotator-header {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
}

.annotator-header h2 {
  margin: 0;
  color: #333;
}

.annotator-content {
  display: flex;
  flex: 1;
  height: calc(100vh - 60px);
}

.annotator-sidebar {
  width: 380px;
  background: #f8f9fa;
  border-right: 1px solid #dee2e6;
  overflow-y: auto;
  flex-shrink: 0;
}

.annotator-canvas {
  flex: 1;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.annotator-ai-sidebar {
  width: 350px;
  background: #f8f9fa;
  border-left: 1px solid #dee2e6;
  overflow-y: auto;
  flex-shrink: 0;
}
</style>