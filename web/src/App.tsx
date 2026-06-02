import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { isAuthenticated, clearToken } from './lib/api'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import Tickets from './pages/Tickets'
import Workspaces from './pages/Workspaces'
import Activity from './pages/Activity'
import Settings from './pages/Settings'
import Chat from './pages/Chat'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 5000 } },
})

export default function App() {
  const [authed, setAuthed] = useState(isAuthenticated)

  const handleLogin = () => setAuthed(true)

  const handleLogout = () => {
    clearToken()
    setAuthed(false)
  }

  if (!authed) return (
    <QueryClientProvider client={queryClient}>
      <Login onLogin={handleLogin} />
    </QueryClientProvider>
  )

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout onLogout={handleLogout} />}>
            <Route index element={<Dashboard />} />
            <Route path="agents" element={<Agents />} />
            <Route path="tickets" element={<Tickets />} />
            <Route path="workspaces" element={<Workspaces />} />
            <Route path="activity" element={<Activity />} />
            <Route path="settings" element={<Settings />} />
            <Route path="chat" element={<Chat />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
