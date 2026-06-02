import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import Tickets from './pages/Tickets'
import Workspaces from './pages/Workspaces'
import Activity from './pages/Activity'
import Settings from './pages/Settings'
import Chat from './pages/Chat'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchInterval: 5000, // Real-time feel
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
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

export default App
