import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../lib/api'
import { Save, RotateCcw } from 'lucide-react'
import './Settings.css'

const EDITABLE_KEYS = ['routing', 'escalation', 'server', 'communication', 'recovery', 'pricing']

export default function Settings() {
  const qc = useQueryClient()
  const { data: settings } = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })
  const [edits, setEdits] = useState<Record<string, string>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState(false)

  const mutation = useMutation({
    mutationFn: (data: any) => api.updateSettings(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settings'] })
      setEdits({})
      setErrors({})
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    },
  })

  const getValue = (key: string, val: any) => {
    if (key in edits) return edits[key]
    return typeof val === 'object' ? JSON.stringify(val, null, 2) : String(val)
  }

  const handleChange = (key: string, value: string) => {
    setEdits(prev => ({ ...prev, [key]: value }))
    setErrors(prev => ({ ...prev, [key]: '' }))
  }

  const handleSave = () => {
    const newErrors: Record<string, string> = {}
    const update: Record<string, any> = {}

    for (const [key, raw] of Object.entries(edits)) {
      const original = settings?.[key]
      if (typeof original === 'object') {
        try {
          update[key] = JSON.parse(raw)
        } catch {
          newErrors[key] = 'Invalid JSON'
        }
      } else if (typeof original === 'number') {
        const n = Number(raw)
        if (isNaN(n)) { newErrors[key] = 'Must be a number'; continue }
        update[key] = n
      } else if (typeof original === 'boolean') {
        update[key] = raw === 'true'
      } else {
        update[key] = raw
      }
    }

    if (Object.keys(newErrors).length > 0) { setErrors(newErrors); return }
    if (Object.keys(update).length === 0) return
    mutation.mutate(update)
  }

  const handleReset = (key: string) => {
    setEdits(prev => { const n = { ...prev }; delete n[key]; return n })
    setErrors(prev => { const n = { ...prev }; delete n[key]; return n })
  }

  const hasEdits = Object.keys(edits).length > 0

  return (
    <div className="settings-page">
      <div className="page-header">
        <div>
          <h1>Settings</h1>
          <p className="page-subtitle">Global CIPHER-OS configuration</p>
        </div>
        {hasEdits && (
          <button className="save-btn" onClick={handleSave} disabled={mutation.isPending}>
            <Save size={15} />
            {mutation.isPending ? 'Saving…' : saved ? '✓ Saved' : 'Save Changes'}
          </button>
        )}
        {saved && !hasEdits && (
          <span className="save-confirm mono">✓ Saved</span>
        )}
      </div>

      <div className="settings-grid">
        {settings && Object.entries(settings)
          .filter(([key]) => EDITABLE_KEYS.includes(key))
          .map(([key, val]) => {
            const isObj = typeof val === 'object'
            const edited = key in edits
            const err = errors[key]
            return (
              <div key={key} className={`settings-section glass-card${edited ? ' settings-section--edited' : ''}`}>
                <div className="settings-section-header">
                  <h3 className="mono">{key.toUpperCase()}</h3>
                  {edited && (
                    <button className="settings-reset-btn" onClick={() => handleReset(key)} title="Reset">
                      <RotateCcw size={13} />
                    </button>
                  )}
                </div>
                {isObj ? (
                  <textarea
                    className={`settings-textarea mono${err ? ' settings-input--error' : ''}`}
                    value={getValue(key, val)}
                    onChange={e => handleChange(key, e.target.value)}
                    rows={Math.min(12, JSON.stringify(val, null, 2).split('\n').length + 1)}
                    spellCheck={false}
                  />
                ) : (
                  <input
                    className={`settings-input mono${err ? ' settings-input--error' : ''}`}
                    value={getValue(key, val)}
                    onChange={e => handleChange(key, e.target.value)}
                  />
                )}
                {err && <div className="settings-error">{err}</div>}
              </div>
            )
          })}

        {/* Read-only system info */}
        {settings && (
          <div className="settings-section glass-card settings-section--readonly">
            <div className="settings-section-header">
              <h3 className="mono">SYSTEM INFO</h3>
              <span className="settings-readonly-badge mono">read-only</span>
            </div>
            <div className="settings-entries">
              {['name', 'version'].map(key => settings[key] !== undefined && (
                <div key={key} className="settings-entry">
                  <span className="settings-key mono">{key.toUpperCase()}</span>
                  <span className="settings-value">{String(settings[key])}</span>
                </div>
              ))}
              {settings.hermes && (
                <div className="settings-entry">
                  <span className="settings-key mono">HERMES BINARY</span>
                  <span className="settings-value mono">{settings.hermes?.binary || '—'}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
