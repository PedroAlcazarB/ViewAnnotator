<template>
  <button @click="exportCoco">Exportar COCO JSON</button>
</template>

<script setup>
import { useAnnotationStore } from '../stores/annotationStore'
const store = useAnnotationStore()

function exportCoco() {
  const coco = {
    images: [
      { id: 1, file_name: "tu_imagen.jpg", width: 800, height: 600 }
    ],
    annotations: store.annotations.map((a, i) => ({
      id: i + 1,
      image_id: 1,
      category_id: a.category_id,
      bbox: a.bbox,
      area: a.bbox[2] * a.bbox[3],
      iscrowd: 0
    })),
    categories: store.categories
  }
  const blob = new Blob([JSON.stringify(coco, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'annotations.json'
  a.click()
  URL.revokeObjectURL(url)
}
</script>