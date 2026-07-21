<template>
  <div class="admin-feedback-detail">
    <div class="page-header">
      <div class="header-left">
        <button class="back-btn" @click="$router.push('/rag-admin/feedbacks')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </button>
        <h1 class="page-title">反馈详情 #{{ $route.params.id }}</h1>
        <span class="status-badge" :class="feedback?.status?.toLowerCase()" v-if="feedback">{{ feedback.status_label }}</span>
      </div>
      <div class="header-actions" v-if="feedback && feedback.status === 'PENDING'">
        <button class="action-btn ignore-btn" @click="openIgnoreModal">忽略反馈</button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="feedback" class="detail-content">
      
      <!-- Basic Info -->
      <section class="detail-section">
        <h2 class="section-title">反馈信息</h2>
        <div class="info-grid">
          <div class="info-item">
            <label>问题类型</label>
            <div class="type-badge" :class="feedback.type_value?.toLowerCase()">{{ feedback.type_label }}</div>
          </div>
          <div class="info-item">
            <label>创建时间</label>
            <div>{{ feedback.created_at }}</div>
          </div>
          <div class="info-item full-width">
            <label>用户备注</label>
            <div class="comment-box">{{ feedback.comment || '无备注' }}</div>
          </div>
        </div>
      </section>

      <!-- QA Snapshot -->
      <section class="detail-section">
        <h2 class="section-title">问答快照</h2>
        <div class="qa-box">
          <div class="qa-item user">
            <div class="qa-avatar">User</div>
            <div class="qa-content">{{ feedback.question }}</div>
          </div>
          <div class="qa-item ai">
            <div class="qa-avatar ai-bg">AI</div>
            <div class="qa-content markdown-body" v-html="renderMarkdown(feedback.answer)"></div>
          </div>
        </div>
      </section>

      <!-- Retrieval Snapshot -->
      <section class="detail-section">
        <h2 class="section-title">检索召回快照</h2>
        
        <h3 class="subsection-title">召回文档 ({{ feedback.documents?.length || 0 }})</h3>
        <div class="docs-list" v-if="feedback.documents?.length">
          <div class="doc-card" v-for="doc in feedback.documents" :key="doc.id">
            <div class="doc-icon">📄</div>
            <div class="doc-info">
              <div class="doc-name">{{ doc.name }}</div>
              <div class="doc-meta">
                知识库: {{ doc.collection_name }} | 版本: v{{ doc.version || '未知' }} | 状态: {{ doc.status }}
              </div>
            </div>
            <div class="doc-actions" v-if="doc.status !== 'inactive' && doc.status !== 'deleted'">
              <button class="action-btn offline-btn" @click="handleOfflineDoc(doc)">下架此文档</button>
            </div>
          </div>
        </div>
        <div v-else class="empty-text">未记录召回文档</div>

        <h3 class="subsection-title" style="margin-top: 24px;">召回 Chunk ({{ feedback.chunks?.length || 0 }})</h3>
        <div class="chunks-list" v-if="feedback.chunks?.length">
          <div class="chunk-card" v-for="chunk in feedback.chunks" :key="chunk.chunk_id">
            <div class="chunk-header">
              <span class="chunk-rank">Top {{ chunk.rank }}</span>
              <span class="chunk-score">Score: {{ chunk.score?.toFixed(4) }}</span>
              <span class="chunk-id">ID: {{ chunk.chunk_id }}</span>
              <div style="flex-grow: 1;"></div>
              <button class="action-btn edit-btn-sm" @click="openEditChunkModal(chunk, feedback.documents)">编辑修改</button>
            </div>
            <div class="chunk-content">{{ chunk.content }}</div>
          </div>
        </div>
        <div v-else class="empty-text">未记录召回 Chunk</div>
      </section>

      <!-- Process Logs -->
      <section class="detail-section" v-if="feedback.logs?.length">
        <h2 class="section-title">处理日志</h2>
        <div class="timeline">
          <div class="timeline-item" v-for="(log, idx) in feedback.logs" :key="idx">
            <div class="timeline-marker"></div>
            <div class="timeline-content">
              <div class="log-header">
                <span class="log-action">{{ log.action }}</span>
                <span class="log-time">{{ log.created_at }}</span>
              </div>
              <div class="log-operator">操作人: {{ log.operator }}</div>
              <div class="log-remark" v-if="log.remark">{{ log.remark }}</div>
            </div>
          </div>
        </div>
      </section>

    </div>

    <!-- Ignore Modal -->
    <div v-if="showIgnoreModal" class="modal-overlay" @click="showIgnoreModal = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>忽略反馈</h2>
          <button class="close-btn" @click="showIgnoreModal = false">×</button>
        </div>
        <div class="modal-body">
          <label class="input-label">处理备注 (必填)</label>
          <textarea v-model="ignoreRemark" class="form-textarea" rows="4" placeholder="请输入忽略该反馈的原因..."></textarea>
          <div class="modal-actions">
            <button class="cancel-btn" @click="showIgnoreModal = false">取消</button>
            <button class="submit-btn" @click="submitIgnore" :disabled="!ignoreRemark.trim()">确认忽略</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Chunk Modal -->
    <div v-if="showEditChunkModal" class="modal-overlay" @click="showEditChunkModal = false">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h2>编辑 Chunk (热修复)</h2>
          <button class="close-btn" @click="showEditChunkModal = false">×</button>
        </div>
        <div class="modal-body">
          <label class="input-label">Chunk ID: {{ currentEditChunk?.chunk_id }}</label>
          <textarea v-model="editChunkContent" class="form-textarea" rows="8" placeholder="在此修改 Chunk 文本内容..."></textarea>
          
          <label class="input-label">修复备注 (选填)</label>
          <input type="text" v-model="editChunkRemark" class="form-input" placeholder="例如：修正了错误的日期" />

          <div class="modal-actions" style="margin-top: 24px;">
            <button class="cancel-btn" @click="showEditChunkModal = false" :disabled="isUpdatingChunk">取消</button>
            <button class="submit-btn" @click="submitUpdateChunk" :disabled="!editChunkContent.trim() || isUpdatingChunk">
              {{ isUpdatingChunk ? '正在编码并保存...' : '确认修改并重载' }}
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
import { adminRequest } from '../../services/adminApi'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const route = useRoute()
const router = useRouter()
const feedbackId = route.params.id

const feedback = ref<any>(null)
const loading = ref(false)

const showIgnoreModal = ref(false)
const ignoreRemark = ref('')

const showEditChunkModal = ref(false)
const currentEditChunk = ref<any>(null)
const editChunkContent = ref('')
const editChunkRemark = ref('')
const currentCollectionName = ref('')
const isUpdatingChunk = ref(false)

const renderMarkdown = (text: string) => {
  try {
    const html = marked.parse(text || '') as string
    return DOMPurify.sanitize(html)
  } catch (e) {
    return DOMPurify.sanitize(text || '')
  }
}

const fetchFeedbackDetail = async () => {
  loading.value = true
  try {
    const res = await adminRequest<any>(`/api/admin/feedback/${feedbackId}/`, { method: 'GET' })
    if (res.success) {
      feedback.value = res.data
    } else {
      alert(`获取详情失败: ${res.error}`)
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const openIgnoreModal = () => {
  ignoreRemark.value = ''
  showIgnoreModal.value = true
}

const submitIgnore = async () => {
  if (!ignoreRemark.value.trim()) return
  try {
    const res = await adminRequest<any>(`/api/admin/feedback/${feedbackId}/ignore/`, {
      method: 'POST',
      body: JSON.stringify({ remark: ignoreRemark.value })
    })
    if (res.success) {
      showIgnoreModal.value = false
      await fetchFeedbackDetail()
    } else {
      alert(`操作失败: ${res.error}`)
    }
  } catch (e: any) {
    console.error(e)
    alert(`请求异常: ${e.message || e}`)
  }
}

const handleOfflineDoc = async (doc: any) => {
  const remark = prompt(`确认下架文档 [${doc.name}] 吗？请填写下架备注（选填）：`)
  if (remark === null) return
  
  try {
    const res = await adminRequest<any>(`/api/admin/feedback/${feedbackId}/offline-document/`, {
      method: 'POST',
      body: JSON.stringify({ document_id: doc.id, remark })
    })
    if (res.success) {
      await fetchFeedbackDetail()
    } else {
      alert(`操作失败: ${res.error}`)
    }
  } catch (e: any) {
    console.error(e)
    alert(`请求异常: ${e.message || e}`)
  }
}

const openEditChunkModal = (chunk: any, documents: any[]) => {
  currentEditChunk.value = chunk
  editChunkContent.value = chunk.content
  editChunkRemark.value = ''
  // 查找所属 collectionName，简化处理：通常一个 Feedback 的 docs 在同一个 collection 下
  if (documents && documents.length > 0) {
    currentCollectionName.value = documents[0].collection_name
  } else {
    currentCollectionName.value = feedback.value?.collection_name || ''
  }
  showEditChunkModal.value = true
}

const submitUpdateChunk = async () => {
  if (!editChunkContent.value.trim() || !currentEditChunk.value || isUpdatingChunk.value) return
  isUpdatingChunk.value = true
  try {
    const res = await adminRequest<any>(`/api/admin/feedback/${feedbackId}/edit-chunk/`, {
      method: 'POST',
      body: JSON.stringify({ 
        chunk_id: currentEditChunk.value.chunk_id,
        new_content: editChunkContent.value,
        collection_name: currentCollectionName.value,
        remark: editChunkRemark.value
      })
    })
    if (res.success) {
      showEditChunkModal.value = false
      await fetchFeedbackDetail()
    } else {
      alert(`操作失败: ${res.error}`)
    }
  } catch (e: any) {
    console.error(e)
    alert(`请求异常: ${e.message || e}`)
  } finally {
    isUpdatingChunk.value = false
  }
}

onMounted(() => {
  fetchFeedbackDetail()
})
</script>

<style scoped>
.admin-feedback-detail { padding: 32px; max-width: 1000px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header-left { display: flex; align-items: center; gap: 16px; }
.back-btn { display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 8px; border: 1px solid #e5e7eb; background: white; cursor: pointer; color: #4b5563; transition: all 0.2s; }
.back-btn:hover { background: #f3f4f6; color: #111827; }
.page-title { font-size: 24px; font-weight: 700; color: #111827; margin: 0; }
.header-actions { display: flex; gap: 12px; }
.action-btn { padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s; border: none; }
.ignore-btn { background: #f3f4f6; color: #4b5563; }
.ignore-btn:hover { background: #e5e7eb; }
.offline-btn { background: #fee2e2; color: #b91c1c; }
.offline-btn:hover { background: #fecaca; }
.edit-btn { background: #dbeafe; color: #1d4ed8; }
.edit-btn:hover { background: #bfdbfe; }

.status-badge { padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; }
.status-badge.pending { background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }
.status-badge.processing { background: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; }
.status-badge.resolved { background: #d1fae5; color: #047857; border: 1px solid #a7f3d0; }
.status-badge.ignored { background: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }

.type-badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: 500; background: #f3f4f6; color: #4b5563; }

.detail-section { background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.section-title { font-size: 18px; font-weight: 600; color: #111827; margin-top: 0; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid #f3f4f6; }
.subsection-title { font-size: 15px; font-weight: 600; color: #374151; margin-bottom: 12px; }

.info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.info-item label { display: block; font-size: 13px; font-weight: 500; color: #6b7280; margin-bottom: 8px; }
.info-item.full-width { grid-column: span 2; }
.comment-box { padding: 12px; background: #f9fafb; border-radius: 8px; font-size: 14px; color: #374151; line-height: 1.6; border: 1px solid #f3f4f6; }

.qa-box { display: flex; flex-direction: column; gap: 16px; }
.qa-item { display: flex; gap: 12px; }
.qa-item.user .qa-content { background: #f3f6f8; border-radius: 2px 12px 12px 12px; }
.qa-item.ai .qa-content { background: #f0f7ff; border-radius: 12px 12px 12px 2px; }
.qa-avatar { width: 40px; height: 40px; border-radius: 8px; background: #e2e8f0; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; color: #475569; flex-shrink: 0; }
.qa-avatar.ai-bg { background: #3b82f6; color: white; }
.qa-content { flex: 1; padding: 16px; font-size: 14px; line-height: 1.6; color: #1e293b; }

.docs-list { display: flex; flex-direction: column; gap: 12px; }
.doc-card { display: flex; align-items: center; gap: 16px; padding: 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; }
.doc-icon { font-size: 24px; }
.doc-name { font-weight: 600; color: #0f172a; margin-bottom: 4px; }
.doc-meta { font-size: 12px; color: #64748b; }

.chunks-list { display: flex; flex-direction: column; gap: 16px; }
.chunk-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
.chunk-header { display: flex; gap: 16px; padding: 12px 16px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; font-size: 12px; font-weight: 500; color: #475569; }
.chunk-rank { color: #2563eb; font-weight: 600; }
.chunk-content { padding: 16px; font-size: 14px; line-height: 1.6; color: #334155; white-space: pre-wrap; }

.empty-text { color: #94a3b8; font-size: 14px; font-style: italic; }

.timeline { position: relative; padding-left: 24px; }
.timeline::before { content: ''; position: absolute; top: 0; bottom: 0; left: 6px; width: 2px; background: #e2e8f0; }
.timeline-item { position: relative; margin-bottom: 24px; }
.timeline-item:last-child { margin-bottom: 0; }
.timeline-marker { position: absolute; left: -24px; top: 4px; width: 14px; height: 14px; border-radius: 50%; background: white; border: 2px solid #3b82f6; z-index: 1; }
.timeline-content { background: #f8fafc; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; }
.log-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
.log-action { font-weight: 600; color: #0f172a; }
.log-time { font-size: 12px; color: #64748b; }
.log-operator { font-size: 13px; color: #475569; margin-bottom: 4px; }
.log-remark { font-size: 13px; color: #64748b; background: white; padding: 8px; border-radius: 4px; margin-top: 8px; border: 1px solid #e2e8f0; }

.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: white; border-radius: 12px; width: 480px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); }
.modal-header { padding: 20px 24px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center; }
.modal-header h2 { margin: 0; font-size: 18px; color: #111827; }
.close-btn { background: none; border: none; font-size: 24px; color: #6b7280; cursor: pointer; line-height: 1; }
.modal-body { padding: 24px; }
.input-label { display: block; font-size: 14px; font-weight: 500; color: #374151; margin-bottom: 8px; }
.form-textarea { width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 6px; resize: vertical; font-family: inherit; font-size: 14px; outline: none; margin-bottom: 24px; }
.form-textarea:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.1); }
.modal-actions { display: flex; justify-content: flex-end; gap: 12px; }
.cancel-btn { padding: 8px 16px; border-radius: 6px; font-weight: 500; background: white; border: 1px solid #d1d5db; color: #374151; cursor: pointer; }
.submit-btn { padding: 8px 16px; border-radius: 6px; font-weight: 500; background: #3b82f6; border: none; color: white; cursor: pointer; }
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.modal-content.large { width: 600px; }
.form-input { width: 100%; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-family: inherit; font-size: 14px; outline: none; margin-bottom: 8px; }
.form-input:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.1); }
.edit-btn-sm { padding: 4px 10px; background: #e0e7ff; color: #4338ca; border-radius: 4px; border: none; cursor: pointer; font-size: 12px; font-weight: 600; }
.edit-btn-sm:hover { background: #c7d2fe; }
.doc-card { display: flex; align-items: center; justify-content: space-between; padding: 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; }
.doc-info-wrapper { display: flex; align-items: center; gap: 16px; }
</style>
