<template>
  <div id="app">
    <div v-if="!authStore.isInitialized" class="app-initializing"></div>
    <div v-else-if="!authStore.isAuthenticated" class="welcome-screen">
      <LoginRegister />
    </div>
    <div v-else :class="containerClass">
      <header v-if="showHeader" :class="headerClass">
        <h1>VISILAB Annotator</h1>
        <nav>
          <RouterLink
            :to="{ name: 'welcome' }"
            class="nav-link"
            :class="{ active: route.name === 'welcome' }"
          >
            Inicio
          </RouterLink>
          <RouterLink
            :to="{ name: 'datasets' }"
            class="nav-link"
            :class="{ active: route.name === 'datasets' }"
          >
            Anotador
          </RouterLink>
          <RouterLink
            :to="{ name: 'models' }"
            class="nav-link"
            :class="{ active: route.name === 'models' }"
          >
            Modelos
          </RouterLink>
          <RouterLink
            :to="{ name: 'categories' }"
            class="nav-link"
            :class="{ active: route.name === 'categories' }"
          >
            Categorías
          </RouterLink>
        </nav>
        <div class="user-menu">
          <span class="username">{{ authStore.user?.username }}</span>
          <button @click="handleLogout" class="btn-logout">Cerrar sesión</button>
        </div>
      </header>
      <RouterView />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import LoginRegister from '@/components/LoginRegister.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

onMounted(async () => {
  await authStore.init()
})

const showHeader = computed(() => route.name !== 'dataset')

const containerClass = computed(() => {
  switch (route.name) {
    case 'welcome':
      return 'welcome-screen'
    case 'datasets':
      return 'datasets-screen'
    case 'models':
      return 'models-screen'
    case 'categories':
      return 'categories-screen'
    case 'dataset':
      return 'dataset-screen'
    default:
      return ''
  }
})

const headerClass = computed(() => (route.name === 'welcome' ? 'welcome-header' : 'app-header'))

const handleLogout = () => {
  authStore.logout()
  router.push({ name: 'welcome' })
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

.app-initializing {
  min-height: 100vh;
  background: #f8fafc;
}

/* Estilos para pantallas con header */
.datasets-screen, .dataset-screen, .models-screen, .categories-screen {
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
