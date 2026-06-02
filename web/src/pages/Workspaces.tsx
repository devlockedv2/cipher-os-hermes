import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../lib/api'
import { FolderOpen, Plus } from 'lucide-react'
import './Workspaces.css'

export default function Workspaces() {
  const { data: workspaces = [], refetch } = useQuery({
    queryKey: ['workspaces'],
    queryFn: api.getWorkspaces,
  })
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')

  const handleCreate = async () => {
    if (!newName.trim()) return
    await api.createWorkspace(newName.trim().toLowerCase())
    setNewName('')
    setCreating(false)
    refetch()
  }

  return (
    <div className="workspaces-page">
      <div className="page-header">
        <div>
          <h1>Workspaces</h1>
          <p className="page-subtitle">Isolated environments for your projects</p>
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
            onKeyDown={e => e.key === 'Enter' && handleCreate()}
            placeholder="workspace-name"
            autoFocus
            className="workspace-input"
          />
          <button onClick={handleCreate} className="create-confirm-btn">Create</button>
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
          workspaces.map((ws: any) => (
            <div key={ws.name || ws} className="workspace-card glass-card">
              <div className="workspace-icon">
                <FolderOpen size={20} color="var(--cyan)" />
              </div>
              <div className="workspace-info">
                <h3>{typeof ws === 'string' ? ws : ws.name}</h3>
                <p className="mono">WORKSPACE</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
