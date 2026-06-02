import { useState, useEffect } from 'react'
import { auth, setToken } from '../lib/api'
import { Shield } from 'lucide-react'
import './Login.css'

export default function Login({ onLogin }: { onLogin: () => void }) {
  const [isSetup, setIsSetup] = useState<boolean | null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    auth.status().then(s => setIsSetup(s.setup_complete)).catch(() => setIsSetup(false))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!isSetup && password !== confirm) {
      setError('Passwords do not match')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    setLoading(true)
    try {
      let result: { token?: string; success?: boolean }
      if (isSetup) {
        result = await auth.login(username, password)
      } else {
        result = await auth.setup(username, password)
      }
      if (result.token) {
        setToken(result.token)
        onLogin()
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  if (isSetup === null) return (
    <div className="login-container">
      <div className="login-loading">Connecting...</div>
    </div>
  )

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-logo">
          <div className="logo-orb">
            <Shield size={28} />
          </div>
          <h1>CIPHER-OS</h1>
          <p className="login-tagline">Command Center</p>
        </div>

        {!isSetup && (
          <div className="setup-banner">
            Initial Setup — create your admin credentials
          </div>
        )}

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="admin"
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          {!isSetup && (
            <div className="form-group">
              <label>Confirm Password</label>
              <input
                type="password"
                value={confirm}
                onChange={e => setConfirm(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
          )}

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? 'Please wait...' : isSetup ? 'Sign In' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  )
}
