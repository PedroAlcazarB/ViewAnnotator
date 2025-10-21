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
            </ul>
          </div>

          <div v-if="selectedFormat === 'pascal'" class="info-box">
            <h4><i class="fas fa-info-circle"></i> Formato PascalVOC</h4>
            <p>Se descargará un archivo ZIP que contiene:</p>
            <ul>
              <li>Archivos .xml con el mismo nombre que las imágenes</li>
              <li>Cada XML contiene las anotaciones con coordenadas absolutas</li>
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
      exporting: false,
      progress: 0,
      progressMessage: '',
      exportResult: null
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
      this.exporting = false
      this.progress = 0
      this.progressMessage = ''
      this.exportResult = null
    },
    async exportAnnotations() {
      this.exporting = true
      this.progress = 0
      this.exportResult = null
      this.progressMessage = 'Preparando exportación...'

      try {
        // Crear FormData para enviar los parámetros
        const params = new URLSearchParams({
          format: this.selectedFormat,
          include_images: this.includeImages,
          only_annotated: this.onlyAnnotated
        })

        this.progressMessage = 'Generando archivo de exportación...'
        this.progress = 30

        // Realizar la petición al backend
        const response = await fetch(
          `http://localhost:5000/api/annotations/export/${this.datasetId}?${params}`,
          {
            method: 'GET'
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
        let filename = `${this.datasetId}_annotations`
        let extension = ''
        
        switch (this.selectedFormat) {
          case 'coco':
            extension = '.json'
            break
          case 'yolo':
          case 'pascal':
            extension = '.zip'
            break
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
          `http://localhost:5000/api/annotations/export-stats/${this.datasetId}?${params}`,
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
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 100%;
  max-width: 700px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h2 {
  margin: 0;
  font-size: 24px;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #666;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f5f5f5;
  color: #333;
}

.modal-body {
  padding: 24px;
}

.format-selector h3 {
  margin: 0 0 16px 0;
  font-size: 18px;
  color: #333;
}

.format-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}

.format-option {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
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
  font-size: 32px;
  color: #2196F3;
  margin-bottom: 8px;
  display: block;
}

.option-content strong {
  display: block;
  font-size: 16px;
  color: #333;
  margin-bottom: 4px;
}

.option-content small {
  display: block;
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}

.format-info {
  margin-bottom: 24px;
}

.info-box {
  background: #e3f2fd;
  border-left: 4px solid #2196F3;
  padding: 16px;
  border-radius: 4px;
}

.info-box h4 {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #1976D2;
}

.info-box h4 i {
  margin-right: 8px;
}

.info-box p {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 14px;
}

.info-box ul {
  margin: 0;
  padding-left: 20px;
  color: #555;
  font-size: 14px;
}

.info-box li {
  margin: 4px 0;
}

.info-box code {
  background: rgba(0, 0, 0, 0.1);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.export-options {
  margin-bottom: 24px;
  padding: 16px;
  background: #f5f5f5;
  border-radius: 8px;
}

.export-options h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #333;
}

.option-item {
  margin-bottom: 12px;
}

.option-item:last-child {
  margin-bottom: 0;
}

.option-item label {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.option-item input[type="checkbox"] {
  margin-right: 8px;
  cursor: pointer;
  width: 18px;
  height: 18px;
}

.option-item small {
  display: block;
  margin-left: 26px;
  color: #666;
  font-size: 12px;
  margin-top: 4px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
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
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #e0e0e0;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #2196F3, #21CBF3);
  transition: width 0.3s ease;
  border-radius: 4px;
}

.progress-text {
  text-align: center;
  color: #666;
  font-size: 14px;
  margin: 0;
}

.result-section {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #e0e0e0;
}

.result-success {
  text-align: center;
  padding: 20px;
}

.result-success i {
  font-size: 48px;
  color: #4CAF50;
  margin-bottom: 12px;
}

.result-success h4 {
  margin: 0 0 16px 0;
  font-size: 18px;
  color: #333;
}

.result-stats {
  display: flex;
  justify-content: center;
  gap: 32px;
  margin-bottom: 16px;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat strong {
  font-size: 24px;
  color: #2196F3;
  display: block;
  margin-bottom: 4px;
}

.stat span {
  font-size: 14px;
  color: #666;
}

.result-message {
  color: #666;
  font-size: 14px;
  margin: 0;
}

/* Scrollbar personalizado */
.modal-content::-webkit-scrollbar {
  width: 8px;
}

.modal-content::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.modal-content::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.modal-content::-webkit-scrollbar-thumb:hover {
  background: #555;
}

/* Responsive */
@media (max-width: 768px) {
  .format-options {
    grid-template-columns: 1fr;
  }
  
  .modal-content {
    max-width: 95%;
  }
}
</style>
