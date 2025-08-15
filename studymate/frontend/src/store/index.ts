import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { 
  Project, 
  Document, 
  ChatMessage, 
  UploadProgress, 
  ModelType,
  AppSettings 
} from '@/types'

interface AppState {
  // Current selections
  currentProject: Project | null
  currentDocuments: Document[]
  chatHistory: ChatMessage[]
  
  // UI state
  sidebarOpen: boolean
  uploadProgress: UploadProgress[]
  isLoading: boolean
  error: string | null
  
  // Settings
  settings: AppSettings
  
  // Actions
  setCurrentProject: (project: Project | null) => void
  setCurrentDocuments: (documents: Document[]) => void
  addDocument: (document: Document) => void
  removeDocument: (documentId: number) => void
  updateDocument: (documentId: number, updates: Partial<Document>) => void
  
  setChatHistory: (messages: ChatMessage[]) => void
  addChatMessage: (message: ChatMessage) => void
  removeChatMessage: (messageId: number) => void
  
  setSidebarOpen: (open: boolean) => void
  toggleSidebar: () => void
  
  setUploadProgress: (progress: UploadProgress[]) => void
  addUploadProgress: (progress: UploadProgress) => void
  updateUploadProgress: (filename: string, updates: Partial<UploadProgress>) => void
  removeUploadProgress: (filename: string) => void
  
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  
  updateSettings: (settings: Partial<AppSettings>) => void
  
  // Reset functions
  reset: () => void
  resetProject: () => void
}

const initialSettings: AppSettings = {
  defaultModel: 'claude',
  streamResponses: true,
  darkMode: false,
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Initial state
      currentProject: null,
      currentDocuments: [],
      chatHistory: [],
      sidebarOpen: true,
      uploadProgress: [],
      isLoading: false,
      error: null,
      settings: initialSettings,

      // Project actions
      setCurrentProject: (project) => 
        set({ currentProject: project }),

      // Document actions
      setCurrentDocuments: (documents) => 
        set({ currentDocuments: documents }),

      addDocument: (document) => 
        set((state) => ({ 
          currentDocuments: [...state.currentDocuments, document] 
        })),

      removeDocument: (documentId) => 
        set((state) => ({
          currentDocuments: state.currentDocuments.filter(doc => doc.id !== documentId)
        })),

      updateDocument: (documentId, updates) => 
        set((state) => ({
          currentDocuments: state.currentDocuments.map(doc =>
            doc.id === documentId ? { ...doc, ...updates } : doc
          )
        })),

      // Chat actions
      setChatHistory: (messages) => 
        set({ chatHistory: messages }),

      addChatMessage: (message) => 
        set((state) => ({ 
          chatHistory: [...state.chatHistory, message] 
        })),

      removeChatMessage: (messageId) => 
        set((state) => ({
          chatHistory: state.chatHistory.filter(msg => msg.id !== messageId)
        })),

      // UI actions
      setSidebarOpen: (open) => 
        set({ sidebarOpen: open }),

      toggleSidebar: () => 
        set((state) => ({ sidebarOpen: !state.sidebarOpen })),

      // Upload progress actions
      setUploadProgress: (progress) => 
        set({ uploadProgress: progress }),

      addUploadProgress: (progress) => 
        set((state) => ({ 
          uploadProgress: [...state.uploadProgress, progress] 
        })),

      updateUploadProgress: (filename, updates) => 
        set((state) => ({
          uploadProgress: state.uploadProgress.map(progress =>
            progress.filename === filename ? { ...progress, ...updates } : progress
          )
        })),

      removeUploadProgress: (filename) => 
        set((state) => ({
          uploadProgress: state.uploadProgress.filter(progress => 
            progress.filename !== filename
          )
        })),

      // Loading and error actions
      setLoading: (loading) => 
        set({ isLoading: loading }),

      setError: (error) => 
        set({ error }),

      // Settings actions
      updateSettings: (newSettings) => 
        set((state) => ({ 
          settings: { ...state.settings, ...newSettings } 
        })),

      // Reset actions
      reset: () => 
        set({
          currentProject: null,
          currentDocuments: [],
          chatHistory: [],
          uploadProgress: [],
          isLoading: false,
          error: null,
        }),

      resetProject: () => 
        set({
          currentDocuments: [],
          chatHistory: [],
          uploadProgress: [],
        }),
    }),
    {
      name: 'studymate-storage',
      partialize: (state) => ({
        settings: state.settings,
        sidebarOpen: state.sidebarOpen,
      }),
    }
  )
)