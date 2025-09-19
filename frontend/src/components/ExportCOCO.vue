<template>
  <button @click="exportCoco" class="export-btn">Exportar COCO JSON</button>
</template>

<script setup>
import { useAnnotationStore } from '../stores/annotationStore'
const store = useAnnotationStore()

function exportCoco() {
  // Obtener todas las imágenes únicas de las anotaciones
  const imageIds = [...new Set(store.annotations.map(ann => ann.image_id))].filter(id => id)
  
  const images = imageIds.map((imageId, index) => ({
    id: index + 1,
    file_name: `imagen_${imageId}.jpg`,
    width: 800, // Estos valores deberían venir de la imagen real
    height: 600,
    date_captured: new Date().toISOString()
  }))

  // Mapear anotaciones con los nuevos IDs de imagen
  const imageIdMapping = {}
  imageIds.forEach((originalId, index) => {
    imageIdMapping[originalId] = index + 1
  })

  const coco = {
    info: {
      description: "Anotaciones generadas con VISILAB Annotator",
      version: "1.0",
      year: new Date().getFullYear(),
      contributor: "VISILAB Annotator",
      date_created: new Date().toISOString()
    },
    images: images.length > 0 ? images : [
      { 
        id: 1, 
        file_name: "imagen_sin_id.jpg", 
        width: 800, 
        height: 600,
        date_captured: new Date().toISOString()
      }
    ],
    annotations: store.annotations.map((a, i) => ({
      id: i + 1,
      image_id: a.image_id ? imageIdMapping[a.image_id] : 1,
      category_id: a.category_id,
      bbox: a.bbox,
      area: Math.abs(a.bbox[2] * a.bbox[3]),
      iscrowd: 0,
      segmentation: []
    })),
    categories: store.categories.map(cat => ({
      id: cat.id,
      name: cat.name,
      supercategory: "object"
    }))
  }
  
  const blob = new Blob([JSON.stringify(coco, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `anotaciones_${new Date().toISOString().split('T')[0]}.json`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.export-btn {
  background: #27ae60;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}

.export-btn:hover {
  background: #229954;
}
</style>