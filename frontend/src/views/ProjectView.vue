<template>
  <div class="project-view">
    <h2>Anotador COCO</h2>
    
    <!-- Gestor de categorías -->
    <CategoryManager />
    
    <!-- Galería de imágenes con paginación -->
    <ImageGallery />
  </div>
</template>

<script setup>
import CategoryManager from '../components/CategoryManager.vue'
import ImageGallery from '../components/ImageGallery.vue'
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

.preview-info {
  margin-top: 2rem;
  text-align: center;
  color: #666;
}

.empty-state {
  margin-top: 3rem;
  color: #999;
  text-align: center;
}

/* Vista de anotación en overlay */
.annotation-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  z-index: 1000;
  display: flex;
  flex-direction: column;
}

.annotation-header {
  background: #2c3e50;
  color: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.annotation-header h3 {
  margin: 0;
  font-size: 1.2rem;
}

.annotation-controls {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.mini-category-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: white;
}

.mini-category-selector label {
  font-size: 0.9rem;
  font-weight: 500;
}

.category-select {
  padding: 0.25rem 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: white;
  font-size: 0.9rem;
}

.close-btn {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
}

.close-btn:hover {
  background: #c0392b;
}

.annotation-content {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 2rem;
  overflow: auto;
}
</style>