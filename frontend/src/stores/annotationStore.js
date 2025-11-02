import { defineStore } from 'pinia'

// Configuración de la API
const API_BASE_URL = 'http://localhost:5000/api'

export const useAnnotationStore = defineStore('annotation', {
  state: () => ({
    // Datos almacenados localmente para performance
    annotations: [],
    images: [],
    categories: [],
    categoryVisibility: {}, // Visibilidad por dataset
    annotationVisibility: {}, // Visibilidad de anotaciones individuales
    
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
      eraser: {
        radius: 20
      }
    },

    // Historial de acciones por imagen (máximo 3 pasos)
    undoStacks: {}
  }),
  
  getters: {
    getCategoryById: (state) => (id) => {
      return state.categories.find(cat => cat.id === id)
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
    },

    // Getter para conteo contextual de anotaciones por categoría
    getCategoryAnnotationCount: (state) => (categoryId) => {
      return state.annotations.filter(ann => 
        ann.category_id === categoryId || ann.category === categoryId
      ).length
    },

    // Getter para verificar si una categoría está oculta
    isCategoryHidden: (state) => (categoryId) => {
      if (!state.currentDataset) return false
      return state.categoryVisibility[categoryId] || false
    },

    // Getter para obtener anotaciones de una categoría específica
    getAnnotationsByCategory: (state) => (categoryId) => {
      return state.annotations.filter(ann => 
        ann.category_id === categoryId || ann.category === categoryId
      )
    },

    // Getter para verificar si una anotación está oculta
    isAnnotationHidden: (state) => (annotationId) => {
      return state.annotationVisibility[annotationId] || false
    },

    // Getter para obtener anotaciones de la imagen actual agrupadas por categoría
    getCurrentImageAnnotationsByCategory: (state) => {
      if (!state.currentImage) return {}
      
      const imageAnnotations = state.annotations.filter(ann => 
        ann.image_id === state.currentImage.id || ann.image_id === state.currentImage._id
      )
      
      // Agrupar por categoría
      const groupedAnnotations = {}
      imageAnnotations.forEach(annotation => {
        const categoryId = annotation.category_id || annotation.category
        if (!groupedAnnotations[categoryId]) {
          groupedAnnotations[categoryId] = []
        }
        groupedAnnotations[categoryId].push(annotation)
      })
      
      return groupedAnnotations
    },

    // Getter para obtener anotaciones visibles de la imagen actual
    getVisibleCurrentImageAnnotations: (state) => {
      if (!state.currentImage) return []
      
      return state.annotations.filter(ann => {
        // Filtrar por imagen actual
        const isCurrentImage = ann.image_id === state.currentImage.id || ann.image_id === state.currentImage._id
        if (!isCurrentImage) return false
        
        // Filtrar por visibilidad de categoría
        const categoryId = ann.category_id || ann.category
        const isCategoryHidden = state.categoryVisibility[categoryId] || false
        if (isCategoryHidden) return false
        
        // Filtrar por visibilidad de anotación individual
        const isAnnotationHidden = state.annotationVisibility[ann.id || ann._id] || false
        if (isAnnotationHidden) return false
        
        return true
      })
    },

    hasUndoForImage: (state) => (imageId) => {
      if (!imageId) return false
      const stack = state.undoStacks?.[imageId]
      return Array.isArray(stack) && stack.length > 0
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

    // ==================== HISTORIAL DE ACCIONES ====================
    ensureUndoStack(imageId) {
      if (!imageId) return
      if (!this.undoStacks[imageId]) {
        this.undoStacks[imageId] = []
      }
    },

    cloneAnnotations(annotations) {
      return annotations.map(ann => JSON.parse(JSON.stringify(ann)))
    },

    pushUndoEntry(imageId, entry) {
      if (!imageId || !entry) return
      if (!entry.annotations || entry.annotations.length === 0) return
      this.ensureUndoStack(imageId)
      const stack = this.undoStacks[imageId]
      stack.push({ ...entry, annotations: this.cloneAnnotations(entry.annotations) })
      if (stack.length > 3) {
        stack.shift()
      }
    },

    clearUndoStack(imageId) {
      if (!imageId) return
      if (this.undoStacks[imageId]) {
        this.undoStacks[imageId] = []
      }
    },

    async undoLastAction(imageId) {
      if (!imageId) return false
      const stack = this.undoStacks[imageId]
      if (!stack || stack.length === 0) {
        return false
      }

      const lastEntry = stack.pop()

      try {
        if (lastEntry.type === 'add') {
          for (const annotation of lastEntry.annotations) {
            const annotationId = annotation._id || annotation.id
            if (!annotationId) continue
            const response = await fetch(`${API_BASE_URL}/annotations/${annotationId}`, {
              method: 'DELETE'
            })
            if (!response.ok) {
              throw new Error(`Error ${response.status}: ${response.statusText}`)
            }
            this.annotations = this.annotations.filter(ann => (ann._id || ann.id) !== annotationId)
          }
        } else if (lastEntry.type === 'clear') {
          // Limpiar anotaciones actuales sin registrar nuevo undo
          await this.clearAnnotationsForImage(imageId, { skipUndo: true })
          for (const annotation of lastEntry.annotations) {
            const { _id, id, image_id, created_at, updated_at, ...rest } = annotation
            await this.addAnnotation(imageId, rest, { skipUndo: true })
          }
        }
        return true
      } catch (error) {
        // Reinsertar la entrada para permitir reintento
        stack.push(lastEntry)
        this.setError(`Error al deshacer acción: ${error.message}`)
        return false
      }
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
    
    async addAnnotation(imageId, annotationData, options = {}) {
      this.loading = true
      this.clearError()
      const skipUndo = options.skipUndo || false
      
      try {
        const payload = {
          image_id: imageId,
          ...annotationData
        }

        if (!payload.category && !payload.category_id && this.selectedCategory) {
          payload.category = this.selectedCategory
          payload.category_id = this.selectedCategory
        } else {
          if (payload.category && !payload.category_id) {
            payload.category_id = payload.category
          }
          if (payload.category_id && !payload.category) {
            payload.category = payload.category_id
          }
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

        if (!skipUndo) {
          this.pushUndoEntry(imageId, {
            type: 'add',
            annotations: [data.annotation]
          })
        }
        
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

    async loadAllAnnotations() {
      this.loading = true
      this.clearError()
      
      try {
        const response = await fetch(`${API_BASE_URL}/annotations`)
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        
        // Reemplazar todas las anotaciones en el estado local
        this.annotations = data.annotations
        
        return data.annotations
        
      } catch (error) {
        this.setError(`Error al cargar todas las anotaciones: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },

    async loadAnnotationsByDataset(datasetId) {
      this.loading = true
      this.clearError()
      
      try {
        const targetDatasetId = datasetId || this.currentDataset?._id
        
        if (!targetDatasetId) {
          throw new Error('No se proporcionó dataset_id y no hay dataset actual')
        }
        
        const response = await fetch(`${API_BASE_URL}/annotations?dataset_id=${targetDatasetId}`)
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        
        // Reemplazar anotaciones del dataset en el estado local
        this.annotations = data.annotations
        
        return data.annotations
        
      } catch (error) {
        this.setError(`Error al cargar anotaciones del dataset: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },

    // Método para obtener conteo global de anotaciones de una categoría (todos los datasets)
    async getCategoryGlobalAnnotationCount(categoryId) {
      try {
        const response = await fetch(`${API_BASE_URL}/annotations`)
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        
        // Contar anotaciones de esta categoría en todas las anotaciones
        return data.annotations.filter(ann => 
          ann.category_id === categoryId || ann.category === categoryId
        ).length
        
      } catch (error) {
        console.error('Error al obtener conteo global:', error)
        return 0
      }
    },

    // Método para verificar si una categoría puede ser eliminada en el contexto actual
    async canDeleteCategory(categoryId) {
      try {
        if (this.currentDataset) {
          // En contexto de dataset: verificar solo anotaciones del dataset actual
          // Las anotaciones ya están cargadas del dataset actual
          return this.getCategoryAnnotationCount(categoryId) === 0
        } else {
          // En contexto global: verificar anotaciones en todos los datasets
          const globalCount = await this.getCategoryGlobalAnnotationCount(categoryId)
          return globalCount === 0
        }
      } catch (error) {
        console.error('Error al verificar si se puede eliminar categoría:', error)
        return false
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
    
    async clearAnnotationsForImage(imageId, options = {}) {
      this.loading = true
      this.clearError()
      const skipUndo = options.skipUndo || false
      const existingAnnotations = this.annotations.filter(ann => ann.image_id === imageId)
      
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

        if (!skipUndo && existingAnnotations.length > 0) {
          this.pushUndoEntry(imageId, {
            type: 'clear',
            annotations: existingAnnotations
          })
        }
        
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
        
        // Si hay dataset_id, filtrar por ese dataset
        // Si no hay, cargar todas las categorías (vista global)
        let url = `${API_BASE_URL}/categories`
        if (targetDatasetId) {
          url += `?dataset_id=${targetDatasetId}`
        }
        
        const response = await fetch(url)
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        this.categories = data.categories || []
        
        // Establecer categoría por defecto si no hay una seleccionada
        if (!this.selectedCategory && this.categories.length > 0) {
          this.selectedCategory = this.categories[0].id
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
        const targetDatasetId = datasetId || this.currentDataset?._id
        
        // dataset_id es obligatorio
        if (!targetDatasetId) {
          throw new Error('dataset_id es requerido para crear una categoría')
        }
        
        const payload = {
          dataset_id: targetDatasetId,
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
          const errorData = await response.json()
          throw new Error(errorData.error || 'Error al crear categoría')
        }
        
        const data = await response.json()
        
        // Recargar categorías para mantener consistencia
        await this.loadCategories(targetDatasetId)
        
        return data.category
        
      } catch (error) {
        this.setError(`Error al crear categoría: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async updateCategory(categoryData) {
      this.loading = true
      this.clearError()
      
      try {
        const categoryId = categoryData.id || categoryData._id
        const response = await fetch(`${API_BASE_URL}/categories/${categoryId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            name: categoryData.name,
            color: categoryData.color,
            supercategory: categoryData.supercategory
          })
        })
        
        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.error || 'Error al actualizar categoría')
        }
        
        const data = await response.json()
        
        // Recargar categorías para mantener consistencia
        await this.loadCategories()
        
        return data.category
      } catch (error) {
        this.setError(`Error al actualizar categoría: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async deleteCategory(categoryId, force = false) {
      this.loading = true
      this.clearError()
      
      try {
        // Construir URL con dataset_id si estamos en contexto de dataset
        let url = `${API_BASE_URL}/categories/${categoryId}`
        const params = new URLSearchParams()
        
        if (this.currentDataset) {
          params.append('dataset_id', this.currentDataset._id)
        }
        
        if (force) {
          params.append('force', 'true')
        }
        
        if (params.toString()) {
          url += `?${params.toString()}`
        }
        
        const response = await fetch(url, {
          method: 'DELETE'
        })
        
        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.error || 'Error al eliminar categoría')
        }
        
        // Si era la categoría seleccionada, cambiar a otra
        if (this.selectedCategory === categoryId) {
          const remainingCategories = this.categories.filter(cat => cat.id !== categoryId)
          this.selectedCategory = remainingCategories.length > 0 ? 
            remainingCategories[0].id : null
        }
        
        // Recargar categorías y anotaciones para mantener consistencia
        await this.loadCategories()
        if (this.currentDataset) {
          await this.loadAnnotationsByDataset()
        } else {
          await this.loadAllAnnotations()
        }
        
      } catch (error) {
        this.setError(`Error al eliminar categoría: ${error.message}`)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    // ==================== MANEJO DE VISIBILIDAD ====================
    
    async loadCategoryVisibility(datasetId) {
      if (!datasetId && !this.currentDataset) return
      
      try {
        const targetDatasetId = datasetId || this.currentDataset._id
        const response = await fetch(`${API_BASE_URL}/categories/visibility/${targetDatasetId}`)
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        this.categoryVisibility = data.visibility || {}
        
      } catch (error) {
        console.error('Error al cargar visibilidad de categorías:', error)
        this.categoryVisibility = {}
      }
    },

    async toggleCategoryVisibility(categoryId) {
      if (!this.currentDataset) return
      
      try {
        const response = await fetch(`${API_BASE_URL}/categories/${categoryId}/toggle-visibility?dataset_id=${this.currentDataset._id}`, {
          method: 'PATCH'
        })
        
        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        
        // Actualizar estado local
        this.categoryVisibility[categoryId] = data.hidden
        
        return data.hidden
        
      } catch (error) {
        this.setError(`Error al cambiar visibilidad: ${error.message}`)
        throw error
      }
    },

    // Métodos para manejar visibilidad de anotaciones individuales
    toggleAnnotationVisibility(annotationId) {
      // Para anotaciones, manejamos la visibilidad localmente
      this.annotationVisibility[annotationId] = !this.annotationVisibility[annotationId]
    },

    hideAllCategoryAnnotations(categoryId) {
      // Ocultar todas las anotaciones de una categoría
      const categoryAnnotations = this.getAnnotationsByCategory(categoryId)
      categoryAnnotations.forEach(annotation => {
        this.annotationVisibility[annotation._id] = true
      })
    },

    showAllCategoryAnnotations(categoryId) {
      // Mostrar todas las anotaciones de una categoría
      const categoryAnnotations = this.getAnnotationsByCategory(categoryId)
      categoryAnnotations.forEach(annotation => {
        this.annotationVisibility[annotation._id] = false
      })
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
      }
    },
    
    async setCurrentImage(image) {
      this.currentImage = image
      
      // Cargar anotaciones de la imagen actual
      if (image && (image.id || image._id)) {
        const imageId = image.id || image._id
        this.ensureUndoStack(imageId)
        try {
          await this.loadAnnotations(imageId)
        } catch (error) {
          console.error('Error al cargar anotaciones para la imagen:', error)
        }
      }
    },

    markImageAsCompleted(imageId) {
      if (!imageId) return
      const image = this.images.find(img => (img._id || img.id) === imageId)
      if (image) {
        image.completed = true
        image.completedAt = new Date().toISOString()
      }
      // Limpiar undo stack cuando la imagen se marca como completada
      this.clearUndoStack(imageId)
    },

    getNextIncompleteImage(imageId) {
      if (!this.images.length) return null
      const normalizedId = imageId
      const total = this.images.length
      const currentIndex = this.images.findIndex(img => (img._id || img.id) === normalizedId)
      const startIndex = currentIndex >= 0 ? currentIndex : -1
      for (let offset = 1; offset <= total; offset += 1) {
        const index = (startIndex + offset) % total
        const candidate = this.images[index]
        if (!candidate?.completed) {
          return candidate
        }
      }
      return null
    },
    
    setCurrentDataset(dataset) {
      this.currentDataset = dataset
      // Limpiar datos cuando cambiamos de dataset
      this.images = []
      this.annotations = []
      this.categories = []
      this.currentImage = null
      this.selectedCategory = null
      this.undoStacks = {}
    },
    
    clearDatasetContext() {
      this.currentDataset = null
      this.images = []
      this.annotations = []
      this.categories = []
      this.currentImage = null
      this.selectedCategory = null
      this.undoStacks = {}
    },
    
    // ==================== INICIALIZACIÓN ====================
    
    async initialize(datasetId = null) {
      try {
        await Promise.all([
          this.loadImages(datasetId),
          this.loadCategories(datasetId),
          this.loadAnnotationsByDataset(datasetId),
          this.loadCategoryVisibility(datasetId)
        ])
      } catch (error) {
        console.error('Error al inicializar store:', error)
      }
    }
  }
})