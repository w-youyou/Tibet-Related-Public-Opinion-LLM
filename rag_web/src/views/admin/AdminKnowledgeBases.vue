<template>
  <div class="kb-view">
    <!-- 头部和动作按钮 -->
    <div class="view-header">
      <p class="view-desc">集中管控所有 Chroma 向量空间，查询底层分块与文件级联。</p>
      
      <!-- 仅 SUPER_ADMIN 有权创建新知识库 -->
      <button
        v-if="isSuperAdmin"
        class="create-btn"
        @click="openCreateModal"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 5v14M5 12h14"/>
        </svg>
        <span>新建知识库</span>
      </button>
      <div v-else class="locked-badge" title="仅超级管理员有权操作">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
        <span>新建锁闭 (仅限超级管理员)</span>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>正在读取向量空间拓扑...</p>
    </div>

    <template v-else>
      <div v-if="kbs.length === 0" class="empty-state-container">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
        </svg>
        <h3>暂无可用知识库</h3>
        <p>系统未关联任何 ChromaDB 空间。请联系超级管理员新建。</p>
      </div>

      <div v-else class="kb-grid">
        <div v-for="kb in kbs" :key="kb.id" class="kb-card" @click="viewKB(kb.id)">
          <div class="kb-card-header">
            <h3 class="kb-name" :title="kb.name">{{ kb.name }}</h3>
            <span v-if="kb.status === 'active'" class="kb-status-badge active" title="运行中">运行中</span>
            <span v-else class="kb-status-badge inactive" title="已禁用">已禁用</span>
          </div>

          <p class="kb-desc-text" v-if="kb.description">{{ kb.description }}</p>
          <p class="kb-desc-text placeholder" v-else>未设定对此空间描述</p>

          <div class="kb-collection-info">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><rect x="9" y="9" width="6" height="6"/>
            </svg>
            <span class="collection-code" :title="kb.collection_name">{{ kb.collection_name }}</span>
          </div>

          <div class="kb-stats-grid">
            <div class="sub-stat">
              <span class="sub-stat-num">{{ kb.doc_count }}</span>
              <span class="sub-stat-label">关联文档</span>
            </div>
            <div class="sub-stat">
              <span class="sub-stat-num">{{ kb.chunk_count }}</span>
              <span class="sub-stat-label">总 Chunks</span>
            </div>
          </div>

          <div class="kb-footer">
            <span class="kb-time">{{ formatDate(kb.created_at) }}</span>
            
            <div class="kb-actions">
              <!-- 查看文档按钮 -->
              <button class="action-btn view" title="查看知识库文档" @click.stop="viewKB(kb.id)">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                </svg>
              </button>

              <!-- 编辑按钮 -->
              <button class="action-btn edit" title="编辑知识库" @click.stop="openEditModal(kb)">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/>
                </svg>
              </button>
              
              <!-- 仅超级管理员可删除知识库 -->
              <button
                v-if="isSuperAdmin"
                class="action-btn delete"
                title="级联彻底删除知识库"
                @click.stop="handleDelete(kb)"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

    </template>

    <!-- 新建/编辑知识库模态弹窗 -->
    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-card" @click.stop>
        <div class="modal-header">
          <h2>{{ isEdit ? '编辑向量空间配置' : '新建 Chroma 知识库' }}</h2>
          <button class="close-btn" @click="closeModal">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <form @submit.prevent="submitForm" class="modal-form">
          <div class="form-group">
            <label for="kbName">知识库名称</label>
            <input
              id="kbName"
              v-model="form.name"
              type="text"
              required
              placeholder="例如: 陇东地区水利条例说明书"
              :disabled="isEdit"
            />
            <p v-if="!isEdit" class="form-help">ChromaDB 将依据此名称创建底层 Collection，创建后不能修改名称。</p>
          </div>

          <div class="form-group">
            <label for="kbDesc">描述说明</label>
            <textarea
              id="kbDesc"
              v-model="form.description"
              rows="4"
              placeholder="请输入对此向量空间的数据集特征描述，便于大模型检索策略匹配..."
            ></textarea>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn-cancel" @click="closeModal">取消</button>
            <button type="submit" class="btn-save" :disabled="submitting || !form.name.trim()">
              <span v-if="submitting" class="spinner-small"></span>
              <span v-else>确定</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listKBs, createKB, updateKB, deleteKB, type AdminKB } from '@/services/adminApi'

const router = useRouter()

const viewKB = (id: string) => {
  router.push(`/rag-admin/knowledge-bases/${id}`)
}
const loading = ref(true)
const kbs = ref<AdminKB[]>([])
const isSuperAdmin = computed(() => localStorage.getItem('admin_role') === 'SUPER_ADMIN')

// 弹窗状态
const showModal = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const activeKbId = ref('')
const form = ref({
  name: '',
  description: ''
})

const fetchKBs = async () => {
  try {
    loading.value = true
    const res = await listKBs()
    if (res.success && res.data) {
      kbs.value = res.data
    }
  } catch (error) {
    console.error('获取知识库列表失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchKBs()
})

const openCreateModal = () => {
  router.push('/rag-admin/knowledge-bases/create')
}

const openEditModal = (kb: AdminKB) => {
  isEdit.value = true
  activeKbId.value = kb.id
  form.value = { name: kb.name, description: kb.description || '' }
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
}

const submitForm = async () => {
  if (!form.value.name.trim() || submitting.value) return
  submitting.value = true
  
  try {
    if (isEdit.value) {
      const res = await updateKB(activeKbId.value, form.value.name, form.value.description)
      if (res.success) {
        closeModal()
        await fetchKBs()
      }
    } else {
      const res = await createKB(form.value.name, form.value.description)
      if (res.success) {
        closeModal()
        await fetchKBs()
      }
    }
  } catch (e: any) {
    alert(e.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (kb: AdminKB) => {
  if (!confirm(`🚨 警告：级联删除知识库将【彻底擦除】对应的 Chroma 向量集合、物理文件列表及版本线，且不可恢复！\n\n确定要删除知识库 "${kb.name}" 吗？`)) {
    return
  }
  
  try {
    const res = await deleteKB(kb.id)
    if (res.success) {
      alert(res.message || '删除成功')
      await fetchKBs()
    }
  } catch (e: any) {
    alert(e.message || '删除失败')
  }
}

const formatDate = (timeStr: string): string => {
  const date = new Date(timeStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}
</script>

<style scoped>
.kb-view {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.view-desc {
  font-size: 0.95rem;
  color: #64748B;
  margin: 0;
}

.create-btn {
  background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
  transition: all 0.2s;
}

.create-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
}

.locked-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  background-color: rgba(226, 232, 240, 0.6);
  border: 1px solid #CBD5E1;
  color: #64748B;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: not-allowed;
}

/* 知识库网格系统 */
.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 24px;
}

.kb-card {
  background-color: #ffffff;
  border: 1px solid rgba(99, 102, 241, 0.06);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.01);
  display: flex;
  flex-direction: column;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.kb-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 30px rgba(99, 102, 241, 0.08);
  border-color: rgba(99, 102, 241, 0.15);
}

.kb-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.kb-name {
  font-size: 1.15rem;
  font-weight: 600;
  color: #1E1B4B;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.kb-status-badge {
  font-size: 0.72rem;
  padding: 3px 8px;
  border-radius: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.kb-status-badge.active {
  background-color: #DCFCE7;
  color: #16A34A;
}

.kb-status-badge.inactive {
  background-color: #FEE2E2;
  color: #DC2626;
}

.kb-desc-text {
  font-size: 0.88rem;
  color: #64748B;
  line-height: 1.5;
  margin: 0 0 16px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  min-height: 38px;
}

.kb-desc-text.placeholder {
  color: #94A3B8;
  font-style: italic;
}

.kb-collection-info {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: rgba(99, 102, 241, 0.04);
  padding: 6px 12px;
  border-radius: 6px;
  color: #6366F1;
  font-size: 0.8rem;
  font-family: 'Fira Code', monospace;
  margin-bottom: 16px;
}

.collection-code {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.kb-stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 12px 0;
  border-top: 1px dashed rgba(99, 102, 241, 0.1);
  border-bottom: 1px dashed rgba(99, 102, 241, 0.1);
  margin-bottom: 16px;
}

.sub-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.sub-stat:first-child {
  border-right: 1px solid rgba(99, 102, 241, 0.08);
}

.sub-stat-num {
  font-family: 'Fira Code', monospace;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1E1B4B;
}

.sub-stat-label {
  font-size: 0.75rem;
  color: #64748B;
}

.kb-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
}

.kb-time {
  font-size: 0.75rem;
  color: #94A3B8;
}

.kb-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  background: none;
  border: 1px solid transparent;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.view {
  background-color: rgba(16, 185, 129, 0.04);
  color: #10B981;
}

.action-btn.view:hover {
  background-color: #10B981;
  color: #ffffff;
}

.action-btn.edit {
  background-color: rgba(99, 102, 241, 0.04);
  color: #6366F1;
}

.action-btn.edit:hover {
  background-color: #6366F1;
  color: #ffffff;
}

.action-btn.delete {
  background-color: rgba(244, 63, 94, 0.04);
  color: #F43F5E;
}

.action-btn.delete:hover {
  background-color: #F43F5E;
  color: #ffffff;
}

/* 模态弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-card {
  background-color: #ffffff;
  border-radius: 16px;
  width: 100%;
  max-width: 500px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.08);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.06);
}

.modal-header h2 {
  font-size: 1.15rem;
  font-weight: 600;
  color: #1E1B4B;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  color: #64748B;
  cursor: pointer;
  padding: 6px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover {
  background-color: #F1F5F9;
  color: #1E1B4B;
}

.modal-form {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #334155;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #CBD5E1;
  outline: none;
  font-size: 0.9rem;
  transition: all 0.2s;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group textarea:focus {
  border-color: #6366F1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}

.form-help {
  font-size: 0.75rem;
  color: #64748B;
  margin: 2px 0 0 0;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 12px;
}

.btn-cancel {
  background-color: #F1F5F9;
  color: #475569;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background-color: #E2E8F0;
}

.btn-save {
  background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);
  color: #ffffff;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-save:hover:not(:disabled) {
  transform: translateY(-1px);
}

.btn-save:disabled {
  background: #CBD5E1;
  color: #94A3B8;
  cursor: not-allowed;
}

/* 全局加载态 */
.loading-overlay {
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

.empty-state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6rem 0;
  text-align: center;
}

.empty-icon {
  width: 60px;
  height: 60px;
  color: #94A3B8;
  margin-bottom: 1rem;
}

.empty-state-container h3 {
  font-size: 1.15rem;
  font-weight: 600;
  color: #334155;
  margin: 0 0 6px 0;
}

.empty-state-container p {
  font-size: 0.88rem;
  color: #64748B;
  margin: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
</style>
