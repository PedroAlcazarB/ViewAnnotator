<template>
  <div class="annotation-toolbar">
    <h3 class="toolbar-title">Herramientas de Anotación</h3>
    
    <div class="tools-grid">
      <!-- Edit Tool -->
      <button
        :class="['tool-btn', { active: activeTool === 'edit' }]"
        @click="setActiveTool('edit')"
        title="Editar Anotaciones"
      >
        <i class="fas fa-edit"></i>
        <span>Editar</span>
      </button>

      <!-- BBox Tool -->
      <button
        :class="['tool-btn', { active: activeTool === 'bbox' }]"
        @click="setActiveTool('bbox')"
        title="Rectángulo delimitador"
      >
        <i class="fas fa-vector-square"></i>
        <span>Rectángulo</span>
      </button>

      <!-- Polygon Tool -->
      <button
        :class="['tool-btn', { active: activeTool === 'polygon' }]"
        @click="setActiveTool('polygon')"
        title="Herramienta de Polígono"
      >
        <i class="fas fa-draw-polygon"></i>
        <span>Polígono</span>
      </button>

      <!-- Brush Tool -->
      <button
        :class="['tool-btn', { active: activeTool === 'brush' }]"
        @click="setActiveTool('brush')"
        title="Pincel de mano alzada"
      >
        <i class="fas fa-paint-brush"></i>
        <span>Pincel</span>
      </button>

      <!-- Eraser Tool -->
      <button
        :class="['tool-btn', { active: activeTool === 'eraser' }]"
        @click="setActiveTool('eraser')"
        title="Borrador"
      >
        <i class="fas fa-eraser"></i>
        <span>Borrador</span>
      </button>

      <!-- Keypoints Tool -->
      <button
        :class="['tool-btn', { active: activeTool === 'keypoints' }]"
        @click="setActiveTool('keypoints')"
        title="Puntos Clave"
      >
        <i class="fas fa-map-marker-alt"></i>
        <span>Puntos</span>
      </button>
    </div>

    <!-- Tool Settings Panel -->
    <div v-if="activeTool && activeTool !== 'edit'" class="tool-settings">
      <h4>Configuración: {{ getToolDisplayName(activeTool) }}</h4>
      
      <!-- Instrucciones específicas -->
      <div class="tool-instructions">
        <div v-if="activeTool === 'polygon'" class="instruction">
          <small>💡 Haz clic para agregar puntos. Doble clic o Enter para completar. Escape para cancelar.</small>
        </div>
        <div v-if="activeTool === 'brush'" class="instruction">
          <small>💡 Mantén presionado y arrastra para dibujar.</small>
        </div>
        <div v-if="activeTool === 'eraser'" class="instruction">
          <small>💡 Mantén presionado y arrastra para borrar anotaciones.</small>
        </div>
        <div v-if="activeTool === 'keypoints'" class="instruction">
          <small>💡 Haz clic para colocar puntos clave.</small>
        </div>
        <div v-if="activeTool === 'bbox'" class="instruction">
          <small>💡 Arrastra para crear un rectángulo delimitador.</small>
        </div>
      </div>

    <!-- Edit Tool Settings -->
    <div v-if="activeTool === 'edit'" class="tool-settings">
      <h4>Modo de Edición</h4>
      
      <div class="tool-instructions">
        <div class="instruction">
          <small>💡 Haz clic en una anotación para seleccionarla y editarla. Arrastra para mover, usa los controles para redimensionar.</small>
        </div>
      </div>
      
      <div class="settings-group">
        <div class="setting-item">
          <label>Sensibilidad de selección:</label>
          <input 
            type="range" 
            min="1" 
            max="10" 
            v-model="toolSettings.edit.tolerance"
            class="range-input"
          />
          <span>{{ toolSettings.edit.tolerance }}px</span>
        </div>
        <label>
          <input 
            type="checkbox" 
            v-model="toolSettings.edit.showHandles"
          />
          Mostrar controles de redimensionado
        </label>
        <label>
          <input 
            type="checkbox" 
            v-model="toolSettings.edit.snapToGrid"
          />
          Ajustar a grilla
        </label>
      </div>
    </div>
      
      <!-- BBox Settings -->
      <div v-if="activeTool === 'bbox'" class="settings-group">
        <label>
          <input 
            type="checkbox" 
            v-model="toolSettings.bbox.autoColor"
          />
          Color automático
        </label>
        <div class="setting-item">
          <label>Color del trazo:</label>
          <input 
            type="color" 
            v-model="toolSettings.bbox.strokeColor"
            class="color-input"
          />
        </div>
      </div>

      <!-- Polygon Settings -->
      <div v-if="activeTool === 'polygon'" class="settings-group">
        <div class="setting-item">
          <label>Distancia mínima:</label>
          <input 
            type="range" 
            min="1" 
            max="20" 
            v-model="toolSettings.polygon.minDistance"
            class="range-input"
          />
          <span>{{ toolSettings.polygon.minDistance }}px</span>
        </div>
        <div class="setting-item">
          <label>Distancia de completado:</label>
          <input 
            type="range" 
            min="5" 
            max="50" 
            v-model="toolSettings.polygon.completeDistance"
            class="range-input"
          />
          <span>{{ toolSettings.polygon.completeDistance }}px</span>
        </div>
        <label>
          <input 
            type="checkbox" 
            v-model="toolSettings.polygon.guidance"
          />
          Mostrar guía
        </label>
      </div>

      <!-- Brush Settings -->
      <div v-if="activeTool === 'brush'" class="settings-group">
        <div class="setting-item">
          <label>Grosor del trazo:</label>
          <input 
            type="range" 
            min="2" 
            max="50" 
            v-model="toolSettings.brush.radius"
            class="range-input"
          />
          <span>{{ toolSettings.brush.radius }}px</span>
        </div>
        <div class="setting-item">
          <label>Color:</label>
          <input 
            type="color" 
            v-model="toolSettings.brush.color"
            class="color-input"
          />
        </div>
      </div>

      <!-- Eraser Settings -->
      <div v-if="activeTool === 'eraser'" class="settings-group">
        <div class="setting-item">
          <label>Tamaño del borrador:</label>
          <input 
            type="range" 
            min="1" 
            max="100" 
            v-model="toolSettings.eraser.radius"
            class="range-input"
          />
          <span>{{ toolSettings.eraser.radius }}px</span>
        </div>
      </div>

      <!-- Keypoints Settings -->
      <div v-if="activeTool === 'keypoints'" class="settings-group">
        <div class="setting-item">
          <label>Tamaño del punto:</label>
          <input 
            type="range" 
            min="2" 
            max="20" 
            v-model="toolSettings.keypoints.size"
            class="range-input"
          />
          <span>{{ toolSettings.keypoints.size }}px</span>
        </div>
        <div class="setting-item">
          <label>Color:</label>
          <input 
            type="color" 
            v-model="toolSettings.keypoints.color"
            class="color-input"
          />
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="quick-actions">
      <button 
        @click="clearCurrentAnnotation"
        class="action-btn danger"
        :disabled="!hasCurrentAnnotation"
        title="Limpiar anotación actual"
      >
        <i class="fas fa-trash"></i>
        Limpiar
      </button>
      
      <button 
        @click="undoLastAction"
        class="action-btn"
        :disabled="!canUndo"
        title="Deshacer última acción"
      >
        <i class="fas fa-undo"></i>
        Deshacer
      </button>
      
      <button 
        @click="completeAnnotation"
        class="action-btn success"
        :disabled="!hasCurrentAnnotation"
        title="Completar anotación"
      >
        <i class="fas fa-check"></i>
        Completar
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useAnnotationStore } from '../stores/annotationStore'

const annotationStore = useAnnotationStore()

// Estado reactivo usando el store
const activeTool = computed({
  get: () => annotationStore.activeTool,
  set: (value) => annotationStore.setActiveTool(value)
})

const toolSettings = computed(() => annotationStore.toolSettings)

// Computadas
const hasCurrentAnnotation = computed(() => {
  if (!annotationStore.currentImage) return false
  return annotationStore.getCurrentImageAnnotations(annotationStore.currentImage.id).length > 0
})

const canUndo = computed(() => {
  // Aquí puedes implementar lógica de undo cuando la tengas
  return false
})

// Métodos
const setActiveTool = (tool) => {
  annotationStore.setActiveTool(tool)
  // Emitir evento para el canvas
  emit('tool-changed', {
    tool,
    settings: toolSettings.value[tool] || {}
  })
}

// Watch para cambios en configuraciones
watch(() => toolSettings.value, (newSettings) => {
  if (activeTool.value && newSettings[activeTool.value]) {
    emit('tool-changed', {
      tool: activeTool.value,
      settings: newSettings[activeTool.value]
    })
  }
}, { deep: true })

// Función para actualizar configuraciones
const updateToolSetting = (tool, key, value) => {
  annotationStore.updateToolSettings(tool, { [key]: value })
}

const getToolDisplayName = (tool) => {
  const names = {
    edit: 'Editar',
    bbox: 'Rectángulo',
    polygon: 'Polígono', 
    brush: 'Pincel',
    eraser: 'Borrador',
    keypoints: 'Puntos Clave'
  }
  return names[tool] || tool
}

const clearCurrentAnnotation = () => {
  if (annotationStore.currentImage) {
    // Limpiar las anotaciones de la imagen actual
    annotationStore.clearAnnotationsForImage(annotationStore.currentImage.id)
    emit('annotation-cleared')
  }
}

const undoLastAction = () => {
  // Implementar lógica de undo
  emit('undo-action')
}

const completeAnnotation = () => {
  // Emitir evento para completar la anotación actual
  emit('annotation-completed')
}

// Eventos
const emit = defineEmits([
  'tool-changed', 
  'annotation-cleared', 
  'undo-action', 
  'annotation-completed'
])

// Inicializar herramienta por defecto
onMounted(() => {
  setActiveTool('edit')
})
</script>

<style scoped>
.annotation-toolbar {
  background: #fff;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  border: 1px solid #e5e7eb;
}

.toolbar-title {
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #374151;
  text-align: center;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.tool-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.75rem 0.5rem;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #6b7280;
  font-size: 0.8rem;
  min-height: 70px;
}

.tool-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
  background: #f8fafc;
}

.tool-btn.active {
  border-color: #3b82f6;
  background: #3b82f6;
  color: white;
}

.tool-btn i {
  font-size: 1.2rem;
  margin-bottom: 0.25rem;
}

.tool-btn span {
  font-weight: 500;
  text-align: center;
}

.tool-settings {
  background: #f8fafc;
  border-radius: 6px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.tool-settings h4 {
  margin: 0 0 1rem 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: #374151;
}

.tool-instructions {
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: #e0f2fe;
  border-radius: 4px;
  border-left: 3px solid #0288d1;
}

.instruction small {
  color: #01579b;
  font-size: 0.75rem;
  line-height: 1.4;
}

.settings-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.setting-item label {
  font-size: 0.8rem;
  font-weight: 500;
  color: #6b7280;
}

.range-input {
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: #e5e7eb;
  outline: none;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.range-input:hover {
  opacity: 1;
}

.range-input::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
}

.color-input {
  width: 100%;
  height: 32px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  cursor: pointer;
}

.settings-group label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: #6b7280;
  cursor: pointer;
}

.settings-group input[type="checkbox"] {
  width: 16px;
  height: 16px;
}

.quick-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: space-between;
}

.action-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #6b7280;
  font-size: 0.7rem;
  min-height: 50px;
}

.action-btn:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #d1d5db;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn.danger {
  color: #ef4444;
  border-color: #fecaca;
}

.action-btn.danger:hover:not(:disabled) {
  background: #fef2f2;
  border-color: #ef4444;
}

.action-btn.success {
  color: #10b981;
  border-color: #a7f3d0;
}

.action-btn.success:hover:not(:disabled) {
  background: #ecfdf5;
  border-color: #10b981;
}

.action-btn i {
  font-size: 1rem;
  margin-bottom: 0.25rem;
}
</style>