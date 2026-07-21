<template>
  <div class="kb-detail-view">
    <!-- Loading -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>正在读取知识库信息与文档列表...</p>
    </div>

    <template v-else-if="!kb">
      <div class="empty-state-container">
        <h3>未找到该知识库</h3>
        <p>指定的知识库不存在或已被删除。</p>
        <button class="back-btn" @click="goBack">返回知识库列表</button>
      </div>
    </template>

    <template v-else>
      <!-- 面包屑导航 -->
      <div class="breadcrumb">
        <button class="back-btn" @click="goBack">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
          </svg>
          <span>返回知识库列表</span>
        </button>
        <span class="breadcrumb-sep">/</span>
        <span class="breadcrumb-current">{{ kb.name }}</span>
      </div>

      <!-- KB 信息头部卡 -->
      <div class="kb-info-card">
        <div class="kb-info-left">
          <div class="kb-icon-bg">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
            </svg>
          </div>
          <div class="kb-info-text">
            <h1 class="kb-title">
              {{ kb.name }}
              <span v-if="kb.status === 'active'" class="kb-status-tag active">运行中</span>
              <span v-else class="kb-status-tag inactive">已禁用</span>
            </h1>
            <p class="kb-desc">{{ kb.description || '暂无描述' }}</p>
            <div class="kb-collection-pill">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/><rect x="9" y="9" width="6" height="6"/>
              </svg>
              <span>{{ kb.collection_name }}</span>
            </div>
          </div>
        </div>
        <div class="kb-stats-row">
          <div class="stat-pill">
            <span class="stat-num">{{ kb.doc_count }}</span>
            <span class="stat-lbl">关联文档</span>
          </div>
          <div class="stat-sep"></div>
          <div class="stat-pill">
            <span class="stat-num">{{ kb.chunk_count }}</span>
            <span class="stat-lbl">总 Chunks</span>
          </div>
          <div class="stat-sep"></div>
          <div class="stat-pill">
            <span class="stat-num">{{ formatDate(kb.created_at) }}</span>
            <span class="stat-lbl">创建日期</span>
          </div>
        </div>
      </div>
      
      <div class="kb-actions-row">
        <button class="secondary-btn toggle-btn" :class="kb.status" @click="toggleKBStatus">
          <template v-if="kb.status === 'active'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/>
            </svg>
            <span>一键禁用该知识库</span>
          </template>
          <template v-else>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <span>恢复启用知识库</span>
          </template>
        </button>
      </div>

      <!-- 文档列表区域 -->
      <div class="docs-section">
        <div class="docs-section-header">
          <h2 class="section-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
            </svg>
            文档列表
            <span class="doc-count-badge">{{ docs.length }}</span>
          </h2>
          <div class="docs-search">
            <svg class="search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input v-model="searchQuery" type="text" placeholder="搜索文档名称..." />
          </div>
        </div>

        <!-- 文档空状态 -->
        <div v-if="filteredDocs.length === 0" class="empty-docs">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          <p>该知识库暂无文档{{ searchQuery ? ' (搜索无匹配)' : '' }}</p>
        </div>

        <!-- 文档卡片网格 -->
        <div v-else class="docs-grid">
          <div
            v-for="doc in filteredDocs"
            :key="doc.id"
            class="doc-card"
            :class="{ 'doc-disabled': doc.status === 'inactive' }"
            @click="viewDoc(doc.id)"
          >
            <!-- 文档图标 + 状态 -->
            <div class="doc-card-top">
              <div class="doc-file-icon" :class="getFileExtClass(doc.name)">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
                <span class="file-ext">{{ getFileExt(doc.name) }}</span>
              </div>
              <div class="doc-badges">
                <span class="ver-badge">{{ doc.version }}</span>
                <span class="status-badge" :class="doc.status">
                  {{ doc.status === 'active' ? '运行中' : '已禁用' }}
                </span>
              </div>
            </div>

            <!-- 文档名称 -->
            <h3 class="doc-name" :title="doc.name">{{ doc.name }}</h3>

            <!-- 文档统计 -->
            <div class="doc-stats">
              <div class="doc-stat">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                </svg>
                <span class="stat-val">{{ doc.chunk_count }}</span>
                <span class="stat-label">Chunks</span>
              </div>
              <div class="doc-stat">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                </svg>
                <span class="stat-val">{{ formatBytes(doc.size) }}</span>
                <span class="stat-label">大小</span>
              </div>
            </div>

            <!-- 分块策略标签 -->
            <div class="doc-footer">
              <span class="chunker-tag" :class="doc.chunker_type">{{ formatChunkerName(doc.chunker_type) }}</span>
              <div class="view-detail-hint" @click.stop="openChunkModal(doc)">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                </svg>
                <span>查看切块</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 切块详情弹窗 Modal -->
    <Teleport to="body">
      <div v-if="showChunkModal" class="modal-overlay" @click.self="closeChunkModal">
        <div class="modal-container">
          <div class="modal-header">
            <h3 class="modal-title">
              <span class="file-icon-small">📄</span> 
              {{ currentPreviewDoc?.name }} - 切分详情
            </h3>
            <button class="close-btn" @click="closeChunkModal">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div class="modal-body">
            <div v-if="loadingChunks" class="modal-loading">
              <div class="spinner"></div>
              <p>正在获取切分数据...</p>
            </div>
            <div v-else-if="previewChunks.length === 0" class="modal-empty">
              <p>未找到该文档的切分数据，可能尚未完成处理或数据已清空。</p>
            </div>
            <ChunkResults 
              v-else
              :chunks="previewChunks" 
              :chunker-name="formatChunkerName(currentPreviewDoc?.chunker_type || 'semantic')" 
            />
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listKBs, listDocs, getDocDetail, updateKB, type AdminKB, type AdminDoc } from '@/services/adminApi'
import ChunkResults from '@/components/ChunkResults.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const kb = ref<AdminKB | null>(null)
const docs = ref<AdminDoc[]>([])
const searchQuery = ref('')

const filteredDocs = computed(() => {
  if (!searchQuery.value.trim()) return docs.value
  const q = searchQuery.value.toLowerCase()
  return docs.value.filter(d => d.name.toLowerCase().includes(q))
})

const fetchData = async () => {
  const kbId = route.params.id as string
  try {
    loading.value = true
    const [kbRes, docRes] = await Promise.all([
      listKBs(),
      listDocs({ knowledge_base_id: kbId })
    ])
    if (kbRes.success && kbRes.data) {
      kb.value = kbRes.data.find(k => k.id === kbId) || null
    }
    if (docRes.success && docRes.data) {
      docs.value = docRes.data
    }
  } catch (e) {
    console.error('获取知识库详情失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)

const toggleKBStatus = async () => {
  if (!kb.value) return
  const isCurrentlyActive = kb.value.status === 'active'
  const actionText = isCurrentlyActive ? '禁用' : '恢复启用'
  if (!confirm(`确定要${actionText}该知识库吗？\n\n禁用后，系统将强制切断该知识库的所有检索入口。`)) return

  try {
    const newStatus = isCurrentlyActive ? 'inactive' : 'active'
    const res = await updateKB(kb.value.id, kb.value.name, kb.value.description || '', newStatus)
    if (res.success && res.data) {
      kb.value = { ...kb.value, ...res.data } as AdminKB
      alert(`${actionText}知识库成功！`)
    }
  } catch (e: any) {
    alert(e.message || `${actionText}失败`)
  }
}

const goBack = () => router.push('/rag-admin/knowledge-bases')
const viewDoc = (docId: string) => router.push(`/rag-admin/documents/${docId}`)

const formatDate = (t: string) =>
  new Date(t).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })

const formatBytes = (bytes: number): string => {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const getFileExt = (name: string): string => {
  const parts = name.split('.')
  return parts.length > 1 ? (parts[parts.length - 1]?.toUpperCase() ?? '') : 'FILE'
}

const getFileExtClass = (name: string): string => {
  const ext = getFileExt(name).toLowerCase()
  if (['pdf'].includes(ext)) return 'ext-pdf'
  if (['docx', 'doc'].includes(ext)) return 'ext-word'
  if (['xlsx', 'xls', 'csv'].includes(ext)) return 'ext-excel'
  if (['txt', 'md'].includes(ext)) return 'ext-txt'
  if (['png', 'jpg', 'jpeg'].includes(ext)) return 'ext-img'
  return 'ext-default'
}

const formatChunkerName = (type: string): string => {
  const map: Record<string, string> = {
    semantic: '语义分块',
    qa: '问答切分',
    law: '法律法规',
    policy: '政策公告',
    table: '表格分块',
    multimodal: '多模态',
    recursive: '递归切分',
    by_length: '按长度',
    by_punctuation: '按标点',
    by_page: '按页切分'
  }
  return map[type] || type
}

// 弹窗状态管理
const showChunkModal = ref(false)
const loadingChunks = ref(false)
const currentPreviewDoc = ref<AdminDoc | null>(null)
const previewChunks = ref<any[]>([])

const openChunkModal = async (doc: AdminDoc) => {
  currentPreviewDoc.value = doc
  showChunkModal.value = true
  loadingChunks.value = true
  previewChunks.value = []
  
  try {
    const res = await getDocDetail(doc.id)
    if (res.success && res.data?.chunks) {
      previewChunks.value = res.data.chunks.map((chunk: any) => ({
        id: chunk.chunk_id,
        content: chunk.content,
        modality_type: 'text',
        metadata: {
          chunkSize: chunk.length,
          position: Number(chunk.chunk_id) - 1,
          chunker: doc.chunker_type
        }
      }))
    }
  } catch (err) {
    console.error('Failed to fetch chunks:', err)
  } finally {
    loadingChunks.value = false
  }
}

const closeChunkModal = () => {
  showChunkModal.value = false
  currentPreviewDoc.value = null
  previewChunks.value = []
}
</script>

<style scoped>
.kb-detail-view {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

/* 面包屑 */
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 10px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  color: #6366F1;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  transition: all 0.2s;
}

.back-btn:hover {
  color: #4F46E5;
  transform: translateX(-2px);
}

.breadcrumb-sep {
  color: #CBD5E1;
  font-size: 0.9rem;
}

.breadcrumb-current {
  font-size: 0.88rem;
  color: #475569;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
}

/* KB 信息头卡 */
.kb-info-card {
  background: #ffffff;
  border: 1px solid rgba(99, 102, 241, 0.08);
  border-radius: 18px;
  padding: 28px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  box-shadow: 0 4px 24px rgba(99, 102, 241, 0.04);
  flex-wrap: wrap;
}

.kb-info-left {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  flex: 1;
}

.kb-icon-bg {
  width: 60px;
  height: 60px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(99, 102, 241, 0.15));
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6366F1;
  flex-shrink: 0;
}

.kb-info-text {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.kb-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: #1E1B4B;
  margin: 0;
}

.kb-desc {
  font-size: 0.88rem;
  color: #64748B;
  margin: 0;
  max-width: 480px;
}

.kb-collection-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(99, 102, 241, 0.05);
  border: 1px solid rgba(99, 102, 241, 0.12);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.78rem;
  font-family: 'Fira Code', monospace;
  color: #6366F1;
  width: fit-content;
}

.kb-stats-row {
  display: flex;
  align-items: center;
  gap: 0;
  background: rgba(99, 102, 241, 0.02);
  border: 1px solid rgba(99, 102, 241, 0.08);
  border-radius: 12px;
  padding: 12px 24px;
  flex-shrink: 0;
}

.stat-pill {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 0 24px;
}

.stat-num {
  font-family: 'Fira Code', monospace;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1E1B4B;
}

.stat-lbl {
  font-size: 0.72rem;
  color: #64748B;
  white-space: nowrap;
}

.stat-sep {
  width: 1px;
  height: 36px;
  background: rgba(99, 102, 241, 0.1);
}

/* 文档区域 */
.docs-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.docs-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1.1rem;
  font-weight: 700;
  color: #1E1B4B;
  margin: 0;
}

.section-title svg {
  color: #6366F1;
}

.doc-count-badge {
  font-size: 0.75rem;
  font-weight: 700;
  background: rgba(99, 102, 241, 0.1);
  color: #6366F1;
  padding: 2px 8px;
  border-radius: 10px;
}

.docs-search {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
  color: #94A3B8;
}

.docs-search input {
  padding: 8px 12px 8px 32px;
  border: 1px solid #CBD5E1;
  border-radius: 8px;
  font-size: 0.88rem;
  outline: none;
  transition: all 0.2s;
  width: 220px;
}

.docs-search input:focus {
  border-color: #6366F1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
}

/* 文档网格 */
.docs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.doc-card {
  background: #ffffff;
  border: 1px solid rgba(99, 102, 241, 0.06);
  border-radius: 14px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
  overflow: hidden;
}

.doc-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #6366F1, #818CF8);
  opacity: 0;
  transition: opacity 0.25s;
}

.doc-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 30px rgba(99, 102, 241, 0.10);
  border-color: rgba(99, 102, 241, 0.18);
}

.doc-card:hover::before {
  opacity: 1;
}

.doc-card.doc-disabled {
  opacity: 0.65;
}

.doc-card.doc-disabled::before {
  background: linear-gradient(90deg, #F43F5E, #FB7185);
}

.doc-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* 文件图标+扩展名 */
.doc-file-icon {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 52px;
  border-radius: 8px;
  gap: 2px;
  flex-shrink: 0;
}

.ext-pdf   { background: rgba(239, 68, 68, 0.08); color: #EF4444; }
.ext-word  { background: rgba(37, 99, 235, 0.08); color: #2563EB; }
.ext-excel { background: rgba(16, 185, 129, 0.08); color: #10B981; }
.ext-txt   { background: rgba(100, 116, 139, 0.08); color: #64748B; }
.ext-img   { background: rgba(236, 72, 153, 0.08); color: #EC4899; }
.ext-default { background: rgba(99, 102, 241, 0.08); color: #6366F1; }

.file-ext {
  font-size: 0.6rem;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.doc-badges {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 5px;
}

.ver-badge {
  font-family: 'Fira Code', monospace;
  font-size: 0.72rem;
  font-weight: 700;
  background: #E0E7FF;
  color: #4F46E5;
  padding: 2px 7px;
  border-radius: 4px;
}

.status-badge {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
}
.status-badge.active   { background: rgba(16, 185, 129, 0.1); color: #10B981; }
.status-badge.inactive { background: rgba(244, 63, 94, 0.1);  color: #F43F5E; }

.doc-name {
  font-size: 0.92rem;
  font-weight: 700;
  color: #1E1B4B;
  margin: 0;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-stats {
  display: flex;
  gap: 16px;
}

.doc-stat {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #64748B;
}

.doc-stat svg {
  color: #94A3B8;
}

.stat-val {
  font-family: 'Fira Code', monospace;
  font-size: 0.85rem;
  font-weight: 700;
  color: #1E1B4B;
}

.stat-label {
  font-size: 0.72rem;
  color: #94A3B8;
}

.doc-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px dashed rgba(99, 102, 241, 0.08);
}

.chunker-tag {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 5px;
}
.chunker-tag.semantic    { background: rgba(99, 102, 241, 0.08); color: #6366F1; }
.chunker-tag.qa          { background: rgba(16, 185, 129, 0.08); color: #10B981; }
.chunker-tag.law         { background: rgba(244, 63, 94, 0.08);  color: #F43F5E; }
.chunker-tag.policy      { background: rgba(245, 158, 11, 0.08); color: #F59E0B; }
.chunker-tag.table       { background: rgba(6, 182, 212, 0.08);  color: #0891B2; }
.chunker-tag.multimodal  { background: rgba(236, 72, 153, 0.08); color: #EC4899; }
.chunker-tag.recursive   { background: rgba(100, 116, 139, 0.08); color: #64748B; }
.chunker-tag.by_length   { background: rgba(100, 116, 139, 0.08); color: #64748B; }

.view-detail-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.72rem;
  color: #94A3B8;
  transition: color 0.2s;
}

.doc-card:hover .view-detail-hint {
  color: #6366F1;
}

/* 空状态 */
.empty-docs {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 5rem 0;
  color: #94A3B8;
  text-align: center;
}

.empty-docs p {
  font-size: 0.95rem;
  margin: 0;
}

/* 通用空状态 & Loading */
.loading-overlay,
.empty-state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6rem 0;
  gap: 12px;
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(99, 102, 241, 0.1);
  border-top-color: #6366F1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.modal-container {
  background: #fff;
  border-radius: 20px;
  width: 100%;
  max-width: 1100px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  animation: modal-fade-in 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modal-fade-in {
  from { opacity: 0; transform: translateY(20px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #F1F5F9;
  background: #F8FAFC;
}

.modal-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: #1E293B;
  display: flex;
  align-items: center;
  gap: 8px;
}

.close-btn {
  background: transparent;
  border: none;
  color: #94A3B8;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #E2E8F0;
  color: #0F172A;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
  background: #F1F5F9;
}

.modal-loading, .modal-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #64748B;
  gap: 16px;
}

.kb-status-tag {
  font-size: 0.75rem;
  padding: 4px 10px;
  border-radius: 20px;
  font-weight: 600;
  vertical-align: middle;
  margin-left: 12px;
}
.kb-status-tag.active {
  background: #DCFCE7;
  color: #16A34A;
}
.kb-status-tag.inactive {
  background: #FEE2E2;
  color: #DC2626;
}

.kb-actions-row {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
.kb-actions-row .secondary-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid #CBD5E1;
  background: white;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
.kb-actions-row .secondary-btn svg {
  stroke-width: 2.5px;
}
.kb-actions-row .secondary-btn.active {
  color: #EF4444;
  border-color: #FECACA;
}
.kb-actions-row .secondary-btn.active:hover {
  background: #FEF2F2;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.1);
}
.kb-actions-row .secondary-btn.inactive {
  color: #10B981;
  border-color: #A7F3D0;
}
.kb-actions-row .secondary-btn.inactive:hover {
  background: #ECFDF5;
  box-shadow: 0 2px 4px rgba(16, 185, 129, 0.1);
}
</style>
