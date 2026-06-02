import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { CircleDot, Search, Compass, Hammer, Shield, ChevronRight } from 'lucide-react'
import { api } from '../lib/api'
import './Agents.css'

const AGENT_ICONS: Record<string, React.ElementType> = {
  cipher:   CircleDot,
  lens:     Search,
  atlas:    Compass,
  forge:    Hammer,
  sentinel: Shield,
}

const fmtCost = (n: number) => `$${(n || 0).toFixed(2)}`
const fmtTokens = (n: number | undefined | null) => {
  if (n == null || isNaN(n)) return '0'
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)
}

export default function Agents() {
  const navigate = useNavigate()
  const { data: agents = [], isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: api.getAgents,
  })

  return (
    <div className="agents-page">
      <div className="page-header">
        <div>
          <h1>Agent Fleet</h1>
          <p className="page-subtitle">Your AI team — click any agent to configure</p>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-row">Loading agents…</div>
      ) : (
        <div className="agent-list">
          {agents.map((agent: any) => {
            const Icon = AGENT_ICONS[agent.name] || CircleDot
            const color = agent.color || '#8B5CF6'
            const statusKey = agent.enabled === false ? 'disabled' : (agent.status || 'idle')

            return (
              <button
                key={agent.name}
                className="agent-row-card"
                style={{ '--agent-color': color } as any}
                onClick={() => navigate(`/agents/${agent.name}`)}
              >
                {/* Accent bar */}
                <div className="arc-bar" style={{ background: color }} />

                <div className="arc-body">
                  {/* Left: icon + identity */}
                  <div className="arc-left">
                    <div className="arc-icon" style={{ color, background: `${color}18`, borderColor: `${color}35` }}>
                      <Icon size={20} />
                    </div>
                    <div className="arc-identity">
                      <div className="arc-name">{agent.name}</div>
                      <div className="arc-role">{agent.role?.split('—')[0]?.trim()}</div>
                    </div>
                  </div>

                  {/* Mid: stats */}
                  <div className="arc-stats">
                    <div className="arc-stat">
                      <span className="arc-stat-val">{agent.tasks_completed ?? 0}</span>
                      <span className="arc-stat-lbl">done</span>
                    </div>
                    <div className="arc-stat">
                      <span className="arc-stat-val arc-stat-val--fail">{agent.tasks_failed ?? 0}</span>
                      <span className="arc-stat-lbl">failed</span>
                    </div>
                    <div className="arc-stat">
                      <span className="arc-stat-val">{fmtTokens((agent.input_tokens ?? 0) + (agent.output_tokens ?? 0))}</span>
                      <span className="arc-stat-lbl">tokens</span>
                    </div>
                    <div className="arc-stat">
                      <span className="arc-stat-val">{fmtCost(agent.total_cost)}</span>
                      <span className="arc-stat-lbl">cost</span>
                    </div>
                  </div>

                  {/* Right: status + chevron */}
                  <div className="arc-right">
                    <span className={`arc-status arc-status--${statusKey}`}>
                      <span className="arc-dot" />
                      {statusKey}
                    </span>
                    <ChevronRight size={16} className="arc-chevron" />
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
