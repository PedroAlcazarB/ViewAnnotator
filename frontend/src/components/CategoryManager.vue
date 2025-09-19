<template>
  <div class="categories-manager">
    <div class="categories-header">
      <h3>Gestión de Categorías</h3>
      <button @click="showAddForm = !showAddForm" class="btn-primary">
        {{ showAddForm ? 'Cancelar' : '+ Nueva Categoría' }}
      </button>
    </div>

    <!-- Formulario para añadir nueva categoría -->
    <div v-if="showAddForm" class="add-category-form">
      <div class="form-group">
        <label for="categoryName">Nombre de la categoría:</label>
        <input 
          id="categoryName"
          v-model="newCategory.name" 
          type="text" 
          placeholder="Ej: Persona, Vehículo, Animal..."
          class="form-input"
          @keyup.enter="addCategory"
        >
      </div>
      <div class="form-group">
        <label for="categoryColor">Color:</label>
        <input 
          id="categoryColor"
          v-model="newCategory.color" 
          type="color" 
          class="form-color"
        >
      </div>
      <div class="form-actions">
        <button @click="addCategory" class="btn-success" :disabled="!newCategory.name.trim()">
          Añadir Categoría
        </button>
        <button @click="cancelAdd" class="btn-secondary">
          Cancelar
        </button>
      </div>
    </div>

    <!-- Lista de categorías existentes -->
    <div class="categories-list">
      <div 
        v-for="category in categories" 
        :key="category.id" 
        class="category-item"
        :class="{ 'active': selectedCategory === category.id }"
        @click="selectCategory(category.id)"
      >
        <div class="category-info">
          <div 
            class="category-color" 
            :style="{ backgroundColor: category.color }"
          ></div>
          <span class="category-name">{{ category.name }}</span>
          <span class="category-count">({{ getCategoryAnnotationCount(category.id) }})</span>
        </div>
        <div class="category-actions">
          <button 
            @click.stop="editCategory(category)" 
            class="btn-edit"
            title="Editar categoría"
          >
            ✏️
          </button>
          <button 
            @click.stop="deleteCategory(category.id)" 
            class="btn-delete"
            title="Eliminar categoría"
            v-if="category.id !== 1"
          >
            🗑️
          </button>
        </div>
      </div>
    </div>

    <!-- Modal de edición -->
    <div v-if="editingCategory" class="modal-overlay" @click="cancelEdit">
      <div class="modal-content" @click.stop>
        <h4>Editar Categoría</h4>
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
        <div class="form-actions">
          <button @click="saveEdit" class="btn-success">Guardar</button>
          <button @click="cancelEdit" class="btn-secondary">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Categoría seleccionada actual -->
    <div class="current-selection" v-if="selectedCategoryInfo">
      <p>
        <strong>Categoría:</strong> 
        <span class="selected-category">
          <span 
            class="category-color small" 
            :style="{ backgroundColor: selectedCategoryInfo.color }"
          ></span>
          {{ selectedCategoryInfo.name }}
        </span>
      </p>
      <p class="help-text">Las nuevas anotaciones se asignarán a esta categoría</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAnnotationStore } from '../stores/annotationStore'

const store = useAnnotationStore()

const showAddForm = ref(false)
const editingCategory = ref(null)
const newCategory = ref({
  name: '',
  color: '#ff0000'
})

const categories = computed(() => store.categories)
const selectedCategory = computed(() => store.selectedCategory)
const annotations = computed(() => store.annotations)

const selectedCategoryInfo = computed(() => {
  return categories.value.find(cat => cat.id === selectedCategory.value)
})

function addCategory() {
  if (!newCategory.value.name.trim()) return
  
  store.addCategory({
    name: newCategory.value.name.trim(),
    color: newCategory.value.color
  })
  
  cancelAdd()
}

function cancelAdd() {
  showAddForm.value = false
  newCategory.value = {
    name: '',
    color: '#ff0000'
  }
}

function selectCategory(categoryId) {
  store.setSelectedCategory(categoryId)
}

function editCategory(category) {
  editingCategory.value = { ...category }
}

function saveEdit() {
  if (editingCategory.value) {
    store.updateCategory(editingCategory.value)
    editingCategory.value = null
  }
}

function cancelEdit() {
  editingCategory.value = null
}

function deleteCategory(categoryId) {
  if (confirm('¿Estás seguro de que quieres eliminar esta categoría? Las anotaciones asociadas se mantendrán pero perderán la categoría.')) {
    store.deleteCategory(categoryId)
  }
}

function getCategoryAnnotationCount(categoryId) {
  return annotations.value.filter(ann => ann.category_id === categoryId).length
}
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
}

.btn-primary {
  background: #3498db;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #2980b9;
}

.add-category-form {
  background: white;
  border-radius: 6px;
  padding: 1rem;
  margin-bottom: 1rem;
  border: 1px solid #e1e5e9;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #2c3e50;
}

.form-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
}

.form-color {
  width: 60px;
  height: 40px;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
}

.form-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-success {
  background: #27ae60;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
}

.btn-success:hover {
  background: #229954;
}

.btn-success:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #95a5a6;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
}

.btn-secondary:hover {
  background: #7f8c8d;
}

.categories-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.category-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  border: 2px solid transparent;
  border-radius: 6px;
  padding: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.category-item:hover {
  border-color: #3498db;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.category-item.active {
  border-color: #27ae60;
  background: #f8fff9;
}

.category-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.category-color {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.category-color.small {
  width: 16px;
  height: 16px;
}

.category-name {
  font-weight: 500;
  color: #2c3e50;
}

.category-count {
  color: #7f8c8d;
  font-size: 0.9rem;
}

.category-actions {
  display: flex;
  gap: 0.25rem;
}

.btn-edit, .btn-delete {
  background: none;
  border: none;
  padding: 0.25rem;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.btn-edit:hover {
  background: #f39c12;
}

.btn-delete:hover {
  background: #e74c3c;
}

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
}

.modal-content {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  min-width: 300px;
  max-width: 500px;
}

.modal-content h4 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
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
</style>