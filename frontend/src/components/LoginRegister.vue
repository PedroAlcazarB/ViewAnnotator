<template>
  <div class="auth-container">
    <div class="auth-panel">
      <div class="auth-left">
        <h1 class="auth-title">VISILAB Annotator</h1>
        <p class="auth-description">
          VISILAB Annotator es una herramienta de anotación de imágenes basada en web 
          diseñada para versatilidad y eficiencia en el etiquetado de imágenes para crear 
          datos de entrenamiento para localización de imágenes y detección de objetos.
        </p>
        <p class="auth-hint">Inicia sesión para crear datasets</p>
      </div>

      <div class="auth-right">
        <div class="auth-tabs">
          <button 
            :class="['tab', { active: activeTab === 'login' }]" 
            @click="activeTab = 'login'"
          >
            Iniciar Sesión
          </button>
          <button 
            :class="['tab', { active: activeTab === 'register' }]" 
            @click="activeTab = 'register'"
          >
            Registrarse
          </button>
        </div>

        <!-- Login Form -->
        <form v-if="activeTab === 'login'" @submit.prevent="handleLogin" class="auth-form">
          <div v-if="error" class="error-message">
            {{ error }}
          </div>

          <div class="form-group">
            <label for="login-username">Nombre de Usuario</label>
            <input
              id="login-username"
              v-model="loginForm.username"
              type="text"
              placeholder="Ingresa tu usuario"
              required
            />
          </div>

          <div class="form-group">
            <label for="login-password">Contraseña</label>
            <input
              id="login-password"
              v-model="loginForm.password"
              type="password"
              placeholder="Ingresa tu contraseña"
              required
            />
          </div>

          <button type="submit" class="btn-primary" :disabled="loading">
            {{ loading ? 'Iniciando sesión...' : 'Iniciar Sesión' }}
          </button>
        </form>

        <!-- Register Form -->
        <form v-if="activeTab === 'register'" @submit.prevent="handleRegister" class="auth-form">
          <div v-if="error" class="error-message">
            {{ error }}
          </div>

          <div class="form-group">
            <label for="register-fullname">
              Nombre Completo <span class="optional">(Opcional)</span>
            </label>
            <input
              id="register-fullname"
              v-model="registerForm.fullName"
              type="text"
              placeholder="Tu nombre completo"
            />
          </div>

          <div class="form-group">
            <label for="register-username">Nombre de Usuario</label>
            <input
              id="register-username"
              v-model="registerForm.username"
              type="text"
              placeholder="Elige un nombre de usuario"
              required
            />
          </div>

          <div class="form-group">
            <label for="register-password">Contraseña</label>
            <input
              id="register-password"
              v-model="registerForm.password"
              type="password"
              placeholder="Elige una contraseña"
              required
            />
          </div>

          <div class="form-group">
            <label for="register-confirm-password">Confirmar Contraseña</label>
            <input
              id="register-confirm-password"
              v-model="registerForm.confirmPassword"
              type="password"
              placeholder="Confirma tu contraseña"
              required
            />
          </div>

          <button type="submit" class="btn-primary" :disabled="loading">
            {{ loading ? 'Registrando...' : 'Registrarse' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/authStore'

const authStore = useAuthStore()

const activeTab = ref('login')
const loading = ref(false)
const error = ref(null)

const loginForm = ref({
  username: '',
  password: ''
})

const registerForm = ref({
  fullName: '',
  username: '',
  password: '',
  confirmPassword: ''
})

const handleLogin = async () => {
  error.value = null
  loading.value = true

  try {
    const result = await authStore.login(loginForm.value.username, loginForm.value.password)
    
    if (result.success) {
      // Redirigir después de login exitoso
      window.location.reload() // Recargar para actualizar la app
    } else {
      error.value = result.error
    }
  } catch (err) {
    error.value = 'Error al iniciar sesión'
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  error.value = null

  // Validar contraseñas
  if (registerForm.value.password !== registerForm.value.confirmPassword) {
    error.value = 'Las contraseñas no coinciden'
    return
  }

  if (registerForm.value.password.length < 6) {
    error.value = 'La contraseña debe tener al menos 6 caracteres'
    return
  }

  if (registerForm.value.username.length < 3) {
    error.value = 'El nombre de usuario debe tener al menos 3 caracteres'
    return
  }

  loading.value = true

  try {
    const result = await authStore.register(
      registerForm.value.username,
      registerForm.value.password,
      registerForm.value.fullName
    )
    
    if (result.success) {
      // Redirigir después de registro exitoso
      window.location.reload() // Recargar para actualizar la app
    } else {
      error.value = result.error
    }
  } catch (err) {
    error.value = 'Error al registrar usuario'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem;
}

.auth-panel {
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 1.25rem 3.75rem rgba(0, 0, 0, 0.3);
  display: flex;
  max-width: 56.25rem;
  width: 100%;
  overflow: hidden;
}

.auth-left {
  flex: 1;
  padding: 3rem;
  background: #f8f9fa;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.auth-title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 1rem;
  color: #2c3e50;
}

.auth-description {
  color: #5a6c7d;
  line-height: 1.6;
  margin-bottom: 1.5rem;
}

.auth-hint {
  color: #2c3e50;
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.auth-link {
  color: #5a6c7d;
  font-size: 0.9rem;
}

.github-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
}

.github-link:hover {
  text-decoration: underline;
}

.auth-right {
  flex: 1;
  padding: 3rem;
  background: white;
}

.auth-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 2rem;
  border-bottom: 0.125rem solid #e1e5e9;
}

.tab {
  flex: 1;
  padding: 1rem;
  background: none;
  border: none;
  font-size: 1rem;
  font-weight: 500;
  color: #5a6c7d;
  cursor: pointer;
  transition: all 0.3s;
  border-bottom: 0.1875rem solid transparent;
  margin-bottom: -0.125rem;
}

.tab:hover {
  color: #667eea;
}

.tab.active {
  color: #667eea;
  border-bottom-color: #667eea;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.error-message {
  background: #fee;
  border: 0.0625rem solid #fcc;
  color: #c33;
  padding: 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.9rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  color: #2c3e50;
  font-size: 0.9rem;
}

.optional {
  color: #8898aa;
  font-weight: 400;
}

.form-group input {
  padding: 0.75rem;
  border: 0.125rem solid #e1e5e9;
  border-radius: 0.375rem;
  font-size: 1rem;
  transition: border-color 0.3s;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
}

.btn-primary {
  padding: 0.875rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.375rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.3s;
  margin-top: 0.5rem;
}

.btn-primary:hover:not(:disabled) {
  background: #5568d3;
}

.btn-primary:disabled {
  background: #8898aa;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 48em) {
  .auth-panel {
    flex-direction: column;
  }

  .auth-left {
    padding: 2rem;
  }

  .auth-right {
    padding: 2rem;
  }

  .auth-title {
    font-size: 1.5rem;
  }
}
</style>
