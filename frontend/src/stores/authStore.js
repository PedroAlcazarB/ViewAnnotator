import { defineStore } from 'pinia'

// Usar rutas relativas para que funcionen a través del proxy de Nginx
const API_BASE_URL = ''

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: null,
    isAuthenticated: false,
    loading: false,
    error: null,
    isInitialized: false
  }),

  actions: {
    // Inicializar autenticación desde localStorage
    async init() {
      if (this.isInitialized) {
        return
      }

      const token = localStorage.getItem('auth_token')
      const user = localStorage.getItem('auth_user')
      
      if (token && user) {
        this.token = token
        this.user = JSON.parse(user)
        this.isAuthenticated = true
        
        // Verificar que el token sigue siendo válido
        await this.verifyToken()
      }
      this.isInitialized = true
    },

    // Registrar nuevo usuario
    async register(username, password, fullName = '') {
      this.loading = true
      this.error = null

      try {
        const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: username,
            password: password,
            full_name: fullName
          })
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.error || 'Error al registrar usuario')
        }

        // Guardar token y usuario
        this.token = data.token
        this.user = data.user
        this.isAuthenticated = true
        this.isInitialized = true

        // Guardar en localStorage
        localStorage.setItem('auth_token', data.token)
        localStorage.setItem('auth_user', JSON.stringify(data.user))

        return { success: true }
      } catch (error) {
        this.error = error.message
        return { success: false, error: error.message }
      } finally {
        this.loading = false
      }
    },

    // Iniciar sesión
    async login(username, password) {
      this.loading = true
      this.error = null

      try {
        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: username,
            password: password
          })
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.error || 'Error al iniciar sesión')
        }

        // Guardar token y usuario
        this.token = data.token
        this.user = data.user
        this.isAuthenticated = true
        this.isInitialized = true

        // Guardar en localStorage
        localStorage.setItem('auth_token', data.token)
        localStorage.setItem('auth_user', JSON.stringify(data.user))

        return { success: true }
      } catch (error) {
        this.error = error.message
        return { success: false, error: error.message }
      } finally {
        this.loading = false
      }
    },

    // Verificar token
    async verifyToken() {
      if (!this.token) {
        this.logout()
        return false
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/auth/verify`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })

        if (!response.ok) {
          // Si el token es inválido, limpiar la sesión silenciosamente
          console.warn('Token inválido o expirado, limpiando sesión...')
          this.logout()
          return false
        }

        const data = await response.json()
        this.user = data.user
        this.isAuthenticated = true
        return true
      } catch (error) {
        console.error('Error verificando token:', error)
        this.logout()
        return false
      }
    },

    // Cerrar sesión
    logout() {
      this.user = null
      this.token = null
      this.isAuthenticated = false
      this.error = null
      this.isInitialized = true

      // Limpiar localStorage
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_user')
    },

    // Obtener headers de autorización para peticiones API
    getAuthHeaders() {
      if (this.token) {
        return {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        }
      }
      return {
        'Content-Type': 'application/json'
      }
    }
  }
})
