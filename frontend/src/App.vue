<template>
  <div id="app">
    <!-- Pantalla de bienvenida -->
    <div v-if="currentView === 'welcome'" class="welcome-screen">
      <!-- Si NO está autenticado, mostrar Login/Register -->
      <LoginRegister v-if="!authStore.isAuthenticated" />
      
      <!-- Si está autenticado, mostrar bienvenida -->
      <template v-else>
        <header class="welcome-header">
          <h1>VISILAB Annotator</h1>
          <nav>
            <a href="#" class="nav-link active">Inicio</a>
            <a href="#" class="nav-link" @click="goToDatasets">Anotador</a>
            <a href="#" class="nav-link" @click="goToModels">Modelos</a>
            <a href="#" class="nav-link" @click="goToCategories">Categorías</a>
          </nav>
          <div class="user-menu">
            <span class="username">{{ authStore.user?.username }}</span>
            <button @click="handleLogout" class="btn-logout">Cerrar sesión</button>
          </div>
        </header>
        
        <div class="welcome-content">
          <h2>Bienvenido a VISILAB Annotator</h2>
          <p class="welcome-user">
            Hola, <strong>{{ authStore.user?.username}}</strong>!
          </p>
            <p>Anota imágenes y videos con bounding boxes, importa/exporta en múltiples formatos y utiliza modelos de IA para anotación automática.</p>
          <button @click="goToDatasets" class="btn btn-primary">
            Ir al anotador
          </button>
        </div>
      </template>
    </div>

    <!-- Gestión de datasets -->
    <div v-else-if="currentView === 'datasets'" class="datasets-screen">
      <header class="app-header">
        <h1>VISILAB Annotator</h1>
        <nav>
          <a href="#" class="nav-link" @click="goToWelcome">Inicio</a>
          <a href="#" class="nav-link active">Anotador</a>
          <a href="#" class="nav-link" @click="goToModels">Modelos</a>
          <a href="#" class="nav-link" @click="goToCategories">Categorías</a>
        </nav>
        <div class="user-menu">
          <span class="username">{{ authStore.user?.username }}</span>
          <button @click="handleLogout" class="btn-logout">Cerrar sesión</button>
        </div>
      </header>
      
      <DatasetManager @dataset-selected="selectDataset" />
    </div>

    <!-- Gestión de modelos de IA -->
    <div v-else-if="currentView === 'models'" class="models-screen">
      <header class="app-header">
        <h1>VISILAB Annotator</h1>
        <nav>
          <a href="#" class="nav-link" @click="goToWelcome">Inicio</a>
          <a href="#" class="nav-link" @click="goToDatasets">Anotador</a>
          <a href="#" class="nav-link active">Modelos</a>
          <a href="#" class="nav-link" @click="goToCategories">Categorías</a>
        </nav>
        <div class="user-menu">
          <span class="username">{{ authStore.user?.username }}</span>
          <button @click="handleLogout" class="btn-logout">Cerrar sesión</button>
        </div>
      </header>
      
      <ModelsView />
    </div>

    <!-- Gestión de categorías -->
    <div v-else-if="currentView === 'categories'" class="categories-screen">
      <header class="app-header">
        <h1>VISILAB Annotator</h1>
        <nav>
          <a href="#" class="nav-link" @click="goToWelcome">Inicio</a>
          <a href="#" class="nav-link" @click="goToDatasets">Anotador</a>
          <a href="#" class="nav-link" @click="goToModels">Modelos</a>
          <a href="#" class="nav-link active">Categorías</a>
        </nav>
        <div class="user-menu">
          <span class="username">{{ authStore.user?.username }}</span>
          <button @click="handleLogout" class="btn-logout">Cerrar sesión</button>
        </div>
      </header>
      
      <CategoriesView />
    </div>

    <!-- Vista individual de dataset -->
    <div v-else-if="currentView === 'dataset'" class="dataset-screen">
      <DatasetView 
        :dataset="selectedDataset" 
        @go-back="goToDatasets"
      />
    </div>
  </div>
</template>

<script>
import { useAuthStore } from './stores/authStore'
import LoginRegister from './components/LoginRegister.vue'
import DatasetManager from './components/DatasetManager.vue'
import DatasetView from './views/DatasetView.vue'
import ModelsView from './views/ModelsView.vue'
import CategoriesView from './views/CategoriesView.vue'

export default {
  name: 'App',
  components: {
    LoginRegister,
    DatasetManager,
    DatasetView,
    ModelsView,
    CategoriesView
  },
  data() {
    return {
      currentView: 'welcome', // 'welcome', 'datasets', 'dataset', 'models', 'categories'
      selectedDataset: null,
      authStore: useAuthStore()
    }
  },
  async mounted() {
    // Inicializar autenticación al cargar la app
    await this.authStore.init()
  },
  methods: {
    checkAuth() {
      if (!this.authStore.isAuthenticated) {
        this.currentView = 'welcome'
        return false
      }
      return true
    },
    
    goToWelcome() {
      this.currentView = 'welcome'
      this.selectedDataset = null
    },
    
    goToDatasets() {
      if (!this.checkAuth()) return
      this.currentView = 'datasets'
      this.selectedDataset = null
    },
    
    goToModels() {
      if (!this.checkAuth()) return
      this.currentView = 'models'
      this.selectedDataset = null
    },
    
    goToCategories() {
      if (!this.checkAuth()) return
      this.currentView = 'categories'
      this.selectedDataset = null
    },
    
    selectDataset(dataset) {
      if (!this.checkAuth()) return
      this.selectedDataset = dataset
      this.currentView = 'dataset'
    },
    
    handleLogout() {
      this.authStore.logout()
      this.currentView = 'welcome'
      this.selectedDataset = null
    }
  }
}
</script>

<style>
/* Reset básico */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  color: #2c3e50;
  min-height: 100vh;
}

/* Estilo del header */
.app-header, .welcome-header {
  background: #ffffff;
  border-bottom: 0.0625rem solid #e1e5e9;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.1);
  gap: 2rem;
}

.app-header h1, .welcome-header h1 {
  color: #2c3e50;
  font-size: 1.5rem;
  font-weight: 600;
  flex-shrink: 0;
}

nav {
  display: flex;
  gap: 2rem;
  flex: 1;
}

.nav-link {
  color: #64748b;
  text-decoration: none;
  font-weight: 500;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  transition: all 0.2s;
}

.nav-link:hover {
  color: #0f172a;
  background: #f1f5f9;
}

.nav-link.active {
  color: #0ea5e9;
  background: #e0f2fe;
}

/* Menú de usuario */
.user-menu {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-shrink: 0;
}

.username {
  color: #2c3e50;
  font-weight: 500;
  font-size: 0.9rem;
  padding: 0.5rem;
}

.btn-logout {
  padding: 0.5rem 1rem;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 0.375rem;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-logout:hover {
  background: #dc2626;
}

/* Pantalla de bienvenida */
.welcome-screen {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.welcome-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 5rem);
  text-align: center;
  color: white;
  padding: 2rem;
}

.welcome-content h2 {
  font-size: 3rem;
  margin-bottom: 1rem;
  font-weight: 700;
}

.welcome-user {
  color: #fff;
  font-size: 1.4rem;
  margin-bottom: 1rem;
  font-weight: 500;
}

.welcome-user strong {
  color: #fbbf24;
  font-weight: 700;
}

.welcome-content p {
  font-size: 1.2rem;
  margin-bottom: 2rem;
  opacity: 0.9;
  max-width: 37.5rem;
}

/* Estilos para pantallas con header */
.datasets-screen, .dataset-screen {
  min-height: 100vh;
  background: #f8fafc;
}

/* Botones */
.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 1rem;
  text-decoration: none;
  display: inline-block;
}

.btn-primary {
  background: #0ea5e9;
  color: white;
}

.btn-primary:hover {
  background: #0284c7;
  transform: translateY(-0.0625rem);
  box-shadow: 0 0.25rem 0.75rem rgba(14, 165, 233, 0.3);
}

/* Responsive */
@media (max-width: 48em) {
  .app-header, .welcome-header {
    padding: 1rem;
    flex-direction: column;
    gap: 1rem;
  }
  
  .welcome-content h2 {
    font-size: 2rem;
  }
  
  nav {
    gap: 1rem;
  }
}
</style>
