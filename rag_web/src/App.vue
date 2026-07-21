<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppHeader from './components/AppHeader.vue'
</script>

<template>
  <div id="app">
    <AppHeader v-if="!$route.path.startsWith('/rag-admin')" />
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<style>
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
