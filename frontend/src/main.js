import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'

import HomeView from './views/HomeView.vue'
import ProjectView from './views/ProjectView.vue'

const app = createApp(App)

// Configuración de Pinia
const pinia = createPinia()
app.use(pinia)

// Configuración del router
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/projects', component: ProjectView },
    { path: '/projects/:id', component: ProjectView }
  ]
})
app.use(router)

app.mount('#app')