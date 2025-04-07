<template>
  <div id="app">
    <h1>{{ message }}</h1>
  </div>
</template>

<script>
export default {
  data() {
    return {
      message: "Loading..."
    };
  },
  async mounted() {
    try {
      const response = await fetch("http://localhost:5000/api/message");
      const data = await response.json();
      this.message = data.message;
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  }
};
</script>