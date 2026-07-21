<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="logo-area">
          <svg class="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <h1 class="login-title">RAG Admin</h1>
        <p class="login-subtitle">涉藏舆情知识问答系统 · 管理后台</p>
      </div>

      <form @submit.prevent="handleLogin" class="login-form" :class="{ 'shake-animation': loginFailed }">
        <div v-if="expiredPrompt" class="alert warning-alert">
          <svg class="alert-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <span>会话已过期，请重新登录。</span>
        </div>

        <div v-if="errorMessage" class="alert danger-alert">
          <svg class="alert-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          <span>{{ errorMessage }}</span>
        </div>

        <div class="form-group">
          <label for="username">管理员账号</label>
          <div class="input-wrapper">
            <svg class="input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
            </svg>
            <input
              id="username"
              v-model="username"
              type="text"
              required
              placeholder="请输入用户名"
              autocomplete="username"
              :disabled="loading"
            />
          </div>
        </div>

        <div class="form-group">
          <label for="password">安全密码</label>
          <div class="input-wrapper">
            <svg class="input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              placeholder="请输入密码"
              autocomplete="current-password"
              :disabled="loading"
            />
          </div>
        </div>

        <button type="submit" class="submit-btn" :disabled="loading || !username || !password">
          <span v-if="loading" class="spinner-small"></span>
          <span v-else>安全登录</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { adminLogin } from '@/services/adminApi'

const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')
const expiredPrompt = ref(false)
const loginFailed = ref(false)

onMounted(() => {
  if (route.query.expired === '1') {
    expiredPrompt.value = true
  }
})

const handleLogin = async () => {
  if (!username.value.trim() || !password.value.trim() || loading.value) return
  
  loading.value = true
  errorMessage.value = ''
  expiredPrompt.value = false
  loginFailed.value = false

  try {
    const res = await adminLogin(username.value, password.value)
    if (res.success) {
      router.push('/rag-admin/dashboard')
    } else {
      throw new Error('未知的认证错误')
    }
  } catch (error: any) {
    errorMessage.value = error.message || '网络连接异常，登录失败'
    loginFailed.value = true
    setTimeout(() => {
      loginFailed.value = false
    }, 500)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');

.login-page {
  font-family: 'Fira Sans', sans-serif;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1E1B4B 0%, #312E81 50%, #4338CA 100%);
  position: relative;
  overflow: hidden;
}

.login-page::before {
  content: "";
  position: absolute;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%);
  top: -100px;
  right: -100px;
  pointer-events: none;
}

.login-page::after {
  content: "";
  position: absolute;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(16, 185, 129, 0.08) 0%, transparent 70%);
  bottom: -150px;
  left: -150px;
  pointer-events: none;
}

.login-card {
  width: 100%;
  max-width: 440px;
  padding: 3rem;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
  z-index: 5;
}

.login-header {
  text-align: center;
  margin-bottom: 2.5rem;
}

.logo-area {
  display: inline-flex;
  padding: 12px;
  background: rgba(99, 102, 241, 0.15);
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.25);
  color: #818CF8;
  margin-bottom: 1rem;
}

.logo-icon {
  width: 32px;
  height: 32px;
}

.login-title {
  font-family: 'Fira Code', monospace;
  font-size: 2.25rem;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 0.5rem 0;
  letter-spacing: -0.05em;
}

.login-subtitle {
  font-size: 0.95rem;
  color: #94A3B8;
  margin: 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.alert {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 10px;
  line-height: 1.4;
}

.warning-alert {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: #FBBF24;
}

.danger-alert {
  background: rgba(244, 63, 94, 0.1);
  border: 1px solid rgba(244, 63, 94, 0.3);
  color: #FB7185;
}

.alert-icon {
  flex-shrink: 0;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 500;
  color: #E2E8F0;
  letter-spacing: 0.05em;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 14px;
  color: #64748B;
  transition: color 0.2s;
}

.input-wrapper input {
  width: 100%;
  padding: 12px 14px 12px 42px;
  background: rgba(15, 23, 42, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: #ffffff;
  font-size: 0.95rem;
  outline: none;
  transition: all 0.2s;
  box-sizing: border-box;
}

.input-wrapper input:focus {
  border-color: #6366F1;
  background: rgba(15, 23, 42, 0.5);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
}

.input-wrapper input:focus + .input-icon,
.input-wrapper input:focus-within ~ .input-icon {
  color: #818CF8;
}

.submit-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);
  color: #ffffff;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
  margin-top: 1rem;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(1px);
}

.submit-btn:disabled {
  background: rgba(255, 255, 255, 0.1);
  color: #64748B;
  cursor: not-allowed;
  box-shadow: none;
}

/* 抖动动画 */
.shake-animation {
  animation: shake 0.5s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-6px); }
  40%, 80% { transform: translateX(6px); }
}

/* loading 菊花 */
.spinner-small {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
