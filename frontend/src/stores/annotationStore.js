import { defineStore } from 'pinia'

// Configuración de la API
const API_BASE_URL = 'http://localhost:5000/api'

export const useAnnotationStore = defineStore('annotation', {
  state: () => ({
    // Datos almacenados localmente para performance
    annotations: [],
    images: [],
    categories: [],
    
    // Contexto del dataset actual
    currentDataset: null,
    
    // Estado de la UI
    selectedCategory: null,
    activeTool: 'edit',
    currentImage: null,
    loading: false,
    error: null,
    selectedAnnotation: null,
    
    // Configuración de herramientas
    toolSettings: {
      edit: {
        tolerance: 5,
        showHandles: true,
        snapToGrid: false
      },
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
    
    async uploadImage(imageFile, datasetId = null) {
      this.loading = true
      this.clearError()
      
      try {
        const formData = new FormData()
        formData.append('image', imageFile)
        if (datasetId || this.currentDataset?._id) {
          formData.append('dataset_id', datasetId || this.currentDataset._id)
        }
        
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
    
    async loadImages(datasetId = null) {
      this.loading = true
      this.clearError()
      
      try {
        const targetDatasetId = datasetId || this.currentDataset?._id
        const url = targetDatasetId ? 
          `${API_BASE_URL}/images?dataset_id=${targetDatasetId}` : 
          `${API_BASE_URL}/images`
        const response = await fetch(url)
        
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
    
    async loadCategories(datasetId = null) {
      this.loading = true
      this.clearError()
      
      try {
        const targetDatasetId = datasetId || this.currentDataset?._id
        const url = targetDatasetId ? 
          `${API_BASE_URL}/categories?dataset_id=${targetDatasetId}` : 
          `${API_BASE_URL}/categories`
        const response = await fetch(url)
        
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
    
    async addCategory(categoryData, datasetId = null) {
      this.loading = true
      this.clearError()
      
      try {
        const payload = {
          dataset_id: datasetId || this.currentDataset?._id,
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
      // Limpiar selección cuando cambiamos de herramienta
      if (tool !== 'edit') {
        this.selectedAnnotation = null
      }
    },
    
    updateToolSettings(tool, settings) {
      if (this.toolSettings[tool]) {
        this.toolSettings[tool] = { ...this.toolSettings[tool], ...settings }
      }
    },
    
    // ==================== MÉTODOS DE EDICIÓN ====================
    
    selectAnnotation(annotation) {
      this.selectedAnnotation = annotation
    },
    
    clearSelection() {
      this.selectedAnnotation = null
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
        
        // Actualizar en el estado local
        const index = this.annotations.findIndex(ann => ann._id === annotationId)
        if (index !== -1) {
          this.annotations[index] = { ...this.annotations[index], ...updates }
        }
        
        return data.annotation
        
      } catch (error) {
        this.setError(`Error al actualizar anotación: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    moveAnnotation(annotationId, deltaX, deltaY) {
      const annotation = this.annotations.find(ann => ann._id === annotationId)
      if (!annotation) return
      
      if (annotation.type === 'bbox' || !annotation.type) {
        // Mover rectángulo
        const newBbox = [
          annotation.bbox[0] + deltaX,
          annotation.bbox[1] + deltaY,
          annotation.bbox[2],
          annotation.bbox[3]
        ]
        this.updateAnnotation(annotationId, { bbox: newBbox })
      } else if (annotation.type === 'polygon' && annotation.points) {
        // Mover todos los puntos del polígono
        const newPoints = annotation.points.map(point => [
          point[0] + deltaX,
          point[1] + deltaY
        ])
        this.updateAnnotation(annotationId, { points: newPoints })
      } else if (annotation.type === 'keypoint') {
        // Mover punto clave
        const newBbox = [
          annotation.bbox[0] + deltaX,
          annotation.bbox[1] + deltaY,
          annotation.bbox[2],
          annotation.bbox[3]
        ]
        this.updateAnnotation(annotationId, { bbox: newBbox })
      }
    },
    
    resizeAnnotation(annotationId, newWidth, newHeight) {
      const annotation = this.annotations.find(ann => ann._id === annotationId)
      if (!annotation) return
      
      if (annotation.type === 'bbox' || !annotation.type) {
        const newBbox = [
          annotation.bbox[0],
          annotation.bbox[1],
          newWidth,
          newHeight
        ]
        this.updateAnnotation(annotationId, { bbox: newBbox })
      } else if (annotation.type === 'keypoint') {
        // Para puntos clave, redimensionar el radio
        const newRadius = Math.max(newWidth, newHeight) / 2
        const newBbox = [
          annotation.bbox[0],
          annotation.bbox[1],
          newRadius * 2,
          newRadius * 2
        ]
        this.updateAnnotation(annotationId, { bbox: newBbox })
      }
    },
    
    setCurrentImage(image) {
      this.currentImage = image
    },
    
    setCurrentDataset(dataset) {
      this.currentDataset = dataset
      // Limpiar datos cuando cambiamos de dataset
      this.images = []
      this.annotations = []
      this.categories = []
      this.currentImage = null
      this.selectedCategory = null
    },
    
    clearDatasetContext() {
      this.currentDataset = null
      this.images = []
      this.annotations = []
      this.categories = []
      this.currentImage = null
      this.selectedCategory = null
    },
    
    // ==================== INICIALIZACIÓN ====================
    
    async initialize(datasetId = null) {
      try {
        await Promise.all([
          this.loadImages(datasetId),
          this.loadCategories(datasetId)
        ])
      } catch (error) {
        console.error('Error al inicializar store:', error)
      }
    }
  }
})