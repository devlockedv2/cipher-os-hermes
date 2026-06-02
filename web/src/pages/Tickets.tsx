import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../lib/api'
import './Tickets.css'

const STATUS_COLUMNS = ['backlog', 'ready', 'in_progress', 'review', 'done']
const STATUS_LABELS: Record<string, string> = {
  backlog: 'Backlog', ready: 'Ready', in_progress: 'In Progress', review: 'Review', done: 'Done',
}
const STATUS_COLORS: Record<string, string> = {
  backlog: 'var(--muted)', ready: 'var(--cyan)', in_progress: 'var(--violet)',
  review: 'var(--amber)', done: 'var(--mint)',
}
const PRIORITY_LABELS: Record<number, string> = { 1: 'Critical', 2: 'High', 3: 'Medium', 4: 'Low', 5: 'Minimal' }
const PRIORITY_COLORS: Record<number, string> = {
  1: 'var(--red)', 2: 'var(--amber)', 3: 'var(--violet)', 4: 'var(--cyan)', 5: 'var(--muted)'
}
const AGENT_COLORS: Record<string, string> = {
  cipher: 'var(--violet)', lens: 'var(--cyan)', atlas: 'var(--mint)',
  forge: 'var(--amber)', sentinel: 'var(--red)',
}

export default function Tickets() {
  const { data: workspacesData = [] } = useQuery({
    queryKey: ['workspaces'],
    queryFn: api.getWorkspaces,
  })
  const workspaces: string[] = workspacesData.map((ws: any) => typeof ws === 'string' ? ws : ws.name)
  const [selectedWs, setSelectedWs] = useState('default')
  const activeWs = workspaces.includes(selectedWs) ? selectedWs : (workspaces[0] || 'default')

  const { data, isLoading, error } = useQuery({
    queryKey: ['tickets', activeWs],
    queryFn: () => api.getTickets(activeWs),
    refetchInterval: 10000,
  })

  const tickets: any[] = data?.tickets || []

  const byStatus = STATUS_COLUMNS.reduce((acc, s) => {
    acc[s] = tickets.filter(t => t.status === s)
    return acc
  }, {} as Record<string, any[]>)

  const openCount = tickets.filter(t => !['done', 'cancelled', 'failed'].includes(t.status)).length

  return (
    <div className="tickets-page">
      <div className="page-header">
        <div>
          <h1>Tickets</h1>
          <p className="page-subtitle">{openCount} open · {tickets.length} total</p>
        </div>
        {workspaces.length > 1 && (
          <div className="workspace-selector">
            {workspaces.map(ws => (
              <button
                key={ws}
                className={`ws-tab${activeWs === ws ? ' ws-tab--active' : ''}`}
                onClick={() => setSelectedWs(ws)}
              >
                {ws}
              </button>
            ))}
          </div>
        )}
      </div>

      {isLoading && <div className="loading">Loading tickets…</div>}
      {error && <div className="error-msg">Failed to load tickets</div>}

      {!isLoading && (
        <div className="kanban-board">
          {STATUS_COLUMNS.map(status => (
            <div className="kanban-column" key={status}>
              <div className="kanban-col-header">
                <span className="kanban-col-dot" style={{ background: STATUS_COLORS[status] }} />
                <span className="kanban-col-title">{STATUS_LABELS[status]}</span>
                <span className="kanban-col-count">{byStatus[status].length}</span>
              </div>
              <div className="kanban-cards">
                {byStatus[status].length === 0 && (
                  <div className="kanban-empty">No tickets</div>
                )}
                {byStatus[status].map(ticket => (
                  <div className="kanban-card" key={ticket.id}>
                    <div className="kanban-card-id mono">{ticket.id}</div>
                    <div className="kanban-card-title">{ticket.title}</div>
                    {ticket.assigned_to && (
                      <div
                        className="kanban-card-agent mono"
                        style={{ color: AGENT_COLORS[ticket.assigned_to] || 'var(--muted)' }}
                      >
                        → {ticket.assigned_to}
                      </div>
                    )}
                    <div className="kanban-card-meta">
                      <span
                        className="priority-badge mono"
                        style={{ color: PRIORITY_COLORS[ticket.priority] || 'var(--muted)' }}
                      >
                        {PRIORITY_LABELS[ticket.priority] || 'Medium'}
                      </span>
                      <span className="ticket-type mono">{ticket.type}</span>
                    </div>
                    {ticket.estimate && (
                      <div className="kanban-card-estimate mono">{ticket.estimate.toUpperCase()}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
