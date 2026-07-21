<template>
  <div class="chat-container" :class="{ 'sidebar-collapsed': isSidebarCollapsed }">
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1 class="sidebar-title">涉藏舆情知识问答系统</h1>
      </div>
      <div v-if="isLoggedIn && knowledgeBases.length > 0" class="kb-selector">
        <label>检索范围</label>
        <div class="dropdown-container">
          <div class="dropdown-trigger" @click="showKbDropdown = !showKbDropdown">
            <span>{{ selectedKnowledgeBases.length === knowledgeBases.length ? '🌐 全部知识库' : `📚 已选 ${selectedKnowledgeBases.length} 个知识库` }}</span>
            <svg :class="{'rotate': showKbDropdown}" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
          <div v-if="showKbDropdown" class="dropdown-menu">
            <div class="dropdown-header">
              <span class="dropdown-title">可多选检索</span>
              <button class="select-all-btn" @click="toggleSelectAllKBs">
                {{ selectedKnowledgeBases.length === knowledgeBases.length ? '取消全选' : '全选' }}
              </button>
            </div>
            <div class="kb-checkbox-group">
              <label v-for="kb in knowledgeBases" :key="kb.id" class="kb-checkbox-label">
                <input type="checkbox" :value="kb.id" v-model="selectedKnowledgeBases">
                <span class="kb-name" :title="kb.name">📚 {{ kb.name }}</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <button v-if="isLoggedIn" class="new-kb-btn" @click="createNewChat">
        <svg class="icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 5v14M5 12h14"/>
        </svg>
        <span>新建对话</span>
      </button>

      <button v-if="isLoggedIn" class="new-kb-btn" @click="goToTimeline">
        <svg class="icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="2" x2="12" y2="22"/>
          <circle cx="12" cy="6" r="2"/>
          <circle cx="12" cy="12" r="2"/>
          <circle cx="12" cy="18" r="2"/>
        </svg>
        <span>舆情时间线</span>
      </button>

      <div class="chat-history">
        <div v-if="chatHistory.length === 0" class="empty-history">
          <p>暂无聊天记录</p>
        </div>
        <div
          v-for="(chat, index) in chatHistory"
          :key="index"
          class="chat-item"
          :class="{ active: activeChatIndex === index }"
          @click="selectChat(index)"
        >
          <svg class="icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          <span class="chat-title">{{ chat.title }}</span>
          <button class="rename-btn" title="重命名" @click.stop="openRename(index)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20h9"/>
              <path d="M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/>
            </svg>
          </button>
          <button class="delete-btn" title="删除" @click.stop="deleteChat(index)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>
      </div>

      <div class="bottom-section">
        <div v-if="isLoggedIn" class="user-info">
          <div class="avatar">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
            </svg>
          </div>
          <div class="user-details">
            <div class="username">{{ userInfo?.username }}</div>
            <div class="user-email">{{ userInfo?.email }}</div>
          </div>
          <button class="profile-btn" @click="goToProfile">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
          </button>
          <button class="logout-btn" @click="logout">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
            </svg>
          </button>
        </div>
        
        <div v-else class="login-prompt">
          <button class="login-btn" @click="showLoginModal = true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3"/>
            </svg>
            <span>登录</span>
          </button>
        </div>
      </div>
    </aside>

    <main class="chat-main">
      <button class="sidebar-toggle-btn" @click="isSidebarCollapsed = !isSidebarCollapsed">
        <svg v-if="isSidebarCollapsed" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
      </button>

      <div class="messages-container" @click="handleCitationClick">
        <div v-if="currentMessages.length === 0" class="welcome-screen">
          <div class="welcome-content">
            <h1 class="welcome-title">欢迎使用涉藏舆情知识问答系统</h1>
            <p class="welcome-subtitle">智能化研究助手，为您提供涉藏舆情分析与政策咨询服务</p>
            <div v-if="isLoggedIn && knowledgeBases.length > 0" class="welcome-info">
              <div class="info-card">
                <svg class="info-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 16v-4M12 8h.01"/>
                </svg>
                <div class="info-text">
                  <p class="info-title">智能检索</p>
                  <p class="info-desc">
                    {{ selectedKnowledgeBases.length === knowledgeBases.length ? `正在检索全部 ${knowledgeBases.length} 个系统知识库` : `当前检索 ${selectedKnowledgeBases.length} 个指定知识库` }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="messages">
          <div
            v-for="(message, index) in currentMessages"
            :key="index"
            class="message"
            :class="message.role"
          >
            <div class="message-content">
              <div class="message-text">
                
                <template v-if="message.role === 'assistant'">
                   <div 
                      class="md" 
                      :class="{ 'typing-cursor': message.isStreaming }" 
                      v-html="renderMarkdown(message.content)">
                   </div>

                   <div v-if="!message.isStreaming && message.images && message.images.length > 0" class="message-images">
                    <div class="images-grid">
                      <div v-for="(img, imgIndex) in message.images" :key="imgIndex" class="image-item">
                        <img :src="img.url" :alt="img.file_name" @click="openImagePreview(img.url)" />
                        <div class="image-caption">{{ img.file_name }}</div>
                      </div>
                    </div>
                  </div>
                  
                  <div v-if="!message.isStreaming && message.sources && message.sources.length > 0" class="message-sources">
                    <details class="sources-details">
                      <summary>📚 参考资料 ({{ message.sources.length }})</summary>
                      <div class="sources-list">
                        <div v-for="(source, srcIndex) in message.sources" :key="srcIndex" class="source-item" :data-source-idx="srcIndex">
                          <div class="source-file">{{ source.file_name }}</div>
                          <div class="source-content">{{ source.content }}</div>
                        </div>
                      </div>
                    </details>
                  </div>

                  <!-- Feedback Buttons -->
                  <div v-if="!message.isStreaming && message.id && !message.feedbackSubmitted" class="message-feedback">
                    <button class="feedback-btn upvote" @click="submitUpvote(message)" title="回答有帮助">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>
                      </svg>
                    </button>
                    <button class="feedback-btn downvote" @click="openFeedbackModal(message)" title="回答有误">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/>
                      </svg>
                    </button>
                  </div>
                  <div v-if="message.feedbackSubmitted" class="feedback-thanks">
                    感谢您的反馈！
                  </div>
                </template>

                <template v-else>
                  {{ message.content }}
                </template>
                
              </div>
            </div>
          </div>
          
          <div v-if="isLoading" class="message assistant">
            <div class="message-content">
              <div class="message-avatar">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
                </svg>
              </div>
              <div class="message-text loading-message">
                <div class="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
                正在思考中...
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="input-container">
        <div class="input-wrapper">
          <textarea
            ref="messageInputRef"
            v-model="inputMessage"
            class="message-input"
            placeholder="输入您的问题..."
            @input="autoResize"
            @keydown.enter.prevent="sendMessage"
            rows="1"
            :disabled="isLoading || isStreaming"
          ></textarea>
          <button class="send-btn" @click="sendMessage" :disabled="!inputMessage.trim() || isLoading || isStreaming">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
            </svg>
          </button>
        </div>
      </div>
    </main>

    <AuthModal v-if="showLoginModal" @close="showLoginModal = false" @login-success="handleLoginSuccess" />
    <div v-if="showImagePreview" class="modal-overlay" @click="closeImagePreview">
      <div class="image-preview-content">
        <img :src="previewImageUrl" alt="图片预览" />
        <button class="close-preview-btn" @click="closeImagePreview">&times;</button>
      </div>
    </div>
    <div v-if="showRenameModal" class="modal-overlay" @click="cancelRename">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>重命名对话</h2>
          <button class="close-btn" @click="cancelRename">×</button>
        </div>
        <div class="modal-body">
          <input class="kb-name-input" v-model="renameTitle" placeholder="请输入新标题" />
          <button class="create-btn" @click="confirmRename">保存</button>
        </div>
      </div>
    </div>

    <!-- 意见反馈弹窗 -->
    <div v-if="showFeedbackModal" class="modal-overlay" @click="closeFeedbackModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>提交反馈</h2>
          <button class="close-btn" @click="closeFeedbackModal">×</button>
        </div>
        <div class="modal-body" style="flex-direction: column; padding: 24px;">
          <div class="feedback-form-group">
            <label class="feedback-label">问题类型</label>
            <div class="feedback-options">
              <label v-for="ftype in feedbackTypes" :key="ftype.value" class="radio-label">
                <input type="radio" v-model="feedbackForm.type" :value="ftype.value" name="feedbackType" />
                <span class="radio-custom"></span>
                {{ ftype.label }}
              </label>
            </div>
          </div>
          <div class="feedback-form-group" style="margin-top: 16px;">
            <label class="feedback-label">详细描述 (选填)</label>
            <textarea v-model="feedbackForm.comment" class="feedback-textarea" rows="4" placeholder="请详细描述您遇到的问题..."></textarea>
          </div>
          <div class="feedback-actions" style="margin-top: 24px; text-align: right;">
            <button class="cancel-btn" @click="closeFeedbackModal" style="margin-right: 12px;">取消</button>
            <button class="create-btn" @click="submitFeedback" :disabled="!feedbackForm.type || isSubmittingFeedback">
              {{ isSubmittingFeedback ? '提交中...' : '提交' }}
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import AuthModal from '../components/AuthModal.vue'
import { 
  getCurrentUser, 
  logout as apiLogout, 
  type User,
  listKnowledgeBases,
  type KnowledgeBase,
  listChatSessions,
  createChatSessionApi,
  deleteChatSession as apiDeleteChatSession,
  listChatMessages,
  renameChatSession
} from '../services/api'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// Markdown渲染配置
marked.setOptions({ gfm: true, breaks: true })

const router = useRouter()

// ----------------------------------------------------------------
// 1. 类型定义
// ----------------------------------------------------------------
interface ChatMessage {
  id?: number
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  images?: Array<{ url: string; file_name: string }>
  sources?: Array<{ content: string; file_name: string }>
  isStreaming?: boolean
  feedbackSubmitted?: boolean
}

interface ChatSession {
  title: string
  id: number
  sessionId?: string
  messages: ChatMessage[]
}

// ----------------------------------------------------------------
// 2. 状态管理
// ----------------------------------------------------------------
const isLoggedIn = ref(false) 
const showLoginModal = ref(false)
const activeChatIndex = ref(-1)
const inputMessage = ref('')
const isLoading = ref(false) 
const isStreaming = ref(false)
const showImagePreview = ref(false)
const previewImageUrl = ref('')
const messageInputRef = ref<HTMLTextAreaElement | null>(null)
const isSidebarCollapsed = ref(false) 

const userInfo = ref<User | null>(null)
const knowledgeBases = ref<KnowledgeBase[]>([])
const selectedKnowledgeBases = ref<string[]>([]) 

const toggleSelectAllKBs = () => {
  if (selectedKnowledgeBases.value.length === knowledgeBases.value.length) {
    selectedKnowledgeBases.value = []
  } else {
    selectedKnowledgeBases.value = knowledgeBases.value.map(kb => kb.id)
  }
}
const chatHistory = ref<ChatSession[]>([])

const showRenameModal = ref(false)
const renameTitle = ref('')
const renameTargetIndex = ref<number | null>(null)
const showKbDropdown = ref(false)

// ----------------------------------------------------------------
// 3. 基础逻辑
// ----------------------------------------------------------------
const autoResize = () => {
  const el = messageInputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}

const currentMessages = computed(() => {
  if (activeChatIndex.value === -1) return []
  return chatHistory.value[activeChatIndex.value]?.messages || []
})

const renderMarkdown = (text: string) => {
  try {
    let html = marked.parse(text || '') as string
    // 将 [1] [2] 等引用标记转换为可点击的上标徽章
    html = html.replace(/\[(\d+)\]/g, '<sup class="citation-badge" data-source-index="$1" title="查看来源 $1">[$1]</sup>')
    return DOMPurify.sanitize(html, { ADD_TAGS: ['sup'], ADD_ATTR: ['data-source-index', 'title'] })
  } catch (e) {
    return DOMPurify.sanitize(text || '')
  }
}

const scrollToBottom = () => {
  const container = document.querySelector('.messages-container')
  if (container) {
    container.scrollTop = container.scrollHeight
  }
}

// 点击引用标记时滚动到对应来源
const handleCitationClick = (event: Event) => {
  const target = event.target as HTMLElement
  if (target.classList && target.classList.contains('citation-badge')) {
    const index = target.getAttribute('data-source-index')
    if (index) {
      // 找到当前消息的 sources 区域
      const messageEl = target.closest('.message.assistant')
      if (messageEl) {
        const sourcesDetails = messageEl.querySelector('.sources-details') as HTMLDetailsElement
        if (sourcesDetails) {
          sourcesDetails.open = true
          const sourceItem = sourcesDetails.querySelector(`[data-source-idx="${parseInt(index) - 1}"]`)
          if (sourceItem) {
            sourceItem.scrollIntoView({ behavior: 'smooth', block: 'center' })
            sourceItem.classList.add('source-highlight')
            setTimeout(() => sourceItem.classList.remove('source-highlight'), 2000)
          }
        }
      }
    }
  }
}

// ----------------------------------------------------------------
// 4. 打字机模拟 (无错版)
// ----------------------------------------------------------------
const simulateTypewriter = (msg: ChatMessage, fullText: string) => {
  return new Promise<void>((resolve) => {
    msg.isStreaming = true
    isStreaming.value = true
    
    let currentIndex = 0
    const totalLength = fullText.length

    const typeNext = () => {
      if (currentIndex >= totalLength) {
        msg.isStreaming = false
        isStreaming.value = false
        nextTick(() => {
          scrollToBottom()
          autoResize()
        })
        resolve()
        return
      }

      const remaining = totalLength - currentIndex
      const step = remaining > 100 ? 5 : (remaining > 50 ? 3 : (Math.random() > 0.5 ? 2 : 1))
      
      const chunk = fullText.slice(currentIndex, currentIndex + step)
      msg.content += chunk
      currentIndex += step

      scrollToBottom()

      setTimeout(() => {
        requestAnimationFrame(typeNext)
      }, 16) 
    }

    requestAnimationFrame(typeNext)
  })
}

// ----------------------------------------------------------------
// 5. 发送消息 (无错版)
// ----------------------------------------------------------------
const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value || isStreaming.value) return
  
  if (!isLoggedIn.value) {
    showLoginModal.value = true
    return
  }

  const userMessage = inputMessage.value
  inputMessage.value = ''

  if (activeChatIndex.value === -1 || !chatHistory.value[activeChatIndex.value]) {
    const newChat: ChatSession = { title: '新对话', id: Date.now(), messages: [] }
    chatHistory.value.unshift(newChat)
    activeChatIndex.value = 0
  }

  const currentChat = chatHistory.value[activeChatIndex.value]
  if (!currentChat) return

  currentChat.messages.push({
    role: 'user',
    content: userMessage,
    timestamp: new Date().toLocaleTimeString()
  })
  
  nextTick(() => scrollToBottom())

  // --- 关键点：开启加载状态 ---
  // 这会触发模板中 v-if="isLoading" 的 loading-message 显示
  isLoading.value = true

  try {
    const response = await fetch('/api/qa/hybrid/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: userMessage,
        knowledge_base_id: selectedKnowledgeBases.value.length > 0 ? selectedKnowledgeBases.value : undefined,
        session_id: currentChat.sessionId
      })
    })

    const data = await response.json()

    if (data.success) {
      // --- 关键点：停止加载状态 ---
      // 数据回来后，思考动画消失，下面开始打字动画
      isLoading.value = false 
      
      if (data.session_id) currentChat.sessionId = data.session_id

      // 若后端返回了生成的标题（新会话第一次问答），同步更新侧栏
      if (data.session_title && currentChat.title === '新对话') {
        currentChat.title = data.session_title
      }

      const rawAssistantMsg: ChatMessage = {
        id: data.message_id,
        role: 'assistant',
        content: '', 
        timestamp: new Date().toLocaleTimeString(),
        images: data.images, 
        sources: data.sources,
        isStreaming: true,
        feedbackSubmitted: false
      }
      
      currentChat.messages.push(rawAssistantMsg)
      const reactiveAssistantMsg = currentChat.messages[currentChat.messages.length - 1]
      
      if (reactiveAssistantMsg) {
        await simulateTypewriter(reactiveAssistantMsg, data.answer)
      }

    } else {
      throw new Error(data.error || '请求失败')
    }

  } catch (error: any) {
    isLoading.value = false
    isStreaming.value = false
    currentChat.messages.push({
      role: 'assistant',
      content: `❌ 出错了: ${error.message || '网络请求失败'}`,
      timestamp: new Date().toLocaleTimeString()
    })
    nextTick(() => scrollToBottom())
  }
}

// ----------------------------------------------------------------
// 6. 其他辅助函数
// ----------------------------------------------------------------
const checkLoginStatus = async () => {
  try {
    const response = await getCurrentUser()
    if (response.success && response.user) {
      isLoggedIn.value = true
      userInfo.value = response.user
      await Promise.all([ loadKnowledgeBases(), loadChatSessionsFromServer() ])
    } else {
      isLoggedIn.value = false
      userInfo.value = null
    }
  } catch (error) {
    isLoggedIn.value = false
    userInfo.value = null
  }
}

const loadKnowledgeBases = async () => {
  try {
    const response = await listKnowledgeBases()
    if (response.success && response.knowledge_bases) {
      knowledgeBases.value = response.knowledge_bases
      selectedKnowledgeBases.value = knowledgeBases.value.map(kb => kb.id)
    }
  } catch (error) { console.error('加载知识库失败:', error) }
}

const loadChatSessionsFromServer = async () => {
  try {
    const res = await listChatSessions()
    if (res.success && res.sessions) {
      chatHistory.value = res.sessions.map(s => ({
        title: s.title,
        id: Date.now() + Math.random(),
        sessionId: s.id,
        messages: []
      }))
      activeChatIndex.value = chatHistory.value.length > 0 ? 0 : -1
    }
  } catch (e) { console.error('加载会话失败:', e) }
}

const selectChat = async (index: number) => {
  if (index < 0 || index >= chatHistory.value.length) return
  activeChatIndex.value = index
  const current = chatHistory.value[index]
  if (isLoggedIn.value && current?.sessionId && current.messages.length === 0) {
    try {
      const res = await listChatMessages(current.sessionId)
      if (res.success && res.messages) {
          current.messages = res.messages.map(m => ({
          id: m.id,
          role: m.role,
          content: m.content,
          timestamp: new Date(m.created_at).toLocaleTimeString(),
          images: m.images as any,
          sources: m.sources as any,
          feedbackSubmitted: false
        }))
      }
      nextTick(() => scrollToBottom())
    } catch (e) { console.error('加载历史消息失败:', e) }
  }
}

const deleteChat = async (index: number) => {
  const session = chatHistory.value[index]
  if (!confirm('确定要删除这条聊天记录吗？')) return
  try {
    if (isLoggedIn.value && session?.sessionId) {
      await apiDeleteChatSession(session.sessionId)
    }
  } catch (e) { console.error('删除会话失败:', e) }
  chatHistory.value.splice(index, 1)
  if (activeChatIndex.value === index) activeChatIndex.value = -1
}

const createNewChat = async () => {
  if (!isLoggedIn.value) { showLoginModal.value = true; return }
  try {
    const res = await createChatSessionApi({
      title: '新对话',
      knowledge_base_id: selectedKnowledgeBases.value.length > 0 ? selectedKnowledgeBases.value[0] : undefined,
    })
    if (res.success && res.session) {
      chatHistory.value.unshift({
        title: res.session.title || '新对话',
        id: Date.now(),
        sessionId: res.session.id,
        messages: []
      })
      activeChatIndex.value = 0
    }
  } catch (e: any) { alert(`创建会话异常：${e?.message || e}`) }
}

const handleLoginSuccess = async (user: User) => {
  isLoggedIn.value = true
  userInfo.value = user
  showLoginModal.value = false
  await Promise.all([ loadKnowledgeBases(), loadChatSessionsFromServer() ])
  if (chatHistory.value.length > 0) await selectChat(0)
}

const logout = async () => {
  try {
    await apiLogout()
    isLoggedIn.value = false
    userInfo.value = null
    chatHistory.value = []
    activeChatIndex.value = -1
    knowledgeBases.value = []
    selectedKnowledgeBases.value = []
  } catch (error) {}
}

const goToProfile = () => router.push('/profile')

const openImagePreview = (url: string) => { previewImageUrl.value = url; showImagePreview.value = true }
const closeImagePreview = () => { showImagePreview.value = false; previewImageUrl.value = '' }

const openRename = (index: number) => {
  const session = chatHistory.value[index]
  if (!session) return
  renameTargetIndex.value = index
  renameTitle.value = session.title
  showRenameModal.value = true
}

const cancelRename = () => { showRenameModal.value = false; renameTitle.value = ''; renameTargetIndex.value = null }

const confirmRename = async () => {
  if (renameTargetIndex.value === null) return
  const index = renameTargetIndex.value
  const session = chatHistory.value[index]
  if (!session) return
  const newTitle = renameTitle.value.trim()
  if (!newTitle) { alert('标题不能为空'); return }
  try {
    if (isLoggedIn.value && session.sessionId) {
      const res = await renameChatSession(session.sessionId, newTitle)
      if (!res.success) throw new Error(res.error)
      session.title = res.session?.title || newTitle
    } else {
      session.title = newTitle
    }
    showRenameModal.value = false
  } catch (e: any) { alert(`重命名失败：${e?.message}`) } 
  finally { renameTitle.value = ''; renameTargetIndex.value = null }
}

// ----------------------------------------------------------------
// 7. 意见反馈逻辑
// ----------------------------------------------------------------
const showFeedbackModal = ref(false)
const isSubmittingFeedback = ref(false)
const targetMessageId = ref<number | null>(null)
const feedbackTypes = ref<{label: string, value: string}[]>([])
const feedbackForm = ref({ type: '', comment: '' })

const fetchFeedbackTypes = async () => {
  try {
    const res = await fetch('/api/chat/feedback-types/')
    const data = await res.json()
    if (data.success) {
      feedbackTypes.value = data.data
    }
  } catch (e) {
    console.error('获取反馈类型失败', e)
  }
}

const openFeedbackModal = (message: ChatMessage) => {
  if (!message.id) return
  targetMessageId.value = message.id
  feedbackForm.value = { type: '', comment: '' }
  showFeedbackModal.value = true
  if (feedbackTypes.value.length === 0) fetchFeedbackTypes()
}

const closeFeedbackModal = () => {
  showFeedbackModal.value = false
  targetMessageId.value = null
}

const submitUpvote = (message: ChatMessage) => {
  message.feedbackSubmitted = true
}

const submitFeedback = async () => {
  if (!targetMessageId.value || !feedbackForm.value.type) return
  isSubmittingFeedback.value = true
  try {
    const res = await fetch('/api/chat/feedback/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message_id: targetMessageId.value,
        feedback_type: feedbackForm.value.type,
        feedback_comment: feedbackForm.value.comment
      })
    })
    const data = await res.json()
    if (data.success) {
      // 找到对应的 message 并标记
      chatHistory.value.forEach(chat => {
        const msg = chat.messages.find(m => m.id === targetMessageId.value)
        if (msg) msg.feedbackSubmitted = true
      })
      closeFeedbackModal()
    } else {
      alert(`反馈提交失败: ${data.error}`)
    }
  } catch (e) {
    alert('请求失败')
  } finally {
    isSubmittingFeedback.value = false
  }
}

onMounted(async () => {
  await checkLoginStatus()
  if (chatHistory.value.length > 0) await selectChat(0)
})
</script>

<style scoped>
/* 原有样式保留 */
.chat-container.sidebar-collapsed .sidebar { width: 0; padding: 0; overflow: hidden; }
.chat-container.sidebar-collapsed .sidebar > * { display: none; }
.sidebar-toggle-btn { position: absolute; top: 50%; left: -16px; transform: translateY(-50%); width: 32px; height: 32px; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 1px 3px rgba(0,0,0,0.1); z-index: 10; transition: left 0.3s ease-in-out; color: #4b5563; }
.sidebar-toggle-btn:hover { background: #f9fafb; }
.chat-container.sidebar-collapsed .sidebar-toggle-btn { left: 8px; }
.chat-main { position: relative; }
.chat-container { display: flex; height: 100vh; background: #f7f8fa; }
.sidebar-header { padding: 20px 16px; text-align: center; border-bottom: 1px solid #e5e7eb; }
.sidebar-title { font-size: 22px; font-weight: 600; color: #1f2937; white-space: nowrap; }
.sidebar { width: 260px; background: #ffffff; color: #374151; display: flex; flex-direction: column; border-right: 1px solid #e5e7eb; transition: width 0.3s ease-in-out, padding 0.3s ease-in-out; }
.new-kb-btn { background: transparent; border: 1px solid #e5e7eb; color: #374151; padding: 12px; margin: 8px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 10px; transition: all 0.2s; font-size: 14px; font-weight: 500; }
.new-kb-btn:hover { background: #f3f4f6; border-color: #d1d5db; }
.new-kb-btn .icon { stroke: currentColor; }
.chat-history { flex: 1; overflow-y: auto; padding: 8px; }
.empty-history { padding: 20px; text-align: center; color: #8e8ea0; font-size: 14px; }
.chat-item { display: flex; align-items: center; gap: 10px; padding: 12px; border-radius: 8px; cursor: pointer; transition: all 0.2s; margin-bottom: 4px; position: relative; }
.chat-item:hover { background: #f3f4f6; }
.chat-item.active { background: #e5e7eb; }
.chat-item .icon { stroke: currentColor; flex-shrink: 0; }
.chat-title { flex: 1; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.rename-btn, .delete-btn { background: none; border: none; color: #9ca3af; cursor: pointer; padding: 4px; border-radius: 4px; display: none; transition: all 0.2s; }
.chat-item:hover .delete-btn, .chat-item:hover .rename-btn { display: block; }
.rename-btn:hover, .delete-btn:hover { color: #1f2937; background: #e5e7eb; }
.user-info { display: flex; align-items: center; gap: 12px; padding: 12px; border-top: 1px solid #e5e7eb; background: #f9fafb; }
.avatar { flex-shrink: 0; width: 40px; height: 40px; background: #e5e7eb; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #6b7280; }
.user-details { flex: 1; min-width: 0; }
.username { font-size: 14px; font-weight: 500; color: #1f2937; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.user-email { font-size: 12px; color: #6b7280; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.logout-btn { background: none; border: none; color: #6b7280; cursor: pointer; padding: 8px; border-radius: 4px; transition: all 0.2s; flex-shrink: 0; }
.logout-btn:hover, .profile-btn:hover { background: #e5e7eb; color: #1f2937; }
.profile-btn { background: none; border: none; color: #6b7280; cursor: pointer; padding: 8px; border-radius: 4px; transition: all 0.2s; flex-shrink: 0; }
.login-prompt { padding: 12px; border-top: 1px solid #e5e7eb; }
.login-btn { width: 100%; background: #2563eb; border: none; color: white; padding: 12px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 8px; justify-content: center; font-size: 14px; font-weight: 500; transition: all 0.2s; }
.login-btn:hover { background: #1d4ed8; transform: translateY(-1px); }
.chat-main { flex: 1; display: flex; flex-direction: column; background: #f7f8fa; }
.messages-container { flex: 1; overflow-y: auto; padding: 24px; }
.welcome-screen { display: flex; align-items: center; justify-content: center; height: 100%; }
.welcome-content { text-align: center; }
.welcome-title { font-size: 32px; font-weight: 600; color: #202123; margin-bottom: 12px; }
.welcome-subtitle { font-size: 16px; color: #8e8ea0; margin-bottom: 32px; }
.welcome-info { display: flex; justify-content: center; margin-top: 24px; }
.info-card { display: flex; align-items: center; gap: 16px; padding: 16px 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3); max-width: 400px; }
.info-icon { flex-shrink: 0; color: white; }
.info-text { text-align: left; }
.info-title { font-size: 14px; font-weight: 600; color: white; margin-bottom: 4px; }
.info-desc { font-size: 13px; color: rgba(255, 255, 255, 0.9); line-height: 1.4; }
.messages { max-width: 768px; margin: 0 auto; }
.message { display: flex; flex-direction: column; margin-bottom: 24px; }
.message.user { align-items: flex-end; justify-content: flex-end; }
.message.assistant { align-items: flex-start; }
.message-content { display: flex; gap: 12px; }
.message.user .message-content { flex-direction: row-reverse; }
.message-avatar { width: 32px; height: 32px; border-radius: 8px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; color: #8e8ea0; flex-shrink: 0; }
.message.user .message-avatar { background: #19c37d; color: white; }
.message.assistant .message-avatar { background: #8757ff; color: white; }
.message-text { padding: 14px 18px; line-height: 1.6; font-size: 16px; word-break: break-word; }
.message.user .message-text { background: #2563eb; color: white; border-radius: 16px 16px 4px 16px; }
.message.assistant .message-text { background: transparent; color: #1f2937; border: none; border-radius: 0; box-shadow: none; }
.input-container { border-top: 1px solid #e5e7eb; padding: 20px 24px; background: #f7f8fa; }
.input-wrapper { max-width: 800px; margin: 0 auto; display: flex; align-items: flex-end; background: #ffffff; border-radius: 16px; padding: 8px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1); transition: all 0.2s; }
.message-input { flex: 1; padding: 10px; border: none; background: transparent; font-size: 16px; resize: none; min-height: 24px; max-height: 200px; font-family: inherit; outline: none; color: #1f2937; }
.input-wrapper:focus-within { border-color: #2563eb; box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.15), 0 2px 4px -2px rgba(37, 99, 235, 0.15); }
.send-btn { width: 40px; height: 40px; background: #2563eb; border: none; border-radius: 12px; color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s; flex-shrink: 0; }
.send-btn:hover:not(:disabled) { background: #1d4ed8; transform: scale(1.05); }
.send-btn:disabled { background: #e5e5e5; cursor: not-allowed; }
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: white; border-radius: 16px; width: 90%; max-width: 500px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px; border-bottom: 1px solid #e5e5e5; }
.modal-header h2 { font-size: 20px; font-weight: 600; color: #202123; }
.close-btn { background: none; border: none; color: #8e8ea0; cursor: pointer; padding: 8px; border-radius: 8px; transition: all 0.2s; }
.close-btn:hover { background: #f5f5f5; }
.modal-body { padding: 24px; display: flex; gap: 12px; }
.kb-name-input { flex: 1; padding: 12px 16px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 15px; outline: none; transition: all 0.2s; }
.kb-name-input:focus { border-color: #19c37d; box-shadow: 0 0 0 3px rgba(25, 195, 125, 0.1); }
.create-btn { padding: 12px 24px; background: #19c37d; color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: 500; cursor: pointer; transition: all 0.2s; }
.create-btn:hover { background: #16a066; }
.kb-selector { padding: 0 16px 16px 16px; display: flex; flex-direction: column; gap: 8px; }
.kb-selector label { font-size: 13px; color: #6b7280; font-weight: 500; }
.dropdown-container { position: relative; width: 100%; }
.dropdown-trigger { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: rgba(255, 255, 255, 0.95); border: 1px solid rgba(229, 231, 235, 0.8); border-radius: 12px; cursor: pointer; font-size: 14px; font-weight: 500; color: #1f2937; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 2px 4px rgba(0,0,0,0.02), inset 0 1px 0 rgba(255,255,255,1); backdrop-filter: blur(8px); }
.dropdown-trigger:hover { border-color: #3b82f6; background: #ffffff; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1), inset 0 1px 0 rgba(255,255,255,1); transform: translateY(-1px); }
.dropdown-trigger svg { transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); color: #6b7280; }
.dropdown-trigger svg.rotate { transform: rotate(180deg); color: #3b82f6; }
.dropdown-menu { position: absolute; top: calc(100% + 8px); left: 0; right: 0; background: rgba(255, 255, 255, 0.98); border: 1px solid rgba(229, 231, 235, 0.8); border-radius: 16px; box-shadow: 0 20px 40px -10px rgba(0,0,0,0.1), 0 10px 20px -5px rgba(0,0,0,0.05); z-index: 50; overflow: hidden; animation: slideDown 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards; backdrop-filter: blur(12px); transform-origin: top; }
.dropdown-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: rgba(248, 250, 252, 0.8); border-bottom: 1px solid rgba(229, 231, 235, 0.5); }
.dropdown-title { font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.select-all-btn { background: #eff6ff; border: 1px solid #bfdbfe; color: #2563eb; font-size: 12px; cursor: pointer; padding: 6px 12px; border-radius: 6px; transition: all 0.2s; font-weight: 600; box-shadow: 0 1px 2px rgba(37,99,235,0.05); }
.select-all-btn:hover { background: #dbeafe; transform: translateY(-1px); box-shadow: 0 2px 4px rgba(37,99,235,0.1); }
.kb-checkbox-group { display: flex; flex-direction: column; max-height: 240px; overflow-y: auto; padding: 8px; gap: 4px; }
.kb-checkbox-group::-webkit-scrollbar { width: 6px; }
.kb-checkbox-group::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; border: 2px solid transparent; background-clip: padding-box; }
.kb-checkbox-group::-webkit-scrollbar-thumb:hover { background: #94a3b8; border: 2px solid transparent; background-clip: padding-box; }
.kb-checkbox-label { display: flex; align-items: center; gap: 12px; font-size: 14px; color: #334155; cursor: pointer; padding: 10px 12px; border-radius: 10px; transition: all 0.2s ease; border: 1px solid transparent; }
.kb-checkbox-label:hover { background-color: #f8fafc; border-color: #e2e8f0; transform: translateX(2px); }
.kb-checkbox-label input[type="checkbox"] { width: 18px; height: 18px; accent-color: #2563eb; cursor: pointer; transition: transform 0.2s; border-radius: 4px; }
.kb-checkbox-label:hover input[type="checkbox"] { transform: scale(1.1); }
.kb-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; font-weight: 500; }

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-8px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.message-images { margin-top: 12px; }
.images-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
.image-item { position: relative; border-radius: 8px; overflow: hidden; cursor: pointer; transition: transform 0.2s; }
.image-item:hover { transform: scale(1.05); }
.image-item img { width: 100%; height: 150px; object-fit: cover; display: block; }
.image-caption { position: absolute; bottom: 0; left: 0; right: 0; padding: 4px 8px; background: rgba(0, 0, 0, 0.7); color: white; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.message-sources { margin-top: 12px; }
.sources-details { background: rgba(255, 255, 255, 0.5); border-radius: 8px; padding: 8px; }
.message.user .sources-details { background: rgba(255, 255, 255, 0.2); }
.sources-details summary { cursor: pointer; font-size: 13px; font-weight: 500; padding: 4px; user-select: none; }
.sources-details summary:hover { opacity: 0.8; }
.sources-list { margin-top: 8px; display: flex; flex-direction: column; gap: 8px; }
.source-item { background: rgba(255, 255, 255, 0.8); padding: 8px; border-radius: 6px; font-size: 13px; }
.message.user .source-item { background: rgba(255, 255, 255, 0.3); }
.source-file { font-weight: 500; margin-bottom: 4px; color: #19c37d; }
.message.user .source-file { color: white; }
.source-content { color: #555; line-height: 1.4; }
.message.user .source-content { color: rgba(255, 255, 255, 0.9); }
.image-preview-content { position: relative; max-width: 90vw; max-height: 90vh; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5); }
.image-preview-content img { display: block; max-width: 100%; max-height: 90vh; object-fit: contain; }
.close-preview-btn { position: absolute; top: 16px; right: 16px; width: 40px; height: 40px; background: rgba(0, 0, 0, 0.7); border: none; border-radius: 50%; color: white; font-size: 28px; line-height: 1; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
.close-preview-btn:hover { background: rgba(0, 0, 0, 0.9); transform: scale(1.1); }
.chat-history::-webkit-scrollbar, .messages-container::-webkit-scrollbar { width: 8px; }
.chat-history::-webkit-scrollbar-track, .messages-container::-webkit-scrollbar-track { background: transparent; }
.chat-history::-webkit-scrollbar-thumb, .messages-container::-webkit-scrollbar-thumb { background: #565869; border-radius: 4px; }
.chat-history::-webkit-scrollbar-thumb:hover, .messages-container::-webkit-scrollbar-thumb:hover { background: #656772; }

/* --- 打字机光标动画 --- */
.typing-cursor::after {
  content: "▋";
  display: inline-block;
  vertical-align: bottom;
  margin-left: 2px;
  animation: blink 1s infinite;
  color: #8757ff;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* --- 加载动画 (思考中) --- */
.loading-message { display: flex; align-items: center; gap: 8px; }
.typing-indicator { display: flex; gap: 4px; }
.typing-indicator span { width: 8px; height: 8px; border-radius: 50%; background: #8e8ea0; animation: typing 1.4s infinite; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing { 
  0%, 60%, 100% { transform: translateY(0); opacity: 0.7; } 
  30% { transform: translateY(-10px); opacity: 1; } 
}

/* --- 反馈按钮和UI --- */
.message-feedback { display: flex; gap: 8px; margin-top: 12px; }
.feedback-btn { background: none; border: 1px solid #e5e7eb; border-radius: 6px; padding: 6px 10px; color: #6b7280; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; }
.feedback-btn:hover { background: #f3f4f6; color: #374151; border-color: #d1d5db; }
.feedback-btn.upvote:hover { color: #10b981; border-color: #34d399; background: #ecfdf5; }
.feedback-btn.downvote:hover { color: #ef4444; border-color: #f87171; background: #fef2f2; }
.feedback-thanks { margin-top: 12px; font-size: 12px; color: #10b981; font-weight: 500; }
.cancel-btn { padding: 12px 24px; background: white; color: #4b5563; border: 1px solid #d1d5db; border-radius: 8px; font-size: 15px; font-weight: 500; cursor: pointer; transition: all 0.2s; }
.cancel-btn:hover { background: #f9fafb; color: #1f2937; }

/* 漂亮的单选框样式 */
.feedback-label { display: block; font-size: 14px; font-weight: 600; color: #374151; margin-bottom: 12px; }
.feedback-options { display: flex; flex-wrap: wrap; gap: 12px; }
.radio-label { display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 14px; color: #4b5563; padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 8px; transition: all 0.2s; }
.radio-label:hover { border-color: #3b82f6; background: #eff6ff; }
.radio-label input[type="radio"] { display: none; }
.radio-custom { width: 16px; height: 16px; border: 2px solid #d1d5db; border-radius: 50%; position: relative; }
.radio-label input[type="radio"]:checked + .radio-custom { border-color: #2563eb; }
.radio-label input[type="radio"]:checked + .radio-custom::after { content: ''; position: absolute; width: 8px; height: 8px; background: #2563eb; border-radius: 50%; top: 50%; left: 50%; transform: translate(-50%, -50%); }
.radio-label:has(input[type="radio"]:checked) { border-color: #2563eb; background: #eff6ff; color: #1e40af; }
.feedback-textarea { width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; resize: vertical; transition: border-color 0.2s; font-family: inherit; }
.feedback-textarea:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1); }

/* --- 引用标记徽章 --- */
.citation-badge {
  display: inline-block;
  font-size: 11px;
  line-height: 1;
  padding: 1px 5px;
  margin: 0 1px;
  border-radius: 8px;
  background: #e0e7ff;
  color: #4338ca;
  cursor: pointer;
  font-weight: 600;
  vertical-align: super;
  transition: all 0.15s ease;
  user-select: none;
}
.citation-badge:hover {
  background: #c7d2fe;
  color: #3730a3;
  transform: scale(1.1);
}

/* --- 来源高亮动画 --- */
.source-highlight {
  animation: sourcePulse 2s ease-out;
  border-left: 3px solid #6366f1 !important;
  background: rgba(99, 102, 241, 0.08) !important;
}
@keyframes sourcePulse {
  0% { background: rgba(99, 102, 241, 0.25) !important; }
  100% { background: rgba(99, 102, 241, 0.08) !important; }
}
</style>