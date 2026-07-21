<template>
  <div class="chunk-results">
    <div class="results-card">
      <div class="results-header">
        <div class="header-info">
          <h3>分块结果</h3>
          <p>使用 <span class="chunker-name">{{ chunkerName }}</span> 处理完成</p>
        </div>
        <div class="results-stats">
          <div class="stat-item">
            <span class="stat-number">{{ chunks.length }}</span>
            <span class="stat-label">个分块</span>
          </div>
          <div class="stat-item">
            <span class="stat-number">{{ totalCharacters }}</span>
            <span class="stat-label">总字符</span>
          </div>
        </div>
      </div>
      
      <div class="results-controls">
        <div class="view-controls">
          <button 
            class="view-btn"
            :class="{ active: viewMode === 'list' }"
            @click="viewMode = 'list'"
          >
            列表视图
          </button>
          <button 
            class="view-btn"
            :class="{ active: viewMode === 'grid' }"
            @click="viewMode = 'grid'"
          >
            网格视图
          </button>
        </div>
        
        <div class="filter-controls">
          <input 
            v-model="searchQuery"
            type="text"
            placeholder="搜索分块内容..."
            class="search-input"
          />
          <select v-model="sortBy" class="sort-select">
            <option value="id">按序号排序</option>
            <option value="size">按大小排序</option>
            <option value="content">按内容排序</option>
          </select>
        </div>
      </div>
      
      <div class="chunks-container" :class="viewMode">
        <div 
          v-for="(chunk, index) in filteredChunks" 
          :key="chunk.id"
          class="chunk-item"
          :class="{ 'expanded': expandedChunks.includes(chunk.id) }"
        >
          <div class="chunk-header" @click="toggleExpand(chunk.id)">
            <div class="chunk-info">
              <span class="chunk-id">#{{ chunk.id }}</span>
              <span class="chunk-type" v-if="chunk.modality_type">
                {{ getModalityTypeName(chunk.modality_type) }}
              </span>
              <span class="chunk-size" v-if="chunk.metadata.chunkSize">
                {{ chunk.metadata.chunkSize }} 字符
              </span>
              <span class="chunk-size" v-else-if="chunk.modality_type === 'image'">
                图片
              </span>
            </div>
            <div class="chunk-actions">
              <button 
                class="action-btn copy-btn"
                @click.stop="copyChunk(chunk)"
                title="复制内容"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              </button>
              <button 
                class="action-btn expand-btn"
                :class="{ 'expanded': expandedChunks.includes(chunk.id) }"
              >
                {{ expandedChunks.includes(chunk.id) ? '−' : '+' }}
              </button>
            </div>
          </div>
          
          <div class="chunk-content" v-show="expandedChunks.includes(chunk.id)">
            <!-- 文本内容 -->
            <div v-if="!chunk.modality_type || chunk.modality_type === 'text'" class="content-text">
              {{ chunk.content }}
            </div>
            
            <!-- 图片内容 -->
            <div v-else-if="chunk.modality_type === 'image'" class="content-image">
              <img 
                :src="getImageSrc(chunk)" 
                :alt="chunk.metadata.image_name || '提取的图片'"
                @error="handleImageError"
                class="extracted-image"
              />
              <div class="image-info" v-if="chunk.metadata.image_name">
                <span class="image-name">{{ chunk.metadata.image_name }}</span>
              </div>
            </div>
            
            <!-- 其他类型内容 -->
            <div v-else class="content-text">
              {{ chunk.content }}
            </div>
            
            <div class="chunk-metadata">
              <div class="metadata-item" v-if="chunk.metadata.chunker">
                <span class="label">分块器:</span>
                <span class="value">{{ chunk.metadata.chunker }}</span>
              </div>
              <div class="metadata-item" v-if="chunk.metadata.position !== undefined">
                <span class="label">位置:</span>
                <span class="value">{{ chunk.metadata.position }}</span>
              </div>
              <div class="metadata-item" v-if="chunk.metadata.chunkSize">
                <span class="label">大小:</span>
                <span class="value">{{ chunk.metadata.chunkSize }} 字符</span>
              </div>
              <div class="metadata-item" v-if="chunk.modality_type">
                <span class="label">类型:</span>
                <span class="value">{{ getModalityTypeName(chunk.modality_type) }}</span>
              </div>
              <div class="metadata-item" v-if="chunk.metadata.image_index">
                <span class="label">图片序号:</span>
                <span class="value">{{ chunk.metadata.image_index }} / {{ chunk.metadata.total_images }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div v-if="filteredChunks.length === 0" class="no-results">
        <div class="no-results-icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        </div>
        <p>没有找到匹配的分块内容</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

// Props
const props = defineProps<{
  chunks: Array<{
    id: number
    content: string
    modality_type?: string  // 'text' | 'image' | 'video'
    metadata: {
      chunkSize?: number
      position?: number
      chunker?: string
      image_url?: string
      image_path?: string
      [key: string]: any
    }
  }>
  chunkerName: string
  isProcessing?: boolean
}>()

// 响应式数据
const viewMode = ref<'list' | 'grid'>('list')
const searchQuery = ref('')
const sortBy = ref<'id' | 'size' | 'content'>('id')
const expandedChunks = ref<number[]>([])

// 计算属性
const totalCharacters = computed(() => {
  return props.chunks.reduce((total, chunk) => total + (chunk.metadata.chunkSize || 0), 0)
})

const filteredChunks = computed(() => {
  let filtered = [...props.chunks]
  
  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(chunk => 
      chunk.content.toLowerCase().includes(query)
    )
  }
  
  // 排序
  filtered.sort((a, b) => {
    switch (sortBy.value) {
      case 'size':
        return (b.metadata.chunkSize || 0) - (a.metadata.chunkSize || 0)
      case 'content':
        return a.content.localeCompare(b.content)
      case 'id':
      default:
        return a.id - b.id
    }
  })
  
  return filtered
})

// 方法
const toggleExpand = (chunkId: number) => {
  const index = expandedChunks.value.indexOf(chunkId)
  if (index > -1) {
    expandedChunks.value.splice(index, 1)
  } else {
    expandedChunks.value.push(chunkId)
  }
}

const copyChunk = async (chunk: any) => {
  try {
    if (chunk.modality_type === 'image') {
      // 如果是图片，尝试复制图片URL
      const imageUrl = getImageSrc(chunk)
      await navigator.clipboard.writeText(imageUrl)
      console.log('图片URL已复制到剪贴板')
    } else {
      await navigator.clipboard.writeText(chunk.content)
      console.log('内容已复制到剪贴板')
    }
  } catch (err) {
    console.error('复制失败:', err)
  }
}

// 获取图片源（URL或base64）
const getImageSrc = (chunk: any): string => {
  if (chunk.modality_type === 'image') {
    // 优先使用metadata中的image_url
    if (chunk.metadata?.image_url) {
      // 确保是完整URL
      if (chunk.metadata.image_url.startsWith('http')) {
        return chunk.metadata.image_url
      }
      // 如果是相对路径，添加API基础URL
      const apiBaseUrl = 'http://8.136.10.252:8000'
      return `${apiBaseUrl}${chunk.metadata.image_url}`
    }
    // 如果content是URL（不以data:开头）
    if (chunk.content && !chunk.content.startsWith('data:')) {
      if (chunk.content.startsWith('http')) {
        return chunk.content
      }
      const apiBaseUrl = 'http://8.136.10.252:8000'
      return `${apiBaseUrl}${chunk.content}`
    }
    // 如果content是base64
    if (chunk.content && chunk.content.startsWith('data:')) {
      return chunk.content
    }
  }
  return ''
}

// 图片加载错误处理
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23f3f4f6" width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%239ca3af" font-family="sans-serif" font-size="14"%3E图片加载失败%3C/text%3E%3C/svg%3E'
}

// 获取模态类型显示名称
const getModalityTypeName = (type: string): string => {
  const typeMap: Record<string, string> = {
    'text': '文本',
    'image': '图片',
    'video': '视频'
  }
  return typeMap[type] || type
}
</script>

<style scoped>
.chunk-results {
  margin-bottom: 2rem;
}

.results-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2rem;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.header-info h3 {
  margin: 0 0 0.5rem 0;
  color: #374151;
  font-size: 1.5rem;
  font-weight: 600;
}

.header-info p {
  margin: 0;
  color: #6b7280;
  font-size: 1rem;
}

.chunker-name {
  color: #10b981;
  font-weight: 600;
}

.results-stats {
  display: flex;
  gap: 2rem;
}

.stat-item {
  text-align: center;
}

.stat-number {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: #374151;
}

.stat-label {
  font-size: 0.875rem;
  color: #6b7280;
}

.results-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid #e5e7eb;
  gap: 1rem;
  flex-wrap: wrap;
}

.view-controls {
  display: flex;
  gap: 0.5rem;
}

.view-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #d1d5db;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.875rem;
}

.view-btn:hover {
  border-color: #667eea;
  background: #f8f9ff;
}

.view-btn.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.filter-controls {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.search-input {
  padding: 0.5rem 1rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.875rem;
  min-width: 200px;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.sort-select {
  padding: 0.5rem 1rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.875rem;
  background: white;
}

.chunks-container {
  max-height: 600px;
  overflow-y: auto;
}

.chunks-container.list {
  padding: 1rem 2rem;
}

.chunks-container.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
  padding: 1rem 2rem;
}

.chunk-item {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fafbfc;
  transition: all 0.3s ease;
  margin-bottom: 1rem;
}

.chunk-item:hover {
  border-color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
}

.chunk-item.expanded {
  border-color: #10b981;
  background: #f0fdf4;
}

.chunk-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  cursor: pointer;
  border-bottom: 1px solid #e5e7eb;
}

.chunk-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.chunk-id {
  background: #667eea;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}

.chunk-size {
  color: #6b7280;
  font-size: 0.875rem;
}

.chunk-type {
  background: #10b981;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-left: 0.5rem;
}

.chunk-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  font-size: 0.875rem;
}

.copy-btn {
  background: #e5e7eb;
  color: #374151;
}

.copy-btn:hover {
  background: #d1d5db;
}

.expand-btn {
  background: #f3f4f6;
  color: #374151;
  font-weight: 600;
}

.expand-btn:hover {
  background: #e5e7eb;
}

.expand-btn.expanded {
  background: #10b981;
  color: white;
}

.chunk-content {
  padding: 1.5rem;
}

.content-text {
  color: #374151;
  line-height: 1.6;
  margin-bottom: 1rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.content-image {
  margin-bottom: 1rem;
}

.extracted-image {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 0.5rem;
  display: block;
}

.image-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #6b7280;
  font-size: 0.875rem;
}

.image-name {
  font-weight: 500;
}

.chunk-metadata {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.metadata-item {
  display: flex;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.label {
  color: #6b7280;
  font-weight: 500;
}

.value {
  color: #374151;
  font-weight: 600;
}

.no-results {
  text-align: center;
  padding: 3rem;
  color: #6b7280;
}

.no-results-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

@media (max-width: 768px) {
  .results-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }
  
  .results-stats {
    gap: 1rem;
  }
  
  .results-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-controls {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .search-input {
    min-width: auto;
  }
  
  .chunks-container.grid {
    grid-template-columns: 1fr;
  }
  
  .chunk-metadata {
    flex-direction: column;
    gap: 0.5rem;
  }
}
</style>
