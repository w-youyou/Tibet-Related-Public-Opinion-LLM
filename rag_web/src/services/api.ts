// API服务模块
const API_BASE_URL = '/api'

export interface ChunkResult {
  id: number
  content: string
  modality_type?: string  // 'text' | 'image' | 'video'
  metadata: Record<string, any>
}

export interface ChunkResponse {
  success: boolean
  chunker_type: string
  file_name: string
  chunks: ChunkResult[]
  metadata?: Record<string, any>
  flow_extract?: {
    enabled: boolean
    success: boolean
    matter_count: number
    message?: string
  }
  statistics: {
    total_chunks: number
    chunker_name: string
    [key: string]: any
  }
}

export interface ChunkerInfo {
  name: string
  description: string
  supported_formats: string[]
  features: string[]
  category?: 'basic' | 'advanced' | 'specialized'
  params?: Record<string, {
    type: 'number' | 'boolean'
    default: number | boolean
    min?: number
    max?: number
    label: string
  }>
}

export interface ChunkersResponse {
  success: boolean
  chunkers: Record<string, ChunkerInfo>
}

// 带重试的请求函数
async function fetchWithRetry(url: string, options: RequestInit = {}, maxRetries = 3): Promise<Response> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const headers: HeadersInit = {}
      
      if (!(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json'
      }

      Object.assign(headers, options.headers)

      const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include',  // ⭐⭐ 加上这个才能带 sessionid
      })

      return response
    } catch (error) {
      if (i === maxRetries - 1) throw error
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)))
    }
  }

  throw new Error('请求失败')
}


// 健康检查
export async function healthCheck(): Promise<{ status: string; message: string }> {
  try {
    const response = await fetchWithRetry(`${API_BASE_URL}/health/`, {}, 1) // 只尝试一次，避免长时间等待
    if (!response.ok) {
      throw new Error(`健康检查失败: ${response.status}`)
    }
    return await response.json()
  } catch (error: any) {
    // 提供更友好的错误信息
    if (error.message && error.message.includes('fetch')) {
      throw new Error(`无法连接到后端服务器 (${API_BASE_URL})。请确保后端服务器已启动。`)
    }
    throw error
  }
}

// 获取分块器信息
export async function getChunkers(): Promise<ChunkersResponse> {
  const response = await fetchWithRetry(`${API_BASE_URL}/chunkers/`)
  if (!response.ok) {
    throw new Error(`获取分块器信息失败: ${response.status}`)
  }
  return await response.json()
}

// 文档分块
export async function chunkDocument(
  file: File, 
  chunkerType: string,
  knowledgeBaseId?: string,
  params?: Record<string, any>,
  enableFlowExtract: boolean = false
): Promise<ChunkResponse> {
  console.log(`准备上传文件: ${file.name}, 大小: ${file.size}, 类型: ${chunkerType}`)
  
  const formData = new FormData()
  formData.append('file', file)
  formData.append('chunker_type', chunkerType)
  if (knowledgeBaseId) {
    formData.append('knowledge_base_id', knowledgeBaseId)
  }
  formData.append('enable_flow_extract', enableFlowExtract ? 'true' : 'false')
  
  // 添加分块器参数
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        formData.append(key, String(value))
      }
    })
  }

  console.log('FormData内容:')
  for (const [key, value] of formData.entries()) {
    console.log(`${key}:`, value)
  }

  const response = await fetchWithRetry(`${API_BASE_URL}/chunk/`, {
    method: 'POST',
    body: formData,
    credentials: 'include', // 包含cookie用于session认证
  })

  console.log(`响应状态: ${response.status}`)

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    console.error('错误响应:', errorData)
    throw new Error(errorData.error || `分块处理失败: ${response.status}`)
  }

  return await response.json()
}

// 错误处理
export class APIError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
    this.name = 'APIError'
  }
}

// 请求拦截器
export async function apiRequest<T>(
  url: string, 
  options: RequestInit = {}
): Promise<T> {
  try {
    const response = await fetch(url, {
      ...options,
      credentials: 'include', // 包含cookie用于session认证
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new APIError(
        errorData.error || `请求失败: ${response.status}`,
        response.status
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof APIError) {
      throw error
    }
    throw new APIError(`网络请求失败: ${error}`)
  }
}

// ==================== 用户认证相关API ====================

export interface User {
  id: number
  username: string
  email: string
  age?: number
  gender?: 'M' | 'F' | 'O'
  user_type: 'personal' | 'enterprise'
  employee_id?: string
}

export interface AuthResponse {
  success: boolean
  message?: string
  error?: string
  user?: User
}

// 用户注册
export async function register(data: {
  username: string
  password: string
  email: string
  age?: number
  gender?: 'M' | 'F' | 'O'
  user_type: 'personal' | 'enterprise'
  employee_id?: string
}): Promise<AuthResponse> {
  return apiRequest<AuthResponse>(`${API_BASE_URL}/auth/register/`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// 用户登录
export async function login(username: string, password: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>(`${API_BASE_URL}/auth/login/`, {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

// 用户登出
export async function logout(): Promise<{ success: boolean; message: string }> {
  return apiRequest(`${API_BASE_URL}/auth/logout/`, {
    method: 'POST',
  })
}

// 获取当前用户
export async function getCurrentUser(): Promise<{ success: boolean; user?: User; error?: string }> {
  return apiRequest(`${API_BASE_URL}/auth/user/`)
}

// 更新当前用户
export async function updateUser(data: {
  username?: string
  email?: string
  age?: number
  gender?: 'M' | 'F' | 'O'
}): Promise<AuthResponse> {
  return apiRequest<AuthResponse>(`${API_BASE_URL}/auth/user/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

// ==================== 知识库管理相关API ====================

export interface KnowledgeBase {
  id: string
  name: string
  description?: string
  collection_name: string
  created_at: string
  updated_at: string
}

export interface KnowledgeBaseResponse {
  success: boolean
  knowledge_base?: KnowledgeBase
  knowledge_bases?: KnowledgeBase[]
  total?: number
  error?: string
  message?: string
}

// 创建知识库
export async function createKnowledgeBase(data: {
  name: string
  description?: string
}): Promise<KnowledgeBaseResponse> {
  return apiRequest<KnowledgeBaseResponse>(`${API_BASE_URL}/knowledge-bases/create/`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// 获取知识库列表
export async function listKnowledgeBases(): Promise<KnowledgeBaseResponse> {
  return apiRequest<KnowledgeBaseResponse>(`${API_BASE_URL}/knowledge-bases/`)
}

// 获取知识库详情
export async function getKnowledgeBase(kbId: string): Promise<KnowledgeBaseResponse> {
  return apiRequest<KnowledgeBaseResponse>(`${API_BASE_URL}/knowledge-bases/${kbId}/`)
}

// 删除知识库
export async function deleteKnowledgeBase(kbId: string): Promise<KnowledgeBaseResponse> {
  return apiRequest<KnowledgeBaseResponse>(`${API_BASE_URL}/knowledge-bases/${kbId}/delete/`, {
    method: 'DELETE',
  })
}

// ==================== 多模态问答相关API ====================

export interface QASource {
  content: string
  file_name: string
  chunk_id: string
  distance: number
}

export interface QAImage {
  url: string
  file_name: string
  distance: number
}

export interface QAMetadata {
  knowledge_base_id?: string
  collection_name: string
  total_results: number
  text_results: number
  image_results: number
}

// 拒答信息
export interface RefusalInfo {
  is_refused: boolean
  reason: 'LOW_SCORE' | 'NO_EVIDENCE' | 'OUT_OF_SCOPE'
  reply_text?: string
  max_ce?: number
  max_fused?: number
  threshold_ce?: number
  threshold_rrf?: number
  suggested_next_questions?: string[]
}

export interface QAResponse {
  success: boolean
  answer?: string
  sources?: QASource[]
  images?: QAImage[]
  flow_references?: Array<{
    matter_title: string
    summary: string
    svg_url?: string
    png_url?: string
  }>
  metadata?: QAMetadata
  session_id?: string
  error?: string
  refusal?: RefusalInfo | null
  suggested_next_questions?: string[]
}

// 多模态问答
export async function askQuestion(data: {
  question: string
  knowledge_base_id?: string
  session_id?: string
  top_k?: number
  include_images?: boolean
}): Promise<QAResponse> {
  return apiRequest<QAResponse>(`${API_BASE_URL}/qa/hybrid/`, {
    method: 'POST',
    body: JSON.stringify({
      question: data.question,
      knowledge_base_id: data.knowledge_base_id,
      session_id: data.session_id,
      top_k: data.top_k,
    }),
  })
}

// ==================== 聊天记录相关API ====================
export interface ChatSessionItem {
  id: string
  title: string
  knowledge_base_id?: string | null
  created_at: string
  updated_at: string
}

export interface ChatSessionsResponse {
  success: boolean
  sessions?: ChatSessionItem[]
  total?: number
  error?: string
}

export interface ChatMessagesResponse {
  success: boolean
  messages?: Array<{
    id: number
    role: 'user' | 'assistant'
    content: string
    images?: Array<{ url: string; file_name: string; distance?: number }>
    sources?: Array<{ content: string; file_name: string; chunk_id?: string; distance?: number }>
    refusal?: RefusalInfo | null
    suggested_next_questions?: string[]
    created_at: string
  }>
  error?: string
}

export async function listChatSessions(): Promise<ChatSessionsResponse> {
  return apiRequest<ChatSessionsResponse>(`${API_BASE_URL}/chat/sessions/`)
}

export async function createChatSessionApi(data: { title?: string; knowledge_base_id?: string }): Promise<{ success: boolean; session?: ChatSessionItem; error?: string }> {
  return apiRequest(`${API_BASE_URL}/chat/sessions/create/`, {
    method: 'POST',
    body: JSON.stringify(data || {}),
  })
}

export async function listChatMessages(sessionId: string): Promise<ChatMessagesResponse> {
  return apiRequest<ChatMessagesResponse>(`${API_BASE_URL}/chat/sessions/${sessionId}/messages/`)
}

export async function deleteChatSession(sessionId: string): Promise<{ success: boolean; message?: string; error?: string }> {
  return apiRequest(`${API_BASE_URL}/chat/sessions/${sessionId}/delete/`, { method: 'DELETE' })
}

export async function renameChatSession(sessionId: string, title: string): Promise<{ success: boolean; session?: ChatSessionItem; error?: string }> {
  return apiRequest(`${API_BASE_URL}/chat/sessions/${sessionId}/rename/`, {
    method: 'PATCH',
    body: JSON.stringify({ title })
  })
}

// ==================== 流程抽取与流程图API ====================

export interface FlowNode {
  id: string
  type: 'start' | 'step' | 'condition' | 'parallel_start' | 'parallel_join' | 'end'
  label: string
  meta?: Record<string, any>
}

export interface FlowEdge {
  from: string
  to: string
  label?: string | null
}

export interface FlowStep {
  id: string
  raw_text: string
  action: string
  department?: string | null
  materials: string[]
  time_limit?: string | null
  condition?: string | null
  branch_true_text?: string | null
  branch_false_text?: string | null
  confidence: number
}

export interface FlowGraph {
  version: string
  title: string
  source_file?: string | null
  nodes: FlowNode[]
  edges: FlowEdge[]
  steps: FlowStep[]
  meta?: Record<string, any>
}

export interface FlowRenderResult {
  svg_path?: string
  png_path?: string
  svg_url?: string
  png_url?: string
  mermaid_path?: string
  mermaid_url?: string
  renderer?: 'graphviz' | 'mermaid_fallback'
  render_message?: string
}

export interface FlowMatterResult {
  matter_index: number
  matter_title: string
  flow_graph: FlowGraph
  render: FlowRenderResult
}

export interface FlowAutoResponse {
  success: boolean
  flow_graph?: FlowGraph
  render?: FlowRenderResult
  matters?: FlowMatterResult[]
  matter_count?: number
  error?: string
}

export async function flowAutoFromFile(data: { file_path: string; title?: string; use_agent?: boolean }): Promise<FlowAutoResponse> {
  return apiRequest<FlowAutoResponse>(`${API_BASE_URL}/flow/auto/`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function flowAutoFromUpload(data: { file: File; title?: string; use_agent?: boolean }): Promise<FlowAutoResponse> {
  const formData = new FormData()
  formData.append('file', data.file)
  if (data.title) formData.append('title', data.title)
  formData.append('use_agent', String(data.use_agent ?? true))

  const response = await fetchWithRetry(`${API_BASE_URL}/flow/auto/`, {
    method: 'POST',
    body: formData,
    credentials: 'include',
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `流程图生成失败: ${response.status}`)
  }
  return await response.json()
}

export async function flowExtractText(data: { text: string; title?: string; source_file?: string }): Promise<{ success: boolean; flow_graph?: FlowGraph; error?: string }> {
  return apiRequest(`${API_BASE_URL}/flow/extract-text/`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
