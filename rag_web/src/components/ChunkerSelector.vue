<template>
  <div class="chunker-selector">
    <div class="selector-card">
      <div class="card-header">
        <h3>选择分块策略</h3>
        <p>不同的分块器适用于不同类型的文档和场景</p>
      </div>
      
      <div class="chunker-grid">
        <div 
          v-for="chunker in chunkers" 
          :key="chunker.id"
          class="chunker-option"
          :class="{ 
            'selected': selectedChunker === chunker.id,
            'disabled': isProcessing 
          }"
          @click="selectChunker(chunker.id)"
        >
          <div class="chunker-icon">{{ chunker.icon }}</div>
          <div class="chunker-info">
            <h4>{{ chunker.name }}</h4>
            <p>{{ chunker.description }}</p>
            <div class="chunker-features">
              <span 
                v-for="feature in chunker.features" 
                :key="feature"
                class="feature-tag"
              >
                {{ feature }}
              </span>
            </div>
          </div>
          <div class="chunker-status">
            <div v-if="selectedChunker === chunker.id" class="selected-indicator">
              ✓
            </div>
          </div>
        </div>
      </div>
      
      <div class="action-buttons">
        <button 
          class="process-btn"
          :disabled="!selectedChunker || isProcessing"
          @click="processDocument"
        >
          <span v-if="!isProcessing">开始分块处理</span>
          <span v-else class="loading">
            <div class="spinner-small"></div>
            处理中...
          </span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

// Props
const props = defineProps<{
  selectedChunker?: string
  isProcessing?: boolean
  availableChunkers?: Record<string, any>
}>()

// Emits
const emit = defineEmits<{
  chunkerSelected: [chunkerName: string]
}>()

// 响应式数据
const selectedChunker = ref<string>('')

// 分块器图标映射
const chunkerIcons: Record<string, string> = {
  'qa': '问答',
  'law': '法规',
  'semantic': '语义',
  'policy': '政策',
  'table': '表格'
}

// 计算属性：从props获取分块器列表
const chunkers = computed(() => {
  if (!props.availableChunkers) {
    return []
  }
  
  return Object.entries(props.availableChunkers).map(([id, info]) => ({
    id,
    name: info.name,
    icon: chunkerIcons[id] || '分块',
    description: info.description,
    features: info.features || []
  }))
})

// 选择分块器
const selectChunker = (chunkerId: string) => {
  if (props.isProcessing) return
  selectedChunker.value = chunkerId
  emit('chunkerSelected', chunkerId)
}

// 处理文档
const processDocument = () => {
  if (selectedChunker.value && !props.isProcessing) {
    // 这里可以添加额外的处理逻辑
    console.log('开始处理文档，使用分块器:', selectedChunker.value)
  }
}
</script>

<style scoped>
.chunker-selector {
  margin-bottom: 2rem;
}

.selector-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.card-header {
  padding: 2rem 2rem 1rem 2rem;
  border-bottom: 1px solid #e5e7eb;
}

.card-header h3 {
  margin: 0 0 0.5rem 0;
  color: #374151;
  font-size: 1.5rem;
  font-weight: 600;
}

.card-header p {
  margin: 0;
  color: #6b7280;
  font-size: 1rem;
}

.chunker-grid {
  padding: 1.5rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}

.chunker-option {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.5rem;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fafbfc;
}

.chunker-option:hover:not(.disabled) {
  border-color: #667eea;
  background: #f8f9ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.chunker-option.selected {
  border-color: #10b981;
  background: #f0fdf4;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);
}

.chunker-option.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.chunker-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.chunker-info {
  flex: 1;
}

.chunker-info h4 {
  margin: 0 0 0.5rem 0;
  color: #374151;
  font-size: 1.125rem;
  font-weight: 600;
}

.chunker-info p {
  margin: 0 0 1rem 0;
  color: #6b7280;
  font-size: 0.875rem;
  line-height: 1.5;
}

.chunker-features {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.feature-tag {
  background: #e5e7eb;
  color: #374151;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 500;
}

.chunker-option.selected .feature-tag {
  background: #d1fae5;
  color: #065f46;
}

.chunker-status {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
}

.selected-indicator {
  width: 24px;
  height: 24px;
  background: #10b981;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  font-weight: bold;
}

.action-buttons {
  padding: 1.5rem 2rem;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}

.process-btn {
  width: 100%;
  padding: 1rem 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.process-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
}

.process-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .chunker-grid {
    grid-template-columns: 1fr;
    padding: 1rem;
  }
  
  .chunker-option {
    padding: 1rem;
  }
  
  .card-header {
    padding: 1.5rem 1rem 1rem 1rem;
  }
  
  .action-buttons {
    padding: 1rem;
  }
}
</style>
