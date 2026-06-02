import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { FolderOpen } from 'lucide-react'

export default function Workspaces() {
  const { data: workspaces = [] } = useQuery({ queryKey: ['workspaces'], queryFn: api.getWorkspaces })

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ marginBottom: 24 }}>Workspaces</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
        {workspaces.map((ws: any) => (
          <div key={ws.name} className="glass-card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <FolderOpen size={20} style={{ color: 'var(--cyan)' }} />
              <span className="mono" style={{ fontSize: 14, fontWeight: 600 }}>{ws.name.toUpperCase()}</span>
            </div>
            <div style={{ display: 'flex', gap: 24, fontSize: 12, color: 'var(--muted)' }}>
              <span>Projects: {ws.project_count || 0}</span>
              <span>Cost: ${(ws.cost_total || 0).toFixed(2)}</span>
            </div>
          </div>
        ))}
        {workspaces.length === 0 && (
          <div className="glass-card" style={{ textAlign: 'center', color: 'var(--muted)', padding: 32 }}>
            No workspaces yet. Create one to get started.
          </div>
        )}
      </div>
    </div>
  )
}
