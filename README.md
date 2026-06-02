# CIPHER-OS

> Multi-Agent OS layer for [Hermes Agent](https://github.com/NousResearch/hermes-agent)

CIPHER-OS adds a persistent multi-agent orchestration layer on top of Hermes — with 5 specialised agents, workspace isolation, ticket management, and a web-based Command Center UI.

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/devlockedv2/cipher-os-hermes/main/install.sh | bash
```

### Options

```bash
# Custom name and port
curl -fsSL .../install.sh | bash -s -- --name "MY-OS" --port 9900

# Skip service setup
curl -fsSL .../install.sh | bash -s -- --no-service

# Skip post-install health check
curl -fsSL .../install.sh | bash -s -- --no-verify
```

## Requirements

- Python 3.10+
- Git
- Node.js 18+ *(for the web UI — optional)*
- [Hermes Agent](https://github.com/NousResearch/hermes-agent)

## Agents

| Agent | Role |
|-------|------|
| **Cipher** | Orchestrator — routes tasks, manages agents |
| **Lens** | Researcher — web search, analysis, summaries |
| **Atlas** | Planner — project planning, task decomposition |
| **Forge** | Developer — writes and reviews code |
| **Sentinel** | DevOps — deploys, monitors, maintains infrastructure |

## CLI

```bash
cipher-os init          # First-run setup
cipher-os status        # System status
cipher-os start         # Start the server
cipher-os stop          # Stop the server
cipher-os update        # Update to latest version
cipher-os logs          # Tail server logs
cipher-os workspace list
cipher-os workspace create <name>
```

## Web UI

Open `http://localhost:9800` after install. Create your admin credentials on first visit.

## Configuration

Data lives at `~/.cipher-os/`:

```
~/.cipher-os/
├── config.yaml       # Main config
├── workspaces/       # Workspace data
├── agents/           # Agent personality overrides
├── skills/           # Global skills
├── memory/           # Agent memory
└── logs/             # Server logs
```

## License

MIT
