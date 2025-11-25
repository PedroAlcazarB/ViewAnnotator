import { createApp } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import App from './App.vue'
import VueKonva from 'vue-konva'
import { apiGet, apiPost, apiPut, apiDelete, apiFetch, apiPatch, API_BASE_URL } from './utils/api'
import { useAuthStore } from './stores/authStore'
import router from './router'

const app = createApp(App)
app.use(VueKonva)

// Configuración de Pinia
const pinia = createPinia()
app.use(pinia)
setActivePinia(pinia)

app.use(router)

const authStore = useAuthStore()

const originalFetch = window.fetch.bind(window)
window.fetch = async (input, init = {}) => {
  let url = typeof input === 'string' ? input : input?.url

  if (typeof url === 'string' && url.startsWith(API_BASE_URL)) {
    const options = { ...init }
    const headers = new Headers(init?.headers || {})

    if (!headers.has('Authorization') && authStore.token) {
      headers.set('Authorization', `Bearer ${authStore.token}`)
      console.log('[AUTH INTERCEPTOR] Token agregado a petición:', url)
    } else if (authStore.token) {
      console.log('[AUTH INTERCEPTOR] Header Authorization ya existe para:', url)
    } else {
      console.warn('[AUTH INTERCEPTOR] No hay token disponible para:', url)
    }

    if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }

    if (!headers.has('Accept')) {
      headers.set('Accept', 'application/json')
    }

    options.headers = headers

    const response = await originalFetch(url, options)

    if (response.status === 401) {
      console.error('[AUTH INTERCEPTOR] Sesión expirada (401) en:', url)
      authStore.logout()
      router.push({ name: 'welcome' })
      throw new Error('Sesión expirada. Por favor, inicia sesión nuevamente.')
    }

    console.log('[AUTH INTERCEPTOR] Petición exitosa a:', url, '- Status:', response.status)
    return response
  }

  return originalFetch(input, init)
}

authStore.init()

// Agregar helpers de API como propiedades globales (Options API)
app.config.globalProperties.$apiGet = apiGet
app.config.globalProperties.$apiPost = apiPost
app.config.globalProperties.$apiPut = apiPut
app.config.globalProperties.$apiDelete = apiDelete
app.config.globalProperties.$apiFetch = apiFetch
app.config.globalProperties.$apiPatch = apiPatch

// Exponer también en window para Composition API y uso general
window.$apiGet = apiGet
window.$apiPost = apiPost
window.$apiPut = apiPut
window.$apiDelete = apiDelete
window.apiFetch = apiFetch
window.$apiPatch = apiPatch

router.isReady().then(() => {
  app.mount('#app')
})