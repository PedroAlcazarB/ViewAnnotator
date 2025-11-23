// Helper para hacer peticiones autenticadas a la API
import { useAuthStore } from '@/stores/authStore'

// Usar rutas relativas para que funcionen a través del proxy de Nginx
export const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || ''

function resolveUrl(endpoint) {
  if (typeof endpoint !== 'string') {
    throw new Error('El endpoint de la API debe ser un string')
  }

  if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
    return endpoint
  }

  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  return `${API_BASE_URL}${normalizedEndpoint}`
}

function buildHeaders(originalHeaders, hasBody) {
  const headers = new Headers(originalHeaders || {})
  const authStore = useAuthStore()

  if (authStore.token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${authStore.token}`)
    console.log('[API HELPER] Token agregado al header')
  } else if (!authStore.token) {
    console.warn('[API HELPER] No hay token disponible')
  }

  if (hasBody && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json')
  }

  return { headers, authStore }
}

async function handleResponse(response, authStore) {
  if (response.status === 401) {
    console.error('[API HELPER] Sesión expirada (401)')
    authStore.logout()
    window.location.href = '/'
    throw new Error('Sesión expirada. Por favor, inicia sesión nuevamente.')
  }

  const contentType = response.headers.get('Content-Type') || ''
  let payload = null

  if (contentType.includes('application/json')) {
    payload = await response.json().catch(() => null)
  } else {
    const text = await response.text().catch(() => '')
    payload = text || null
  }

  if (!response.ok) {
    const message = payload?.error || payload?.message || payload || `Error ${response.status}`
    console.error(`[API HELPER] Error ${response.status}:`, message)
    const error = new Error(message)
    error.status = response.status
    error.data = payload
    throw error
  }

  console.log('[API HELPER] Petición exitosa - Status:', response.status)
  return payload
}

/**
 * Realiza una petición fetch con autenticación automática
 * @param {string} endpoint - El endpoint de la API (ej: '/api/datasets')
 * @param {Object} options - Opciones de fetch (method, body, etc.)
 * @returns {Promise} - Respuesta del servidor
 */
export async function apiFetch(endpoint, options = {}) {
  const url = resolveUrl(endpoint)
  const isFormData = options.body instanceof FormData
  const hasBody = Boolean(options.body) && !isFormData

  console.log(`[API HELPER] ${options.method || 'GET'} ${url}`)

  const { headers, authStore } = buildHeaders(options.headers, hasBody)
  const fetchOptions = {
    ...options,
    headers
  }

  if (hasBody && typeof options.body !== 'string') {
    fetchOptions.body = JSON.stringify(options.body)
  }

  const response = await fetch(url, fetchOptions)
  return handleResponse(response, authStore)
}

/**
 * GET request helper
 */
export async function apiGet(endpoint) {
  return apiFetch(endpoint, { method: 'GET' })
}

/**
 * POST request helper
 */
export async function apiPost(endpoint, data) {
  return apiFetch(endpoint, {
    method: 'POST',
    body: data
  })
}

/**
 * PUT request helper
 */
export async function apiPut(endpoint, data) {
  return apiFetch(endpoint, {
    method: 'PUT',
    body: data
  })
}

/**
 * DELETE request helper
 */
export async function apiDelete(endpoint) {
  return apiFetch(endpoint, { method: 'DELETE' })
}

/**
 * PATCH request helper
 */
export async function apiPatch(endpoint, data) {
  return apiFetch(endpoint, {
    method: 'PATCH',
    body: data
  })
}
