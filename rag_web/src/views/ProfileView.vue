<template>
  <div class="profile-container">
    <div class="profile-card">
      <h2 class="profile-title">个人信息</h2>
      
      <div v-if="isLoading" class="loading-spinner">加载中...</div>
      
      <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
      <div v-if="successMessage" class="success-message">{{ successMessage }}</div>

      <form v-if="user" @submit.prevent="handleUpdate">
        <div class="form-group">
          <label for="username">用户名</label>
          <input id="username" v-model="user.username" type="text" class="form-input">
        </div>
        <div class="form-group">
          <label for="email">邮箱</label>
          <input id="email" v-model="user.email" type="email" class="form-input">
        </div>
        <div class="form-group">
          <label for="age">年龄</label>
          <input id="age" v-model.number="user.age" type="number" class="form-input">
        </div>
        <div class="form-group">
          <label for="gender">性别</label>
          <select id="gender" v-model="user.gender" class="form-input">
            <option value="M">男</option>
            <option value="F">女</option>
            <option value="O">其他</option>
          </select>
        </div>
        <button type="submit" class="submit-btn" :disabled="isUpdating">{{ isUpdating ? '更新中...' : '保存更改' }}</button>
      </form>

      <button @click="goBack" class="back-btn">返回聊天</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getCurrentUser, updateUser, type User } from '../services/api'

const router = useRouter()
const user = ref<User | null>(null)
const isLoading = ref(true)
const isUpdating = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

onMounted(async () => {
  try {
    const response = await getCurrentUser()
    if (response.success && response.user) {
      user.value = response.user
    } else {
      errorMessage.value = '无法加载用户信息，请先登录。'
    }
  } catch (error: any) {
    errorMessage.value = error.message || '加载用户信息失败。'
  } finally {
    isLoading.value = false
  }
})

const handleUpdate = async () => {
  if (!user.value) return

  isUpdating.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const response = await updateUser({
      username: user.value.username,
      email: user.value.email,
      age: user.value.age,
      gender: user.value.gender,
    })

    if (response.success) {
      successMessage.value = '用户信息更新成功！'
    } else {
      errorMessage.value = response.error || '更新失败。'
    }
  } catch (error: any) {
    errorMessage.value = error.message || '更新失败，请稍后重试。'
  } finally {
    isUpdating.value = false
  }
}

const goBack = () => {
  router.push('/')
}
</script>

<style scoped>
.profile-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 52px);
  background: var(--color-bg);
  padding: var(--space-xl);
}

.profile-card {
  background: var(--color-surface);
  padding: var(--space-xl);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-sm);
  width: 100%;
  max-width: 480px;
}

.profile-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-lg);
  text-align: center;
}

.form-group {
  margin-bottom: var(--space-md);
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: var(--color-text);
  font-size: var(--font-size-sm);
}

.form-input {
  width: 100%;
  padding: 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  font-size: var(--font-size-base);
  font-family: var(--font-family);
  color: var(--color-text);
  background: var(--color-surface);
  transition: border-color var(--transition-fast);
}
.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(26, 54, 93, 0.08);
}

.submit-btn {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: #fff;
  font-size: var(--font-size-base);
  font-family: var(--font-family);
  font-weight: 500;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.submit-btn:hover { background: var(--color-primary-light); }
.submit-btn:disabled {
  background: var(--color-border);
  cursor: not-allowed;
}

.back-btn {
  width: 100%;
  padding: 12px;
  margin-top: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
  font-family: var(--font-family);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.back-btn:hover { background: var(--color-border-light); color: var(--color-text); }

.error-message, .success-message, .loading-spinner {
  margin-bottom: var(--space-md);
  padding: 10px;
  border-radius: var(--radius-sm);
  text-align: center;
  font-size: var(--font-size-sm);
}

.error-message {
  background: var(--color-danger-light);
  color: var(--color-danger);
}

.success-message {
  background: var(--color-accent-light);
  color: var(--color-accent);
}
</style>
