import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Activity as ActivityIcon, DollarSign } from 'lucide-react'
import './Activity.css'

export default function Activity() {
  const { data } = useQuery({ queryKey: ['activity'], queryFn: () => api.getActivity() })
  const { data: stats } = useQuery({ queryKey: ['activity-stats'], queryFn: () => api.getActivityStats() })

  const entries = data?.entries || []

  return (
    <div className="activity-page">
      <div className="page-header">
        <h1>Activity Log</h1>
        <p className="page-subtitle">Token usage and cost tracking across agents</p>
      </div>

      {stats && (
        <div className="activity-stats-row">
          <div className="activity-stat glass-card">
            <ActivityIcon size={16} color="var(--cyan)" />
            <div>
              <div className="activity-stat-value">{stats.total_tasks || 0}</div>
              <div className="activity-stat-label mono">TOTAL TASKS</div>
            </div>
          </div>
          <div className="activity-stat glass-card">
            <DollarSign size={16} color="var(--gold)" />
            <div>
              <div className="activity-stat-value">${(stats.total_cost || 0).toFixed(4)}</div>
              <div className="activity-stat-label mono">TOTAL COST</div>
            </div>
          </div>
          <div className="activity-stat glass-card">
            <span style={{ color: 'var(--mint)', fontSize: 14, fontWeight: 600 }}>↑</span>
            <div>
              <div className="activity-stat-value">{((stats.total_input_tokens || 0) / 1000).toFixed(1)}k</div>
              <div className="activity-stat-label mono">INPUT TOKENS</div>
            </div>
          </div>
          <div className="activity-stat glass-card">
            <span style={{ color: 'var(--violet)', fontSize: 14, fontWeight: 600 }}>↓</span>
            <div>
              <div className="activity-stat-value">{((stats.total_output_tokens || 0) / 1000).toFixed(1)}k</div>
              <div className="activity-stat-label mono">OUTPUT TOKENS</div>
            </div>
          </div>
        </div>
      )}

      <div className="activity-table glass-card">
        {entries.length === 0 ? (
          <div className="empty-state">
            <ActivityIcon size={24} color="var(--muted)" />
            <p>No activity recorded yet.</p>
          </div>
        ) : (
          <div className="activity-list">
            {entries.map((entry: any, i: number) => (
              <div key={i} className="activity-list-item">
                <div className="activity-list-dot" style={{
                  background: entry.status === 'completed' ? 'var(--mint)' :
                              entry.status === 'running' ? 'var(--cyan)' :
                              entry.status === 'failed' ? 'var(--red)' : 'var(--muted)'
                }} />
                <div className="activity-list-content">
                  <div className="activity-list-task">{entry.task}</div>
                  <div className="activity-list-meta mono">
                    <span>{entry.agent}</span>
                    <span>•</span>
                    <span>{entry.model || 'default'}</span>
                    <span>•</span>
                    <span>{entry.workspace}</span>
                  </div>
                </div>
                <div className="activity-list-stats">
                  <div className="activity-list-tokens mono">
                    {entry.input_tokens || 0} / {entry.output_tokens || 0}
                  </div>
                  <div className="activity-list-cost mono">
                    ${(entry.cost || 0).toFixed(4)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
