import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export default function Tickets() {
  const { data } = useQuery({
    queryKey: ['tickets'],
    queryFn: () => api.getTickets('default'),
  })

  const tickets = data?.tickets || []

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ marginBottom: 24 }}>Tickets</h1>
      <div className="glass-card">
        {tickets.length === 0 ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--muted)' }}>
            No tickets yet. Create a workspace and start assigning tasks.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {tickets.map((t: any) => (
              <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '8px 16px', borderBottom: '1px solid var(--border-card)' }}>
                <span className="mono" style={{ color: 'var(--cyan)', width: 100 }}>{t.id}</span>
                <span style={{ flex: 1 }}>{t.title}</span>
                <span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>{t.assigned_to || 'unassigned'}</span>
                <span className={`status-tag ${t.status}`}>{t.status}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
