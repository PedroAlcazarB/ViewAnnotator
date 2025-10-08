<template>
  <div class="dataset-manager">
    <div class="header">
      <h1>Datasets</h1>
      <p class="subtitle">{{ datasets.length }} datasets cargados.</p>
      
      <div class="actions">
        <button @click="showCreateModal = true" class="btn btn-success">
          Crear
        </button>
        <button @click="refreshDatasets" class="btn btn-secondary">
          Actualizar
        </button>
      </div>
    </div>

    <!-- Lista de datasets -->
    <div class="dataset-grid">
      <div 
        v-for="dataset in datasets" 
        :key="dataset._id" 
        class="dataset-card"
        @click="selectDataset(dataset)"
      >
        <div class="dataset-icon">
          <i class="fas fa-folder"></i>
        </div>
        <div class="dataset-info">
          <h3>{{ dataset.name }}</h3>
          <p class="image-count">{{ dataset.image_count || 0 }} imágenes en el dataset</p>
          <p class="creator">Creado por {{ dataset.created_by || 'usuario' }}</p>
        </div>
        <div class="dataset-actions">
          <button @click.stop="deleteDataset(dataset)" class="btn-icon">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal para crear dataset -->
    <div v-if="showCreateModal" class="modal-overlay" @click="showCreateModal = false">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>Creando un Dataset</h2>
          <button @click="showCreateModal = false" class="close-btn">&times;</button>
        </div>
        
        <div class="modal-body">
          <div class="form-group">
            <label>Nombre del Dataset</label>
            <input 
              v-model="newDataset.name" 
              type="text" 
              placeholder="Nombre del dataset"
              :class="{ 'error': !newDataset.name && showError }"
            />
            <span v-if="!newDataset.name && showError" class="error-text">
              El nombre del dataset es requerido
            </span>
          </div>
          
          <div class="form-group">
            <label>Categorías por Defecto</label>
            <div class="categories-input">
              <span v-for="(category, index) in newDataset.categories" :key="index" class="category-tag">
                {{ category }}
                <button @click="removeCategory(index)" type="button">&times;</button>
              </span>
              <input 
                v-model="categoryInput" 
                @keydown.enter.prevent="addCategory"
                type="text" 
                placeholder="Agregar una categoría"
              />
            </div>
          </div>
          
          <div class="form-group">
            <label>Directorio de Carpeta</label>
            <input 
              v-model="newDataset.folder_path" 
              type="text" 
              readonly
              class="readonly"
            />
          </div>
        </div>
        
        <div class="modal-footer">
          <button @click="showCreateModal = false" class="btn btn-secondary">
            Close
          </button>
          <button @click="createDataset" class="btn btn-primary">
            Create Dataset
          </button>
        </div>
      </div>
    </div>

    <!-- Loading overlay -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>{{ loadingMessage }}</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DatasetManager',
  data() {
    return {
      datasets: [],
      showCreateModal: false,
      showError: false,
      loading: false,
      loadingMessage: '',
      newDataset: {
        name: '',
        description: '',
        folder_path: '/images/',
        categories: ['persona', 'vehiculo', 'objeto']
      },
      categoryInput: ''
    }
  },
  mounted() {
    this.loadDatasets()
  },
  watch: {
    'newDataset.name'(newName) {
      this.newDataset.folder_path = `/images/${newName || ''}`
    }
  },
  methods: {
    async loadDatasets() {
      try {
        this.loading = true
        this.loadingMessage = 'Loading datasets...'
        
        const response = await fetch('http://localhost:5000/api/datasets')
        const data = await response.json()
        
        if (response.ok) {
          this.datasets = data.datasets || []
        } else {
          console.error('Error loading datasets:', data.error)
        }
      } catch (error) {
        console.error('Error loading datasets:', error)
      } finally {
        this.loading = false
      }
    },
    
    async createDataset() {
      if (!this.newDataset.name.trim()) {
        this.showError = true
        return
      }
      
      try {
        this.loading = true
        this.loadingMessage = 'Creating dataset...'
        
        const response = await fetch('http://localhost:5000/api/datasets', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(this.newDataset)
        })
        
        const data = await response.json()
        
        if (response.ok) {
          this.showCreateModal = false
          this.resetForm()
          await this.loadDatasets()
        } else {
          alert('Error creating dataset: ' + data.error)
        }
      } catch (error) {
        console.error('Error creating dataset:', error)
        alert('Error creating dataset')
      } finally {
        this.loading = false
      }
    },
    
    async deleteDataset(dataset) {
      if (!confirm(`¿Estás seguro de que quieres eliminar el dataset "${dataset.name}"?`)) {
        return
      }
      
      try {
        this.loading = true
        this.loadingMessage = 'Deleting dataset...'
        
        const response = await fetch(`http://localhost:5000/api/datasets/${dataset._id}`, {
          method: 'DELETE'
        })
        
        if (response.ok) {
          await this.loadDatasets()
        } else {
          const data = await response.json()
          alert('Error deleting dataset: ' + data.error)
        }
      } catch (error) {
        console.error('Error deleting dataset:', error)
        alert('Error deleting dataset')
      } finally {
        this.loading = false
      }
    },
    
    selectDataset(dataset) {
      this.$emit('dataset-selected', dataset)
    },
    
    refreshDatasets() {
      this.loadDatasets()
    },
    
    addCategory() {
      if (this.categoryInput.trim() && !this.newDataset.categories.includes(this.categoryInput.trim())) {
        this.newDataset.categories.push(this.categoryInput.trim())
        this.categoryInput = ''
      }
    },
    
    removeCategory(index) {
      this.newDataset.categories.splice(index, 1)
    },
    
    resetForm() {
      this.newDataset = {
        name: '',
        description: '',
        folder_path: '/datasets/',
        categories: ['persona', 'vehiculo', 'objeto']
      }
      this.categoryInput = ''
      this.showError = false
    }
  }
}
</script>

<style scoped>
.dataset-manager {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h1 {
  font-size: 2.5rem;
  color: #333;
  margin-bottom: 10px;
}

.subtitle {
  color: #666;
  font-size: 1.1rem;
  margin-bottom: 20px;
}

.actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-bottom: 30px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.btn-success {
  background-color: #28a745;
  color: white;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.dataset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.dataset-card {
  background: white;
  border-radius: 10px;
  border: 1px solid #e0e0e0;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.dataset-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  transform: translateY(-2px);
}

.dataset-icon {
  text-align: center;
  margin-bottom: 15px;
}

.dataset-icon i {
  font-size: 3rem;
  color: #ccc;
}

.dataset-info h3 {
  font-size: 1.3rem;
  color: #333;
  margin-bottom: 8px;
}

.image-count {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 5px;
}

.creator {
  color: #999;
  font-size: 0.8rem;
}

.dataset-actions {
  position: absolute;
  top: 10px;
  right: 10px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.dataset-card:hover .dataset-actions {
  opacity: 1;
}

.btn-icon {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #dc3545;
  border-radius: 4px;
  cursor: pointer;
  padding: 8px;
  color: #dc3545;
  font-size: 12px;
  transition: all 0.2s ease;
}

.btn-icon:hover {
  background: #dc3545;
  color: white;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 10px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h2 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #333;
}

.form-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 14px;
}

.form-group input.error {
  border-color: #dc3545;
}

.form-group input.readonly {
  background-color: #f8f9fa;
  color: #6c757d;
}

.error-text {
  color: #dc3545;
  font-size: 12px;
  margin-top: 5px;
}

.categories-input {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  padding: 5px;
  border: 1px solid #ddd;
  border-radius: 5px;
  min-height: 40px;
  align-items: center;
}

.category-tag {
  background-color: #e9ecef;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.category-tag button {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: #6c757d;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #e0e0e0;
}

/* Loading Overlay */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255,255,255,0.9);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>