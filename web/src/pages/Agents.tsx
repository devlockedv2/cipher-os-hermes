import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { CircleDot, Search, Compass, Hammer, Shield } from 'lucide-react'

const AGENT_ICONS: Record<string, typeof CircleDot> = {
  cipher: CircleDot, lens: Search, atlas: Compass, forge: Hammer, sentinel: Shield,
}

export default function Agents() {
  const { data: agents = [] } = useQuery({ queryKey: ['agents'], queryFn: api.getAgents })

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ marginBottom: 24 }}>Agents</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
        {agents.map((agent: any) => {
          const Icon = AGENT_ICONS[agent.name] || CircleDot
          return (
            <div key={agent.name} className="glass-card" style={{ cursor: 'pointer' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <Icon size={24} style={{ color: 'var(--violet-glow)' }} />
                <div>
                  <div className="mono" style={{ fontSize: 14, fontWeight: 600 }}>{agent.name.toUpperCase()}</div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>{agent.role}</div>
                </div>
                <span className={`status-dot ${agent.status}`} style={{ marginLeft: 'auto' }} />
              </div>
              <div style={{ fontSize: 13, color: 'var(--muted)' }}>
                {agent.current_task || 'Idle — waiting for tasks'}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
