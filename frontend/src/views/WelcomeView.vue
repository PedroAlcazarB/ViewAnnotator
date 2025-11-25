<template>
  <div class="welcome-content">
    <h2>Bienvenido a VISILAB Annotator</h2>
    <p class="welcome-user">
      Hola, <strong>{{ username }}</strong>!
    </p>
    <p>
      Anota imágenes y videos con bounding boxes, importa/exporta en múltiples formatos y utiliza modelos de IA para anotación automática.
    </p>
    <button @click="goToDatasets" class="btn btn-primary">
      Ir al anotador
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'

const router = useRouter()
const authStore = useAuthStore()

const username = computed(() => authStore.user?.username || 'Usuario')

const goToDatasets = () => {
  router.push({ name: 'datasets' })
}
</script>
