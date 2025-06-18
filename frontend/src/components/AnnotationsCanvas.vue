<template>
  <div>
    <v-stage
      :config="stageConfig"
      v-if="image"
      @mousedown="startDraw"
      @mousemove="draw"
      @mouseup="endDraw"
    >
      <v-layer>
        <v-image :config="imageConfig" />
        <!-- Rectángulos existentes -->
        <v-rect
          v-for="(ann, i) in annotations"
          :key="i"
          :config="{
            x: ann.bbox[0],
            y: ann.bbox[1],
            width: ann.bbox[2],
            height: ann.bbox[3],
            stroke: 'red'
          }"
        />
        <!-- Preview de rectángulo nuevo -->
        <v-rect v-if="drawing" :config="drawingRect" />
      </v-layer>
    </v-stage>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { useAnnotationStore } from '../stores/annotationStore'
const store = useAnnotationStore()

const stageWidth = 800, stageHeight = 600
const stageConfig = { width: stageWidth, height: stageHeight }

const props = defineProps({
  imageUrl: String
})

const image = ref(null)
const imageConfig = reactive({ image: null, x: 0, y: 0, width: stageWidth, height: stageHeight })
const drawing = ref(false)
const startPt = ref({ x: 0, y: 0 })
const drawingRect = reactive({ x: 0, y: 0, width: 0, height: 0, stroke: 'blue' })

const annotations = computed(() => store.annotations)

watch(() => props.imageUrl, (url) => {
  if (!url) return
  const img = new window.Image()
  img.onload = () => {
    imageConfig.image = img
    image.value = img
  }
  img.src = url
})

function startDraw(e) {
  drawing.value = true
  const pos = e.target.getStage().getPointerPosition()
  startPt.value = pos
  Object.assign(drawingRect, { x: pos.x, y: pos.y, width: 0, height: 0 })
}
function draw(e) {
  if (!drawing.value) return
  const pos = e.target.getStage().getPointerPosition()
  drawingRect.width = pos.x - startPt.value.x
  drawingRect.height = pos.y - startPt.value.y
}
function endDraw() {
  if (!drawing.value) return
  store.addAnnotation({
    bbox: [drawingRect.x, drawingRect.y, drawingRect.width, drawingRect.height],
    category_id: store.selectedCategory,
    id: Date.now()
  })
  drawing.value = false
  Object.assign(drawingRect, { x: 0, y: 0, width: 0, height: 0 })
}
</script>