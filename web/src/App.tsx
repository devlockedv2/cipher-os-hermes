import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { auth } from './lib/api'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import Tickets from './pages/Tickets'
import Workspaces from './pages/Workspaces'
import Activity from './pages/Activity'
import Settings from './pages/Settings'
import Chat from './pages/Chat'
import './index.css'
import './pages/Login.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchInterval: 5000, staleTime: 2000 },
  },
})

export default function App() {
  const [authenticated, setAuthenticated] = useState(auth.isAuthenticated())

  if (!authenticated) {
    return (
      <Login onLogin={() => setAuthenticated(true)} />
    )
  }

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout onLogout={() => { auth.clearToken(); setAuthenticated(false) }} />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/tickets" element={<Tickets />} />
            <Route path="/workspaces" element={<Workspaces />} />
            <Route path="/activity" element={<Activity />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/chat" element={<Chat />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
