<template>
  <div class="project-view">
    <h2>Anotador COCO</h2>
    <ImageUploader @file-selected="onFileSelected" />
    <div v-if="selectedImageUrl" class="canvas-container">
      <AnnotationCanvas :imageUrl="selectedImageUrl" />
      <ExportCOCO />
    </div>
    <div v-else class="empty-state">
      <p>Sube una imagen para comenzar a anotar.</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ImageUploader from '../components/ImageUploader.vue'
import AnnotationCanvas from '../components/AnnotationsCanvas.vue'
import ExportCOCO from '../components/ExportCOCO.vue'

const selectedImageUrl = ref(null)

function onFileSelected({ url }) {
  selectedImageUrl.value = url
}
</script>

<style scoped>
.project-view {
  max-width: 900px;
  margin: 2rem auto;
  background: #fff;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.canvas-container {
  margin-top: 2rem;
}
.empty-state {
  margin-top: 3rem;
  color: #999;
  text-align: center;
}
</style>