import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import {
  CircleDot, Search, Compass, Hammer, Shield,
  Activity, DollarSign, CheckCircle, XCircle,
  Zap, Clock, ChevronRight, TrendingUp
} from 'lucide-react'
import './Dashboard.css'

const AGENT_ICONS: Record<string, any> = {
  cipher: CircleDot, lens: Search, atlas: Compass, forge: Hammer, sentinel: Shield,
}
const AGENT_COLORS: Record<string, string> = {
  cipher: '#8B5CF6', lens: '#06B6D4', atlas: '#10B981', forge: '#F59E0B', sentinel: '#EF4444',
}

function fmtTokens(n: number) {
  if (!n) return '0'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

function fmtCost(n: number) {
  if (!n) return '$0.00'
  if (n < 0.001) return '<$0.001'
  return '$' + n.toFixed(n < 0.1 ? 4 : 2)
}

// SVG sparkline for hourly activity
function Sparkline({ data, color = '#8B5CF6' }: { data: { hour: string; tasks: number }[], color?: string }) {
  if (!data || data.length < 2) return <div className="sparkline-empty">No data yet</div>
  const max = Math.max(...data.map(d => d.tasks), 1)
  const W = 200, H = 40, pad = 4
  const pts = data.map((d, i) => {
    const x = pad + (i / (data.length - 1)) * (W - pad * 2)
    const y = H - pad - ((d.tasks / max) * (H - pad * 2))
    return `${x},${y}`
  }).join(' ')
  const area = `${pad},${H - pad} ` + pts + ` ${W - pad},${H - pad}`
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="sparkline-svg" preserveAspectRatio="none">
      <defs>
        <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <polygon points={area} fill="url(#sg)" />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}

// Horizontal bar chart for agent cost breakdown
function AgentBarChart({ data }: { data: any[] }) {
  if (!data || data.length === 0) return <div className="empty-state"><p>No agent data yet</p></div>
  const max = Math.max(...data.map(d => d.cost), 0.0001)
  return (
    <div className="agent-bars">
      {data.map(d => {
        const color = AGENT_COLORS[d.agent] || '#8B5CF6'
        const pct = (d.cost / max) * 100
        return (
          <div key={d.agent} className="agent-bar-row">
            <div className="agent-bar-label">
              <span className="agent-bar-name">{d.agent}</span>
              <span className="agent-bar-cost mono">{fmtCost(d.cost)}</span>
            </div>
            <div className="agent-bar-track">
              <div className="agent-bar-fill" style={{ width: `${pct}%`, background: color, boxShadow: `0 0 8px ${color}66` }} />
            </div>
            <div className="agent-bar-stats mono">
              <span>{d.completed}/{d.total}</span>
              <span>{fmtTokens(d.output_tokens)} tok</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default function Dashboard() {
  const { data, isLoading } = useQuery({ queryKey: ['dashboard'], queryFn: api.getDashboard, refetchInterval: 15000 })
  const navigate = useNavigate()

  if (isLoading || !data) return (
    <div className="dashboard">
      <div className="loading">Loading...</div>
    </div>
  )

  const { agents, system_health, metrics, recent_activity, hourly_activity, agent_breakdown } = data
  const m = metrics || {}
  const successRate = m.tasks_total > 0
    ? Math.round((m.tasks_completed / m.tasks_total) * 100)
    : 0

  return (
    <div className="dashboard">

      {/* ── Metric Cards ─────────────────────────────── */}
      <div className="stats-row">
        <div className="stat-card glass-card">
          <div className="stat-icon" style={{ color: '#F59E0B' }}><DollarSign size={18} /></div>
          <div className="stat-content">
            <div className="stat-value">{fmtCost(m.cost_today || 0)}</div>
            <div className="stat-label mono">COST TODAY</div>
          </div>
        </div>
        <div className="stat-card glass-card">
          <div className="stat-icon" style={{ color: '#8B5CF6' }}><TrendingUp size={18} /></div>
          <div className="stat-content">
            <div className="stat-value">{fmtCost(m.cost_alltime || 0)}</div>
            <div className="stat-label mono">ALL-TIME COST</div>
          </div>
        </div>
        <div className="stat-card glass-card">
          <div className="stat-icon" style={{ color: '#10B981' }}><CheckCircle size={18} /></div>
          <div className="stat-content">
            <div className="stat-value">{m.tasks_completed || 0}<span className="stat-sub">/{m.tasks_total || 0}</span></div>
            <div className="stat-label mono">TASKS DONE</div>
          </div>
        </div>
        <div className="stat-card glass-card">
          <div className="stat-icon" style={{ color: '#EF4444' }}><XCircle size={18} /></div>
          <div className="stat-content">
            <div className="stat-value">{successRate}%</div>
            <div className="stat-label mono">SUCCESS RATE</div>
          </div>
        </div>
        <div className="stat-card glass-card">
          <div className="stat-icon" style={{ color: '#06B6D4' }}><Zap size={18} /></div>
          <div className="stat-content">
            <div className="stat-value">{fmtTokens(m.total_tokens || 0)}</div>
            <div className="stat-label mono">TOTAL TOKENS</div>
          </div>
        </div>
        <div className="stat-card glass-card">
          <div className="stat-icon" style={{ color: '#10B981' }}><Clock size={18} /></div>
          <div className="stat-content">
            <div className="stat-value">{system_health?.uptime || '—'}</div>
            <div className="stat-label mono">UPTIME</div>
          </div>
        </div>
      </div>

      {/* ── Agent Cards ───────────────────────────────── */}
      <div className="agent-cards-row">
        {agents.map((agent: any) => {
          const Icon = AGENT_ICONS[agent.name] || CircleDot
          const color = AGENT_COLORS[agent.name] || '#8B5CF6'
          return (
            <button
              key={agent.name}
              className="agent-glance-card glass-card"
              onClick={() => navigate(`/agents/${agent.name}`)}
              style={{ '--agent-color': color } as any}
            >
              <div className="agc-header">
                <div className="agc-icon" style={{ color, background: `${color}18`, borderColor: `${color}44` }}>
                  <Icon size={16} />
                </div>
                <ChevronRight size={13} className="agc-arrow" />
              </div>
              <div className="agc-name">{agent.name}</div>
              <div className="agc-role mono">{(agent.role || '').split('—')[0].trim()}</div>
              <div className="agc-stats-mini mono">
                <span>{agent.tasks_completed || 0} done</span>
                <span>{fmtCost(agent.total_cost || 0)}</span>
              </div>
              <div className="agc-footer">
                <span className={`agc-status agc-status--${agent.enabled === false ? 'disabled' : (agent.status || 'idle')}`}>
                  <span className="agc-dot" />
                  {agent.enabled === false ? 'off' : (agent.status || 'idle')}
                </span>
                <span className="agc-tokens mono">{fmtTokens((agent.input_tokens || 0) + (agent.output_tokens || 0))}</span>
              </div>
            </button>
          )
        })}
      </div>

      {/* ── Bottom Grid: Activity sparkline + Agent bars + Feed ── */}
      <div className="dashboard-bottom">

        {/* Activity Sparkline */}
        <div className="glass-card spark-panel">
          <div className="panel-header">
            <h2 className="panel-title">Activity (24h)</h2>
            <span className="panel-badge mono">{m.tasks_total || 0} tasks</span>
          </div>
          <Sparkline data={hourly_activity || []} color="#8B5CF6" />
          <div className="spark-legend">
            <span className="mono">in: {fmtTokens(m.input_tokens || 0)}</span>
            <span className="mono">out: {fmtTokens(m.output_tokens || 0)}</span>
            <span className="mono" style={{ color: '#F59E0B' }}>{fmtCost(m.cost_today || 0)} today</span>
          </div>
        </div>

        {/* Agent Cost Breakdown */}
        <div className="glass-card breakdown-panel">
          <div className="panel-header">
            <h2 className="panel-title">Agent Breakdown</h2>
          </div>
          <AgentBarChart data={agent_breakdown || []} />
        </div>

        {/* Recent Activity Feed */}
        <div className="glass-card activity-panel">
          <div className="panel-header">
            <h2 className="panel-title">Recent Activity</h2>
            <button className="panel-link" onClick={() => navigate('/activity')}>View all</button>
          </div>
          <div className="activity-feed">
            {recent_activity && recent_activity.length > 0 ? (
              recent_activity.slice(0, 10).map((item: any, i: number) => (
                <div key={i} className="activity-item">
                  <div className="activity-dot" style={{
                    background: item.status === 'completed' ? '#10B981' :
                                item.status === 'running' ? '#06B6D4' :
                                item.status === 'failed' ? '#EF4444' : '#666'
                  }} />
                  <div className="activity-content">
                    <div className="activity-task">{item.task || '—'}</div>
                    <div className="activity-meta mono">
                      {item.agent && <span style={{ color: AGENT_COLORS[item.agent] || 'var(--muted)' }}>{item.agent}</span>}
                      {item.workspace && <span>· {item.workspace}</span>}
                      {item.created_at && <span>· {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>}
                    </div>
                  </div>
                  <div className="activity-right">
                    {item.cost > 0 && <div className="activity-cost mono">{fmtCost(item.cost)}</div>}
                    <div className={`activity-status activity-status--${item.status}`}>{item.status}</div>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <Activity size={24} color="var(--muted)" />
                <p>No activity yet.</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}
