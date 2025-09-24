import { defineStore } from 'pinia'

// Configuración de la API
const API_BASE_URL = 'http://localhost:5000/api'

export const useAnnotationStore = defineStore('annotation', {
  state: () => ({
    // Datos almacenados localmente para performance
    annotations: [],
    images: [],
    categories: [],
    
    // Estado de la UI
    selectedCategory: null,
    activeTool: 'select',
    currentImage: null,
    loading: false,
    error: null,
    
    // Configuración de herramientas
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
    }
  }),
  
  getters: {
    getCategoryById: (state) => (id) => {
      return state.categories.find(cat => cat._id === id || cat.id === id)
    },
    
    getAnnotationsByCategory: (state) => (categoryId) => {
      return state.annotations.filter(ann => ann.category === categoryId || ann.category_id === categoryId)
    },
    
    getAnnotationsByImageId: (state) => (imageId) => {
      return state.annotations.filter(ann => ann.image_id === imageId)
    },
    
    getCurrentImageAnnotations: (state) => (imageId) => {
      return state.annotations.filter(ann => ann.image_id === imageId)
    },
    
    getToolSettings: (state) => (tool) => {
      return state.toolSettings[tool] || {}
    },
    
    getImageById: (state) => (id) => {
      return state.images.find(img => img._id === id || img.id === id)
    }
  },
  
  actions: {
    // ==================== MANEJO DE ERRORES ====================
    
    setError(error) {
      this.error = error
      console.error('Store Error:', error)
    },
    
    clearError() {
      this.error = null
    },
    
    // ==================== APIS DE IMÁGENES ====================
    
    async uploadImage(imageFile, projectId = 'default') {
      this.loading = true
      this.clearError()
      
      try {
        const formData = new FormData()
        formData.append('image', imageFile)
        formData.append('project_id', projectId)
        
        const response = await fetch(`${API_BASE_URL}/images`, {
          method: 'POST',
          body: formData
        })
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        
        // Añadir imagen al estado local
        this.images.push(data.image)
        
        return data.image
        
      } catch (error) {
        this.setError(`Error al subir imagen: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async loadImages(projectId = 'default') {
      this.loading = true
      this.clearError()
      
      try {
        const response = await fetch(`${API_BASE_URL}/images?project_id=${projectId}`)
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        this.images = data.images
        
        return data.images
        
      } catch (error) {
        this.setError(`Error al cargar imágenes: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async deleteImage(imageId) {
      this.loading = true
      this.clearError()
      
      try {
        const response = await fetch(`${API_BASE_URL}/images/${imageId}`, {
          method: 'DELETE'
        })
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        // Remover imagen del estado local
        this.images = this.images.filter(img => img._id !== imageId)
        
        // Remover anotaciones asociadas del estado local
        this.annotations = this.annotations.filter(ann => ann.image_id !== imageId)
        
        return true
        
      } catch (error) {
        this.setError(`Error al eliminar imagen: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    // ==================== APIS DE ANOTACIONES ====================
    
    async addAnnotation(imageId, annotationData) {
      this.loading = true
      this.clearError()
      
      try {
        const payload = {
          image_id: imageId,
          category: this.selectedCategory,
          ...annotationData
        }
        
        const response = await fetch(`${API_BASE_URL}/annotations`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        })
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        
        // Añadir anotación al estado local
        this.annotations.push(data.annotation)
        
        return data.annotation
        
      } catch (error) {
        this.setError(`Error al crear anotación: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async loadAnnotations(imageId) {
      this.loading = true
      this.clearError()
      
      try {
        const response = await fetch(`${API_BASE_URL}/annotations?image_id=${imageId}`)
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        
        // Reemplazar anotaciones para esta imagen en el estado local
        this.annotations = this.annotations.filter(ann => ann.image_id !== imageId)
        this.annotations.push(...data.annotations)
        
        return data.annotations
        
      } catch (error) {
        this.setError(`Error al cargar anotaciones: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async updateAnnotation(annotationId, updates) {
      this.loading = true
      this.clearError()
      
      try {
        const response = await fetch(`${API_BASE_URL}/annotations/${annotationId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(updates)
        })
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        
        // Actualizar anotación en el estado local
        const index = this.annotations.findIndex(ann => ann._id === annotationId)
        if (index !== -1) {
          this.annotations[index] = data.annotation
        }
        
        return data.annotation
        
      } catch (error) {
        this.setError(`Error al actualizar anotación: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async removeAnnotation(annotationId) {
      this.loading = true
      this.clearError()
      
      try {
        const response = await fetch(`${API_BASE_URL}/annotations/${annotationId}`, {
          method: 'DELETE'
        })
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        // Remover anotación del estado local
        this.annotations = this.annotations.filter(ann => ann._id !== annotationId)
        
        return true
        
      } catch (error) {
        this.setError(`Error al eliminar anotación: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async clearAnnotationsForImage(imageId) {
      this.loading = true
      this.clearError()
      
      try {
        const response = await fetch(`${API_BASE_URL}/annotations/bulk`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ image_id: imageId })
        })
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        // Remover anotaciones del estado local
        this.annotations = this.annotations.filter(ann => ann.image_id !== imageId)
        
        return true
        
      } catch (error) {
        this.setError(`Error al limpiar anotaciones: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    // ==================== APIS DE CATEGORÍAS ====================
    
    async loadCategories(projectId = 'default') {
      this.loading = true
      this.clearError()
      
      try {
        const response = await fetch(`${API_BASE_URL}/categories?project_id=${projectId}`)
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        this.categories = data.categories
        
        // Seleccionar primera categoría si no hay ninguna seleccionada
        if (this.categories.length > 0 && !this.selectedCategory) {
          this.selectedCategory = this.categories[0]._id
        }
        
        return data.categories
        
      } catch (error) {
        this.setError(`Error al cargar categorías: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async addCategory(categoryData, projectId = 'default') {
      this.loading = true
      this.clearError()
      
      try {
        const payload = {
          project_id: projectId,
          ...categoryData
        }
        
        const response = await fetch(`${API_BASE_URL}/categories`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        })
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        
        // Añadir categoría al estado local
        this.categories.push(data.category)
        
        return data.category
        
      } catch (error) {
        this.setError(`Error al crear categoría: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    // ==================== ACCIONES LOCALES ====================
    
    setSelectedCategory(categoryId) {
      this.selectedCategory = categoryId
    },
    
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
    },
    
    // ==================== INICIALIZACIÓN ====================
    
    async initialize(projectId = 'default') {
      try {
        await Promise.all([
          this.loadImages(projectId),
          this.loadCategories(projectId)
        ])
      } catch (error) {
        console.error('Error al inicializar store:', error)
      }
    }
  }
})