import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useState } from 'react'
import {
  LayoutGrid, Bot, ClipboardList, FolderOpen,
  Activity, Settings, MessageSquare, LogOut, Menu, X, Kanban
} from 'lucide-react'
import './Layout.css'

const NAV_ITEMS = [
  { to: '/', icon: LayoutGrid, label: 'Dashboard' },
  { to: '/agents', icon: Bot, label: 'Agents' },
  { to: '/plan', icon: Kanban, label: 'Plan' },
  { to: '/tickets', icon: ClipboardList, label: 'Tickets' },
  { to: '/workspaces', icon: FolderOpen, label: 'Workspaces' },
  { to: '/activity', icon: Activity, label: 'Activity' },
  { to: '/chat', icon: MessageSquare, label: 'Chat' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout({ onLogout }: { onLogout?: () => void }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const location = useLocation()
  const isChat = location.pathname === '/chat'

  return (
    <div className="app-layout">
      <nav className="topnav">
        <div className="topnav-brand">
          <span className="brand-text">CIPHER-OS</span>
          <span className="brand-version mono">v0.1.0</span>
        </div>

        <div className={`topnav-links ${mobileMenuOpen ? 'open' : ''}`}>
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              <Icon size={16} />
              <span>{label}</span>
            </NavLink>
          ))}
          {onLogout && (
            <button onClick={onLogout} className="nav-link logout-btn-mobile">
              <LogOut size={16} />
              <span>Logout</span>
            </button>
          )}
        </div>

        <div className="topnav-actions">
          {onLogout && (
            <button onClick={onLogout} className="logout-btn" title="Logout">
              <LogOut size={16} />
            </button>
          )}
          <button
            className="mobile-menu-btn"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </nav>
      <main className="main-content">
        {isChat ? (
          <Outlet />
        ) : (
          <div className="scrollable-page">
            <Outlet />
          </div>
        )}
      </main>
    </div>
  )
}
