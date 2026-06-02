import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import {
  CircleDot, Search, Compass, Hammer, Shield,
  ChevronDown, ChevronUp, RotateCcw, Save, Pencil, X
} from 'lucide-react'
import './Agents.css'

const AGENT_ICONS: Record<string, React.ElementType> = {
  cipher:   CircleDot,
  lens:     Search,
  atlas:    Compass,
  forge:    Hammer,
  sentinel: Shield,
}

export default function Agents() {
  const [expanded, setExpanded] = useState<string | null>(null)
  const [searchParams] = useSearchParams()

  // Open agent from ?open= query param (e.g. from dashboard cards)
  useEffect(() => {
    const openAgent = searchParams.get('open')
    if (openAgent) setExpanded(openAgent)
  }, [searchParams])

  const { data: agents = [], isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: api.getAgents,
  })

  const toggle = (name: string) =>
    setExpanded(prev => prev === name ? null : name)

  return (
    <div className="agents-page">
      <div className="page-header">
        <h1>Agent Fleet</h1>
        <p className="page-subtitle">Configure and monitor your AI team</p>
      </div>

      {isLoading ? (
        <div className="loading-row">Loading agents…</div>
      ) : (
        <div className="agents-list">
          {agents.map((agent: any) => (
            <AgentRow
              key={agent.name}
              agent={agent}
              open={expanded === agent.name}
              onToggle={() => toggle(agent.name)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Agent row + drawer ──────────────────────────────────────────────────────

function AgentRow({ agent, open, onToggle }: {
  agent: any
  open: boolean
  onToggle: () => void
}) {
  const qc = useQueryClient()
  const Icon = AGENT_ICONS[agent.name] || CircleDot
  const color = agent.color || '#8B5CF6'
  const rowRef = useRef<HTMLDivElement>(null)

  // Scroll into view when opened
  useEffect(() => {
    if (open && rowRef.current) {
      setTimeout(() => rowRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
    }
  }, [open])

  // Fetch full detail (including personality) only when expanded
  const { data: detail } = useQuery({
    queryKey: ['agent', agent.name],
    queryFn: () => api.getAgent(agent.name),
    enabled: open,
  })

  // Config fields state — initialised from list data
  const [cfg, setCfg] = useState({
    model:          agent.model || '',
    max_cost:       agent.max_cost ?? 5.0,
    routing_weight: agent.routing_weight ?? 1.0,
    timeout:        agent.timeout ?? 300,
    enabled:        agent.enabled ?? true,
  })

  // Prompt editor state
  const [promptMode, setPromptMode] = useState(false)
  const [promptText, setPromptText] = useState('')

  // Sync prompt text when detail loads
  if (detail && promptText === '' && !promptMode) {
    setPromptText(detail.personality_md || '')
  }

  const configMutation = useMutation({
    mutationFn: (data: typeof cfg) => api.updateAgentConfig(agent.name, {
      ...data,
      model: data.model || undefined,
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  })

  const promptMutation = useMutation({
    mutationFn: (text: string) => api.updatePersonality(agent.name, text),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agent', agent.name] })
      setPromptMode(false)
    },
  })

  const resetMutation = useMutation({
    mutationFn: () => api.resetPersonality(agent.name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agent', agent.name] })
      setPromptText('')
      setPromptMode(false)
    },
  })

  return (
    <div
      ref={rowRef}
      className={`agent-row glass-card ${open ? 'agent-row--open' : ''}`}
    >
      {/* ── Summary bar ── */}
      <button className="agent-row-header" onClick={onToggle}>
        <div className="agent-row-left">
          <div className="agent-row-icon" style={{ color, borderColor: `${color}55`, background: `${color}18` }}>
            <Icon size={18} />
          </div>
          <div className="agent-row-info">
            <span className="agent-row-name">{agent.name}</span>
            <span className="agent-row-role mono">{agent.role}</span>
          </div>
        </div>

        <div className="agent-row-meta">
          <span className={`status-pill status-pill--${agent.enabled === false ? 'disabled' : agent.status}`}>
            <span className={`status-dot status-dot--${agent.enabled === false ? 'disabled' : agent.status}`} />
            {agent.enabled === false ? 'disabled' : (agent.status || 'idle')}
          </span>
          <span className="agent-meta-item mono">${(agent.total_cost || 0).toFixed(3)}</span>
          <span className="agent-meta-item mono">{agent.tasks_completed || 0} tasks</span>
          {open ? <ChevronUp size={16} className="chevron" /> : <ChevronDown size={16} className="chevron" />}
        </div>
      </button>

      {/* ── Drawer ── */}
      {open && (
        <div className="agent-drawer">
          <p className="agent-description">{agent.description}</p>

          <div className="drawer-grid">
            {/* ── Config panel ── */}
            <div className="drawer-panel">
              <h4 className="drawer-panel-title">Configuration</h4>

              <label className="field-label">Model override
                <span className="field-hint">leave blank to inherit global</span>
              </label>
              <input
                className="field-input"
                placeholder="e.g. us.anthropic.claude-sonnet-4-5-20250929-v1:0"
                value={cfg.model}
                onChange={e => setCfg(p => ({ ...p, model: e.target.value }))}
              />

              <div className="field-row">
                <div className="field-group">
                  <label className="field-label">Max cost (USD)
                    <span className="field-hint">per task</span>
                  </label>
                  <input
                    className="field-input"
                    type="number"
                    min="0.01"
                    step="0.5"
                    value={cfg.max_cost}
                    onChange={e => setCfg(p => ({ ...p, max_cost: parseFloat(e.target.value) || 0 }))}
                  />
                </div>
                <div className="field-group">
                  <label className="field-label">Timeout (s)</label>
                  <input
                    className="field-input"
                    type="number"
                    min="30"
                    step="30"
                    value={cfg.timeout}
                    onChange={e => setCfg(p => ({ ...p, timeout: parseInt(e.target.value) || 300 }))}
                  />
                </div>
              </div>

              <label className="field-label">Routing weight
                <span className="field-hint">0 = never route, 2 = prefer</span>
              </label>
              <div className="slider-row">
                <input
                  type="range"
                  min="0" max="2" step="0.1"
                  value={cfg.routing_weight}
                  onChange={e => setCfg(p => ({ ...p, routing_weight: parseFloat(e.target.value) }))}
                  className="slider"
                  style={{ '--thumb-color': color } as any}
                />
                <span className="slider-value mono">{cfg.routing_weight.toFixed(1)}</span>
              </div>

              <div className="toggle-row">
                <span className="field-label" style={{ margin: 0 }}>Enabled</span>
                <button
                  className={`toggle ${cfg.enabled ? 'toggle--on' : 'toggle--off'}`}
                  style={{ '--toggle-color': color } as any}
                  onClick={() => setCfg(p => ({ ...p, enabled: !p.enabled }))}
                />
              </div>

              <button
                className="btn btn-primary"
                style={{ '--btn-color': color, '--btn-color-dim': `${color}33` } as any}
                disabled={configMutation.isPending}
                onClick={() => configMutation.mutate(cfg)}
              >
                <Save size={14} />
                {configMutation.isPending ? 'Saving…' : 'Save config'}
              </button>

              {configMutation.isSuccess && (
                <span className="save-ok">✓ Saved</span>
              )}
            </div>

            {/* ── Prompt panel ── */}
            <div className="drawer-panel">
              <div className="drawer-panel-title-row">
                <h4 className="drawer-panel-title">
                  System prompt
                  {detail?.has_local_prompt && <span className="badge-custom">custom</span>}
                </h4>
                <div className="prompt-actions">
                  {!promptMode && (
                    <button className="btn-icon" title="Edit prompt" onClick={() => setPromptMode(true)}>
                      <Pencil size={14} />
                    </button>
                  )}
                  {promptMode && (
                    <button className="btn-icon" title="Cancel" onClick={() => setPromptMode(false)}>
                      <X size={14} />
                    </button>
                  )}
                  {detail?.has_local_prompt && (
                    <button
                      className="btn-icon btn-icon--danger"
                      title="Reset to default"
                      onClick={() => resetMutation.mutate()}
                      disabled={resetMutation.isPending}
                    >
                      <RotateCcw size={14} />
                    </button>
                  )}
                </div>
              </div>

              {promptMode ? (
                <>
                  <textarea
                    className="prompt-editor"
                    value={promptText}
                    onChange={e => setPromptText(e.target.value)}
                    rows={12}
                    spellCheck={false}
                  />
                  <button
                    className="btn btn-primary"
                    style={{ '--btn-color': color, '--btn-color-dim': `${color}33` } as any}
                    disabled={promptMutation.isPending}
                    onClick={() => promptMutation.mutate(promptText)}
                  >
                    <Save size={14} />
                    {promptMutation.isPending ? 'Saving…' : 'Save prompt'}
                  </button>
                </>
              ) : (
                <pre className="prompt-preview">{promptText || (detail ? '(loading…)' : '(expand to load)')}</pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
