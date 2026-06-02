import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../lib/api'
import { FolderOpen, Plus, Cpu, DollarSign } from 'lucide-react'
import './Workspaces.css'

export default function Workspaces() {
  const qc = useQueryClient()
  const { data: workspaces = [] } = useQuery({
    queryKey: ['workspaces'],
    queryFn: api.getWorkspaces,
  })
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')

  const createMutation = useMutation({
    mutationFn: (name: string) => api.createWorkspace(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workspaces'] })
      setNewName('')
      setCreating(false)
    },
  })

  const handleCreate = () => {
    if (!newName.trim()) return
    createMutation.mutate(newName.trim().toLowerCase().replace(/[^a-z0-9-_]/g, '-'))
  }

  return (
    <div className="workspaces-page">
      <div className="page-header">
        <div>
          <h1>Workspaces</h1>
          <p className="page-subtitle">Isolated environments for your projects · {workspaces.length} total</p>
        </div>
        <button className="create-btn" onClick={() => setCreating(true)}>
          <Plus size={16} />
          <span>New Workspace</span>
        </button>
      </div>

      {creating && (
        <div className="create-workspace glass-card">
          <input
            type="text"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') handleCreate()
              if (e.key === 'Escape') setCreating(false)
            }}
            placeholder="workspace-name (lowercase, hyphens ok)"
            autoFocus
            className="workspace-input"
          />
          <button
            onClick={handleCreate}
            className="create-confirm-btn"
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? 'Creating…' : 'Create'}
          </button>
          <button onClick={() => setCreating(false)} className="create-cancel-btn">Cancel</button>
        </div>
      )}

      <div className="workspaces-grid">
        {workspaces.length === 0 ? (
          <div className="empty-state glass-card">
            <FolderOpen size={32} color="var(--muted)" />
            <p>No workspaces yet. Create one to get started.</p>
          </div>
        ) : (
          workspaces.map((ws: any) => {
            const name = typeof ws === 'string' ? ws : ws.name
            const projects = ws.project_count ?? ws.projects?.length ?? 0
            const cost = ws.cost_total ?? 0
            const tokens = ws.tokens_total ?? 0
            return (
              <div key={name} className="workspace-card glass-card">
                <div className="workspace-card-header">
                  <div className="workspace-icon">
                    <FolderOpen size={20} color="var(--cyan)" />
                  </div>
                  <div className="workspace-info">
                    <h3>{name}</h3>
                    <p className="mono">
                      {projects} project{projects !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
                <div className="workspace-stats">
                  <div className="workspace-stat">
                    <DollarSign size={12} color="var(--gold)" />
                    <span className="mono">${cost.toFixed(4)}</span>
                  </div>
                  <div className="workspace-stat">
                    <Cpu size={12} color="var(--cyan)" />
                    <span className="mono">{(tokens / 1000).toFixed(1)}k tokens</span>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
