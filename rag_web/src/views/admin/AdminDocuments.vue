<template>
  <div class="docs-view">
    <!-- 过滤工具条与动作 -->
    <div class="toolbar">
      <div class="filter-group">
        <!-- 搜索输入框 -->
        <div class="search-box">
          <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            v-model="filters.search"
            type="text"
            placeholder="搜索文档名称..."
            @input="handleFilterChange"
          />
        </div>

        <!-- 知识库选择器 -->
        <select v-model="filters.knowledge_base_id" @change="handleFilterChange" class="filter-select">
          <option value="">🌐 全部知识库</option>
          <option v-for="kb in kbs" :key="kb.id" :value="kb.id">
            📚 {{ kb.name }}
          </option>
        </select>

        <!-- 状态选择器 -->
        <select v-model="filters.status" @change="handleFilterChange" class="filter-select">
          <option value="">🏷️ 全部状态</option>
          <option value="active">🟢 运行中(已启用)</option>
          <option value="inactive">🔴 已下架(已禁用)</option>
        </select>
      </div>

      <button class="upload-btn" @click="openUploadModal">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
        </svg>
        <span>上传全新文档</span>
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>正在拉取文档信息，请稍候...</p>
    </div>

    <template v-else>
      <div v-if="docs.length === 0" class="empty-state-container">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
        </svg>
        <h3>暂无任何文档</h3>
        <p>所选检索范围内未查询到文档。请点击上方按钮导入文件。</p>
      </div>

      <!-- 数据表格 -->
      <div v-else class="table-card">
        <table class="admin-table">
          <thead>
            <tr>
              <th>文档名称</th>
              <th>关联知识库</th>
              <th class="text-center">运行版本</th>
              <th class="text-right">文件大小</th>
              <th class="text-right">Chunks数</th>
              <th>分块策略</th>
              <th class="text-center">状态</th>
              <th class="text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="doc in docs" 
              :key="doc.id" 
              class="doc-row"
              @click="router.push(`/rag-admin/documents/${doc.id}`)"
              title="点击查看文档切块详情"
            >
              <td class="doc-name-cell">
                <span class="file-icon">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                  </svg>
                </span>
                <router-link :to="`/rag-admin/documents/${doc.id}`" class="doc-link" :title="doc.name">
                  {{ doc.name }}
                </router-link>
              </td>
              <td>
                <span class="kb-tag">📚 {{ doc.kb_name }}</span>
              </td>
              <td class="text-center">
                <span class="version-label">{{ doc.version }}</span>
              </td>
              <td class="text-right text-muted">{{ formatBytes(doc.size) }}</td>
              <td class="text-right font-code">{{ doc.chunk_count }}</td>
              <td>
                <span class="chunker-tag" :class="doc.chunker_type">{{ formatChunkerName(doc.chunker_type) }}</span>
              </td>
              <td class="text-center">
                <span class="status-badge" :class="doc.status">
                  {{ doc.status === 'active' ? '运行中' : '已禁用' }}
                </span>
              </td>
              <td class="text-right">
                <div class="row-actions">
                  <router-link :to="`/rag-admin/documents/${doc.id}`" class="row-action-btn view" title="文档详情">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                    </svg>
                  </router-link>
                  
                  <button
                    class="row-action-btn toggle"
                    :class="doc.status === 'active' ? 'disable' : 'enable'"
                    :title="doc.status === 'active' ? '下架(禁用)文档' : '上架(恢复)文档'"
                    @click="handleToggleStatus(doc)"
                    :disabled="statusChanging[doc.id]"
                  >
                    <span v-if="statusChanging[doc.id]" class="spinner-tiny"></span>
                    <svg v-else-if="doc.status === 'active'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="9" x2="15" y2="15"/><line x1="15" y1="9" x2="9" y2="15"/>
                    </svg>
                    <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                  </button>

                  <button
                    class="row-action-btn delete"
                    title="软删除文档"
                    @click="handleSoftDelete(doc)"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- 上传全新文档弹窗 -->
    <div v-if="showUploadModal" class="modal-overlay" @click="closeUploadModal">
      <div class="modal-card" @click.stop>
        <div class="modal-header">
          <h2>上传并向量化全新文档</h2>
          <button class="close-btn" @click="closeUploadModal">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <form @submit.prevent="handleUpload" class="modal-form">
          <div class="form-group">
            <label for="uploadKB">关联目标知识库</label>
            <select id="uploadKB" v-model="uploadForm.kb_id" required>
              <option value="" disabled>-- 请选择目标知识空间 --</option>
              <option v-for="kb in kbs" :key="kb.id" :value="kb.id">
                📚 {{ kb.name }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label for="uploadChunker">分块器切分策略</label>
            <select id="uploadChunker" v-model="uploadForm.chunker_type" required>
              <option value="semantic">🧠 语义分块器 (推荐 - 基于语义窗口智能识别)</option>
              <option value="qa">❓ 问答分块器 (专门针对 Q/A 问答对抽取)</option>
              <option value="law">⚖️ 法律法规分块器 (按“条”切分，章节级联)</option>
              <option value="policy">📢 政策公告分块器 (按一级标题，提取发布日期)</option>
              <option value="table">📊 表格分块器 (按行切片并持久化表头结构)</option>
              <option value="multimodal">🖼️ 多模态分块器 (包含文档截图、图片及深度视频编码)</option>
              <option value="recursive">智能递归切分 (按高优分隔符递归切分)</option>
              <option value="by_length">按字符长度切分 (经典按固定大小切分)</option>
              <option value="by_punctuation">按标点切分 (保持句子语法完整性)</option>
            </select>
          </div>

          <div class="form-group">
            <label>物理文件选择</label>
            <div
              class="upload-dropzone"
              :class="{ 'drag-over': isDragOver }"
              @dragover.prevent="isDragOver = true"
              @dragleave="isDragOver = false"
              @drop.prevent="handleFileDrop"
              @click="triggerFileInput"
            >
              <input
                ref="fileInput"
                type="file"
                class="hidden-file-input"
                @change="handleFileSelect"
                accept=".txt,.pdf,.docx,.doc,.xlsx,.xls,.png,.jpg,.jpeg"
              />
              
              <svg class="dropzone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
              </svg>
              
              <span v-if="!selectedFile" class="dropzone-text">点击或拖拽文件到此区域进行上传</span>
              <div v-else class="selected-file-meta">
                <span class="selected-name">{{ selectedFile.name }}</span>
                <span class="selected-size">({{ formatBytes(selectedFile.size) }})</span>
              </div>
              <span class="dropzone-sub">支持格式：TXT, PDF, Word (DOCX/DOC), Excel (XLSX), 图片</span>
            </div>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn-cancel" @click="closeUploadModal" :disabled="uploading">取消</button>
            <button type="submit" class="btn-save" :disabled="uploading || !uploadForm.kb_id || !selectedFile">
              <span v-if="uploading" class="spinner-small"></span>
              <span v-else>安全解析入库</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listKBs, listDocs, uploadDoc, setDocStatus, type AdminKB, type AdminDoc } from '@/services/adminApi'

const router = useRouter()

const loading = ref(true)
const kbs = ref<AdminKB[]>([])
const docs = ref<AdminDoc[]>([])
const statusChanging = ref<Record<string, boolean>>({})

// 过滤参数
const filters = ref({
  search: '',
  knowledge_base_id: '',
  status: ''
})

// 上传参数
const showUploadModal = ref(false)
const uploading = ref(false)
const isDragOver = ref(false)
const selectedFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const uploadForm = ref({
  kb_id: '',
  chunker_type: 'semantic'
})

const fetchInitialData = async () => {
  try {
    loading.value = true
    const [kbRes, docRes] = await Promise.all([listKBs(), listDocs({})])
    if (kbRes.success && kbRes.data) kbs.value = kbRes.data
    if (docRes.success && docRes.data) docs.value = docRes.data
  } catch (error) {
    console.error('获取初始列表失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchInitialData()
})

const handleFilterChange = async () => {
  try {
    const res = await listDocs({
      knowledge_base_id: filters.value.knowledge_base_id || undefined,
      status: filters.value.status || undefined,
      search: filters.value.search.trim() || undefined
    })
    if (res.success && res.data) {
      docs.value = res.data
    }
  } catch (error) {
    console.error('过滤筛选失败:', error)
  }
}

const openUploadModal = () => {
  uploadForm.value = { kb_id: '', chunker_type: 'semantic' }
  selectedFile.value = null
  showUploadModal.value = true
}

const closeUploadModal = () => {
  if (uploading.value) return
  showUploadModal.value = false
}

// 触发文件输入
const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0] || null
  }
}

const handleFileDrop = (event: DragEvent) => {
  isDragOver.value = false
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    selectedFile.value = event.dataTransfer.files[0] || null
  }
}

const handleUpload = async () => {
  if (!selectedFile.value || !uploadForm.value.kb_id || uploading.value) return
  
  uploading.value = true
  try {
    const res = await uploadDoc(selectedFile.value, uploadForm.value.kb_id, uploadForm.value.chunker_type)
    if (res.success) {
      alert(res.message || '文档上传并向量化分析成功')
      showUploadModal.value = false
      await handleFilterChange()
    }
  } catch (e: any) {
    alert(e.message || '文档处理入库异常，请重试')
  } finally {
    uploading.value = false
  }
}

// 启用/禁用文档
const handleToggleStatus = async (doc: AdminDoc) => {
  const targetStatus = doc.status === 'active' ? 'inactive' : 'active'
  if (doc.status === 'active' && !confirm(`⚠️ 提示：禁用文档 "${doc.name}" 将会立刻从向量库中【彻底屏蔽下架】对应的所有切片数据，用户问答将无法检索召回该文件信息。确定吗？`)) {
    return
  }
  
  statusChanging.value[doc.id] = true
  try {
    const res = await setDocStatus(doc.id, targetStatus)
    if (res.success) {
      doc.status = targetStatus
      // 级联改变列表上的 chunks 和 embeddings 表现（禁用时变 0）
      if (targetStatus === 'inactive') {
        doc.chunk_count = 0
        doc.embedding_count = 0
      } else {
        // 重新获取该行以刷新实际的分块数
        const docRes = await listDocs({ search: doc.name })
        const found = docRes.data?.find(d => d.id === doc.id)
        if (found) {
          doc.chunk_count = found.chunk_count
          doc.embedding_count = found.embedding_count
        }
      }
    }
  } catch (e: any) {
    alert(e.message || '操作状态失败')
  } finally {
    statusChanging.value[doc.id] = false
  }
}

// 软删除
const handleSoftDelete = async (doc: AdminDoc) => {
  if (!confirm(`确定要下架并彻底删除文档 "${doc.name}" 吗？该操作将立刻卸载向量数据。`)) {
    return
  }
  try {
    const res = await setDocStatus(doc.id, 'deleted')
    if (res.success) {
      alert('已成功删除文档，底层索引同步洗刷完毕')
      await handleFilterChange()
    }
  } catch (e: any) {
    alert(e.message || '删除失败')
  }
}

// 格式化展示辅助
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
</script>

<style scoped>
.docs-view {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 过滤栏与操作 */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background-color: #ffffff;
  padding: 16px 24px;
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.06);
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.01);
}

@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  flex-wrap: wrap;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 240px;
  flex: 1;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: #64748B;
}

.search-box input {
  width: 100%;
  padding: 8px 12px 8px 36px;
  border-radius: 8px;
  border: 1px solid #CBD5E1;
  font-size: 0.9rem;
  outline: none;
  transition: all 0.2s;
}

.search-box input:focus {
  border-color: #6366F1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}

.filter-select {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #CBD5E1;
  font-size: 0.9rem;
  background-color: #ffffff;
  outline: none;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-select:focus {
  border-color: #6366F1;
}

.upload-btn {
  background: linear-gradient(135deg, #10B981 0%, #059669 100%);
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
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
  transition: all 0.2s;
  flex-shrink: 0;
}

.upload-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(16, 185, 129, 0.35);
}

/* 后台数据表格设计 */
.table-card {
  background-color: #ffffff;
  border: 1px solid rgba(99, 102, 241, 0.06);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.01);
  overflow-x: auto;
}

.admin-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.9rem;
}

.admin-table th {
  background-color: rgba(99, 102, 241, 0.02);
  padding: 16px;
  font-weight: 600;
  color: #475569;
  border-bottom: 1px solid rgba(99, 102, 241, 0.08);
}

.admin-table td {
  padding: 16px;
  border-bottom: 1px solid #F1F5F9;
  color: #334155;
  vertical-align: middle;
}

.admin-table tbody tr:hover {
  background-color: rgba(99, 102, 241, 0.01);
}

.doc-row {
  cursor: pointer;
  transition: background-color 0.15s;
}

.doc-row:hover {
  background-color: rgba(99, 102, 241, 0.025) !important;
}

.doc-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 280px;
}

.file-icon {
  color: #818CF8;
  flex-shrink: 0;
}

.doc-link {
  font-weight: 600;
  color: #1E1B4B;
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.2s;
}

.doc-link:hover {
  color: #6366F1;
  text-decoration: underline;
}

.kb-tag {
  font-size: 0.8rem;
  background-color: rgba(99, 102, 241, 0.05);
  color: #6366F1;
  padding: 4px 8px;
  border-radius: 6px;
  font-weight: 500;
  display: inline-block;
  white-space: nowrap;
}

.version-label {
  font-family: 'Fira Code', monospace;
  font-size: 0.8rem;
  font-weight: 600;
  color: #4F46E5;
  background-color: #E0E7FF;
  padding: 2px 6px;
  border-radius: 4px;
}

.chunker-tag {
  font-size: 0.75rem;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: 6px;
  display: inline-block;
}

.chunker-tag.semantic { background-color: rgba(99, 102, 241, 0.08); color: #6366F1; }
.chunker-tag.qa { background-color: rgba(16, 185, 129, 0.08); color: #10B981; }
.chunker-tag.law { background-color: rgba(244, 63, 94, 0.08); color: #F43F5E; }
.chunker-tag.policy { background-color: rgba(245, 158, 11, 0.08); color: #F59E0B; }
.chunker-tag.table { background-color: rgba(6, 182, 212, 0.08); color: #0891B2; }
.chunker-tag.multimodal { background-color: rgba(236, 72, 153, 0.08); color: #D946EF; }

.status-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
}

.status-badge.active {
  background-color: rgba(16, 185, 129, 0.1);
  color: #10B981;
}

.status-badge.inactive {
  background: rgba(244, 63, 94, 0.1); 
  color: #F43F5E;
}

.row-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.row-action-btn {
  background: none;
  border: none;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  color: #64748B;
}

.row-action-btn.view {
  background-color: #F1F5F9;
}

.row-action-btn.view:hover {
  background-color: #E2E8F0;
  color: #1E1B4B;
}

.row-action-btn.toggle.disable {
  background-color: rgba(245, 158, 11, 0.05);
  color: #F59E0B;
}

.row-action-btn.toggle.disable:hover {
  background-color: #F59E0B;
  color: #ffffff;
}

.row-action-btn.toggle.enable {
  background-color: rgba(16, 185, 129, 0.05);
  color: #10B981;
}

.row-action-btn.toggle.enable:hover {
  background-color: #10B981;
  color: #ffffff;
}

.row-action-btn.delete {
  background-color: rgba(244, 63, 94, 0.04);
  color: #F43F5E;
}

.row-action-btn.delete:hover {
  background-color: #F43F5E;
  color: #ffffff;
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

.dropzone-sub {
  font-size: 0.75rem;
  color: #94A3B8;
  text-align: center;
}

.hidden-file-input {
  display: none;
}

/* 对齐排版辅助 */
.text-center { text-align: center; }
.text-right { text-align: right; }
.text-muted { color: #64748B; }
.font-code { font-family: 'Fira Code', monospace; }

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
  max-width: 540px;
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
  background: linear-gradient(135deg, #10B981 0%, #059669 100%);
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
