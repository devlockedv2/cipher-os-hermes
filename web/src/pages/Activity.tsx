import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export default function Activity() {
  const { data } = useQuery({ queryKey: ['activity'], queryFn: () => api.getActivity() })
  const entries = data?.entries || []

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ marginBottom: 24 }}>Activity Log</h1>
      <div className="glass-card">
        {entries.length === 0 ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--muted)' }}>
            No activity recorded yet.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left' }}>
                <th className="label" style={{ padding: '8px 12px' }}>Agent</th>
                <th className="label" style={{ padding: '8px 12px' }}>Task</th>
                <th className="label" style={{ padding: '8px 12px' }}>Status</th>
                <th className="label" style={{ padding: '8px 12px' }}>Cost</th>
                <th className="label" style={{ padding: '8px 12px' }}>Time</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e: any, i: number) => (
                <tr key={i} style={{ borderTop: '1px solid var(--border-card)' }}>
                  <td className="mono" style={{ padding: '8px 12px', color: 'var(--cyan)' }}>{e.agent}</td>
                  <td style={{ padding: '8px 12px', fontSize: 13 }}>{e.task?.slice(0, 60)}</td>
                  <td style={{ padding: '8px 12px' }}><span className={`status-tag ${e.status}`}>{e.status}</span></td>
                  <td style={{ padding: '8px 12px', color: 'var(--gold)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>${(e.cost || 0).toFixed(4)}</td>
                  <td className="mono" style={{ padding: '8px 12px', fontSize: 11, color: 'var(--muted)' }}>{e.created_at?.slice(11, 19)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
