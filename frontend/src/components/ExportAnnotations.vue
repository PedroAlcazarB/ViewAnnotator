<template>
  <div class="export-annotations-modal" v-if="show" @click.self="closeModal">
    <div class="modal-content">
      <div class="modal-header">
        <h2>Exportar Anotaciones</h2>
        <button @click="closeModal" class="close-btn">
          <i class="fas fa-times"></i>
        </button>
      </div>

      <div class="modal-body">
        <!-- Selector de formato -->
        <div class="format-selector">
          <h3>Selecciona el formato de exportación</h3>
          <div class="format-options">
            <label class="format-option" :class="{ active: selectedFormat === 'coco' }">
              <input type="radio" value="coco" v-model="selectedFormat" />
              <div class="option-content">
                <i class="fas fa-file-code"></i>
                <strong>COCO</strong>
                <small>JSON con anotaciones en formato MS COCO</small>
              </div>
            </label>

            <label class="format-option" :class="{ active: selectedFormat === 'yolo' }">
              <input type="radio" value="yolo" v-model="selectedFormat" />
              <div class="option-content">
                <i class="fas fa-file-alt"></i>
                <strong>YOLO</strong>
                <small>Archivos .txt con coordenadas normalizadas</small>
              </div>
            </label>

            <label class="format-option" :class="{ active: selectedFormat === 'pascal' }">
              <input type="radio" value="pascal" v-model="selectedFormat" />
              <div class="option-content">
                <i class="fas fa-file-code"></i>
                <strong>PascalVOC</strong>
                <small>Archivos XML con anotaciones</small>
              </div>
            </label>
          </div>
        </div>

        <!-- Información del formato seleccionado -->
        <div v-if="selectedFormat" class="format-info">
          <div v-if="selectedFormat === 'coco'" class="info-box">
            <h4><i class="fas fa-info-circle"></i> Formato COCO</h4>
            <p>Se descargará un archivo JSON con:</p>
            <ul>
              <li>Lista de imágenes con sus metadatos</li>
              <li>Lista de anotaciones con bboxes y segmentaciones</li>
              <li>Lista de categorías</li>
            </ul>
          </div>

          <div v-if="selectedFormat === 'yolo'" class="info-box">
            <h4><i class="fas fa-info-circle"></i> Formato YOLO</h4>
            <p>Se descargará un archivo ZIP que contiene:</p>
            <ul>
              <li>Archivos .txt con el mismo nombre que las imágenes</li>
              <li>Cada línea: <code>class_id center_x center_y width height</code></li>
              <li>Archivo classes.txt con las clases (una por línea)</li>
              <li>Este formato no soporta polígonos; las anotaciones de polígonos se exportarán como rectángulos.</li>
            </ul>
          </div>

          <div v-if="selectedFormat === 'pascal'" class="info-box">
            <h4><i class="fas fa-info-circle"></i> Formato PascalVOC</h4>
            <p>Se descargará un archivo ZIP que contiene:</p>
            <ul>
              <li>Archivos .xml con el mismo nombre que las imágenes</li>
              <li>Cada XML contiene las anotaciones con coordenadas absolutas</li>
              <li>Este formato no soporta polígonos; las anotaciones de polígonos se exportarán como rectángulos.</li>

            </ul>
          </div>
        </div>

        <!-- Opciones adicionales -->
        <div v-if="selectedFormat" class="export-options">
          <h3>Opciones de exportación</h3>
          
          <div class="option-item">
            <label>
              <input type="checkbox" v-model="includeImages" />
              <span>Incluir imágenes en el ZIP</span>
            </label>
            <small>Si está marcado, las imágenes se incluirán junto con las anotaciones</small>
          </div>

          <div class="option-item">
            <label>
              <input type="checkbox" v-model="onlyAnnotated" />
              <span>Solo imágenes con anotaciones</span>
            </label>
            <small>Excluir imágenes sin anotaciones</small>
          </div>

          <div class="option-item">
            <label>
              <input type="checkbox" v-model="enableSplit" />
              <span>Dividir en Train/Val/Test</span>
            </label>
            <small>Divide las imágenes en conjuntos de entrenamiento, validación y test de forma aleatoria</small>
          </div>

          <!-- Configuración de división -->
          <div v-if="enableSplit" class="split-config">
            <div class="split-header">
              <h4>Configuración de división</h4>
              <span class="total-percentage" :class="{ 'invalid': totalPercentage !== 100 }">
                Total: {{ totalPercentage }}%
                <i v-if="totalPercentage !== 100" class="fas fa-exclamation-triangle"></i>
              </span>
            </div>
            
            <div class="split-item">
              <label>
                <i class="fas fa-graduation-cap"></i>
                <span>Entrenamiento</span>
              </label>
              <div class="slider-container">
                <input 
                  type="range" 
                  v-model.number="trainPercentage" 
                  min="0" 
                  max="100" 
                  step="5"
                  class="percentage-slider"
                />
                <input 
                  type="number" 
                  v-model.number="trainPercentage" 
                  min="0" 
                  max="100" 
                  class="percentage-input"
                />
                <span class="percentage-label">%</span>
              </div>
            </div>

            <div class="split-item">
              <label>
                <i class="fas fa-clipboard-check"></i>
                <span>Validación</span>
              </label>
              <div class="slider-container">
                <input 
                  type="range" 
                  v-model.number="valPercentage" 
                  min="0" 
                  max="100" 
                  step="5"
                  class="percentage-slider"
                />
                <input 
                  type="number" 
                  v-model.number="valPercentage" 
                  min="0" 
                  max="100" 
                  class="percentage-input"
                />
                <span class="percentage-label">%</span>
              </div>
            </div>

            <div class="split-item">
              <label>
                <i class="fas fa-vial"></i>
                <span>Test</span>
              </label>
              <div class="slider-container">
                <input 
                  type="range" 
                  v-model.number="testPercentage" 
                  min="0" 
                  max="100" 
                  step="5"
                  class="percentage-slider"
                />
                <input 
                  type="number" 
                  v-model.number="testPercentage" 
                  min="0" 
                  max="100" 
                  class="percentage-input"
                />
                <span class="percentage-label">%</span>
              </div>
            </div>

            <div v-if="totalPercentage !== 100" class="split-warning">
              <i class="fas fa-exclamation-triangle"></i>
              <span>La suma de los porcentajes debe ser 100%</span>
            </div>

            <div class="split-info">
              <i class="fas fa-info-circle"></i>
              <span>La división se realizará de forma aleatoria. Cada imagen será asignada a un único conjunto (train, val o test).</span>
            </div>
          </div>
        </div>

        <!-- Botones de acción -->
        <div class="modal-actions">
          <button 
            @click="exportAnnotations" 
            :disabled="!selectedFormat || exporting"
            class="btn btn-primary"
          >
            <i class="fas" :class="exporting ? 'fa-spinner fa-spin' : 'fa-download'"></i>
            {{ exporting ? 'Exportando...' : 'Exportar' }}
          </button>
          <button @click="closeModal" class="btn btn-secondary">
            Cancelar
          </button>
        </div>

        <!-- Barra de progreso -->
        <div v-if="exporting" class="progress-section">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progress + '%' }"></div>
          </div>
          <p class="progress-text">{{ progressMessage }}</p>
        </div>

        <!-- Resultado de la exportación -->
        <div v-if="exportResult" class="result-section">
          <div class="result-success">
            <i class="fas fa-check-circle"></i>
            <h4>¡Exportación completada!</h4>
            <div class="result-stats">
              <div class="stat">
                <strong>{{ exportResult.images }}</strong>
                <span>Imágenes</span>
              </div>
              <div class="stat">
                <strong>{{ exportResult.annotations }}</strong>
                <span>Anotaciones</span>
              </div>
              <div class="stat">
                <strong>{{ exportResult.categories }}</strong>
                <span>Categorías</span>
              </div>
            </div>
            <p class="result-message">El archivo se descargó automáticamente</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { useAuthStore } from '@/stores/authStore'

export default {
  name: 'ExportAnnotations',
  props: {
    show: {
      type: Boolean,
      required: true
    },
    datasetId: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      selectedFormat: 'coco',
      includeImages: false,
      onlyAnnotated: true,
      enableSplit: false,
      trainPercentage: 80,
      valPercentage: 10,
      testPercentage: 10,
      exporting: false,
      progress: 0,
      progressMessage: '',
      exportResult: null
    }
  },
  computed: {
    totalPercentage() {
      return this.trainPercentage + this.valPercentage + this.testPercentage
    }
  },
  methods: {
    closeModal() {
      if (!this.exporting) {
        this.resetModal()
        this.$emit('close')
      }
    },
    resetModal() {
      this.selectedFormat = 'coco'
      this.includeImages = false
      this.onlyAnnotated = true
      this.enableSplit = false
      this.trainPercentage = 80
      this.valPercentage = 10
      this.testPercentage = 10
      this.exporting = false
      this.progress = 0
      this.progressMessage = ''
      this.exportResult = null
    },
    async exportAnnotations() {
      // Validar que los porcentajes sumen 100 si la división está habilitada
      if (this.enableSplit && this.totalPercentage !== 100) {
        alert('La suma de los porcentajes debe ser 100%')
        return
      }

      this.exporting = true
      this.progress = 0
      this.exportResult = null
      this.progressMessage = 'Preparando exportación...'

      try {
        // Crear FormData para enviar los parámetros
        const params = new URLSearchParams({
          format: this.selectedFormat,
          include_images: this.includeImages,
          only_annotated: this.onlyAnnotated,
          enable_split: this.enableSplit
        })

        // Agregar porcentajes si la división está habilitada
        if (this.enableSplit) {
          params.append('train_percentage', this.trainPercentage)
          params.append('val_percentage', this.valPercentage)
          params.append('test_percentage', this.testPercentage)
        }

        this.progressMessage = 'Generando archivo de exportación...'
        this.progress = 30

        // Obtener el store de autenticación
        const authStore = useAuthStore()
        
        const response = await fetch(
          `/api/annotations/export/${this.datasetId}?${params}`,
          {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${authStore.token}`
            }
          }
        )

        this.progress = 70

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.message || 'Error al exportar anotaciones')
        }

        this.progressMessage = 'Descargando archivo...'
        this.progress = 90

        // Obtener el blob del archivo
        const blob = await response.blob()
        
        // Determinar el nombre del archivo y extensión
        let filename = `${this.datasetId}_${this.selectedFormat}`
        let extension = ''

        // Lógica corregida que coincide con el backend
        if (this.selectedFormat === 'coco' && !this.enableSplit && !this.includeImages) {
            // Este es el ÚNICO caso que descarga un JSON
          extension = '.json'
        } else {
           // Todos los demás casos (YOLO, Pascal, o COCO con split/imágenes) son ZIP
          extension = '.zip'
        }
        
        filename += extension

        // Crear un enlace temporal y descargarlo
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)

        this.progress = 100
        this.progressMessage = '¡Exportación completada!'

        // Obtener estadísticas reales de la exportación
        await this.fetchExportStats()

        // Esperar un poco antes de permitir cerrar
        setTimeout(() => {
          this.exporting = false
        }, 1000)

      } catch (error) {
        console.error('Error al exportar:', error)
        alert(`Error al exportar anotaciones: ${error.message}`)
        this.exporting = false
        this.progress = 0
      }
    },
    async fetchExportStats() {
      try {
        // Crear parámetros para las estadísticas (mismo filtro que la exportación)
        const params = new URLSearchParams({
          only_annotated: this.onlyAnnotated
        })

        const response = await fetch(
          `/api/annotations/export-stats/${this.datasetId}?${params}`,
          {
            method: 'GET'
          }
        )

        if (!response.ok) {
          console.error('Error al obtener estadísticas de exportación')
          // Usar valores por defecto si falla
          this.exportResult = {
            images: 0,
            annotations: 0,
            categories: 0
          }
          return
        }

        const stats = await response.json()
        this.exportResult = {
          images: stats.images || 0,
          annotations: stats.annotations || 0,
          categories: stats.categories || 0
        }

      } catch (error) {
        console.error('Error al obtener estadísticas:', error)
        // Usar valores por defecto si falla
        this.exportResult = {
          images: 0,
          annotations: 0,
          categories: 0
        }
      }
    }
  }
}
</script>

<style scoped>
.export-annotations-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 1.25rem;
}

.modal-content {
  background: white;
  border-radius: 0.75rem;
  width: 100%;
  max-width: 43.75rem;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 0.625rem 2.5rem rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 0.0625rem solid #e0e0e0;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #666;
  cursor: pointer;
  padding: 0;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.25rem;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f5f5f5;
  color: #333;
}

.modal-body {
  padding: 1.5rem;
}

.format-selector h3 {
  margin: 0 0 1rem 0;
  font-size: 1.125rem;
  color: #333;
}

.format-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.format-option {
  border: 0.125rem solid #e0e0e0;
  border-radius: 0.5rem;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.format-option:hover {
  border-color: #2196F3;
  background: #f5f9ff;
}

.format-option.active {
  border-color: #2196F3;
  background: #e3f2fd;
}

.format-option input[type="radio"] {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.option-content {
  text-align: center;
}

.option-content i {
  font-size: 2rem;
  color: #2196F3;
  margin-bottom: 0.5rem;
  display: block;
}

.option-content strong {
  display: block;
  font-size: 1rem;
  color: #333;
  margin-bottom: 0.25rem;
}

.option-content small {
  display: block;
  font-size: 0.75rem;
  color: #666;
  line-height: 1.4;
}

.format-info {
  margin-bottom: 1.5rem;
}

.info-box {
  background: #e3f2fd;
  border-left: 0.25rem solid #2196F3;
  padding: 1rem;
  border-radius: 0.25rem;
}

.info-box h4 {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
  color: #1976D2;
}

.info-box h4 i {
  margin-right: 0.5rem;
}

.info-box p {
  margin: 0 0 0.5rem 0;
  color: #333;
  font-size: 0.875rem;
}

.info-box ul {
  margin: 0;
  padding-left: 1.25rem;
  color: #555;
  font-size: 0.875rem;
}

.info-box li {
  margin: 0.25rem 0;
}

.info-box code {
  background: rgba(0, 0, 0, 0.1);
  padding: 0.125rem 0.375rem;
  border-radius: 0.1875rem;
  font-family: 'Courier New', monospace;
  font-size: 0.8125rem;
}

.export-options {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 0.5rem;
}

.export-options h3 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  color: #333;
}

.option-item {
  margin-bottom: 0.75rem;
}

.option-item:last-child {
  margin-bottom: 0;
}

.option-item label {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 0.875rem;
  color: #333;
  font-weight: 500;
}

.option-item input[type="checkbox"] {
  margin-right: 0.5rem;
  cursor: pointer;
  width: 1.125rem;
  height: 1.125rem;
}

.option-item small {
  display: block;
  margin-left: 1.625rem;
  color: #666;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.split-config {
  margin-top: 1rem;
  padding: 1rem;
  background: white;
  border-radius: 0.375rem;
  border: 0.125rem solid #2196F3;
}

.split-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.split-header h4 {
  margin: 0;
  font-size: 0.9375rem;
  color: #333;
}

.total-percentage {
  font-size: 0.875rem;
  font-weight: 600;
  color: #4CAF50;
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.total-percentage.invalid {
  color: #f44336;
}

.total-percentage i {
  font-size: 0.875rem;
}

.split-item {
  margin-bottom: 1rem;
}

.split-item:last-of-type {
  margin-bottom: 0;
}

.split-item label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #333;
}

.split-item label i {
  color: #2196F3;
  width: 1.125rem;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.percentage-slider {
  flex: 1;
  height: 0.375rem;
  border-radius: 0.1875rem;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
  background: #e0e0e0;
}

.percentage-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 1.125rem;
  height: 1.125rem;
  border-radius: 50%;
  background: #2196F3;
  cursor: pointer;
  transition: all 0.2s;
}

.percentage-slider::-webkit-slider-thumb:hover {
  background: #1976D2;
  transform: scale(1.2);
}

.percentage-slider::-moz-range-thumb {
  width: 1.125rem;
  height: 1.125rem;
  border-radius: 50%;
  background: #2196F3;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.percentage-slider::-moz-range-thumb:hover {
  background: #1976D2;
  transform: scale(1.2);
}

.percentage-input {
  width: 3.75rem;
  padding: 0.375rem 0.5rem;
  border: 0.0625rem solid #ddd;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  text-align: center;
  outline: none;
}

.percentage-input:focus {
  border-color: #2196F3;
}

.percentage-label {
  font-size: 0.875rem;
  color: #666;
  font-weight: 500;
}

.split-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 0.75rem;
  background: #fff3cd;
  border: 0.0625rem solid #ffc107;
  border-radius: 0.25rem;
  color: #856404;
  font-size: 0.8125rem;
  margin-top: 0.75rem;
}

.split-warning i {
  font-size: 1rem;
}

.split-info {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.625rem 0.75rem;
  background: #e3f2fd;
  border: 0.0625rem solid #2196F3;
  border-radius: 0.25rem;
  color: #1565C0;
  font-size: 0.75rem;
  margin-top: 0.75rem;
  line-height: 1.4;
}

.split-info i {
  font-size: 0.875rem;
  margin-top: 0.0625rem;
  flex-shrink: 0;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #2196F3;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1976D2;
}

.btn-secondary {
  background: #757575;
  color: white;
}

.btn-secondary:hover {
  background: #616161;
}

.progress-section {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 0.0625rem solid #e0e0e0;
}

.progress-bar {
  width: 100%;
  height: 0.5rem;
  background: #e0e0e0;
  border-radius: 0.25rem;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #2196F3, #21CBF3);
  transition: width 0.3s ease;
  border-radius: 0.25rem;
}

.progress-text {
  text-align: center;
  color: #666;
  font-size: 0.875rem;
  margin: 0;
}

.result-section {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 0.0625rem solid #e0e0e0;
}

.result-success {
  text-align: center;
  padding: 1.25rem;
}

.result-success i {
  font-size: 3rem;
  color: #4CAF50;
  margin-bottom: 0.75rem;
}

.result-success h4 {
  margin: 0 0 1rem 0;
  font-size: 1.125rem;
  color: #333;
}

.result-stats {
  display: flex;
  justify-content: center;
  gap: 2rem;
  margin-bottom: 1rem;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat strong {
  font-size: 1.5rem;
  color: #2196F3;
  display: block;
  margin-bottom: 0.25rem;
}

.stat span {
  font-size: 0.875rem;
  color: #666;
}

.result-message {
  color: #666;
  font-size: 0.875rem;
  margin: 0;
}

/* Scrollbar personalizado */
.modal-content::-webkit-scrollbar {
  width: 0.5rem;
}

.modal-content::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.modal-content::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 0.25rem;
}

.modal-content::-webkit-scrollbar-thumb:hover {
  background: #555;
}

/* Responsive */
@media (max-width: 48em) {
  .format-options {
    grid-template-columns: 1fr;
  }
  
  .modal-content {
    max-width: 95%;
  }
}
</style>
