import { useState } from 'react'
import { api } from '../lib/api'
import { Send } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMsg: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const response = await api.sendChat(input, 'default')
      const assistantMsg: Message = {
        role: 'assistant',
        content: `Routing to ${response.routing.agent.toUpperCase()} (${response.routing.type}, confidence: ${response.routing.confidence.toFixed(1)})\n\n${response.routing.reason}\n\nApproval: ${response.approval.approved ? '✓ Approved' : '✗ ' + response.approval.reason}`,
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <h1 style={{ marginBottom: 16 }}>Chat with Cipher</h1>

      <div className="glass-card" style={{ flex: 1, overflow: 'auto', marginBottom: 16, padding: 24 }}>
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--muted)', paddingTop: 60 }}>
            <p style={{ fontSize: 14 }}>Send a message to the Orchestrator.</p>
            <p style={{ fontSize: 12, marginTop: 8 }}>Cipher will route your task to the right agent.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {messages.map((msg, i) => (
              <div key={i} style={{
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '75%',
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                background: msg.role === 'user' ? 'rgba(139, 92, 246, 0.15)' : 'rgba(31, 31, 43, 0.8)',
                border: `1px solid ${msg.role === 'user' ? 'rgba(139, 92, 246, 0.3)' : 'var(--border-card)'}`,
              }}>
                <div className="mono" style={{ fontSize: 10, marginBottom: 4, color: 'var(--muted)' }}>
                  {msg.role === 'user' ? 'YOU' : 'CIPHER'}
                </div>
                <div style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>{msg.content}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
          placeholder="Describe a task for the team..."
          disabled={loading}
          style={{
            flex: 1,
            padding: '12px 16px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-card)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--text)',
            fontFamily: 'var(--font-heading)',
            fontSize: 14,
            outline: 'none',
            backdropFilter: 'blur(20px)',
          }}
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          style={{
            padding: '12px 20px',
            background: 'rgba(139, 92, 246, 0.2)',
            border: '1px solid rgba(139, 92, 246, 0.3)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--violet-glow)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  )
}
