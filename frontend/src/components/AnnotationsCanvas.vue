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
              stroke: getCategoryColor(ann.category || ann.category_id),
              strokeWidth: 2,
              listening: true
            }"
            @click="selectAnnotation(ann)"
          />
          
          <!-- Polígonos -->
          <v-line
            v-if="ann.type === 'polygon' && ann.points"
            :config="{
              points: ann.points.flat(),
              stroke: getCategoryColor(ann.category || ann.category_id),
              strokeWidth: 2,
              closed: true,
              listening: true
            }"
            @click="selectAnnotation(ann)"
          />
          
          <!-- Trazos de pincel -->
          <v-line
            v-if="ann.type === 'brush' && ann.points"
            :config="{
              points: ann.points,
              stroke: getCategoryColor(ann.category || ann.category_id),
              strokeWidth: props.toolSettings?.brush?.radius / 2 || 8,
              lineCap: 'round',
              lineJoin: 'round',
              listening: true
            }"
            @click="selectAnnotation(ann)"
          />
          
          <!-- Puntos clave -->
          <v-circle
            v-if="ann.type === 'keypoint'"
            :config="{
              x: ann.center?.x || (ann.bbox[0] + ann.bbox[2]/2),
              y: ann.center?.y || (ann.bbox[1] + ann.bbox[3]/2),
              radius: ann.bbox[2]/2,
              stroke: getCategoryColor(ann.category || ann.category_id),
              fill: getCategoryColor(ann.category || ann.category_id),
              strokeWidth: 2,
              listening: true,
              opacity: 0.8
            }"
            @click="selectAnnotation(ann)"
          />
        </template>

        <!-- Forma en curso (preview) -->
        <v-rect v-if="drawing && (props.activeTool === 'bbox')" :config="drawingRect" />
        
        <!-- Polígono en construcción -->
        <v-line 
          v-if="currentPath.length > 1 && props.activeTool === 'polygon'"
          :config="{
            points: currentPath.flat(),
            stroke: props.toolSettings?.polygon?.strokeColor || 'blue',
            strokeWidth: 2,
            dash: [5, 5],
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
            radius: 3,
            fill: 'blue',
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
    case 'select': return 'default'
    case 'bbox': return 'crosshair'
    case 'polygon': return 'crosshair'
    case 'brush': return 'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'24\' height=\'24\' viewBox=\'0 0 24 24\'%3E%3Ccircle cx=\'12\' cy=\'12\' r=\'3\' fill=\'%23000\'/%3E%3C/svg%3E") 12 12, auto'
    case 'eraser': return 'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'24\' height=\'24\' viewBox=\'0 0 24 24\'%3E%3Ccircle cx=\'12\' cy=\'12\' r=\'8\' fill=\'none\' stroke=\'%23f00\' stroke-width=\'2\'/%3E%3C/svg%3E") 12 12, auto'
    case 'keypoints': return 'crosshair'
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
const brushPath = ref([]) // Para pincel
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
  stroke: 'blue',
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

// Eventos de teclado para herramientas
function handleKeyDown(e) {
  if (e.key === 'Escape') {
    // Cancelar polígono en construcción
    if (props.activeTool === 'polygon' && currentPath.value.length > 0) {
      currentPath.value = []
    }
  } else if (e.key === 'Enter') {
    // Completar polígono con Enter
    if (props.activeTool === 'polygon' && currentPath.value.length >= 3) {
      completePolygon()
    }
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
      
      // Crear canvas oculto para obtener datos de imagen para varita mágica
      createImageData(img, scaledWidth, scaledHeight)
      
      console.log('Canvas ajustado a:', stageWidth.value, 'x', stageHeight.value)
      console.log('Imagen configurada:', imageConfig)
    }
    img.onerror = (error) => {
      console.error('Error cargando imagen:', error)
    }
    img.src = url
  },
  { immediate: true }
)

// Función para crear datos de imagen para la varita mágica
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
    console.log('Datos de imagen creados para varita mágica')
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
    case 'select':
      // No hacer nada, solo seleccionar
      break
      
    case 'bbox':
      drawing.value = true
      Object.assign(drawingRect, { 
        x: pos.x, 
        y: pos.y, 
        width: 0, 
        height: 0,
        stroke: props.toolSettings?.bbox?.strokeColor || 'blue'
      })
      break
      
    case 'polygon':
      handlePolygonClick(pos)
      break
      
    case 'brush':
      drawing.value = true
      brushPath.value = [pos.x, pos.y]
      break
      
    case 'eraser':
      drawing.value = true
      eraseAtPosition(pos)
      break
      
    case 'keypoints':
      createKeypoint(pos)
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
      
    case 'brush':
      // Agregar punto al path del pincel
      brushPath.value.push(pos.x, pos.y)
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
      
    case 'brush':
      completeBrush()
      break
      
    case 'eraser':
      // El borrado ya se hizo durante el arrastre
      break
  }
  
  drawing.value = false
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
    // Cerrar polígono
    completePolygon()
  } else {
    // Agregar nuevo punto
    const lastPoint = currentPath.value[currentPath.value.length - 1]
    const lastDistance = Math.sqrt(
      Math.pow(pos.x - lastPoint[0], 2) + Math.pow(pos.y - lastPoint[1], 2)
    )
    
    if (lastDistance >= minDistance.value) {
      currentPath.value.push([pos.x, pos.y])
    }
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
    } catch (error) {
      console.error('Error al crear anotación polígono:', error)
    }
  }
  
  // Limpiar path
  currentPath.value = []
}

async function completeBrush() {
  if (brushPath.value.length >= 4) {
    // Calcular bounding box del trazo
    const xs = brushPath.value.filter((_, i) => i % 2 === 0)
    const ys = brushPath.value.filter((_, i) => i % 2 === 1)
    const minX = Math.min(...xs)
    const minY = Math.min(...ys)
    const maxX = Math.max(...xs)
    const maxY = Math.max(...ys)
    
    try {
      await store.addAnnotation(props.imageId, {
        bbox: [minX, minY, maxX - minX, maxY - minY],
        type: 'brush',
        points: brushPath.value
      })
    } catch (error) {
      console.error('Error al crear anotación brush:', error)
    }
  }
  
  brushPath.value = []
}

async function eraseAtPosition(pos) {
  // Encontrar anotaciones que intersectan con el área del borrador
  const annotations = store.getAnnotationsByImageId(props.imageId)
  
  for (const ann of annotations) {
    const annCenterX = ann.bbox[0] + ann.bbox[2] / 2
    const annCenterY = ann.bbox[1] + ann.bbox[3] / 2
    
    const distance = Math.sqrt(
      Math.pow(pos.x - annCenterX, 2) + Math.pow(pos.y - annCenterY, 2)
    )
    
    if (distance < eraserRadius.value) {
      try {
        await store.removeAnnotation(ann._id)
      } catch (error) {
        console.error('Error al eliminar anotación:', error)
      }
    }
  }
}

async function createKeypoint(pos) {
  const size = props.toolSettings.size || 6
  try {
    await store.addAnnotation(props.imageId, {
      bbox: [pos.x - size/2, pos.y - size/2, size, size],
      type: 'keypoint',
      center: { x: pos.x, y: pos.y }
    })
  } catch (error) {
    console.error('Error al crear anotación keypoint:', error)
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
