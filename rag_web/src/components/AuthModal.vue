<template>
  <div class="auth-modal-overlay" @click="closeModal">
    <div class="auth-modal" @click.stop>
      <!-- 关闭按钮 -->
      <button class="close-btn" @click="closeModal">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12"/>
        </svg>
      </button>

      <!-- 登录/注册切换 -->
      <div class="auth-tabs">
        <button 
          class="tab-btn" 
          :class="{ active: isLogin }"
          @click="isLogin = true"
        >
          登录
        </button>
        <button 
          class="tab-btn" 
          :class="{ active: !isLogin }"
          @click="isLogin = false"
        >
          注册
        </button>
      </div>

      <!-- 登录表单 -->
      <div v-if="isLogin" class="auth-form">
        <h2 class="form-title">欢迎回来</h2>
        
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>
        
        <div class="form-group">
          <label>用户名或邮箱</label>
          <input 
            v-model="loginForm.username" 
            type="text" 
            placeholder="请输入用户名或邮箱"
            class="form-input"
            :disabled="isLoading"
            @keyup.enter="handleLogin"
          />
        </div>

        <div class="form-group">
          <label>密码</label>
          <input 
            v-model="loginForm.password" 
            type="password" 
            placeholder="请输入密码"
            class="form-input"
            :disabled="isLoading"
            @keyup.enter="handleLogin"
          />
        </div>

        <button 
          class="submit-btn" 
          @click="handleLogin"
          :disabled="isLoading"
        >
          <span v-if="isLoading">登录中...</span>
          <span v-else>登录</span>
        </button>
      </div>

      <!-- 注册表单 -->
      <div v-else class="auth-form">
        <h2 class="form-title">创建新账户</h2>
        
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>
        
        <div class="form-group">
          <label>用户名</label>
          <input 
            v-model="registerForm.username" 
            type="text" 
            placeholder="请输入用户名"
            class="form-input"
            :disabled="isLoading"
          />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>密码</label>
            <input 
              v-model="registerForm.password" 
              type="password" 
              placeholder="请输入密码（至少6位）"
              class="form-input"
              :disabled="isLoading"
            />
          </div>

          <div class="form-group">
            <label>确认密码</label>
            <input 
              v-model="registerForm.confirmPassword" 
              type="password" 
              placeholder="请再次输入密码"
              class="form-input"
              :disabled="isLoading"
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>邮箱</label>
            <input 
              v-model="registerForm.email" 
              type="email" 
              placeholder="个人用户必填"
              class="form-input"
              :disabled="isLoading"
            />
          </div>
          <div class="form-group">
            <label>用户类型</label>
            <div class="radio-group" style="height: 45px; align-items: center;">
              <label class="radio-label">
                <input type="radio" v-model="registerForm.user_type" value="personal" :disabled="isLoading">
                普通用户
              </label>
              <label class="radio-label">
                <input type="radio" v-model="registerForm.user_type" value="enterprise" :disabled="isLoading">
                企业用户
              </label>
            </div>
          </div>
        </div>

        <div v-if="registerForm.user_type === 'enterprise'" class="form-group">
          <label>工号</label>
          <input 
            v-model="registerForm.employee_id" 
            type="text" 
            placeholder="请输入工号"
            class="form-input"
            :disabled="isLoading"
          />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>年龄</label>
            <input 
              v-model.number="registerForm.age" 
              type="number" 
              placeholder="请输入年龄"
              class="form-input"
              min="1"
              max="120"
              :disabled="isLoading"
            />
          </div>

          <div class="form-group">
            <label>性别</label>
            <select v-model="registerForm.gender" class="form-input" :disabled="isLoading">
              <option value="">请选择</option>
              <option value="male">男</option>
              <option value="female">女</option>
              <option value="other">其他</option>
            </select>
          </div>
        </div>

        <button 
          class="submit-btn"
          @click="handleRegister"
          :disabled="isLoading"
        >
          <span v-if="isLoading">注册中...</span>
          <span v-else>注册</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { login, register, type User } from '../services/api'

const emit = defineEmits(['close', 'login-success', 'register-success'])

const isLogin = ref(true)
const isLoading = ref(false)
const errorMessage = ref('')

// 登录表单
const loginForm = ref({
  username: '',
  password: ''
})

// 注册表单
const registerForm = ref({
  username: '',
  password: '',
  confirmPassword: '',
  email: '',
  age: '',
  gender: '',
  user_type: 'personal',
  employee_id: ''
})

// 关闭模态框
const closeModal = () => {
  emit('close')
  errorMessage.value = ''
}

// 处理登录
const handleLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password) {
    errorMessage.value = '请填写完整的登录信息'
    return
  }

  isLoading.value = true
  errorMessage.value = ''
  
  try {
    const response = await login(loginForm.value.username, loginForm.value.password)
    if (response.success && response.user) {
      emit('login-success', response.user)
      // 重置表单
      loginForm.value = {
        username: '',
        password: ''
      }
    } else {
      errorMessage.value = response.error || '登录失败'
    }
  } catch (error: any) {
    errorMessage.value = error.message || '登录失败，请稍后重试'
  } finally {
    isLoading.value = false
  }
}

// 处理注册
const handleRegister = async () => {
  // 验证表单
  if (!registerForm.value.username) {
    errorMessage.value = '请输入用户名'
    return
  }

  if (!registerForm.value.password || registerForm.value.password.length < 6) {
    errorMessage.value = '密码至少需要6位'
    return
  }

  if (registerForm.value.password !== registerForm.value.confirmPassword) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }

  if (registerForm.value.user_type === 'enterprise' && !registerForm.value.employee_id) {
    errorMessage.value = '企业用户必须提供工号'
    return
  }

  if (registerForm.value.user_type === 'personal' && (!registerForm.value.email || !registerForm.value.email.includes('@'))) {
    errorMessage.value = '个人用户请输入有效的邮箱地址'
    return
  }

  errorMessage.value = ''
  isLoading.value = true

  try {
    const genderMap: Record<string, 'M' | 'F' | 'O'> = {
      'male': 'M',
      'female': 'F',
      'other': 'O'
    }
    
    const response = await register({
      username: registerForm.value.username,
      password: registerForm.value.password,
      email: registerForm.value.email,
      age: registerForm.value.age ? parseInt(registerForm.value.age) : undefined,
      gender: registerForm.value.gender ? genderMap[registerForm.value.gender] : undefined,
      user_type: registerForm.value.user_type as 'personal' | 'enterprise',
      employee_id: registerForm.value.employee_id
    })
    
    if (response.success && response.user) {
      // 注册成功后自动登录
      emit('login-success', response.user)
      // 重置表单
      registerForm.value = {
        username: '',
        password: '',
        confirmPassword: '',
        email: '',
        age: '',
        gender: '',
        user_type: 'personal',
        employee_id: ''
      }
    } else {
      errorMessage.value = response.error || '注册失败'
    }
  } catch (error: any) {
    errorMessage.value = error.message || '注册失败，请稍后重试'
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.auth-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(4px);
}

.auth-modal {
  background: white;
  border-radius: 20px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  position: relative;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  color: #666;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f5f5f5;
  color: #333;
}

.auth-tabs {
  display: flex;
  border-bottom: 1px solid #e5e5e5;
  padding: 0 24px;
}

.tab-btn {
  flex: 1;
  background: none;
  border: none;
  padding: 16px;
  font-size: 16px;
  font-weight: 500;
  color: #8e8ea0;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-btn.active {
  color: #19c37d;
  border-bottom-color: #19c37d;
}

.auth-form {
  padding: 32px 24px;
}

.form-title {
  font-size: 24px;
  font-weight: 600;
  color: #202123;
  margin-bottom: 24px;
  text-align: center;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 15px;
  transition: all 0.2s;
  outline: none;
}

.form-input:focus {
  border-color: #19c37d;
  box-shadow: 0 0 0 3px rgba(25, 195, 125, 0.1);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.submit-btn {
  width: 100%;
  padding: 14px;
  background: #19c37d;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 8px;
}

.submit-btn:hover {
  background: #16a066;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(25, 195, 125, 0.3);
}

.submit-btn:active {
  transform: translateY(0);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.error-message {
  background: #fee2e2;
  border: 1px solid #fecaca;
  color: #dc2626;
  padding: 12px;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 20px;
}

.radio-group {
  display: flex;
  gap: 20px;
  margin-top: 10px;
}

.radio-label {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.radio-label input {
  margin-right: 8px;
}
</style>

