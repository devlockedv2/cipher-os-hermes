const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

// Token management
export function getToken(): string | null {
  return localStorage.getItem('cipher_token')
}

export function setToken(token: string) {
  localStorage.setItem('cipher_token', token)
}

export function clearToken() {
  localStorage.removeItem('cipher_token')
}

export function isAuthenticated(): boolean {
  return !!getToken()
}

// Core fetch helper
async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers,
    ...options,
  })

  if (res.status === 401) {
    clearToken()
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }

  return res.json()
}

// Auth
export const auth = {
  status: () => fetchAPI<{ setup_complete: boolean }>('/auth/status'),
  setup: (username: string, password: string) =>
    fetchAPI<{ success: boolean; token: string }>('/auth/setup', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  login: (username: string, password: string) =>
    fetchAPI<{ token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  logout: () => clearToken(),
}

// API methods
export const api = {
  getDashboard: () => fetchAPI<any>('/dashboard'),
  getAgents: () => fetchAPI<any[]>('/agents'),
  getAgent: (name: string) => fetchAPI<any>(`/agents/${name}`),
  updateAgentConfig: (name: string, data: {
    model?: string
    max_cost?: number
    routing_weight?: number
    enabled?: boolean
    timeout?: number
  }) => fetchAPI<any>(`/agents/${name}/config`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  updatePersonality: (name: string, content: string) =>
    fetchAPI<any>(`/agents/${name}/personality`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    }),
  resetPersonality: (name: string) =>
    fetchAPI<any>(`/agents/${name}/personality`, { method: 'DELETE' }),

  getTickets: (workspace: string = 'default') =>
    fetchAPI<any>(`/tickets?workspace=${workspace}`),
  createTicket: (workspace: string, data: any) =>
    fetchAPI<any>(`/tickets?workspace=${workspace}`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getWorkspaces: () => fetchAPI<any[]>('/workspaces'),
  createWorkspace: (name: string) =>
    fetchAPI<any>('/workspaces', { method: 'POST', body: JSON.stringify({ name }) }),

  getActivity: (params?: { workspace?: string; agent?: string; limit?: number }) => {
    const q = new URLSearchParams()
    if (params?.workspace) q.set('workspace', params.workspace)
    if (params?.agent) q.set('agent', params.agent)
    if (params?.limit) q.set('limit', String(params.limit))
    return fetchAPI<any>(`/activity${q.toString() ? '?' + q : ''}`)
  },
  getActivityStats: (workspace?: string) =>
    fetchAPI<any>(`/activity/stats${workspace ? `?workspace=${workspace}` : ''}`),

  getSettings: () => fetchAPI<any>('/settings'),
  updateSettings: (data: any) =>
    fetchAPI<any>('/settings', { method: 'PUT', body: JSON.stringify(data) }),

  sendChat: (message: string, workspace: string = 'default') =>
    fetchAPI<any>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, workspace }),
    }),
}

// WebSocket client
export class CipherWS {
  private ws: WebSocket | null = null
  private subs: Map<string, Set<(data: any) => void>> = new Map()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null

  connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const token = getToken()
    this.ws = new WebSocket(`${proto}://${location.host}/ws?token=${token}`)

    this.ws.onmessage = (e) => {
      try {
        const { channel, data } = JSON.parse(e.data)
        this.subs.get(channel)?.forEach(cb => cb(data))
        this.subs.get('*')?.forEach(cb => cb({ channel, data }))
      } catch {}
    }

    this.ws.onclose = () => {
      this.reconnectTimer = setTimeout(() => this.connect(), 3000)
    }
  }

  subscribe(channel: string, cb: (data: any) => void) {
    if (!this.subs.has(channel)) this.subs.set(channel, new Set())
    this.subs.get(channel)!.add(cb)
    return () => this.subs.get(channel)?.delete(cb)
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
  }
}

export const ws = new CipherWS()
