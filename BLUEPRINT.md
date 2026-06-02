# CIPHER-OS Blueprint

> Distributable agent OS layer on Hermes. Installable script users run on their own Hermes server.
> Template-able naming: CIPHER-OS or {AGENT_NAME}-OS for custom branding.

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                 WEB UI (Command Center)               │
│   Dashboard · Tickets · Workspaces · Agent Monitor    │
│   Chat (Orchestrator) · Settings · History            │
└──────────────────────────┬──────────────────────────┘
                           │ API (FastAPI + WebSocket)
┌──────────────────────────▼──────────────────────────┐
│                CIPHER-OS CORE (Python)                │
│   Agent Spawner · Ticket Engine · Workspace Manager   │
│   Memory Engine · Rules Engine · Knowledge Loader     │
└──┬───────────────────────────────────────────────────┘
   │
   │  Spawns as Hermes Profiles (parallel processes)
   │
┌──▼──────────────────────────────────────────────────┐
│                    AGENT ROSTER                        │
│                                                       │
│  Cipher (Orchestrator) — Routes, delegates, approves  │
│  Lens (Researcher) — Deep research, source synthesis  │
│  Atlas (Planner) — Architecture, planning, estimation │
│  Forge (Developer) — Code, tests, refactoring         │
│  Sentinel (DevOps) — Infra, deploy, monitoring        │
│                                                       │
└──────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────┐
│                    WORKSPACES                          │
│                                                       │
│  ~/.cipher-os/workspaces/                             │
│  ├── workspace-alpha/                                 │
│  │   ├── config.yaml        (workspace overrides)     │
│  │   ├── .env               (workspace env vars)      │
│  │   ├── memories/          (per-agent workspace mem) │
│  │   ├── knowledge/         (shared KB)               │
│  │   ├── sessions/          (per-agent session DBs)   │
│  │   ├── tickets/           (SQLite ticket board)     │
│  │   └── projects/                                    │
│  │       └── project-x/                               │
│  │           ├── .cipher.yaml (project overrides)     │
│  │           └── repo/                                │
│  └── workspace-beta/                                  │
│       └── ...                                         │
└──────────────────────────────────────────────────────┘
```

---

## Agent Identity System

| Agent | Name | Role | Core Trait |
|-------|------|------|------------|
| Orchestrator | Cipher | Routes tasks, delegates, approves plans | Strategic, decisive |
| Researcher | Lens | Deep research, source synthesis | Thorough, curious |
| Planner | Atlas | Architecture, estimation, planning | Structured, scope-aware |
| Developer | Forge | Code, tests, refactoring | Precise, pragmatic |
| DevOps | Sentinel | Infra, deploy, monitoring | Reliable, security-minded |

### Identity Guarantees

- Immutable `personality.md` per agent
- Double-anchored (system prompt + first memory line)
- Agents aware of each other's existence and capabilities
- Boundaries enforced — agents refuse out-of-scope work and redirect

### Profile Layout

```
~/.hermes/profiles/
├── cipher-orchestrator/
│   ├── config.yaml
│   ├── personality.md
│   ├── memories/
│   ├── state.db
│   └── skills/
├── cipher-researcher/
├── cipher-planner/
├── cipher-developer/
└── cipher-devops/
```

---

## Memory System

### Engine

- **Storage:** SQLite + FTS5 (zero external dependencies)
- **View layer:** Auto-synced markdown files (bidirectional)
- **Rationale:** Distributable installer = zero deps mandatory. FTS5 handles agent-written memories perfectly. Semantic search is overkill at this scale.

### Two-Tier Scoping

```
Profile Memory (general)              Workspace Memory (project-specific)
━━━━━━━━━━━━━━━━━━━━━━━              ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"I prefer pytest over unittest"       "project-alpha uses FastAPI + SQLAlchemy"
"React apps usually need X setup"     "staging server is at 10.0.1.50"
Persists across all workspaces        Isolated to one workspace
```

### Schema

```sql
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    scope TEXT NOT NULL,            -- 'profile' or 'workspace:<name>'
    category TEXT,                  -- 'pattern', 'fact', 'preference', 'decision'
    content TEXT NOT NULL,
    source_session TEXT,
    created_at TIMESTAMP,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    pinned BOOLEAN DEFAULT FALSE
);

CREATE VIRTUAL TABLE memories_fts USING fts5(content, category, agent);
```

### Lifecycle

- **Write:** → SQLite (source of truth) → Auto-export to .md (human-readable)
- **Read:** → FTS5 query at session start → Load relevant memories → Increment access_count
- **Prune:** → Low access_count + old age → archived. Pinned = exempt.
- **Edit:** → User edits .md → file watcher syncs to SQLite (or via Web UI)

### Write Rules

| Event | Writes To |
|-------|-----------|
| Agent learns a general pattern | Profile memory |
| Agent learns something project-specific | Workspace memory |
| Agent makes a decision worth preserving | Workspace knowledge (shared) |
| Conversation happens | Workspace session DB |

---

## Shared Knowledge Base

```
~/.cipher-os/
├── knowledge/                     # GLOBAL (all workspaces)
│   ├── team-roster.md             # Agent capabilities
│   ├── workflows.md               # Collaboration patterns
│   └── standards.md               # Universal conventions
│
└── workspaces/alpha/knowledge/    # PER-WORKSPACE
    ├── architecture.md
    ├── conventions.md
    └── decisions.md               # ADRs
```

---

## Session Continuity

- Each agent gets a workspace-scoped session DB
- `session_search` queries prior conversations per-agent-per-workspace
- Agents build institutional knowledge over time
- Compounding: short-term (session) → medium-term (session search) → long-term (memory)

---

## Config Inheritance

```
Global (~/.cipher-os/config.yaml)
  └── Workspace (workspaces/alpha/config.yaml)
       └── Project (projects/x/.cipher.yaml)
```

Each level can override: env vars, model, tools, repo path, branch strategy, CI config, agent preferences.

---

## Ticket System

- **Engine:** SQLite per workspace
- **States:** `backlog → ready → in_progress → review → done`
- **Features:** priority, dependencies, agent assignment, cross-agent creation
- **Orchestrator** monitors all boards, auto-assigns based on ticket type/tags

---

## Activity Log

### Engine

Single global SQLite database: `~/.cipher-os/activity.db`

### Schema

```sql
CREATE TABLE activity_log (
    uuid TEXT PRIMARY KEY,
    workspace TEXT NOT NULL,
    project TEXT,
    agent TEXT NOT NULL,
    model TEXT NOT NULL,
    task TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_activity_workspace ON activity_log(workspace);
CREATE INDEX idx_activity_project ON activity_log(project);
CREATE INDEX idx_activity_agent ON activity_log(agent);
CREATE INDEX idx_activity_status ON activity_log(status);
CREATE INDEX idx_activity_created_at ON activity_log(created_at);
CREATE INDEX idx_activity_workspace_agent ON activity_log(workspace, agent);
CREATE INDEX idx_activity_workspace_project ON activity_log(workspace, project);
```

### Status Values

```
queued → running → completed
                 → failed
                 → cancelled
```

### Self-Logging Mechanism

Agents call a script/function to log themselves. No external watcher.

**Script location:** `~/.cipher-os/scripts/log_activity.py`

**CLI usage:**
```bash
cipher-log --workspace alpha --project api-service --agent forge --model claude-opus-4-7 --task "Added refresh token rotation" --status running
cipher-log --uuid <uuid> --status completed
cipher-log --uuid <uuid> --status failed
```

**Python usage:**
```python
from cipher_os.activity import log

# Single call for simple replies
log(
    workspace="alpha",
    project="api-service",
    agent="forge",
    model="claude-opus-4-7",
    task="Explained JWT refresh flow",
    status="completed"
)

# Two calls for multi-step work
entry = log(workspace="alpha", project="api-service", agent="forge",
            model="claude-opus-4-7", task="Implementing refresh token rotation",
            status="running")
# ... work ...
log(uuid=entry.uuid, status="completed")
```

---

## Operations Rules (Universal)

Loaded FIRST in every session. Cannot be overridden by personality.

```
~/.cipher-os/rules/
├── operations.md         # Universal rules (below)
├── safety.md             # Future: guardrails, forbidden actions
└── overrides/
    └── devops.md         # Future: agent-specific rule additions
```

### Load Order (every agent, every session)

```
1. operations.md    (rules — highest priority)
2. personality.md   (identity)
3. knowledge/       (shared context)
4. workspace memory (project context)
```

### Rules Content

```
PROGRESS RULES:
- On any task with more than one step, send a short status line before starting each step.
  Format: '[Agent]: Step X of Y — [what you are doing now]'
- If you are waiting on a sub-agent, say so: '[Main]: Waiting on Scribe...'
- Never go silent for more than 60 seconds on an active task.
  Send: '[Agent]: Still working — [what is taking time]'

APPROVAL RULES:
- Always show what you plan to do before you do it.
- Orchestrator auto-approves routine sub-agent plans.
- Destructive/irreversible actions (deploys to prod, data deletion, external payments) → escalate to user.

COMMUNICATION RULES:
- Keep responses short and clear. No padding, no filler.
- When giving options always label them: 1, 2, 3 or A, B, C.
- Lead with the decision needed, not background context.
- Never open with 'Great question', 'Certainly', or 'Absolutely'.

DELEGATION RULES:
- Tell which sub-agent you are delegating to and why, in one line.
- Pass structured briefs to sub-agents, never raw conversation.
- If a sub-agent fails or goes silent, report immediately.
- Never fabricate a result. If it failed, say so.

LOGGING RULES:
- Log EVERY response. No exceptions. Simple replies, quick answers, everything.
- Task description: concise and meaningful, under 140 characters.
- Status "completed" when response succeeded.
- Status "failed" if something went wrong.
- Log at start (status=running) and end (status=completed/failed) for multi-step work.
- Log once (status=completed/failed) for single responses.
```

---

## Approval Hierarchy

```
User ← only sees destructive/irreversible actions
  │
Cipher (Orchestrator) ← approves routine sub-agent plans
  │
Lens / Atlas / Forge / Sentinel ← submit plans before execution
```

---

## Web UI (Command Center)

### Stack

- **Backend:** FastAPI (Python — direct access to Hermes internals)
- **Frontend:** TBD (user providing designs)
- **Streaming:** WebSocket for live agent output

### Features

- 🏠 Dashboard — active agents, recent activity, health
- 📋 Ticket Board — kanban view, drag-n-drop, all workspaces
- 📁 Workspace Manager — create, configure, browse
- 🤖 Agent Monitor — live output, logs, streaming
- 💬 Chat — direct to Orchestrator (on-demand trigger)
- ⚙️ Settings — config, profiles, env vars
- 📊 History — past runs, outcomes

---

## Still To Define

- [ ] Ticket schema (full fields, priorities, dependency format)
- [ ] API endpoints (REST + WebSocket events)
- [ ] Orchestrator routing logic (how Cipher decides who to call)
- [ ] Agent personality.md content (full prompts for each)
- [ ] Installer script mechanics (`cipher-os install`)
- [ ] Web UI designs / frontend framework
- [ ] Safety rules (`rules/safety.md`)
- [ ] Agent-specific rule overrides
- [ ] Authentication for Web UI (self-hosted vs deployable)

---

## Distribution

Single installer script that sets up everything on any Hermes server:
- Creates profiles
- Sets up directory structure
- Installs scripts
- Initializes databases
- Configures rules and knowledge base
- Template-able for custom agent names
