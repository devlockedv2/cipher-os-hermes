import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { CircleDot, Search, Compass, Hammer, Shield } from 'lucide-react'
import './Agents.css'

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

const AGENT_DESCRIPTIONS: Record<string, string> = {
  cipher: 'Routes tasks, manages delegation, approves actions',
  lens: 'Deep research, analysis, comparisons, evaluations',
  atlas: 'Architecture, planning, estimation, scoping',
  forge: 'Implementation, testing, debugging, deployment',
  sentinel: 'Infrastructure, security, monitoring, CI/CD',
}

export default function Agents() {
  const { data: agents = [] } = useQuery({
    queryKey: ['agents'],
    queryFn: api.getAgents,
  })

  return (
    <div className="agents-page">
      <div className="page-header">
        <h1>Agent Fleet</h1>
        <p className="page-subtitle">Monitor and manage your AI team</p>
      </div>

      <div className="agents-grid">
        {agents.map((agent: any) => {
          const Icon = AGENT_ICONS[agent.name] || CircleDot
          const color = AGENT_COLORS[agent.name] || 'var(--muted)'
          return (
            <div key={agent.name} className="agent-card glass-card">
              <div className="agent-card-header">
                <div className="agent-card-icon" style={{ color, borderColor: color }}>
                  <Icon size={20} />
                </div>
                <span className={`status-pill status-pill--${agent.status}`}>
                  <span className={`status-dot status-dot--${agent.status}`} />
                  {agent.status}
                </span>
              </div>
              <div className="agent-card-body">
                <h3 className="agent-card-name">{agent.name}</h3>
                <p className="agent-card-role mono">{agent.role}</p>
                <p className="agent-card-desc">{AGENT_DESCRIPTIONS[agent.name]}</p>
              </div>
              <div className="agent-card-stats">
                <div className="agent-stat">
                  <span className="agent-stat-value">{agent.tasks_completed || 0}</span>
                  <span className="agent-stat-label mono">TASKS</span>
                </div>
                <div className="agent-stat">
                  <span className="agent-stat-value">${(agent.total_cost || 0).toFixed(2)}</span>
                  <span className="agent-stat-label mono">COST</span>
                </div>
                <div className="agent-stat">
                  <span className="agent-stat-value">{agent.uptime || '—'}</span>
                  <span className="agent-stat-label mono">UPTIME</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
