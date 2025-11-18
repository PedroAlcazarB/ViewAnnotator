<template>
  <div class="annotation-toolbar">
    <h3 class="toolbar-title">Herramientas de Anotación</h3>
    
    <div class="tools-grid">

      <!-- Pan Tool -->
      <button
        :class="['tool-btn', { active: activeTool === 'pan' }]"
        @click="setActiveTool('pan')"
        title="💡 Arrastra para moverte por la imagen. Usa la rueda del ratón para zoom. Tecla 'R' para resetear."
      >
        <i class="fas fa-hand-paper"></i>
        <span>Mover</span>
      </button>
      
            <!-- Edit Tool -->
      <button
        :class="['tool-btn', { active: activeTool === 'edit' }]"
        @click="setActiveTool('edit')"
        title="💡 Haz clic en una anotación para seleccionarla y editarla. Arrastra para mover, usa los controles para redimensionar.++"
      >
        <i class="fas fa-edit"></i>
        <span>Editar</span>
      </button>

      <!-- BBox Tool -->
      <button
        :class="['tool-btn', { active: activeTool === 'bbox' }]"
        @click="setActiveTool('bbox')"
        title="💡 Arrastra para crear un rectángulo delimitador."
      >
        <i class="fas fa-vector-square"></i>
        <span>Rectángulo</span>
      </button>

      <!-- Polygon Tool -->
      <button
        :class="['tool-btn', { active: activeTool === 'polygon' }]"
        @click="setActiveTool('polygon')"
        title="💡 Haz clic para agregar puntos. Doble clic o Enter para completar. Escape para cancelar."
      >
        <i class="fas fa-draw-polygon"></i>
        <span>Polígono</span>
      </button>

      <!-- Eraser Tool -->
      <button
        :class="['tool-btn', { active: activeTool === 'eraser' }]"
        @click="setActiveTool('eraser')"
        title="💡 Mantén presionado y arrastra para borrar anotaciones."
      >
        <i class="fas fa-eraser"></i>
        <span>Borrador</span>
      </button>
    </div>

    <!-- Quick Actions -->
    <div class="quick-actions">
      <button 
        @click="clearCurrentAnnotation"
        class="action-btn danger"
        :disabled="!hasImageAnnotations"
        title="Limpiar todas las anotaciones de la imagen"
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
    </div>
  </div>
</template>

<script setup>
import { computed, watch, onMounted } from 'vue'
import { useAnnotationStore } from '../stores/annotationStore'

const annotationStore = useAnnotationStore()

// Estado reactivo usando el store
const activeTool = computed({
  get: () => annotationStore.activeTool,
  set: (value) => annotationStore.setActiveTool(value)
})

const toolSettings = computed(() => annotationStore.toolSettings)

const currentImageId = computed(() => {
  const image = annotationStore.currentImage
  if (!image) return null
  return image.id || image._id || null
})

// Computadas
const hasImageAnnotations = computed(() => {
  const imageId = currentImageId.value
  if (!imageId) return false
  return annotationStore.getCurrentImageAnnotations(imageId).length > 0
})

const canUndo = computed(() => {
  const imageId = currentImageId.value
  if (!imageId) return false
  return annotationStore.hasUndoForImage(imageId)
})

// Métodos
const setActiveTool = (tool) => {
  // Herramientas que requieren categorías para funcionar
  const annotationTools = ['bbox', 'polygon', 'brush', 'keypoints']
  
  if (annotationTools.includes(tool)) {
    // Verificar que existan categorías antes de permitir herramientas de anotación
    if (!annotationStore.categories || annotationStore.categories.length === 0) {
      alert('No se pueden usar herramientas de anotación sin categorías. Primero debe crear al menos una categoría para este dataset.')
      return
    }
    
    // Verificar que haya una categoría seleccionada
    if (!annotationStore.selectedCategory) {
      alert('Debe seleccionar una categoría antes de crear anotaciones.')
      return
    }
  }
  
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
    pan: 'Mover Vista',
    bbox: 'Rectángulo',
    polygon: 'Polígono', 
    eraser: 'Borrador'
  }
  return names[tool] || tool
}

const clearCurrentAnnotation = async () => {
  const imageId = currentImageId.value
  if (!imageId || !hasImageAnnotations.value) return
  try {
    const result = await annotationStore.clearAnnotationsForImage(imageId)
    if (result) {
      emit('annotation-cleared', { imageId })
    }
  } catch (error) {
    console.error('Error al limpiar anotaciones:', error)
  }
}

const undoLastAction = async () => {
  const imageId = currentImageId.value
  if (!imageId) return
  try {
    const undone = await annotationStore.undoLastAction(imageId)
    if (undone) {
      emit('undo-action', { imageId })
    }
  } catch (error) {
    console.error('Error al deshacer anotación:', error)
  }
}

// Eventos
const emit = defineEmits([
  'tool-changed', 
  'annotation-cleared', 
  'undo-action'
])

// Inicializar herramienta por defecto
onMounted(() => {
  setActiveTool('pan')
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