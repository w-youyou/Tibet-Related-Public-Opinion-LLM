<template>
  <div class="doc-detail-view">
    <!-- 加载中 -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>正在读取文档追溯树与向量切块...</p>
    </div>

    <template v-else-if="!docBasic">
      <div class="empty-state-container">
        <h3>未找到该文档</h3>
        <p>指定的文档记录不存在或已被彻底删除。</p>
        <button class="back-btn" @click="goBack">返回列表</button>
      </div>
    </template>

    <template v-else>
      <!-- 头部卡片与返回 -->
      <div class="view-header">
        <button class="back-btn" @click="goBack">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
          </svg>
          <span>返回文档管理</span>
        </button>
        <div class="header-badges">
          <span class="badge kb-badge">📚 {{ docBasic.kb_name }}</span>
          <span class="status-badge" :class="docBasic.status">
            {{ docBasic.status === 'active' ? '运行中(启用)' : '停用中(禁用)' }}
          </span>
        </div>
      </div>

      <!-- 网格面板：左侧属性大卡，右侧详情视窗 -->
      <div class="detail-grid">
        <!-- 左侧：文档全局元数据卡 -->
        <div class="left-card info-card">
          <div class="doc-meta-header">
            <div class="file-icon-bg large">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
              </svg>
            </div>
            <h2 class="detail-doc-name" :title="docBasic.name">{{ docBasic.name }}</h2>
          </div>

          <div class="meta-list">
            <div class="meta-item">
              <span class="meta-label">文档 ID:</span>
              <span class="meta-value font-code small">{{ docBasic.id }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">当前运行版本:</span>
              <span class="meta-value font-code bold active-ver">v{{ docBasic.current_version || '无' }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">切片分块 Chunks:</span>
              <span class="meta-value font-code bold">{{ docBasic.chunk_count }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">多模态向量数:</span>
              <span class="meta-value font-code bold">{{ docBasic.embedding_count }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">分块策略:</span>
              <span class="meta-value bold">{{ formatChunkerName(docBasic.chunker_type) }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">物理文件大小:</span>
              <span class="meta-value">{{ formatBytes(docBasic.file_size) }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">导入系统时间:</span>
              <span class="meta-value">{{ formatFullTime(docBasic.created_at) }}</span>
            </div>
          </div>

          <!-- 快速控制 -->
          <div class="control-box">
            <button
              class="control-btn toggle-btn"
              :class="docBasic.status === 'active' ? 'disable' : 'enable'"
              @click="toggleDocStatus"
              :disabled="statusChanging"
            >
              <span v-if="statusChanging" class="spinner-tiny"></span>
              <span v-else>{{ docBasic.status === 'active' ? '下架禁用文档' : '上架启用文档' }}</span>
            </button>
            <button class="control-btn upload-version-btn" @click="openUploadModal">
              上传更新版本 (升级v{{ (docBasic.current_version || 0) + 1 }})
            </button>
          </div>
        </div>

        <!-- 右侧：分块预览 & 版本控制选项卡 -->
        <div class="right-card tabs-card">
          <div class="tabs-header">
            <button 
              class="tab-btn" 
              :class="{ active: activeTab === 'chunks' }"
              @click="activeTab = 'chunks'"
            >
              🧩 Chunks 预览 ({{ docBasic.chunk_count }})
            </button>
            <button 
              class="tab-btn" 
              :class="{ active: activeTab === 'versions' }"
              @click="activeTab = 'versions'"
            >
              ⏳ 版本时间轴 ({{ versions.length }})
            </button>
            <button 
              class="tab-btn" 
              :class="{ active: activeTab === 'logs' }"
              @click="activeTab = 'logs'"
            >
              📋 文件变动日志 ({{ logs.length }})
            </button>
          </div>

          <!-- Tab 1: Chunks 预览区 -->
          <div v-if="activeTab === 'chunks'" class="tab-pane chunks-pane">
            <div class="pane-actions" style="margin-bottom: 12px; display: flex; justify-content: flex-end;">
              <label style="font-size: 13px; color: #4b5563; display: flex; align-items: center; gap: 6px; cursor: pointer;">
                <input type="checkbox" v-model="showAllChunks" @change="fetchDetail" />
                展示历史版本 Chunks
              </label>
            </div>
            
            <div v-if="docBasic.status !== 'active'" class="info-alert">
              <span>⚠️ 文档当前处于“已禁用”状态，ChromaDB 向量数据已被动态卸载。启用文档后即可正常召回并显示分块。</span>
            </div>
            
            <div v-else-if="chunks.length === 0" class="empty-state">
              <span>ChromaDB 集合中未检索到激活的文本 Chunks，可能尚未完成向量化。</span>
            </div>
            
            <div v-else class="chunks-list">
              <div v-for="chunk in chunks" :key="chunk.chunk_id" class="chunk-item" :class="{ 'inactive-chunk': !chunk.is_active }">
                <div class="chunk-header">
                  <div class="chunk-header-left" style="display: flex; align-items: center;">
                    <span class="chunk-badge" :class="{ inactive: !chunk.is_active }">Chunk #{{ chunk.chunk_id }}</span>
                    <span class="chunk-length">{{ chunk.length }} 字符</span>
                    <span class="chunk-version" style="font-size: 12px; color: #64748b; margin-left: 12px;">版本: {{ chunk.version_number }}</span>
                    <span v-if="!chunk.is_active" style="color: #ef4444; font-size: 12px; margin-left: 8px;">(历史存档/已失效)</span>
                  </div>
                  <button v-if="chunk.is_active" class="edit-chunk-btn" @click="openEditChunkModal(chunk)" title="修改此 Chunk 的内容">
                    📝 编辑修改
                  </button>
                </div>
                <pre class="chunk-content font-code">{{ chunk.content }}</pre>
              </div>
            </div>
          </div>

          <!-- Tab 2: 版本时间轴区 -->
          <div v-if="activeTab === 'versions'" class="tab-pane versions-pane">
            <div class="timeline-container">
              <div v-for="ver in versions" :key="ver.id" class="timeline-node" :class="{ current: ver.status === 'current' }">
                <div class="node-marker">
                  <span class="node-version">v{{ ver.version_number }}</span>
                </div>
                
                <div class="node-card">
                  <div class="node-header">
                    <div class="node-title">
                      <span class="badge-status" :class="ver.status">
                        {{ ver.status === 'current' ? '当前激活主版本' : '历史存档版本' }}
                      </span>
                      <span class="node-time">{{ formatFullTime(ver.uploaded_at) }}</span>
                    </div>

                    <!-- 版本切换操作：仅在非 current 时可选 -->
                    <button
                      v-if="ver.status !== 'current'"
                      class="switch-version-btn"
                      @click="handleSwitchVersion(ver.id)"
                      :disabled="switchingVersion"
                    >
                      <span v-if="switchingVersion" class="spinner-tiny"></span>
                      <span>切换/回滚为当前主版本</span>
                    </button>
                  </div>

                  <div class="node-details font-code">
                    <div class="detail-cell">
                      <span class="cell-label">物理大小:</span>
                      <span>{{ formatBytes(ver.file_size) }}</span>
                    </div>
                    <div class="detail-cell">
                      <span class="cell-label">切片分块:</span>
                      <span>{{ ver.chunk_count }}</span>
                    </div>
                    <div class="detail-cell">
                      <span class="cell-label">分块策略:</span>
                      <span>{{ formatChunkerName(ver.chunker_type) }}</span>
                    </div>
                    <div class="detail-cell">
                      <span class="cell-label">操作人:</span>
                      <span class="cell-user">👤 {{ ver.uploaded_by }}</span>
                    </div>
                  </div>
                  <div class="node-remark" v-if="ver.remark">
                    <strong>📝 备注：</strong> {{ ver.remark }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Tab 3: 文件变动日志 -->
          <div v-if="activeTab === 'logs'" class="tab-pane logs-pane">
            <div v-if="logs.length === 0" class="empty-state">
              <span style="font-size: 24px; margin-bottom: 8px; display: block;">📭</span>
              暂无任何变更操作记录
            </div>
            <div v-else class="logs-timeline-container">
              <div class="log-timeline-item" v-for="log in logs" :key="log.id">
                <div class="log-time-column">
                  <div class="log-date">{{ new Date(log.created_at).toLocaleDateString() }}</div>
                  <div class="log-time">{{ new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}</div>
                </div>
                <div class="log-timeline-marker">
                  <div class="marker-dot"></div>
                  <div class="marker-line"></div>
                </div>
                <div class="log-content-column">
                  <div class="log-header">
                    <span class="action-badge" :class="{'edit-action': log.action === 'EDIT_CHUNK'}">{{ log.action }}</span>
                    <span class="user-badge">👤 {{ log.operator }}</span>
                  </div>
                  <div class="log-details-card">
                    <p>{{ log.details }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </template>

    <!-- 上传更新版本向导模态窗 -->
    <AdminVersionUploadWizard 
      v-if="showUploadModal" 
      :doc-id="docBasic?.id" 
      @close="closeUploadModal" 
      @success="handleUploadSuccess" 
    />

    <!-- Chunk 编辑模态窗 -->
    <div class="modal-overlay" v-if="showEditChunkModal" @click.self="showEditChunkModal = false">
      <div class="modal-content large-modal">
        <div class="modal-header">
          <h3>📝 编辑文档分块 (Hotfix)</h3>
          <button class="close-btn" @click="showEditChunkModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="info-alert" style="margin-bottom: 16px;">
            ⚠️ <strong>警告：</strong>此处修改将直接覆盖 ChromaDB 底层向量数据，属于紧急热修复。下次重新上传该文档的新版本时，此处的修改将会被覆盖丢失。
          </div>
          <div class="form-group">
            <label>Chunk ID: <span class="font-code">{{ currentEditChunk?.chunk_id }}</span></label>
          </div>
          <div class="form-group" style="margin-top: 12px;">
            <label>新文本内容：</label>
            <textarea 
              v-model="editChunkContent" 
              class="form-textarea font-code" 
              rows="12" 
              placeholder="请输入新的 Chunk 文本..."
              style="width: 100%; padding: 12px; border: 1px solid #cbd5e1; border-radius: 6px; resize: vertical;"
            ></textarea>
          </div>
          <div class="form-group" style="margin-top: 12px;">
            <label>修改备注 (Operation Log)：</label>
            <input 
              type="text" 
              v-model="editChunkRemark" 
              class="form-input" 
              placeholder="例如：修正了错别字或错误的数值" 
              style="width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px;"
            />
          </div>

          <div class="modal-actions" style="margin-top: 24px; display: flex; justify-content: flex-end; gap: 12px;">
            <button 
              class="cancel-btn" 
              @click="showEditChunkModal = false" 
              :disabled="isUpdatingChunk"
              style="padding: 8px 16px; border: 1px solid #cbd5e1; background: white; border-radius: 6px; cursor: pointer;"
            >取消</button>
            <button 
              class="submit-btn" 
              @click="submitUpdateChunk" 
              :disabled="!editChunkContent.trim() || isUpdatingChunk"
              style="padding: 8px 16px; background: #6366f1; color: white; border: none; border-radius: 6px; cursor: pointer;"
            >
              {{ isUpdatingChunk ? '正在重新编码并保存...' : '确认修改并重载' }}
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDocDetail, setDocStatus, uploadVersion, switchVersion, updateDocumentChunk, type AdminDocVersion } from '@/services/adminApi'
import AdminVersionUploadWizard from './AdminVersionUploadWizard.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const docBasic = ref<any>(null)
const chunks = ref<any[]>([])
const versions = ref<AdminDocVersion[]>([])
const logs = ref<any[]>([])
const activeTab = ref('chunks')
const showAllChunks = ref(false)

// 状态变动锁
const statusChanging = ref(false)
const switchingVersion = ref(false)

// 弹窗状态
const showUploadModal = ref(false)
const uploading = ref(false)
const isDragOver = ref(false)
const selectedFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const uploadForm = ref({
  chunker_type: 'semantic'
})

// Chunk 编辑状态
const showEditChunkModal = ref(false)
const currentEditChunk = ref<any>(null)
const editChunkContent = ref('')
const editChunkRemark = ref('')
const isUpdatingChunk = ref(false)

const openEditChunkModal = (chunk: any) => {
  currentEditChunk.value = chunk
  editChunkContent.value = chunk.content
  editChunkRemark.value = ''
  showEditChunkModal.value = true
}

const submitUpdateChunk = async () => {
  if (!editChunkContent.value.trim() || !currentEditChunk.value || isUpdatingChunk.value) return
  isUpdatingChunk.value = true
  try {
    const res = await updateDocumentChunk(
      docBasic.value.id, 
      currentEditChunk.value.chunk_id, 
      editChunkContent.value, 
      editChunkRemark.value
    )
    if (res.success) {
      showEditChunkModal.value = false
      await fetchDetail()
    } else {
      alert(`操作失败: ${res.message || '未知错误'}`)
    }
  } catch (e: any) {
    console.error(e)
    alert(`请求异常: ${e.message || e}`)
  } finally {
    isUpdatingChunk.value = false
  }
}

const fetchDetail = async () => {
  const docId = route.params.id as string
  try {
    loading.value = true
    const res = await getDocDetail(docId, showAllChunks.value)
    if (res.success && res.data) {
      docBasic.value = res.data.basic
      chunks.value = res.data.chunks
      versions.value = res.data.versions
      logs.value = res.data.logs || []
      uploadForm.value.chunker_type = res.data.basic.chunker_type || 'semantic'
    }
  } catch (error) {
    console.error('获取文档详情失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDetail()
})

const goBack = () => {
  router.push('/rag-admin/documents')
}

// 启用禁用状态
const toggleDocStatus = async () => {
  if (!docBasic.value) return
  const isCurrentlyActive = docBasic.value.status === 'active'
  const targetStatus = isCurrentlyActive ? 'inactive' : 'active'
  
  if (isCurrentlyActive && !confirm('确定要禁用该文档吗？这将从 Chroma 向量库中隐藏其所有的切片数据，提问问答将无法检索到该文件内容，但后台仍可预览！')) {
    return
  }
  
  statusChanging.value = true
  try {
    const res = await setDocStatus(docBasic.value.id, targetStatus)
    if (res.success) {
      docBasic.value.status = targetStatus
      await fetchDetail() // 重新刷新 Chunks 渲染
    }
  } catch (e: any) {
    alert(e.message || '修改状态失败')
  } finally {
    statusChanging.value = false
  }
}

// 切换/回滚版本
const handleSwitchVersion = async (versionId: string) => {
  if (!confirm('确定要将向量主版本回滚/切换到这一版本吗？\n系统将自动擦除 Chroma 中原有分块，并同步加载新版本的物理切片写入索引！')) {
    return
  }
  
  const remark = prompt('请输入切换/回滚的备注说明（可选）:', '')
  if (remark === null) return // User cancelled
  
  switchingVersion.value = true
  try {
    const res = await switchVersion(versionId, remark)
    if (res.success) {
      alert(res.message || '运行版本切换并向量库刷写成功！')
      await fetchDetail()
    }
  } catch (e: any) {
    alert(e.message || '切换版本失败')
  } finally {
    switchingVersion.value = false
  }
}

// 打开上传弹窗
const openUploadModal = () => {
  selectedFile.value = null
  showUploadModal.value = true
}

const closeUploadModal = () => {
  if (uploading.value) return
  showUploadModal.value = false
}

const handleUploadSuccess = () => {
  showUploadModal.value = false
  activeTab.value = 'versions'
  fetchDetail()
}

// 格式化辅助
const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatChunkerName = (type: string): string => {
  const map: Record<string, string> = {
    'semantic': '🧠 语义分块',
    'qa': '❓ 问答切分',
    'law': '⚖️ 法律法规',
    'policy': '📢 政策公告',
    'table': '📊 表格分块',
    'multimodal': '🖼️ 多模态',
    'recursive': '智能递归',
    'by_length': '按长度',
    'by_punctuation': '按标点',
    'by_page': '按页切分'
  }
  return map[type] || type
}

const formatFullTime = (timeStr: string): string => {
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
.doc-detail-view {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.back-btn {
  background-color: #ffffff;
  border: 1px solid rgba(99, 102, 241, 0.1);
  color: #64748B;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
  box-shadow: 0 4px 10px rgba(99, 102, 241, 0.01);
}

.back-btn:hover {
  background-color: rgba(99, 102, 241, 0.04);
  color: #6366F1;
  border-color: rgba(99, 102, 241, 0.2);
}

.header-badges {
  display: flex;
  align-items: center;
  gap: 12px;
}

.badge {
  font-size: 0.85rem;
  padding: 4px 10px;
  border-radius: 6px;
  font-weight: 500;
}

.kb-badge {
  background-color: rgba(99, 102, 241, 0.05);
  color: #6366F1;
}

.status-badge {
  font-size: 0.85rem;
  padding: 4px 10px;
  border-radius: 6px;
  font-weight: 600;
}

.status-badge.active {
  background-color: rgba(16, 185, 129, 0.1);
  color: #10B981;
}

.status-badge.inactive {
  background: rgba(244, 63, 94, 0.1); 
  color: #F43F5E;
}

/* 核心布局 */
.detail-grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 32px;
  align-items: flex-start;
}

@media (max-width: 960px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}

.left-card,
.right-card {
  background-color: #ffffff;
  border: 1px solid rgba(99, 102, 241, 0.06);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.01);
  box-sizing: border-box;
}

.left-card {
  padding: 24px;
}

.doc-meta-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
  padding-bottom: 24px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.06);
  margin-bottom: 24px;
}

.file-icon-bg.large {
  width: 60px;
  height: 60px;
  border-radius: 14px;
  background-color: rgba(99, 102, 241, 0.05);
  color: #6366F1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.detail-doc-name {
  font-size: 1.2rem;
  font-weight: 600;
  color: #1E1B4B;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}

.meta-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 28px;
}

.meta-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.88rem;
}

.meta-label {
  color: #64748B;
  font-weight: 500;
}

.meta-value {
  color: #334155;
}

.meta-value.active-ver {
  background-color: #E0E7FF;
  color: #4F46E5;
  padding: 2px 6px;
  border-radius: 4px;
}

/* 控制按钮 */
.control-box {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.control-btn {
  width: 100%;
  padding: 11px;
  border-radius: 8px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.toggle-btn.disable {
  background-color: rgba(244, 63, 94, 0.05);
  border: 1px solid rgba(244, 63, 94, 0.2);
  color: #F43F5E;
}

.toggle-btn.disable:hover {
  background-color: #F43F5E;
  color: #ffffff;
  border-color: #F43F5E;
}

.toggle-btn.enable {
  background-color: rgba(16, 185, 129, 0.05);
  border: 1px solid rgba(16, 185, 129, 0.2);
  color: #10B981;
}

.toggle-btn.enable:hover {
  background-color: #10B981;
  color: #ffffff;
  border-color: #10B981;
}

.upload-version-btn {
  background-color: #6366F1;
  color: #ffffff;
  border: none;
  box-shadow: 0 4px 10px rgba(99, 102, 241, 0.2);
}

.upload-version-btn:hover {
  background-color: #4F46E5;
  transform: translateY(-1px);
}

/* 右侧 Tab 页面 */
.tabs-card {
  display: flex;
  flex-direction: column;
  min-height: 500px;
}

.tabs-header {
  display: flex;
  background-color: rgba(99, 102, 241, 0.02);
  border-bottom: 1px solid rgba(99, 102, 241, 0.06);
  padding: 0 24px;
}

.tab-btn {
  background: none;
  border: none;
  padding: 16px 20px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #64748B;
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
}

.tab-btn:hover {
  color: #6366F1;
}

.tab-btn.active {
  color: #6366F1;
}

.tab-btn.active::after {
  content: "";
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background-color: #6366F1;
}

.tab-pane {
  padding: 24px;
  flex: 1;
}

.info-alert {
  padding: 12px 16px;
  background-color: rgba(245, 158, 11, 0.06);
  border: 1px solid rgba(245, 158, 11, 0.2);
  border-radius: 8px;
  font-size: 0.85rem;
  color: #D97706;
  line-height: 1.5;
  margin-bottom: 20px;
}

.info-alert.highlight {
  background-color: rgba(99, 102, 241, 0.05);
  border-color: rgba(99, 102, 241, 0.15);
  color: #4F46E5;
}

/* Chunks 列表 */
.chunks-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 520px;
  overflow-y: auto;
  padding-right: 8px;
}

.chunk-item {
  background-color: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.chunk-item.inactive-chunk { opacity: 0.6; background-color: #f1f5f9; }

.chunk-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
}
.edit-chunk-btn {
  background: white;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s;
}
.edit-chunk-btn:hover {
  border-color: #6366f1;
  color: #6366f1;
}

.chunk-badge {
  font-family: 'Fira Code', monospace;
  background-color: rgba(99, 102, 241, 0.1);
  color: #6366F1;
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: 600;
  margin-right: 12px;
}
.chunk-badge.inactive {
  background-color: #cbd5e1;
  color: #475569;
}

.chunk-length {
  color: #94A3B8;
}

.chunk-content {
  font-size: 0.88rem;
  line-height: 1.6;
  color: #334155;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

/* 版本时间轴时间线样式 */
.timeline-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
  position: relative;
  padding-left: 54px;
}

.timeline-container::before {
  content: "";
  position: absolute;
  left: 20px;
  top: 10px;
  bottom: 10px;
  width: 2px;
  background-color: #E2E8F0;
}

.timeline-node {
  position: relative;
}

.node-marker {
  position: absolute;
  left: -54px;
  top: 16px;
  width: 42px;
  height: 28px;
  border-radius: 6px;
  background-color: #F1F5F9;
  border: 1px solid #CBD5E1;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.node-version {
  font-family: 'Fira Code', monospace;
  font-size: 0.8rem;
  font-weight: 700;
  color: #64748B;
}

.timeline-node.current .node-marker {
  background-color: #E0E7FF;
  border-color: #818CF8;
}

.timeline-node.current .node-version {
  color: #4F46E5;
}

.node-card {
  background-color: #ffffff;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 2px 10px rgba(99, 102, 241, 0.01);
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: border-color 0.2s;
}

.timeline-node.current .node-card {
  border-color: rgba(99, 102, 241, 0.2);
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.04);
  background-color: rgba(99, 102, 241, 0.005);
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.node-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.node-time {
  font-size: 0.78rem;
  color: #94A3B8;
}

.badge-status {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
}

.badge-status.current {
  background-color: rgba(16, 185, 129, 0.1);
  color: #10B981;
}

.badge-status.historical {
  background-color: #F1F5F9;
  color: #64748B;
}

.switch-version-btn {
  background: none;
  border: 1px solid #CBD5E1;
  color: #475569;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 4px;
}

.switch-version-btn:hover:not(:disabled) {
  border-color: #6366F1;
  color: #6366F1;
  background-color: rgba(99, 102, 241, 0.02);
}

.node-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  background-color: #F8FAFC;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid rgba(226, 232, 240, 0.8);
}

.node-remark {
  margin-top: 12px;
  padding: 12px;
  background-color: #FFFBEB;
  border-radius: 8px;
  border: 1px solid #FDE68A;
  font-size: 0.9rem;
  color: #92400E;
  line-height: 1.5;
}

.detail-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.cell-label {
  color: #94A3B8;
}

.cell-user {
  color: #64748B;
}

/* 文本格式规范辅助 */
.font-code { font-family: 'Fira Code', monospace; }
.bold { font-weight: 600; }
.small { font-size: 0.78rem; }
.bold.active-ver { font-weight: 700; }

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

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4rem 0;
  color: #94A3B8;
  font-size: 0.85rem;
}

/* 变动日志时间轴样式 */
.logs-timeline-container {
  display: flex;
  flex-direction: column;
  padding: 10px 10px 20px 10px;
}

.log-timeline-item {
  display: flex;
  position: relative;
  min-height: 80px;
}

.log-time-column {
  width: 100px;
  flex-shrink: 0;
  text-align: right;
  padding-right: 16px;
  padding-top: 4px;
}

.log-date {
  font-size: 0.85rem;
  color: #64748B;
  font-weight: 500;
}

.log-time {
  font-size: 0.75rem;
  color: #94A3B8;
  margin-top: 4px;
}

.log-timeline-marker {
  width: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.marker-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #6366F1;
  border: 2px solid #E0E7FF;
  z-index: 2;
  margin-top: 6px;
}

.marker-line {
  position: absolute;
  top: 16px;
  bottom: -6px;
  width: 2px;
  background-color: #E2E8F0;
  z-index: 1;
}

.log-timeline-item:last-child .marker-line {
  display: none;
}

.log-content-column {
  flex: 1;
  padding-left: 20px;
  padding-bottom: 24px;
}

.log-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.action-badge {
  background: rgba(148, 163, 184, 0.1);
  color: #475569;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: 'Fira Code', monospace;
  font-size: 0.75rem;
  font-weight: 600;
}

.action-badge.edit-action {
  background: rgba(99, 102, 241, 0.1);
  color: #4F46E5;
}

.user-badge {
  font-size: 0.8rem;
  color: #334155;
  font-weight: 500;
}

.log-details-card {
  background-color: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 0.9rem;
  color: #475569;
  line-height: 1.5;
}

.log-details-card p {
  margin: 0;
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

.modal-content {
  background-color: #ffffff;
  border-radius: 16px;
  width: 100%;
  max-width: 600px;
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

.form-group select {
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #CBD5E1;
  outline: none;
  font-size: 0.9rem;
  background-color: #ffffff;
  cursor: pointer;
  transition: all 0.2s;
}

.form-group select:focus {
  border-color: #6366F1;
}

/* 上传拖拽面板 */
.upload-dropzone {
  border: 2px dashed #CBD5E1;
  border-radius: 12px;
  padding: 32px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: all 0.2s;
  background-color: #F8FAFC;
}

.upload-dropzone:hover,
.upload-dropzone.drag-over {
  border-color: #6366F1;
  background-color: rgba(99, 102, 241, 0.02);
}

.dropzone-icon {
  width: 40px;
  height: 40px;
  color: #94A3B8;
  transition: color 0.2s;
}

.upload-dropzone:hover .dropzone-icon {
  color: #6366F1;
}

.dropzone-text {
  font-size: 0.9rem;
  color: #475569;
  font-weight: 500;
  text-align: center;
}

.selected-file-meta {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.selected-name {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1E1B4B;
  text-align: center;
}

.selected-size {
  font-size: 0.8rem;
  color: #64748B;
}

.hidden-file-input {
  display: none;
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

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner-tiny {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
