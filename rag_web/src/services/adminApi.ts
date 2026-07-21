// 后台管理 API 服务模块
const API_BASE_URL = '/api/admin'

export interface AdminTokens {
  access_token: string
  refresh_token: string
  expires_in: number
  role: 'SUPER_ADMIN' | 'KB_ADMIN'
  username: string
  email: string
}

export interface AdminStats {
  kb_total: number
  doc_total: number
  chunk_total: number
  embedding_total: number
  recent_files: Array<{
    id: string
    document_id: string
    name: string
    kb_name: string
    version: string
    uploaded_at: string
    size: number
    status: 'active' | 'inactive' | 'deleted'
  }>
  operation_logs: Array<{
    id: number
    admin_username: string
    action: string
    details: string
    created_at: string
  }>
}

export interface AdminKB {
  id: string
  name: string
  description?: string
  collection_name: string
  doc_count: number
  chunk_count: number
  status: 'active' | 'inactive'
  created_at: string
}

export interface AdminDoc {
  id: string
  name: string
  kb_id: string
  kb_name: string
  status: 'active' | 'inactive' | 'deleted'
  created_at: string
  version: string
  size: number
  chunk_count: number
  embedding_count: number
  chunker_type: string
}

export interface AdminDocVersion {
  id: string
  version_number: number
  file_size: number
  chunk_count: number
  embedding_count: number
  chunker_type: string
  status: 'current' | 'historical'
  uploaded_at: string
  uploaded_by: string
  remark?: string
}

export interface AdminDocDetailResponse {
  basic: {
    id: string
    name: string
    status: 'active' | 'inactive' | 'deleted'
    kb_id: string
    kb_name: string
    created_at: string
    current_version: number | null
    chunker_type: string
    file_size: number
    chunk_count: number
    embedding_count: number
  }
  chunks: Array<{
    chunk_id: string | number
    content: string
    length: number
    is_active?: boolean
    version_number?: string
  }>
  versions: AdminDocVersion[]
  logs: Array<{
    id: number
    operator: string
    action: string
    details: string
    created_at: string
  }>
}

export class AdminAPIError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
    this.name = 'AdminAPIError'
  }
}

// 统一后台网络请求包装器 (带 Bearer JWT 自动校验注入)
export async function adminRequest<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('admin_access_token')
  const headers: HeadersInit = {}

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  Object.assign(headers, options.headers)

  try {
    const response = await fetch(url, {
      ...options,
      headers
    })

    // 针对 401 状态，提示需要重新登录并清除残余状态
    if (response.status === 401) {
      localStorage.removeItem('admin_access_token')
      localStorage.removeItem('admin_refresh_token')
      localStorage.removeItem('admin_username')
      localStorage.removeItem('admin_role')
      // 如果是在浏览器环境，重定向至登录页
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/rag-admin/login')) {
        window.location.href = '/rag-admin/login?expired=1'
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new AdminAPIError(
        errorData.error || `请求失败: ${response.status}`,
        response.status
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof AdminAPIError) {
      throw error
    }
    throw new AdminAPIError(`网络请求失败: ${error}`)
  }
}

// ==================== 1. 管理员认证 API ====================

export async function adminLogin(username: string, password: string): Promise<{ success: boolean; data: AdminTokens }> {
  const res = await adminRequest<{ success: boolean; data: AdminTokens }>(`${API_BASE_URL}/auth/login/`, {
    method: 'POST',
    body: JSON.stringify({ username, password })
  })

  if (res.success && res.data) {
    localStorage.setItem('admin_access_token', res.data.access_token)
    localStorage.setItem('admin_refresh_token', res.data.refresh_token)
    localStorage.setItem('admin_username', res.data.username)
    localStorage.setItem('admin_role', res.data.role)
  }
  return res
}

export async function adminLogout(): Promise<{ success: boolean; message: string }> {
  try {
    await adminRequest(`${API_BASE_URL}/auth/logout/`, { method: 'POST' })
  } finally {
    localStorage.removeItem('admin_access_token')
    localStorage.removeItem('admin_refresh_token')
    localStorage.removeItem('admin_username')
    localStorage.removeItem('admin_role')
  }
  return { success: true, message: '注销成功' }
}

export function isAdminLoggedIn(): boolean {
  return !!localStorage.getItem('admin_access_token')
}

// ==================== 2. 大屏统计 API ====================

export async function getDashboardStats(): Promise<{ success: boolean; data: AdminStats }> {
  return adminRequest<{ success: boolean; data: AdminStats }>(`${API_BASE_URL}/dashboard/stats/`)
}

// ==================== 3. 知识库管理 API ====================

export async function listKBs(): Promise<{ success: boolean; data: AdminKB[] }> {
  return adminRequest<{ success: boolean; data: AdminKB[] }>(`${API_BASE_URL}/kb/`)
}

export async function createKB(name: string, description: string): Promise<{ success: boolean; data: AdminKB }> {
  return adminRequest<{ success: boolean; data: AdminKB }>(`${API_BASE_URL}/kb/`, {
    method: 'POST',
    body: JSON.stringify({ name, description })
  })
}

export async function updateKB(id: string, name: string, description: string, status?: string): Promise<{ success: boolean; data: Partial<AdminKB> }> {
  return adminRequest<{ success: boolean; data: Partial<AdminKB> }>(`${API_BASE_URL}/kb/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify({ name, description, status })
  })
}

export async function deleteKB(id: string): Promise<{ success: boolean; message: string }> {
  return adminRequest<{ success: boolean; message: string }>(`${API_BASE_URL}/kb/${id}/`, {
    method: 'DELETE'
  })
}

// ==================== 4. 文档生命周期 API ====================

export async function listDocs(params: {
  knowledge_base_id?: string
  status?: string
  search?: string
}): Promise<{ success: boolean; data: AdminDoc[] }> {
  const urlParams = new URLSearchParams()
  if (params.knowledge_base_id) urlParams.append('knowledge_base_id', params.knowledge_base_id)
  if (params.status) urlParams.append('status', params.status)
  if (params.search) urlParams.append('search', params.search)

  const query = urlParams.toString()
  return adminRequest<{ success: boolean; data: AdminDoc[] }>(`${API_BASE_URL}/document/${query ? '?' + query : ''}`)
}

export async function uploadDoc(
  file: File,
  kbId: string,
  chunkerType: string
): Promise<{ success: boolean; message: string; data: any }> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('knowledge_base_id', kbId)
  formData.append('chunker_type', chunkerType)

  return adminRequest<{ success: boolean; message: string; data: any }>(`${API_BASE_URL}/document/upload/`, {
    method: 'POST',
    body: formData
  })
}

export async function setDocStatus(id: string, status: 'active' | 'inactive' | 'deleted'): Promise<{ success: boolean; message: string; data: any }> {
  return adminRequest<{ success: boolean; message: string; data: any }>(`${API_BASE_URL}/document/${id}/status/`, {
    method: 'PATCH',
    body: JSON.stringify({ status })
  })
}

export async function getDocDetail(id: string, showAllChunks: boolean = false): Promise<{ success: boolean; data: AdminDocDetailResponse }> {
  return adminRequest<{ success: boolean; data: AdminDocDetailResponse }>(`${API_BASE_URL}/document/${id}/?show_all_chunks=${showAllChunks}`)
}

export async function updateDocumentChunk(docId: string, chunkId: string, newContent: string, remark: string = ''): Promise<{ success: boolean; message?: string }> {
  return adminRequest<{ success: boolean; message?: string }>(`${API_BASE_URL}/document/${docId}/edit-chunk/`, {
    method: 'POST',
    body: JSON.stringify({ chunk_id: chunkId, new_content: newContent, remark })
  })
}

// ==================== 5. 文档版本管理 API ====================

export async function uploadVersion(
  docId: string,
  file: File,
  chunkerType: string,
  remark?: string
): Promise<{ success: boolean; message: string; data: any }> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('document_id', docId)
  formData.append('chunker_type', chunkerType)
  if (remark) formData.append('remark', remark)

  return adminRequest<{ success: boolean; message: string; data: any }>(`${API_BASE_URL}/document-version/upload/`, {
    method: 'POST',
    body: formData
  })
}

export async function switchVersion(versionId: string, remark?: string): Promise<{ success: boolean; message: string; data: any }> {
  return adminRequest<{ success: boolean; message: string; data: any }>(`${API_BASE_URL}/document-version/switch/`, {
    method: 'POST',
    body: JSON.stringify({ version_id: versionId, remark })
  })
}

// ==================== 6. 审计日志 API ====================

export async function getOperationLogs(params: {
  action?: string
  username?: string
} = {}): Promise<{ success: boolean; data: any[] }> {
  const urlParams = new URLSearchParams()
  if (params.action) urlParams.append('action', params.action)
  if (params.username) urlParams.append('username', params.username)

  const query = urlParams.toString()
  return adminRequest<{ success: boolean; data: any[] }>(`${API_BASE_URL}/settings/logs/${query ? '?' + query : ''}`)
}


// ==================== 5. 管理员账号管理 API ====================

export async function addAdminAccount(data: any): Promise<{ success: boolean; message?: string; data?: any }> {
  return adminRequest<{ success: boolean; message?: string; data?: any }>(`${API_BASE_URL}/auth/add-account/`, {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export async function changeAdminPassword(data: any): Promise<{ success: boolean; message?: string }> {
  return adminRequest<{ success: boolean; message?: string }>(`${API_BASE_URL}/auth/change-password/`, {
    method: 'POST',
    body: JSON.stringify(data)
  })
}
