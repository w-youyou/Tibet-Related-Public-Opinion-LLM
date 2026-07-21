<template>
  <div class="kb-manage-container">
    <div class="container">
      <div class="header">
        <h1 class="title">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align: middle;">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
          </svg>
          我的知识库
        </h1>
        <div class="header-actions">
          <button class="back-chat-btn" @click="goToChat">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <span>返回聊天</span>
          </button>
          <button class="create-btn" @click="goToCreate">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            <span>创建知识库</span>
          </button>
        </div>
      </div>

      <!-- 检索范围选择器 -->
      <div v-if="knowledgeBases.length > 0" class="kb-selector">
        <label for="kb-select">检索范围</label>
        <select id="kb-select" :value="kbFilterStore.selectedKnowledgeBase" @change="kbFilterStore.setSelected(($event.target as HTMLSelectElement).value)">
          <option value="">所有知识库</option>
          <option v-for="kb in knowledgeBases" :key="kb.id" :value="kb.id">
            {{ kb.name }}
          </option>
        </select>
      </div>

      <!-- 知识库列表 -->
      <div class="kb-list">
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>加载中...</p>
        </div>

        <div v-else-if="knowledgeBases.length === 0" class="empty-state">
          <div class="empty-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" style="color: var(--color-text-muted);">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <h3>暂无知识库</h3>
          <p>创建您的第一个知识库，开始管理文档</p>
          <button class="create-empty-btn" @click="goToCreate">创建知识库</button>
        </div>

        <div v-else class="kb-grid">
          <div
            v-for="kb in knowledgeBases"
            :key="kb.id"
            class="kb-card"
            @click="viewKnowledgeBase(kb.id)"
          >
            <div class="kb-card-header">
              <h3 class="kb-name">{{ kb.name }}</h3>
              <div class="kb-actions">
                <button
                  class="action-btn edit-btn"
                  @click.stop="editKnowledgeBase(kb)"
                  title="编辑"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                </button>
                <button
                  class="action-btn delete-btn"
                  @click.stop="deleteKB(kb)"
                  title="删除"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </button>
              </div>
            </div>
            
            <p v-if="kb.description" class="kb-description">{{ kb.description }}</p>
            <p v-else class="kb-description placeholder">暂无描述</p>
            
            <div class="kb-meta">
              <div class="meta-item">
                <span class="meta-label">创建时间：</span>
                <span class="meta-value">{{ formatDate(kb.created_at) }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">更新时间：</span>
                <span class="meta-value">{{ formatDate(kb.updated_at) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 编辑知识库模态框 -->
      <div v-if="showEditModal" class="modal-overlay" @click="showEditModal = false">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h2>编辑知识库</h2>
            <button class="close-btn" @click="showEditModal = false">×</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>知识库名称</label>
              <input
                v-model="editForm.name"
                type="text"
                class="form-input"
                placeholder="请输入知识库名称"
              />
            </div>
            <div class="form-group">
              <label>知识库描述</label>
              <textarea
                v-model="editForm.description"
                class="form-textarea"
                rows="3"
                placeholder="请输入知识库描述（可选）"
              ></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click="showEditModal = false">取消</button>
            <button class="btn-save" @click="saveEdit" :disabled="!editForm.name.trim()">保存</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useKbFilterStore } from '@/stores/kbFilter'
import { listKnowledgeBases, deleteKnowledgeBase, type KnowledgeBase } from '@/services/api'

const router = useRouter()
const kbFilterStore = useKbFilterStore()

const knowledgeBases = ref<KnowledgeBase[]>([])
const loading = ref(false)
const showEditModal = ref(false)
const editForm = ref({
  id: '',
  name: '',
  description: ''
})

// 加载知识库列表
const loadKnowledgeBases = async () => {
  try {
    loading.value = true
    const response = await listKnowledgeBases()
    if (response.success && response.knowledge_bases) {
      knowledgeBases.value = response.knowledge_bases
    } else {
      console.error('加载知识库列表失败:', response.error)
    }
  } catch (error) {
    console.error('加载知识库列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 删除知识库
const deleteKB = async (kb: KnowledgeBase) => {
  if (!confirm(`确定要删除知识库"${kb.name}"吗？此操作不可恢复。`)) {
    return
  }

  try {
    const response = await deleteKnowledgeBase(kb.id)
    if (response.success) {
      await loadKnowledgeBases()
    } else {
      alert(`删除失败: ${response.error}`)
    }
  } catch (error: any) {
    alert(`删除失败: ${error.message || error}`)
  }
}

// 编辑知识库
const editKnowledgeBase = (kb: KnowledgeBase) => {
  editForm.value = {
    id: kb.id,
    name: kb.name,
    description: kb.description || ''
  }
  showEditModal.value = true
}

// 保存编辑（注意：目前后端没有更新接口，这里先留空，后续可以添加）
const saveEdit = async () => {
  // TODO: 实现更新知识库API
  alert('更新功能待实现')
  showEditModal.value = false
}

// 查看知识库
const viewKnowledgeBase = (kbId: string) => {
  router.push(`/chunker?kb_id=${kbId}`)
}

// 跳转到创建页面
const goToCreate = () => {
  router.push('/chunker')
}

// 返回聊天界面
const goToChat = () => {
  router.push('/')
}

// 格式化日期
const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  loadKnowledgeBases()
})
</script>

<style scoped>
.kb-manage-container {
  min-height: calc(100vh - 52px);
  background: var(--color-bg);
  padding: var(--space-xl) 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-lg);
}

/* ===== Header ===== */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-xl);
}

.title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ===== KB Selector ===== */
.kb-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: var(--space-lg);
  padding: 10px 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.kb-selector label {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text);
  white-space: nowrap;
}

.kb-selector select {
  flex: 1;
  min-width: 200px;
  padding: 8px 12px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  cursor: pointer;
  outline: none;
  transition: all var(--transition-fast);
}
.kb-selector select:hover { border-color: var(--color-text-muted); }
.kb-selector select:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(26, 54, 93, 0.08);
}

/* ===== Buttons ===== */
.back-chat-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.back-chat-btn:hover { background: var(--color-border-light); }

.create-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.create-btn:hover {
  background: var(--color-primary-light);
  box-shadow: var(--shadow-md);
}

/* ===== States ===== */
.loading-state {
  text-align: center;
  padding: var(--space-2xl) 0;
  color: var(--color-text-secondary);
}

.spinner {
  width: 36px; height: 36px;
  border: 3px solid var(--color-border);
  border-top: 3px solid var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto var(--space-md);
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: var(--space-2xl) 0;
}
.empty-icon {
  margin-bottom: var(--space-md);
}
.empty-state h3 {
  color: var(--color-text);
  font-size: var(--font-size-lg);
  margin-bottom: 6px;
}
.empty-state p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  margin-bottom: var(--space-lg);
}

.create-empty-btn {
  padding: 10px 22px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.create-empty-btn:hover {
  background: var(--color-primary-light);
}

/* ===== KB Cards ===== */
.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-lg);
}

.kb-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.kb-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}

.kb-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-md);
}

.kb-name {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
  flex: 1;
}

.kb-actions { display: flex; gap: 6px; }

.action-btn {
  width: 30px; height: 30px;
  border: none;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-fast);
  background: var(--color-bg);
  color: var(--color-text-secondary);
}
.action-btn:hover { background: var(--color-border-light); }

.edit-btn:hover {
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

.delete-btn:hover {
  background: var(--color-danger-light);
  color: var(--color-danger);
}

.kb-description {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  margin-bottom: var(--space-md);
  min-height: 2.5rem;
  line-height: 1.5;
}
.kb-description.placeholder {
  color: var(--color-text-muted);
  font-style: italic;
}

.kb-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: var(--space-md);
  border-top: 1px solid var(--color-border-light);
}
.meta-item {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}
.meta-label { font-weight: 500; }

/* ===== Modal ===== */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-lg);
  border-bottom: 1px solid var(--color-border-light);
}
.modal-header h2 {
  margin: 0;
  color: var(--color-text);
  font-size: var(--font-size-xl);
}

.close-btn {
  width: 32px; height: 32px;
  border: none;
  background: none;
  font-size: 22px;
  color: var(--color-text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}
.close-btn:hover { background: var(--color-bg); color: var(--color-text); }

.modal-body { padding: var(--space-lg); }

.form-group { margin-bottom: var(--space-lg); }
.form-group label {
  display: block;
  margin-bottom: 6px;
  color: var(--color-text);
  font-weight: 500;
  font-size: var(--font-size-sm);
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
  font-family: var(--font-family);
  transition: all var(--transition-fast);
  box-sizing: border-box;
  color: var(--color-text);
  background: var(--color-surface);
}
.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(26, 54, 93, 0.08);
}
.form-textarea { resize: vertical; }

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-md);
  padding: var(--space-lg);
  border-top: 1px solid var(--color-border-light);
}

.btn-cancel,
.btn-save {
  padding: 8px 18px;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-cancel {
  background: var(--color-bg);
  color: var(--color-text);
}
.btn-cancel:hover { background: var(--color-border-light); }

.btn-save {
  background: var(--color-primary);
  color: #fff;
}
.btn-save:hover:not(:disabled) { background: var(--color-primary-light); }
.btn-save:disabled { opacity: 0.5; cursor: not-allowed; }

@media (max-width: 768px) {
  .header { flex-direction: column; align-items: flex-start; gap: var(--space-md); }
  .kb-grid { grid-template-columns: 1fr; }
}
</style>

