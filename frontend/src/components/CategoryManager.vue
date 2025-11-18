<template>
  <div class="categories-manager">
    <!-- Header -->
    <div class="categories-header">
      <h3 class="categories-title">Gestión de Categorías</h3>
      <div class="header-buttons-row">
        <button @click="showImportModal = true" class="btn-import" title="Importar categorías de otros datasets">
          <i class="fas fa-file-import"></i>
          <span>Importar</span>
        </button>
        <button @click="showAddForm = true" class="btn-primary">
          <i class="fas fa-plus-circle"></i>
          <span>Nueva</span>
        </button>
      </div>
    </div>

    <!-- Formulario para nueva categoría -->
    <div v-if="showAddForm" class="add-form">
      <h4>Nueva Categoría</h4>
      <div class="form-group">
        <label>Nombre:</label>
        <input 
          v-model="newCategory.name" 
          type="text" 
          class="form-input"
          placeholder="Nombre de la categoría"
          @keydown.enter="addCategory"
        >
      </div>
      <div class="form-group">
        <label>Color:</label>
        <input 
          v-model="newCategory.color" 
          type="color" 
          class="form-color"
        >
      </div>
      <div class="form-actions">
        <button @click="addCategory" class="btn-success" :disabled="adding">
          {{ adding ? 'Añadiendo...' : 'Añadir' }}
        </button>
        <button @click="cancelAdd" class="btn-secondary">Cancelar</button>
      </div>
    </div>

    <!-- Lista de categorías -->
    <div class="categories-list">
      <div v-if="loading" class="loading-state">
        <p>Cargando categorías...</p>
      </div>
      
      <div v-else-if="categories.length === 0" class="empty-state">
        <div class="empty-icon">📁</div>
        <h4>No hay categorías disponibles</h4>
        <p>Crea tu primera categoría para comenzar a anotar</p>
        <button @click="showAddForm = true" class="btn-create-first">
          <i class="fas fa-folder-plus"></i>
          <span>Crear primera categoría</span>
        </button>
      </div>
      
      <div 
        v-else
        v-for="category in categories" 
        :key="category.id" 
        class="category-section"
      >
        <!-- Header de la categoría -->
        <div 
          class="category-header"
          :class="{ 
            'active': selectedCategory === category.id,
            'hidden-category': isHidden(category.id)
          }"
          @click="selectCategory(category.id)"
        >
          <div class="category-info">
            <div 
              class="category-color" 
              :style="{ backgroundColor: category.color }"
            ></div>
            <div class="category-details">
              <span class="category-name">{{ category.name }}</span>
            </div>
            <span class="category-count">({{ getCategoryAnnotationCount(category.id) }})</span>
          </div>
          <div class="category-actions">
            <button 
              @click.stop="editCategory(category)" 
              class="btn-edit"
              title="Editar categoría"
            >
              <i class="fas fa-edit"></i>
            </button>
            <button 
              @click.stop="toggleVisibility(category.id)" 
              class="btn-visibility"
              :title="isHidden(category.id) ? 'Mostrar categoría' : 'Ocultar categoría'"
            >
              <i v-if="isHidden(category.id)" class="fa-solid fa-eye-slash"></i>
              <i v-else class="fa-solid fa-eye"></i>
            </button>
          </div>
        </div>

        <!-- Lista de anotaciones de esta categoría -->
        <div 
          v-if="getCategoryAnnotations(category.id).length > 0" 
          class="annotations-list"
        >
          <div 
            v-for="(annotation, index) in getCategoryAnnotations(category.id)" 
            :key="annotation._id"
            class="annotation-item"
            :class="{ 'hidden-annotation': isAnnotationHidden(annotation._id) }"
            @click="selectAnnotation(annotation)"
          >
            <span class="annotation-number">{{ index + 1 }}</span>
            <span class="annotation-id">(id: {{ annotation._id.slice(-2) }})</span>
            <div class="annotation-actions">
              <button 
                @click.stop="toggleAnnotationVisibility(annotation._id)" 
                class="btn-visibility-small"
                :title="isAnnotationHidden(annotation._id) ? 'Mostrar anotación' : 'Ocultar anotación'"
              >
                <i v-if="isAnnotationHidden(annotation._id)" class="fa-solid fa-eye-slash"></i>
                <i v-else class="fa-solid fa-eye"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de edición -->
    <div v-if="editingCategory" class="modal-overlay" @click="cancelEdit">
      <div class="modal-content modal-edit" @click.stop>
        <div class="modal-header">
          <h3>Editar Categoría</h3>
          <button @click="cancelEdit" class="btn-close">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Nombre:</label>
            <input 
              v-model="editingCategory.name" 
              type="text" 
              class="form-input"
            >
          </div>
          <div class="form-group">
            <label>Color:</label>
            <input 
              v-model="editingCategory.color" 
              type="color" 
              class="form-color"
            >
          </div>
        </div>
        <div class="modal-footer">
          <button @click="saveEdit" class="btn-success">Guardar</button>
          <button @click="cancelEdit" class="btn-secondary">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Modal de importación de categorías -->
    <div v-if="showImportModal" class="modal-overlay" @click="closeImportModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Importar Categorías</h3>
          <button @click="closeImportModal" class="btn-close">&times;</button>
        </div>
        
        <div class="modal-body">
          <p class="modal-description">
            Selecciona las categorías de otros datasets que deseas importar al dataset actual.
          </p>
          
          <div v-if="loadingAllCategories" class="loading-state">
            <p>Cargando categorías disponibles...</p>
          </div>
          
          <div v-else-if="availableCategoriesToImport.length === 0" class="empty-state">
            <p>No hay categorías disponibles para importar desde otros datasets.</p>
          </div>
          
          <div v-else class="import-categories-list">
            <div 
              v-for="category in availableCategoriesToImport" 
              :key="category.id"
              class="import-category-item"
            >
              <label class="checkbox-label">
                <input 
                  type="checkbox" 
                  :value="category.id"
                  v-model="selectedCategoriesToImport"
                  class="category-checkbox"
                >
                <div class="category-info-import">
                  <div 
                    class="category-color-preview" 
                    :style="{ backgroundColor: category.color }"
                  ></div>
                  <span class="category-name-import">{{ category.name }}</span>
                  <span class="category-dataset-info">({{ getDatasetName(category.dataset_id) }})</span>
                </div>
              </label>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button 
            @click="importSelectedCategories" 
            class="btn-success" 
            :disabled="selectedCategoriesToImport.length === 0 || importing"
          >
            {{ importing ? 'Importando...' : `Importar ${selectedCategoriesToImport.length} categoría(s)` }}
          </button>
          <button @click="closeImportModal" class="btn-secondary">Cancelar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAnnotationStore } from '../stores/annotationStore'

// Store
const store = useAnnotationStore()

// Estado reactivo
const categories = computed(() => store.categories)
const annotations = computed(() => store.annotations)
const loading = computed(() => store.loading)
const selectedCategory = computed(() => store.selectedCategory)

const selectedCategoryData = computed(() => {
  return categories.value.find(cat => cat.id === selectedCategory.value)
})

const showAddForm = ref(false)
const adding = ref(false)
const editingCategory = ref(null)

// Estado para importación
const showImportModal = ref(false)
const allCategories = ref([])
const allDatasets = ref([])
const loadingAllCategories = ref(false)
const selectedCategoriesToImport = ref([])
const importing = ref(false)

const newCategory = ref({
  name: '',
  color: '#ff0000'
})

// Métodos
function selectCategory(categoryId) {
  store.setSelectedCategory(categoryId)
}

async function addCategory() {
  if (!newCategory.value.name.trim()) return
  
  adding.value = true
  try {
    await store.addCategory(newCategory.value)
    newCategory.value = { name: '', color: '#ff0000' }
    showAddForm.value = false
  } catch (error) {
    // El error ya se maneja en el store
  } finally {
    adding.value = false
  }
}

function cancelAdd() {
  showAddForm.value = false
  newCategory.value = { name: '', color: '#ff0000' }
}

function editCategory(category) {
  editingCategory.value = { ...category }
}

async function saveEdit() {
  try {
    await store.updateCategory(editingCategory.value)
    editingCategory.value = null
  } catch (error) {
    // El error ya se maneja en el store
  }
}

function cancelEdit() {
  editingCategory.value = null
}

function getCategoryAnnotationCount(categoryId) {
  return store.getCategoryAnnotationCount(categoryId)
}

// Función para verificar si una categoría está oculta
function isHidden(categoryId) {
  return store.isCategoryHidden(categoryId)
}

// Función para toggle visibilidad
async function toggleVisibility(categoryId) {
  try {
    await store.toggleCategoryVisibility(categoryId)
  } catch (error) {
    console.error('Error al cambiar visibilidad:', error)
  }
}

// Nuevas funciones para manejar anotaciones individuales
function getCategoryAnnotations(categoryId) {
  // Usar el nuevo getter que filtra por imagen actual
  const annotationsByCategory = store.getCurrentImageAnnotationsByCategory
  return annotationsByCategory[categoryId] || []
}

function isAnnotationHidden(annotationId) {
  return store.isAnnotationHidden(annotationId)
}

function toggleAnnotationVisibility(annotationId) {
  store.toggleAnnotationVisibility(annotationId)
}

function selectAnnotation(annotation) {
  store.selectAnnotation(annotation)
}

// Funciones de importación de categorías
const availableCategoriesToImport = computed(() => {
  if (!store.currentDataset) return []
  
  // Filtrar categorías que NO pertenecen al dataset actual
  const otherDatasetCategories = allCategories.value.filter(cat => 
    cat.dataset_id !== store.currentDataset._id
  )
  
  // Excluir categorías que ya existen en el dataset actual (por nombre)
  const currentCategoryNames = categories.value.map(c => c.name.toLowerCase())
  return otherDatasetCategories.filter(cat => 
    !currentCategoryNames.includes(cat.name.toLowerCase())
  )
})

function getDatasetName(datasetId) {
  const dataset = allDatasets.value.find(d => d._id === datasetId)
  return dataset ? dataset.name : 'Dataset desconocido'
}

async function loadAllCategoriesAndDatasets() {
  loadingAllCategories.value = true
  try {
    // Cargar todas las categorías (sin filtro de dataset)
    const categoriesData = await window.$apiGet('/api/categories')
    allCategories.value = categoriesData.categories || []
    
    // Cargar todos los datasets para mostrar nombres
    const datasetsData = await window.$apiGet('/api/datasets')
    allDatasets.value = datasetsData.datasets || []
  } catch (error) {
    console.error('Error al cargar datos para importación:', error)
    alert('Error al cargar categorías disponibles: ' + error.message)
  } finally {
    loadingAllCategories.value = false
  }
}

async function importSelectedCategories() {
  if (selectedCategoriesToImport.value.length === 0) return
  if (!store.currentDataset) {
    alert('No hay dataset seleccionado')
    return
  }
  
  importing.value = true
  try {
    let successCount = 0
    let errorCount = 0
    
    for (const categoryId of selectedCategoriesToImport.value) {
      const categoryToImport = allCategories.value.find(c => c.id === categoryId)
      if (!categoryToImport) continue
      
      try {
        // Crear una nueva categoría con los mismos datos pero en el dataset actual
        await store.addCategory({
          name: categoryToImport.name,
          color: categoryToImport.color
        }, store.currentDataset._id)
        successCount++
      } catch (error) {
        console.error(`Error al importar categoría ${categoryToImport.name}:`, error)
        errorCount++
      }
    }
    
    if (successCount > 0) {
      alert(`✅ Se importaron ${successCount} categoría(s) correctamente${errorCount > 0 ? `. ${errorCount} fallaron.` : ''}`)
      closeImportModal()
      // Recargar categorías del dataset actual
      await store.loadCategories(store.currentDataset._id)
    } else {
      alert('❌ No se pudo importar ninguna categoría')
    }
  } catch (error) {
    console.error('Error al importar categorías:', error)
    alert('Error al importar categorías: ' + error.message)
  } finally {
    importing.value = false
  }
}

function closeImportModal() {
  showImportModal.value = false
  selectedCategoriesToImport.value = []
  allCategories.value = []
  allDatasets.value = []
}

// Cargar categorías al montar el componente
onMounted(() => {
  if (categories.value.length === 0) {
    store.loadCategories()
  }
  // Cargar anotaciones del dataset actual (si hay uno) o todas si no hay dataset
  if (annotations.value.length === 0) {
    if (store.currentDataset) {
      store.loadAnnotationsByDataset()
      store.loadCategoryVisibility()
    } else {
      store.loadAllAnnotations()
    }
  }
})

// Watch para cargar categorías cuando se abre el modal de importación
watch(showImportModal, (newValue) => {
  if (newValue) {
    loadAllCategoriesAndDatasets()
  }
})
</script>

<style scoped>
.categories-manager {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
}

.categories-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.categories-header h3 {
  margin: 0;
  color: #2c3e50;
  font-size: 1.2rem;
  font-weight: 600;
}

.add-form {
  background: white;
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  border: 1px solid #ddd;
}

.add-form h4 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
  font-size: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 500;
  color: #555;
  font-size: 0.9rem;
}

.form-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
}

.form-color {
  width: 50px;
  height: 35px;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
}

.form-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-success {
  background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
  transition: all 0.3s ease;
  box-shadow: 0 2px 6px rgba(39, 174, 96, 0.3);
}

.btn-success:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(39, 174, 96, 0.4);
  background: linear-gradient(135deg, #229954 0%, #27ae60 100%);
}

.btn-success:active {
  transform: translateY(0);
}

.btn-success:disabled {
  background: #95a5a6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-secondary {
  background: #ecf0f1;
  color: #34495e;
  border: 1px solid #bdc3c7;
  padding: 0.6rem 1.2rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.btn-secondary:hover {
  background: #bdc3c7;
  color: #2c3e50;
  border-color: #95a5a6;
}

.categories-header {
  gap: 0.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 1.2rem;
}

.categories-title {
  color: #2c3e50;
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-align: center;
}

.header-buttons-row {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  justify-content: center;
  width: 100%;
  margin-top: 0.2rem;
  margin-bottom: 0.5rem;
}

.category-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem;
  border-bottom: 1px solid #e1e5e9;
  cursor: pointer;
  transition: background-color 0.2s;
}

.category-header:hover {
  background: #f8f9fa;
}

.category-header.active {
  border-color: #27ae60;
  background: #f8fff9;
}

.category-header.hidden-category {
  opacity: 0.5;
  background: #f5f5f5;
}

.category-header.hidden-category .category-color {
  opacity: 0.6;
}

.category-header.hidden-category .category-name {
  color: #999;
  text-decoration: line-through;
}

.category-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.category-color {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid white;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.1);
}

.category-color.small {
  width: 12px;
  height: 12px;
}

.category-details {
  flex: 1;
}

.category-name {
  font-weight: 500;
  color: #2c3e50;
  font-size: 0.9rem;
}

.category-count {
  color: #666;
  font-size: 1rem;
  margin-left: 0.5rem;
  margin-right: 0.65rem;
  display: flex;
  align-items: center;
  line-height: 1;
  transform: translateY(-1px);
}

.category-actions {
  display: flex;
  gap: 0.65rem;
}

.btn-edit, .btn-delete, .btn-visibility {
  background: none;
  border: none;
  font-size: 1rem;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 3px;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.btn-edit:hover, .btn-delete:hover, .btn-visibility:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.1);
}

.annotations-list {
  background: #f8f9fa;
  border-top: 1px solid #e1e5e9;
}

.annotation-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #e1e5e9;
  cursor: pointer;
  transition: background-color 0.2s;
}

.annotation-item:last-child {
  border-bottom: none;
}

.annotation-item:hover {
  background: #e9ecef;
}

.annotation-item.hidden-annotation {
  opacity: 0.5;
  background: #f5f5f5;
  text-decoration: line-through;
}

.annotation-number {
  font-weight: 600;
  color: #3498db;
  font-size: 0.9rem;
}

.annotation-id {
  color: #666;
  font-size: 0.8rem;
  margin-left: 0.5rem;
}

.annotation-actions {
  display: flex;
  gap: 0.25rem;
}

.btn-visibility-small {
  background: none;
  border: none;
  font-size: 0.8rem;
  cursor: pointer;
  padding: 0.1rem;
  border-radius: 3px;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.btn-visibility-small:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.1);
}

/* ==================== ESTILOS PARA MODALES ==================== */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 0;
  min-width: 400px;
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

/* Modal específico para edición de categoría */
.modal-edit {
  min-width: 350px;
  max-width: 450px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h3 {
  margin: 0;
  color: #2c3e50;
  font-size: 1.3rem;
}

.modal-body {
  padding: 1.5rem;
  flex: 1;
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1.5rem;
  border-top: 1px solid #e0e0e0;
  background: #f8f9fa;
}

.btn-close {
  background: transparent;
  border: none;
  font-size: 1.8rem;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background 0.3s;
}

.btn-close:hover {
  background: #f0f0f0;
  color: #333;
}

.current-selection {
  background: #e8f5e8;
  border: 1px solid #27ae60;
  border-radius: 6px;
  padding: 1rem;
  margin-top: 1rem;
}

.selected-category {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  color: #27ae60;
}

.help-text {
  margin: 0.5rem 0 0 0;
  font-size: 0.9rem;
  color: #666;
}

/* Estilos para botones del header */
.header-buttons {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.btn-import {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 0.65rem 1.25rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-import i {
  font-size: 1rem;
}

.btn-import:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
  background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
}

.btn-import:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  padding: 0.65rem 1.25rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-primary i {
  font-size: 1rem;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
}

.btn-primary:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

/* ==================== ESTILOS ESPECÍFICOS PARA MODAL DE IMPORTACIÓN ==================== */
.modal-description {
  margin: 0 0 1rem 0;
  color: #666;
  font-size: 0.95rem;
}

.import-categories-list {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 0.5rem;
}

.import-category-item {
  padding: 0.75rem;
  border-bottom: 1px solid #f0f0f0;
}

.import-category-item:last-child {
  border-bottom: none;
}

.checkbox-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  width: 100%;
}

.category-checkbox {
  margin-right: 0.75rem;
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.category-info-import {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.category-color-preview {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.1);
}

.category-name-import {
  font-weight: 500;
  color: #2c3e50;
}

.category-dataset-info {
  color: #7f8c8d;
  font-size: 0.85rem;
  font-style: italic;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 1.5rem 1rem;
  color: #7f8c8d;
}

.empty-state {
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  border: 2px dashed #e0e6ed;
  border-radius: 12px;
  margin: 1rem 0;
}

.empty-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
  opacity: 0.7;
}

.empty-state h4 {
  color: #2c3e50;
  margin: 0 0 0.3rem 0;
  font-size: 0.95rem;
  font-weight: 600;
}

.empty-state p {
  color: #7f8c8d;
  margin: 0 0 1rem 0;
  font-size: 0.8rem;
}

.btn-create-first {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  transition: all 0.3s ease;
  box-shadow: 0 3px 8px rgba(102, 126, 234, 0.4);
  margin: 0 auto;
}

.btn-create-first i {
  font-size: 1.2rem;
  animation: pulse 2s ease-in-out infinite;
}

.btn-create-first:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(139, 92, 246, 0.5);
  background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);
}

.btn-create-first:active {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.15); opacity: 0.9; }
}
</style>