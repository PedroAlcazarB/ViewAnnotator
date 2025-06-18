<template>
  <div id="app">
    <header class="app-header">
      <h1>VISILAB Annotator</h1>
      <nav>
        <router-link to="/">Inicio</router-link>
        <router-link to="/projects">Anotador</router-link>
      </nav>
    </header>
    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { RouterView } from 'vue-router'
</script>

<style>
#app {
  font-family: 'Segoe UI', 'Roboto', sans-serif;
  min-height: 100vh;
  background: #f4f6f8;
  display: flex;
  flex-direction: column;
}
.app-header {
  background: #2c3e50;
  color: #fff;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
nav a {
  color: #fff;
  margin-left: 1rem;
  text-decoration: none;
  font-weight: 500;
}
nav a.router-link-active {
  text-decoration: underline;
}
main {
  flex: 1;
  padding: 1rem 0;
}
</style>
