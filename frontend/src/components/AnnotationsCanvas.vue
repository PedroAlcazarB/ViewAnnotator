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
      class="annotation-stage"
      :style="{ cursor: canvasCursor }"
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
              x: ann.bbox[0],
              y: ann.bbox[1],
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
                x: ann.bbox[0],
                y: ann.bbox[1],
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true,
                dragBoundFunc: (pos) => pos
              }"
              @dragmove="handleResizeDrag(ann, $event, 'nw')"
            />
            <v-circle
              :config="{
                x: ann.bbox[0] + ann.bbox[2],
                y: ann.bbox[1],
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true,
                dragBoundFunc: (pos) => pos
              }"
              @dragmove="handleResizeDrag(ann, $event, 'ne')"
            />
            <v-circle
              :config="{
                x: ann.bbox[0],
                y: ann.bbox[1] + ann.bbox[3],
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true,
                dragBoundFunc: (pos) => pos
              }"
              @dragmove="handleResizeDrag(ann, $event, 'sw')"
            />
            <v-circle
              :config="{
                x: ann.bbox[0] + ann.bbox[2],
                y: ann.bbox[1] + ann.bbox[3],
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true,
                dragBoundFunc: (pos) => pos
              }"
              @dragmove="handleResizeDrag(ann, $event, 'se')"
            />
            <!-- Bordes -->
            <v-circle
              :config="{
                x: ann.bbox[0] + ann.bbox[2] / 2,
                y: ann.bbox[1],
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true,
                dragBoundFunc: (pos) => pos
              }"
              @dragmove="handleResizeDrag(ann, $event, 'n')"
            />
            <v-circle
              :config="{
                x: ann.bbox[0] + ann.bbox[2] / 2,
                y: ann.bbox[1] + ann.bbox[3],
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true,
                dragBoundFunc: (pos) => pos
              }"
              @dragmove="handleResizeDrag(ann, $event, 's')"
            />
            <v-circle
              :config="{
                x: ann.bbox[0],
                y: ann.bbox[1] + ann.bbox[3] / 2,
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true,
                dragBoundFunc: (pos) => pos
              }"
              @dragmove="handleResizeDrag(ann, $event, 'w')"
            />
            <v-circle
              :config="{
                x: ann.bbox[0] + ann.bbox[2],
                y: ann.bbox[1] + ann.bbox[3] / 2,
                radius: 6,
                fill: '#ffffff',
                stroke: getCategoryColor(ann.category || ann.category_id),
                strokeWidth: 2,
                draggable: true,
                dragBoundFunc: (pos) => pos
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
                points: ann.points.flat(),
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
                  x: point[0],
                  y: point[1],
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
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted, onUnmounted } from 'vue'
import { useAnnotationStore } from '../stores/annotationStore'

const store = useAnnotationStore()

// Canvas responsive que se adapta a la imagen
const stageWidth = ref(800)
const stageHeight = ref(600)
const stageConfig = computed(() => ({ 
  width: stageWidth.value, 
  height: stageHeight.value
}))

// Cursor según herramienta activa
const canvasCursor = computed(() => {
  switch(props.activeTool) {
    case 'edit': return 'default'
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
  // Filtrar anotaciones solo para la imagen actual
  if (props.imageId) {
    return store.getAnnotationsByImageId(props.imageId)
  }
  return store.annotations
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
  }
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

      // Ajustar el canvas al tamaño de la imagen escalada
      stageWidth.value = scaledWidth
      stageHeight.value = scaledHeight

      // Configurar la imagen para que ocupe todo el canvas
      Object.assign(imageConfig, {
        image: img,
        width: scaledWidth,
        height: scaledHeight,
        x: 0,
        y: 0
      })

      image.value = img
      
      // Crear canvas oculto para obtener datos de imagen
      createImageData(img, scaledWidth, scaledHeight)
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
  
  const pos = e.target.getStage().getPointerPosition()
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
  if (!drawing.value) return
  
  const pos = e.target.getStage().getPointerPosition()
  
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
      await store.addAnnotation(props.imageId, {
        bbox: [
          Math.min(drawingRect.x, drawingRect.x + drawingRect.width),
          Math.min(drawingRect.y, drawingRect.y + drawingRect.height),
          Math.abs(drawingRect.width),
          Math.abs(drawingRect.height)
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
    // Calcular bounding box del polígono
    const xs = currentPath.value.map(p => p[0])
    const ys = currentPath.value.map(p => p[1])
    const minX = Math.min(...xs)
    const minY = Math.min(...ys)
    const maxX = Math.max(...xs)
    const maxY = Math.max(...ys)
    
    try {
      await store.addAnnotation(props.imageId, {
        bbox: [minX, minY, maxX - minX, maxY - minY],
        type: 'polygon',
        points: currentPath.value
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
        const distance = Math.sqrt(
          Math.pow(pos.x - point[0], 2) + Math.pow(pos.y - point[1], 2)
        )
        if (distance < eraserRadius.value) {
          shouldErase = true
          break
        }
      }
    } else if (ann.bbox) {
      // Para rectángulos, verificar intersección con el círculo del borrador
      const rectLeft = ann.bbox[0]
      const rectTop = ann.bbox[1]
      const rectRight = ann.bbox[0] + ann.bbox[2]
      const rectBottom = ann.bbox[1] + ann.bbox[3]
      
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
  
  const node = event.target
  const newPos = {
    x: node.x(),
    y: node.y()
  }
  
  if (annotation.bbox) {
    // Para rectángulos - actualizar bbox temporalmente
    annotation.bbox[0] = newPos.x
    annotation.bbox[1] = newPos.y
  }
  // Para polígonos agrupados, no necesitamos hacer nada aquí
  // El v-group maneja automáticamente el movimiento visual
}

function handleAnnotationDragEnd(annotation, event) {
  if (props.activeTool !== 'edit') return
  
  const node = event.target
  const currentPos = { x: node.x(), y: node.y() }
  
  if (annotation.bbox) {
    // Para rectángulos - calcular el delta y aplicar
    const deltaX = currentPos.x - annotation.bbox[0]
    const deltaY = currentPos.y - annotation.bbox[1]
    
    store.moveAnnotation(annotation._id, deltaX, deltaY)
    node.position({ x: annotation.bbox[0], y: annotation.bbox[1] })
  } else if (annotation.points && annotation.type === 'polygon') {
    // Para polígonos - el grupo se ha movido, usar las coordenadas del grupo como delta
    const deltaX = currentPos.x
    const deltaY = currentPos.y
    
    // Actualizar las coordenadas del polígono en el store
    store.moveAnnotation(annotation._id, deltaX, deltaY)
    
    // Resetear la posición del grupo a (0, 0)
    node.position({ x: 0, y: 0 })
  }
}

function handleResizeDrag(annotation, event, handle) {
  if (props.activeTool !== 'edit') return
  
  const node = event.target
  const newPos = {
    x: node.x(),
    y: node.y()
  }
  
  const minSize = 10
  let x = annotation.bbox[0]
  let y = annotation.bbox[1]
  let width = annotation.bbox[2]
  let height = annotation.bbox[3]
  
  // Calcular nuevas dimensiones según el manejador
  switch (handle) {
    case 'nw': // Noroeste (superior izquierda)
      const deltaX_nw = newPos.x - x
      const deltaY_nw = newPos.y - y
      x = newPos.x
      y = newPos.y
      width = Math.max(width - deltaX_nw, minSize)
      height = Math.max(height - deltaY_nw, minSize)
      break
      
    case 'ne': // Noreste (superior derecha)
      const deltaY_ne = newPos.y - y
      y = newPos.y
      width = Math.max(newPos.x - x, minSize)
      height = Math.max(height - deltaY_ne, minSize)
      break
      
    case 'sw': // Suroeste (inferior izquierda)
      const deltaX_sw = newPos.x - x
      x = newPos.x
      width = Math.max(width - deltaX_sw, minSize)
      height = Math.max(newPos.y - y, minSize)
      break
      
    case 'se': // Sureste (inferior derecha)
      width = Math.max(newPos.x - x, minSize)
      height = Math.max(newPos.y - y, minSize)
      break
      
    case 'n': // Norte (arriba)
      const deltaY_n = newPos.y - y
      y = newPos.y
      height = Math.max(height - deltaY_n, minSize)
      break
      
    case 's': // Sur (abajo)
      height = Math.max(newPos.y - y, minSize)
      break
      
    case 'w': // Oeste (izquierda)
      const deltaX_w = newPos.x - x
      x = newPos.x
      width = Math.max(width - deltaX_w, minSize)
      break
      
    case 'e': // Este (derecha)
      width = Math.max(newPos.x - x, minSize)
      break
  }
  
  // Actualizar la anotación con las nuevas dimensiones
  const updatedBbox = [x, y, width, height]
  store.updateAnnotation(annotation._id, { bbox: updatedBbox })
}

function handlePolygonPointDrag(annotation, pointIndex, event) {
  if (props.activeTool !== 'edit') return
  
  const node = event.target
  const newPos = {
    x: node.x(),
    y: node.y()
  }
  
  // Actualizar el punto específico del polígono
  const newPoints = [...annotation.points]
  newPoints[pointIndex] = [newPos.x, newPos.y]
  
  store.updateAnnotation(annotation._id, { points: newPoints })
}
</script>

<style scoped>
.canvas-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 1rem;
}

.annotation-stage {
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
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
