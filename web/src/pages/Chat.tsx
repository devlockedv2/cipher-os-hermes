import { useState, useRef, useEffect } from 'react'
import { api } from '../lib/api'
import { Send, CircleDot } from 'lucide-react'
import './Chat.css'

interface Message {
  role: 'user' | 'assistant'
  content: string
  routing?: { agent: string; type: string; confidence: number; reason: string }
  approved?: boolean
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const feedRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight
    }
  }, [messages])

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
        content: response.routing.reason,
        routing: response.routing,
        approved: response.approval?.approved,
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${err.message}`,
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-header">
        <CircleDot size={20} color="var(--violet)" />
        <div>
          <h1>Chat with Cipher</h1>
          <p className="mono">ORCHESTRATOR • ROUTES TO BEST AGENT</p>
        </div>
      </div>

      <div className="chat-feed glass-card" ref={feedRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            <CircleDot size={32} color="var(--violet)" />
            <h3>Ready for tasks</h3>
            <p>Describe what you need done. Cipher will route it to the right agent.</p>
            <div className="chat-suggestions">
              <button onClick={() => setInput('Fix the login bug in the auth module')}>Fix a bug</button>
              <button onClick={() => setInput('Research best practices for caching in microservices')}>Research something</button>
              <button onClick={() => setInput('Plan the v2 API migration')}>Plan a feature</button>
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`chat-message chat-message--${msg.role}`}>
              <div className="chat-message-sender mono">
                {msg.role === 'user' ? 'YOU' : 'CIPHER'}
              </div>
              <div className="chat-message-content">{msg.content}</div>
              {msg.routing && (
                <div className="chat-routing">
                  <span className="routing-agent mono">{msg.routing.agent}</span>
                  <span className="routing-type mono">{msg.routing.type}</span>
                  <span className={`routing-status ${msg.approved ? 'approved' : 'pending'}`}>
                    {msg.approved ? '✓ Approved' : '⏳ Needs approval'}
                  </span>
                </div>
              )}
            </div>
          ))
        )}
        {loading && (
          <div className="chat-message chat-message--assistant">
            <div className="chat-message-sender mono">CIPHER</div>
            <div className="chat-thinking">
              <span /><span /><span />
            </div>
          </div>
        )}
      </div>

      <div className="chat-input-row">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
          placeholder="Describe a task for the team..."
          disabled={loading}
          className="chat-input"
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="chat-send-btn"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  )
}
