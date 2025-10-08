<template>
  <div class="dataset-view">
    <!-- Header del dataset -->
    <div class="dataset-header">
      <div class="header-left">
        <button @click="goBack" class="back-btn">
          <i class="fas fa-arrow-left"></i>
        </button>
        <div class="dataset-info">
          <h1>{{ dataset.name }}</h1>
          <p>Total de {{ images.length }} imágenes mostradas en 1 página.</p>
        </div>
      </div>
      
      <div class="header-actions">
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
        
        <div v-else class="image-grid">
          <div 
            v-for="image in images" 
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
                {{ getAnnotationCount(image._id) }} annotations
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

    <!-- Modal del anotador -->
    <div v-if="selectedImage" class="annotator-modal">
      <div class="annotator-header">
        <button @click="closeAnnotator" class="back-btn">
          <i class="fas fa-arrow-left"></i> Volver al Dataset
        </button>
        <h2>{{ selectedImage.filename }}</h2>
      </div>
      
      <div class="annotator-content">
        <!-- Panel lateral izquierdo -->
        <div class="annotator-sidebar">
          <CategoryManager />
          <AnnotationToolbar />
        </div>
        
        <!-- Canvas principal -->
        <div class="annotator-canvas">
          <AnnotationsCanvas 
            :image-url="`http://localhost:5000/api/images/${selectedImage._id}/data`"
            :image-id="selectedImage._id"
            :active-tool="store.activeTool"
            :tool-settings="store.toolSettings"
            @annotation-saved="handleAnnotationSaved"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import ImageUploader from '../components/ImageUploader.vue'
import AnnotationsCanvas from '../components/AnnotationsCanvas.vue'
import AnnotationToolbar from '../components/AnnotationToolbar.vue'
import CategoryManager from '../components/CategoryManager.vue'
import { useAnnotationStore } from '../stores/annotationStore'

export default {
  name: 'DatasetView',
  components: {
    ImageUploader,
    AnnotationsCanvas,
    AnnotationToolbar,
    CategoryManager
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
      selectedImage: null
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
      return this.annotations.length
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
    
    getAnnotationCount(imageId) {
      return this.store.getAnnotationsByImageId(imageId).length
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
    
    handleImageError(event) {
      console.error('Error loading image:', event.target.src)
      event.target.style.display = 'none'
    },
    
    async openAnnotator(image) {
      this.selectedImage = image
      // Establecer la imagen actual en el store
      this.store.setCurrentImage(image)
      // Cargar anotaciones para esta imagen
      try {
        await this.store.loadAnnotations(image._id)
      } catch (error) {
        console.error('Error loading annotations for image:', error)
      }
    },
    
    closeAnnotator() {
      this.selectedImage = null
      // Las anotaciones se manejan automáticamente por el store
    },
    
    handleAnnotationSaved() {
      // El store maneja las actualizaciones automáticamente
    },
    
    goBack() {
      this.$emit('go-back')
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
  gap: 15px;
}

.back-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  color: #6c757d;
  padding: 8px;
  border-radius: 4px;
  transition: all 0.3s ease;
}

.back-btn:hover {
  background-color: #e9ecef;
  color: #495057;
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

.btn-primary {
  background-color: #007bff;
  color: white;
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
  width: 300px;
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
</style>