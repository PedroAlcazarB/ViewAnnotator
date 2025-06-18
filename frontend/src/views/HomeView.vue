<template>
  <div class="home-view">
    <div class="welcome-section">
      <h2>Bienvenido a VISILAB Annotator</h2>
      <p>Anota imágenes con bounding boxes y exporta en formato COCO.</p>
      <div class="actions">
        <router-link to="/projects" class="btn primary">
          Ir al anotador
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.home-view {
  max-width: 600px;
  margin: 3rem auto;
  padding: 2rem;
}
.welcome-section {
  text-align: center;
  background: #f9f9f9;
  border-radius: 8px;
  padding: 2rem;
}
.actions {
  margin-top: 2rem;
}
.btn {
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  text-decoration: none;
  font-weight: 500;
  color: white;
  background: #42b983;
  transition: background 0.2s;
}
.btn:hover {
  background: #369e6f;
}
</style>