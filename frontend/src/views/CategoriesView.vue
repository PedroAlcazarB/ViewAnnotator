<template>
  <div class="categories-view">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-title">
          <h1>
            <i class="fas fa-tags"></i>
            Categorías
          </h1>
          <p class="subtitle">Gestiona las categorías de anotación para tus proyectos</p>
        </div>
        <div class="header-actions">
          <button @click="showCreateModal = true" class="btn btn-primary">
            <i class="fas fa-plus"></i>
            Crear Categoría
          </button>
          <button @click="refreshCategories" class="btn btn-secondary">
            <i class="fas fa-sync-alt"></i>
            Actualizar
          </button>
        </div>
      </div>
    </div>

    <!-- Categories Grid -->
    <div class="categories-container">
      <div v-if="loading" class="loading-state">
        <i class="fas fa-spinner fa-spin"></i>
        <p>Cargando categorías...</p>
      </div>

      <div v-else-if="categories.length === 0" class="empty-state">
        <i class="fas fa-tags"></i>
        <h3>No hay categorías</h3>
        <p>Crea tu primera categoría para comenzar a anotar</p>
        <button @click="showCreateModal = true" class="btn btn-primary btn-large">
          <i class="fas fa-plus"></i>
          Crear Primera Categoría
        </button>
      </div>

      <div v-else class="categories-grid">
        <div
          v-for="category in categories"
          :key="category.id"
          class="category-card"
          @click="selectCategory(category)"
        >
          <div class="card-header">
            <div class="category-title">
              <div 
                class="category-color" 
                :style="{ backgroundColor: category.color }"
              ></div>
              <h3>{{ category.name }}</h3>
            </div>
            <div class="card-actions">
              <button 
                @click.stop="editCategory(category)" 
                class="btn-icon btn-edit"
                title="Editar categoría"
              >
                <i class="fas fa-edit"></i>
              </button>
              <button 
                @click.stop="deleteCategory(category)" 
                class="btn-icon btn-delete"
                title="Eliminar categoría"
              >
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>

          <div class="card-body">
            <div class="dataset-info">
              <span class="dataset-name">{{ getDatasetName(category.dataset_id) }}</span>
            </div>
            <div v-if="getCategoryAnnotationCount(category.id) > 0" class="annotation-count">
              <i class="fas fa-layer-group"></i>
              <span>{{ getCategoryAnnotationCount(category.id) }} anotaciones</span>
            </div>
            <div v-else class="annotation-count">
              <i class="fas fa-layer-group"></i>
              <span class="no-annotations">Sin anotaciones</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal para crear categoría -->
    <div v-if="showCreateModal" class="modal-overlay" @click="closeCreateModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>
            <i class="fas fa-plus"></i>
            Nueva Categoría
          </h2>
          <button @click="closeCreateModal" class="btn-close">
            <i class="fas fa-times"></i>
          </button>
        </div>

        <div class="modal-body">
          <form @submit.prevent="createCategory">
            <div class="form-group">
              <label for="categoryDataset">
                <i class="fas fa-database"></i>
                Dataset *
              </label>
              <select
                id="categoryDataset"
                v-model="newCategory.dataset_id"
                class="form-input"
                :class="{ 'error': errors.dataset_id }"
                required
              >
                <option value="">Selecciona un dataset</option>
                <option 
                  v-for="dataset in datasets" 
                  :key="dataset._id" 
                  :value="dataset._id"
                >
                  {{ dataset.name }}
                </option>
              </select>
              <span v-if="errors.dataset_id" class="error-message">{{ errors.dataset_id }}</span>
            </div>

            <div class="form-group">
              <label for="categoryName">
                <i class="fas fa-tag"></i>
                Nombre de la categoría *
              </label>
              <input
                id="categoryName"
                v-model="newCategory.name"
                type="text"
                class="form-input"
                :class="{ 'error': errors.name }"
                placeholder="Ej: Persona, Vehículo, Animal..."
                required
              />
              <span v-if="errors.name" class="error-message">{{ errors.name }}</span>
            </div>

            <div class="form-group">
              <label for="categoryColor">
                <i class="fas fa-palette"></i>
                Color
              </label>
              <div class="color-input-group">
                <input
                  id="categoryColor"
                  v-model="newCategory.color"
                  type="color"
                  class="form-color"
                />
                <input
                  v-model="newCategory.color"
                  type="text"
                  class="form-input color-text"
                  placeholder="#ff0000"
                />
              </div>
            </div>
          </form>
        </div>

        <div class="modal-footer">
          <button @click="createCategory" class="btn btn-primary" :disabled="creating">
            <i v-if="creating" class="fas fa-spinner fa-spin"></i>
            <i v-else class="fas fa-save"></i>
            {{ creating ? 'Creando...' : 'Crear Categoría' }}
          </button>
          <button @click="closeCreateModal" class="btn btn-secondary">
            <i class="fas fa-times"></i>
            Cancelar
          </button>
        </div>
      </div>
    </div>

    <!-- Modal para editar categoría -->
    <div v-if="showEditModal" class="modal-overlay" @click="closeEditModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>
            <i class="fas fa-edit"></i>
            Editar Categoría: {{ editingCategory.name }}
          </h2>
          <button @click="closeEditModal" class="btn-close">
            <i class="fas fa-times"></i>
          </button>
        </div>

        <div class="modal-body">
          <form @submit.prevent="updateCategory">
            <div class="form-group">
              <label for="editCategoryName">
                <i class="fas fa-tag"></i>
                Nombre de la categoría *
              </label>
              <input
                id="editCategoryName"
                v-model="editingCategory.name"
                type="text"
                class="form-input"
                :class="{ 'error': errors.name }"
                required
              />
              <span v-if="errors.name" class="error-message">{{ errors.name }}</span>
            </div>

            <div class="form-group">
              <label for="editCategoryColor">
                <i class="fas fa-palette"></i>
                Color
              </label>
              <div class="color-input-group">
                <input
                  id="editCategoryColor"
                  v-model="editingCategory.color"
                  type="color"
                  class="form-color"
                />
                <input
                  v-model="editingCategory.color"
                  type="text"
                  class="form-input color-text"
                  placeholder="#ff0000"
                />
              </div>
            </div>
          </form>
        </div>

        <div class="modal-footer">
          <button @click="updateCategory" class="btn btn-primary" :disabled="updating">
            <i v-if="updating" class="fas fa-spinner fa-spin"></i>
            <i v-else class="fas fa-save"></i>
            {{ updating ? 'Guardando...' : 'Guardar Cambios' }}
          </button>
          <button @click="closeEditModal" class="btn btn-secondary">
            <i class="fas fa-times"></i>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAnnotationStore } from '@/stores/annotationStore'

// Store
const store = useAnnotationStore()

// Estado reactivo
const categories = computed(() => store.categories)
const annotations = computed(() => store.annotations)
const loading = computed(() => store.loading)
const datasets = ref([])
const showCreateModal = ref(false)
const showEditModal = ref(false)
const creating = ref(false)
const updating = ref(false)
const errors = ref({})

const newCategory = ref({
  name: '',
  color: '#ff0000',
  dataset_id: ''
})

const editingCategory = ref({
  id: '',
  name: '',
  color: '#ff0000'
})

// Métodos
async function loadDatasets() {
  try {
    const data = await window.$apiGet('/api/datasets')
    datasets.value = data.datasets || []
  } catch (error) {
    console.error('Error al cargar datasets:', error)
    alert('Error al cargar datasets: ' + error.message)
  }
}

async function loadCategories() {
  try {
    await store.loadCategories()
  } catch (error) {
    console.error('Error al cargar categorías:', error)
    alert('Error al cargar categorías: ' + error.message)
  }
}

function getDatasetName(datasetId) {
  const dataset = datasets.value.find(d => d._id === datasetId)
  return dataset ? dataset.name : 'Dataset desconocido'
}

async function createCategory() {
  if (!validateForm(newCategory.value)) return
  
  creating.value = true
  errors.value = {}
  
  try {
    await store.addCategory(newCategory.value, newCategory.value.dataset_id)
    alert('Categoría creada correctamente')
    closeCreateModal()
    await loadCategories()
  } catch (error) {
    console.error('Error al crear categoría:', error)
    alert('Error al crear categoría: ' + error.message)
  } finally {
    creating.value = false
  }
}

async function updateCategory() {
  if (!validateForm(editingCategory.value)) return
  
  updating.value = true
  errors.value = {}
  
  try {
    await store.updateCategory(editingCategory.value)
    alert('Categoría actualizada correctamente')
    closeEditModal()
  } catch (error) {
    console.error('Error al actualizar categoría:', error)
    alert('Error al actualizar categoría: ' + error.message)
  } finally {
    updating.value = false
  }
}

// Función para obtener el conteo actualizado de anotaciones
function getCategoryAnnotationCount(categoryId) {
  return store.getCategoryAnnotationCount(categoryId)
}

// Función para determinar si mostrar el botón de eliminar
function canShowDeleteButton(categoryId) {
  return getCategoryAnnotationCount(categoryId) === 0
}

async function deleteCategory(category) {
  // Obtener información contextual
  const currentCount = getCategoryAnnotationCount(category.id)
  const globalCount = await store.getCategoryGlobalAnnotationCount(category.id)
  
  let message = `¿Estás seguro de que quieres eliminar la categoría "${category.name}"?`
  
  if (store.currentDataset) {
    // En contexto de dataset
    if (currentCount > 0) {
      message = `La categoría "${category.name}" tiene ${currentCount} anotaciones en este dataset. ¿Estás seguro de que quieres eliminarla? Esto eliminará también las anotaciones asociadas.`
    } else if (globalCount > 0) {
      message = `La categoría "${category.name}" no tiene anotaciones en este dataset, pero sí en otros datasets (${globalCount} total). ¿Quieres eliminarla completamente del sistema?`
    }
  } else {
    // En contexto global
    if (globalCount > 0) {
      message = `La categoría "${category.name}" tiene ${globalCount} anotaciones en total. ¿Estás seguro de que quieres eliminarla? Esto eliminará también todas las anotaciones asociadas.`
    }
  }
  
  if (!confirm(message)) {
    return
  }
  
  try {
    await store.deleteCategory(category.id, true) // force = true
    alert('Categoría eliminada correctamente')
  } catch (error) {
    console.error('Error al eliminar categoría:', error)
    alert('Error al eliminar categoría: ' + error.message)
  }
}

function validateForm(category) {
  errors.value = {}
  
  if (!category.name || category.name.trim() === '') {
    errors.value.name = 'El nombre es requerido'
    return false
  }
  
  if (category.name.length > 50) {
    errors.value.name = 'El nombre no puede exceder 50 caracteres'
    return false
  }
  
  // Validar dataset_id solo para nuevas categorías
  if (showCreateModal.value && (!category.dataset_id || category.dataset_id.trim() === '')) {
    errors.value.dataset_id = 'Debes seleccionar un dataset'
    return false
  }
  
  return true
}

function editCategory(category) {
  editingCategory.value = {
    id: category.id,
    name: category.name,
    color: category.color
  }
  showEditModal.value = true
}

function selectCategory(category) {
  // Seleccionar categoría en el store para sincronización
  store.setSelectedCategory(category.id)
  console.log('Categoría seleccionada:', category)
}

async function refreshCategories() {
  await loadCategories()
  await store.loadAllAnnotations()  // Cargar todas las anotaciones para conteos actualizados
}

function closeCreateModal() {
  showCreateModal.value = false
  newCategory.value = {
    name: '',
    color: '#ff0000',
    dataset_id: ''
  }
  errors.value = {}
}

function closeEditModal() {
  showEditModal.value = false
  editingCategory.value = {
    id: '',
    name: '',
    color: '#ff0000'
  }
  errors.value = {}
}

// Lifecycle
onMounted(() => {
  // Cargar datasets primero
  loadDatasets()
  // Cargar categorías si no están ya cargadas
  if (categories.value.length === 0) {
    loadCategories()
  }
  // Cargar todas las anotaciones para poder calcular conteos correctos
  if (annotations.value.length === 0) {
    store.loadAllAnnotations()
  }
})
</script>

<style scoped>
.categories-view {
  min-height: 100vh;
  background: #f8f9fa;
}

/* Header */
.page-header {
  background: white;
  border-bottom: 0.0625rem solid #e1e5e9;
  padding: 2rem 0;
}

.header-content {
  max-width: 75rem;
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.header-title h1 {
  margin: 0;
  color: #2c3e50;
  font-size: 2rem;
  font-weight: 700;
}

.header-title h1 i {
  margin-right: 0.5rem;
  color: #3498db;
}

.subtitle {
  margin: 0.5rem 0 0 0;
  color: #6c757d;
  font-size: 1rem;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

/* Categories Container */
.categories-container {
  max-width: 75rem;
  margin: 0 auto;
  padding: 2rem;
}

/* Loading & Empty States */
.loading-state, .empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #6c757d;
}

.loading-state i, .empty-state i {
  font-size: 3rem;
  margin-bottom: 1rem;
  color: #3498db;
}

.empty-state h3 {
  margin: 1rem 0;
  color: #2c3e50;
}

.empty-state .btn-large {
  padding: 0.875rem 2rem;
  font-size: 1.1rem;
  font-weight: 600;
  margin-top: 1.5rem;
  border-radius: 0.5rem;
  box-shadow: 0 0.125rem 0.5rem rgba(52, 152, 219, 0.3);
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.empty-state .btn-large:hover {
  transform: translateY(-0.125rem);
  box-shadow: 0 0.25rem 0.75rem rgba(52, 152, 219, 0.4);
}

.empty-state .btn-large i {
  font-size: 1.2rem !important;
  line-height: 1 !important;
  margin: 0 !important;
  color: white !important;
  opacity: 1 !important;
  visibility: visible !important;
  display: inline-block !important;
}

/* Categories Grid */
.categories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(20rem, 1fr));
  gap: 1.5rem;
}

.category-card {
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.1);
  transition: all 0.2s ease;
  cursor: pointer;
  overflow: hidden;
}

.category-card:hover {
  transform: translateY(-0.125rem);
  box-shadow: 0 0.25rem 0.75rem rgba(0,0,0,0.15);
}

.card-header {
  padding: 1.5rem;
  border-bottom: 0.0625rem solid #f1f3f4;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.category-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.category-title h3 {
  margin: 0;
  color: #2c3e50;
  font-size: 1.2rem;
  font-weight: 600;
}

.category-color {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  border: 0.125rem solid white;
  box-shadow: 0 0.0625rem 0.1875rem rgba(0,0,0,0.3);
  flex-shrink: 0;
}

.card-actions {
  display: flex;
  gap: 0.375rem;
  opacity: 1;
  transition: opacity 0.2s;
}

.btn-icon {
  background: rgba(255, 255, 255, 0.95);
  border: 0.0625rem solid rgba(0, 0, 0, 0.15);
  padding: 0.4rem;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.2s;
  min-width: 1.75rem;
  min-height: 1.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0.0625rem 0.125rem rgba(0, 0, 0, 0.1);
}

.btn-edit {
  background: rgba(52, 152, 219, 0.15);
  border-color: rgba(52, 152, 219, 0.4);
  color: #2980b9;
}

.btn-edit:hover {
  background: rgba(52, 152, 219, 0.25);
  border-color: rgba(52, 152, 219, 0.6);
  color: #1e6091;
  transform: translateY(-0.03125rem);
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.15);
}

.btn-delete {
  background: rgba(231, 76, 60, 0.15);
  border-color: rgba(231, 76, 60, 0.4);
  color: #c0392b;
}

.btn-delete:hover:not(:disabled) {
  background: rgba(231, 76, 60, 0.25);
  border-color: rgba(231, 76, 60, 0.6);
  color: #a93226;
  transform: translateY(-0.03125rem);
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.15);
}

.btn-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.card-body {
  padding: 1rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.dataset-info {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  color: #7f8c8d;
  padding: 0.4rem 0.8rem;
  background: #f8f9fa;
  border-radius: 0.25rem;
  width: fit-content;
}

.dataset-info i {
  color: #667eea;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.dataset-name {
  font-weight: 500;
  color: #667eea;
}

.annotation-count {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
}

.annotation-count i {
  color: #3498db;
}

.no-annotations {
  color: #6c757d;
  font-style: italic;
}



/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1.2rem;
  border: none;
  border-radius: 0.375rem;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2980b9;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Modals */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: white;
  border-radius: 0.75rem;
  max-width: 31.25rem;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 0.25rem 1.25rem rgba(0,0,0,0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 0.0625rem solid #e1e5e9;
}

.modal-header h2 {
  margin: 0;
  color: #2c3e50;
  font-size: 1.3rem;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: #6c757d;
  padding: 0.5rem;
  border-radius: 0.25rem;
}

.btn-close:hover {
  background: #f8f9fa;
  color: #2c3e50;
}

.modal-body {
  padding: 1.5rem;
}

.modal-footer {
  padding: 1.5rem;
  border-top: 0.0625rem solid #e1e5e9;
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

/* Forms */
.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #2c3e50;
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  border: 0.0625rem solid #ddd;
  border-radius: 0.375rem;
  font-size: 0.95rem;
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 0.125rem rgba(52, 152, 219, 0.2);
}

.form-input.error {
  border-color: #e74c3c;
}

.color-input-group {
  display: flex;
  gap: 0.75rem;
}

.form-color {
  width: 3.75rem;
  height: 2.8125rem;
  border: 0.0625rem solid #ddd;
  border-radius: 0.375rem;
  cursor: pointer;
}

.color-text {
  flex: 1;
}

.error-message {
  color: #e74c3c;
  font-size: 0.85rem;
  margin-top: 0.25rem;
  display: block;
}

/* Responsive */
@media (max-width: 48em) {
  .header-content {
    flex-direction: column;
    align-items: stretch;
    text-align: center;
  }
  
  .header-actions {
    justify-content: center;
  }
  
  .categories-grid {
    grid-template-columns: 1fr;
  }
  
  .card-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }
  
  .card-actions {
    align-self: flex-end;
  }
}
</style>