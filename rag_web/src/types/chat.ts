// 对话模式和状态类型定义

export enum ChatMode {
  CONSULT = 'consult',   // 咨询模式 - RAG检索
  TASK = 'task',         // 办事模式 - 向导式
  WIZARD = 'wizard'      // 向导进行中
}

// 向导选项
export interface WizardOption {
  id: string
  label: string
  description?: string
  icon?: string
  nextStep?: number
  resultData?: Record<string, any>
}

// 向导步骤
export interface WizardStep {
  step: number
  totalSteps: number
  title: string
  description?: string
  options: WizardOption[]
  selectedOption?: string
}

// 向导数据
export interface WizardData {
  taskType: string
  steps: WizardStep[]
  currentStep: number
  answers: Record<string, string>
  result?: WizardResult
}

// 向导结果
export interface WizardResult {
  title: string
  materials: string[]
  process: string[]
  tips?: string[]
}

// 消息反馈
export interface MessageFeedback {
  messageId: string
  helpful: boolean
  suggestion?: string
  timestamp: number
}

// 聊天消息扩展
export interface ChatMessageEx extends ChatMessage {
  mode?: ChatMode
  wizardData?: WizardData
  feedback?: MessageFeedback
}

// 基础聊天消息
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  images?: Array<{ url: string; file_name: string }>
  sources?: Array<{ content: string; file_name: string }>
  flowReferences?: Array<{
    matter_title: string
    summary: string
    svg_url?: string
    png_url?: string
  }>
}

// 任务信息（办事模式）
export interface TaskInfo {
  title: string
  materials: string[]
  steps: string[]
  tips?: string[]
}

// 问答响应
export interface QAResponse {
  success: boolean
  answer: string
  session_id?: string
  mode?: 'consult' | 'task'
  need_kb?: boolean
  intent_type?: 'consult' | 'task'  // 新增：意图类型
  task_info?: TaskInfo              // 新增：办事信息
  sources?: Source[]
  images?: Image[]
  wizard_data?: WizardData
  error?: string
}

export interface Source {
  content: string
  file_name: string
  chunk_id?: string
}

export interface Image {
  url: string
  file_name: string
}

// 反馈请求
export interface FeedbackRequest {
  message_id: string
  session_id: string
  helpful: boolean
  suggestion?: string
}

// 引导问题配置
export interface GuidedQuestionConfig {
  taskType: string
  title: string
  steps: WizardStepConfig[]
}

export interface WizardStepConfig {
  title: string
  question: string
  options: Array<{
    label: string
    value: string
    nextStep?: number
    isFinal?: boolean
  }>
}
