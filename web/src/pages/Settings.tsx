import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export default function Settings() {
  const { data: settings } = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <h1 style={{ marginBottom: 24 }}>Settings</h1>
      <div className="glass-card">
        <h3 style={{ marginBottom: 16 }}>Configuration</h3>
        <pre style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 12,
          color: 'var(--text)',
          background: 'rgba(0,0,0,0.3)',
          padding: 16,
          borderRadius: 'var(--radius-sm)',
          overflow: 'auto',
          maxHeight: 500,
        }}>
          {JSON.stringify(settings, null, 2)}
        </pre>
      </div>
    </div>
  )
}
