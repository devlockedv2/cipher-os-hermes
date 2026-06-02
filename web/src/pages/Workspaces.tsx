import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../lib/api'
import { FolderOpen, Plus, Cpu, DollarSign, Link2, CheckCircle2, XCircle, Eye, EyeOff, ChevronDown } from 'lucide-react'
import './Workspaces.css'

export default function Workspaces() {
  const qc = useQueryClient()
  const { data: workspaces = [] } = useQuery({
    queryKey: ['workspaces'],
    queryFn: api.getWorkspaces,
  })
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [expandedWs, setExpandedWs] = useState<string | null>(null)
  const [linearKeys, setLinearKeys] = useState<Record<string, string>>({})
  const [showKey, setShowKey] = useState<Record<string, boolean>>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [saveResult, setSaveResult] = useState<Record<string, 'ok' | 'err' | null>>({})

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

  const handleSaveLinear = async (wsName: string) => {
    const key = (linearKeys[wsName] || '').trim()
    if (!key) return
    setSaving(s => ({ ...s, [wsName]: true }))
    setSaveResult(r => ({ ...r, [wsName]: null }))
    try {
      await api.setLinearKey(wsName, key)
      setSaveResult(r => ({ ...r, [wsName]: 'ok' }))
      qc.invalidateQueries({ queryKey: ['workspaces'] })
      setTimeout(() => setSaveResult(r => ({ ...r, [wsName]: null })), 3000)
    } catch {
      setSaveResult(r => ({ ...r, [wsName]: 'err' }))
    } finally {
      setSaving(s => ({ ...s, [wsName]: false }))
    }
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
            const linearOk = ws.linear_configured ?? false
            const expanded = expandedWs === name

            return (
              <div key={name} className={`workspace-card glass-card${expanded ? ' expanded' : ''}`}>
                <div className="workspace-card-main">
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
                    <div className="workspace-badges">
                      <span className={`integration-pill ${linearOk ? 'active' : 'inactive'}`}>
                        {linearOk
                          ? <><CheckCircle2 size={11} /> Linear</>
                          : <><XCircle size={11} /> Linear</>
                        }
                      </span>
                    </div>
                    <button
                      className={`expand-btn${expanded ? ' open' : ''}`}
                      onClick={() => setExpandedWs(expanded ? null : name)}
                      title="Settings"
                    >
                      <ChevronDown size={16} />
                    </button>
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

                {expanded && (
                  <div className="workspace-settings">
                    <div className="settings-section">
                      <div className="settings-section-title">
                        <Link2 size={13} />
                        <span>Linear Integration</span>
                        {linearOk && <span className="configured-badge">Configured</span>}
                      </div>
                      <p className="settings-hint">
                        Paste your Linear personal API key. Cipher will use it to fetch and create issues for this workspace.
                      </p>
                      <div className="api-key-row">
                        <div className="api-key-input-wrap">
                          <input
                            type={showKey[name] ? 'text' : 'password'}
                            className="api-key-input"
                            placeholder={linearOk ? '••••••••••••••••••••• (key saved)' : 'lin_api_…'}
                            value={linearKeys[name] ?? ''}
                            onChange={e => setLinearKeys(k => ({ ...k, [name]: e.target.value }))}
                            onKeyDown={e => e.key === 'Enter' && handleSaveLinear(name)}
                          />
                          <button
                            className="show-key-btn"
                            onClick={() => setShowKey(s => ({ ...s, [name]: !s[name] }))}
                            tabIndex={-1}
                          >
                            {showKey[name] ? <EyeOff size={14} /> : <Eye size={14} />}
                          </button>
                        </div>
                        <button
                          className="save-key-btn"
                          onClick={() => handleSaveLinear(name)}
                          disabled={saving[name] || !(linearKeys[name] || '').trim()}
                        >
                          {saving[name] ? 'Saving…' : 'Save'}
                        </button>
                      </div>
                      {saveResult[name] === 'ok' && (
                        <p className="save-success">✓ Linear key saved</p>
                      )}
                      {saveResult[name] === 'err' && (
                        <p className="save-error">Failed to save key</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
