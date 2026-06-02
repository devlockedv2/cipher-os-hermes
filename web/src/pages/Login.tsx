import { useState, useEffect } from 'react'
import { auth } from '../lib/api'
import { Shield } from 'lucide-react'

export default function Login({ onLogin }: { onLogin: () => void }) {
  const [isSetup, setIsSetup] = useState<boolean | null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    auth.status().then(s => setIsSetup(s.setup_complete)).catch(() => setIsSetup(false))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (!isSetup) {
        // First-time setup
        if (password !== confirmPassword) {
          setError('Passwords do not match')
          setLoading(false)
          return
        }
        if (password.length < 8) {
          setError('Password must be at least 8 characters')
          setLoading(false)
          return
        }
        const res = await auth.setup(username, password)
        auth.setToken(res.token)
      } else {
        // Login
        const res = await auth.login(username, password)
        auth.setToken(res.token)
      }
      onLogin()
    } catch (err: any) {
      setError(err.message || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  if (isSetup === null) return null // Loading

  return (
    <div className="login-container">
      <div className="login-card glass-card">
        <div className="login-header">
          <Shield size={40} color="var(--violet)" />
          <h1>CIPHER-OS</h1>
          <p className="mono">{isSetup ? 'COMMAND CENTER LOGIN' : 'INITIAL SETUP'}</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group">
            <label className="mono">USERNAME</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="admin"
              required
              autoFocus
            />
          </div>

          <div className="input-group">
            <label className="mono">PASSWORD</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          {!isSetup && (
            <div className="input-group">
              <label className="mono">CONFIRM PASSWORD</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
          )}

          {error && <div className="login-error">{error}</div>}

          <button type="submit" disabled={loading} className="login-button">
            {loading ? 'Authenticating...' : isSetup ? 'Login' : 'Create Account'}
          </button>
        </form>

        {!isSetup && (
          <p className="setup-note">
            First time? Create your admin credentials above.
          </p>
        )}
      </div>
    </div>
  )
}
