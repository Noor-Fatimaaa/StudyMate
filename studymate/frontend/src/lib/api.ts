import axios from 'axios'
import type { 
  Project, 
  Document, 
  ChatMessage, 
  ChatRequest, 
  ChatResponse, 
  ApiError 
} from '@/types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use((config) => {
  console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
  return config
})

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// Project API
export const projectApi = {
  async getAll(): Promise<Project[]> {
    const response = await api.get('/projects')
    return response.data
  },

  async getById(id: number): Promise<Project> {
    const response = await api.get(`/projects/${id}`)
    return response.data
  },

  async create(data: { name: string; description?: string }): Promise<Project> {
    const response = await api.post('/projects', data)
    return response.data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/projects/${id}`)
  },
}

// Document API
export const documentApi = {
  async getByProject(projectId: number): Promise<Document[]> {
    const response = await api.get(`/projects/${projectId}/documents`)
    return response.data
  },

  async getById(id: number): Promise<Document> {
    const response = await api.get(`/documents/${id}`)
    return response.data
  },

  async upload(
    projectId: number, 
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<{ message: string; document_id: number; status: string }> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post(`/projects/${projectId}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      },
    })
    return response.data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/documents/${id}`)
  },
}

// Chat API
export const chatApi = {
  async sendMessage(
    projectId: number, 
    request: ChatRequest
  ): Promise<ChatResponse> {
    const response = await api.post(`/projects/${projectId}/chat`, request)
    return response.data
  },

  async streamMessage(
    projectId: number, 
    request: ChatRequest
  ): Promise<ReadableStream> {
    const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ...request, stream: true }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.body!
  },

  async getHistory(projectId: number, limit = 50): Promise<ChatMessage[]> {
    const response = await api.get(`/projects/${projectId}/chat/history`, {
      params: { limit }
    })
    return response.data
  },

  async deleteMessage(messageId: number): Promise<void> {
    await api.delete(`/chat/${messageId}`)
  },
}

// Health check
export const healthApi = {
  async check(): Promise<{ status: string; service: string }> {
    const response = await api.get('/health')
    return response.data
  },
}

export default api