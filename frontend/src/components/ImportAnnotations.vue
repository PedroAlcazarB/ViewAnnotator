<template>
  <div class="import-annotations-modal" v-if="show" @click.self="closeModal">
    <div class="modal-content">
      <div class="modal-header">
        <h2>Importar Anotaciones</h2>
        <button @click="closeModal" class="close-btn">
          <i class="fas fa-times"></i>
        </button>
      </div>

      <div class="modal-body">
        <!-- Selector de formato -->
        <div class="format-selector">
          <h3>Selecciona el formato de las anotaciones</h3>
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
            <p>Sube un archivo con anotaciones en formato COCO:</p>
            <ul>
              <li><strong>JSON único</strong>: Un solo archivo con images, annotations y categories</li>
              <li><strong>ZIP múltiple</strong>: Formato MS COCO oficial (instances_*.json, captions_*.json, person_keypoints_*.json)</li>
              <li>Se combinan automáticamente todas las anotaciones encontradas</li>
            </ul>
          </div>

          <div v-if="selectedFormat === 'yolo'" class="info-box">
            <h4><i class="fas fa-info-circle"></i> Formato YOLO</h4>
            <p>Sube un archivo ZIP que contenga:</p>
            <ul>
              <li>Archivos .txt con el mismo nombre que las imágenes</li>
              <li>Cada línea: <code>class_id center_x center_y width height</code></li>
              <li>Archivo classes.txt con las clases (una por línea)</li>
              <li>Este formato no soporta polígonos; las anotaciones de polígonos se importarán como rectángulos.</li>
            </ul>
          </div>

          <div v-if="selectedFormat === 'pascal'" class="info-box">
            <h4><i class="fas fa-info-circle"></i> Formato PascalVOC</h4>
            <p>Sube un archivo ZIP que contenga:</p>
            <ul>
              <li>Archivos .xml con el mismo nombre que las imágenes</li>
              <li>Cada XML contiene las anotaciones con coordenadas absolutas</li>
              <li>Este formato no soporta polígonos; las anotaciones de polígonos se importarán como rectángulos.</li>
            </ul>
          </div>
        </div>

        <!-- Upload de archivos -->
        <div v-if="selectedFormat" class="upload-section">
          <h3>Sube tus archivos</h3>
          
          <!-- Para COCO: JSON único o ZIP con múltiples JSONs -->
          <div v-if="selectedFormat === 'coco'" class="upload-box">
            <label class="file-input-label">
              <input 
                type="file" 
                accept=".json,.zip" 
                @change="handleFileSelect($event, 'annotations')"
                class="file-input"
              />
              <div class="upload-content">
                <i class="fas fa-cloud-upload-alt"></i>
                <p v-if="!annotationsFile">Selecciona archivo JSON o ZIP de COCO</p>
                <p v-else class="file-selected">
                  <i class="fas fa-check-circle"></i> {{ annotationsFile.name }}
                </p>
              </div>
            </label>
          </div>

          <!-- Para YOLO y PascalVOC: archivo ZIP -->
          <div v-if="selectedFormat !== 'coco'" class="upload-box">
            <label class="file-input-label">
              <input 
                type="file" 
                accept=".zip" 
                @change="handleFileSelect($event, 'annotations')"
                class="file-input"
              />
              <div class="upload-content">
                <i class="fas fa-cloud-upload-alt"></i>
                <p v-if="!annotationsFile">Selecciona el archivo ZIP con las anotaciones</p>
                <p v-else class="file-selected">
                  <i class="fas fa-check-circle"></i> {{ annotationsFile.name }}
                </p>
              </div>
            </label>
          </div>

          <div class="upload-note">
            <i class="fas fa-info-circle"></i>
            <p>Las anotaciones se asociarán automáticamente con las imágenes existentes en el dataset por nombre de archivo.</p>
          </div>
        </div>

        <!-- Progreso de importación -->
        <div v-if="uploading" class="upload-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
          </div>
          <p>{{ uploadMessage }}</p>
        </div>

        <!-- Resultado de la importación -->
        <div v-if="importResult" class="import-result" :class="importResult.success ? 'success' : 'error'">
          <i :class="importResult.success ? 'fas fa-check-circle' : 'fas fa-exclamation-circle'"></i>
          <div class="result-content">
            <h4>{{ importResult.success ? '¡Importación exitosa!' : 'Error en la importación' }}</h4>
            <p>{{ importResult.message }}</p>
            <div v-if="importResult.success && importResult.stats" class="stats">
              <div class="stat">
                <strong>{{ importResult.stats.images }}</strong>
                <span>imágenes procesadas</span>
              </div>
              <div class="stat">
                <strong>{{ importResult.stats.annotations }}</strong>
                <span>anotaciones importadas</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button @click="closeModal" class="btn btn-secondary" :disabled="uploading">
          Cancelar
        </button>
        <button 
          @click="importAnnotations" 
          class="btn btn-primary"
          :disabled="!canImport || uploading"
        >
          <i class="fas fa-file-import"></i>
          {{ uploading ? 'Importando...' : 'Importar' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  show: Boolean,
  datasetId: [String, Number]
})

const emit = defineEmits(['close', 'import-complete'])

const selectedFormat = ref('coco')
const annotationsFile = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadMessage = ref('')
const importResult = ref(null)

const canImport = computed(() => {
  return selectedFormat.value && annotationsFile.value
})

function handleFileSelect(event, type) {
  const file = event.target.files[0]
  if (file) {
    if (type === 'annotations') {
      annotationsFile.value = file
    }
    importResult.value = null // Limpiar resultado anterior
  }
}

async function importAnnotations() {
  if (!canImport.value) return

  uploading.value = true
  uploadProgress.value = 0
  uploadMessage.value = 'Preparando archivos...'
  importResult.value = null

  try {
    const formData = new FormData()
    formData.append('format', selectedFormat.value)
    formData.append('annotations', annotationsFile.value)
    
    if (props.datasetId) {
      formData.append('dataset_id', props.datasetId)
    }

    uploadMessage.value = 'Subiendo archivos...'
    uploadProgress.value = 30

    const result = await window.apiFetch('/api/annotations/import', {
      method: 'POST',
      body: formData
    })

    uploadProgress.value = 60
    uploadMessage.value = 'Procesando anotaciones...'

    uploadProgress.value = 100
    uploadMessage.value = 'Completado!'

    importResult.value = {
      success: true,
      message: result.message,
      stats: result.stats
    }

    // Emitir evento de completado después de 2 segundos
    setTimeout(() => {
      emit('import-complete', result)
      resetForm()
    }, 2000)

  } catch (error) {
    console.error('Error al importar anotaciones:', error)
    importResult.value = {
      success: false,
      message: error.message
    }
  } finally {
    uploading.value = false
  }
}

function resetForm() {
  selectedFormat.value = 'coco'
  annotationsFile.value = null
  uploadProgress.value = 0
  uploadMessage.value = ''
  importResult.value = null
}

function closeModal() {
  if (!uploading.value) {
    resetForm()
    emit('close')
  }
}
</script>

<style scoped>
.import-annotations-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #1f2937;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #6b7280;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #1f2937;
}

.modal-body {
  padding: 1.5rem;
}

.modal-body h3 {
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
  color: #374151;
}

.format-selector {
  margin-bottom: 2rem;
}

.format-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.format-option {
  cursor: pointer;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 1rem;
  transition: all 0.2s;
  display: block;
}

.format-option:hover {
  border-color: #3b82f6;
  background: #f8fafc;
}

.format-option.active {
  border-color: #3b82f6;
  background: #eff6ff;
}

.format-option input[type="radio"] {
  display: none;
}

.option-content {
  text-align: center;
}

.option-content i {
  font-size: 2rem;
  color: #3b82f6;
  margin-bottom: 0.5rem;
  display: block;
}

.option-content strong {
  display: block;
  margin-bottom: 0.25rem;
  color: #1f2937;
}

.option-content small {
  color: #6b7280;
  font-size: 0.75rem;
}

.format-info {
  margin-bottom: 1.5rem;
}

.info-box {
  background: #eff6ff;
  border-left: 4px solid #3b82f6;
  padding: 1rem;
  border-radius: 4px;
}

.info-box h4 {
  margin: 0 0 0.5rem 0;
  color: #1e40af;
  font-size: 1rem;
}

.info-box h4 i {
  margin-right: 0.5rem;
}

.info-box p {
  margin: 0 0 0.5rem 0;
  color: #1e3a8a;
}

.info-box ul {
  margin: 0;
  padding-left: 1.5rem;
  color: #1e3a8a;
}

.info-box ul li {
  margin-bottom: 0.25rem;
}

.info-box code {
  background: #dbeafe;
  padding: 0.125rem 0.25rem;
  border-radius: 2px;
  font-family: monospace;
  font-size: 0.875rem;
}

.upload-section {
  margin-bottom: 1.5rem;
}

.upload-box {
  margin-bottom: 1rem;
}

.upload-note {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 6px;
  padding: 1rem;
  margin-top: 1rem;
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.upload-note i {
  color: #0284c7;
  font-size: 1.1rem;
  margin-top: 0.1rem;
  flex-shrink: 0;
}

.upload-note p {
  margin: 0;
  color: #0c4a6e;
  font-size: 0.9rem;
  line-height: 1.4;
}

.file-input-label {
  display: block;
  cursor: pointer;
}

.file-input {
  display: none;
}

.upload-content {
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  transition: all 0.2s;
}

.file-input-label:hover .upload-content {
  border-color: #3b82f6;
  background: #f8fafc;
}

.upload-content i {
  font-size: 3rem;
  color: #9ca3af;
  margin-bottom: 1rem;
  display: block;
}

.upload-content p {
  margin: 0;
  color: #6b7280;
}

.upload-content small {
  display: block;
  margin-top: 0.5rem;
  color: #9ca3af;
  font-size: 0.875rem;
}

.file-selected {
  color: #10b981 !important;
  font-weight: 600;
}

.file-selected i {
  color: #10b981;
  font-size: 1.5rem !important;
  display: inline !important;
  margin-right: 0.5rem;
}

.upload-progress {
  margin: 1.5rem 0;
}

.progress-bar {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  transition: width 0.3s ease;
}

.upload-progress p {
  text-align: center;
  color: #6b7280;
  margin: 0;
}

.import-result {
  padding: 1rem;
  border-radius: 8px;
  margin-top: 1rem;
  display: flex;
  gap: 1rem;
  align-items: start;
}

.import-result.success {
  background: #ecfdf5;
  border: 1px solid #10b981;
}

.import-result.error {
  background: #fef2f2;
  border: 1px solid #ef4444;
}

.import-result i {
  font-size: 2rem;
}

.import-result.success i {
  color: #10b981;
}

.import-result.error i {
  color: #ef4444;
}

.result-content {
  flex: 1;
}

.result-content h4 {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
}

.import-result.success h4 {
  color: #047857;
}

.import-result.error h4 {
  color: #dc2626;
}

.result-content p {
  margin: 0 0 1rem 0;
  color: #6b7280;
}

.stats {
  display: flex;
  gap: 2rem;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat strong {
  font-size: 1.5rem;
  color: #047857;
  display: block;
}

.stat span {
  font-size: 0.875rem;
  color: #6b7280;
}

.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover:not(:disabled) {
  background: #e5e7eb;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}
</style>
