<template>
  <div class="timeline-page">
    <div class="timeline-header">
      <h1 class="page-title">舆情时间线</h1>
      <p class="page-subtitle">从知识库中提取的涉藏舆情事件时间线</p>
    </div>

    <div class="timeline-controls">
      <div class="control-group">
        <label>选择知识库</label>
        <select v-model="selectedKbId" @change="fetchTimeline" class="kb-select">
          <option value="">请选择知识库</option>
          <option v-for="kb in knowledgeBases" :key="kb.id" :value="kb.id">
            {{ kb.name }}
          </option>
        </select>
      </div>
      <div class="control-group">
        <label>搜索关键词</label>
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="输入关键词过滤事件..." 
          class="search-input"
          @keyup.enter="fetchTimeline"
        />
      </div>
      <div class="control-group">
        <label>年份范围</label>
        <div class="year-range">
          <input v-model.number="startYear" type="number" placeholder="起始" class="year-input" />
          <span>—</span>
          <input v-model.number="endYear" type="number" placeholder="结束" class="year-input" />
        </div>
      </div>
      <button @click="fetchTimeline" :disabled="!selectedKbId || isLoading" class="fetch-btn">
        <span v-if="isLoading" class="spinner"></span>
        <span v-else>提取时间线</span>
      </button>
    </div>

    <div v-if="stats" class="timeline-stats">
      <div class="stat-item">
        <span class="stat-value">{{ stats.total_events }}</span>
        <span class="stat-label">总事件数</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ stats.event_count }}</span>
        <span class="stat-label">关键事件</span>
      </div>
      <div class="stat-item" v-if="stats.year_range">
        <span class="stat-value">{{ stats.year_range[0] }} - {{ stats.year_range[1] }}</span>
        <span class="stat-label">时间跨度</span>
      </div>
    </div>

    <div v-if="isLoading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>正在提取时间线数据...</p>
    </div>

    <div v-else-if="events.length > 0" class="timeline-container">
      <div class="timeline">
        <div 
          v-for="(event, index) in events" 
          :key="index" 
          class="timeline-item"
          :class="{ 'is-event': event.is_event }"
        >
          <div class="timeline-marker">
            <div class="marker-dot" :class="{ 'event-dot': event.is_event }"></div>
            <div v-if="index < events.length - 1" class="marker-line"></div>
          </div>
          <div class="timeline-content">
            <div class="event-date">
              <span class="date-text">{{ event.date_str || '日期未知' }}</span>
              <span v-if="event.is_event" class="event-badge">事件</span>
            </div>
            <h3 class="event-title">{{ event.title }}</h3>
            <p class="event-description">{{ event.description }}</p>
            <div class="event-meta">
              <span class="source-file">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                </svg>
                {{ event.source_file }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="hasSearched" class="empty-state">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <p>未找到时间线数据</p>
      <p class="empty-hint">请尝试选择其他知识库或调整搜索条件</p>
    </div>

    <div v-else class="initial-state">
      <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
      </svg>
      <p>选择知识库并点击"提取时间线"开始</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listKnowledgeBases, type KnowledgeBase } from '../services/api'

interface TimelineEvent {
  date: string | null
  date_str: string
  year: number | null
  title: string
  description: string
  source_file: string
  chunk_id?: string
  is_event: boolean
  relevance_score: number
}

interface TimelineStats {
  total_events: number
  event_count: number
  year_range: [number, number] | null
}

const knowledgeBases = ref<KnowledgeBase[]>([])
const selectedKbId = ref('')
const searchQuery = ref('')
const startYear = ref<number | null>(null)
const endYear = ref<number | null>(null)
const events = ref<TimelineEvent[]>([])
const stats = ref<TimelineStats | null>(null)
const isLoading = ref(false)
const hasSearched = ref(false)

const fetchTimeline = async () => {
  if (!selectedKbId.value) return
  
  isLoading.value = true
  hasSearched.value = true
  
  try {
    const payload: any = {
      knowledge_base_id: selectedKbId.value,
    }
    
    if (searchQuery.value.trim()) {
      payload.query = searchQuery.value.trim()
    }
    
    if (startYear.value && endYear.value) {
      payload.year_range = [startYear.value, endYear.value]
    }
    
    const response = await fetch('/api/timeline/extract/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
    })
    
    const data = await response.json()
    
    if (data.success) {
      events.value = data.events || []
      stats.value = data.stats || null
    } else {
      console.error('Failed to fetch timeline:', data.error)
      events.value = []
      stats.value = null
    }
  } catch (error) {
    console.error('Timeline fetch error:', error)
    events.value = []
    stats.value = null
  } finally {
    isLoading.value = false
  }
}

onMounted(async () => {
  try {
    const res = await listKnowledgeBases()
    if (res.success && res.knowledge_bases) {
      knowledgeBases.value = res.knowledge_bases
    }
  } catch (error) {
    console.error('Failed to load knowledge bases:', error)
  }
})
</script>

<style scoped>
.timeline-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 32px 24px;
}

.timeline-header {
  margin-bottom: 32px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 15px;
  color: #6b7280;
  margin: 0;
}

.timeline-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: flex-end;
  padding: 20px;
  background: #f9fafb;
  border-radius: 12px;
  margin-bottom: 24px;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.control-group label {
  font-size: 13px;
  font-weight: 500;
  color: #4b5563;
}

.kb-select, .search-input, .year-input {
  padding: 10px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  background: white;
  transition: border-color 0.2s;
}

.kb-select:focus, .search-input:focus, .year-input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.kb-select {
  min-width: 200px;
}

.search-input {
  min-width: 220px;
}

.year-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.year-input {
  width: 80px;
}

.fetch-btn {
  padding: 10px 20px;
  background: #6366f1;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.fetch-btn:hover:not(:disabled) {
  background: #4f46e5;
  transform: translateY(-1px);
}

.fetch-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.timeline-stats {
  display: flex;
  gap: 24px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  margin-bottom: 24px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: white;
}

.stat-label {
  font-size: 12px;
  color: rgba(255,255,255,0.8);
  margin-top: 4px;
}

.loading-state, .empty-state, .initial-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #6b7280;
  text-align: center;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e5e7eb;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

.empty-state svg, .initial-state svg {
  color: #d1d5db;
  margin-bottom: 16px;
}

.empty-hint {
  font-size: 13px;
  color: #9ca3af;
  margin-top: 8px;
}

/* Timeline styles */
.timeline-container {
  padding: 20px 0;
}

.timeline {
  position: relative;
}

.timeline-item {
  display: flex;
  gap: 20px;
  margin-bottom: 8px;
}

.timeline-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 20px;
  flex-shrink: 0;
}

.marker-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #d1d5db;
  border: 2px solid white;
  box-shadow: 0 0 0 2px #d1d5db;
  flex-shrink: 0;
  margin-top: 4px;
}

.marker-dot.event-dot {
  background: #6366f1;
  box-shadow: 0 0 0 2px #6366f1;
  width: 14px;
  height: 14px;
}

.marker-line {
  width: 2px;
  flex: 1;
  background: #e5e7eb;
  margin-top: 4px;
}

.timeline-content {
  flex: 1;
  padding: 12px 16px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  margin-bottom: 12px;
  transition: all 0.2s;
}

.timeline-content:hover {
  border-color: #c7d2fe;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.08);
}

.timeline-item.is-event .timeline-content {
  border-left: 3px solid #6366f1;
  background: #fafafe;
}

.event-date {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.date-text {
  font-size: 13px;
  font-weight: 600;
  color: #6366f1;
}

.event-badge {
  font-size: 11px;
  padding: 2px 8px;
  background: #e0e7ff;
  color: #4338ca;
  border-radius: 10px;
  font-weight: 500;
}

.event-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
  line-height: 1.4;
}

.event-description {
  font-size: 14px;
  color: #4b5563;
  line-height: 1.6;
  margin: 0 0 12px 0;
}

.event-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.source-file {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #6b7280;
}

.source-file svg {
  color: #9ca3af;
}

/* Responsive */
@media (max-width: 768px) {
  .timeline-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .kb-select, .search-input {
    min-width: auto;
    width: 100%;
  }
  
  .timeline-stats {
    flex-wrap: wrap;
    gap: 16px;
  }
}
</style>