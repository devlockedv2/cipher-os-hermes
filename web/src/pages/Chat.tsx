import { useState, useRef, useEffect, useCallback } from 'react'
import { getToken } from '../lib/api'
import { Send, CircleDot, Search, Compass, Hammer, Shield, Bot, AlertTriangle, Ticket } from 'lucide-react'
import './Chat.css'

interface Message {
  role: 'user' | 'assistant' | 'system' | 'thinking'
  content: string
  agent?: string
  ticket_id?: string
  streaming?: boolean
  error?: boolean
}

const AGENT_ICONS: Record<string, React.ReactNode> = {
  cipher:   <CircleDot size={14} />,
  lens:     <Search size={14} />,
  atlas:    <Compass size={14} />,
  forge:    <Hammer size={14} />,
  sentinel: <Shield size={14} />,
}

const AGENT_COLORS: Record<string, string> = {
  cipher:   '#8B5CF6',
  lens:     '#7DD3FC',
  atlas:    '#5EE2B5',
  forge:    '#F5B544',
  sentinel: '#F26D6D',
}

const SUGGESTIONS = [
  'Research the latest trends in AI agent frameworks',
  'Plan a REST API with authentication and rate limiting',
  'Review my code for security vulnerabilities',
  'Set up a CI/CD pipeline for a Node.js project',
]

function getWsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const token = getToken()
  return `${proto}//${host}/api/v1/chat/ws${token ? `?token=${token}` : ''}`
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([{
    role: 'system',
    content: 'Connected to CIPHER-OS. Send a task to get started.',
  }])
  const [input, setInput] = useState('')
  const [workspace] = useState('default')
  const [connected, setConnected] = useState(false)
  const [busy, setBusy] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => { scrollToBottom() }, [messages])

  // ── WebSocket lifecycle ────────────────────────────────────────────────
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(getWsUrl())
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
    }

    ws.onclose = () => {
      setConnected(false)
      setBusy(false)
      // Reconnect after 3s
      reconnectTimer.current = setTimeout(connect, 3000)
    }

    ws.onerror = () => {
      setConnected(false)
    }

    ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        handleEvent(event)
      } catch {
        // ignore malformed
      }
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  // ── Event handler ──────────────────────────────────────────────────────
  const routedRef = useRef(false)

  const handleEvent = (event: { type: string; [key: string]: unknown }) => {
    switch (event.type) {
      case 'thinking': {
        // Only show dots before routing — once routing card + streaming bubble exist, cursor is enough
        if (routedRef.current) break
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (last?.role === 'thinking') return prev // already showing
          return [...prev, { role: 'thinking', content: '' }]
        })
        break
      }
      case 'routing': {
        routedRef.current = true
        const agent = event.agent as string
        setMessages(prev => {
          const filtered = prev.filter(m => m.role !== 'thinking')
          return [...filtered, {
            role: 'system',
            content: `Routing to **${agent}**`,
            agent,
          }]
        })
        // Start empty streaming message
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: '',
          agent,
          streaming: true,
        }])
        break
      }

      case 'token': {
        const content = event.content as string
        setMessages(prev => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last?.streaming) {
            updated[updated.length - 1] = { ...last, content: last.content + content }
          }
          return updated
        })
        break
      }

      case 'ticket': {
        setMessages(prev => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last?.streaming) {
            updated[updated.length - 1] = { ...last, ticket_id: event.ticket_id as string }
          }
          return updated
        })
        break
      }

      case 'done': {
        setMessages(prev => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last?.streaming) {
            updated[updated.length - 1] = { ...last, streaming: false }
          }
          return updated
        })
        setBusy(false)
        break
      }

      case 'error': {
        setMessages(prev => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last?.streaming) {
            // Replace the streaming message with the error
            updated[updated.length - 1] = {
              ...last,
              streaming: false,
              error: true,
              content: (event.content as string) || 'An error occurred',
            }
          } else {
            updated.push({
              role: 'system',
              content: (event.content as string) || 'An error occurred',
              error: true,
            })
          }
          return updated
        })
        setBusy(false)
        break
      }

      case 'blocked': {
        setMessages(prev => [...prev, {
          role: 'system',
          content: `⚠️ Task blocked: ${event.content}`,
          error: true,
        }])
        setBusy(false)
        break
      }
    }
  }

  // ── Send message ───────────────────────────────────────────────────────
  const send = (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || busy || !connected) return

    setMessages(prev => [...prev, { role: 'user', content: trimmed }])
    setInput('')
    setBusy(true)
    routedRef.current = false  // reset for new message

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        message: trimmed,
        workspace,
      }))
    } else {
      setMessages(prev => [...prev, {
        role: 'system',
        content: 'Not connected — reconnecting...',
        error: true,
      }])
      setBusy(false)
      connect()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <div className="chat-page">
      <div className="chat-header">
        <div className="chat-header-left">
          <div className="cipher-avatar">
            <CircleDot size={18} />
          </div>
          <div>
            <div className="chat-title">Cipher</div>
            <div className="chat-subtitle">Orchestrator</div>
          </div>
        </div>
        <div className={`ws-status ${connected ? 'connected' : 'disconnected'}`}>
          <span className="ws-dot" />
          {connected ? 'Live' : 'Reconnecting...'}
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <ChatBubble key={i} msg={msg} />
        ))}
        {busy && !messages.find(m => m.streaming) && (
          <div className="thinking">
            <span /><span /><span />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {messages.length === 1 && (
        <div className="suggestions">
          {SUGGESTIONS.map((s, i) => (
            <button key={i} className="suggestion-chip" onClick={() => send(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="chat-input-row">
        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder={connected ? 'Ask Cipher anything...' : 'Connecting...'}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={busy || !connected}
          rows={1}
        />
        <button
          className="send-btn"
          onClick={() => send(input)}
          disabled={!input.trim() || busy || !connected}
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  )
}

function ChatBubble({ msg }: { msg: Message }) {
  const agentColor = msg.agent ? AGENT_COLORS[msg.agent] || '#8B5CF6' : '#8B5CF6'
  const agentIcon = msg.agent ? AGENT_ICONS[msg.agent] || <Bot size={14} /> : null

  if (msg.role === 'thinking') {
    return (
      <div className="thinking-indicator">
        <div className="thinking-dot" />
        <div className="thinking-dot" />
        <div className="thinking-dot" />
      </div>
    )
  }

  if (msg.role === 'system') {
    return (
      <div className={`system-msg ${msg.error ? 'system-error' : ''}`}>
        {msg.error && <AlertTriangle size={12} />}
        <span dangerouslySetInnerHTML={{ __html: msg.content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
      </div>
    )
  }

  if (msg.role === 'user') {
    return (
      <div className="bubble-row user-row">
        <div className="bubble user-bubble">{msg.content}</div>
      </div>
    )
  }

  return (
    <div className="bubble-row agent-row">
      <div className="agent-avatar" style={{ background: `${agentColor}22`, color: agentColor, border: `1px solid ${agentColor}44` }}>
        {agentIcon}
      </div>
      <div className="bubble agent-bubble">
        <div className="agent-label" style={{ color: agentColor }}>
          {msg.agent || 'cipher'}
          {msg.ticket_id && (
            <span className="ticket-badge">
              <Ticket size={10} /> {msg.ticket_id}
            </span>
          )}
        </div>
        <div className={`agent-content ${msg.streaming ? 'streaming' : ''} ${msg.error ? 'error-content' : ''}`}>
          {msg.content || (msg.streaming ? '' : '—')}
          {msg.streaming && <span className="cursor" />}
        </div>
      </div>
    </div>
  )
}
