<template>
  <div class="ai-tools">
    <h3>
      <i class="fas fa-robot"></i>
      Herramientas de IA
    </h3>
    
    <!-- Selección de modelo -->
    <div class="ai-section">
      <h4>Modelo de IA</h4>
      
      <div v-if="isLoadingSavedModels" class="loading-indicator">
        <i class="fas fa-spinner fa-spin"></i>
        <span>Cargando modelos...</span>
      </div>
      
      <div v-else>
        <!-- Desplegable de modelos precargados -->
        <div v-if="preloadedModels.length > 0" class="models-accordion">
          <div class="accordion-header" @click="togglePreloadedModels">
            <div class="accordion-title">
              <i class="fas fa-star"></i>
              <strong>Modelos Precargados</strong>
              <span class="model-count">({{ preloadedModels.length }})</span>
            </div>
            <i class="fas fa-chevron-down accordion-icon" :class="{ 'expanded': showPreloadedModels }"></i>
          </div>
          <div v-show="showPreloadedModels" class="accordion-content">
            <div class="models-list">
              <div 
                v-for="model in preloadedModels" 
                :key="model.id"
                class="model-item"
                :class="{
                  'active': isModelLoaded && loadedModelId === model.id,
                  'loading': isLoadingModel && selectedSavedModel === model.id
                }"
              >
                <div class="model-info">
                  <div class="model-name">
                    <strong>{{ model.name }}</strong>
                  </div>
                  <small class="model-meta">{{ model.categories?.length || 0 }} categorías</small>
                </div>
                <button 
                  class="btn-load"
                  :class="{ 'active': isModelLoaded && loadedModelId === model.id }"
                  :disabled="isLoadingModel || (isModelLoaded && loadedModelId === model.id)"
                  @click="selectAndLoadModel(model.id)"
                >
                  <i v-if="isLoadingModel && selectedSavedModel === model.id" class="fas fa-spinner fa-spin"></i>
                  <i v-else-if="isModelLoaded && loadedModelId === model.id" class="fas fa-check"></i>
                  <i v-else class="fas fa-play"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Desplegable de modelos personalizados -->
        <div v-if="customModels.length > 0" class="models-accordion">
          <div class="accordion-header" @click="toggleCustomModels">
            <div class="accordion-title">
              <i class="fas fa-cube"></i>
              <strong>Modelos Personalizados</strong>
              <span class="model-count">({{ customModels.length }})</span>
            </div>
            <i class="fas fa-chevron-down accordion-icon" :class="{ 'expanded': showCustomModels }"></i>
          </div>
          <div v-show="showCustomModels" class="accordion-content">
            <div class="models-list">
              <div 
                v-for="model in customModels" 
                :key="model.id"
                class="model-item"
                :class="{
                  'active': isModelLoaded && loadedModelId === model.id,
                  'loading': isLoadingModel && selectedSavedModel === model.id
                }"
              >
                <div class="model-info">
                  <div class="model-name">
                    <strong>{{ model.name }}</strong>
                  </div>
                  <small class="model-meta">{{ model.categories?.length || 0 }} categorías</small>
                </div>
                <button 
                  class="btn-load"
                  :class="{ 'active': isModelLoaded && loadedModelId === model.id }"
                  :disabled="isLoadingModel || (isModelLoaded && loadedModelId === model.id)"
                  @click="selectAndLoadModel(model.id)"
                >
                  <i v-if="isLoadingModel && selectedSavedModel === model.id" class="fas fa-spinner fa-spin"></i>
                  <i v-else-if="isModelLoaded && loadedModelId === model.id" class="fas fa-check"></i>
                  <i v-else class="fas fa-play"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Mensaje cuando no hay modelos -->
        <div v-if="preloadedModels.length === 0 && customModels.length === 0" class="no-models">
          <i class="fas fa-inbox"></i>
          <p>No hay modelos disponibles</p>
        </div>
        
        <!-- Hint para gestionar modelos -->
        <div class="models-hint">
          <i class="fas fa-info-circle"></i>
          <span>Gestiona tus modelos desde la sección <strong>Modelos</strong> en el menú superior</span>
        </div>
      </div>
      
      <!-- Estado del modelo cargado -->
      <div v-if="isModelLoaded" class="model-status loaded">
        <i class="fas fa-check-circle"></i>
        <div class="status-info">
          <strong>{{ loadedModelName }}</strong>
          <span>Modelo cargado</span>
        </div>
        <button @click="unloadModel" class="btn btn-sm btn-outline" title="Eliminar modelo">
          <i class="fas fa-times"></i>
        </button>
      </div>
      
      <div v-else-if="modelError" class="model-status error">
        <i class="fas fa-exclamation-triangle"></i>
        <span>{{ modelError }}</span>
      </div>
    </div>
    
    <!-- Sección de predicción -->
    <div class="ai-section">
      <h4>Predicción</h4>
      
      <!-- Configuración de confianza -->
      <div class="form-group">
        <label for="confidence">
          Umbral de confianza: {{ confidence }}
          <i class="fas fa-info-circle" title="Determina qué tan seguro debe estar el modelo para mostrar una detección. 0.1 = muy permisivo, 0.8 = muy estricto"></i>
        </label>
        <input 
          id="confidence"
          v-model.number="confidence"
          type="range"
          min="0.1"
          max="1.0"
          step="0.05"
          class="form-control range-input"
          :disabled="!isModelLoaded"
        />
        <div class="confidence-guide">
          <small>
            <strong>Guía:</strong>
            0.1-0.3 (Permisivo) | 0.4-0.6 (Equilibrado) | 0.7-1.0 (Estricto)
          </small>
        </div>
      </div>
      
      <!-- Botón de predicción -->
      <button 
        @click="predictImage"
        class="btn btn-success"
        :disabled="!canPredict || isPredicting"
      >
        <i v-if="isPredicting" class="fas fa-spinner fa-spin"></i>
        <i v-else class="fas fa-magic"></i>
        {{ isPredicting ? 'Prediciendo...' : 'Predecir Imagen' }}
      </button>
      
      <!-- Resultados de predicción -->
      <div v-if="lastPrediction" class="prediction-results">
        <h5>Últimos resultados:</h5>
        <div v-if="lastPrediction.detections && lastPrediction.detections.length > 0">
          <p><strong>{{ lastPrediction.detections.length }}</strong> detecciones encontradas</p>
          <div class="detections-summary">
            <div 
              v-for="detection in lastPrediction.detections.slice(0, 5)" 
              :key="`${detection.bbox[0]}-${detection.bbox[1]}`"
              class="detection-item"
            >
              <span class="detection-class">{{ getClassName(detection.class) }}</span>
              <span class="detection-confidence">{{ (detection.confidence * 100).toFixed(1) }}%</span>
            </div>
            <div v-if="lastPrediction.detections.length > 5" class="more-detections">
              +{{ lastPrediction.detections.length - 5 }} más...
            </div>
          </div>
        </div>
        <div v-else>
          <p>No se encontraron detecciones</p>
        </div>
      </div>
    </div>
    
    <!-- Navegación entre imágenes -->
    <div class="ai-section">
      <h4>Navegación</h4>
      <div class="navigation-controls">
        <button 
          @click="goToPreviousImage"
          class="btn btn-outline"
          :disabled="!canNavigatePrevious"
        >
          <i class="fas fa-chevron-left"></i>
          Anterior
        </button>
        
        <button 
          @click="goToNextImage"
          class="btn btn-outline"
          :disabled="!canNavigateNext"
        >
          Siguiente
          <i class="fas fa-chevron-right"></i>
        </button>
      </div>
      
      <div v-if="isModelLoaded" class="auto-predict">
        <label>
          <input 
            v-model="autoPredictOnNavigate" 
            type="checkbox"
          />
          Predecir automáticamente al cambiar imagen
        </label>
      </div>
    </div>

  </div>
</template>

<script>
import { useAnnotationStore } from '@/stores/annotationStore'

export default {
  name: 'AITools',
  props: {
    currentImage: {
      type: Object,
      default: null
    },
    datasetId: {
      type: String,
      required: true
    },
    canNavigatePrevious: {
      type: Boolean,
      default: false
    },
    canNavigateNext: {
      type: Boolean,
      default: false
    }
  },
  setup() {
    const store = useAnnotationStore()
    return { store }
  },
  data() {
    return {
      // Estado del modelo
      loadedModelName: '',
      loadedModelId: null,
      isModelLoaded: false,
      isLoadingModel: false,
      modelError: null,
      modelCategories: [],
      
      // Modelos guardados
      preloadedModels: [],
      customModels: [],
      selectedSavedModel: '',
      isLoadingSavedModels: false,
      
      // Estado de los desplegables
      showPreloadedModels: false,
      showCustomModels: false,
      
      // Configuración de predicción
      confidence: 0.5,
      isPredicting: false,
      lastPrediction: null,
      
      // Navegación
      autoPredictOnNavigate: true
    }
  },
  computed: {
    canPredict() {
      return this.isModelLoaded && this.currentImage && !this.isPredicting
    }
  },
  watch: {
    currentImage: {
      handler(newImage, oldImage) {
        if (newImage && oldImage && newImage._id !== oldImage._id) {
          if (this.autoPredictOnNavigate && this.isModelLoaded) {
            // Pequeño delay para asegurar que la imagen se haya cargado
            setTimeout(() => {
              this.predictImage()
            }, 500)
          }
        }
      },
      immediate: false
    }
  },
  
  async mounted() {
    await this.loadSavedModelsList()
  },
  
  methods: {
    togglePreloadedModels() {
      this.showPreloadedModels = !this.showPreloadedModels
    },
    
    toggleCustomModels() {
      this.showCustomModels = !this.showCustomModels
    },
    
    async loadSavedModelsList() {
      this.isLoadingSavedModels = true
      try {
        const result = await this.$apiGet('/api/ai/saved-models')
        this.preloadedModels = result.preloaded || []
        this.customModels = result.custom || []
      } catch (error) {
        console.error('Error al cargar modelos guardados:', error)
      } finally {
        this.isLoadingSavedModels = false
      }
    },
    
    async selectAndLoadModel(modelId) {
      if (!modelId || this.isLoadingModel) return
      if (this.isModelLoaded && this.loadedModelId === modelId) return
      
      this.selectedSavedModel = modelId
      await this.loadSavedModel()
    },
    
    async loadSavedModel() {
      if (!this.selectedSavedModel) return
      
      this.isLoadingModel = true
      this.modelError = null
      
      try {
        const result = await this.$apiPost('/api/ai/load-saved-model', {
          model_id: this.selectedSavedModel,
          dataset_id: this.datasetId
        })
        
        this.isModelLoaded = true
        this.loadedModelName = result.model_info.name
        this.loadedModelId = result.model_info.id
        this.modelCategories = result.categories || []

        const createdCount = result.created_categories ? result.created_categories.length : 0
        if (this.datasetId) {
          await this.store.loadCategories(this.datasetId)
        }

        if (createdCount > 0) {
          console.log(`Se crearon ${createdCount} categorías automáticamente`)
        }
        
        this.$emit('model-loaded', {
          name: this.loadedModelName,
          categories: this.modelCategories
        })
      } catch (error) {
        console.error('Error loading saved model:', error)
        this.modelError = error.message || 'Error al cargar el modelo guardado'
      } finally {
        this.isLoadingModel = false
      }
    },
    
    async unloadModel() {
      try {
        await this.$apiPost('/api/ai/unload-model', {})
        
        this.isModelLoaded = false
        this.loadedModelName = ''
        this.loadedModelId = null
        this.modelCategories = []
        this.lastPrediction = null
        this.selectedSavedModel = ''
        
        // Las anotaciones se manejan automáticamente por el store
        
        this.$emit('model-unloaded')
      } catch (error) {
        console.error('Error unloading model:', error)
      }
    },
    
    async predictImage() {
      if (!this.canPredict) return
      
      this.isPredicting = true
      
      try {
        const result = await this.$apiPost('/api/ai/predict', {
          image_id: this.currentImage._id,
          confidence: this.confidence
        })
        
        this.lastPrediction = result
        
        // Las predicciones ahora se guardan automáticamente como anotaciones en el backend
        // Solo necesitamos notificar que se crearon nuevas anotaciones
        const detectionCount = result.detections ? result.detections.length : 0
        const annotationsCreated = result.annotations ? result.annotations.length : 0
        
        // Emitir evento para refrescar las anotaciones en el canvas
        this.$emit('annotations-updated', {
          annotations: result.annotations || [],
          created_categories: result.created_categories || [],
          message: result.message || `Se crearon ${annotationsCreated} anotaciones de ${detectionCount} detecciones.`
        })
        
        // Log para depuración
        console.log(`Predicción completada: ${detectionCount} detecciones encontradas, ${annotationsCreated} anotaciones creadas automáticamente`)
        
        // Mostrar mensaje informativo si se crearon categorías
        if (result.created_categories && result.created_categories.length > 0) {
          const categoryNames = result.created_categories.map(cat => cat.name).join(', ')
          console.log(`Se crearon automáticamente las categorías: ${categoryNames}`)
        }
      } catch (error) {
        console.error('Error predicting image:', error)
        
        // Mostrar error más detallado
        let errorMessage = 'Error en la predicción'
        const errorStr = error.message || ''
        if (errorStr.includes('bytes-like object is required')) {
          errorMessage = 'Error de formato de imagen. La imagen puede estar corrupta.'
        } else if (errorStr.includes('No hay modelo cargado')) {
          errorMessage = 'No hay modelo cargado. Por favor, carga un modelo primero.'
        } else if (errorStr.includes('No se pueden crear anotaciones sin categorías')) {
          errorMessage = 'No hay categorías disponibles. Las categorías del modelo se crearán automáticamente en la primera predicción.'
        } else {
          errorMessage = errorStr || 'Error de conexión durante la predicción.'
        }
        
        alert(errorMessage)
      } finally {
        this.isPredicting = false
      }
    },
    
    getClassName(classIndex) {
      return this.modelCategories[classIndex] || `Clase ${classIndex}`
    },
    
    goToPreviousImage() {
      if (!this.canNavigatePrevious) {
        return
      }

      this.$emit('navigate', 'previous')
    },
    
    goToNextImage() {
      if (!this.canNavigateNext) {
        return
      }

      this.$emit('navigate', 'next')
    }
  }
}
</script>

<style scoped>
.ai-tools {
  background: white;
  border-radius: 0.5rem;
  border: 0.0625rem solid #e0e0e0;
  overflow: hidden;
}

.ai-tools h3 {
  background: #f8f9fa;
  margin: 0;
  padding: 0.9375rem 1.25rem;
  border-bottom: 0.0625rem solid #e0e0e0;
  color: #495057;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.ai-tools h3 i {
  color: #6f42c1;
}

.ai-section {
  padding: 1.25rem;
  border-bottom: 0.0625rem solid #f0f0f0;
}

.ai-section:last-child {
  border-bottom: none;
}

.ai-section h4 {
  margin: 0 0 0.9375rem 0;
  color: #343a40;
  font-size: 0.95rem;
  font-weight: 600;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.9375rem;
  background: #f8f9fa;
  border-radius: 0.375rem;
  color: #6c757d;
  font-size: 0.9rem;
}

.models-accordion {
  margin-bottom: 0.75rem;
  border: 0.0625rem solid #dee2e6;
  border-radius: 0.375rem;
  overflow: hidden;
  background: white;
}

.accordion-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 0.9375rem;
  background: #f8f9fa;
  cursor: pointer;
  transition: background 0.2s;
  user-select: none;
}

.accordion-header:hover {
  background: #e9ecef;
}

.accordion-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #495057;
}

.accordion-title i {
  color: #f59e0b;
}

.accordion-title i.fa-cube {
  color: #3b82f6;
}

.accordion-title strong {
  font-weight: 600;
}

.model-count {
  font-size: 0.85rem;
  color: #6c757d;
  font-weight: normal;
}

.accordion-icon {
  color: #6c757d;
  transition: transform 0.3s ease;
  font-size: 0.85rem;
}

.accordion-icon.expanded {
  transform: rotate(180deg);
}

.accordion-content {
  padding: 0.75rem;
  background: white;
  border-top: 0.0625rem solid #e9ecef;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-0.625rem);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.models-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.model-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.625rem 0.75rem;
  background: #f8f9fa;
  border: 0.0625rem solid #e9ecef;
  border-radius: 0.25rem;
  transition: all 0.2s;
}

.model-item:hover {
  background: #e9ecef;
  border-color: #dee2e6;
  transform: translateX(0.125rem);
}

.model-item.active {
  background: #d4edda;
  border-color: #c3e6cb;
  box-shadow: 0 0 0 0.125rem rgba(40, 167, 69, 0.1);
}

.model-item.loading {
  opacity: 0.7;
}

.model-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.model-name {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.9rem;
  color: #495057;
}

.model-name i {
  font-size: 0.85rem;
  color: #f59e0b;
}

.model-name i.fa-cube {
  color: #3b82f6;
}

.model-meta {
  font-size: 0.8rem;
  color: #6c757d;
}

.btn-load {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.375rem;
  border: 0.0625rem solid #dee2e6;
  background: white;
  color: #495057;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-load:hover:not(:disabled) {
  background: #007bff;
  color: white;
  border-color: #007bff;
  transform: scale(1.05);
}

.btn-load.active {
  background: #28a745;
  color: white;
  border-color: #28a745;
}

.btn-load:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.no-models {
  text-align: center;
  padding: 1.875rem 1.25rem;
  color: #6c757d;
}

.no-models i {
  font-size: 2.5rem;
  margin-bottom: 0.625rem;
  opacity: 0.3;
}

.no-models p {
  margin: 0;
  font-size: 0.9rem;
}

.models-hint {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #e7f3ff;
  border: 0.0625rem solid #b3d9ff;
  border-radius: 0.375rem;
  font-size: 0.85rem;
  color: #004085;
  margin-top: 0.9375rem;
}

.models-hint i {
  margin-top: 0.125rem;
  flex-shrink: 0;
}

.model-status {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.625rem;
  border-radius: 0.25rem;
  margin-top: 0.9375rem;
  font-size: 0.9rem;
}

.model-status.loaded {
  background-color: #d4edda;
  color: #155724;
  border: 0.0625rem solid #c3e6cb;
}

.model-status.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 0.0625rem solid #f5c6cb;
}

.status-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.status-info strong {
  margin-bottom: 0.125rem;
}

.status-info span {
  font-size: 0.8rem;
  opacity: 0.8;
}

.form-group {
  margin-bottom: 0.9375rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.3125rem;
  font-weight: 500;
  color: #495057;
  font-size: 0.9rem;
}

.form-group label i {
  margin-left: 0.3125rem;
  color: #6c757d;
  cursor: help;
}

.confidence-guide {
  margin-top: 0.3125rem;
  text-align: center;
}

.confidence-guide small {
  color: #6c757d;
  font-size: 0.8rem;
}

.form-control {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 0.0625rem solid #ced4da;
  border-radius: 0.25rem;
  font-size: 0.9rem;
  transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.form-control:focus {
  outline: none;
  border-color: #80bdff;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

.form-control:disabled {
  background-color: #e9ecef;
  opacity: 1;
}

.range-input {
  padding: 0;
  height: 1.875rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 0.25rem;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  text-decoration: none;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-success {
  background-color: #28a745;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background-color: #1e7e34;
}

.btn-outline {
  background-color: transparent;
  color: #6c757d;
  border: 0.0625rem solid #6c757d;
}

.btn-outline:hover:not(:disabled) {
  background-color: #6c757d;
  color: white;
}

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.8rem;
}

.categories-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 9.375rem;
  overflow-y: auto;
}

.category-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.375rem 0.625rem;
  background-color: #f8f9fa;
  border-radius: 0.25rem;
  border: 0.0625rem solid #e9ecef;
}

.category-index {
  background-color: #6c757d;
  color: white;
  padding: 0.125rem 0.375rem;
  border-radius: 0.75rem;
  font-size: 0.8rem;
  font-weight: 500;
  min-width: 1.5rem;
  text-align: center;
}

.category-name {
  font-weight: 500;
  color: #495057;
}

.prediction-results {
  margin-top: 0.9375rem;
  padding: 0.75rem;
  background-color: #f8f9fa;
  border-radius: 0.25rem;
  border: 0.0625rem solid #e9ecef;
}

.prediction-results h5 {
  margin: 0 0 0.625rem 0;
  color: #495057;
  font-size: 0.9rem;
}

.detections-summary {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.detection-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.25rem 0.5rem;
  background-color: white;
  border-radius: 0.1875rem;
  border: 0.0625rem solid #dee2e6;
  font-size: 0.85rem;
}

.detection-class {
  font-weight: 500;
  color: #495057;
}

.detection-confidence {
  color: #28a745;
  font-weight: 600;
}

.more-detections {
  text-align: center;
  color: #6c757d;
  font-style: italic;
  font-size: 0.8rem;
  padding: 0.25rem;
}

.navigation-controls {
  display: flex;
  gap: 0.625rem;
  margin-bottom: 0.625rem;
}

.navigation-controls .btn {
  flex: 1;
  justify-content: center;
}

.auto-predict {
  margin-top: 0.625rem;
}

.auto-predict label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #495057;
  cursor: pointer;
  font-weight: normal;
}

.auto-predict input[type="checkbox"] {
  margin: 0;
}

/* Estilos para la sección de ayuda */
.help-section {
  border: 0.125rem solid #e3f2fd;
  border-radius: 0.5rem;
  background: linear-gradient(135deg, #f8f9ff 0%, #e3f2fd 100%);
  margin-top: 0.9375rem;
}

.help-section h4 {
  color: #1976d2;
  margin-bottom: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.help-content {
  font-size: 0.85rem;
}

.help-content p {
  margin: 0 0 0.625rem 0;
  color: #424242;
  font-weight: 500;
}

.help-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0.5rem 0;
  padding: 0.375rem 0.5rem;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 0.25rem;
  color: #424242;
}

.help-item i {
  width: 1rem;
  text-align: center;
}

.help-item strong {
  min-width: 3.75rem;
}

.help-note {
  margin-top: 0.75rem;
  padding: 0.5rem;
  background: rgba(25, 118, 210, 0.1);
  border-radius: 0.25rem;
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.help-note i {
  color: #1976d2;
  margin-top: 0.125rem;
}

.help-note small {
  color: #424242;
  line-height: 1.3;
}

.text-success {
  color: #28a745 !important;
}

.text-danger {
  color: #dc3545 !important;
}

/* Estilos para el separador */
.separator {
  margin: 0.9375rem 0;
  text-align: center;
  position: relative;
}

.separator::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 0.0625rem;
  background: #dee2e6;
}

.separator span {
  background: white;
  padding: 0 0.625rem;
  color: #6c757d;
  font-size: 0.85rem;
  position: relative;
  z-index: 1;
}
</style>