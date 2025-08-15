export interface Project {
  id: number
  name: string
  description?: string
  created_at: string
  updated_at?: string
}

export interface Document {
  id: number
  filename: string
  original_filename: string
  file_type: string
  file_size: number
  content_preview?: string
  page_count?: number
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  error_message?: string
  created_at: string
}

export interface ChatMessage {
  id: number
  message: string
  response: string
  citations?: Citation[]
  related_excerpts?: string[]
  model_used: string
  tokens_used?: number
  response_time?: number
  created_at: string
}

export interface Citation {
  file: string
  page?: number
  section?: string
}

export interface ChatRequest {
  message: string
  model_type?: string
  stream?: boolean
}

export interface ChatResponse {
  answer: string
  citations: Citation[]
  related_excerpts: string[]
  model_used: string
  tokens_used: number
  response_time: number
}

export interface StreamingChatChunk {
  type: 'content' | 'citations' | 'related_excerpts' | 'done' | 'error'
  data: any
}

export interface UploadProgress {
  filename: string
  progress: number
  status: 'uploading' | 'processing' | 'completed' | 'error'
  error?: string
}

export interface ApiError {
  detail: string
}

export type ModelType = 'claude' | 'openai' | 'gemini' | 'local'

export interface AppSettings {
  defaultModel: ModelType
  streamResponses: boolean
  darkMode: boolean
}