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
          <p>{{ filteredMedia.length }} archivo{{ filteredMedia.length !== 1 ? 's' : '' }}{{ filterStatus !== 'all' ? ' filtrados' : '' }}</p>
        </div>
      </div>
      
      <div class="header-actions">
        <button @click="showExportModal = true" class="btn btn-warning" title="Exportar Anotaciones">
          <i class="fas fa-file-export"></i>
          <span class="btn-text">Exportar</span>
        </button>
        <button @click="showImportModal = true" class="btn btn-info" title="Importar Anotaciones">
          <i class="fas fa-file-import"></i>
          <span class="btn-text">Importar</span>
        </button>
        <button @click="showUploadModal = true" class="btn btn-success" title="Subir Imágenes">
          <i class="fas fa-upload"></i>
          <span class="btn-text">Subir</span>
        </button>
      </div>
    </div>

    <!-- Barra lateral de acciones -->
    <div class="content-wrapper">
      <div class="sidebar">
        <div class="sidebar-header">
          <i class="fas fa-chart-bar"></i>
          <h3>Estadísticas</h3>
        </div>
        <div class="sidebar-stats-cards"><div class="sidebar-stat-card">
          <i class="fas fa-images sidebar-stat-icon sidebar-icon-images"></i>
          <div class="sidebar-stat-info">
            <span class="sidebar-stat-label">Imágenes</span>
            <span class="sidebar-stat-value">{{ images.length }}</span>
          </div>
        </div>
        <div class="sidebar-stat-card">
          <i class="fas fa-video sidebar-stat-icon sidebar-icon-videos"></i>
          <div class="sidebar-stat-info">
            <span class="sidebar-stat-label">Videos</span>
            <span class="sidebar-stat-value">{{ videos.length }}</span>
          </div>
        </div>
          <div class="sidebar-stat-card">
            <i class="fas fa-tags sidebar-stat-icon sidebar-icon-annotations"></i>
            <div class="sidebar-stat-info">
              <span class="sidebar-stat-label">Anotaciones</span>
              <span class="sidebar-stat-value">{{ totalAnnotations }}</span>
            </div>
          </div>
          <div class="sidebar-stat-card">
            <i class="fas fa-check-circle sidebar-stat-icon sidebar-icon-with"></i>
            <div class="sidebar-stat-info">
              <span class="sidebar-stat-label">Con anotaciones</span>
              <span class="sidebar-stat-value">{{ imagesWithAnnotationsCount }}</span>
            </div>
          </div>
          <div class="sidebar-stat-card">
            <i class="fas fa-times sidebar-stat-icon sidebar-icon-without"></i>
            <div class="sidebar-stat-info">
              <span class="sidebar-stat-label">Sin anotaciones</span>
              <span class="sidebar-stat-value">{{ imagesWithoutAnnotationsCount }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Galería de imágenes -->
      <div class="main-content">
        <div class="content-area">
          <div v-if="loading" class="loading">
            <div class="spinner"></div>
            <p>Cargando imágenes...</p>
          </div>
          
          <div v-else-if="!hasAnyMedia" class="no-images">
            <i class="fas fa-file"></i>
            <p>No se encontraron archivos en el dataset</p>
            <button @click="showUploadModal = true" class="btn btn-primary">
              Subir archivos
            </button>
          </div>
          
          <div v-else>
            <!-- Barra de filtros -->
            <div class="filter-bar">
              <label class="filter-label" id="image-filter-label">Filtrar:</label>
              <div class="filter-select-wrapper" ref="filterDropdown">
                <button
                  type="button"
                  class="filter-select"
                  :class="{ open: isFilterDropdownOpen }"
                  id="filter-select-button"
                  :aria-expanded="isFilterDropdownOpen.toString()"
                  aria-haspopup="listbox"
                  aria-labelledby="image-filter-label filter-select-button"
                  @click.stop="toggleFilterDropdown"
                >
                  <span class="filter-select__value">{{ filterStatusLabel }}</span>
                  <i class="fas fa-chevron-down dropdown-icon"></i>
                </button>
                <ul
                  v-if="isFilterDropdownOpen"
                  class="filter-options"
                  role="listbox"
                  aria-labelledby="image-filter-label"
                >
                  <li
                    v-for="option in filterOptions"
                    :key="option.value"
                    class="filter-option"
                    :class="{ active: option.value === filterStatus }"
                    role="option"
                    :aria-selected="option.value === filterStatus"
                    @click.stop="selectFilterOption(option.value)"
                  >
                    <span>{{ option.label }}</span>
                    <i v-if="option.value === filterStatus" class="fas fa-check"></i>
                  </li>
                </ul>
              </div>
              <span v-if="filterStatus !== 'all'" class="filter-results">
                {{ filteredMedia.length }} resultado(s)
              </span>
            </div>

            <!-- Mensaje cuando no hay resultados del filtro -->
            <div v-if="filteredMedia.length === 0" class="no-images">
              <i class="fas fa-filter"></i>
              <p>No hay archivos que coincidan con el filtro seleccionado</p>
              <button @click="filterStatus = 'all'" class="btn btn-secondary">
                Limpiar filtro
              </button>
            </div>

            <!-- Grid mixto de imágenes y videos -->
            <div v-else class="images-container">
              <div class="image-grid">
                <div
                  v-for="media in paginatedMedia"
                  :key="media.id"
                  :class="['image-card', { 'video-card': media.type === 'video' }]"
                  @click="media.type === 'video' ? openVideoAnnotator(media.item) : openAnnotator(media.item)"
                >
                  <template v-if="media.type === 'video'">
                    <div class="video-thumbnail" :class="{ 'has-thumbnail': videoThumbnail(media.item) }">
                      <img
                        v-if="videoThumbnail(media.item)"
                        :src="videoThumbnail(media.item)"
                        :alt="`Vista previa de ${media.item.filename}`"
                        class="video-thumbnail-image"
                      />
                      <span v-else class="video-icon">🎬</span>
                      <span class="video-duration">{{ formatDuration(media.item.duration) }}</span>
                    </div>
                    <div class="image-info">
                      <p class="filename">{{ media.item.filename }}</p>
                      <p class="annotations-count">
                        {{ media.item.frames_count || 0 }} frames • {{ Math.round(media.item.fps || 0) }} fps
                      </p>
                    </div>
                    <div class="image-actions">
                      <button @click.stop="deleteVideo(media.item)" class="btn-icon delete">
                        <i class="fas fa-trash"></i>
                      </button>
                    </div>
                  </template>

                  <template v-else>
                    <img
                      :src="`http://localhost:5000/api/images/${media.item._id}/data`"
                      :alt="media.item.filename"
                      @error="handleImageError"
                    />
                    <div class="image-info">
                      <p class="filename">{{ media.item.filename }}</p>
                      <p class="annotations-count">
                        {{ getAnnotationCount(media.item) }} anotaciones
                      </p>
                    </div>
                    <div class="image-actions">
                      <button @click.stop="deleteImage(media.item)" class="btn-icon delete">
                        <i class="fas fa-trash"></i>
                      </button>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Paginación fija al final -->
        <div v-if="!loading && hasAnyMedia && filteredMedia.length > 0 && totalPages > 1" class="pagination-container">
          <div class="pagination">
            <button 
              @click="goToPage(currentPage - 1)"
              :disabled="currentPage === 1"
              class="pagination-btn"
            >
              « Anterior
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
              Siguiente »
            </button>
          </div>

          <!-- Información de página actual -->
          <div v-if="filteredMedia.length > 0" class="page-info">
            <span>Página {{ currentPage }} de {{ totalPages }}</span>
            <span class="separator">•</span>
            <span>Mostrando {{ Math.min(startIndex + 1, filteredMedia.length) }}-{{ Math.min(endIndex, filteredMedia.length) }} de {{ filteredMedia.length }} archivos</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de subida de imágenes -->
    <div v-if="showUploadModal" class="modal-overlay" @click="showUploadModal = false">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>Subir datos a {{ dataset.name }}</h2>
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
          />
          <CategoryManager />
        </div>
        
        <!-- Contenedor principal con canvas y frames -->
        <div class="annotator-main-area">
          <!-- Canvas principal -->
          <div class="annotator-canvas canvas-flex">
            <AnnotationsCanvas 
              ref="annotationsCanvas"
              :image-url="`http://localhost:5000/api/images/${selectedImage._id}/data`"
              :image-id="selectedImage._id"
              :active-tool="store.activeTool"
              :tool-settings="store.toolSettings"
              @annotation-saved="handleAnnotationSaved"
            />
          </div>
          
          <!-- Navegador de frames (solo visible cuando hay un video seleccionado) -->
          <div v-if="selectedVideo" class="frames-navigator">
            <div class="frames-scroll">
              <div 
                v-for="(frame, index) in videoFrames" 
                :key="frame._id"
                class="frame-thumbnail"
                :class="{ active: index === currentFrameIndex }"
                @click="selectFrame(index)"
              >
                <img 
                  :src="`http://localhost:5000/api/images/${frame._id}/data`" 
                  :alt="`Frame ${index + 1}`"
                />
                <div class="frame-info">
                  <span class="frame-number">Frame {{ index + 1 }}</span>
                  <span class="frame-time">{{ formatTimestamp(frame.timestamp) }}</span>
                  <span class="frame-annotations">{{ getAnnotationCount(frame) }} ann.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Panel lateral derecho - Herramientas de IA -->
        <div class="annotator-ai-sidebar">
          <AITools 
            :current-image="selectedImage"
            :dataset-id="dataset._id"
            :can-navigate-previous="canNavigatePrevious"
            :can-navigate-next="canNavigateNext"
            @model-loaded="handleModelLoaded"
            @model-unloaded="handleModelUnloaded"
            @annotations-updated="handleAnnotationsUpdated"
            @navigate="handleNavigateRequest"
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
      filterStatus: 'all',
      filterOptions: [
        { value: 'all', label: 'Todos los archivos' },
        { value: 'with-annotations', label: 'Con anotaciones' },
        { value: 'no-annotations', label: 'Sin anotaciones' }
      ],
      isFilterDropdownOpen: false,
      currentPage: 1,
      imagesPerPage: 24,
      // Estado para videos
      videos: [],
      videoThumbnails: {},
      selectedVideo: null,
      videoFrames: [],
      currentFrameIndex: 0
    }
  },
  computed: {
    images() {
      return this.store.images
    },
    annotations() {
      return this.store.annotations
    },
    totalMediaCount() {
      return this.images.length + this.videos.length
    },
    hasAnyMedia() {
      return this.totalMediaCount > 0
    },
    totalAnnotations() {
      const imageAnnotations = this.images.reduce((total, image) => {
        return total + (image.annotation_count || 0)
      }, 0)
      const videoAnnotations = this.videos.reduce((total, video) => {
        return total + (video.annotation_count || 0)
      }, 0)
      return imageAnnotations + videoAnnotations
    },
    mediaItems() {
      const combined = []
      let orderIndex = 0

      for (const video of this.videos) {
        combined.push({
          id: `video-${video._id}`,
          type: 'video',
          item: video,
          annotationCount: video.annotation_count || 0,
          sortDate: this.getMediaSortDate(video),
          orderIndex: orderIndex += 1
        })
      }

      for (const image of this.images) {
        combined.push({
          id: `image-${image._id}`,
          type: 'image',
          item: image,
          annotationCount: this.getAnnotationCount(image),
          sortDate: this.getMediaSortDate(image),
          orderIndex: orderIndex += 1
        })
      }

      return combined.sort((a, b) => {
        if (a.sortDate === b.sortDate) {
          return a.orderIndex - b.orderIndex
        }
        return a.sortDate - b.sortDate
      })
    },
    filteredMedia() {
      if (this.filterStatus === 'with-annotations') {
        return this.mediaItems.filter(entry => entry.annotationCount > 0)
      }
      if (this.filterStatus === 'no-annotations') {
        return this.mediaItems.filter(entry => entry.annotationCount === 0)
      }
      return this.mediaItems
    },
    imagesWithAnnotationsCount() {
      const imageCount = this.images.filter(image => this.getAnnotationCount(image) > 0).length
      const videoCount = this.videos.filter(video => (video.annotation_count || 0) > 0).length
      return imageCount + videoCount
    },
    imagesWithoutAnnotationsCount() {
      const imageCount = this.images.filter(image => this.getAnnotationCount(image) === 0).length
      const videoCount = this.videos.filter(video => (video.annotation_count || 0) === 0).length
      return imageCount + videoCount
    },
    totalPages() {
      return Math.ceil(this.filteredMedia.length / this.imagesPerPage)
    },
    startIndex() {
      return (this.currentPage - 1) * this.imagesPerPage
    },
    endIndex() {
      return this.startIndex + this.imagesPerPage
    },
    paginatedMedia() {
      return this.filteredMedia.slice(this.startIndex, this.endIndex)
    },
    visiblePages() {
      const pages = []
      const start = Math.max(1, this.currentPage - 2)
      const end = Math.min(this.totalPages, this.currentPage + 2)
      
      for (let i = start; i <= end; i++) {
        pages.push(i)
      }
      return pages
    },
    filterStatusLabel() {
      const match = this.filterOptions.find(option => option.value === this.filterStatus)
      return match ? match.label : 'Filtrar'
    },
    currentMediaKey() {
      if (this.selectedVideo) {
        return `video-${this.selectedVideo._id}`
      }
      if (this.selectedImage) {
        if (this.selectedImage.video_id) {
          return `video-${this.selectedImage.video_id}`
        }
        const imageId = this.selectedImage._id || this.selectedImage.id
        if (imageId) {
          return `image-${imageId}`
        }
      }
      return null
    },
    canNavigatePrevious() {
      if (!this.currentMediaKey) {
        return false
      }
      const index = this.mediaItems.findIndex(entry => entry.id === this.currentMediaKey)
      return index > 0
    },
    canNavigateNext() {
      if (!this.currentMediaKey) {
        return false
      }
      const index = this.mediaItems.findIndex(entry => entry.id === this.currentMediaKey)
      return index >= 0 && index < this.mediaItems.length - 1
    }
  },
  async mounted() {
    // Establecer contexto del dataset y cargar datos
    this.store.setCurrentDataset(this.dataset)
    await this.loadDatasetData()
    await this.loadVideos()
    document.addEventListener('click', this.handleClickOutside)
  },
  beforeUnmount() {
    // Limpiar contexto al salir
    this.store.clearDatasetContext()
    document.removeEventListener('click', this.handleClickOutside)
  },
  watch: {
    filterStatus() {
      // Resetear a la primera página cuando cambie el filtro
      this.currentPage = 1
    },
    filteredMedia(newList) {
      if (!Array.isArray(newList) || newList.length === 0) {
        this.currentPage = 1
        return
      }

      const totalPages = Math.ceil(newList.length / this.imagesPerPage)
      if (totalPages > 0 && this.currentPage > totalPages) {
        this.currentPage = totalPages
      }
    }
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

    getMediaSortDate(media) {
      const candidates = [media?.upload_date, media?.created_at, media?.updated_at]
      for (const value of candidates) {
        if (!value) {
          continue
        }
        const parsed = new Date(value)
        if (!Number.isNaN(parsed.getTime())) {
          return parsed.getTime()
        }
      }
      return 0
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
      
      // Recargar imágenes y videos para actualizar la galería
      try {
        await this.store.loadImages(this.dataset._id)
        await this.loadVideos()
      } catch (error) {
        console.error('Error reloading images after upload:', error)
      }
    },
    
    async handleImportComplete(result) {
      this.showImportModal = false
      console.log('Import completed:', result)
      
      // Recargar imágenes y anotaciones para actualizar la vista
      try {
        await this.loadDatasetData()
        alert(`✅ Importación completada: ${result.stats.annotations} anotaciones importadas`)
      } catch (error) {
        console.error('Error reloading data after import:', error)
      }
    },
    
    handleImageError(event) {
      console.error('Error loading image:', event.target.src)
      event.target.style.display = 'none'
    },

    toggleFilterDropdown() {
      this.isFilterDropdownOpen = !this.isFilterDropdownOpen
    },

    selectFilterOption(value) {
      if (this.filterStatus !== value) {
        this.filterStatus = value
      }
      this.isFilterDropdownOpen = false
    },

    handleClickOutside(event) {
      const dropdown = this.$refs.filterDropdown
      if (!dropdown) {
        return
      }
      if (!dropdown.contains(event.target)) {
        this.isFilterDropdownOpen = false
      }
    },
    
    async openAnnotator(image) {
      this.selectedImage = image
      // Limpiar estado de video
      this.selectedVideo = null
      this.videoFrames = []
      this.currentFrameIndex = 0
      // Establecer la imagen actual en el store (ya carga automáticamente las anotaciones)
      await this.store.setCurrentImage(image)
    },
    
    closeAnnotator() {
      this.selectedImage = null
      this.selectedVideo = null
      this.videoFrames = []
      this.currentFrameIndex = 0
      // Las anotaciones se manejan automáticamente por el store
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
    
    goToPage(page) {
      if (page >= 1 && page <= this.totalPages) {
        this.currentPage = page
        // Scroll hacia arriba cuando cambie de página
        const contentArea = this.$el.querySelector('.content-area')
        if (contentArea) {
          contentArea.scrollTop = 0
        }
      }
    },
    
    // Métodos para herramientas de IA
    handleModelLoaded(modelInfo) {
      console.log('Model loaded:', modelInfo)
    },
    
    handleModelUnloaded() {
      console.log('Model unloaded')
      // Limpiar cualquier visualización de predicciones
      if (this.$refs.annotationsCanvas) {
        this.$refs.annotationsCanvas.clearPredictions()
      }
    },
    
    async handleAnnotationsUpdated(updateData = {}) {
      console.log('Annotations updated:', updateData)

      try {
        const newAnnotations = Array.isArray(updateData.annotations) ? updateData.annotations : []
        const canvasRef = this.$refs.annotationsCanvas

        if (
          this.selectedImage &&
          newAnnotations.length > 0 &&
          canvasRef &&
          typeof canvasRef.getImageMetrics === 'function'
        ) {
          const metrics = canvasRef.getImageMetrics()
          const scaleX = Number(metrics?.scaleX) || 0
          const scaleY = Number(metrics?.scaleY) || 0

          if (scaleX > 0 && scaleY > 0 && (scaleX !== 1 || scaleY !== 1)) {
            const updates = newAnnotations
              .filter(ann => ann && ann._id && Array.isArray(ann.bbox) && ann.bbox.length >= 4)
              .map(ann => {
                const [x, y, w, h] = ann.bbox.map(Number)
                const scaledBBox = [x * scaleX, y * scaleY, w * scaleX, h * scaleY]
                return this.store.updateAnnotation(ann._id, { bbox: scaledBBox })
              })

            if (updates.length) {
              await Promise.allSettled(updates)
            }
          }
        }

        if (this.selectedImage) {
          await this.store.loadAnnotations(this.selectedImage._id)
          this.handleAnnotationSaved()
        }

        if (updateData.created_categories && updateData.created_categories.length > 0) {
          await this.store.loadCategories(this.dataset._id)
        }

        if (updateData.message) {
          console.log(updateData.message)
        }
      } catch (error) {
        console.error('Error al refrescar anotaciones tras la predicción:', error)
      }
    },
    
    async handleNavigateToImage(image) {
      if (!image) {
        return
      }

      if (image.video_id) {
        const targetVideo = this.videos.find(video => video._id === image.video_id)
        if (targetVideo) {
          await this.openVideoAnnotator(targetVideo)
          const targetFrameIndex = this.videoFrames.findIndex(frame => frame._id === image._id)
          if (targetFrameIndex >= 0) {
            await this.selectFrame(targetFrameIndex)
          }
          return
        }
      }

      // Cambiar a la nueva imagen
      await this.openAnnotator(image)
      
      // Limpiar predicciones si la predicción automática está deshabilitada
      // (el componente AITools se encargará de esto a través de su watcher)
    },

    async handleNavigateRequest(direction) {
      if (!direction) {
        return
      }

      const offset = direction === 'previous' ? -1 : direction === 'next' ? 1 : 0
      if (offset === 0) {
        return
      }

      if (!this.currentMediaKey) {
        return
      }

      const currentIndex = this.mediaItems.findIndex(entry => entry.id === this.currentMediaKey)
      if (currentIndex === -1) {
        return
      }

      const targetIndex = currentIndex + offset
      if (targetIndex < 0 || targetIndex >= this.mediaItems.length) {
        return
      }

      const target = this.mediaItems[targetIndex]
      if (!target) {
        return
      }

      if (target.type === 'video') {
        await this.openVideoAnnotator(target.item)
      } else {
        await this.openAnnotator(target.item)
      }
    },
    
    // Métodos para videos
    async loadVideos() {
      try {
        const data = await window.apiFetch(`/api/videos?dataset_id=${this.dataset._id}`)
        this.videos = data.videos || []
        this.videoThumbnails = {}

        await Promise.all(
          this.videos.map(video => this.prepareVideoThumbnail(video))
        )
      } catch (error) {
        console.error('Error loading videos:', error)
      }
    },

    async prepareVideoThumbnail(video) {
      if (!video || !video._id) {
        return null
      }

      // Usar thumbnail existente si está disponible
      if (video.thumbnail_frame_id) {
        const url = `http://localhost:5000/api/images/${video.thumbnail_frame_id}/data`
        this.videoThumbnails[video._id] = url
        return url
      }

      try {
        const response = await window.apiFetch(`/api/videos/${video._id}/frames?limit=1`)
        const frame = response.frames && response.frames[0]

        if (frame && frame._id) {
          const url = `http://localhost:5000/api/images/${frame._id}/data`
          this.videoThumbnails[video._id] = url
          video.thumbnail_frame_id = frame._id
          return url
        }
      } catch (error) {
        console.error(`Error loading thumbnail for video ${video._id}:`, error)
      }

      return null
    },

    videoThumbnail(video) {
      if (!video || !video._id) {
        return null
      }
      return this.videoThumbnails[video._id] || null
    },
    
    async openVideoAnnotator(video) {
      this.selectedVideo = video
      this.selectedImage = null
      
      // Cargar frames del video
      await this.loadVideoFrames(video._id)
      
      // Abrir el anotador con el primer frame
      if (this.videoFrames.length > 0) {
        this.currentFrameIndex = 0
        this.selectedImage = this.videoFrames[0]
        // Establecer imagen actual en el store para que el canvas se actualice
        await this.store.setCurrentImage(this.selectedImage)
        await this.store.loadAnnotations(this.selectedImage._id)
      }
    },
    
    async loadVideoFrames(videoId) {
      try {
        const data = await window.apiFetch(`/api/videos/${videoId}/frames`)
        this.videoFrames = data.frames || []
      } catch (error) {
        console.error('Error loading video frames:', error)
      }
    },
    
    async selectFrame(index) {
      this.currentFrameIndex = index
      if (this.videoFrames[index]) {
        this.selectedImage = this.videoFrames[index]
        // Establecer imagen actual en el store para que el canvas se actualice
        await this.store.setCurrentImage(this.selectedImage)
        await this.store.loadAnnotations(this.selectedImage._id)
      }
    },
    
    previousFrame() {
      if (this.selectedVideo && this.currentFrameIndex > 0) {
        this.selectFrame(this.currentFrameIndex - 1)
      }
    },
    
    nextFrame() {
      if (this.selectedVideo && this.currentFrameIndex < this.videoFrames.length - 1) {
        this.selectFrame(this.currentFrameIndex + 1)
      }
    },
    
    closeVideoAnnotator() {
      this.selectedImage = null
      this.selectedVideo = null
      this.videoFrames = []
      this.currentFrameIndex = 0
    },
    
    async deleteVideo(video) {
      if (!confirm(`¿Estás seguro de que quieres eliminar el video "${video.filename}" y todos sus frames?`)) {
        return
      }
      
      try {
        await window.apiFetch(`/api/videos/${video._id}`, {
          method: 'DELETE'
        })
        
        // Recargar lista de videos
        await this.loadVideos()
        
        // Recargar imágenes (se eliminaron los frames)
        await this.store.loadImages(this.dataset._id)
      } catch (error) {
        console.error('Error deleting video:', error)
        alert('Error al eliminar el video')
      }
    },
    
    formatDuration(seconds) {
      if (!seconds) return '0:00'
      const mins = Math.floor(seconds / 60)
      const secs = Math.floor(seconds % 60)
      return `${mins}:${secs.toString().padStart(2, '0')}`
    },
    
    formatTimestamp(seconds) {
      if (!seconds && seconds !== 0) return '0:00'
      const mins = Math.floor(seconds / 60)
      const secs = (seconds % 60).toFixed(2)
      // Mostrar minutos:segundos exactos redondeados (MM:SS.xx)
      return `${mins}:${parseFloat(secs).toFixed(2).padStart(5, '0')}`
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
  padding: 12px 20px;
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
  font-size: 0.85rem;
  color: #495057;
  padding: 8px 12px;
  border-radius: 6px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-right: 1rem;
  font-weight: 500;
}

.back-btn .fas {
  font-size: 0.8rem;
}

.back-text {
  font-size: 0.85rem;
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
  font-size: 1.5rem;
  line-height: 1.2;
}

.dataset-info p {
  margin: 2px 0 0 0;
  color: #6c757d;
  font-size: 0.85rem;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.header-actions .btn {
  padding: 8px 14px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.header-actions .btn i {
  font-size: 14px;
}

.header-actions .btn-text {
  display: inline;
}

@media (max-width: 1200px) {
  .header-actions .btn-text {
    display: none;
  }
  
  .header-actions .btn {
    padding: 8px 12px;
  }
}

.btn-success {
  background-color: #28a745;
  color: white;
}

.btn-info {
  background-color: #17a2b8;
  color: white;
}

.btn-info:hover {
  background-color: #138496;
}

.btn-warning {
  background-color: #ff9800;
  color: white;
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
  padding: 15px;
  display: flex;
  flex-direction: column;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.images-container {
  flex: 1;
  display: flex;
}

.pagination-container {
  flex-shrink: 0;
  background: white;
  border-top: 1px solid #dee2e6;
  padding-top: 10px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #ffffff;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 15px;
  color: #495057;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.filter-label {
  font-weight: 600;
  font-size: 0.95rem;
  color: #343a40;
}

.filter-select-wrapper {
  position: relative;
  flex: 0 0 260px;
}

.filter-select {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
  border: 2px solid #e9ecef;
  border-radius: 10px;
  padding: 12px 16px;
  font-size: 0.95rem;
  font-weight: 500;
  color: #495057;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.06);
  background-clip: padding-box;
}

.filter-select:hover,
.filter-select.open {
  border-color: #4a90e2;
  box-shadow: 0 6px 18px rgba(74, 144, 226, 0.18);
  transform: translateY(-1px);
}

.filter-select:focus-visible {
  outline: none;
  border-color: #4a90e2;
  box-shadow: 0 0 0 4px rgba(74, 144, 226, 0.15), 0 6px 18px rgba(74, 144, 226, 0.18);
}

.filter-select__value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.filter-select .dropdown-icon {
  font-size: 0.75rem;
  color: #4a90e2;
  transition: transform 0.25s ease;
}

.filter-select.open .dropdown-icon {
  transform: rotate(-180deg);
}

.filter-options {
  position: absolute;
  top: calc(100% + 10px);
  left: 0;
  right: 0;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.12);
  list-style: none;
  margin: 0;
  padding: 8px;
  z-index: 25;
  animation: dropdown-fade 0.18s ease;
}

.filter-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  color: #4a4a4a;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-option + .filter-option {
  margin-top: 4px;
}

.filter-option:hover {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  color: #2c3e50;
  transform: translateX(2px);
}

.filter-option.active {
  background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
  color: #ffffff;
  box-shadow: 0 8px 16px rgba(74, 144, 226, 0.25);
}

.filter-option.active i {
  color: inherit;
}

.filter-option i {
  font-size: 0.75rem;
  color: #adb5bd;
}

@keyframes dropdown-fade {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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
  padding: 40px 20px; /* Padding reducido */
  color: #6c757d;
}

.no-images .btn-primary {
  margin-top: 20px;
}

.no-images i {
  font-size: 3rem; /* Icono más pequeño */
  margin-bottom: 15px; /* Margen reducido */
  color: #dee2e6;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
  width: 100%;
  padding: 10px 0;
}

/* Ajustes para pantallas muy anchas */
@media (min-width: 1800px) {
  .image-grid {
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 15px;
  }
}

/* Para pantallas estándar, mantener tarjetas pequeñas */
@media (max-width: 1600px) and (min-width: 1200px) {
  .image-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 10px;
  }
}

.image-card {
  background: white;
  border-radius: 6px;
  border: 1px solid #dee2e6;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  display: flex;
  flex-direction: column;
  height: 201px; /* Aumenta el alto para más espacio */
}

.image-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  transform: translateY(-2px);
}

.image-card img {
  width: 100%;
  height: 140px;
  object-fit: cover;
  flex-shrink: 0;
}

.image-info {
  padding: 6px 8px;/* Más espacio arriba y abajo */
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: white;
}

.filename {
  font-weight: 500;
  margin: 0 0 2px 0; /* Más margen inferior para que no se corte */
  font-size: 0.75rem;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}

.annotations-count {
  margin: 0;
  color: #6c757d;
  font-size: 0.7rem;
  line-height: 1.2;
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
  width: 26px;
  height: 26px;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  font-size: 0.7rem;
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
  overflow: hidden;
}

.annotator-sidebar {
  width: 380px;
  background: #f8f9fa;
  border-right: 1px solid #dee2e6;
  overflow-y: auto;
  flex-shrink: 0;
}

.annotator-main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
  min-height: 0;
}

.annotator-canvas {
  flex: 1;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
  min-height: 0;
  padding: 20px;
}
.canvas-flex {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
}

.annotator-ai-sidebar {
  width: 350px;
  background: #f8f9fa;
  border-left: 1px solid #dee2e6;
  overflow-y: auto;
  flex-shrink: 0;
}

/* Paginación */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
}

.pagination-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 0.4rem 0.8rem; /* Más compacto */
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem; /* Texto más pequeño */
  font-weight: 500;
  transition: all 0.2s ease;
}

.pagination-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
  opacity: 0.6;
}

.pagination-btn:hover:not(:disabled) {
  background: #2980b9;
  transform: translateY(-1px);
  box-shadow: 0 2px 5px rgba(0,0,0,0.15);
}

.page-numbers {
  display: flex;
  gap: 0.25rem;
}

.page-btn {
  background: white;
  color: #3498db;
  border: 1px solid #3498db;
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  min-width: 36px;
  transition: all 0.2s ease;
}

.page-btn:hover {
  background: #3498db;
  color: white;
  transform: translateY(-1px);
  box-shadow: 0 2px 5px rgba(0,0,0,0.15);
}

.page-btn.active {
  background: #3498db;
  color: white;
  box-shadow: 0 2px 5px rgba(52, 152, 219, 0.3);
}

.page-info {
  text-align: center;
  color: #6c757d;
  font-size: 0.8rem; /* Texto más pequeño */
  padding: 0.3rem 0 0; /* Padding reducido */
  margin: 0;
}

.page-info .separator {
  margin: 0 0.5rem;
  color: #bdc3c7;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 15px;
  margin-bottom: 18px;
  border-bottom: 1px solid #495057;
}
.sidebar-header i {
  font-size: 1.15rem;
  color: #adb5bd;
}
.sidebar-header h3 {
  margin: 0;
  font-size: 1.08rem;
  font-weight: 600;
  color: #ffffff;
}
.sidebar-stats-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sidebar-stat-card {
  background: #495057;
  border-radius: 8px;
  padding: 7px 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: box-shadow 0.18s, background 0.18s;
  box-shadow: 0 2px 10px rgba(0,0,0,0.10);
  border: 1px solid #3a3f44;
}
.sidebar-stat-card:hover {
  background: #5a6268;
  box-shadow: 0 4px 16px rgba(52,152,219,0.10);
}
.sidebar-stat-icon {
  font-size: 1rem;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
}
.sidebar-icon-images {
  color: #4da3ff;
  background: rgba(77, 163, 255, 0.15);
}

.sidebar-icon-videos {
  color: #26c6da;
  background: rgba(38, 198, 218, 0.15);
}
.sidebar-icon-annotations {
  color: #f39c12;
  background: rgba(243, 156, 18, 0.15);
}
.sidebar-icon-with {
  color: #28a745;
  background: rgba(40,167,69,0.12);
}
.sidebar-icon-without {
  color: #e74c3c;
  background: rgba(231,76,60,0.12);
}
.sidebar-stat-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.sidebar-stat-label {
  font-size: 0.78rem;
  color: #ced4da;
  font-weight: 500;
}
.sidebar-stat-value {
  font-size: 1.08rem;
  color: #fff;
  font-weight: 700;
  letter-spacing: 0.5px;
}

/* Media queries adicionales para optimizar la distribución */
@media (max-width: 1200px) {
  .image-grid {
    grid-template-columns: repeat(6, 1fr); /* 6 columnas: 3-4 filas */
    gap: 8px;
  }
  
  .image-card {
    min-height: 140px;
    max-height: 180px;
  }
}

@media (max-width: 900px) {
  .image-grid {
    grid-template-columns: repeat(5, 1fr); /* 5 columnas: 4-5 filas */
    gap: 6px;
  }
  
  .image-card {
    min-height: 120px;
    max-height: 160px;
  }

  .filename {
    font-size: 0.75rem;
  }
  
  .annotations-count {
    font-size: 0.7rem;
  }
}

/* Estilos para videos mezclados con imágenes */
.image-card.video-card:hover {
  box-shadow: 0 6px 16px rgba(0,0,0,0.15);
  transform: translateY(-3px);
  border-color: #667eea;
}

.video-thumbnail {
  position: relative;
  width: 100%;
  height: 140px;  /* Mismo alto que las imágenes */
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.video-thumbnail.has-thumbnail {
  background: #000;
}

.video-thumbnail-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 12px 12px 0 0;
}

.video-duration {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.75);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
}



/* Navegador de frames */
.frames-navigator {
  flex-shrink: 0;
  background: #2c3e50;
  padding: 0.75rem 1rem;
  border-top: 2px solid #34495e;
  min-height: 160px;
  max-height: 160px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.frames-scroll {
  display: flex;
  gap: 0.75rem;
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 0.5rem;
  flex: 1;
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
  cursor: pointer;
  border: 3px solid transparent;
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
  box-shadow: 0 0 12px rgba(230, 126, 34, 0.6);
}

.frame-thumbnail img {
  width: 100%;
  height: 65px;
  object-fit: contain;
  background-color: #000;
  display: block;
}

.frame-info {
  padding: 0.35rem 0.4rem;;
  display: flex;
  flex-direction: column;
  background: #34495e;
}

.frame-number {
  font-size: 0.72rem;
  color: #ecf0f1;
  font-weight: 600;
  line-height: 1.2;
}

.frame-time {
  font-size: 0.68rem;
  color: #95a5a6;
  line-height: 1.2;
}

.frame-annotations {
  font-size: 0.7rem;
  color: #e67e22;
  font-weight: 700;
  line-height: 1.2;
}
</style>