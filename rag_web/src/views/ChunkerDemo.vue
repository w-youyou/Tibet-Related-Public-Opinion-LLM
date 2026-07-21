<template>
  <div class="chunker-demo">
    <div class="container">
      <!-- 页面标题 -->
      <div class="header">
        <div class="header-top">
          <div class="header-content">
            <h1 class="title">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="vertical-align: middle;">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
              </svg>
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
          <span class="status-dot"></span>
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
              <FileUpload 
                @file-uploaded="handleFileUploaded"
                :is-processing="isProcessing"
              />
              <div class="flow-toggle">
                <label class="flow-toggle-label">
                  <input
                    type="checkbox"
                    v-model="enableFlowExtract"
                    :disabled="isProcessing"
                  />
                  <span>上传时提取流程图（仅适用于包含办理流程的文件）</span>
                </label>
              </div>
              <div class="panel-actions">
                <button class="btn-secondary" @click="prevStep">上一步</button>
                <button 
                  class="btn-primary"
                  @click="nextStep"
                  :disabled="!uploadedFile || isProcessing"
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
                  <span class="summary-value">{{ uploadedFile?.name }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">分块策略：</span>
                  <span class="summary-value">{{ selectedChunkerInfo?.name }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">流程图提取：</span>
                  <span class="summary-value">{{ enableFlowExtract ? '开启' : '关闭' }}</span>
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
              <div v-if="flowExtractResult && flowExtractResult.enabled" class="flow-result-tip">
                <strong>流程提取：</strong>
                <span v-if="flowExtractResult.success">成功，提取 {{ flowExtractResult.matter_count }} 个事项。</span>
                <span v-else>未提取到可用流程（不影响上传）。{{ flowExtractResult.message || '' }}</span>
              </div>
              <div v-if="chunkResults.length > 0">
                <ChunkResults 
                  :chunks="chunkResults"
                  :chunker-name="selectedChunker"
                  :is-processing="isProcessing"
                />
              </div>
              <div v-else-if="creationSuccess" class="success-message">
                <div class="success-icon">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                  </svg>
                </div>
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
          <span class="error-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </span>
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
                <div class="step-icon">1</div>
                <div class="step-text">
                  <div class="step-title">文档解析中</div>
                  <div class="step-desc">正在读取和解析文档内容</div>
                </div>
              </div>
              <div class="step" :class="{ active: processingStep >= 2 }">
                <div class="step-icon">2</div>
                <div class="step-text">
                  <div class="step-title">分块处理中</div>
                  <div class="step-desc">使用 {{ selectedChunkerInfo?.name }} 策略进行分块</div>
                </div>
              </div>
              <div class="step" :class="{ active: processingStep >= 3 }">
                <div class="step-icon">3</div>
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
import FileUpload from '@/components/FileUpload.vue'
import ChunkResults from '@/components/ChunkResults.vue'
import { 
  chunkDocument, 
  getChunkers, 
  healthCheck, 
  getCurrentUser,
  createKnowledgeBase,
  type ChunkResponse, 
  type ChunkerInfo,
  type User,
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
const uploadedFile = ref<File | null>(null)
const selectedChunker = ref<string>('')
const chunkResults = ref<any[]>([])
const availableChunkers = ref<Record<string, ChunkerInfo>>({})
const showParams = ref(false)
const creationSuccess = ref(false)

// 用户和知识库相关
const isLoggedIn = ref(false)
const currentUser = ref<User | null>(null)
const currentKnowledgeBase = ref<KnowledgeBase | null>(null)
const knowledgeBaseForm = ref({
  name: '',
  description: ''
})
const enableFlowExtract = ref(false)
const flowExtractResult = ref<{ enabled: boolean; success: boolean; matter_count: number; message?: string } | null>(null)

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
    'by_length': '按长度',
    'by_punctuation': '按标点',
    'recursive': '递归',
    'by_page': '按页',
    'semantic': '语义',
    'multimodal': '多模态',
    'qa': '问答',
    'law': '法规',
    'policy': '政策',
    'table': '表格'
  }
  return icons[chunkerId] || '分块'
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
  try {
    const response = await getCurrentUser()
    if (response.success && response.user) {
      isLoggedIn.value = true
      currentUser.value = response.user
    }
  } catch (error) {
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

// 处理文件上传
const handleFileUploaded = (file: File) => {
  uploadedFile.value = file
  chunkResults.value = []
  errorMessage.value = ''
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
  if (!uploadedFile.value || !selectedChunker.value) {
    errorMessage.value = '请完成所有步骤'
    return
  }

  isProcessing.value = true
  errorMessage.value = ''
  processingStep.value = 1
  processingProgress.value = 0

  try {
    // 步骤1: 创建知识库（如果已登录）
    if (isLoggedIn.value && !currentKnowledgeBase.value) {
      processingMessage.value = '正在创建知识库...'
      const kbResponse = await createKnowledgeBase({
        name: knowledgeBaseForm.value.name,
        description: knowledgeBaseForm.value.description || undefined
      })
      
      if (kbResponse.success && kbResponse.knowledge_base) {
        currentKnowledgeBase.value = kbResponse.knowledge_base
        processingProgress.value = 20
      }
    }

    // 步骤2: 处理文档
    processingStep.value = 2
    processingMessage.value = `正在使用 ${selectedChunkerInfo.value?.name} 处理文档...`
    processingProgress.value = 40

    // 准备参数
    const params: Record<string, any> = {}
    const selectedChunkerParams = selectedChunker.value ? chunkerParams.value[selectedChunker.value] : undefined
    if (selectedChunkerParams) {
      Object.assign(params, selectedChunkerParams)
    }

    const response: ChunkResponse = await chunkDocument(
      uploadedFile.value,
      selectedChunker.value,
      currentKnowledgeBase.value?.id,
      params,
      enableFlowExtract.value
    )

    flowExtractResult.value = response.flow_extract || {
      enabled: enableFlowExtract.value,
      success: false,
      matter_count: 0,
      message: enableFlowExtract.value ? '后端暂未返回流程提取结果' : '未开启流程提取'
    }

    processingStep.value = 3
    processingProgress.value = 90
    processingMessage.value = '正在生成结果...'

    // 转换结果
    chunkResults.value = response.chunks.map(chunk => ({
      id: chunk.id,
      content: chunk.content,
      modality_type: chunk.modality_type,
      metadata: {
        chunkSize: chunk.modality_type === 'image' ? 0 : chunk.content.length,
        position: chunk.id - 1,
        chunker: response.chunker_type,
        ...chunk.metadata
      }
    }))

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
  uploadedFile.value = null
  selectedChunker.value = ''
  chunkResults.value = []
  creationSuccess.value = false
  currentKnowledgeBase.value = null
  enableFlowExtract.value = false
  flowExtractResult.value = null
}

// 跳转到知识库管理
const goToKnowledgeBases = () => {
  router.push('/kb')
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
  min-height: calc(100vh - 52px);
  background: var(--color-bg);
  padding: var(--space-xl) 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-lg);
}

/* ===== Header ===== */
.header {
  margin-bottom: var(--space-lg);
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.header-content { flex: 1; text-align: center; }

.chat-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.chat-btn:hover {
  background: var(--color-border-light);
  border-color: var(--color-text-muted);
}

.title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.subtitle {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

.connection-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 99px;
  font-size: var(--font-size-xs);
  font-weight: 500;
  transition: all 0.3s ease;
}
.connection-status.connected {
  background: var(--color-accent-light);
  border: 1px solid rgba(182, 139, 64, 0.3);
  color: var(--color-accent);
}
.connection-status.disconnected {
  background: var(--color-danger-light);
  border: 1px solid rgba(196, 30, 58, 0.2);
  color: var(--color-danger);
}
.status-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

/* ===== Step Indicator ===== */
.step-indicator {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-bottom: var(--space-xl);
  padding: 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex: 1;
  max-width: 150px;
}

.step-number {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: var(--color-border-light);
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: var(--font-size-sm);
  transition: all 0.3s;
}

.step-item.active .step-number {
  background: var(--color-primary);
  color: #fff;
  transform: scale(1.08);
}

.step-item.completed .step-number {
  background: var(--color-accent);
  color: #fff;
}

.step-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  text-align: center;
}
.step-item.active .step-label {
  color: var(--color-primary);
  font-weight: 600;
}
.step-item.completed .step-label { color: var(--color-accent); }

/* ===== Panels ===== */
.step-content { position: relative; }
.step-panel { animation: fadeIn 0.3s; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.panel-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.panel-header {
  padding: var(--space-lg) var(--space-lg) var(--space-md);
  border-bottom: 1px solid var(--color-border-light);
}
.panel-header h2 {
  margin: 0 0 4px 0;
  color: var(--color-text);
  font-size: var(--font-size-xl);
  font-weight: 600;
}
.panel-header p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.panel-body { padding: var(--space-lg); }

/* ===== Forms ===== */
.form-group { margin-bottom: var(--space-lg); }
.form-group label {
  display: block;
  margin-bottom: 6px;
  color: var(--color-text);
  font-weight: 500;
  font-size: var(--font-size-sm);
}
.required { color: var(--color-danger); }

.form-input,
.form-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
  font-family: var(--font-family);
  color: var(--color-text);
  background: var(--color-surface);
  transition: all var(--transition-fast);
  box-sizing: border-box;
}
.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(26, 54, 93, 0.08);
}
.form-textarea { resize: vertical; }

.panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-md);
  margin-top: var(--space-lg);
  padding-top: var(--space-lg);
  border-top: 1px solid var(--color-border-light);
}

/* ===== Buttons ===== */
.btn-primary,
.btn-secondary {
  padding: 10px 22px;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-primary {
  background: var(--color-primary);
  color: #fff;
}
.btn-primary:hover:not(:disabled) { background: var(--color-primary-light); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  background: var(--color-bg);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}
.btn-secondary:hover { background: var(--color-border-light); }

/* ===== Chunker Cards ===== */
.chunker-category { margin-bottom: var(--space-xl); }

.category-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-md);
  padding-bottom: 6px;
  border-bottom: 2px solid var(--color-border-light);
}

.chunker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space-md);
}

.chunker-card {
  padding: var(--space-lg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.25s;
  background: var(--color-surface);
}
.chunker-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}
.chunker-card.selected {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
}

.chunker-icon {
  display: inline-block;
  padding: 2px 8px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 600;
  margin-bottom: 10px;
}

.chunker-card h4 {
  margin: 0 0 6px 0;
  color: var(--color-text);
  font-size: var(--font-size-base);
  font-weight: 600;
}
.chunker-card p {
  margin: 0 0 10px 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.5;
}

.chunker-features {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.feature-tag {
  background: var(--color-border-light);
  color: var(--color-text-secondary);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
}
.chunker-card.selected .feature-tag {
  background: rgba(26, 54, 93, 0.1);
  color: var(--color-primary);
}

/* ===== Params ===== */
.params-section { margin-top: var(--space-lg); }

.params-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.params-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
}
.params-header h3 { margin: 0; color: var(--color-text); font-size: var(--font-size-sm); }

.toggle-btn {
  padding: 4px 12px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-family: var(--font-family);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.toggle-btn:hover { background: var(--color-border-light); }

.params-body { padding: var(--space-md); }

.param-item { margin-bottom: var(--space-md); }
.param-item label {
  display: block;
  margin-bottom: 4px;
  color: var(--color-text);
  font-size: var(--font-size-sm);
}
.param-default { color: var(--color-text-muted); font-size: var(--font-size-xs); }

.param-input {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
}

.params-actions {
  margin-top: var(--space-md);
  padding-top: var(--space-md);
  border-top: 1px solid var(--color-border-light);
}
.btn-reset {
  padding: 6px 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  font-family: var(--font-family);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.btn-reset:hover { background: var(--color-border-light); }

/* ===== Summary ===== */
.summary-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
}
.summary-card h3 {
  margin: 0 0 14px 0;
  color: var(--color-text);
  font-size: var(--font-size-base);
  font-weight: 600;
}
.summary-item {
  display: flex;
  margin-bottom: 8px;
}
.summary-label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  min-width: 110px;
}
.summary-value {
  color: var(--color-text);
  font-size: var(--font-size-sm);
  flex: 1;
}

.flow-toggle {
  margin-top: var(--space-md);
  padding: 10px 14px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}
.flow-toggle-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text);
  font-size: var(--font-size-sm);
}
.flow-result-tip {
  margin-bottom: var(--space-md);
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-bg);
  border: 1px solid rgba(26, 54, 93, 0.15);
  color: var(--color-text);
  font-size: var(--font-size-sm);
}

.btn-create { min-width: 140px; }
.loading { display: flex; align-items: center; gap: 8px; }

.spinner-small {
  width: 14px; height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* ===== Success ===== */
.success-message {
  text-align: center;
  padding: var(--space-2xl) var(--space-lg);
}
.success-icon {
  margin-bottom: var(--space-md);
  color: var(--color-accent);
}
.success-message h3 {
  color: var(--color-text);
  font-size: var(--font-size-lg);
  margin-bottom: 6px;
}
.success-message p {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  margin-bottom: var(--space-lg);
}
.success-actions {
  display: flex;
  justify-content: center;
  gap: var(--space-md);
}

/* ===== Error ===== */
.error-message {
  position: fixed;
  top: 68px; right: 20px;
  z-index: 1001;
  max-width: 380px;
}
.error-content {
  background: var(--color-danger-light);
  border: 1px solid rgba(196, 30, 58, 0.2);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  box-shadow: var(--shadow-md);
}
.error-icon { flex-shrink: 0; color: var(--color-danger); }
.error-content p {
  margin: 0;
  color: var(--color-danger);
  font-size: var(--font-size-sm);
  flex: 1;
}
.error-close {
  background: none;
  border: none;
  color: var(--color-danger);
  font-size: 18px;
  cursor: pointer;
  padding: 0;
  width: 20px; height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color var(--transition-fast);
}
.error-close:hover { background: rgba(196, 30, 58, 0.08); }

/* ===== Processing Overlay ===== */
.processing-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(3px);
}

.processing-card {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: var(--space-xl);
  max-width: 460px;
  width: 90%;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

.processing-header {
  text-align: center;
  margin-bottom: var(--space-lg);
}
.processing-header h3 {
  margin: 0;
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text);
}

.spinner {
  width: 44px; height: 44px;
  border: 4px solid var(--color-border-light);
  border-top: 4px solid var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto var(--space-md);
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.processing-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.processing-steps { margin-bottom: var(--space-md); }

.step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: var(--radius-sm);
  margin-bottom: 6px;
  transition: all 0.3s;
  opacity: 0.45;
}
.step.active {
  background: var(--color-primary-bg);
  border: 1px solid rgba(26, 54, 93, 0.15);
  opacity: 1;
}

.step-icon {
  width: 36px; height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-border-light);
  border-radius: 50%;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-muted);
  flex-shrink: 0;
}
.step.active .step-icon {
  background: var(--color-primary);
  color: #fff;
}

.step-text { flex: 1; }
.step-title {
  font-weight: 600;
  color: var(--color-text);
  font-size: var(--font-size-sm);
  margin-bottom: 2px;
}
.step-desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: var(--color-border-light);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 12px;
}
.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.processing-info { text-align: center; }
.processing-message {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
}

@media (max-width: 768px) {
  .title { font-size: var(--font-size-xl); }
  .step-indicator { flex-wrap: wrap; }
  .step-item { max-width: 80px; }
  .chunker-grid { grid-template-columns: 1fr; }
  .panel-actions { flex-direction: column-reverse; }
  .btn-primary, .btn-secondary { width: 100%; }
}
</style>
