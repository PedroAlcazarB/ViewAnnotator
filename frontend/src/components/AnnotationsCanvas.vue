<template>
  <div class="canvas-container">
    <!-- Debug info -->
    <div v-if="!image" class="image-loading-info">
      <div class="loading-icon">
        <i class="fas fa-spinner fa-spin"></i>
      </div>
      <div class="loading-text">
        <strong>Cargando imagen</strong>
      </div>
    </div>
    
    <v-stage
      :config="stageConfig"
      v-if="image"
      @mousedown="startDraw"
      @mousemove="draw"
      @mouseup="endDraw"
      @dblclick="handleDoubleClick"
      @wheel="handleWheel"
      class="annotation-stage"
      :style="{ cursor: canvasCursor }"
      ref="stageRef"
    >
      <v-layer>
        <!-- Imagen de fondo (no bloquea eventos) -->
        <v-image :config="{ ...imageConfig, listening: false }" />

        <!-- Predicciones de IA -->
        <template v-for="(prediction, i) in predictions" :key="`prediction-${i}`">
          <v-group>
            <!-- Rectángulo de predicción -->
            <v-rect
              :config="{
                x: toCanvasX(prediction.bbox[0]),
                y: toCanvasY(prediction.bbox[1]),
                width: prediction.bbox[2],
                height: prediction.bbox[3],
                fill: 'transparent',
                stroke: '#ff6b6b',
                strokeWidth: 2,
                dash: [8, 4],
                listening: true
              }"
              @click="handlePredictionClick(prediction, i)"
              @mouseenter="() => handlePredictionMouseEnter(i)"
              @mouseleave="handlePredictionMouseLeave"
            />
            
            <!-- Etiqueta de predicción -->
            <v-group>
              <v-rect
                :config="{
                  x: toCanvasX(prediction.bbox[0]),
                  y: toCanvasY(prediction.bbox[1]) - 25,
                  width: getPredictionLabelWidth(prediction),
                  height: 22,
                  fill: '#ff6b6b',
                  cornerRadius: 3,
                  listening: false
                }"
              />
              <v-text
                :config="{
                  x: toCanvasX(prediction.bbox[0]) + 5,
                  y: toCanvasY(prediction.bbox[1]) - 20,
                  text: getPredictionLabel(prediction),
                  fontSize: 12,
                  fontFamily: 'Arial',
                  fill: 'white',
                  listening: false
                }"
              />
            </v-group>

            <!-- Botones de acción para predicciones -->
            <v-group v-if="hoveredPrediction === i || selectedPrediction === i">
              <!-- Botón Aceptar (convertir a anotación) -->
              <v-group
                @click="acceptPrediction(prediction, i)"
                @mouseenter="() => predictionButtonHover = 'accept'"
                @mouseleave="() => predictionButtonHover = null"
              >
                <v-circle
                  :config="{
                    x: toCanvasX(prediction.bbox[0]) + prediction.bbox[2] - 15,
                    y: toCanvasY(prediction.bbox[1]) + 15,
                    radius: 12,
                    fill: predictionButtonHover === 'accept' ? '#27ae60' : '#2ecc71',
                    stroke: 'white',
                    strokeWidth: 2,
                    listening: true
                  }"
                />
                <v-text
                  :config="{
                    x: toCanvasX(prediction.bbox[0]) + prediction.bbox[2] - 19,
                    y: toCanvasY(prediction.bbox[1]) + 11,
                    text: '✓',
                    fontSize: 14,
                    fontFamily: 'Arial',
                    fill: 'white',
                    listening: false
                  }"
                />
              </v-group>

              <!-- Botón Rechazar -->
              <v-group
                @click="rejectPrediction(i)"
                @mouseenter="() => predictionButtonHover = 'reject'"
                @mouseleave="() => predictionButtonHover = null"
              >
                <v-circle
                  :config="{
                    x: toCanvasX(prediction.bbox[0]) + prediction.bbox[2] - 15,
                    y: toCanvasY(prediction.bbox[1]) + 40,
                    radius: 12,
                    fill: predictionButtonHover === 'reject' ? '#c0392b' : '#e74c3c',
                    stroke: 'white',
                    strokeWidth: 2,
                    listening: true
                  }"
                />
                <v-text
                  :config="{
                    x: toCanvasX(prediction.bbox[0]) + prediction.bbox[2] - 19,
                    y: toCanvasY(prediction.bbox[1]) + 36,
                    text: '✕',
                    fontSize: 14,
                    fontFamily: 'Arial',
                    fill: 'white',
                    listening: false
                  }"
                />
              </v-group>
            </v-group>
          </v-group>
        </template>

        <!-- Anotaciones existentes -->
        <template v-for="(ann, i) in annotations" :key="i">
          <!-- Rectángulos -->
          <v-rect
            v-if="ann.type === 'bbox' || !ann.type"
            :config="{
              x: toCanvasX(ann.bbox[0]),
              y: toCanvasY(ann.bbox[1]),
              width: ann.bbox[2],
              height: ann.bbox[3],
              fill: getCategoryColor(ann.category || ann.category_id) + '40',
              stroke: getCategoryColor(ann.category || ann.category_id),
              strokeWidth: isSelectedAnnotation(ann) ? 3 : 2,
              listening: true,
              draggable: props.activeTool === 'edit'
            }"
            @click="handleAnnotationClick(ann)"
            @dragmove="handleAnnotationDrag(ann, $event)"
            @dragend="handleAnnotationDragEnd(ann, $event)"
          />
          
          <!-- Controles de redimensionado para rectángulos seleccionados -->
          <template v-if="isSelectedAnnotation(ann) && (ann.type === 'bbox' || !ann.type) && props.activeTool === 'edit'">
            <!-- Esquinas -->
            <v-circle
              :config="{
                x: toCanvasX(ann.bbox[0]),
                y: toCanvasY(ann.bbox[1]),
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true
              }"
              @dragmove="handleResizeDrag(ann, $event, 'nw')"
              @dragend="handleResizeDragEnd(ann)"
            />
            <v-circle
              :config="{
                x: toCanvasX(ann.bbox[0]) + ann.bbox[2],
                y: toCanvasY(ann.bbox[1]),
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true
              }"
              @dragmove="handleResizeDrag(ann, $event, 'ne')"
              @dragend="handleResizeDragEnd(ann)"
            />
            <v-circle
              :config="{
                x: toCanvasX(ann.bbox[0]),
                y: toCanvasY(ann.bbox[1]) + ann.bbox[3],
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true
              }"
              @dragmove="handleResizeDrag(ann, $event, 'sw')"
              @dragend="handleResizeDragEnd(ann)"
            />
            <v-circle
              :config="{
                x: toCanvasX(ann.bbox[0]) + ann.bbox[2],
                y: toCanvasY(ann.bbox[1]) + ann.bbox[3],
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true
              }"
              @dragmove="handleResizeDrag(ann, $event, 'se')"
              @dragend="handleResizeDragEnd(ann)"
            />
            <!-- Bordes - CON RESTRICCIONES DE MOVIMIENTO -->
            <v-circle
              :config="{
                x: toCanvasX(ann.bbox[0]) + ann.bbox[2] / 2,
                y: toCanvasY(ann.bbox[1]),
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true,
                dragBoundFunc: (pos) => ({
                  x: toCanvasX(ann.bbox[0]) + ann.bbox[2] / 2,
                  y: pos.y
                })
              }"
              @dragmove="handleResizeDrag(ann, $event, 'n')"
              @dragend="handleResizeDragEnd(ann)"
            />
            <v-circle
              :config="{
                x: toCanvasX(ann.bbox[0]) + ann.bbox[2] / 2,
                y: toCanvasY(ann.bbox[1]) + ann.bbox[3],
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true,
                dragBoundFunc: (pos) => ({
                  x: toCanvasX(ann.bbox[0]) + ann.bbox[2] / 2,
                  y: pos.y
                })
              }"
              @dragmove="handleResizeDrag(ann, $event, 's')"
              @dragend="handleResizeDragEnd(ann)"
            />
            <v-circle
              :config="{
                x: toCanvasX(ann.bbox[0]),
                y: toCanvasY(ann.bbox[1]) + ann.bbox[3] / 2,
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true,
                dragBoundFunc: (pos) => ({
                  x: pos.x,
                  y: toCanvasY(ann.bbox[1]) + ann.bbox[3] / 2
                })
              }"
              @dragmove="handleResizeDrag(ann, $event, 'w')"
              @dragend="handleResizeDragEnd(ann)"
            />
            <v-circle
              :config="{
                x: toCanvasX(ann.bbox[0]) + ann.bbox[2],
                y: toCanvasY(ann.bbox[1]) + ann.bbox[3] / 2,
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true,
                dragBoundFunc: (pos) => ({
                  x: pos.x,
                  y: toCanvasY(ann.bbox[1]) + ann.bbox[3] / 2
                })
              }"
              @dragmove="handleResizeDrag(ann, $event, 'e')"
              @dragend="handleResizeDragEnd(ann)"
            />
          </template>
          
          <!-- Polígonos agrupados con sus puntos de control -->
          <v-group
            v-if="ann.type === 'polygon' && ann.points && Array.isArray(ann.points) && ann.points.length >= 3"
            :config="{
              x: 0,
              y: 0,
              draggable: props.activeTool === 'edit',
              listening: true
            }"
            @click="handleAnnotationClick(ann)"
            @dragmove="handleAnnotationDrag(ann, $event)"
            @dragend="handleAnnotationDragEnd(ann, $event)"
          >
            <v-line
              :config="{
                points: ann.points.flatMap(point => [
                  toCanvasX(point[0]),
                  toCanvasY(point[1])
                ]),
                fill: getCategoryColor(ann.category || ann.category_id) + '40',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: isSelectedAnnotation(ann) ? 3 : 2,
                closed: true,
                listening: true
              }"
            />
            
            <!-- Puntos de control para polígonos seleccionados -->
            <template v-if="isSelectedAnnotation(ann) && props.activeTool === 'edit'">
              <v-circle
                v-for="(point, pointIndex) in ann.points"
                :key="`control-${pointIndex}`"
                :config="{
                  x: toCanvasX(point[0]),
                  y: toCanvasY(point[1]),
                  radius: 6,
                  fill: '#ffffff',
                  stroke: getCategoryColor(ann.category || ann.category_id),
                  strokeWidth: 2,
                  draggable: true
                }"
                @dragmove="handlePolygonPointDrag(ann, pointIndex, $event)"
                @dragend="handlePolygonPointDragEnd(ann)"
              />
            </template>
          </v-group>
        </template>

        <!-- Forma en curso (preview) -->
        <v-rect v-if="drawing && (props.activeTool === 'bbox')" :config="drawingRect" />
        
        <!-- Polígono en construcción -->
        <v-line 
          v-if="currentPath.length > 1 && props.activeTool === 'polygon'"
          :config="{
            points: currentPath.flat(),
            fill: (getCategoryColor(store.selectedCategory) || '#3498db') + '40',
            stroke: getCategoryColor(store.selectedCategory) || '#3498db',
            strokeWidth: 2,
            dash: [5, 5],
            closed: currentPath.length > 2,
            listening: false
          }"
        />
        
        <!-- Puntos del polígono -->
        <v-circle
          v-for="(point, index) in currentPath"
          :key="`polygon-point-${index}`"
          :config="{
            x: point[0],
            y: point[1],
            radius: 5,
            fill: '#ffffff',
            stroke: getCategoryColor(store.selectedCategory) || '#3498db',
            strokeWidth: 2,
            listening: false
          }"
        />
        
        <!-- Círculo del borrador -->
        <v-circle
          v-if="props.activeTool === 'eraser' && drawing"
          :config="{
            x: startPt.x,
            y: startPt.y,
            radius: eraserRadius.value,
            stroke: 'red',
            strokeWidth: 2,
            dash: [3, 3],
            listening: false
          }"
        />
      </v-layer>
    </v-stage>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted, onUnmounted } from 'vue'
import { useAnnotationStore } from '../stores/annotationStore'

const store = useAnnotationStore()

// Referencias para el stage
const stageRef = ref(null)

// Variables de zoom y pan
const scale = ref(1)
const stagePos = reactive({ x: 0, y: 0 })
const isDragging = ref(false)
const lastPointerPos = ref({ x: 0, y: 0 })

// Canvas responsive que se adapta a la imagen
const stageWidth = ref(800)
const stageHeight = ref(600)
const stageConfig = computed(() => ({ 
  width: stageWidth.value, 
  height: stageHeight.value,
  scaleX: scale.value,
  scaleY: scale.value,
  x: stagePos.x,
  y: stagePos.y,
  draggable: false // Controlaremos el drag manualmente
}))

// Cursor según herramienta activa
const canvasCursor = computed(() => {
  if (isDragging.value) return 'grabbing'
  
  switch(props.activeTool) {
    case 'edit': return 'default'
    case 'pan': return isDragging.value ? 'grabbing' : 'grab'
    case 'bbox': return 'crosshair'
    case 'polygon': return 'crosshair'
    case 'eraser': return 'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'24\' height=\'24\' viewBox=\'0 0 24 24\'%3E%3Ccircle cx=\'12\' cy=\'12\' r=\'8\' fill=\'none\' stroke=\'%23f00\' stroke-width=\'2\'/%3E%3C/svg%3E") 12 12, auto'
    default: return 'default'
  }
})

// No necesitamos updateCanvasSize ya que el canvas se adaptará a la imagen
onMounted(() => {
  // Canvas inicial
})

onUnmounted(() => {
  // Cleanup si es necesario
})

const props = defineProps({
  imageUrl: String,
  imageId: [String, Number],
  activeTool: {
    type: String,
    default: 'edit'
  },
  toolSettings: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['annotation-saved', 'annotation-deleted'])

const image = ref(null)
const imageConfig = reactive({
  image: null,
  x: 0,
  y: 0,
  width: 0,
  height: 0,
  naturalWidth: 0,
  naturalHeight: 0,
  scaleX: 1,
  scaleY: 1
})

const imageOffset = computed(() => ({
  x: imageConfig.x || 0,
  y: imageConfig.y || 0
}))

const imageBounds = computed(() => ({
  width: imageConfig.width || imageConfig.naturalWidth || 0,
  height: imageConfig.height || imageConfig.naturalHeight || 0
}))

const imageScale = computed(() => ({
  x: imageConfig.naturalWidth ? imageConfig.width / imageConfig.naturalWidth : 1,
  y: imageConfig.naturalHeight ? imageConfig.height / imageConfig.naturalHeight : 1
}))

const toCanvasX = (value) => value + imageOffset.value.x
const toCanvasY = (value) => value + imageOffset.value.y
const toCanvasPoint = (point) => [toCanvasX(point[0]), toCanvasY(point[1])]

const toImageX = (value) => value - imageOffset.value.x
const toImageY = (value) => value - imageOffset.value.y

const canvasBounds = computed(() => ({
  left: imageOffset.value.x,
  top: imageOffset.value.y,
  right: imageOffset.value.x + (imageConfig.width || 0),
  bottom: imageOffset.value.y + (imageConfig.height || 0)
}))

function clampValue(value, min, max) {
  if (Number.isNaN(value)) return min
  if (max <= min) return min
  return Math.min(Math.max(value, min), max)
}

function clampImageX(value) {
  return clampValue(value, 0, imageBounds.value.width)
}

function clampImageY(value) {
  return clampValue(value, 0, imageBounds.value.height)
}

function clampCanvasX(value) {
  return clampValue(value, canvasBounds.value.left, canvasBounds.value.right)
}

function clampCanvasY(value) {
  return clampValue(value, canvasBounds.value.top, canvasBounds.value.bottom)
}

function clampCanvasPoint(point) {
  return {
    x: clampCanvasX(point.x),
    y: clampCanvasY(point.y)
  }
}

// Canvas hidden para obtener ImageData
const hiddenCanvas = ref(null)
const hiddenCtx = ref(null)
const imageData = ref(null)

const drawing = ref(false)
const startPt = ref({ x: 0, y: 0 })
const currentPath = ref([]) // Para polígonos
const isPolygonComplete = ref(false)

// Variables para predicciones de IA
const predictions = ref([])
const predictionCategories = ref([])
const hoveredPrediction = ref(null)
const selectedPrediction = ref(null)
const predictionButtonHover = ref(null)

// Estados específicos para herramientas
const eraserRadius = computed(() => Number(props.toolSettings?.eraser?.radius) || 12)
const polygonGuidance = computed(() => props.toolSettings?.polygon?.guidance !== false)
const minDistance = computed(() => props.toolSettings?.polygon?.minDistance || 2)
const completeDistance = computed(() => props.toolSettings?.polygon?.completeDistance || 15)

const drawingRect = reactive({
  x: 0,
  y: 0,
  width: 0,
  height: 0,
  fill: '#3498db40',
  stroke: '#3498db',
  strokeWidth: 2,
  dash: [4, 4]
})

const annotations = computed(() => {
  // Usar el nuevo getter que ya incluye filtrado por imagen actual y visibilidad
  return store.getVisibleCurrentImageAnnotations
})

// Función para obtener el color de una categoría sin importar si llega el id o el nombre
function getCategoryColor(categoryRef) {
  if (!categoryRef) {
    return '#e74c3c'
  }

  const category = store.getCategoryById(categoryRef) ||
    store.categories.find(cat => cat.name === categoryRef)

  return category && category.color ? category.color : '#e74c3c'
}

// Variable para prevenir eliminaciones duplicadas
let isDeleting = false

// Eventos de teclado para herramientas
function handleKeyDown(e) {
  if (e.key === 'Escape') {
    // Cancelar polígono en construcción
    if (props.activeTool === 'polygon' && currentPath.value.length > 0) {
      currentPath.value = []
    }
    // Deseleccionar anotación si hay una seleccionada
    if (store.selectedAnnotation) {
      store.clearSelection()
    }
  } else if (e.key === 'Enter') {
    // Completar polígono con Enter
    if (props.activeTool === 'polygon' && currentPath.value.length >= 3) {
      completePolygon()
    }
  } else if (e.key === 'Delete' || e.key === 'Backspace') {
    // Eliminar anotación seleccionada
    if (store.selectedAnnotation && !isDeleting) {
      e.preventDefault()
      deleteSelectedAnnotation()
    }
  } else if (e.key === 'r' || e.key === 'R') {
    // Reset zoom con la tecla R
    resetZoom()
  }
}

// ==================== FUNCIONES DE ZOOM Y PAN ====================

function handleWheel(e) {
  e.evt.preventDefault()
  
  const stage = stageRef.value.getNode()
  const pointer = stage.getPointerPosition()
  
  // Factor de zoom
  const scaleBy = 1.05
  const oldScale = scale.value
  const newScale = e.evt.deltaY > 0 ? oldScale / scaleBy : oldScale * scaleBy
  
  // Limitar el zoom entre 0.1x y 5x
  scale.value = Math.max(0.1, Math.min(5, newScale))
  
  // Calcular nueva posición para mantener el punto del mouse fijo
  const mousePointTo = {
    x: (pointer.x - stagePos.x) / oldScale,
    y: (pointer.y - stagePos.y) / oldScale
  }
  
  const newPos = {
    x: pointer.x - mousePointTo.x * scale.value,
    y: pointer.y - mousePointTo.y * scale.value
  }
  
  // Aplicar nuevos valores y luego forzar límites
  stagePos.x = newPos.x
  stagePos.y = newPos.y
  applyStagePanLimits()
}

function resetZoom() {
  scale.value = 1
  
  // Centrar la vista en la imagen cuando está en el canvas expandido
  if (imageConfig.width && imageConfig.height) {
    // Calcular la posición para centrar la imagen en la vista
    const canvasCenterX = stageWidth.value / 2
    const canvasCenterY = stageHeight.value / 2
    const imageCenterX = imageConfig.x + imageConfig.width / 2
    const imageCenterY = imageConfig.y + imageConfig.height / 2
    
    stagePos.x = canvasCenterX - imageCenterX
    stagePos.y = canvasCenterY - imageCenterY
    // Aplicar límites que dependen del tamaño del stage / imagen
    applyStagePanLimits()
  } else {
    stagePos.x = 0
    stagePos.y = 0
  }
}

// ==================== HELPERS PARA LIMPIAR Y LIMTAR EL PAN ====================
function getStagePanLimits() {
  // Posiciones en escala actual
  const s = scale.value
  const imageLeft = imageConfig.x * s
  const imageTop = imageConfig.y * s
  const imageRight = (imageConfig.x + imageConfig.width) * s
  const imageBottom = (imageConfig.y + imageConfig.height) * s

  // Limites para que la imagen cubra el viewport del stage
  let minX = stageWidth.value - imageRight
  let maxX = -imageLeft
  let minY = stageHeight.value - imageBottom
  let maxY = -imageTop

  // Si la imagen escalada es más pequeña que el stage en un eje,
  // centrarla en ese eje (min==max => pos centrada)
  const scaledImageWidth = (imageConfig.width || 0) * s
  const scaledImageHeight = (imageConfig.height || 0) * s

  if (scaledImageWidth <= stageWidth.value) {
    const centerX = stageWidth.value / 2 - (imageConfig.x + (imageConfig.width || 0) / 2) * s
    minX = centerX
    maxX = centerX
  }

  if (scaledImageHeight <= stageHeight.value) {
    const centerY = stageHeight.value / 2 - (imageConfig.y + (imageConfig.height || 0) / 2) * s
    minY = centerY
    maxY = centerY
  }

  // Asegurar que min <= max
  if (minX > maxX) {
    const centerX = stageWidth.value / 2 - (imageConfig.x + (imageConfig.width || 0) / 2) * s
    minX = centerX
    maxX = centerX
  }
  if (minY > maxY) {
    const centerY = stageHeight.value / 2 - (imageConfig.y + (imageConfig.height || 0) / 2) * s
    minY = centerY
    maxY = centerY
  }

  return { minX, maxX, minY, maxY }
}

function applyStagePanLimits() {
  const { minX, maxX, minY, maxY } = getStagePanLimits()
  stagePos.x = clampValue(stagePos.x, minX, maxX)
  stagePos.y = clampValue(stagePos.y, minY, maxY)
}

function getRelativePointerPosition(stage) {
  const transform = stage.getAbsoluteTransform().copy()
  transform.invert()
  const pos = stage.getPointerPosition()
  return transform.point(pos)
}

// Función para eliminar anotación seleccionada con protección contra duplicados
async function deleteSelectedAnnotation() {
  if (isDeleting || !store.selectedAnnotation) {
    return
  }
  
  isDeleting = true
  const annotationId = store.selectedAnnotation._id
  
  console.log('Eliminando anotación:', annotationId)
  
  try {
    await store.removeAnnotation(annotationId)
    store.clearSelection()
    emit('annotation-saved')
    console.log('Anotación eliminada exitosamente:', annotationId)
  } catch (error) {
    console.error('Error al eliminar anotación:', error)
  } finally {
    // Resetear el flag después de un breve delay
    setTimeout(() => {
      isDeleting = false
    }, 100)
  }
}

// Manejar doble clic para completar polígono
function handleDoubleClick(e) {
  if (props.activeTool === 'polygon' && currentPath.value.length >= 3) {
    completePolygon()
  } else if (e.target === e.target.getStage()) {
    // Doble clic en el fondo para resetear zoom
    resetZoom()
  }
}

// Añadir event listeners
onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)
  // Escucha cambios de tamaño para recalcular el área disponible
  window.addEventListener('resize', updateStageSize)
  // Inicializar tamaño del stage al tamaño disponible
  updateStageSize()
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('resize', updateStageSize)
})

function getAvailableStageSize() {
  // Sidebar izquierdo: 380px, Sidebar derecho: 350px, padding: 80px total
  const availableWidth = Math.max(window.innerWidth - 380 - 350 - 80, 400)
  const availableHeight = Math.max(window.innerHeight - 120, 300)
  return { availableWidth, availableHeight }
}

function updateStageSize() {
  const { availableWidth, availableHeight } = getAvailableStageSize()
  stageWidth.value = availableWidth
  stageHeight.value = availableHeight
  // Asegurar que el pan respete los nuevos límites
  applyStagePanLimits()
}

watch(
  () => props.imageUrl,
  (url) => {
    if (!url) return
    console.log('Cargando imagen:', url)
    const img = new window.Image()
    img.crossOrigin = 'anonymous' // Para evitar problemas de CORS
    img.onload = () => {
      console.log('Imagen cargada:', img.width, 'x', img.height)
   
      // Calcular el espacio disponible considerando los sidebars
      // Sidebar izquierdo: 380px, Sidebar derecho: 350px, padding: 80px total
      const availableWidth = window.innerWidth - 380 - 350 - 80
      const availableHeight = window.innerHeight - 120 // Header + padding
      
      // Calcular el tamaño máximo respetando el espacio disponible
      const maxWidth = Math.max(availableWidth, 400) // Mínimo 400px
      const maxHeight = Math.max(availableHeight, 300) // Mínimo 300px

      // Calcular escala para ajustar la imagen manteniendo proporción
      const scaleX = maxWidth / img.width
      const scaleY = maxHeight / img.height
      const scale = Math.min(scaleX, scaleY, 1) // No agrandar más del tamaño original

      const scaledWidth = img.width * scale
      const scaledHeight = img.height * scale


  // 1. El canvas (stage) debe ocupar el espacio disponible (para permitir mover la imagen)
  //    pero la imagen se mantiene centrada por defecto ("pegada" al centro como antes)
  const canvasWidth = maxWidth
  const canvasHeight = maxHeight

  // 2. Centrar la imagen dentro del canvas por defecto. De esta forma la imagen se
  // empezará "pegada" en el centro como antes, pero el usuario podrá hacer zoom y
  // moverla dentro del espacio disponible
  const imageX = Math.round((canvasWidth - scaledWidth) / 2)
  const imageY = Math.round((canvasHeight - scaledHeight) / 2)

  stageWidth.value = canvasWidth
  stageHeight.value = canvasHeight
      // Configurar la imagen para que llene el canvas
      Object.assign(imageConfig, {
        image: img,
        width: scaledWidth,
        height: scaledHeight,
        naturalWidth: img.width,
        naturalHeight: img.height,
        x: imageX,
        y: imageY
      })     
       
    image.value = img
      
      // Crear canvas oculto para obtener datos de imagen
      createImageData(img, scaledWidth, scaledHeight)
      
      // Centrar la vista en la imagen al cargar
      resetZoom()
    }
    img.onerror = (error) => {
      console.error('Error cargando imagen:', error)
    }
    img.src = url
  },
  { immediate: true }
)

// Función para crear datos de imagen
function createImageData(img, width, height) {
  // Crear canvas oculto
  if (!hiddenCanvas.value) {
    hiddenCanvas.value = document.createElement('canvas')
    hiddenCtx.value = hiddenCanvas.value.getContext('2d')
  }
  
  hiddenCanvas.value.width = width
  hiddenCanvas.value.height = height
  
  // Dibujar la imagen en el canvas oculto
  hiddenCtx.value.drawImage(img, 0, 0, width, height)
  
  // Obtener los datos de imagen
  try {
    imageData.value = hiddenCtx.value.getImageData(0, 0, width, height)
  } catch (e) {
    console.warn('No se pudieron obtener los datos de imagen:', e)
    imageData.value = null
  }
}

function startDraw(e) {
  console.log('Mouse down en canvas, herramienta activa:', props.activeTool)
  
  // Para la herramienta pan, siempre permitir arrastre
  if (props.activeTool === 'pan') {
    isDragging.value = true
    const pos = e.target.getStage().getPointerPosition()
    lastPointerPos.value = { x: pos.x, y: pos.y }
    return
  }
  
  const stage = stageRef.value.getNode()
  const rawPos = getRelativePointerPosition(stage)
  const clampedCanvasPos = clampCanvasPoint(rawPos)
  const clampedImagePos = {
    x: clampImageX(toImageX(clampedCanvasPos.x)),
    y: clampImageY(toImageY(clampedCanvasPos.y))
  }
  const canvasPos = {
    x: toCanvasX(clampedImagePos.x),
    y: toCanvasY(clampedImagePos.y)
  }
  startPt.value = canvasPos
  
  switch(props.activeTool) {
    case 'edit':
      // En modo edición, solo deseleccionar si se hace clic en el fondo
      if (e.target === e.target.getStage()) {
        store.clearSelection()
      }
      break
      
    case 'bbox':
      drawing.value = true
      const color = getCategoryColor(store.selectedCategory) || '#3498db'
      Object.assign(drawingRect, { 
        x: canvasPos.x, 
        y: canvasPos.y, 
        width: 0, 
        height: 0,
        fill: color + '40',
        stroke: color,
        strokeWidth: 2,
        dash: [4, 4]
      })
      startPt.value = canvasPos
      break
      
    case 'polygon':
      handlePolygonClick(canvasPos)
      break
      
    case 'eraser':
      drawing.value = true
      eraseAtPosition(canvasPos)
      break
  }
}

function draw(e) {
  // Si estamos arrastrando para pan
  if (isDragging.value) {
    const stage = e.target.getStage()
    const pos = stage.getPointerPosition()
    const dx = pos.x - lastPointerPos.value.x
    const dy = pos.y - lastPointerPos.value.y
    
    stagePos.x += dx
    stagePos.y += dy
    
    // Mantener el pan dentro de los límites permitidos
    applyStagePanLimits()

    lastPointerPos.value = { x: pos.x, y: pos.y }
    return
  }
  
  if (!drawing.value) return
  
  const stage = stageRef.value.getNode()
  const rawPos = getRelativePointerPosition(stage)
  const clampedCanvasPos = clampCanvasPoint(rawPos)
  const clampedImagePos = {
    x: clampImageX(toImageX(clampedCanvasPos.x)),
    y: clampImageY(toImageY(clampedCanvasPos.y))
  }
  const canvasPos = {
    x: toCanvasX(clampedImagePos.x),
    y: toCanvasY(clampedImagePos.y)
  }
  
  switch(props.activeTool) {
    case 'bbox':
      // Limitar posición del cursor dentro de la imagen
      drawingRect.width = canvasPos.x - startPt.value.x
      drawingRect.height = canvasPos.y - startPt.value.y
      break
      
    case 'eraser':
      startPt.value = canvasPos
      eraseAtPosition(canvasPos)
      break
  }
}

function endDraw() {
  // Si estamos terminando un pan drag
  if (isDragging.value) {
    isDragging.value = false
    return
  }
  
  if (!drawing.value) return
  
  switch(props.activeTool) {
    case 'bbox':
      completeBBox()
      break
      
    case 'eraser':
      // Limpiar los conjuntos de anotaciones borradas
      erasedAnnotations.value.clear()
      deletingAnnotations.value.clear()
      break
  }
  
  drawing.value = false
}

// Función para verificar si un punto está dentro del polígono usando ray casting
function isPointInsidePolygon(point, polygon) {
  if (polygon.length < 3) return true // Si tenemos menos de 3 puntos, consideramos que está "dentro"
  
  let inside = false
  const x = point.x, y = point.y
  
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i][0], yi = polygon[i][1]
    const xj = polygon[j][0], yj = polygon[j][1]
    
    if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
      inside = !inside
    }
  }
  
  return inside
}

// Funciones específicas para cada herramienta
function handlePolygonClick(pos) {
  // Limitar posición dentro de la imagen
  const clampedCanvasPos = clampCanvasPoint(pos)
  const clampedImagePos = {
    x: clampImageX(toImageX(clampedCanvasPos.x)),
    y: clampImageY(toImageY(clampedCanvasPos.y))
  }
  const clampedPos = {
    x: toCanvasX(clampedImagePos.x),
    y: toCanvasY(clampedImagePos.y)
  }
  
  // Si es el primer punto
  if (currentPath.value.length === 0) {
    currentPath.value = [[clampedPos.x, clampedPos.y]]
    return
  }
  
  // Verificar si el clic está cerca del primer punto para cerrar el polígono
  const firstPoint = currentPath.value[0]
  const distance = Math.sqrt(
    Math.pow(clampedPos.x - firstPoint[0], 2) + Math.pow(clampedPos.y - firstPoint[1], 2)
  )
  
  if (distance < completeDistance.value && currentPath.value.length >= 3) {
    // Cerrar polígono haciendo clic cerca del primer punto
    completePolygon()
    return
  }
  
  // Si tenemos al menos 4 puntos, verificar si el nuevo clic está fuera del polígono
  // Usamos 4 puntos para que el usuario pueda dar forma al polígono antes de la detección automática
  if (currentPath.value.length >= 4) {
    const isInside = isPointInsidePolygon(clampedPos, currentPath.value)
    
    // Si el punto está fuera del polígono, completarlo automáticamente
    if (!isInside) {
      console.log('Clic fuera del polígono detectado, completando automáticamente')
      completePolygon()
      return
    }
  }
  
  // Agregar nuevo punto si está suficientemente lejos del último punto
  const lastPoint = currentPath.value[currentPath.value.length - 1]
  const lastDistance = Math.sqrt(
    Math.pow(clampedPos.x - lastPoint[0], 2) + Math.pow(clampedPos.y - lastPoint[1], 2)
  )
  
  if (lastDistance >= minDistance.value) {
    currentPath.value.push([clampedPos.x, clampedPos.y])
    console.log(`Punto ${currentPath.value.length} agregado al polígono`)
  }
}

async function completeBBox() {
  if (Math.abs(drawingRect.width) > 10 && Math.abs(drawingRect.height) > 10) {
    try {
      const minCanvasX = clampCanvasX(Math.min(drawingRect.x, drawingRect.x + drawingRect.width))
      const minCanvasY = clampCanvasY(Math.min(drawingRect.y, drawingRect.y + drawingRect.height))
      const maxCanvasX = clampCanvasX(Math.max(drawingRect.x, drawingRect.x + drawingRect.width))
      const maxCanvasY = clampCanvasY(Math.max(drawingRect.y, drawingRect.y + drawingRect.height))

      const imageMinX = clampImageX(toImageX(minCanvasX))
      const imageMinY = clampImageY(toImageY(minCanvasY))
      const imageMaxX = clampImageX(toImageX(maxCanvasX))
      const imageMaxY = clampImageY(toImageY(maxCanvasY))

      const bboxWidth = Math.abs(imageMaxX - imageMinX)
      const bboxHeight = Math.abs(imageMaxY - imageMinY)

      if (bboxWidth <= 0 || bboxHeight <= 0) {
        return
      }

      await store.addAnnotation(props.imageId, {
        bbox: [
          Math.min(imageMinX, imageMaxX),
          Math.min(imageMinY, imageMaxY),
          bboxWidth,
          bboxHeight
        ],
        type: 'bbox'
      })
      emit('annotation-saved')
    } catch (error) {
      console.error('Error al crear anotación bbox:', error)
    }
  }
}

async function completePolygon() {
  if (currentPath.value.length >= 3) {
    const imagePoints = currentPath.value.map(([x, y]) => [
      clampImageX(toImageX(x)),
      clampImageY(toImageY(y))
    ])

    // Calcular bounding box del polígono en coordenadas de imagen
    const xs = imagePoints.map(p => p[0])
    const ys = imagePoints.map(p => p[1])
    const minX = Math.min(...xs)
    const minY = Math.min(...ys)
    const maxX = Math.max(...xs)
    const maxY = Math.max(...ys)
    const bboxWidth = maxX - minX
    const bboxHeight = maxY - minY

    if (bboxWidth <= 0 || bboxHeight <= 0) {
      currentPath.value = []
      return
    }
    
    try {
      await store.addAnnotation(props.imageId, {
        bbox: [minX, minY, bboxWidth, bboxHeight],
        type: 'polygon',
        points: imagePoints
      })
      emit('annotation-saved')
    } catch (error) {
      console.error('Error al crear anotación polígono:', error)
    }
  }
  
  // Limpiar path
  currentPath.value = []
}

const erasedAnnotations = ref(new Set())
const deletingAnnotations = ref(new Set()) // Para evitar eliminaciones concurrentes

async function eraseAtPosition(pos) {
  // Encontrar anotaciones que intersectan con el área del borrador
  const annotations = store.getAnnotationsByImageId(props.imageId)
  
  for (const ann of annotations) {
    // Si ya fue borrada o está siendo borrada, omitir
    if (erasedAnnotations.value.has(ann._id) || deletingAnnotations.value.has(ann._id)) continue
    
    let shouldErase = false
    
    if (ann.type === 'polygon' && ann.points) {
      // Para polígonos, verificar si algún punto está dentro del círculo del borrador
      for (const point of ann.points) {
        const [canvasX, canvasY] = toCanvasPoint(point)
        const distance = Math.sqrt(
          Math.pow(pos.x - canvasX, 2) + Math.pow(pos.y - canvasY, 2)
        )
        if (distance < eraserRadius.value) {
          shouldErase = true
          break
        }
      }
    } else if (ann.bbox) {
      // Para rectángulos, verificar intersección con el círculo del borrador
      const rectLeft = toCanvasX(ann.bbox[0])
      const rectTop = toCanvasY(ann.bbox[1])
      const rectRight = rectLeft + ann.bbox[2]
      const rectBottom = rectTop + ann.bbox[3]
      
      // Encontrar el punto más cercano del rectángulo al centro del borrador
      const closestX = Math.max(rectLeft, Math.min(pos.x, rectRight))
      const closestY = Math.max(rectTop, Math.min(pos.y, rectBottom))
      
      const distance = Math.sqrt(
        Math.pow(pos.x - closestX, 2) + Math.pow(pos.y - closestY, 2)
      )
      
      shouldErase = distance < eraserRadius.value
    }
    
    if (shouldErase) {
      // Marcar como "siendo eliminada" para evitar duplicados
      deletingAnnotations.value.add(ann._id)
      
      try {
        console.log('Eliminando anotación con borrador:', ann._id)
        await store.removeAnnotation(ann._id)
        erasedAnnotations.value.add(ann._id)
        emit('annotation-saved')
        console.log('Anotación eliminada exitosamente:', ann._id)
      } catch (error) {
        console.error('Error al eliminar anotación:', error)
      } finally {
        // Remover del set de "siendo eliminadas" después de un breve delay
        setTimeout(() => {
          deletingAnnotations.value.delete(ann._id)
        }, 100)
      }
    }
  }
}

// ==================== FUNCIONES DE EDICIÓN ====================

function isSelectedAnnotation(annotation) {
  return store.selectedAnnotation && store.selectedAnnotation._id === annotation._id
}

function handleAnnotationClick(annotation) {
  if (props.activeTool === 'edit') {
    // Si ya está seleccionada, deseleccionar
    if (isSelectedAnnotation(annotation)) {
      store.clearSelection()
    } else {
      store.selectAnnotation(annotation)
    }
  }
}

function handleAnnotationDrag(annotation, event) {
  if (props.activeTool !== 'edit') return
  
  const node = event.target
  const currentPos = { x: node.x(), y: node.y() }
  
  // Para rectángulos (bbox), actualizar bbox en tiempo real para que los controles se muevan
  if (annotation.bbox && (annotation.type === 'bbox' || !annotation.type)) {
    const width = annotation.bbox[2]
    const height = annotation.bbox[3]
    const imageX = toImageX(currentPos.x)
    const imageY = toImageY(currentPos.y)

    const maxX = Math.max(0, imageBounds.value.width - width)
    const maxY = Math.max(0, imageBounds.value.height - height)

    const clampedX = clampValue(imageX, 0, maxX)
    const clampedY = clampValue(imageY, 0, maxY)

    // Actualizar bbox temporalmente para feedback instantáneo
    store.updateAnnotationLocally(annotation._id, { bbox: [clampedX, clampedY, width, height] })

    // Asegurar que la posición del nodo sea correcta
    node.position({ x: toCanvasX(clampedX), y: toCanvasY(clampedY) })
  }
  // Para polígonos, solo verificar límites
  else if (annotation.points && annotation.type === 'polygon') {
    // Permitir movimiento libre del grupo
    // La verificación de límites se hará en dragend
  }
}

function handleAnnotationDragEnd(annotation, event) {
  if (props.activeTool !== 'edit') return
  
  const node = event.target
  const groupPos = { x: node.x(), y: node.y() }
  
  if (annotation.bbox && (annotation.type === 'bbox' || !annotation.type)) {
    // Para rectángulos, ya actualizamos bbox durante el drag
    // Solo necesitamos guardar en el store
    const width = annotation.bbox[2]
    const height = annotation.bbox[3]
    const imageX = toImageX(groupPos.x)
    const imageY = toImageY(groupPos.y)

    const maxX = Math.max(0, imageBounds.value.width - width)
    const maxY = Math.max(0, imageBounds.value.height - height)

    const clampedX = clampValue(imageX, 0, maxX)
    const clampedY = clampValue(imageY, 0, maxY)

    const newBbox = [clampedX, clampedY, width, height]
    annotation.bbox = newBbox
    
    // Guardar en el store
    store.updateAnnotation(annotation._id, { bbox: newBbox })

    // Asegurar posición final
    node.position({ x: toCanvasX(clampedX), y: toCanvasY(clampedY) })
    
  } else if (annotation.points && annotation.type === 'polygon') {
    // Ignorar dragend disparado por los manejadores hijos (puntos individuales)
    if (event.target !== event.currentTarget) {
      return
    }

    // Actualiza las coordenadas de los puntos del polígono cuando su grupo cambia de posición.
    // El desplazamiento se aplica en el sistema de coordenadas del canvas.
    const deltaCanvasX = groupPos.x
    const deltaCanvasY = groupPos.y
    

    const deltaImageX = deltaCanvasX
    const deltaImageY = deltaCanvasY

    // -----------------------------------------------------------------
    
    // Si el movimiento es muy pequeño, ignorar
    if (Math.abs(deltaImageX) < 0.5 && Math.abs(deltaImageY) < 0.5) {
      node.position({ x: 0, y: 0 })
      return
    }

    // Calcular nuevos puntos aplicando el desplazamiento
    const newPoints = annotation.points.map(point => [
      point[0] + deltaImageX,
      point[1] + deltaImageY
    ])

    // Verificar límites
    const xs = newPoints.map(point => point[0])
    const ys = newPoints.map(point => point[1])
    let minX = Math.min(...xs)
    let minY = Math.min(...ys)
    let maxX = Math.max(...xs)
    let maxY = Math.max(...ys)

    // Si se sale de límites, ajustar todos los puntos
    let finalPoints = newPoints
    if (minX < 0 || minY < 0 || maxX > imageBounds.value.width || maxY > imageBounds.value.height) {
      const adjustX = Math.max(0, -minX) - Math.max(0, maxX - imageBounds.value.width)
      const adjustY = Math.max(0, -minY) - Math.max(0, maxY - imageBounds.value.height)
      
      finalPoints = newPoints.map(point => [
        point[0] + adjustX,
        point[1] + adjustY
      ])
      
      // Recalcular límites
      const adjXs = finalPoints.map(point => point[0])
      const adjYs = finalPoints.map(point => point[1])
      minX = Math.min(...adjXs)
      minY = Math.min(...adjYs)
      maxX = Math.max(...adjXs)
      maxY = Math.max(...adjYs)
    }

    // Actualizar anotación
    annotation.points = finalPoints
    annotation.bbox = [minX, minY, maxX - minX, maxY - minY]

    // Guardar en el store
    store.updateAnnotation(annotation._id, {
      points: finalPoints,
      bbox: annotation.bbox
    })

    // IMPORTANTE: Resetear la posición del grupo a (0, 0)
    node.position({ x: 0, y: 0 })
  }
}

function handleResizeDrag(annotation, event, handle) {
  if (props.activeTool !== 'edit') return
  
  const node = event.target
  const canvasPos = {
    x: node.x(),
    y: node.y()
  }
  const imagePos = {
    x: clampImageX(toImageX(canvasPos.x)),
    y: clampImageY(toImageY(canvasPos.y))
  }
  
  const minSize = 10
  const [origX, origY, origWidth, origHeight] = annotation.bbox
  const origRight = origX + origWidth
  const origBottom = origY + origHeight
  let x = origX
  let y = origY
  let width = origWidth
  let height = origHeight
  
  // Calcular nuevas dimensiones según el manejador
  switch (handle) {
    case 'nw': // Noroeste (superior izquierda)
      x = clampValue(imagePos.x, 0, origRight - minSize)
      y = clampValue(imagePos.y, 0, origBottom - minSize)
      width = Math.max(origRight - x, minSize)
      height = Math.max(origBottom - y, minSize)
      // Forzar posición del nodo
      node.position({ x: toCanvasX(x), y: toCanvasY(y) })
      break
      
    case 'ne': // Noreste (superior derecha)
      y = clampValue(imagePos.y, 0, origBottom - minSize)
      const newRightNE = clampValue(imagePos.x, origX + minSize, imageBounds.value.width)
      width = Math.max(newRightNE - origX, minSize)
      height = Math.max(origBottom - y, minSize)
      // Forzar posición del nodo
      node.position({ x: toCanvasX(origX + width), y: toCanvasY(y) })
      break
      
    case 'sw': // Suroeste (inferior izquierda)
      x = clampValue(imagePos.x, 0, origRight - minSize)
      const newBottomSW = clampValue(imagePos.y, origY + minSize, imageBounds.value.height)
      width = Math.max(origRight - x, minSize)
      height = Math.max(newBottomSW - origY, minSize)
      // Forzar posición del nodo
      node.position({ x: toCanvasX(x), y: toCanvasY(origY + height) })
      break
      
    case 'se': // Sureste (inferior derecha)
      const newRightSE = clampValue(imagePos.x, origX + minSize, imageBounds.value.width)
      const newBottomSE = clampValue(imagePos.y, origY + minSize, imageBounds.value.height)
      width = Math.max(newRightSE - origX, minSize)
      height = Math.max(newBottomSE - origY, minSize)
      // Forzar posición del nodo
      node.position({ x: toCanvasX(origX + width), y: toCanvasY(origY + height) })
      break
      
    case 'n': // Norte (arriba)
      y = clampValue(imagePos.y, 0, origBottom - minSize)
      height = Math.max(origBottom - y, minSize)
      // Forzar posición del nodo
      node.position({ x: toCanvasX(origX + origWidth / 2), y: toCanvasY(y) })
      break
      
    case 's': // Sur (abajo)
      const newBottom = clampValue(imagePos.y, origY + minSize, imageBounds.value.height)
      height = Math.max(newBottom - origY, minSize)
      // Forzar posición del nodo
      node.position({ x: toCanvasX(origX + origWidth / 2), y: toCanvasY(origY + height) })
      break
      
    case 'w': // Oeste (izquierda)
      x = clampValue(imagePos.x, 0, origRight - minSize)
      width = Math.max(origRight - x, minSize)
      // Forzar posición del nodo
      node.position({ x: toCanvasX(x), y: toCanvasY(origY + origHeight / 2) })
      break
      
    case 'e': // Este (derecha)
      const newRight = clampValue(imagePos.x, origX + minSize, imageBounds.value.width)
      width = Math.max(newRight - origX, minSize)
      // Forzar posición del nodo
      node.position({ x: toCanvasX(origX + width), y: toCanvasY(origY + origHeight / 2) })
      break
  }
  
  width = Math.min(width, imageBounds.value.width - x)
  height = Math.min(height, imageBounds.value.height - y)
  width = Math.max(width, minSize)
  height = Math.max(height, minSize)
  
  // Actualizar la anotación con las nuevas dimensiones
  const updatedBbox = [x, y, width, height]
  const hasChanged =
    x !== origX ||
    y !== origY ||
    width !== origWidth ||
    height !== origHeight

  annotation.bbox = updatedBbox

  if (hasChanged) {
    // Actualizar localmente para feedback instantáneo durante el drag
    store.updateAnnotationLocally(annotation._id, { bbox: updatedBbox })
  }
}

function handlePolygonPointDrag(annotation, pointIndex, event) {
  if (props.activeTool !== 'edit') return
  
  const node = event.target
  // OBTENER EL NODO DEL STAGE
  const stage = stageRef.value.getNode()

  // Obtiene la posición lógica del cursor, que ya ha sido
  // transformada correctamente por Konva (manejando el zoom).
  const canvasPos = getRelativePointerPosition(stage)
  

  const clampedX = clampImageX(toImageX(canvasPos.x))
  const clampedY = clampImageY(toImageY(canvasPos.y))

  // Forzar posición del nodo para que se quede en los límites visualmente
  node.position({ x: toCanvasX(clampedX), y: toCanvasY(clampedY) })

  const newPoints = annotation.points.map((point, idx) =>
    idx === pointIndex ? [clampedX, clampedY] : [...point]
  )

  const currentPoint = annotation.points[pointIndex]
  const hasChanged = currentPoint[0] !== clampedX || currentPoint[1] !== clampedY

  if (hasChanged) {
    const xs = newPoints.map(point => point[0])
    const ys = newPoints.map(point => point[1])
    const minX = Math.min(...xs)
    const minY = Math.min(...ys)
    const maxX = Math.max(...xs)
    const maxY = Math.max(...ys)

    const newBbox = [minX, minY, maxX - minX, maxY - minY]
    // Actualización local reactiva
    store.updateAnnotationLocally(annotation._id, {
      points: newPoints,
      bbox: newBbox
    })
  }
}

function handleResizeDragEnd(annotation) {
  if (!annotation) return
  if (annotation.bbox) {
    store.updateAnnotation(annotation._id, { bbox: annotation.bbox }).catch(err => {
      console.error('Error al guardar BBox en dragEnd:', err)
    })
  }
}

function handlePolygonPointDragEnd(annotation) {
  if (!annotation) return
  if (annotation.points) {
    store.updateAnnotation(annotation._id, { points: annotation.points, bbox: annotation.bbox }).catch(err => {
      console.error('Error al guardar Polígono en dragEnd:', err)
    })
  }
}

// ==================== FUNCIONES PARA PREDICCIONES DE IA ====================

function showPredictions(detections, categories) {
  predictions.value = detections.map(detection => ({
    bbox: detection.bbox,
    class: detection.class,
    confidence: detection.confidence
  }))
  predictionCategories.value = categories
}

function clearPredictions() {
  predictions.value = []
  predictionCategories.value = []
  hoveredPrediction.value = null
  selectedPrediction.value = null
  predictionButtonHover.value = null
}

function getPredictionLabel(prediction) {
  const className = predictionCategories.value[prediction.class] || `Clase ${prediction.class}`
  const confidence = (prediction.confidence * 100).toFixed(1)
  return `${className} (${confidence}%)`
}

function getPredictionLabelWidth(prediction) {
  const label = getPredictionLabel(prediction)
  // Estimación aproximada del ancho del texto (12px font size * 0.6 factor aproximado)
  return Math.max(80, label.length * 7 + 10)
}

// Funciones para interacción con predicciones
function handlePredictionClick(prediction, index) {
  selectedPrediction.value = index
  console.log('Predicción seleccionada:', prediction)
}

function handlePredictionMouseEnter(index) {
  hoveredPrediction.value = index
  // Cambiar cursor para indicar que es clickeable
  document.body.style.cursor = 'pointer'
}

function handlePredictionMouseLeave() {
  hoveredPrediction.value = null
  // Restaurar cursor
  document.body.style.cursor = 'default'
}

function acceptPrediction(prediction, index) {
  console.log('Aceptando predicción:', prediction)
  
  // Verificar que hay un imageId disponible
  const imageId = props.imageId || store.currentImage?._id || store.currentImage?.id
  if (!imageId) {
    console.error('No hay imagen actual seleccionada')
    return
  }
  
  console.log('ImageId para guardar anotación:', imageId)

  // Convertir predicción a anotación
  const annotationData = {
    type: 'bbox',
    bbox: [...prediction.bbox], // Copiar bbox
    category_id: getCurrentCategoryForPrediction(prediction),
    confidence: prediction.confidence,
    source: 'ai_prediction' // Marcar como originada de IA
  }
  
  console.log('Datos de anotación a guardar:', annotationData)
  
  // Agregar la anotación usando el store
  store.addAnnotation(imageId, annotationData)
    .then(() => {
      console.log('Predicción convertida a anotación exitosamente')
      
      // Remover la predicción de la lista
      predictions.value.splice(index, 1)
      
      // Limpiar selección
      selectedPrediction.value = null
      hoveredPrediction.value = null
    })
    .catch((error) => {
      console.error('Error al convertir predicción a anotación:', error)
    })
}

function rejectPrediction(index) {
  console.log('Rechazando predicción en índice:', index)
  
  // Remover la predicción de la lista
  predictions.value.splice(index, 1)
  
  // Limpiar selección
  selectedPrediction.value = null
  hoveredPrediction.value = null
}

function getCurrentCategoryForPrediction(prediction) {
  // Buscar una categoría que coincida con la clase de la predicción
  const className = predictionCategories.value[prediction.class]
  console.log('Buscando categoría para predicción. Clase:', prediction.class, 'Nombre:', className)
  
  if (className) {
    // Buscar en las categorías del store una que tenga el mismo nombre
    const matchingCategory = store.categories.find(cat => 
      cat.name.toLowerCase() === className.toLowerCase()
    )
    if (matchingCategory) {
      console.log('Categoría coincidente encontrada:', matchingCategory)
      return matchingCategory.id
    }
  }
  
  // Si no se encuentra categoría coincidente, usar la categoría seleccionada actualmente
  if (store.selectedCategory) {
    console.log('Usando categoría seleccionada:', store.selectedCategory)
    return store.selectedCategory
  }
  
  // Si no hay categoría seleccionada, usar la primera disponible
  if (store.categories.length > 0) {
    console.log('Usando primera categoría disponible:', store.categories[0])
    return store.categories[0].id
  }
  
  // Si no hay categorías, retornar null
  console.warn('No se encontró ninguna categoría válida')
  return null
}

function getImageMetrics() {
  const naturalWidth = imageConfig.naturalWidth || image.value?.naturalWidth || image.value?.width || 0
  const naturalHeight = imageConfig.naturalHeight || image.value?.naturalHeight || image.value?.height || 0

  return {
    displayWidth: imageConfig.width || 0,
    displayHeight: imageConfig.height || 0,
    naturalWidth,
    naturalHeight,
    scaleX: naturalWidth ? (imageConfig.width || 0) / naturalWidth : 1,
    scaleY: naturalHeight ? (imageConfig.height || 0) / naturalHeight : 1
  }
}

// Exponer métodos para uso externo
defineExpose({
  showPredictions,
  clearPredictions,
  acceptPrediction,
  rejectPrediction,
  getImageMetrics
})
</script>

<style scoped>
.canvas-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.annotation-stage {
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  user-select: none; /* Prevenir selección de texto durante el arrastre */
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  cursor: grab;
}

.annotation-stage:active {
  cursor: grabbing;
}

/* Mensaje profesional de carga de imagen */
.image-loading-info {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f4f6fb;
  color: #2c3e50;
  border-radius: 10px;
  padding: 1.2rem 2rem;
  margin: 2rem auto;
  box-shadow: 0 4px 16px rgba(44,62,80,0.07);
  max-width: 480px;
  font-size: 1rem;
  gap: 1.2rem;
}
.loading-icon {
  font-size: 2.2rem;
  color: #3b82f6;
  margin-right: 0.5rem;
}
.loading-text {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.loading-text strong {
  font-size: 1.08rem;
  color: #2563eb;
}
.loading-url {
  font-size: 0.92rem;
  color: #6b7280;
}
.loading-url span {
  word-break: break-all;
  color: #374151;
}

.debug-canvas-info {
  color: #155724;
  background: #d4edda;
  border-color: #c3e6cb;
}
</style>
