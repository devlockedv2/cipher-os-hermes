import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CircleDot, Search, Compass, Hammer, Shield,
  ArrowLeft, Save, RotateCcw, Pencil, X, Check,
  CheckCircle2, XCircle, Clock, Zap, DollarSign, Activity
} from 'lucide-react'
import { api } from '../lib/api'
import './AgentDetail.css'

const AGENT_ICONS: Record<string, React.ElementType> = {
  cipher:   CircleDot,
  lens:     Search,
  atlas:    Compass,
  forge:    Hammer,
  sentinel: Shield,
}

const fmtCost = (n: number) => `$${(n || 0).toFixed(4)}`
const fmtCostShort = (n: number) => `$${(n || 0).toFixed(2)}`
const fmtTokens = (n: number | undefined | null) => {
  if (n == null || isNaN(n)) return '0'
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)
}
const fmtTime = (ts: string) => {
  const d = new Date(ts)
  const now = Date.now()
  const diff = now - d.getTime()
  if (diff < 60000) return 'just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return d.toLocaleDateString()
}

const STATUS_ICONS: Record<string, React.ElementType> = {
  completed: CheckCircle2,
  failed: XCircle,
  running: Clock,
}

export default function AgentDetail() {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [editingPrompt, setEditingPrompt] = useState(false)
  const [promptDraft, setPromptDraft] = useState('')
  const [savedConfig, setSavedConfig] = useState(false)

  // Local config state
  const [cfgModel, setCfgModel] = useState<string | null>(null)
  const [cfgMaxCost, setCfgMaxCost] = useState<number | null>(null)
  const [cfgTimeout, setCfgTimeout] = useState<number | null>(null)
  const [cfgWeight, setCfgWeight] = useState<number | null>(null)
  const [cfgEnabled, setCfgEnabled] = useState<boolean | null>(null)

  const { data: agentRaw, isLoading } = useQuery({
    queryKey: ['agent', name],
    queryFn: () => api.getAgent(name!),
  })
  const agent = agentRaw as any

  // Sync config state when agent data loads
  useState(() => {
    if (agent) {
      setCfgModel(agent.model)
      setCfgMaxCost(agent.max_cost)
      setCfgTimeout(agent.timeout)
      setCfgWeight(agent.routing_weight)
      setCfgEnabled(agent.enabled)
      if (!editingPrompt) setPromptDraft(agent.personality_md || '')
    }
  })

  const { data: actData } = useQuery({
    queryKey: ['agent-activity', name],
    queryFn: () => api.getAgentActivity(name!),
    refetchInterval: 15000,
  })

  const saveCfg = useMutation({
    mutationFn: () => api.updateAgentConfig(name!, {
      model: cfgModel || undefined,
      max_cost: cfgMaxCost ?? undefined,
      timeout: cfgTimeout ?? undefined,
      routing_weight: cfgWeight ?? undefined,
      enabled: cfgEnabled ?? undefined,
    }),
    onSuccess: () => { setSavedConfig(true); setTimeout(() => setSavedConfig(false), 2000); qc.invalidateQueries({ queryKey: ['agents'] }) },
  })

  const savePrompt = useMutation({
    mutationFn: () => api.updateAgentPersonality(name!, promptDraft),
    onSuccess: () => { setEditingPrompt(false); qc.invalidateQueries({ queryKey: ['agent'] }) },
  })

  const resetPrompt = useMutation({
    mutationFn: () => api.resetAgentPersonality(name!),
    onSuccess: () => { setEditingPrompt(false); qc.invalidateQueries({ queryKey: ['agent'] }) },
  })

  if (isLoading || !agent) return <div className="agent-detail-loading">Loading…</div>

  const agentData = agent as any
  const Icon = AGENT_ICONS[agentData.name] || CircleDot
  const color = agentData.color || '#8B5CF6'
  const stats = actData?.stats || {}
  const entries = actData?.entries || []

  return (
    <div className="agent-detail">
      {/* Header */}
      <div className="ad-header" style={{ '--agent-color': color } as any}>
        <div className="ad-header-bar" style={{ background: `linear-gradient(90deg, ${color}40, transparent)` }} />
        <button className="ad-back" onClick={() => navigate('/agents')}>
          <ArrowLeft size={16} /> Agents
        </button>
        <div className="ad-hero">
          <div className="ad-icon" style={{ color, background: `${color}20`, borderColor: `${color}50` }}>
            <Icon size={28} />
          </div>
          <div>
            <h1 className="ad-name">{agentData.name}</h1>
            <p className="ad-role">{agentData.role}</p>
          </div>
          <span className={`ad-status ad-status--${agentData.enabled === false ? 'disabled' : (agentData.status || 'idle')}`}>
            <span className="ad-dot" />
            {agentData.enabled === false ? 'disabled' : (agentData.status || 'idle')}
          </span>
        </div>
      </div>

      <div className="ad-body">
        {/* Stat bar */}
        <div className="ad-stat-bar">
          <div className="ad-stat">
            <CheckCircle2 size={14} style={{ color: 'var(--mint)' }} />
            <span className="ad-stat-val">{stats.tasks_completed ?? 0}</span>
            <span className="ad-stat-lbl">Completed</span>
          </div>
          <div className="ad-stat-div" />
          <div className="ad-stat">
            <XCircle size={14} style={{ color: 'var(--red)' }} />
            <span className="ad-stat-val ad-stat-val--fail">{stats.tasks_failed ?? 0}</span>
            <span className="ad-stat-lbl">Failed</span>
          </div>
          <div className="ad-stat-div" />
          <div className="ad-stat">
            <Zap size={14} style={{ color: 'var(--cyan)' }} />
            <span className="ad-stat-val">{fmtTokens(stats.input_tokens)}</span>
            <span className="ad-stat-lbl">In tokens</span>
          </div>
          <div className="ad-stat-div" />
          <div className="ad-stat">
            <Zap size={14} style={{ color: color }} />
            <span className="ad-stat-val">{fmtTokens(stats.output_tokens)}</span>
            <span className="ad-stat-lbl">Out tokens</span>
          </div>
          <div className="ad-stat-div" />
          <div className="ad-stat">
            <DollarSign size={14} style={{ color: 'var(--amber)' }} />
            <span className="ad-stat-val">{fmtCostShort(stats.total_cost)}</span>
            <span className="ad-stat-lbl">Total cost</span>
          </div>
        </div>

        <div className="ad-cols">
          {/* Left col: config + prompt */}
          <div className="ad-left">
            {/* Config card */}
            <div className="ad-card">
              <div className="ad-card-header">
                <span>Configuration</span>
                <button
                  className={`ad-save-btn ${savedConfig ? 'ad-save-btn--ok' : ''}`}
                  onClick={() => saveCfg.mutate()}
                  disabled={saveCfg.status === 'pending'}
                >
                  {savedConfig ? <><Check size={13} /> Saved</> : <><Save size={13} /> Save</>}
                </button>
              </div>

              <div className="ad-field">
                <label>Model override</label>
                <input
                  className="ad-input"
                  value={cfgModel || ''}
                  placeholder="inherit from hermes config"
                  onChange={e => setCfgModel(e.target.value)}
                />
              </div>

              <div className="ad-field-row">
                <div className="ad-field">
                  <label>Max cost ($)</label>
                  <input
                    className="ad-input"
                    type="number" min={0} step={0.5}
                    value={cfgMaxCost ?? ''}
                    onChange={e => setCfgMaxCost(parseFloat(e.target.value))}
                  />
                </div>
                <div className="ad-field">
                  <label>Timeout (s)</label>
                  <input
                    className="ad-input"
                    type="number" min={30} step={30}
                    value={cfgTimeout ?? ''}
                    onChange={e => setCfgTimeout(parseInt(e.target.value))}
                  />
                </div>
              </div>

              <div className="ad-field">
                <label>Routing weight <span className="ad-muted">({(cfgWeight ?? 1).toFixed(1)})</span></label>
                <input
                  type="range" min={0} max={2} step={0.1}
                  className="ad-slider"
                  style={{ '--thumb-color': color } as any}
                  value={cfgWeight ?? 1}
                  onChange={e => setCfgWeight(parseFloat(e.target.value))}
                />
              </div>

              <div className="ad-field ad-field--toggle">
                <label>Enabled</label>
                <button
                  className={`ad-toggle ${cfgEnabled !== false ? 'ad-toggle--on' : 'ad-toggle--off'}`}
                  style={cfgEnabled !== false ? { '--toggle-color': color } as any : {}}
                  onClick={() => setCfgEnabled(prev => !(prev !== false))}
                >
                  <span className="ad-toggle-knob" />
                </button>
              </div>
            </div>

            {/* Prompt card */}
            <div className="ad-card">
              <div className="ad-card-header">
                <span>
                  Personality prompt
                  {(agent as any).has_local_prompt && <span className="ad-badge">custom</span>}
                </span>
                <div style={{ display: 'flex', gap: 6 }}>
                  {!editingPrompt ? (
                    <button className="ad-icon-btn" onClick={() => { setEditingPrompt(true); setPromptDraft((agent as any).personality_md || '') }}>
                      <Pencil size={13} /> Edit
                    </button>
                  ) : (
                    <>
                      <button className="ad-icon-btn ad-icon-btn--save" onClick={() => savePrompt.mutate()}>
                        <Save size={13} /> Save
                      </button>
                      <button className="ad-icon-btn ad-icon-btn--cancel" onClick={() => setEditingPrompt(false)}>
                        <X size={13} />
                      </button>
                    </>
                  )}
                  {(agent as any).has_local_prompt && (
                    <button className="ad-icon-btn ad-icon-btn--reset" onClick={() => resetPrompt.mutate()} title="Reset to default">
                      <RotateCcw size={13} />
                    </button>
                  )}
                </div>
              </div>
              {editingPrompt ? (
                <textarea
                  className="ad-textarea"
                  value={promptDraft}
                  onChange={e => setPromptDraft(e.target.value)}
                  rows={16}
                />
              ) : (
                <pre className="ad-prompt-preview">{(agent as any).personality_md || 'No prompt loaded.'}</pre>
              )}
            </div>
          </div>

          {/* Right col: activity log */}
          <div className="ad-right">
            <div className="ad-card ad-card--full">
              <div className="ad-card-header">
                <span><Activity size={13} style={{ marginRight: 6 }} />Recent Activity</span>
                <span className="ad-muted">{entries.length} entries</span>
              </div>

              {entries.length === 0 ? (
                <div className="ad-empty">No activity yet</div>
              ) : (
                <div className="ad-activity-list">
                  {entries.map((e: any) => {
                    const SIcon = STATUS_ICONS[e.status] || Clock
                    return (
                      <div key={e.uuid} className={`ad-activity-row ad-activity-row--${e.status}`}>
                        <SIcon size={13} className="ad-act-icon" />
                        <div className="ad-act-body">
                          <div className="ad-act-task">{e.task}</div>
                          <div className="ad-act-meta">
                            <span className="ad-act-ws">{e.workspace}</span>
                            <span className="ad-act-sep">·</span>
                            <span>{fmtTokens(e.input_tokens + e.output_tokens)} tok</span>
                            <span className="ad-act-sep">·</span>
                            <span>{fmtCost(e.cost)}</span>
                            <span className="ad-act-sep">·</span>
                            <span className="ad-act-time">{fmtTime(e.created_at)}</span>
                          </div>
                        </div>
                        <span className={`ad-act-status ad-act-status--${e.status}`}>{e.status}</span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
