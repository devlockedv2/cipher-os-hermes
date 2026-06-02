import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import {
  CircleDot, Search, Compass, Hammer, Shield,
  Loader, CheckCircle, XCircle, Clock, Bot
} from 'lucide-react'
import './Plan.css'

const AGENT_ICONS: Record<string, any> = {
  cipher: CircleDot, lens: Search, atlas: Compass, forge: Hammer, sentinel: Shield,
}
const AGENT_COLORS: Record<string, string> = {
  cipher: '#8B5CF6', lens: '#06B6D4', atlas: '#10B981', forge: '#F59E0B', sentinel: '#EF4444',
}

const COL_ICONS: Record<string, any> = {
  running: Loader,
  pending: Clock,
  completed: CheckCircle,
  failed: XCircle,
}

function fmtTime(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH}h ago`
  return d.toLocaleDateString()
}

function fmtCost(n: number) {
  if (!n) return null
  return '$' + (n < 0.001 ? '<0.001' : n.toFixed(4))
}

function TaskCard({ task }: { task: any }) {
  const color = AGENT_COLORS[task.agent] || '#8B5CF6'
  const Icon = AGENT_ICONS[task.agent] || Bot
  return (
    <div className="task-card glass-card">
      <div className="task-accent" style={{ background: color }} />
      <div className="task-body">
        <div className="task-text">{task.task}</div>
        <div className="task-footer">
          <div className="task-agent" style={{ color }}>
            <Icon size={11} />
            <span>{task.agent}</span>
          </div>
          <div className="task-meta">
            {task.workspace !== 'default' && (
              <span className="task-workspace">{task.workspace}</span>
            )}
            {fmtCost(task.cost) && (
              <span className="task-cost">{fmtCost(task.cost)}</span>
            )}
            <span className="task-time">{fmtTime(task.created_at)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Plan() {
  const [workspace, setWorkspace] = useState<string | undefined>(undefined)

  const { data, isLoading } = useQuery({
    queryKey: ['plan', workspace],
    queryFn: () => api.getPlan(workspace),
    refetchInterval: 8000,
  })

  return (
    <div className="plan-page">
      {/* Header */}
      <div className="plan-header">
        <div>
          <h1 className="plan-title">Plan</h1>
          <p className="plan-subtitle">Active and recent tasks across all agents</p>
        </div>
        <div className="plan-controls">
          {data?.workspaces && (
            <select
              className="ws-select"
              value={workspace || ''}
              onChange={e => setWorkspace(e.target.value || undefined)}
            >
              <option value="">All workspaces</option>
              {data.workspaces.map((ws: string) => (
                <option key={ws} value={ws}>{ws}</option>
              ))}
            </select>
          )}
          <div className="plan-total mono">
            {data?.total || 0} tasks
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="plan-loading">Loading...</div>
      ) : (
        <div className="plan-board">
          {(data?.columns || []).map((col: any) => {
            const ColIcon = COL_ICONS[col.id] || Clock
            return (
              <div key={col.id} className="plan-column">
                <div className="col-header">
                  <div className="col-title-row">
                    <ColIcon size={14} style={{ color: col.color }} className={col.id === 'running' ? 'spin' : ''} />
                    <span className="col-title" style={{ color: col.color }}>{col.label}</span>
                  </div>
                  <span className="col-count" style={{ background: `${col.color}22`, color: col.color }}>
                    {col.tasks.length}
                  </span>
                </div>
                <div className="col-tasks">
                  {col.tasks.length === 0 ? (
                    <div className="col-empty">No tasks</div>
                  ) : (
                    col.tasks.slice(0, 30).map((t: any) => (
                      <TaskCard key={t.uuid} task={t} />
                    ))
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
