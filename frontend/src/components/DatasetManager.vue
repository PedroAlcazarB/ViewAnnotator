<template>
  <div class="dataset-manager">
    <div class="header">
      <h1>Datasets</h1>
      <p class="subtitle">{{ datasets.length }} datasets cargados.</p>
      
      <div class="actions">
        <button @click="showCreateModal = true" class="btn btn-success">
          <i class="fas fa-plus"></i> Crear
        </button>
        <button @click="refreshDatasets" class="btn btn-secondary">
          <i class="fas fa-sync-alt"></i> Actualizar
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
        <div class="card-header">
          <div class="dataset-icon">
            <i class="fas fa-folder"></i>
          </div>
          <div class="dataset-actions">
            <button @click.stop="deleteDataset(dataset)" class="btn-icon" title="Eliminar">
              <i class="fas fa-trash-alt"></i>
            </button>
          </div>
        </div>
        <div class="dataset-info">
          <h3 class="dataset-name">{{ dataset.name }}</h3>
          <div class="dataset-meta">
            <span class="meta-item">
              {{ dataset.file_count || 0 }} archivo{{ dataset.file_count !== 1 ? 's' : '' }}
            </span>
          </div>
          <p class="creator">Creado por {{ dataset.created_by }}</p>
        </div>
      </div>
    </div>

    <!-- Modal para crear dataset -->
    <div v-if="showCreateModal" class="modal-overlay" @click="closeModal" @keydown.esc="closeModal">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>Crear Nuevo Dataset</h2>
          <button @click="closeModal" class="close-btn" aria-label="Cerrar modal">&times;</button>
        </div>
        
        <div class="modal-body">
          <div class="form-group">
            <label for="dataset-name">Nombre del Dataset</label>
            <input 
              id="dataset-name"
              ref="datasetNameInput"
              v-model="newDataset.name" 
              type="text" 
              placeholder="Ej: Detección de vehículos"
              :class="{ 'error': !newDataset.name && showError }"
              @keydown.enter="createDataset"
              @keydown.esc="closeModal"
              autofocus
            />
            <span v-if="!newDataset.name && showError" class="error-text">
              ⚠️ El nombre del dataset es requerido
            </span>
          </div>
          
          <div class="form-group">
            <label>Directorio</label>
            <div class="folder-path-display">
              <span class="path-icon">📁</span>
              <span class="path-text">{{ newDataset.folder_path }}</span>
            </div>
            <p class="help-text">Los archivos se guardarán en este directorio automáticamente</p>
          </div>
        </div>
        
        <div class="modal-footer">
          <button 
            @click="createDataset" 
            class="btn btn-primary"
            :disabled="!newDataset.name.trim()"
            @keydown.enter="createDataset"
          >
            ✓ Crear Dataset
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
        folder_path: '/datasets/'
      }
    }
  },
  mounted() {
    this.loadDatasets()
    // Listener global para ESC
    document.addEventListener('keydown', this.handleGlobalKeydown)
  },
  beforeUnmount() {
    document.removeEventListener('keydown', this.handleGlobalKeydown)
  },
  watch: {
    'newDataset.name'(newName) {
      this.newDataset.folder_path = `/datasets/${newName || ''}`
    },
    showCreateModal(newVal) {
      if (newVal) {
        // Enfocar el input cuando se abre el modal
        this.$nextTick(() => {
          this.$refs.datasetNameInput?.focus()
        })
      }
    }
  },
  methods: {
    async loadDatasets() {
      try {
        this.loading = true
        this.loadingMessage = 'Cargando datasets...'
        
        const data = await this.$apiGet('/api/datasets')
        this.datasets = data.datasets || []
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
        this.loadingMessage = 'Creando dataset...'
        
        await this.$apiPost('/api/datasets', this.newDataset)
        this.closeModal()
        await this.loadDatasets()
        alert('✅ Dataset creado exitosamente')
      } catch (error) {
        console.error('Error creating dataset:', error)
        alert('❌ Error al crear dataset')
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
        this.loadingMessage = 'Eliminando dataset...'
        
        await this.$apiDelete(`/api/datasets/${dataset._id}`)
        await this.loadDatasets()
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
    
    closeModal() {
      this.showCreateModal = false
      this.resetForm()
    },
    
    handleGlobalKeydown(e) {
      if (e.key === 'Escape' && this.showCreateModal) {
        this.closeModal()
      }
    },
    
    resetForm() {
      this.newDataset = {
        name: '',
        description: '',
        folder_path: '/datasets/'
      }
      this.showError = false
    }
  }
}
</script>

<style scoped>
.dataset-manager {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  min-height: 100vh;
}

.header {
  text-align: center;
  margin-bottom: 2.5rem;
}

.header h1 {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 0.5rem;
  font-weight: 700;
}

.subtitle {
  color: #5a6c7d;
  font-size: 1rem;
  margin-bottom: 1.5rem;
  font-weight: 500;
}

.actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
  margin-top: 1.5rem;
}

.btn {
  padding: 0.6rem 1.5rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
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
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.dataset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1.25rem;
  margin-top: 2rem;
}

.dataset-card {
  background: white;
  border-radius: 12px;
  border: 2px solid #e1e8ed;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.dataset-card:hover {
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-4px);
  border-color: #007bff;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1rem 0.5rem 1rem;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
}

.dataset-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.dataset-icon i {
  font-size: 2.5rem;
  color: #007bff;
  opacity: 0.85;
}

.dataset-info {
  padding: 0.75rem 1rem 1rem 1rem;
}

.dataset-name {
  font-size: 1.1rem;
  color: #2c3e50;
  margin: 0 0 0.75rem 0;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dataset-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: #495057;
  font-size: 0.85rem;
  font-weight: 500;
  background: #f1f3f5;
  padding: 0.3rem 0.6rem;
  border-radius: 6px;
}

.meta-item i {
  color: #007bff;
  font-size: 13px;
}

.creator {
  color: #868e96;
  font-size: 0.75rem;
  margin: 0.5rem 0 0 0;
  font-weight: 500;
}

.dataset-actions {
  opacity: 0;
  transition: opacity 0.2s ease;
}

.dataset-card:hover .dataset-actions {
  opacity: 1;
}

.btn-icon {
  background: white;
  border: 1px solid #e1e8ed;
  border-radius: 6px;
  cursor: pointer;
  padding: 0.4rem 0.5rem;
  color: #dc3545;
  font-size: 13px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  background: #dc3545;
  color: white;
  border-color: #dc3545;
  transform: scale(1.05);
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 520px;
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { 
    opacity: 0;
    transform: translateY(20px);
  }
  to { 
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid #e5e7eb;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.modal-header h2 {
  margin: 0;
  color: white;
  font-size: 1.4rem;
  font-weight: 600;
}

.close-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: white;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

.modal-body {
  padding: 28px 24px;
  max-height: calc(90vh - 180px);
  overflow-y: auto;
}

.form-group {
  margin-bottom: 24px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #374151;
  font-size: 0.95rem;
}

.form-group input {
  width: 100%;
  padding: 12px 14px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 15px;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-group input.error {
  border-color: #ef4444;
  background-color: #fef2f2;
}

.form-group input.error:focus {
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.error-text {
  color: #ef4444;
  font-size: 13px;
  margin-top: 6px;
  display: block;
  font-weight: 500;
}

.folder-path-display {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  background: #f3f4f6;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  color: #374151;
}

.path-icon {
  font-size: 18px;
}

.path-text {
  flex: 1;
  overflow-x: auto;
  white-space: nowrap;
}

.help-text {
  margin-top: 8px;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.5;
}

.modal-footer {
  display: flex;
  justify-content: center;
  padding: 20px 24px;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}

.modal-footer .btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 12px 32px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 15px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  display: flex;
  align-items: center;
  gap: 8px;
}

.modal-footer .btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.modal-footer .btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.modal-footer .btn-primary:disabled {
  background: #d1d5db;
  cursor: not-allowed;
  box-shadow: none;
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