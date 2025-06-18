import { defineStore } from 'pinia'

export const useAnnotationStore = defineStore('annotation', {
  state: () => ({
    annotations: [],
    selectedCategory: 1,  // Puedes tener una lista de categorías
    categories: [{ id: 1, name: 'object' }]
  }),
  actions: {
    addAnnotation(ann) {
      this.annotations.push(ann)
    },
    clearAnnotations() {
      this.annotations = []
    }
  }
})