const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:9800/api/v1'

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || 'API Error')
  }
  return res.json()
}

export const api = {
  // Dashboard
  getDashboard: () => fetchAPI<any>('/dashboard'),

  // Agents
  getAgents: () => fetchAPI<any[]>('/agents'),
  getAgent: (name: string) => fetchAPI<any>(`/agents/${name}`),
  updatePersonality: (name: string, content: string) =>
    fetchAPI<any>(`/agents/${name}/personality`, { method: 'PUT', body: JSON.stringify({ content }) }),
  resetPersonality: (name: string) =>
    fetchAPI<any>(`/agents/${name}/personality`, { method: 'DELETE' }),

  // Tickets
  getTickets: (workspace: string, filters?: Record<string, string>) => {
    const params = new URLSearchParams({ workspace, ...filters })
    return fetchAPI<any>(`/tickets?${params}`)
  },
  createTicket: (data: any) =>
    fetchAPI<any>('/tickets', { method: 'POST', body: JSON.stringify(data) }),
  updateTicket: (id: string, workspace: string, data: any) =>
    fetchAPI<any>(`/tickets/${id}?workspace=${workspace}`, { method: 'PATCH', body: JSON.stringify(data) }),

  // Workspaces
  getWorkspaces: () => fetchAPI<any[]>('/workspaces'),
  createWorkspace: (name: string) =>
    fetchAPI<any>('/workspaces', { method: 'POST', body: JSON.stringify({ name }) }),

  // Activity
  getActivity: (filters?: Record<string, string>) => {
    const params = new URLSearchParams(filters || {})
    return fetchAPI<any>(`/activity?${params}`)
  },
  getActivityStats: (filters?: Record<string, string>) => {
    const params = new URLSearchParams(filters || {})
    return fetchAPI<any>(`/activity/stats?${params}`)
  },

  // Settings
  getSettings: () => fetchAPI<any>('/settings'),
  updateSettings: (config: any) =>
    fetchAPI<any>('/settings', { method: 'PUT', body: JSON.stringify({ config }) }),

  // Chat
  sendChat: (message: string, workspace: string) =>
    fetchAPI<any>('/chat', { method: 'POST', body: JSON.stringify({ message, workspace }) }),

  // Health
  getHealth: () => fetchAPI<any>('/health'),
}
