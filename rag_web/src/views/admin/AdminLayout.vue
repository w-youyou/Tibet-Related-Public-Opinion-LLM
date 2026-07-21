<template>
  <div class="admin-layout">
    <!-- 侧边导航栏 -->
    <aside class="admin-sidebar">
      <div class="sidebar-brand">
        <svg class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
        <span class="brand-text">RAG Admin</span>
      </div>

      <nav class="sidebar-menu">
        <router-link to="/rag-admin/dashboard" class="menu-item" active-class="active">
          <svg class="menu-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
          </svg>
          <span class="menu-text">控制看板</span>
        </router-link>

        <router-link to="/rag-admin/knowledge-bases" class="menu-item" active-class="active">
          <svg class="menu-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
          </svg>
          <span class="menu-text">知识库管理</span>
        </router-link>

        <router-link to="/rag-admin/documents" class="menu-item" active-class="active">
          <div class="menu-icon-wrapper"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg></div>
          <span class="menu-text">文档管理</span>
        </router-link>

        <router-link to="/rag-admin/feedbacks" class="menu-item" active-class="active">
          <div class="menu-icon-wrapper">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
            </svg>
          </div>
          <span class="menu-text">反馈管理</span>
        </router-link>

        <router-link to="/rag-admin/settings" class="menu-item" active-class="active">
          <svg class="menu-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l-.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
          <span class="menu-text">系统设置</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <router-link to="/" class="back-home-link">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
          </svg>
          <span>返回问答对话</span>
        </router-link>
      </div>
    </aside>

    <!-- 主展示区 -->
    <div class="admin-main">
      <!-- 顶栏导航 -->
      <header class="admin-header">
        <div class="header-left">
          <h2 class="page-title">{{ pageTitle }}</h2>
        </div>

        <div class="header-right">
          <div class="admin-profile">
            <div class="admin-avatar">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
              </svg>
            </div>
            <div class="admin-meta">
              <span class="admin-name">{{ adminName }}</span>
              <span class="admin-role-badge" :class="adminRole.toLowerCase()">
                {{ adminRole === 'SUPER_ADMIN' ? '超级管理员' : '知识库管理员' }}
              </span>
            </div>
          </div>

          <button class="logout-btn" title="退出安全登录" @click="handleLogout">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
            </svg>
          </button>
        </div>
      </header>

      <!-- 视图容器 -->
      <main class="content-container">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { adminLogout } from '@/services/adminApi'

const route = useRoute()
const router = useRouter()

const adminName = computed(() => localStorage.getItem('admin_username') || '管理员')
const adminRole = computed(() => localStorage.getItem('admin_role') || 'KB_ADMIN')

const pageTitle = computed(() => {
  switch (route.name) {
    case 'admin-dashboard':
      return '控制主面板'
    case 'admin-kb':
      return '知识库管理'
    case 'admin-docs':
      return '全生命文档管理'
    case 'admin-doc-detail':
      return '文档追溯详情与历史版本'
    case 'admin-settings':
      return '系统配置与审计日志'
    default:
      return '管理后台'
  }
})

const handleLogout = async () => {
  if (!confirm('确定要安全退出 RAG Admin 系统吗？')) return
  await adminLogout()
  router.push('/rag-admin/login')
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');

.admin-layout {
  font-family: 'Fira Sans', sans-serif;
  display: flex;
  height: 100vh;
  overflow: hidden;
  background-color: #F5F3FF;
  color: #1E1B4B;
}

/* 侧边导航栏样式 */
.admin-sidebar {
  width: 260px;
  background-color: #ffffff;
  border-right: 1px solid rgba(99, 102, 241, 0.1);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  box-shadow: 4px 0 20px rgba(99, 102, 241, 0.03);
  z-index: 10;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.06);
}

.brand-icon {
  width: 28px;
  height: 28px;
  color: #6366F1;
}

.brand-text {
  font-family: 'Fira Code', monospace;
  font-size: 1.35rem;
  font-weight: 700;
  color: #1E1B4B;
  letter-spacing: -0.05em;
}

.sidebar-menu {
  flex: 1;
  padding: 24px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  color: #64748B;
  text-decoration: none;
  border-radius: 10px;
  font-weight: 500;
  transition: all 0.2s ease-in-out;
}

.menu-item:hover {
  background-color: rgba(99, 102, 241, 0.04);
  color: #6366F1;
}

.menu-item.active {
  background-color: #6366F1;
  color: #ffffff;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.25);
}

.menu-icon {
  flex-shrink: 0;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(99, 102, 241, 0.06);
}

.back-home-link {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px;
  border-radius: 8px;
  background-color: #F3F4F6;
  color: #4B5563;
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.2s;
}

.back-home-link:hover {
  background-color: #E5E7EB;
  color: #1F2937;
}

/* 右侧主展示区 */
.admin-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.admin-header {
  height: 70px;
  background-color: #ffffff;
  border-bottom: 1px solid rgba(99, 102, 241, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.02);
  flex-shrink: 0;
}

.page-title {
  font-size: 1.35rem;
  font-weight: 600;
  color: #1E1B4B;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.admin-profile {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-right: 20px;
  border-right: 1px solid rgba(99, 102, 241, 0.1);
}

.admin-avatar {
  width: 38px;
  height: 38px;
  background-color: rgba(99, 102, 241, 0.08);
  color: #6366F1;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.admin-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.admin-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1E1B4B;
}

.admin-role-badge {
  font-size: 0.7rem;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  display: inline-block;
  letter-spacing: 0.02em;
}

.admin-role-badge.super_admin {
  background-color: rgba(16, 185, 129, 0.1);
  color: #10B981;
}

.admin-role-badge.kb_admin {
  background-color: rgba(99, 102, 241, 0.1);
  color: #6366F1;
}

.logout-btn {
  background: none;
  border: none;
  color: #64748B;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logout-btn:hover {
  background-color: rgba(244, 63, 94, 0.08);
  color: #F43F5E;
}

/* 页面内容视图容器 */
.content-container {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
  box-sizing: border-box;
}

/* 路由路由切换过度动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.25s ease-out;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}
</style>
