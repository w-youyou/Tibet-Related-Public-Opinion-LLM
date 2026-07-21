<template>
  <div class="admin-feedback-list">
    <div class="page-header">
      <h1 class="page-title">反馈管理</h1>
      <p class="page-subtitle">查看和处理用户关于 RAG 问答质量的反馈</p>
    </div>

    <div class="filter-bar">
      <div class="filter-item">
        <label>时间范围</label>
        <select v-model="filters.timeRange" @change="fetchFeedbacks">
          <option value="all">全部</option>
          <option value="7d">最近7天</option>
          <option value="30d">最近1个月</option>
        </select>
      </div>
      <div class="filter-item">
        <label>状态</label>
        <select v-model="filters.status" @change="fetchFeedbacks">
          <option value="">全部</option>
          <option value="PENDING">待处理</option>
          <option value="PROCESSING">处理中</option>
          <option value="RESOLVED">已解决</option>
          <option value="IGNORED">已忽略</option>
        </select>
      </div>
      <div class="filter-item">
        <label>类型</label>
        <select v-model="filters.type" @change="fetchFeedbacks">
          <option value="">全部</option>
          <option v-for="type in typeOptions" :key="type.value" :value="type.value">{{ type.label }}</option>
        </select>
      </div>
      <div class="filter-item search-item">
        <input type="text" v-model="filters.keyword" placeholder="搜索问题、回答或备注..." @keyup.enter="fetchFeedbacks" />
        <button class="search-btn" @click="fetchFeedbacks">搜索</button>
      </div>
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th width="80">ID</th>
            <th>反馈类型</th>
            <th>用户提问 (摘要)</th>
            <th width="120">状态</th>
            <th width="150">创建时间</th>
            <th width="120">处理人</th>
            <th width="120">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7" class="loading-state">加载中...</td>
          </tr>
          <tr v-else-if="feedbacks.length === 0">
            <td colspan="7" class="empty-state">暂无反馈记录</td>
          </tr>
          <tr v-else v-for="item in feedbacks" :key="item.id">
            <td>#{{ item.id }}</td>
            <td>
              <span class="type-badge" :class="item.type_value.toLowerCase()">{{ item.type_label }}</span>
            </td>
            <td class="text-truncate" :title="item.question">{{ item.question }}</td>
            <td>
              <span class="status-badge" :class="item.status.toLowerCase()">{{ item.status_label }}</span>
            </td>
            <td>{{ item.created_at }}</td>
            <td>{{ item.handler || '-' }}</td>
            <td>
              <router-link :to="`/rag-admin/feedbacks/${item.id}`" class="action-link">查看/处理</router-link>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminRequest } from '../../services/adminApi'

const feedbacks = ref<any[]>([])
const loading = ref(false)
const typeOptions = ref<any[]>([])

const filters = ref({
  status: 'PENDING',
  type: '',
  keyword: '',
  timeRange: 'all'
})

const fetchTypeOptions = async () => {
  try {
    const res = await adminRequest<any>('/api/chat/feedback-types/', { method: 'GET' })
    if (res.success) {
      typeOptions.value = res.data
    }
  } catch (error) {
    console.error('Failed to fetch type options', error)
  }
}

const fetchFeedbacks = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (filters.value.status) params.append('status', filters.value.status)
    if (filters.value.type) params.append('type', filters.value.type)
    if (filters.value.keyword) params.append('keyword', filters.value.keyword)
    if (filters.value.timeRange && filters.value.timeRange !== 'all') {
      params.append('time_range', filters.value.timeRange)
    }
    
    const res = await adminRequest<any>(`/api/admin/feedback/?${params.toString()}`, { method: 'GET' })
    if (res.success) {
      feedbacks.value = res.data
    }
  } catch (error) {
    console.error('Failed to fetch feedbacks', error)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await fetchTypeOptions()
  await fetchFeedbacks()
})
</script>

<style scoped>
.admin-feedback-list { padding: 32px; max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 28px; font-weight: 700; color: #111827; margin-bottom: 8px; }
.page-subtitle { font-size: 15px; color: #6b7280; }

.filter-bar { display: flex; gap: 16px; margin-bottom: 24px; align-items: center; background: white; padding: 16px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.filter-item { display: flex; align-items: center; gap: 8px; }
.filter-item label { font-size: 14px; font-weight: 500; color: #4b5563; }
.filter-item select, .filter-item input { padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; outline: none; }
.filter-item select:focus, .filter-item input:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.1); }
.search-item { flex: 1; display: flex; gap: 8px; }
.search-item input { flex: 1; }
.search-btn { padding: 8px 16px; background: #3b82f6; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s; }
.search-btn:hover { background: #2563eb; }

.table-container { background: white; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); overflow: hidden; }
.data-table { width: 100%; border-collapse: collapse; text-align: left; }
.data-table th { background: #f9fafb; padding: 16px; font-size: 13px; font-weight: 600; color: #6b7280; text-transform: uppercase; border-bottom: 1px solid #e5e7eb; }
.data-table td { padding: 16px; font-size: 14px; color: #374151; border-bottom: 1px solid #e5e7eb; }
.data-table tr:hover { background: #f9fafb; }
.text-truncate { max-width: 300px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.type-badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; background: #f3f4f6; color: #4b5563; }
.type-badge.answer_error { background: #fee2e2; color: #b91c1c; }
.type-badge.hallucination { background: #fef3c7; color: #b45309; }
.type-badge.document_outdated { background: #e0e7ff; color: #4338ca; }
.type-badge.retrieval_error { background: #ffedd5; color: #c2410c; }

.status-badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.status-badge.pending { background: #fef3c7; color: #b45309; }
.status-badge.processing { background: #dbeafe; color: #1d4ed8; }
.status-badge.resolved { background: #d1fae5; color: #047857; }
.status-badge.ignored { background: #f3f4f6; color: #4b5563; }

.action-link { color: #3b82f6; text-decoration: none; font-weight: 500; }
.action-link:hover { text-decoration: underline; color: #2563eb; }

.loading-state, .empty-state { text-align: center; padding: 48px !important; color: #6b7280; font-size: 14px; }
</style>
