<template>
  <header class="app-header">
    <div class="header-inner">
      <div class="header-brand">
        <svg class="brand-icon" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
        <span class="brand-text">涉藏舆情分析服务大模型</span>
      </div>
      <nav class="header-nav">
      </nav>
    </div>
  </header>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<style scoped>
.app-header {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  height: 52px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
  position: relative;
  z-index: 100;
}

.header-inner {
  width: 100%;
  padding: 0 var(--space-lg);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  opacity: 0.85;
}

.brand-text {
  font-size: var(--font-size-lg);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.header-nav {
  display: flex;
  gap: 4px;
}

.nav-link {
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  padding: 6px 16px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  transition: all var(--transition-fast);
}

.nav-link:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.nav-link.router-link-active {
  color: #fff;
  background: rgba(255, 255, 255, 0.15);
}
</style>
