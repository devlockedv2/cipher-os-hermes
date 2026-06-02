import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Settings as SettingsIcon } from 'lucide-react'
import './Settings.css'

export default function Settings() {
  const { data: settings } = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })

  return (
    <div className="settings-page">
      <div className="page-header">
        <h1>Settings</h1>
        <p className="page-subtitle">Global configuration for CIPHER-OS</p>
      </div>

      <div className="settings-grid">
        <div className="settings-section glass-card">
          <h3><SettingsIcon size={16} /> General</h3>
          {settings ? (
            <div className="settings-entries">
              {Object.entries(settings).map(([key, value]) => (
                <div key={key} className="settings-entry">
                  <span className="settings-key mono">{key.toUpperCase()}</span>
                  <span className="settings-value">
                    {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="settings-loading">Loading configuration...</p>
          )}
        </div>
      </div>
    </div>
  )
}
