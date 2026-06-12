import { create } from 'zustand'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  image_uploaded?: boolean
}

export interface ChatSession {
  id: string
  title: string
  rag_enabled: boolean
  tag_enabled: boolean
  cag_enabled: boolean
  system_prompt: string | null
}

interface ChatState {
  token: string | null
  isAuthenticated: boolean
  sessions: ChatSession[]
  currentSessionId: string | null
  messages: Message[]
  isStreaming: boolean
  activeSettings: {
    rag_enabled: boolean
    tag_enabled: boolean
    cag_enabled: boolean
    system_prompt: string | null
  }
  
  // Actions
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
  fetchSessions: () => Promise<void>
  createSession: (title?: string) => Promise<string>
  setCurrentSessionId: (id: string) => void
  updateSessionSettings: (settings: Partial<typeof ChatState.prototype.activeSettings>) => Promise<void>
  uploadFile: (file: File) => Promise<void>
  sendMessage: (text: string, imageBase64?: string | null) => Promise<void>
}

export const useChatStore = create<ChatState>((set, get) => ({
  token: localStorage.getItem('vlm_token'),
  isAuthenticated: !!localStorage.getItem('vlm_token'),
  sessions: [],
  currentSessionId: null,
  messages: [],
  isStreaming: false,
  activeSettings: {
    rag_enabled: true,
    tag_enabled: false,
    cag_enabled: true,
    system_prompt: "You are Qwen2-VL, a high-performance multimodal AI assistant with cognitive tool pipelines."
  },

  login: async (email, password) => {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })
    if (!res.ok) throw new Error('Invalid credentials')
    const data = await res.json()
    localStorage.setItem('vlm_token', data.access_token)
    set({ token: data.access_token, isAuthenticated: true })
    await get().fetchSessions()
  },

  register: async (email, password) => {
    const res = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })
    if (!res.ok) throw new Error('Registration failed')
    const data = await res.json()
    localStorage.setItem('vlm_token', data.access_token)
    set({ token: data.access_token, isAuthenticated: true })
    await get().fetchSessions()
  },

  logout: () => {
    localStorage.removeItem('vlm_token')
    set({ token: null, isAuthenticated: false, sessions: [], currentSessionId: null, messages: [] })
  },

  fetchSessions: async () => {
    const { token } = get()
    if (!token) return
    const res = await fetch('/api/v1/chat/sessions', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      const sessions = await res.json()
      set({ sessions })
      if (sessions.length > 0 && !get().currentSessionId) {
        get().setCurrentSessionId(sessions[0].id)
      }
    }
  },

  createSession: async (title = 'New Conversation') => {
    const { token } = get()
    if (!token) throw new Error('Not authenticated')
    const res = await fetch('/api/v1/chat/sessions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ title })
    })
    if (!res.ok) throw new Error('Failed to create session')
    const newSession = await res.json()
    set(state => ({
      sessions: [newSession, ...state.sessions],
      currentSessionId: newSession.id,
      messages: [],
      activeSettings: {
        rag_enabled: newSession.rag_enabled,
        tag_enabled: newSession.tag_enabled,
        cag_enabled: newSession.cag_enabled,
        system_prompt: newSession.system_prompt
      }
    }))
    return newSession.id
  },

  setCurrentSessionId: (id) => {
    const session = get().sessions.find(s => s.id === id)
    if (!session) return
    set({
      currentSessionId: id,
      messages: [], // Real app would load session messages from API
      activeSettings: {
        rag_enabled: session.rag_enabled,
        tag_enabled: session.tag_enabled,
        cag_enabled: session.cag_enabled,
        system_prompt: session.system_prompt
      }
    })
  },

  updateSessionSettings: async (newSettings) => {
    const { token, currentSessionId, activeSettings } = get()
    if (!token || !currentSessionId) return
    
    const updatedSettings = { ...activeSettings, ...newSettings }
    const res = await fetch(`/api/v1/chat/sessions/${currentSessionId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(updatedSettings)
    })
    
    if (res.ok) {
      const updatedSession = await res.json()
      set(state => ({
        activeSettings: {
          rag_enabled: updatedSession.rag_enabled,
          tag_enabled: updatedSession.tag_enabled,
          cag_enabled: updatedSession.cag_enabled,
          system_prompt: updatedSession.system_prompt
        },
        sessions: state.sessions.map(s => s.id === currentSessionId ? updatedSession : s)
      }))
    }
  },

  uploadFile: async (file: File) => {
    const { token, currentSessionId } = get()
    if (!token || !currentSessionId) throw new Error('Session or Token missing')
    
    const formData = new FormData()
    formData.append('session_id', currentSessionId)
    formData.append('file', file)
    
    const res = await fetch('/api/v1/chat/upload', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    })
    
    if (!res.ok) throw new Error('File upload failed')
  },

  sendMessage: async (text: string, imageBase64 = null) => {
    const { token, currentSessionId, messages } = get()
    if (!token || !currentSessionId) return

    // Append user message
    const userMsgId = Math.random().toString()
    const userMsg: Message = {
      id: userMsgId,
      role: 'user',
      content: text,
      image_uploaded: !!imageBase64
    }
    
    // Add temporary assistant placeholder message that will be streamed into
    const assistantMsgId = Math.random().toString()
    const assistantMsg: Message = {
      id: assistantMsgId,
      role: 'assistant',
      content: ''
    }

    set({
      messages: [...messages, userMsg, assistantMsg],
      isStreaming: true
    })

    // Construct stream URL
    let url = `/api/v1/chat/stream?session_id=${currentSessionId}&query=${encodeURIComponent(text)}`
    
    try {
      const res = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (!res.ok) throw new Error('Streaming connection failed')
      
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      
      if (!reader) return

      let botResponse = ''
      
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              break
            }
            if (data.startsWith('Error:')) {
              throw new Error(data)
            }
            botResponse += data
            
            // Live update the last message in messages state
            set(state => ({
              messages: state.messages.map(msg => 
                msg.id === assistantMsgId ? { ...msg, content: botResponse } : msg
              )
            }))
          }
        }
      }
    } catch (err: any) {
      set(state => ({
        messages: state.messages.map(msg => 
          msg.id === assistantMsgId ? { ...msg, content: `Error: ${err.message || 'Stream processing failed'}` } : msg
        )
      }))
    } finally {
      set({ isStreaming: false })
    }
  }
}))
