<template>
  <div class="dashboard-view">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p class="loading-text">正在加载控制看板实时数据...</p>
    </div>

    <template v-else>
      <!-- 四大 KPI 统计卡片 -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon-wrapper kb-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
            </svg>
          </div>
          <div class="stat-content">
            <span class="stat-label">知识库总数</span>
            <h2 class="stat-value">{{ stats.kb_total }}</h2>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon-wrapper doc-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
          </div>
          <div class="stat-content">
            <span class="stat-label">逻辑文档总数</span>
            <h2 class="stat-value">{{ stats.doc_total }}</h2>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon-wrapper chunk-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="21" y1="10" x2="3" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/><line x1="21" y1="14" x2="3" y2="14"/><line x1="21" y1="18" x2="3" y2="18"/>
            </svg>
          </div>
          <div class="stat-content">
            <span class="stat-label">数据 Chunks 总数</span>
            <h2 class="stat-value">{{ formatNumber(stats.chunk_total) }}</h2>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon-wrapper vector-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"/>
              <line x1="12" y1="22" x2="12" y2="12"/><line x1="22" y1="8.5" x2="12" y2="12"/><line x1="2" y1="8.5" x2="12" y2="12"/>
            </svg>
          </div>
          <div class="stat-content">
            <span class="stat-label">向量 Embeddings 数</span>
            <h2 class="stat-value">{{ formatNumber(stats.embedding_total) }}</h2>
          </div>
        </div>
      </div>

      <!-- 双栏展示区 (最近上传 & 最近审计日志) -->
      <div class="dashboard-sections">
        <!-- 左侧：最近文件入库列表 -->
        <div class="section-card">
          <div class="section-header">
            <h3 class="section-title">
              <svg class="title-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 5v14M5 12h14"/>
              </svg>
              最近导入文档
            </h3>
            <router-link to="/rag-admin/documents" class="view-all-link">全部文档</router-link>
          </div>

          <div class="files-list">
            <div v-if="stats.recent_files.length === 0" class="empty-state">
              <span>暂无最近导入文件</span>
            </div>
            
            <div
              v-for="file in stats.recent_files"
              :key="file.id"
              class="file-item"
              @click="goToDetail(file.document_id)"
            >
              <div class="file-info">
                <div class="file-icon-bg">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                  </svg>
                </div>
                <div class="file-meta">
                  <span class="file-name" :title="file.name">{{ file.name }}</span>
                  <span class="file-kb">{{ file.kb_name }}</span>
                </div>
              </div>
              
              <div class="file-badges">
                <span class="badge version-badge">{{ file.version }}</span>
                <span class="badge size-badge">{{ formatBytes(file.size) }}</span>
                <span class="status-badge" :class="{
                'active': file.status === 'active',
                'disabled': file.status === 'inactive' || file.status === 'deleted'
              }">{{ file.status === 'active' ? '已启用' : (file.status === 'inactive' ? '已禁用' : '已删除') }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧：审计日志时间轴 -->
        <div class="section-card">
          <div class="section-header">
            <h3 class="section-title">
              <svg class="title-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
              </svg>
              管理员审计日志
            </h3>
            <router-link to="/rag-admin/settings" class="view-all-link">全部审计</router-link>
          </div>

          <div class="logs-timeline">
            <div v-if="stats.operation_logs.length === 0" class="empty-state">
              <span>暂无管理员审计日志</span>
            </div>
            
            <div
              v-for="log in stats.operation_logs"
              :key="log.id"
              class="timeline-item"
            >
              <div class="timeline-dot" :class="log.action.toLowerCase()"></div>
              <div class="timeline-content">
                <div class="log-meta">
                  <span class="log-user">{{ log.admin_username }}</span>
                  <span class="log-time">{{ formatTime(log.created_at) }}</span>
                </div>
                <p class="log-details">{{ log.details }}</p>
                <div class="log-tag" :class="log.action.toLowerCase()">{{ log.action }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getDashboardStats, type AdminStats } from '@/services/adminApi'

const router = useRouter()
const loading = ref(true)
const stats = ref<AdminStats>({
  kb_total: 0,
  doc_total: 0,
  chunk_total: 0,
  embedding_total: 0,
  recent_files: [],
  operation_logs: []
})

const fetchStats = async () => {
  try {
    loading.value = true
    const res = await getDashboardStats()
    if (res.success && res.data) {
      stats.value = res.data
    }
  } catch (error) {
    console.error('加载看板统计异常:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStats()
})

const goToDetail = (docId: string) => {
  router.push(`/rag-admin/documents/${docId}`)
}

// 格式化数据辅助方法
const formatNumber = (num: number): string => {
  return num.toLocaleString()
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatTime = (timeStr: string): string => {
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.dashboard-view {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* KPI 看板样式 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 24px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(99, 102, 241, 0.08);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.02);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: default;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 30px rgba(99, 102, 241, 0.08);
  border-color: rgba(99, 102, 241, 0.2);
}

.stat-icon-wrapper {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.kb-icon {
  background-color: rgba(99, 102, 241, 0.08);
  color: #6366F1;
}

.doc-icon {
  background-color: rgba(129, 140, 248, 0.08);
  color: #818CF8;
}

.chunk-icon {
  background-color: rgba(16, 185, 129, 0.08);
  color: #10B981;
}

.vector-icon {
  background-color: rgba(244, 63, 94, 0.08);
  color: #F43F5E;
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 0.85rem;
  font-weight: 500;
  color: #64748B;
}

.stat-value {
  font-family: 'Fira Code', monospace;
  font-size: 1.8rem;
  font-weight: 700;
  color: #1E1B4B;
  margin: 0;
}

/* 双栏排版 */
.dashboard-sections {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
}

@media (max-width: 1024px) {
  .dashboard-sections {
    grid-template-columns: 1fr;
  }
}

.section-card {
  background-color: #ffffff;
  border: 1px solid rgba(99, 102, 241, 0.06);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.01);
  display: flex;
  flex-direction: column;
  min-height: 400px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.06);
  padding-bottom: 16px;
}

.section-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1E1B4B;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}

.title-icon {
  color: #6366F1;
}

.view-all-link {
  font-size: 0.85rem;
  font-weight: 600;
  color: #6366F1;
  text-decoration: none;
  transition: opacity 0.2s;
}

.view-all-link:hover {
  opacity: 0.8;
}

/* 最近上传文档列表 */
.files-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-radius: 10px;
  background-color: #F9FAFB;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
}

.file-item:hover {
  background-color: rgba(99, 102, 241, 0.03);
  border-color: rgba(99, 102, 241, 0.1);
  transform: translateX(4px);
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.file-icon-bg {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  background-color: rgba(99, 102, 241, 0.05);
  color: #818CF8;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.file-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1E1B4B;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-kb {
  font-size: 0.75rem;
  color: #64748B;
}

.file-badges {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.badge {
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.version-badge {
  background-color: #E0E7FF;
  color: #4F46E5;
}

.size-badge {
  background-color: #F3F4F6;
  color: #4B5563;
}

.badge-status {
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.badge-status.active {
  background-color: rgba(16, 185, 129, 0.1);
  color: #10B981;
}

.badge-status.disabled {
  background-color: rgba(244, 63, 94, 0.1);
  color: #F43F5E;
}

.badge-status.deleted {
  background-color: #E5E7EB;
  color: #9CA3AF;
}

/* 审计日志时间轴样式 */
.logs-timeline {
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;
  padding-left: 20px;
  flex: 1;
}

.logs-timeline::before {
  content: "";
  position: absolute;
  left: 5px;
  top: 5px;
  bottom: 5px;
  width: 2px;
  background-color: #E2E8F0;
}

.timeline-item {
  position: relative;
  display: flex;
  flex-direction: column;
}

.timeline-dot {
  position: absolute;
  left: -20px;
  top: 4px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #ffffff;
  box-shadow: 0 0 0 2px #E2E8F0;
  z-index: 2;
}

.timeline-dot.login { background-color: #6366F1; box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2); }
.timeline-dot.create_kb { background-color: #10B981; box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2); }
.timeline-dot.delete_kb { background-color: #F43F5E; box-shadow: 0 0 0 2px rgba(244, 63, 94, 0.2); }
.timeline-dot.upload_doc { background-color: #818CF8; box-shadow: 0 0 0 2px rgba(129, 140, 248, 0.2); }
.timeline-dot.disable_doc { background-color: #FBBF24; box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.2); }
.timeline-dot.enable_doc { background-color: #10B981; box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2); }
.timeline-dot.upload_version { background-color: #6366F1; box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2); }
.timeline-dot.rollback_ver { background-color: #EC4899; box-shadow: 0 0 0 2px rgba(236, 72, 153, 0.2); }

.timeline-content {
  background-color: #F9FAFB;
  border-radius: 10px;
  padding: 12px;
  border: 1px solid rgba(99, 102, 241, 0.03);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.log-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.log-user {
  font-size: 0.85rem;
  font-weight: 600;
  color: #1E1B4B;
}

.log-time {
  font-size: 0.75rem;
  color: #94A3B8;
}

.log-details {
  font-size: 0.85rem;
  color: #4B5563;
  line-height: 1.4;
  margin: 0;
}

.log-tag {
  align-self: flex-start;
  font-family: 'Fira Code', monospace;
  font-size: 0.65rem;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
}

.log-tag.login { background-color: rgba(99, 102, 241, 0.1); color: #6366F1; }
.log-tag.create_kb { background-color: rgba(16, 185, 129, 0.1); color: #10B981; }
.log-tag.delete_kb { background-color: rgba(244, 63, 94, 0.1); color: #F43F5E; }
.log-tag.upload_doc { background-color: rgba(129, 140, 248, 0.1); color: #818CF8; }
.log-tag.disable_doc { background-color: rgba(245, 158, 11, 0.1); color: #FBBF24; }
.log-tag.enable_doc { background-color: rgba(16, 185, 129, 0.1); color: #10B981; }
.log-tag.upload_version { background-color: rgba(99, 102, 241, 0.1); color: #6366F1; }
.log-tag.rollback_ver { background-color: rgba(236, 72, 153, 0.1); color: #EC4899; }

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

.loading-text {
  color: #64748B;
  font-size: 0.95rem;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem 0;
  color: #94A3B8;
  font-size: 0.85rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
