<template>
  <div class="settings-view">
    <div class="settings-grid">
      <!-- 左栏：系统参数状态配置板 -->
      <div class="settings-card config-card">
        <div class="card-header">
          <h3 class="card-title">
            <svg class="header-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            系统核心参数状态
          </h3>
        </div>

        <div class="config-list font-code">
          <div class="config-item">
            <span class="config-label">ChromaDB 存储路径:</span>
            <span class="config-val">./chroma_db</span>
          </div>
          <div class="config-item">
            <span class="config-label">RAG 排序重排模型 (Reranker):</span>
            <span class="config-val">G:\models\bge-reranker-large</span>
          </div>
          <div class="config-item">
            <span class="config-label">RAG 语义编码模型 (Embedding):</span>
            <span class="config-val">tongyi-embedding-vision-plus</span>
          </div>
          <div class="config-item">
            <span class="config-label">DASHSCOPE_API_KEY 状态:</span>
            <span class="status-tag active">已加载且就绪</span>
          </div>
          <div class="config-item">
            <span class="config-label">RAG 判定阈值 (RRF Relevance):</span>
            <span class="config-val">0.06 (动态低阈值，召回率保障)</span>
          </div>
          <div class="config-item">
            <span class="config-label">RAG 判定阈值 (CE Rerank):</span>
            <span class="config-val">0.20 (精排硬关卡，防范语义幻觉)</span>
          </div>
          <div class="config-item">
            <span class="config-label">数据大屏系统版本:</span>
            <span class="config-val bold">RAG Admin v1.0.0 (Phase 0)</span>
          </div>
        </div>
      </div>

      <!-- 右栏：管理员操作审计日志表 -->
      <div class="settings-card audit-card">
        <div class="card-header">
          <h3 class="card-title">
            <svg class="header-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
            </svg>
            管理员行为操作审计日志
          </h3>
          
          <div class="filter-bar">
            <select v-model="filters.action" @change="fetchLogs" class="filter-select">
              <option value="">🎯 全部操作类型</option>
              <option value="LOGIN">LOGIN (管理员登录)</option>
              <option value="LOGOUT">LOGOUT (管理员退出)</option>
              <option value="CREATE_KB">CREATE_KB (知识库创建)</option>
              <option value="DELETE_KB">DELETE_KB (知识库删除)</option>
              <option value="UPLOAD_DOC">UPLOAD_DOC (文档首次上传)</option>
              <option value="DISABLE_DOC">DISABLE_DOC (下架禁用文档)</option>
              <option value="ENABLE_DOC">ENABLE_DOC (恢复启用文档)</option>
              <option value="UPLOAD_VERSION">UPLOAD_VERSION (文档版本升级)</option>
              <option value="ROLLBACK_VER">ROLLBACK_VER (版本回滚)</option>
            </select>
          </div>
        </div>

        <!-- 日志表格区 -->
        <div class="table-container">
          <div v-if="loading" class="table-loading">
            <div class="spinner"></div>
            <p>正在拉取审计日志...</p>
          </div>

          <div v-else-if="logs.length === 0" class="empty-state">
            <span>未筛选到对应管理员的审计日志</span>
          </div>

          <table v-else class="audit-table">
            <thead>
              <tr>
                <th>操作账号</th>
                <th>动作</th>
                <th>审计明细</th>
                <th class="text-right">时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="log in logs" :key="log.id">
                <td class="font-code bold">{{ log.admin_username }}</td>
                <td>
                  <span class="log-badge" :class="log.action.toLowerCase()">{{ log.action }}</span>
                </td>
                <td class="log-details">{{ log.details }}</td>
                <td class="text-right text-muted">{{ formatTime(log.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <!-- 账号安全与管理模块 -->
    <div class="settings-grid" style="margin-top: 32px;">
      <!-- 修改密码模块 (所有人可见) -->
      <div class="settings-card">
        <div class="card-header">
          <h3 class="card-title">
            <svg class="header-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
            </svg>
            修改当前账号密码
          </h3>
        </div>
        <div class="card-body" style="padding: 24px;">
          <form @submit.prevent="handleChangePassword" class="account-form">
            <div class="form-group">
              <label>旧密码</label>
              <div class="pwd-input-wrapper">
                <input :type="showOldPwd ? 'text' : 'password'" v-model="pwdForm.old_password" required placeholder="请输入原密码" />
                <span class="eye-icon" @click="showOldPwd = !showOldPwd">
                  <svg v-if="!showOldPwd" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                </span>
              </div>
            </div>
            <div class="form-group">
              <label>新密码</label>
              <div class="pwd-input-wrapper">
                <input :type="showNewPwd ? 'text' : 'password'" v-model="pwdForm.new_password" required placeholder="请输入新密码" />
                <span class="eye-icon" @click="showNewPwd = !showNewPwd">
                  <svg v-if="!showNewPwd" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                </span>
              </div>
            </div>
            <div class="form-group">
              <label>确认新密码</label>
              <div class="pwd-input-wrapper">
                <input :type="showConfirmPwd ? 'text' : 'password'" v-model="pwdForm.confirm_password" required placeholder="请再次输入新密码" />
                <span class="eye-icon" @click="showConfirmPwd = !showConfirmPwd">
                  <svg v-if="!showConfirmPwd" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                </span>
              </div>
            </div>
            <div class="form-actions">
              <button type="submit" class="submit-btn" :disabled="isChangingPwd">
                {{ isChangingPwd ? '提交中...' : '修改密码' }}
              </button>
            </div>
            <p v-if="pwdMsg" class="form-msg" :class="{'error': pwdError}">{{ pwdMsg }}</p>
          </form>
        </div>
      </div>

      <!-- 添加管理员模块 (仅SUPER_ADMIN可见) -->
      <div class="settings-card" v-if="isAdminSuper">
        <div class="card-header">
          <h3 class="card-title">
            <svg class="header-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><line x1="20" y1="8" x2="20" y2="14"></line><line x1="23" y1="11" x2="17" y2="11"></line>
            </svg>
            添加新管理员账号
          </h3>
        </div>
        <div class="card-body" style="padding: 24px;">
          <form @submit.prevent="handleAddAdmin" class="account-form">
            <div class="form-group">
              <label>用户名</label>
              <input type="text" v-model="addForm.username" required placeholder="设置新管理员用户名" />
            </div>
            <div class="form-group">
              <label>登录密码</label>
              <div class="pwd-input-wrapper">
                <input :type="showAddPwd ? 'text' : 'password'" v-model="addForm.password" required placeholder="设置初始登录密码" />
                <span class="eye-icon" @click="showAddPwd = !showAddPwd">
                  <svg v-if="!showAddPwd" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                </span>
              </div>
            </div>
            <div class="form-group">
              <label>电子邮箱</label>
              <input type="email" v-model="addForm.email" required placeholder="设置绑定邮箱" />
            </div>
            <div class="form-group">
              <label>分配角色</label>
              <select v-model="addForm.role" required>
                <option value="KB_ADMIN">知识库管理员 (常规)</option>
                <option value="SUPER_ADMIN">超级管理员 (全局权限)</option>
              </select>
            </div>
            <div class="form-actions">
              <button type="submit" class="submit-btn" :disabled="isAddingAdmin">
                {{ isAddingAdmin ? '添加中...' : '确认添加' }}
              </button>
            </div>
            <p v-if="addMsg" class="form-msg" :class="{'error': addError}">{{ addMsg }}</p>
          </form>
        </div>
      </div>
    </div>
  </div>

</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getOperationLogs, addAdminAccount, changeAdminPassword } from '@/services/adminApi'

const isAdminSuper = ref(false)

const pwdForm = ref({ old_password: '', new_password: '', confirm_password: '' })
const isChangingPwd = ref(false)
const pwdMsg = ref('')
const pwdError = ref(false)
const showOldPwd = ref(false)
const showNewPwd = ref(false)
const showConfirmPwd = ref(false)

const addForm = ref({ username: '', password: '', email: '', role: 'KB_ADMIN' })
const isAddingAdmin = ref(false)
const addMsg = ref('')
const addError = ref(false)
const showAddPwd = ref(false)

const handleChangePassword = async () => {
  if (pwdForm.value.new_password !== pwdForm.value.confirm_password) {
    pwdMsg.value = '两次输入的新密码不一致'
    pwdError.value = true
    return
  }
  isChangingPwd.value = true
  pwdMsg.value = ''
  try {
    const res = await changeAdminPassword({
      old_password: pwdForm.value.old_password,
      new_password: pwdForm.value.new_password
    })
    pwdError.value = !res.success
    pwdMsg.value = res.message || (res.success ? '密码修改成功，请重新登录' : '密码修改失败')
    if (res.success) {
      pwdForm.value = { old_password: '', new_password: '', confirm_password: '' }
      setTimeout(() => {
        window.location.href = '/rag-admin/login'
      }, 2000)
    }
  } catch (err: any) {
    pwdError.value = true
    pwdMsg.value = err.message || '网络异常'
  } finally {
    isChangingPwd.value = false
  }
}

const handleAddAdmin = async () => {
  isAddingAdmin.value = true
  addMsg.value = ''
  try {
    const res = await addAdminAccount(addForm.value)
    addError.value = !res.success
    addMsg.value = res.message || (res.success ? '管理员账号添加成功' : '添加失败')
    if (res.success) {
      addForm.value = { username: '', password: '', email: '', role: 'KB_ADMIN' }
    }
  } catch (err: any) {
    addError.value = true
    addMsg.value = err.message || '网络异常'
  } finally {
    isAddingAdmin.value = false
  }
}


const loading = ref(true)
const logs = ref<any[]>([])
const filters = ref({
  action: '',
  username: ''
})

const fetchLogs = async () => {
  try {
    loading.value = true
    const res = await getOperationLogs({
      action: filters.value.action || undefined,
      username: filters.value.username || undefined
    })
    if (res.success && res.data) {
      logs.value = res.data
    }
  } catch (error) {
    console.error('拉取操作日志发生异常:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  isAdminSuper.value = localStorage.getItem('admin_role') === 'SUPER_ADMIN'
  fetchLogs()
})

const formatTime = (timeStr: string): string => {
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>


<style scoped>
.account-form { display: flex; flex-direction: column; gap: 16px; }
.form-group { display: flex; flex-direction: column; gap: 8px; }
.form-group label { font-size: 14px; font-weight: 500; color: #374151; }
.form-group input, .form-group select { padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 8px; outline: none; font-size: 14px; }
.form-group input:focus, .form-group select:focus { border-color: #4f46e5; box-shadow: 0 0 0 2px rgba(79,70,229,0.1); }
.pwd-input-wrapper { position: relative; display: flex; align-items: center; }
.pwd-input-wrapper input { width: 100%; padding-right: 36px; box-sizing: border-box; }
.pwd-input-wrapper .eye-icon { position: absolute; right: 10px; color: #9ca3af; cursor: pointer; display: flex; align-items: center; justify-content: center; height: 100%; }
.pwd-input-wrapper .eye-icon:hover { color: #4b5563; }
.submit-btn { padding: 10px 16px; background-color: #4f46e5; color: white; border: none; border-radius: 8px; font-weight: 500; cursor: pointer; transition: background-color 0.2s; align-self: flex-start; }
.submit-btn:hover:not(:disabled) { background-color: #4338ca; }
.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.form-msg { font-size: 14px; margin-top: 8px; color: #059669; }
.form-msg.error { color: #dc2626; }

.settings-view {

  display: flex;
  flex-direction: column;
}

.settings-grid {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 32px;
  align-items: flex-start;
}

@media (max-width: 960px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}

.settings-card {
  background-color: #ffffff;
  border: 1px solid rgba(99, 102, 241, 0.06);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.01);
  box-sizing: border-box;
}

.card-header {
  padding: 20px 24px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.card-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1E1B4B;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}

.header-icon {
  color: #6366F1;
}

/* 左侧配置栏 */
.config-card {
  padding-bottom: 20px;
}

.config-list {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.85rem;
  border-bottom: 1px solid #F1F5F9;
  padding-bottom: 12px;
}

.config-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.config-label {
  color: #64748B;
  font-weight: 500;
}

.config-val {
  color: #1E1B4B;
  word-break: break-all;
  line-height: 1.4;
}

.status-tag {
  align-self: flex-start;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.status-tag.active {
  background-color: rgba(16, 185, 129, 0.1);
  color: #10B981;
}

/* 右侧日志列表 */
.audit-card {
  display: flex;
  flex-direction: column;
  min-height: 520px;
}

.filter-select {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #CBD5E1;
  font-size: 0.88rem;
  background-color: #ffffff;
  outline: none;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-select:focus {
  border-color: #6366F1;
}

.table-container {
  overflow-x: auto;
  flex: 1;
}

.audit-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.88rem;
}

.audit-table th {
  background-color: rgba(99, 102, 241, 0.01);
  padding: 14px 16px;
  font-weight: 600;
  color: #475569;
  border-bottom: 1px solid rgba(99, 102, 241, 0.08);
}

.audit-table td {
  padding: 14px 16px;
  border-bottom: 1px solid #F1F5F9;
  color: #334155;
  vertical-align: middle;
}

.audit-table tbody tr:hover {
  background-color: rgba(99, 102, 241, 0.01);
}

.log-details {
  max-width: 320px;
  line-height: 1.4;
}

.log-badge {
  font-family: 'Fira Code', monospace;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
}

.log-badge.login { background-color: rgba(99, 102, 241, 0.1); color: #6366F1; }
.log-badge.logout { background-color: rgba(71, 85, 105, 0.1); color: #475569; }
.log-badge.create_kb { background-color: rgba(16, 185, 129, 0.1); color: #10B981; }
.log-badge.delete_kb { background-color: rgba(244, 63, 94, 0.1); color: #F43F5E; }
.log-badge.upload_doc { background-color: rgba(129, 140, 248, 0.1); color: #818CF8; }
.log-badge.disable_doc { background-color: rgba(245, 158, 11, 0.1); color: #F59E0B; }
.log-badge.enable_doc { background-color: rgba(16, 185, 129, 0.1); color: #10B981; }
.log-badge.upload_version { background-color: rgba(99, 102, 241, 0.1); color: #6366F1; }
.log-badge.rollback_ver { background-color: rgba(236, 72, 153, 0.1); color: #EC4899; }

/* 文本格式规范辅助 */
.font-code { font-family: 'Fira Code', monospace; }
.bold { font-weight: 600; }
.text-right { text-align: right; }
.text-muted { color: #64748B; }

/* 加载菊花 */
.table-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6rem 0;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(99, 102, 241, 0.1);
  border-top-color: #6366F1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6rem 0;
  color: #94A3B8;
  font-size: 0.85rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
