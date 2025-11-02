<template>
  <div class="canvas-container">
    <!-- Debug info -->
    <div v-if="!image" class="debug-info">
      <p>Cargando imagen...</p>
      <p>URL: {{ props.imageUrl }}</p>
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
                  x: toCanvasX(ann.bbox[0]) + ann.bbox[2] / 2, // X fijo
                  y: pos.y // Solo Y puede cambiar
                })
              }"
              @dragmove="handleResizeDrag(ann, $event, 'n')"
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
                  x: toCanvasX(ann.bbox[0]) + ann.bbox[2] / 2, // X fijo
                  y: pos.y // Solo Y puede cambiar
                })
              }"
              @dragmove="handleResizeDrag(ann, $event, 's')"
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
                  x: pos.x, // Solo X puede cambiar
                  y: toCanvasY(ann.bbox[1]) + ann.bbox[3] / 2 // Y fijo
                })
              }"
              @dragmove="handleResizeDrag(ann, $event, 'w')"
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
                  x: pos.x, // Solo X puede cambiar
                  y: toCanvasY(ann.bbox[1]) + ann.bbox[3] / 2 // Y fijo
                })
              }"
              @dragmove="handleResizeDrag(ann, $event, 'e')"
            />
          </template>
          
          <!-- Polígonos agrupados con sus puntos de control -->
          <v-group
            v-if="ann.type === 'polygon' && ann.points && Array.isArray(ann.points) && ann.points.length >= 3"
            :config="{
              draggable: props.activeTool === 'edit',
              listening: true
            }"
            @click="handleAnnotationClick(ann)"
            @dragmove="handleAnnotationDrag(ann, $event)"
            @dragend="handleAnnotationDragEnd(ann, $event)"
          >
            <v-line
              :config="{
                points: ann.points.flatMap((point) => toCanvasPoint(point)),
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
                @dragend="handlePolygonPointDrag(ann, pointIndex, $event)"
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
            radius: eraserRadius,
            stroke: 'red',
            strokeWidth: 2,
            dash: [3, 3],
            listening: false
          }"
        />
      </v-layer>
    </v-stage>
    
    <!-- Debug canvas info -->
    <div v-if="image" class="debug-canvas-info">
      <p>Canvas: {{ stageWidth }}x{{ stageHeight }}</p>
      <p>Imagen: {{ imageConfig.width }}x{{ imageConfig.height }} en ({{ imageConfig.x }}, {{ imageConfig.y }})</p>
      <p>Zoom: {{ Math.round(scale * 100) }}% | Desplazamiento: ({{ Math.round(stagePos.x) }}, {{ Math.round(stagePos.y) }})</p>
      <p v-if="props.activeTool === 'pan'"><small>�️ Herramienta Pan activa - Arrastra para mover la vista | Rueda para zoom | 'R' para resetear</small></p>
      <p v-else><small>�💡 Usa la rueda del ratón para zoom | Tecla 'R' para resetear | Selecciona "Mover" para desplazarte</small></p>
    </div>
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
    default: 'select'
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
  height: 0
})

const imageOffset = computed(() => ({
  x: imageConfig.x || 0,
  y: imageConfig.y || 0
}))

const imageBounds = computed(() => ({
  width: imageConfig.width || 0,
  height: imageConfig.height || 0
}))

const toCanvasX = (value) => value + imageOffset.value.x
const toCanvasY = (value) => value + imageOffset.value.y
const toCanvasPoint = (point) => [toCanvasX(point[0]), toCanvasY(point[1])]

const toImageX = (value) => value - imageOffset.value.x
const toImageY = (value) => value - imageOffset.value.y

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

// Canvas hidden para obtener ImageData
const hiddenCanvas = ref(null)
const hiddenCtx = ref(null)
const imageData = ref(null)

const drawing = ref(false)
const startPt = ref({ x: 0, y: 0 })
const currentPath = ref([]) // Para polígonos
const isPolygonComplete = ref(false)

// Estados específicos para herramientas
const eraserRadius = computed(() => props.toolSettings?.eraser?.radius || 20)
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

// Función para obtener el color de una categoría
function getCategoryColor(categoryId) {
  const category = store.getCategoryById(categoryId)
  return category ? category.color : '#e74c3c'
}

function selectAnnotation(annotation) {
  console.log('Anotación seleccionada:', annotation)
  // Aquí puedes agregar lógica para seleccionar/editar anotaciones
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
  
  stagePos.x = newPos.x
  stagePos.y = newPos.y
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
  } else {
    stagePos.x = 0
    stagePos.y = 0
  }
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
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})

watch(
  () => props.imageUrl,
  (url) => {
    if (!url) return
    console.log('Cargando imagen:', url)
    const img = new window.Image()
    img.crossOrigin = 'anonymous' // Para evitar problemas de CORS
    img.onload = () => {
      console.log('Imagen cargada:', img.width, 'x', img.height)
      
      // Calcular el tamaño máximo para la ventana
      const maxWidth = Math.min(window.innerWidth - 200, img.width)
      const maxHeight = Math.min(window.innerHeight - 200, img.height)
      
      // Calcular escala para ajustar la imagen manteniendo proporción
      const scaleX = maxWidth / img.width
      const scaleY = maxHeight / img.height
      const scale = Math.min(scaleX, scaleY, 1) // No agrandar más del tamaño original

      const scaledWidth = img.width * scale
      const scaledHeight = img.height * scale

      // Factor de expansión del canvas para permitir zoom extendido
      const canvasExpansionFactor = 2.5
      
      // Hacer el canvas más grande que la imagen para permitir zoom extendido
      let canvasWidth = scaledWidth * canvasExpansionFactor
      let canvasHeight = scaledHeight * canvasExpansionFactor
      
      // Limitar el tamaño máximo del canvas para evitar problemas de rendimiento
      const maxCanvasWidth = Math.min(window.innerWidth - 50, 2000)
      const maxCanvasHeight = Math.min(window.innerHeight - 100, 1500)
      
      canvasWidth = Math.min(canvasWidth, maxCanvasWidth)
      canvasHeight = Math.min(canvasHeight, maxCanvasHeight)
      
      // Centrar la imagen en el canvas expandido
      const imageX = (canvasWidth - scaledWidth) / 2
      const imageY = (canvasHeight - scaledHeight) / 2

      stageWidth.value = canvasWidth
      stageHeight.value = canvasHeight

      // Configurar la imagen centrada en el canvas expandido
      Object.assign(imageConfig, {
        image: img,
        width: scaledWidth,
        height: scaledHeight,
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
  const pos = getRelativePointerPosition(stage)
  startPt.value = pos
  
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
        x: pos.x, 
        y: pos.y, 
        width: 0, 
        height: 0,
        fill: color + '40',
        stroke: color,
        strokeWidth: 2,
        dash: [4, 4]
      })
      break
      
    case 'polygon':
      handlePolygonClick(pos)
      break
      
    case 'eraser':
      drawing.value = true
      eraseAtPosition(pos)
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
    
    lastPointerPos.value = { x: pos.x, y: pos.y }
    return
  }
  
  if (!drawing.value) return
  
  const stage = stageRef.value.getNode()
  const pos = getRelativePointerPosition(stage)
  
  switch(props.activeTool) {
    case 'bbox':
      drawingRect.width = pos.x - startPt.value.x
      drawingRect.height = pos.y - startPt.value.y
      break
      
    case 'eraser':
      startPt.value = pos
      eraseAtPosition(pos)
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
  // Si es el primer punto
  if (currentPath.value.length === 0) {
    currentPath.value = [[pos.x, pos.y]]
    return
  }
  
  // Verificar si el clic está cerca del primer punto para cerrar el polígono
  const firstPoint = currentPath.value[0]
  const distance = Math.sqrt(
    Math.pow(pos.x - firstPoint[0], 2) + Math.pow(pos.y - firstPoint[1], 2)
  )
  
  if (distance < completeDistance.value && currentPath.value.length >= 3) {
    // Cerrar polígono haciendo clic cerca del primer punto
    completePolygon()
    return
  }
  
  // Si tenemos al menos 4 puntos, verificar si el nuevo clic está fuera del polígono
  // Usamos 4 puntos para que el usuario pueda dar forma al polígono antes de la detección automática
  if (currentPath.value.length >= 4) {
    const isInside = isPointInsidePolygon(pos, currentPath.value)
    
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
    Math.pow(pos.x - lastPoint[0], 2) + Math.pow(pos.y - lastPoint[1], 2)
  )
  
  if (lastDistance >= minDistance.value) {
    currentPath.value.push([pos.x, pos.y])
    console.log(`Punto ${currentPath.value.length} agregado al polígono`)
  }
}

async function completeBBox() {
  if (Math.abs(drawingRect.width) > 10 && Math.abs(drawingRect.height) > 10) {
    try {
      const minX = Math.min(drawingRect.x, drawingRect.x + drawingRect.width)
      const minY = Math.min(drawingRect.y, drawingRect.y + drawingRect.height)
      const maxX = Math.max(drawingRect.x, drawingRect.x + drawingRect.width)
      const maxY = Math.max(drawingRect.y, drawingRect.y + drawingRect.height)

      const imageMinX = clampImageX(toImageX(minX))
      const imageMinY = clampImageY(toImageY(minY))
      const imageMaxX = clampImageX(toImageX(maxX))
      const imageMaxY = clampImageY(toImageY(maxY))

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
  } else {
    // Para otras herramientas, mantener la funcionalidad original
    selectAnnotation(annotation)
  }
}

function handleAnnotationDrag(annotation, event) {
  if (props.activeTool !== 'edit') return
  
  // No mutamos la anotación aquí; el movimiento visual lo maneja Konva
}

function handleAnnotationDragEnd(annotation, event) {
  if (props.activeTool !== 'edit') return
  
  const node = event.target
  const currentPos = { x: node.x(), y: node.y() }
  
  if (annotation.bbox) {
    const width = annotation.bbox[2]
    const height = annotation.bbox[3]
    const tentativeX = clampImageX(toImageX(currentPos.x))
    const tentativeY = clampImageY(toImageY(currentPos.y))

    const maxX = Math.max(0, imageBounds.value.width - width)
    const maxY = Math.max(0, imageBounds.value.height - height)

    const clampedX = clampValue(tentativeX, 0, maxX)
    const clampedY = clampValue(tentativeY, 0, maxY)

    if (clampedX !== annotation.bbox[0] || clampedY !== annotation.bbox[1]) {
      const newBbox = [clampedX, clampedY, width, height]
      annotation.bbox = newBbox
      store.updateAnnotation(annotation._id, { bbox: newBbox })
    }

    node.position({ x: toCanvasX(clampedX), y: toCanvasY(clampedY) })
  } else if (annotation.points && annotation.type === 'polygon') {
    const originalPoints = annotation.points.map(point => [...point])
    const xs = originalPoints.map(point => point[0])
    const ys = originalPoints.map(point => point[1])

    if (Math.abs(currentPos.x) < 0.01 && Math.abs(currentPos.y) < 0.01) {
      node.position({ x: 0, y: 0 })
      return
    }

    const rawMinDeltaX = -Math.min(...xs)
    const rawMaxDeltaX = imageBounds.value.width - Math.max(...xs)
    const rawMinDeltaY = -Math.min(...ys)
    const rawMaxDeltaY = imageBounds.value.height - Math.max(...ys)

    const minAllowedDeltaX = Math.min(rawMinDeltaX, rawMaxDeltaX)
    const maxAllowedDeltaX = Math.max(rawMinDeltaX, rawMaxDeltaX)
    const minAllowedDeltaY = Math.min(rawMinDeltaY, rawMaxDeltaY)
    const maxAllowedDeltaY = Math.max(rawMinDeltaY, rawMaxDeltaY)

    const clampedDeltaX = clampValue(currentPos.x, minAllowedDeltaX, maxAllowedDeltaX)
    const clampedDeltaY = clampValue(currentPos.y, minAllowedDeltaY, maxAllowedDeltaY)

    if (clampedDeltaX !== 0 || clampedDeltaY !== 0) {
      const newPoints = originalPoints.map(point => [
        point[0] + clampedDeltaX,
        point[1] + clampedDeltaY
      ])

      const newXs = newPoints.map(point => point[0])
      const newYs = newPoints.map(point => point[1])
      const minX = Math.min(...newXs)
      const minY = Math.min(...newYs)
      const maxX = Math.max(...newXs)
      const maxY = Math.max(...newYs)

      annotation.bbox = [minX, minY, maxX - minX, maxY - minY]
      store.updateAnnotation(annotation._id, {
        points: newPoints,
        bbox: [minX, minY, maxX - minX, maxY - minY]
      })
    }

    // Resetear la posición del grupo a (0, 0)
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
      break
      
    case 'ne': // Noreste (superior derecha)
      y = clampValue(imagePos.y, 0, origBottom - minSize)
      const newRightNE = clampValue(imagePos.x, origX + minSize, imageBounds.value.width)
      width = Math.max(newRightNE - origX, minSize)
      height = Math.max(origBottom - y, minSize)
      break
      
    case 'sw': // Suroeste (inferior izquierda)
      x = clampValue(imagePos.x, 0, origRight - minSize)
      const newBottomSW = clampValue(imagePos.y, origY + minSize, imageBounds.value.height)
      width = Math.max(origRight - x, minSize)
      height = Math.max(newBottomSW - origY, minSize)
      break
      
    case 'se': // Sureste (inferior derecha)
      const newRightSE = clampValue(imagePos.x, origX + minSize, imageBounds.value.width)
      const newBottomSE = clampValue(imagePos.y, origY + minSize, imageBounds.value.height)
      width = Math.max(newRightSE - origX, minSize)
      height = Math.max(newBottomSE - origY, minSize)
      break
      
    case 'n': // Norte (arriba)
      y = clampValue(imagePos.y, 0, origBottom - minSize)
      height = Math.max(origBottom - y, minSize)
      break
      
    case 's': // Sur (abajo)
      const newBottom = clampValue(imagePos.y, origY + minSize, imageBounds.value.height)
      height = Math.max(newBottom - origY, minSize)
      break
      
    case 'w': // Oeste (izquierda)
      x = clampValue(imagePos.x, 0, origRight - minSize)
      width = Math.max(origRight - x, minSize)
      break
      
    case 'e': // Este (derecha)
      const newRight = clampValue(imagePos.x, origX + minSize, imageBounds.value.width)
      width = Math.max(newRight - origX, minSize)
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

  switch (handle) {
    case 'nw':
      node.position({ x: toCanvasX(x), y: toCanvasY(y) })
      break
    case 'ne':
      node.position({ x: toCanvasX(x) + width, y: toCanvasY(y) })
      break
    case 'sw':
      node.position({ x: toCanvasX(x), y: toCanvasY(y) + height })
      break
    case 'se':
      node.position({ x: toCanvasX(x) + width, y: toCanvasY(y) + height })
      break
    case 'n':
      node.position({ x: toCanvasX(x) + width / 2, y: toCanvasY(y) })
      break
    case 's':
      node.position({ x: toCanvasX(x) + width / 2, y: toCanvasY(y) + height })
      break
    case 'w':
      node.position({ x: toCanvasX(x), y: toCanvasY(y) + height / 2 })
      break
    case 'e':
      node.position({ x: toCanvasX(x) + width, y: toCanvasY(y) + height / 2 })
      break
  }

  if (hasChanged) {
    store.updateAnnotation(annotation._id, { bbox: updatedBbox })
  }
}

function handlePolygonPointDrag(annotation, pointIndex, event) {
  if (props.activeTool !== 'edit') return
  
  const node = event.target
  const canvasPos = {
    x: node.x(),
    y: node.y()
  }
  const clampedX = clampImageX(toImageX(canvasPos.x))
  const clampedY = clampImageY(toImageY(canvasPos.y))

  const newPoints = annotation.points.map((point, idx) =>
    idx === pointIndex ? [clampedX, clampedY] : [...point]
  )

  const currentPoint = annotation.points[pointIndex]
  const hasChanged = currentPoint[0] !== clampedX || currentPoint[1] !== clampedY
  annotation.points = newPoints

  node.position({ x: toCanvasX(clampedX), y: toCanvasY(clampedY) })

  if (hasChanged) {
    const xs = newPoints.map(point => point[0])
    const ys = newPoints.map(point => point[1])
    const minX = Math.min(...xs)
    const minY = Math.min(...ys)
    const maxX = Math.max(...xs)
    const maxY = Math.max(...ys)

    annotation.bbox = [minX, minY, maxX - minX, maxY - minY]
    store.updateAnnotation(annotation._id, {
      points: newPoints,
      bbox: [minX, minY, maxX - minX, maxY - minY]
    })
  }
}
</script>

<style scoped>
.canvas-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 1rem;
  overflow: hidden; /* Ocultar el contenido que se desborde */
  max-width: 100vw;
  max-height: 100vh;
}

.annotation-stage {
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  user-select: none; /* Prevenir selección de texto durante el arrastre */
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  max-width: calc(100vw - 2rem);
  max-height: calc(100vh - 4rem);
  cursor: grab;
}

.annotation-stage:active {
  cursor: grabbing;
}

.debug-info, .debug-canvas-info {
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 4px;
  padding: 1rem;
  margin: 0.5rem;
  font-family: monospace;
  font-size: 0.9rem;
}

.debug-info {
  color: #856404;
}

.debug-canvas-info {
  color: #155724;
  background: #d4edda;
  border-color: #c3e6cb;
}
</style>
