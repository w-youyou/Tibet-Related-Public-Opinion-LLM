<template>
  <div class="chunker-demo">
    <div class="container">
      <!-- 页面标题 -->
      <div class="header">
        <div class="header-top">
          <div class="header-content">
            <h1 class="title">
              <span class="icon">📚</span>
              个人知识库创建
            </h1>
            <p class="subtitle">分步骤创建您的专属知识库</p>
          </div>
          <!-- 聊天界面按钮 -->
          <button class="chat-btn" @click="goToChat">
            <svg class="icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <span>聊天界面</span>
          </button>
        </div>
        
        <!-- API连接状态指示器 -->
        <div class="connection-status" :class="{ 'connected': apiConnected, 'disconnected': !apiConnected }">
          <span class="status-icon">{{ apiConnected ? '🟢' : '🔴' }}</span>
          <span class="status-text">{{ apiConnected ? 'API服务已连接' : 'API服务未连接' }}</span>
        </div>
      </div>

      <!-- 步骤指示器 -->
      <div class="step-indicator">
        <div 
          v-for="(step, index) in steps" 
          :key="index"
          class="step-item"
          :class="{ 
            'active': currentStep === index + 1, 
            'completed': currentStep > index + 1 
          }"
        >
          <div class="step-number">{{ index + 1 }}</div>
          <div class="step-label">{{ step.label }}</div>
        </div>
      </div>

      <!-- 步骤内容 -->
      <div class="step-content">
        <!-- 步骤1: 知识库信息 -->
        <div v-if="currentStep === 1" class="step-panel">
          <div class="panel-card">
            <div class="panel-header">
              <h2>知识库信息</h2>
              <p>为您的知识库设置名称和描述</p>
            </div>
            <div class="panel-body">
              <div class="form-group">
                <label>知识库名称 <span class="required">*</span></label>
                <input 
                  v-model="knowledgeBaseForm.name"
                  type="text"
                  placeholder="例如：法律法规知识库"
                  class="form-input"
                  :disabled="isProcessing"
                />
              </div>
              <div class="form-group">
                <label>知识库描述</label>
                <textarea 
                  v-model="knowledgeBaseForm.description"
                  placeholder="简要描述这个知识库的用途和内容（可选）"
                  class="form-textarea"
                  rows="3"
                  :disabled="isProcessing"
                ></textarea>
              </div>
              <div class="panel-actions">
                <button 
                  class="btn-primary"
                  @click="nextStep"
                  :disabled="!knowledgeBaseForm.name.trim() || isProcessing"
                >
                  下一步
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 步骤2: 上传文件 -->
        <div v-if="currentStep === 2" class="step-panel">
          <div class="panel-card">
            <div class="panel-header">
              <h2>上传文档</h2>
              <p>选择要处理的文档文件</p>
            </div>
            <div class="panel-body">
              <div class="upload-card file-upload">
                <div class="upload-area" 
                     :class="{ 'drag-over': isDragOver, 'has-file': uploadedFiles.length > 0 }"
                     @dragover.prevent="isDragOver = true"
                     @dragleave.prevent="isDragOver = false"
                     @drop.prevent="handleFileDrop"
                     @click="triggerFileInput">
                  
                  <input 
                    ref="fileInput"
                    type="file" 
                    multiple
                    accept=".txt,.pdf,.doc,.docx,.md,.xlsx,.xls,.png,.jpg,.jpeg"
                    @change="handleFileSelect"
                    style="display: none"
                  />
                  
                  <div v-if="uploadedFiles.length === 0" class="upload-content">
                    <div class="upload-icon">📁</div>
                    <h3>拖拽多个文件到此处或点击选择文件</h3>
                    <p>支持格式：TXT, PDF, Word, Excel, Markdown, 图片</p>
                    <div class="file-size-limit">最大文件大小：50MB</div>
                  </div>
                  
                  <div v-else class="file-info-list" @click.stop>
                    <div class="list-header">
                      <h3>已选中文件 ({{ uploadedFiles.length }})</h3>
                      <div class="file-actions">
                        <button @click.stop="triggerFileInput" class="change-btn">继续添加</button>
                        <button @click.stop="clearAllFiles" class="remove-btn">清空</button>
                      </div>
                    </div>
                    <div class="files-scroll-area">
                      <div v-for="(file, idx) in uploadedFiles" :key="idx" class="file-details-row">
                        <div class="file-meta">
                          <span class="file-icon-small">📄</span>
                          <span class="file-name" :title="file.name">{{ file.name }}</span>
                          <span class="file-size">({{ formatFileSize(file.size) }})</span>
                        </div>
                        <button @click.stop="removeFile(idx)" class="remove-icon-btn">❌</button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="panel-actions">
                <button class="btn-secondary" @click="prevStep">上一步</button>
                <button 
                  class="btn-primary"
                  @click="nextStep"
                  :disabled="uploadedFiles.length === 0 || isProcessing"
                >
                  下一步
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 步骤3: 选择分块策略 -->
        <div v-if="currentStep === 3" class="step-panel">
          <div class="panel-card">
            <div class="panel-header">
              <h2>选择分块策略</h2>
              <p>根据文档类型选择合适的分块方式</p>
            </div>
            <div class="panel-body">
              <!-- 基础切分方式 -->
              <div class="chunker-category">
                <h3 class="category-title">基础切分方式</h3>
                <div class="chunker-grid">
                  <div
                    v-for="chunker in basicChunkers"
                    :key="chunker.id"
                    class="chunker-card"
                    :class="{ 'selected': selectedChunker === chunker.id }"
                    @click="selectChunker(chunker.id)"
                  >
                    <div class="chunker-icon">{{ getChunkerIcon(chunker.id) }}</div>
                    <h4>{{ chunker.name }}</h4>
                    <p>{{ chunker.description }}</p>
                    <div class="chunker-features">
                      <span v-for="feature in chunker.features" :key="feature" class="feature-tag">
                        {{ feature }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 进阶切分方式 -->
              <div class="chunker-category">
                <h3 class="category-title">进阶切分方式</h3>
                <div class="chunker-grid">
                  <div
                    v-for="chunker in advancedChunkers"
                    :key="chunker.id"
                    class="chunker-card"
                    :class="{ 'selected': selectedChunker === chunker.id }"
                    @click="selectChunker(chunker.id)"
                  >
                    <div class="chunker-icon">{{ getChunkerIcon(chunker.id) }}</div>
                    <h4>{{ chunker.name }}</h4>
                    <p>{{ chunker.description }}</p>
                    <div class="chunker-features">
                      <span v-for="feature in chunker.features" :key="feature" class="feature-tag">
                        {{ feature }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 专用切分方式 -->
              <div class="chunker-category">
                <h3 class="category-title">专用切分方式</h3>
                <div class="chunker-grid">
                  <div
                    v-for="chunker in specializedChunkers"
                    :key="chunker.id"
                    class="chunker-card"
                    :class="{ 'selected': selectedChunker === chunker.id }"
                    @click="selectChunker(chunker.id)"
                  >
                    <div class="chunker-icon">{{ getChunkerIcon(chunker.id) }}</div>
                    <h4>{{ chunker.name }}</h4>
                    <p>{{ chunker.description }}</p>
                    <div class="chunker-features">
                      <span v-for="feature in chunker.features" :key="feature" class="feature-tag">
                        {{ feature }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 参数设置（如果选中了需要参数的分块器） -->
              <div v-if="selectedChunker && selectedChunkerInfo?.params" class="params-section">
                <div class="params-card">
                  <div class="params-header">
                    <h3>参数设置（可选）</h3>
                    <button class="toggle-btn" @click="showParams = !showParams">
                      {{ showParams ? '收起' : '展开' }}
                    </button>
                  </div>
                  <div v-if="showParams" class="params-body">
                    <div
                      v-for="(paramConfig, paramKey) in selectedChunkerInfo.params"
                      :key="paramKey"
                      class="param-item"
                    >
                      <label>
                        {{ paramConfig.label }}
                        <span class="param-default">（默认：{{ paramConfig.default }}）</span>
                      </label>
                    <input
                      v-if="paramConfig.type === 'number' && selectedChunker && chunkerParams[selectedChunker]"
                      v-model.number="chunkerParams[selectedChunker]![paramKey]"
                      type="number"
                      :min="paramConfig.min"
                      :max="paramConfig.max"
                      class="param-input"
                    />
                    <input
                      v-else-if="paramConfig.type === 'boolean' && selectedChunker && chunkerParams[selectedChunker]"
                      v-model="chunkerParams[selectedChunker]![paramKey]"
                      type="checkbox"
                      class="param-checkbox"
                    />
                    </div>
                    <div class="params-actions">
                      <button class="btn-reset" @click="resetParams">重置为默认值</button>
                    </div>
                  </div>
                </div>
              </div>

              <div class="panel-actions">
                <button class="btn-secondary" @click="prevStep">上一步</button>
                <button 
                  class="btn-primary"
                  @click="nextStep"
                  :disabled="!selectedChunker || isProcessing"
                >
                  下一步
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 步骤4: 开始创建并展示结果 -->
        <div v-if="currentStep === 4" class="step-panel">
          <div class="panel-card">
            <div class="panel-header">
              <h2>开始创建</h2>
              <p>确认信息后开始创建知识库并处理文档</p>
            </div>
            <div class="panel-body">
              <div class="summary-card">
                <h3>创建摘要</h3>
                <div class="summary-item">
                  <span class="summary-label">知识库名称：</span>
                  <span class="summary-value">{{ knowledgeBaseForm.name }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">知识库描述：</span>
                  <span class="summary-value">{{ knowledgeBaseForm.description || '无' }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">文档文件：</span>
                  <span class="summary-value">{{ uploadedFiles.length }} 个文件</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">分块策略：</span>
                  <span class="summary-value">{{ selectedChunkerInfo?.name }}</span>
                </div>
              </div>
              <div class="panel-actions">
                <button class="btn-secondary" @click="prevStep">上一步</button>
                <button 
                  class="btn-primary btn-create"
                  @click="startCreation"
                  :disabled="isProcessing"
                >
                  <span v-if="!isProcessing">开始创建</span>
                  <span v-else class="loading">
                    <div class="spinner-small"></div>
                    处理中...
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 步骤5: 结果展示 -->
        <div v-if="currentStep === 5" class="step-panel">
          <div class="panel-card">
            <div class="panel-header">
              <h2>创建完成</h2>
              <p>知识库已创建，文档处理完成</p>
            </div>
            <div class="panel-body">
              <div v-if="chunkResults.length > 0">
                <ChunkResults 
                  :chunks="chunkResults"
                  :chunker-name="selectedChunker"
                  :is-processing="isProcessing"
                />
              </div>
              <div v-else-if="creationSuccess" class="success-message">
                <div class="success-icon">✅</div>
                <h3>知识库创建成功！</h3>
                <p>您的知识库已创建，文档处理完成。</p>
                <div class="success-actions">
                  <button class="btn-primary" @click="resetWizard">创建新知识库</button>
                  <button class="btn-secondary" @click="goToKnowledgeBases">查看我的知识库</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="errorMessage" class="error-message">
        <div class="error-content">
          <span class="error-icon">⚠️</span>
          <p>{{ errorMessage }}</p>
          <button @click="errorMessage = ''" class="error-close">×</button>
        </div>
      </div>

      <!-- 处理状态 -->
      <div v-if="isProcessing" class="processing-overlay">
        <div class="processing-card">
          <div class="processing-header">
            <div class="processing-icon">
              <div class="spinner"></div>
            </div>
            <h3>正在处理文档</h3>
          </div>
          <div class="processing-content">
            <div class="processing-steps">
              <div class="step" :class="{ active: processingStep >= 1 }">
                <div class="step-icon">📄</div>
                <div class="step-text">
                  <div class="step-title">文档解析中</div>
                  <div class="step-desc">正在读取和解析文档内容</div>
                </div>
              </div>
              <div class="step" :class="{ active: processingStep >= 2 }">
                <div class="step-icon">⚙️</div>
                <div class="step-text">
                  <div class="step-title">分块处理中</div>
                  <div class="step-desc">使用 {{ selectedChunkerInfo?.name }} 策略进行分块</div>
                </div>
              </div>
              <div class="step" :class="{ active: processingStep >= 3 }">
                <div class="step-icon">✨</div>
                <div class="step-text">
                  <div class="step-title">结果生成中</div>
                  <div class="step-desc">正在生成分块结果</div>
                </div>
              </div>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: processingProgress + '%' }"></div>
            </div>
            <div class="processing-info">
              <p class="processing-message">{{ processingMessage }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import ChunkResults from '@/components/ChunkResults.vue'
import { 
  createKB, 
  uploadDoc,
  getDocDetail,
  isAdminLoggedIn
} from '@/services/adminApi'
import {
  healthCheck,
  getChunkers,
  type ChunkResponse,
  type ChunkerInfo,
  type KnowledgeBase
} from '@/services/api'

const router = useRouter()

// 步骤定义
const steps = [
  { label: '知识库信息' },
  { label: '上传文档' },
  { label: '选择策略' },
  { label: '开始创建' },
  { label: '完成' }
]

const currentStep = ref(1)
const apiConnected = ref(false)
const errorMessage = ref<string>('')
const isProcessing = ref(false)
const uploadedFiles = ref<File[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const isDragOver = ref(false)
const selectedChunker = ref<string>('')
const chunkResults = ref<any[]>([])
const availableChunkers = ref<Record<string, ChunkerInfo>>({})
const showParams = ref(false)
const creationSuccess = ref(false)

// 用户和知识库相关
const isLoggedIn = ref(false)
const currentUser = ref<any>(null)
const currentKnowledgeBase = ref<KnowledgeBase | null>(null)
const knowledgeBaseForm = ref({
  name: '',
  description: ''
})

// 分块器参数
const chunkerParams = ref<Record<string, Record<string, any>>>({})

// 处理状态
const processingStep = ref(1)
const processingProgress = ref(0)
const processingMessage = ref('正在初始化处理流程...')

// 计算属性：分类的分块器
const basicChunkers = computed(() => {
  return Object.entries(availableChunkers.value)
    .filter(([_, info]) => info.category === 'basic')
    .map(([id, info]) => ({ id, ...info }))
})

const advancedChunkers = computed(() => {
  return Object.entries(availableChunkers.value)
    .filter(([_, info]) => info.category === 'advanced')
    .map(([id, info]) => ({ id, ...info }))
})

const specializedChunkers = computed(() => {
  return Object.entries(availableChunkers.value)
    .filter(([_, info]) => info.category === 'specialized')
    .map(([id, info]) => ({ id, ...info }))
})

const selectedChunkerInfo = computed(() => {
  return selectedChunker.value ? availableChunkers.value[selectedChunker.value] : null
})

// 获取分块器图标
const getChunkerIcon = (chunkerId: string) => {
  const icons: Record<string, string> = {
    'by_length': '📏',
    'by_punctuation': '🔤',
    'recursive': '🔄',
    'by_page': '📄',
    'semantic': '🧠',
    'multimodal': '🎨',
    'qa': '❓',
    'law': '⚖️',
    'policy': '📋',
    'table': '📊'
  }
  return icons[chunkerId] || '📝'
}

// 检查API连接
const checkApiConnection = async () => {
  try {
    await healthCheck()
    apiConnected.value = true
    errorMessage.value = ''
    
    const chunkersResponse = await getChunkers()
    availableChunkers.value = chunkersResponse.chunkers
    
    // 初始化参数默认值
    Object.entries(availableChunkers.value).forEach(([id, info]) => {
      if (info.params) {
        if (!chunkerParams.value[id]) {
          chunkerParams.value[id] = {}
        }
        Object.entries(info.params).forEach(([paramKey, paramConfig]: [string, any]) => {
          if (chunkerParams.value[id] && chunkerParams.value[id][paramKey] === undefined) {
            chunkerParams.value[id][paramKey] = paramConfig.default
          }
        })
      }
    })
  } catch (error: any) {
    apiConnected.value = false
    errorMessage.value = error?.message || `API连接失败: ${error}`
  }
}

// 检查用户登录状态
const checkUserLogin = async () => {
  // 对于 Admin 后台，直接检查 Admin Token 是否存在
  if (isAdminLoggedIn()) {
    isLoggedIn.value = true
    currentUser.value = { id: 1, username: localStorage.getItem('admin_username') || 'Admin' } as any
  } else {
    isLoggedIn.value = false
  }
}

// 步骤导航
const nextStep = () => {
  if (currentStep.value < steps.length) {
    currentStep.value++
  }
}

const prevStep = () => {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

// 触发文件选择
const triggerFileInput = () => {
  if (isProcessing.value) return
  fileInput.value?.click()
}

// 处理文件选择
const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    const filesArray = Array.from(target.files)
    const uniqueFiles = filesArray.filter(
      newFile => !uploadedFiles.value.some(existing => existing.name === newFile.name && existing.size === newFile.size)
    )
    uploadedFiles.value = [...uploadedFiles.value, ...uniqueFiles]
  }
  if (target) target.value = ''
}

// 处理拖拽
const handleFileDrop = (event: DragEvent) => {
  isDragOver.value = false
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    const filesArray = Array.from(event.dataTransfer.files)
    const uniqueFiles = filesArray.filter(
      newFile => !uploadedFiles.value.some(existing => existing.name === newFile.name && existing.size === newFile.size)
    )
    uploadedFiles.value = [...uploadedFiles.value, ...uniqueFiles]
  }
}

// 移除单个文件
const removeFile = (index: number) => {
  uploadedFiles.value.splice(index, 1)
}

// 清空全部文件
const clearAllFiles = () => {
  uploadedFiles.value = []
}

// 格式化大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 选择分块器
const selectChunker = (chunkerId: string) => {
  if (isProcessing.value) return
  selectedChunker.value = chunkerId
}

// 重置参数
const resetParams = () => {
  if (selectedChunker.value && selectedChunkerInfo.value?.params && chunkerParams.value[selectedChunker.value]) {
    Object.entries(selectedChunkerInfo.value.params).forEach(([paramKey, paramConfig]: [string, any]) => {
      chunkerParams.value[selectedChunker.value]![paramKey] = paramConfig.default
    })
  }
}

// 开始创建
const startCreation = async () => {
  if (uploadedFiles.value.length === 0 || !selectedChunker.value) {
    errorMessage.value = '请完成所有步骤'
    return
  }

  isProcessing.value = true
  errorMessage.value = ''
  processingStep.value = 1
  processingProgress.value = 0
  chunkResults.value = []

  try {
    // 步骤1: 创建知识库
    if (!currentKnowledgeBase.value) {
      processingMessage.value = '正在创建知识库...'
      const kbResponse = await createKB(
        knowledgeBaseForm.value.name,
        knowledgeBaseForm.value.description || ''
      )
      
      if (kbResponse.success && kbResponse.data) {
        currentKnowledgeBase.value = kbResponse.data as any
        processingProgress.value = 20
      } else {
        throw new Error('知识库创建失败')
      }
    }

    // 步骤2: 处理文档 (多文件循环)
    processingStep.value = 2
    
    let allChunks: any[] = []
    
    for (let i = 0; i < uploadedFiles.value.length; i++) {
      const file = uploadedFiles.value[i] as File
      if (!file) continue
      
      processingMessage.value = `正在使用 ${selectedChunkerInfo.value?.name} 处理第 ${i + 1}/${uploadedFiles.value.length} 个文档: ${file.name}...`
      // 计算进度 (40 到 90)
      processingProgress.value = 40 + (i / uploadedFiles.value.length) * 50

      const uploadResponse = await uploadDoc(
        file,
        currentKnowledgeBase.value?.id as string,
        selectedChunker.value
      )
      
      if (!uploadResponse.success || !uploadResponse.data?.document_id) {
        throw new Error(uploadResponse.message || `文档 ${file.name} 上传失败`)
      }

      // 获取上传文档的详细信息及chunks
      const docDetail = await getDocDetail(uploadResponse.data.document_id)
      
      if (docDetail.success && docDetail.data?.chunks) {
        const fileChunks = docDetail.data.chunks.map((chunk: any) => ({
          id: `${file.name}-${chunk.chunk_id}`,
          content: `[${file.name}]\n` + chunk.content,
          modality_type: 'text',
          metadata: {
            chunkSize: chunk.length,
            position: Number(chunk.chunk_id) - 1,
            chunker: selectedChunker.value
          }
        }))
        allChunks = allChunks.concat(fileChunks)
      }
    }

    processingStep.value = 3
    processingProgress.value = 90
    processingMessage.value = '正在生成总结果...'

    // 转换结果
    chunkResults.value = allChunks

    processingProgress.value = 100
    creationSuccess.value = true
    currentStep.value = 5
    
  } catch (error: any) {
    console.error('❌ 处理失败:', error)
    errorMessage.value = `处理失败: ${error.message || error}`
  } finally {
    isProcessing.value = false
  }
}

// 重置向导
const resetWizard = () => {
  currentStep.value = 1
  knowledgeBaseForm.value = { name: '', description: '' }
  uploadedFiles.value = []
  selectedChunker.value = ''
  chunkResults.value = []
  creationSuccess.value = false
  currentKnowledgeBase.value = null
}

// 跳转到知识库管理
const goToKnowledgeBases = () => {
  router.push('/rag-admin/knowledge-bases')
}

// 跳转到聊天界面
const goToChat = () => {
  router.push('/')
}

onMounted(async () => {
  await checkApiConnection()
  await checkUserLogin()
})
</script>

<style scoped>
.chunker-demo {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.header {
  margin-bottom: 2rem;
  color: white;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.header-content {
  flex: 1;
  text-align: center;
}

.chat-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  color: white;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.chat-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.chat-btn .icon {
  flex-shrink: 0;
}

.title {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

.icon {
  font-size: 3rem;
}

.subtitle {
  font-size: 1.1rem;
  opacity: 0.9;
  margin-bottom: 1rem;
}

.connection-status {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.connection-status.connected {
  background: rgba(34, 197, 94, 0.2);
  border: 1px solid rgba(34, 197, 94, 0.3);
  color: #22c55e;
}

.connection-status.disconnected {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

/* 步骤指示器 */
.step-indicator {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 2rem;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  backdrop-filter: blur(10px);
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  max-width: 150px;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  transition: all 0.3s;
}

.step-item.active .step-number {
  background: white;
  color: #667eea;
  transform: scale(1.1);
}

.step-item.completed .step-number {
  background: #10b981;
  color: white;
}

.step-label {
  font-size: 0.875rem;
  color: white;
  text-align: center;
  opacity: 0.7;
}

.step-item.active .step-label {
  opacity: 1;
  font-weight: 600;
}

/* 步骤内容 */
.step-content {
  position: relative;
}

.step-panel {
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.panel-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.panel-header {
  padding: 2rem 2rem 1rem 2rem;
  border-bottom: 1px solid #e5e7eb;
}

.panel-header h2 {
  margin: 0 0 0.5rem 0;
  color: #374151;
  font-size: 1.5rem;
  font-weight: 600;
}

.panel-header p {
  margin: 0;
  color: #6b7280;
  font-size: 1rem;
}

.panel-body {
  padding: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #374151;
  font-weight: 500;
  font-size: 0.875rem;
}

.required {
  color: #ef4444;
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 1rem;
  transition: all 0.2s;
  box-sizing: border-box;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
}

.btn-primary,
.btn-secondary {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

/* 分块器选择 */
.chunker-category {
  margin-bottom: 2rem;
}

.category-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #e5e7eb;
}

.chunker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.chunker-card {
  padding: 1.5rem;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  background: #fafbfc;
}

.chunker-card:hover {
  border-color: #667eea;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.chunker-card.selected {
  border-color: #10b981;
  background: #f0fdf4;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);
}

.chunker-icon {
  font-size: 2rem;
  margin-bottom: 0.75rem;
}

.chunker-card h4 {
  margin: 0 0 0.5rem 0;
  color: #374151;
  font-size: 1.125rem;
  font-weight: 600;
}

.chunker-card p {
  margin: 0 0 0.75rem 0;
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

.chunker-card.selected .feature-tag {
  background: #d1fae5;
  color: #065f46;
}

/* 参数设置 */
.params-section {
  margin-top: 2rem;
}

.params-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
}

.params-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.params-header h3 {
  margin: 0;
  color: #374151;
  font-size: 1rem;
  font-weight: 600;
}

.toggle-btn {
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  color: #374151;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.toggle-btn:hover {
  background: #f3f4f6;
}

.params-body {
  padding: 1.5rem;
}

.param-item {
  margin-bottom: 1rem;
}

.param-item label {
  display: block;
  margin-bottom: 0.5rem;
  color: #374151;
  font-size: 0.875rem;
  font-weight: 500;
}

.param-default {
  color: #9ca3af;
  font-weight: normal;
  font-size: 0.8rem;
}

.param-input {
  width: 100%;
  padding: 0.625rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
}

.param-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.params-actions {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.btn-reset {
  padding: 0.625rem 1.25rem;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  color: #374151;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-reset:hover {
  background: #e5e7eb;
}

/* 摘要卡片 */
.summary-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.summary-card h3 {
  margin: 0 0 1rem 0;
  color: #374151;
  font-size: 1.125rem;
  font-weight: 600;
}

.summary-item {
  display: flex;
  margin-bottom: 0.75rem;
}

.summary-label {
  color: #6b7280;
  font-weight: 500;
  min-width: 120px;
}

.summary-value {
  color: #374151;
  flex: 1;
}

.btn-create {
  min-width: 150px;
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

/* 成功消息 */
.success-message {
  text-align: center;
  padding: 3rem 2rem;
}

.success-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.success-message h3 {
  color: #374151;
  margin-bottom: 0.5rem;
}

.success-message p {
  color: #6b7280;
  margin-bottom: 2rem;
}

.success-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
}

/* 错误提示 */
.error-message {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1001;
  max-width: 400px;
}

.error-content {
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 1rem;
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.error-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.error-content p {
  margin: 0;
  color: #dc2626;
  font-size: 0.875rem;
  flex: 1;
}

.error-close {
  background: none;
  border: none;
  color: #dc2626;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.error-close:hover {
  background-color: rgba(220, 38, 38, 0.1);
}

/* 处理状态 */
.processing-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.processing-card {
  background: white;
  border-radius: 20px;
  padding: 2rem;
  max-width: 500px;
  width: 90%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.processing-header {
  text-align: center;
  margin-bottom: 2rem;
}

.processing-icon {
  margin-bottom: 1rem;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #e5e7eb;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.processing-header h3 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: #374151;
}

.processing-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.processing-steps {
  margin-bottom: 2rem;
}

.step {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border-radius: 12px;
  margin-bottom: 0.5rem;
  transition: all 0.3s ease;
  opacity: 0.5;
}

.step.active {
  background: #f0f9ff;
  border: 1px solid #0ea5e9;
  opacity: 1;
  transform: scale(1.02);
}

.step-icon {
  font-size: 1.5rem;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  border-radius: 50%;
  flex-shrink: 0;
}

.step.active .step-icon {
  background: #0ea5e9;
  color: white;
}

.step-text {
  flex: 1;
}

.step-title {
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.25rem;
}

.step-desc {
  font-size: 0.875rem;
  color: #6b7280;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 1.5rem;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.processing-info {
  text-align: center;
}

.processing-message {
  font-size: 1rem;
  font-weight: 500;
  color: #374151;
}

@media (max-width: 768px) {
  .title {
    font-size: 2rem;
  }
  
  .step-indicator {
    flex-wrap: wrap;
  }
  
  .step-item {
    max-width: 100px;
  }
  
  .chunker-grid {
    grid-template-columns: 1fr;
  }
  
  .panel-actions {
    flex-direction: column-reverse;
  }
  
  .btn-primary,
  .btn-secondary {
    width: 100%;
  }
}
/* 自定义多文件列表样式 */
.file-upload {
  margin-bottom: 2rem;
}
.upload-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.05);
  overflow: hidden;
  transition: all 0.3s ease;
  border: 1px solid #f1f5f9;
}
.upload-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.1);
}
.upload-area {
  padding: 3rem 2rem;
  border: 2px dashed #e1e5e9;
  border-radius: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fafbfc;
}
.upload-area:hover {
  border-color: #667eea;
  background: #f8f9ff;
}
.upload-area.drag-over {
  border-color: #667eea;
  background: #f0f4ff;
  transform: scale(1.02);
}
.upload-area.has-file {
  border-color: #10b981;
  background: #f0fdf4;
}
.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}
.upload-icon {
  font-size: 4rem;
  opacity: 0.6;
}
.upload-content h3 {
  margin: 0;
  color: #374151;
  font-size: 1.5rem;
  font-weight: 600;
}
.upload-content p {
  margin: 0;
  color: #6b7280;
  font-size: 1rem;
}
.file-size-limit {
  color: #9ca3af;
  font-size: 0.875rem;
}

.file-info-list {
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e1e5e9;
  padding-bottom: 0.8rem;
}
.list-header h3 {
  margin: 0;
  color: #374151;
  font-size: 1.1rem;
}
.file-actions {
  display: flex;
  gap: 0.5rem;
}
.remove-btn, .change-btn {
  padding: 0.4rem 0.8rem;
  border: none;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}
.remove-btn {
  background: #fee2e2;
  color: #dc2626;
}
.remove-btn:hover {
  background: #fecaca;
}
.change-btn {
  background: #dbeafe;
  color: #2563eb;
}
.change-btn:hover {
  background: #bfdbfe;
}
.files-scroll-area {
  max-height: 200px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-right: 8px;
}
.file-details-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.6rem 1rem;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}
.file-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  overflow: hidden;
}
.file-icon-small {
  font-size: 1.2rem;
}
.file-name {
  font-weight: 500;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
}
.file-size {
  color: #64748B;
  font-size: 0.8rem;
}
.remove-icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  opacity: 0.5;
}
.remove-icon-btn:hover {
  opacity: 1;
}
</style>
