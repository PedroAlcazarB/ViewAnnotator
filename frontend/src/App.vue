<template>
  <div>
    <input type="file" @change="handleFileUpload" accept="image/*" />

    <div v-if="previewUrl" style="margin-top: 20px;">
      <h4>Imagen:</h4>
      <vue-panzoom style="display: inline-block; border: 1px solid #ccc; max-width: 400px;">
        <img :src="previewUrl" alt="Imagen cargada" style="max-width: 100%; display: block;" />
      </vue-panzoom>
      <p style="margin-top: 10px;">Usa la rueda del ratón para hacer zoom y arrastra para desplazarte.</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import VuePanZoom from 'vue-panzoom'

const previewUrl = ref(null)

const handleFileUpload = (event) => {
  const file = event.target.files[0]

  if (file) {
    previewUrl.value = URL.createObjectURL(file)
  } else {
    previewUrl.value = null
  }
}

</script>
