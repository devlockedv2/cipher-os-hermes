import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import {
  CircleDot, Search, Compass, Hammer, Shield,
  Activity, Cpu, DollarSign, Ticket
} from 'lucide-react'
import './Dashboard.css'

const AGENT_ICONS: Record<string, typeof CircleDot> = {
  cipher: CircleDot,
  lens: Search,
  atlas: Compass,
  forge: Hammer,
  sentinel: Shield,
}

const AGENT_COLORS: Record<string, string> = {
  cipher: 'var(--violet)',
  lens: 'var(--cyan)',
  atlas: 'var(--mint)',
  forge: 'var(--amber)',
  sentinel: 'var(--red)',
}

export default function Dashboard() {
  const { data } = useQuery({ queryKey: ['dashboard'], queryFn: api.getDashboard })

  if (!data) return <div className="loading">Loading...</div>

  const { agents, active_tickets, system_health, recent_activity, cost_today } = data

  return (
    <div className="dashboard">
      {/* Stats Row */}
      <div className="stats-row">
        <div className="stat-card glass-card">
          <div className="stat-icon" style={{ color: 'var(--mint)' }}><Cpu size={18} /></div>
          <div className="stat-content">
            <div className="stat-value">{system_health.status === 'nominal' ? 'Nominal' : system_health.status}</div>
            <div className="stat-label mono">SYSTEM STATUS</div>
          </div>
        </div>
        <div className="stat-card glass-card">
          <div className="stat-icon" style={{ color: 'var(--cyan)' }}><Activity size={18} /></div>
          <div className="stat-content">
            <div className="stat-value">{agents.filter((a: any) => a.status === 'working').length}/{agents.length}</div>
            <div className="stat-label mono">AGENTS ACTIVE</div>
          </div>
        </div>
        <div className="stat-card glass-card">
          <div className="stat-icon" style={{ color: 'var(--violet)' }}><Ticket size={18} /></div>
          <div className="stat-content">
            <div className="stat-value">{active_tickets || 0}</div>
            <div className="stat-label mono">OPEN TICKETS</div>
          </div>
        </div>
        <div className="stat-card glass-card">
          <div className="stat-icon" style={{ color: 'var(--gold)' }}><DollarSign size={18} /></div>
          <div className="stat-content">
            <div className="stat-value">${(cost_today || 0).toFixed(2)}</div>
            <div className="stat-label mono">COST TODAY</div>
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="dashboard-grid">
        {/* Agent Status Panel */}
        <div className="glass-card agents-panel">
          <h2 className="panel-title">Agent Fleet</h2>
          <div className="agents-list">
            {agents.map((agent: any) => {
              const Icon = AGENT_ICONS[agent.name] || CircleDot
              const color = AGENT_COLORS[agent.name] || 'var(--muted)'
              return (
                <div key={agent.name} className="agent-row">
                  <div className="agent-identity">
                    <div className="agent-icon" style={{ color, borderColor: color }}>
                      <Icon size={16} />
                    </div>
                    <div>
                      <div className="agent-name">{agent.name}</div>
                      <div className="agent-role mono">{agent.role}</div>
                    </div>
                  </div>
                  <span className={`status-pill status-pill--${agent.status}`}>
                    <span className={`status-dot status-dot--${agent.status}`} />
                    {agent.status}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Activity Feed */}
        <div className="glass-card activity-panel">
          <h2 className="panel-title">Recent Activity</h2>
          <div className="activity-feed">
            {recent_activity && recent_activity.length > 0 ? (
              recent_activity.slice(0, 8).map((item: any, i: number) => (
                <div key={i} className="activity-item">
                  <div className="activity-dot" style={{
                    background: item.status === 'completed' ? 'var(--mint)' :
                                item.status === 'running' ? 'var(--cyan)' :
                                item.status === 'failed' ? 'var(--red)' : 'var(--muted)'
                  }} />
                  <div className="activity-content">
                    <div className="activity-task">{item.task || item.description || 'Task'}</div>
                    <div className="activity-meta mono">
                      {item.agent && <span>{item.agent}</span>}
                      {item.workspace && <span>• {item.workspace}</span>}
                    </div>
                  </div>
                  {item.cost > 0 && (
                    <div className="activity-cost mono">${item.cost.toFixed(3)}</div>
                  )}
                </div>
              ))
            ) : (
              <div className="empty-state">
                <Activity size={24} color="var(--muted)" />
                <p>No activity yet. Send a task to get started.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
