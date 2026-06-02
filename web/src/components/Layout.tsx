import { Outlet, NavLink } from 'react-router-dom'
import {
  LayoutGrid, Bot, ClipboardList, FolderOpen,
  Activity, Settings, MessageSquare
} from 'lucide-react'
import './Layout.css'

const NAV_ITEMS = [
  { path: '/', label: 'Overview', icon: LayoutGrid },
  { path: '/agents', label: 'Agents', icon: Bot },
  { path: '/tickets', label: 'Tickets', icon: ClipboardList },
  { path: '/workspaces', label: 'Workspaces', icon: FolderOpen },
  { path: '/activity', label: 'Activity', icon: Activity },
  { path: '/settings', label: 'Settings', icon: Settings },
]

export default function Layout() {
  return (
    <div className="app-layout">
      <div className="dot-grid" />

      {/* Top Navigation */}
      <header className="topnav">
        <div className="topnav-left">
          <div className="logo">
            <svg viewBox="0 0 32 32" width="28" height="28">
              <circle cx="16" cy="16" r="14" fill="none" stroke="var(--violet)" strokeWidth="1.5" />
              <circle cx="16" cy="16" r="9" fill="none" stroke="var(--violet-glow)" strokeWidth="1" />
              <circle cx="16" cy="16" r="3" fill="var(--violet)" />
            </svg>
            <span className="logo-text">CIPHER-OS</span>
          </div>
        </div>

        <nav className="topnav-center">
          {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              end={path === '/'}
            >
              <Icon size={16} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="topnav-right">
          <NavLink to="/chat" className={({ isActive }) => `chat-btn ${isActive ? 'active' : ''}`}>
            <MessageSquare size={16} />
            <span>Chat</span>
          </NavLink>
          <div className="system-status">
            <span className="status-dot idle" />
            <span className="mono">System Active</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
