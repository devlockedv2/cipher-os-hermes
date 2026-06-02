import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import {
  CircleDot, Search, Compass, Hammer, Shield
} from 'lucide-react'
import './Dashboard.css'

const AGENT_ICONS: Record<string, typeof CircleDot> = {
  cipher: CircleDot,
  lens: Search,
  atlas: Compass,
  forge: Hammer,
  sentinel: Shield,
}

const STATUS_COLORS: Record<string, string> = {
  idle: 'var(--mint)',
  working: 'var(--cyan)',
  errored: 'var(--red)',
  dead: 'var(--muted)',
}

export default function Dashboard() {
  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: api.getDashboard,
  })

  if (isLoading) return <div className="loading">Loading...</div>

  const agents = dashboard?.agents || []
  const activity = dashboard?.recent_activity || []
  const stats = dashboard?.stats || {}

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Orchestrator Overview</h1>
        <p className="mono subtitle">
          CIPHER-OS v0.1.0 ONLINE • ALL SYSTEMS NOMINAL
        </p>
      </div>

      <div className="dashboard-grid">
        {/* Metrics Row */}
        <div className="metrics-row">
          <div className="glass-card metric-card">
            <span className="label">Tokens Today</span>
            <span className="metric-value">
              {((stats.total_input_tokens || 0) + (stats.total_output_tokens || 0)).toLocaleString()}
            </span>
          </div>
          <div className="glass-card metric-card">
            <span className="label">Cost Today</span>
            <span className="metric-value cost">
              ${(stats.total_cost || 0).toFixed(2)}
            </span>
          </div>
          <div className="glass-card metric-card">
            <span className="label">Active Tickets</span>
            <span className="metric-value">
              {stats.total_tasks || 0}
            </span>
          </div>
        </div>

        {/* Agents Panel */}
        <div className="glass-card agents-panel">
          <div className="panel-header">
            <h3>Active Agents</h3>
            <span className="label badge">{agents.filter((a: any) => a.status !== 'dead').length} ONLINE</span>
          </div>
          <div className="agent-list">
            {agents.map((agent: any) => {
              const Icon = AGENT_ICONS[agent.name] || CircleDot
              return (
                <div key={agent.name} className="agent-row">
                  <div className="agent-icon" style={{ color: STATUS_COLORS[agent.status] || 'var(--muted)' }}>
                    <Icon size={18} />
                  </div>
                  <div className="agent-info">
                    <span className="agent-name">{agent.name.toUpperCase()}</span>
                    <span className="agent-role">{agent.role.split('—')[1]?.trim() || agent.role}</span>
                  </div>
                  <span className={`status-dot ${agent.status}`} />
                </div>
              )
            })}
          </div>
        </div>

        {/* Activity Log */}
        <div className="glass-card activity-panel">
          <div className="panel-header">
            <h3>Recent Operations Log</h3>
            <span className="label live-indicator">● LIVE FEED</span>
          </div>
          <div className="activity-table">
            <div className="table-header">
              <span>TASK ID</span>
              <span>TIMESTAMP</span>
              <span>DESCRIPTION</span>
              <span>AGENT</span>
              <span>STATUS</span>
            </div>
            {activity.length === 0 ? (
              <div className="empty-state">
                <span className="muted">No activity yet. Send a task to get started.</span>
              </div>
            ) : (
              activity.slice(0, 8).map((entry: any, i: number) => (
                <div key={i} className={`table-row ${entry.status === 'running' ? 'active-row' : ''}`}>
                  <span className="mono">{entry.uuid?.slice(0, 8) || '—'}</span>
                  <span className="mono">{entry.created_at?.slice(11, 19) || '—'}</span>
                  <span className="task-desc">{entry.task?.slice(0, 50) || '—'}</span>
                  <span className="mono agent-tag">{entry.agent?.toUpperCase() || '—'}</span>
                  <span className={`status-tag ${entry.status}`}>{entry.status?.toUpperCase()}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
