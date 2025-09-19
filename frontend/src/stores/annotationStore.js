import { defineStore } from 'pinia'

export const useAnnotationStore = defineStore('annotation', {
  state: () => ({
    annotations: [],
    selectedCategory: 1,
    categories: [
      { id: 1, name: 'Objeto', color: '#e74c3c' },
      { id: 2, name: 'Persona', color: '#3498db' },
      { id: 3, name: 'Vehículo', color: '#f39c12' }
    ],
    nextCategoryId: 4,
    // Herramientas de anotación
    activeTool: 'select',
    toolSettings: {
      bbox: {
        autoColor: true,
        strokeColor: '#ff0000'
      },
      polygon: {
        minDistance: 2,
        completeDistance: 15,
        guidance: true
      },
      brush: {
        radius: 15,
        color: '#ff0000'
      },
      eraser: {
        radius: 20
      },
      keypoints: {
        size: 6,
        color: '#ff0000'
      }
    },
    // Estado del canvas y imagen actual
    currentImage: null
  }),
  
  getters: {
    getCategoryById: (state) => (id) => {
      return state.categories.find(cat => cat.id === id)
    },
    
    getAnnotationsByCategory: (state) => (categoryId) => {
      return state.annotations.filter(ann => ann.category_id === categoryId)
    },
    
    getAnnotationsByImageId: (state) => (imageId) => {
      return state.annotations.filter(ann => ann.image_id === imageId)
    },
    
    getCurrentImageAnnotations: (state) => (imageId) => {
      return state.annotations.filter(ann => ann.image_id === imageId)
    },
    
    getToolSettings: (state) => (tool) => {
      return state.toolSettings[tool] || {}
    }
  },
  
  actions: {
    addAnnotation(ann) {
      this.annotations.push({
        ...ann,
        category_id: this.selectedCategory,
        id: Date.now() + Math.random(),
        image_id: ann.image_id // Importante: incluir el ID de la imagen
      })
    },
    
    clearAnnotations() {
      this.annotations = []
    },
    
    clearAnnotationsForImage(imageId) {
      this.annotations = this.annotations.filter(ann => ann.image_id !== imageId)
    },
    
    setSelectedCategory(categoryId) {
      this.selectedCategory = categoryId
    },
    
    addCategory(categoryData) {
      const newCategory = {
        id: this.nextCategoryId++,
        name: categoryData.name,
        color: categoryData.color
      }
      this.categories.push(newCategory)
      return newCategory
    },
    
    updateCategory(updatedCategory) {
      const index = this.categories.findIndex(cat => cat.id === updatedCategory.id)
      if (index !== -1) {
        this.categories[index] = { ...updatedCategory }
      }
    },
    
    deleteCategory(categoryId) {
      // No permitir eliminar la categoría por defecto
      if (categoryId === 1) return
      
      // Eliminar la categoría
      this.categories = this.categories.filter(cat => cat.id !== categoryId)
      
      // Si la categoría eliminada era la seleccionada, seleccionar la primera disponible
      if (this.selectedCategory === categoryId) {
        this.selectedCategory = this.categories[0]?.id || 1
      }
      
      // Opcional: reasignar anotaciones huérfanas a la categoría por defecto
      this.annotations.forEach(ann => {
        if (ann.category_id === categoryId) {
          ann.category_id = 1 // Reasignar a "Objeto"
        }
      })
    },
    
    removeAnnotation(annotationId) {
      this.annotations = this.annotations.filter(ann => ann.id !== annotationId)
    },
    
    removeAnnotationsByImageId(imageId) {
      this.annotations = this.annotations.filter(ann => ann.image_id !== imageId)
    },
    
    // Acciones para herramientas
    setActiveTool(tool) {
      this.activeTool = tool
    },
    
    updateToolSettings(tool, settings) {
      if (this.toolSettings[tool]) {
        this.toolSettings[tool] = { ...this.toolSettings[tool], ...settings }
      }
    },
    
    setCurrentImage(image) {
      this.currentImage = image
    }
  }
})