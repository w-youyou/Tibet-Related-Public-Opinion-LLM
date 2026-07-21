import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'chat',
      component: ChatView,
    },
    {
      path: '/chunker',
      name: 'chunker-demo',
      component: () => import('../views/ChunkerDemo.vue'),
    },
    {
      path: '/timeline',
      name: 'timeline',
      component: () => import('../views/TimelineView.vue'),
    },
    {
      path: '/knowledge-bases',
      name: 'knowledge-bases',
      component: () => import('../views/KnowledgeBaseManage.vue'),
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/ProfileView.vue'),
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('../views/AboutView.vue'),
    },
    // ==================== 后台管理系统路由 (Phase 0) ====================
    {
      path: '/rag-admin/login',
      name: 'admin-login',
      component: () => import('../views/admin/AdminLogin.vue'),
    },
    {
      path: '/rag-admin',
      name: 'admin-layout',
      component: () => import('../views/admin/AdminLayout.vue'),
      children: [
        {
          path: '',
          redirect: '/rag-admin/dashboard',
        },
        {
          path: 'dashboard',
          name: 'admin-dashboard',
          component: () => import('../views/admin/AdminDashboard.vue'),
        },
        {
          path: 'knowledge-bases',
          name: 'admin-kb',
          component: () => import('../views/admin/AdminKnowledgeBases.vue'),
        },
        {
          path: 'knowledge-bases/create',
          name: 'admin-kb-create',
          component: () => import('../views/admin/AdminKBCreate.vue'),
        },
        {
          path: 'knowledge-bases/:id',
          name: 'admin-kb-detail',
          component: () => import('../views/admin/AdminKBDetail.vue'),
        },
        {
          path: 'documents',
          name: 'admin-docs',
          component: () => import('../views/admin/AdminDocuments.vue'),
        },
        {
          path: 'documents/:id',
          name: 'admin-doc-detail',
          component: () => import('../views/admin/AdminDocDetail.vue'),
        },
        {
          path: 'feedbacks',
          name: 'admin-feedbacks',
          component: () => import('../views/admin/FeedbackList.vue'),
        },
        {
          path: 'feedbacks/:id',
          name: 'admin-feedback-detail',
          component: () => import('../views/admin/FeedbackDetail.vue'),
        },
        {
          path: 'settings',
          name: 'admin-settings',
          component: () => import('../views/admin/AdminSettings.vue'),
        },
      ],
    },
  ],
})

// 全局路由守卫：校验后台管理员登录状态
router.beforeEach((to, from, next) => {
  const isBackoffice = to.path.startsWith('/rag-admin')
  const isLogin = to.path === '/rag-admin/login'
  const hasToken = !!localStorage.getItem('admin_access_token')

  if (isBackoffice && !isLogin && !hasToken) {
    next('/rag-admin/login')
  } else if (isLogin && hasToken) {
    next('/rag-admin/dashboard')
  } else {
    next()
  }
})

export default router
